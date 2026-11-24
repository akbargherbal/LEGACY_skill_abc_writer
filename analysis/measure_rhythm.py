#!/usr/bin/env python3
"""Measure the rhythm section: phrase starts, lengths, gaps, onsets, drum cues.

The checker answers "is this a valid score of the declared shape?". This script
answers "can a drummer interact with this?". It is report-only: no gate, no
calibration, no score rewrite.

The metrics were chosen from the session-04 failure (2026-11-24): 26 phrases,
all starting on beat 1, all the same 3-bar length, gaps of 1 or 2 beats, 55%
eighth notes, and no drum voice in the seed. That score passed `--strict-style`
with 0 warnings and was heard as a drummer playing his own idea.

Usage:
    python3 analysis/measure_rhythm.py score.abc
    python3 analysis/measure_rhythm.py score.abc --seed seed.abc --json
    python3 analysis/measure_rhythm.py --corpus ~/.../five_stars --out analysis/out

The corpus mode is indicative only: the 177 transcripts have two voices and no
drum staff. Use it to place a score's phrase starts/lengths/gaps next to the
corpus, not to grade a drum part.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_177 as cal  # noqa: E402
import measure_phrasing as mp  # noqa: E402

DURATION = re.compile(r"([_^=]?[A-Ga-g][,']*)(\d*)(-?)")
REST = re.compile(r"[zZ](\d*)")
LENGTH = re.compile(r"^L:\s*1/(\d+)\s*$")
METER = re.compile(r"^M:\s*(\d+)/(\d+)\s*$")


def _positions(notes: list[dict], bars: list[dict], unit: Fraction) -> list[dict]:
    """Attach bar, 16th-position and end-16th-position to every vocal note."""
    out = []
    for n in notes:
        bi = cal.bar_index(bars, n["onset"])
        start = sum(b["length"] for b in bars[:bi])
        s16 = float((n["onset"] - start) / unit)
        e16 = float((n["onset"] + n["dur"] - start) / unit)
        out.append({**n, "bar_index": bi, "s16": round(s16, 2),
                    "e16": round(e16, 2)})
    return out


def _seed_drums(path: Path, bars: list[dict], unit: Fraction) -> dict | None:
    """Parse a free-ABC `V: Drums` voice. Returns None when there is no drum voice."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^V:\s*(Drums?|Percussion|Perc)\b", line, re.I):
            start = i + 1
            break
    if start is None:
        return None

    # The seed may carry its own L:; use it when present, else the score unit.
    seed_unit = unit
    for line in lines:
        m = LENGTH.match(line.strip())
        if m:
            seed_unit = Fraction(1, int(m.group(1)))
            break

    hits: list[dict] = []
    bar_i = 0
    for line in lines[start:]:
        s = line.strip()
        if s.startswith("V:"):
            break
        if not s or s.startswith("%") or s.startswith("K:") or s.startswith("M:") \
                or s.startswith("L:") or s.startswith("Q:") or s.startswith("X:") \
                or s.startswith("T:"):
            continue
        for bar in s.split("|"):
            bar = bar.strip()
            if not bar:
                continue
            whole = re.fullmatch(r"Z(\d*)", bar)
            if whole:
                bar_i += int(whole.group(1) or 1)
                continue
            pos = Fraction(0)
            for token in re.finditer(r"([_^=]?[A-Ga-g][,']*)(\d*)(-?)|([zZ])(\d*)", bar):
                if token.group(4):  # rest inside the bar
                    value = int(token.group(5) or 1)
                    pos += value * seed_unit
                else:
                    value = int(token.group(2) or 1)
                    hits.append({
                        "bar": bar_i,
                        "pos16": round(float(pos / seed_unit), 2),
                        "pitch": token.group(1),
                        "dur16": value,
                    })
                    pos += value * seed_unit
            bar_i += 1
    return {"path": str(path), "hits": hits, "bars_seen": bar_i,
            "seed_unit": str(seed_unit)}


