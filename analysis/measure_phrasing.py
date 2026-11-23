#!/usr/bin/env python3
"""Measure phrasing, melodic shape and tessitura on an ABC score.

The checker measures bars, register mean/top, duration spread, ties and
syllable ratio. It cannot see how the voice *moves*: how long it sings without
a breath, whether every phrase ends on the same pitch, or whether the line is a
scale. Those are the differences a listener hears first, and this script puts
numbers on them.

    python3 analysis/measure_phrasing.py score.abc [more.abc ...]
    python3 analysis/measure_phrasing.py --corpus <dir> --out analysis/out

Definitions (all in the shipped ABC dialect, no listening):

- **phrase** = a contiguous run of vocal notes. A phrase ends at any rest, a
  section change, or a rest of at least one beat (the checker's boundary).
  `phrase_rest` uses any rest, `phrase_beat` uses the checker's one-beat rule.
- **unbroken singing** = wall-clock seconds from the first note of a phrase to
  the last note's end, i.e. how long the singer goes without a breath.
- **pause** = the silence between two phrases, in seconds. Only gaps of at
  least 0.3 s count as a breath; shorter gaps are articulation, not breath.
- **stepwise** = share of intervals inside a phrase with |semitones| <= 2.
- **repeated** = share of intervals inside a phrase with 0 semitones.
- **phrase endings** = the pitch class of the last note of each phrase.
- **tessitura** = share of vocal notes at or above C5 (MIDI 72); median MIDI.
- **duration mix** = share of the most common, and of eighths/quarters, in
  L-units so it is comparable across `L:1/16` and `L:1/32` scores.

No score is modified. The corpus mode is for calibrating a threshold; write the
distribution, then decide the gate class, never the reverse.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import Counter
from fractions import Fraction
from pathlib import Path

import calibrate_177 as cal


PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _phrase_split(notes: list[dict], bars: list[dict], unit: Fraction,
                  boundary: str) -> list[list[dict]]:
    out: list[list[dict]] = []
    cur: list[dict] = []
    prev_end: Fraction | None = None
    for n in notes:
        bi = cal.bar_index(bars, n["onset"])
        if boundary == "rest":
            split = prev_end is not None and n["onset"] > prev_end
        else:  # checker rule: a rest of at least one beat, or a section change
            split = bool(cur) and (n["section"] != cur[-1]["section"]
                                   or (prev_end is not None
                                       and n["onset"] - prev_end >= bars[bi]["length"] / 4))
        if cur and split:
            out.append(cur)
            cur = []
        cur.append(n)
        prev_end = n["onset"] + n["dur"]
    if cur:
        out.append(cur)
    # `rest` keeps one-note fragments so gaps are measured exactly; the beat
    # boundary drops them, as the checker does.
    return out if boundary == "rest" else [p for p in out if len(p) >= 2]


def _seconds(units: Fraction, unit: Fraction, tempo: float) -> float:
    """Quarter-note positions -> seconds.

    `parse_score` keeps onsets and durations in quarter notes already, so the
    L-unit conversion is not applied again here.
    """
    return float(units) * 60.0 / tempo


def measure(path: Path) -> dict:
    parsed = cal.parse_score(path)
    bars = parsed["voices"]["Vocal"].bars
    notes = sorted(parsed["voices"]["Vocal"].notes, key=lambda n: n["onset"])
    unit = parsed["unit"]
    tempo = parsed["tempo"]
    if not notes:
        raise cal.AbcError("no vocal notes")

    rest_phrases = _phrase_split(notes, bars, unit, "rest")
    beat_phrases = _phrase_split(notes, bars, unit, "beat")

    def span_s(ph: list[dict]) -> float:
        return _seconds(ph[-1]["onset"] + ph[-1]["dur"] - ph[0]["onset"], unit, tempo)

    # breaths: any internal gap, and gaps long enough to be a real breath
    gaps: list[float] = []
    for a, b in zip(rest_phrases, rest_phrases[1:]):
        end = a[-1]["onset"] + a[-1]["dur"]
        if b[0]["onset"] > end:
            gaps.append(_seconds(b[0]["onset"] - end, unit, tempo))
    breaths = [g for g in gaps if g >= 0.3]

    # melodic intervals inside a phrase (never across a breath)
    intervals: list[int] = []
    for ph in rest_phrases:
        for a, b in zip(ph, ph[1:]):
            intervals.append(b["pitch"] - a["pitch"])

    # phrase-ending pitch classes, using the checker's phrase boundary so it is
    # comparable to the checker's answer-rate metric
    endings = [PC_NAME[ph[-1]["pitch"] % 12] for ph in beat_phrases]
    ending_counts = Counter(endings)
    distinct_endings = len(ending_counts)

    # phrase peaks and the jump between consecutive peaks
    peaks = [max(n["pitch"] for n in ph) for ph in beat_phrases]
    peak_jumps = [abs(b - a) for a, b in zip(peaks, peaks[1:])]

    pitches = [n["pitch"] for n in notes]
    durations = Counter(n["dur"] for n in notes)
    total = sum(durations.values())
    top_dur = max(durations, key=durations.get)

    # eighths/quarters in sixteenth-note units, so L:1/32 scores compare.
    # `parse_score` stores durations in quarter notes; one sixteenth is 1/4.
    dur16 = {d: float(d) * 4 for d in durations}
    eighth = sum(n for d, n in durations.items() if abs(dur16[d] - 2.0) < 1e-9)
    quarter = sum(n for d, n in durations.items() if abs(dur16[d] - 4.0) < 1e-9)
    sixteenth = sum(n for d, n in durations.items() if abs(dur16[d] - 1.0) < 1e-9)

    # verse/chorus median contrast
    verse = [n["pitch"] for n in notes if n["section"].startswith("verse")]
    chorus = [n["pitch"] for n in notes if n["section"] == "chorus"]

    return {
        "path": str(path),
        "bars": len(bars),
        "seconds": _seconds(sum(b["length"] for b in bars), unit, tempo),
        "tempo": tempo,
        "vocal_notes": len(notes),
        "phrases_rest": len(rest_phrases),
        "phrases_beat": len(beat_phrases),
        "phrase_seconds_median": round(st.median(span_s(p) for p in rest_phrases), 2),
        "phrase_seconds_max": round(max(span_s(p) for p in rest_phrases), 2),
        "unbroken_seconds_max": round(max(span_s(p) for p in rest_phrases), 2),
        "breaths": len(breaths),
        "breaths_per_bar": round(len(breaths) / len(bars), 3),
        "breath_seconds_median": round(st.median(breaths), 2) if breaths else None,
        "gap_seconds_median": round(st.median(gaps), 2) if gaps else None,
        "stepwise_share": round(sum(1 for i in intervals if abs(i) <= 2) / len(intervals), 3)
        if intervals else None,
        "repeated_share": round(sum(1 for i in intervals if i == 0) / len(intervals), 3)
        if intervals else None,
        "leap_share": round(sum(1 for i in intervals if abs(i) > 4) / len(intervals), 3)
        if intervals else None,
        "distinct_phrase_endings": distinct_endings,
        "phrase_endings": dict(ending_counts.most_common()),
        "final_ending": endings[-1] if endings else None,
        "peak_jump_median": round(st.median(peak_jumps), 1) if peak_jumps else None,
        "peak_jump_max": max(peak_jumps) if peak_jumps else None,
        "register_median": st.median(pitches),
        "tessitura_share_ge_C5": round(sum(1 for p in pitches if p >= 72) / len(pitches), 3),
        "top_duration_share": round(durations[top_dur] / total, 3),
        "eighth_share": round(eighth / total, 3),
        "quarter_share": round(quarter / total, 3),
        "sixteenth_share": round(sixteenth / total, 3),
        "verse_median": round(st.median(verse), 1) if verse else None,
        "chorus_median": round(st.median(chorus), 1) if chorus else None,
        "verse_chorus_semitones": round(st.median(chorus) - st.median(verse), 1)
        if verse and chorus else None,
    }


def band(values: list[float]) -> dict:
    v = sorted(x for x in values if x is not None)
    if not v:
        return {"n": 0}

    def pct(p: float) -> float:
        return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]

    return {"n": len(v), "min": round(v[0], 3), "p5": round(pct(0.05), 3),
            "p25": round(pct(0.25), 3), "median": round(st.median(v), 3),
            "p75": round(pct(0.75), 3), "p95": round(pct(0.95), 3),
            "max": round(v[-1], 3)}


METRICS = [
    "phrases_beat", "phrase_seconds_median", "unbroken_seconds_max",
    "breaths_per_bar", "breath_seconds_median", "stepwise_share",
    "repeated_share", "leap_share", "distinct_phrase_endings",
    "peak_jump_median", "peak_jump_max", "register_median",
    "tessitura_share_ge_C5", "top_duration_share", "eighth_share",
    "quarter_share", "verse_chorus_semitones",
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scores", nargs="*", type=Path)
    ap.add_argument("--corpus", type=Path, default=None,
                    help="directory of five_stars transcripts (transcripts/*.abc)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    files: list[Path] = list(args.scores)
    if args.corpus:
        root = args.corpus / "transcripts"
        files += sorted((root if root.is_dir() else args.corpus).glob("*.abc"))
    if not files:
        ap.error("give at least one score or --corpus")

    rows, errors = [], []
    for f in files:
        try:
            rows.append(measure(f))
        except (cal.AbcError, OSError, ValueError) as exc:
            errors.append({"path": str(f), "error": str(exc)})

    report = {"n": len(rows), "errors": errors,
              "distributions": {m: band([r[m] for r in rows]) for m in METRICS}}
    if len(files) <= 20:
        report["scores"] = rows
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(f"wrote {args.out}", file=__import__("sys").stderr)
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
