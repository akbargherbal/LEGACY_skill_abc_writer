#!/usr/bin/env python3
"""Measure the craft shape of a score: phrase variety, contour, cadence ladder.

The checker answers "is this a valid score of the declared shape?". This script
answers a different question: "is this a *tune*?" It puts numbers on the things
a listener hears first and the gate cannot see:

- **phrase rhythm variety** — distinct normalised rhythms per phrase. A score
  that sets every line to the same 2-2-1-2 pattern is a grid even when every
  duration is "varied".
- **contour** — descending share, phrases that start and end on the same pitch,
  and where the phrase peak sits. A phrase that always starts on its highest
  note is a sigh; 26 of them is a tic.
- **cadence ladder** — the scale degree each phrase ends on, relative to the
  tonic. The corpus does not end every phrase on the tonic.
- **literal repetition** — unique vocal bars / bars. A tune reuses *cells*;
  a loop reuses *bars*.
- **n-gram recurrence** — how much 4-note pitch and rhythm material returns
  inside the track. Recurrence is the hook; literal looping is the failure mode.
- **cadence length** — share of phrases whose last note is a quarter or longer.
  When it is 100%, every line is closed the same way.

Definitions follow `analysis/calibrate_177.py` and `analysis/measure_phrasing.py`
so the numbers are comparable with `references/reference.md` §7. Phrases split
at a section change or a rest of at least one beat.

Provenance: every distribution below is `corpus:n=177` on the `five_stars`
SheetSage2 transcripts (2026-11-24). They describe what those takes do. They are
**not gates** and not a definition of beauty; they are a mirror for a draft.

Usage:
    python3 analysis/measure_craft.py score.abc
    python3 analysis/measure_craft.py --corpus ~/.../five_stars --out analysis/out
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_177 as cal  # noqa: E402

METRICS = (
    "phrases", "phrase_notes_median", "step_share", "repeat_share",
    "leap4_share", "leap7_share", "descending_share", "same_start_end_share",
    "peak_late_share", "end_long_share", "rhythm_variety", "contour_variety",
    "shape_variety", "distinct_bar_share", "n4_recurrence", "r4_recurrence",
    "distinct_end_degrees",
)


def _phrases(notes: list[dict], bars: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    cur: list[dict] = []
    prev_end = None
    for note in notes:
        bi = cal.bar_index(bars, note["onset"])
        split = bool(cur) and (
            note["section"] != cur[-1]["section"]
            or (prev_end is not None
                and note["onset"] - prev_end >= bars[bi]["length"] / 4)
        )
        if cur and split:
            out.append(cur)
            cur = []
        cur.append(note)
        prev_end = note["onset"] + note["dur"]
    if cur:
        out.append(cur)
    return [p for p in out if len(p) >= 3]


def _contour(pitches: list[int]) -> str:
    return "".join(
        "U" if b > a else "D" if b < a else "S"
        for a, b in zip(pitches, pitches[1:])
    )


def _section_notes(notes: list[dict], label: str) -> list[dict]:
    return [n for n in notes if label in n["section"].lower()]


def measure_track(parsed: dict) -> dict:
    voice = parsed["voices"]["Vocal"]
    unit = parsed["unit"]
    tonic = cal.tonic_pc(parsed["key"])
    phrases = _phrases(voice.notes, voice.bars)
    if len(phrases) < 4:
        raise ValueError("fewer than 4 phrases")

    intervals: list[int] = []
    rhythms: set[tuple[float, ...]] = set()
    contours: set[str] = set()
    shapes: set[tuple[str, str, int]] = set()
    endings: list[int] = []
    end_long = 0
    peak_late = 0
    peak_first = 0
    same_start_end = 0
    descending = 0
    n4: Counter[tuple[int, ...]] = Counter()
    r4: Counter[tuple[int, ...]] = Counter()

    for phrase in phrases:
        pitches = [n["pitch"] for n in phrase]
        durations = [float(n["dur"] / unit) for n in phrase]
        intervals += [b - a for a, b in zip(pitches, pitches[1:])]

        total = sum(durations) or 1.0
        rhythms.add(tuple(round(d / total, 2) for d in durations))
        contour = _contour(pitches)
        contours.add(contour)
        changes = sum(1 for a, b in zip(contour, contour[1:]) if a != b)
        shapes.add((contour[:1], contour[-1:], min(changes, 4)))

        endings.append((pitches[-1] - tonic) % 12)
        if float(phrase[-1]["dur"]) >= 1.0:  # quarter note or longer
            end_long += 1
        position = pitches.index(max(pitches)) / max(1, len(pitches) - 1)
        peak_late += position >= 0.4
        peak_first += position == 0
        same_start_end += pitches[0] == pitches[-1]
        descending += pitches[-1] < pitches[0]

        for i in range(len(pitches) - 3):
            n4[tuple(pitches[i:i + 4])] += 1
            r4[tuple(int(d) for d in durations[i:i + 4])] += 1

    abs_intervals = [abs(i) for i in intervals]
    n = len(phrases)

    def recurrence(counter: Counter) -> float:
        total = sum(counter.values())
        return sum(c - 1 for c in counter.values() if c > 1) / total if total else 0.0

    bars: dict[int, list[int]] = defaultdict(list)
    for note in voice.notes:
        bars[note["bar"]].append(note["pitch"])
    cells = [tuple(p) for p in bars.values()]
    ending_counts = Counter(endings)

    def section(label: str) -> dict | None:
        notes = _section_notes(voice.notes, label)
        if len(notes) < 8:
            return None
        pitches = [n["pitch"] for n in notes]
        ivs = [b - a for a, b in zip(pitches, pitches[1:])]
        span = {n["bar"] for n in notes}
        return {
            "mean": st.mean(pitches),
            "notes_per_bar": len(notes) / max(1, len(span)),
            "repeat": sum(1 for i in ivs if i == 0) / max(1, len(ivs)),
            "leap": sum(1 for i in ivs if abs(i) >= 5) / max(1, len(ivs)),
        }

    verse, chorus = section("verse"), section("chorus")
    return {
        "bars": len(voice.bars),
        "vocal_notes": len(voice.notes),
        "phrases": n,
        "phrase_notes_median": st.median(len(p) for p in phrases),
        "step_share": sum(1 for i in abs_intervals if i <= 2) / len(abs_intervals),
        "repeat_share": sum(1 for i in abs_intervals if i == 0) / len(abs_intervals),
        "leap4_share": sum(1 for i in abs_intervals if i >= 5) / len(abs_intervals),
        "leap7_share": sum(1 for i in abs_intervals if i >= 7) / len(abs_intervals),
        "descending_share": descending / n,
        "same_start_end_share": same_start_end / n,
        "peak_late_share": peak_late / n,
        "peak_first_share": peak_first / n,
        "end_long_share": end_long / n,
        "rhythm_variety": len(rhythms) / n,
        "contour_variety": len(contours) / n,
        "shape_variety": len(shapes) / n,
        "distinct_bar_share": len(set(cells)) / max(1, len(cells)),
        "n4_recurrence": recurrence(n4),
        "r4_recurrence": recurrence(r4),
        "distinct_end_degrees": len(ending_counts),
        "end_degrees": dict(sorted(ending_counts.items())),
        "verse": verse,
        "chorus": chorus,
        "verse_chorus_mean": (chorus["mean"] - verse["mean"]) if verse and chorus else None,
        "verse_chorus_leap": (chorus["leap"] - verse["leap"]) if verse and chorus else None,
        "verse_chorus_repeat": (chorus["repeat"] - verse["repeat"]) if verse and chorus else None,
    }


def band(values: list[float]) -> dict:
    values = sorted(v for v in values if v is not None)
    if not values:
        return {"n": 0}

    def q(f: float) -> float:
        return values[min(len(values) - 1, int(round(f * (len(values) - 1))))]

    return {
        "n": len(values), "min": values[0], "p10": q(.10),
        "median": st.median(values), "p90": q(.90), "max": values[-1],
    }


def summarise(rows: list[dict]) -> dict:
    summary = {name: band([r[name] for r in rows]) for name in METRICS}
    pooled: Counter[int] = Counter()
    for row in rows:
        pooled.update(row["end_degrees"])
    total = sum(pooled.values()) or 1
    summary["end_degree_share"] = {
        degree: round(count / total, 3) for degree, count in sorted(pooled.items())
    }
    for key in ("verse_chorus_mean", "verse_chorus_leap", "verse_chorus_repeat"):
        summary[key] = band([r[key] for r in rows])
    return summary


def print_track(name: str, m: dict) -> None:
    print(f"\n{name}")
    print(f"  bars {m['bars']}  phrases {m['phrases']}  "
          f"notes/phrase {m['phrase_notes_median']:.1f}")
    print(f"  phrases: rhythm {m['rhythm_variety']:.2f}  contour "
          f"{m['contour_variety']:.2f}  shape {m['shape_variety']:.2f}")
    print(f"  intervals: step {m['step_share']:.3f}  repeat {m['repeat_share']:.3f}  "
          f"4th+ {m['leap4_share']:.3f}  5th+ {m['leap7_share']:.3f}")
    print(f"  contour: descending {m['descending_share']:.2f}  "
          f"same-start-end {m['same_start_end_share']:.2f}  "
          f"peak-late {m['peak_late_share']:.2f}  end-long {m['end_long_share']:.2f}")
    print(f"  repetition: unique bars {m['distinct_bar_share']:.2f}  "
          f"4-note pitch {m['n4_recurrence']:.2f}  rhythm {m['r4_recurrence']:.2f}")
    print(f"  endings ({m['distinct_end_degrees']}): {m['end_degrees']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scores", nargs="*", type=Path)
    ap.add_argument("--corpus", type=Path,
                    help="five_stars root (reads transcripts/*.abc)")
    ap.add_argument("--out", type=Path, help="write craft.json here")
    args = ap.parse_args()

    rows: list[dict] = []
    errors: list[dict] = []
    paths = list(args.scores)
    if args.corpus:
        paths += sorted((args.corpus / "transcripts").glob("*.abc"))
    if not paths:
        ap.error("give one or more score files, or --corpus")

    for path in paths:
        try:
            m = measure_track(cal.parse_score(path))
        except Exception as exc:  # noqa: BLE001
            errors.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})
            continue
        m["file"] = str(path)
        rows.append(m)
        print_track(path.name, m)

    payload = {"metric_basis": "corpus:n=177 (five_stars, 2026-11-24)",
               "definitions": __doc__.split("Usage:")[0].strip(),
               "rows": rows, "errors": errors}
    if args.corpus and rows:
        payload["summary"] = summarise(rows)
        print("\nSUMMARY (corpus)")
        for name in METRICS:
            b = payload["summary"][name]
            print(f"  {name:22s} n {b['n']:3d}  min {b['min']:.3f}  "
                  f"p10 {b['p10']:.3f}  med {b['median']:.3f}  "
                  f"p90 {b['p90']:.3f}  max {b['max']:.3f}")
        print("  end degrees:",
              payload["summary"]["end_degree_share"])
        for key in ("verse_chorus_mean", "verse_chorus_leap", "verse_chorus_repeat"):
            b = payload["summary"][key]
            print(f"  {key:22s} med {b['median']:+.3f}  "
                  f"p10 {b['p10']:+.3f}  p90 {b['p90']:+.3f}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "craft.json"
        target.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        print(f"\nwrote {target}")
    if errors:
        for e in errors:
            print(f"ERROR {e['file']}: {e['error']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