def _drum_interaction(hits: list[dict], vocal: list[dict], bars: list[dict],
                      unit: Fraction) -> dict:
    """How many drum hits fall in a vocal rest, and where the fills are."""
    sounding = [(n["onset"], n["onset"] + n["dur"]) for n in vocal]
    in_rest = 0
    under = 0
    fill_bars: Counter[int] = Counter()
    for hit in hits:
        if hit["bar"] >= len(bars):
            continue
        start = sum(b["length"] for b in bars[:hit["bar"]])
        onset = start + Fraction(hit["pos16"]) * unit
        under_voice = any(a <= onset < b for a, b in sounding)
        under += under_voice
        in_rest += not under_voice
        if not under_voice:
            fill_bars[hit["bar"]] += 1
    total = len(hits)
    return {
        "hits": total,
        "hits_in_vocal_rest": in_rest,
        "hits_under_vocal": under,
        "share_in_vocal_rest": round(in_rest / total, 3) if total else None,
        "fill_bars": sorted(b for b, n in fill_bars.items() if n >= 3),
        "drop_bars": sorted(set(range(len(bars))) - {h["bar"] for h in hits}),
    }


def measure(path: Path, seed: Path | None = None) -> dict:
    parsed = cal.parse_score(path)
    voice = parsed["voices"]["Vocal"]
    unit = parsed["unit"]
    notes = sorted(voice.notes, key=lambda n: n["onset"])
    if not notes:
        raise cal.AbcError("no vocal notes")
    bars = voice.bars
    pos = _positions(notes, bars, unit)
    phrases = mp._phrase_split(notes, bars, unit, "beat")
    if len(phrases) < 4:
        raise ValueError("fewer than 4 phrases")

    starts: Counter[float] = Counter()
    lengths: Counter[float] = Counter()
    ends: Counter[float] = Counter()
    gaps: Counter[float] = Counter()
    onsets: Counter[float] = Counter()
    for p in phrases:
        first = pos[next(i for i, n in enumerate(pos) if n["onset"] == p[0]["onset"])]
        last = pos[next(i for i, n in enumerate(pos) if n["onset"] == p[-1]["onset"])]
        starts[first["s16"]] += 1
        ends[last["e16"] % 16] += 1
        lengths[round((p[-1]["onset"] + p[-1]["dur"] - p[0]["onset"]) / unit, 2)] += 1
    for a, b in zip(phrases, phrases[1:]):
        gap = b[0]["onset"] - (a[-1]["onset"] + a[-1]["dur"])
        gaps[round(float(gap / unit), 2)] += 1
    for n in pos:
        onsets[n["s16"]] += 1

    total = len(pos)
    quarter = sum(c for s, c in onsets.items() if abs(s % 4) < 1e-6)
    weak16 = sum(c for s, c in onsets.items() if abs(s - round(s)) < 1e-6 and int(s) % 2 == 1)
    sustain3 = sum(1 for n in pos if n["s16"] < 8 < n["e16"])
    cross = sum(1 for n in pos if n["e16"] > 16)
    line_gaps = Counter({k: v for k, v in gaps.items() if k <= 8})

    flags: list[str] = []
    if len(starts) == 1:
        flags.append(f"all {len(phrases)} phrases start on the same beat "
                     f"({sorted(starts)[0]:g}/16): no pickup, no cue")
    top2 = sum(v for _, v in lengths.most_common(2)) if lengths else 0
    if len(phrases) >= 8 and len(lengths) <= 3 and top2 / len(phrases) >= 0.8:
        top = ", ".join(f"{k:g}" for k, _ in lengths.most_common(2))
        flags.append(f"{top2}/{len(phrases)} phrases use only "
                     f"{min(2, len(lengths))} lengths ({top} 16ths): "
                     "the 3-bar frame")
    if len(phrases) >= 8 and len(line_gaps) <= 3:
        flags.append(f"line-end gaps use only {len(line_gaps)} lengths "
                     f"({', '.join(f'{k:g}' for k in sorted(line_gaps))} 16ths): "
                     "the breath is a metronome")
    if total and weak16 / total < 0.05:
        flags.append(f"weak-16th onsets {weak16}/{total} "
                     f"({weak16 / total:.1%}): almost no 16th syncopation")
    if total and sustain3 / total < 0.05:
        flags.append(f"{sustain3}/{total} notes sustain through beat 3: "
                     "no weight on the backbeat")
    if not any(g >= 8 for g in line_gaps):
        flags.append("no 2-beat gap: the drummer has no fill window")

    drum = None
    if seed is not None:
        drum = _seed_drums(seed, bars, unit)
        if drum is None:
            flags.append("no Drums voice in the seed: the drummer is unspecified")
        else:
            inter = _drum_interaction(drum["hits"], notes, bars, unit)
            drum.update(inter)
            if inter["share_in_vocal_rest"] is not None and inter["share_in_vocal_rest"] < 0.5:
                flags.append(f"only {inter['share_in_vocal_rest']:.0%} of drum hits "
                             "fall in a vocal rest: the drums are a bed, not an answer")

    return {
        "file": str(path),
        "seed": str(seed) if seed else None,
        "bars": len(bars),
        "phrases": len(phrases),
        "phrase_starts": {str(k): v for k, v in sorted(starts.items())},
        "distinct_phrase_starts": len(starts),
        "phrase_lengths_16ths": {str(k): v for k, v in sorted(lengths.items())},
        "distinct_phrase_lengths": len(lengths),
        "phrase_end_positions": {str(k): v for k, v in sorted(ends.items())},
        "gaps_16ths": {str(k): v for k, v in sorted(gaps.items())},
        "line_gaps_16ths": {str(k): v for k, v in sorted(line_gaps.items())},
        "distinct_gaps": len(gaps),
        "onsets_16ths": {str(k): v for k, v in sorted(onsets.items())},
        "quarter_beat_share": round(quarter / total, 3) if total else None,
        "weak16_share": round(weak16 / total, 3) if total else None,
        "sustain_beat3": sustain3,
        "barline_crossings": cross,
        "drums": drum,
        "flags": flags,
    }


def print_track(m: dict) -> None:
    print(f"\n{m['file']}")
    print(f"  bars {m['bars']}  phrases {m['phrases']}")
    print(f"  starts (16ths): {m['phrase_starts']}  distinct {m['distinct_phrase_starts']}")
    print(f"  lengths (16ths): {m['phrase_lengths_16ths']}  distinct {m['distinct_phrase_lengths']}")
    print(f"  gaps (16ths): {m['gaps_16ths']}  distinct {m['distinct_gaps']}")
    print(f"  line-end gaps: {m['line_gaps_16ths']}")
    print(f"  cadence positions: {m['phrase_end_positions']}")
    print(f"  onsets: quarter-beat {m['quarter_beat_share']:.2f}  "
          f"weak-16th {m['weak16_share']:.2f}  "
          f"sustain beat 3 {m['sustain_beat3']}  barline {m['barline_crossings']}")
    if m["drums"] is None:
        print("  drums: absent")
    elif "hits" in m["drums"]:
        d = m["drums"]
        print(f"  drums: {d['hits']} hits; {d['share_in_vocal_rest']:.0%} in a vocal rest; "
              f"fills {d['fill_bars']}")
    if m["flags"]:
        print("  flags:")
        for f in m["flags"]:
            print(f"    - {f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scores", nargs="*", type=Path)
    ap.add_argument("--seed", type=Path, help="seed.abc with an optional V: Drums voice")
    ap.add_argument("--corpus", type=Path, help="five_stars root (transcripts/*.abc)")
    ap.add_argument("--out", type=Path, help="write rhythm.json here")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    args = ap.parse_args(argv)

    paths = list(args.scores)
    if args.corpus:
        root = args.corpus / "transcripts"
        paths += sorted((root if root.is_dir() else args.corpus).glob("*.abc"))
    if not paths:
        ap.error("give at least one score, or --corpus")

    rows, errors = [], []
    for path in paths:
        try:
            rows.append(measure(path, args.seed))
        except Exception as exc:  # noqa: BLE001
            errors.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})
    payload = {"metric_basis": "session-04 failure + corpus:n=177 (two-voice)",
               "rows": rows, "errors": errors}
    if args.corpus and rows:
        for key in ("distinct_phrase_starts", "distinct_phrase_lengths",
                    "distinct_gaps", "quarter_beat_share", "weak16_share"):
            vals = sorted(r[key] for r in rows if r[key] is not None)
            if vals:
                payload.setdefault("summary", {})[key] = {
                    "n": len(vals), "min": vals[0],
                    "median": st.median(vals), "max": vals[-1],
                }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            print_track(row)
        if payload.get("summary"):
            print("\nSUMMARY (corpus, two-voice)")
            for key, band in payload["summary"].items():
                print(f"  {key:24s} n {band['n']:3d}  min {band['min']:.3f}  "
                      f"med {band['median']:.3f}  max {band['max']:.3f}")
        for e in errors:
            print(f"ERROR {e['file']}: {e['error']}", file=sys.stderr)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "rhythm.json"
        target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        print(f"\nwrote {target}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
