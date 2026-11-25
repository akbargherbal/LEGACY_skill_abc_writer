#!/usr/bin/env python3
"""Turn a global checker failure into a bar/phrase repair map.

`checker.py` names a metric (register_mean, repeated_share, simultaneity,
distinct bars, top duration, unbroken singing, phrase plan). A metric is not a
repair instruction. This script reads the same score and the checker report and
lists the bars/phrases responsible, so the composer can use `edit` instead of
rewriting the whole score.

It is a report, not a gate: it exits 0 when it can build the map. The checker
still decides PASS/FAIL.

Usage:
    python3 repair.py score.abc --report report.json --plan plan.json \
        --phrases phrases.json --json repair.json
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _craft_calibrate as cal  # noqa: E402
import _craft_measure as cm  # noqa: E402
import checker  # noqa: E402
import copies  # noqa: E402
import phrase_table  # noqa: E402

PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _load(path: Path | None) -> dict:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _bar_key(note_list: list) -> tuple:
    return (tuple(n.pitch for n in note_list), tuple(n.dur for n in note_list))


def _maps(score, parsed, plan: dict, phrases: dict | None) -> dict:
    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    ins = sorted(score.notes_of("Ins"), key=lambda n: n.onset)
    unit_seconds = 4.0 / score.unit_den * 60.0 / score.tempo
    by_bar: dict[int, list] = defaultdict(list)
    for n in vocal:
        by_bar[n.bar + 1].append(n)

    # Register: section means and bars outside the plan's band.
    reg = plan.get("register") or {}
    target = reg.get("mean")
    tol = float(reg.get("tolerance", 3) or 3)
    sections: dict[str, list[int]] = defaultdict(list)
    for n in vocal:
        sections[n.section].append(n.pitch)
    section_mean = {k: round(st.mean(v), 1) for k, v in sections.items() if v}
    section_bars: dict[str, list[int]] = defaultdict(list)
    for n in vocal:
        if n.bar + 1 not in section_bars[n.section]:
            section_bars[n.section].append(n.bar + 1)
    register_out = []
    for sec, mean in section_mean.items():
        if target is not None and abs(mean - float(target)) > tol:
            register_out.append({"section": sec, "mean": mean,
                                 "bars": f"{min(section_bars[sec])}-{max(section_bars[sec])}"})
    bar_mean = {bar: round(st.mean(n.pitch for n in notes), 1)
                for bar, notes in by_bar.items()}
    bar_out = [bar for bar, mean in bar_mean.items()
               if target is not None and abs(mean - float(target)) > tol]

    # Simultaneity: bars where Vocal and Ins overlap.
    overlap_bars: dict[int, float] = defaultdict(float)
    for a in vocal:
        a0, a1 = a.onset, a.onset + a.dur
        for b in ins:
            b0, b1 = b.onset, b.onset + b.dur
            s, e = max(a0, b0), min(a1, b1)
            if e > s:
                overlap_bars[a.bar + 1] += e - s
    overlap_bars = {bar: round(float(v), 2) for bar, v in overlap_bars.items()}

    # Repeated pitch: bar-level share.
    repeated_bars = []
    for bar, notes in sorted(by_bar.items()):
        notes = sorted(notes, key=lambda n: n.onset)
        ivs = [b.pitch - a.pitch for a, b in zip(notes, notes[1:])]
        if len(ivs) >= 3:
            share = sum(1 for i in ivs if i == 0) / len(ivs)
            if share >= 0.5:
                repeated_bars.append({"bar": bar, "share": round(share, 2)})

    # Literal bar repetition: duplicate (pitch, duration) tuples (excluding declared copy bars).
    copy_bars_1based = copies.declared_copy_bars(plan, max_bars=score.n_bars)
    keys: dict[tuple, list[int]] = defaultdict(list)
    for bar, notes in by_bar.items():
        if bar in copy_bars_1based:
            continue
        keys[_bar_key(sorted(notes, key=lambda n: n.onset))].append(bar)
    duplicate_bars = [{"bars": sorted(v), "count": len(v)}
                      for v in keys.values() if len(v) > 1]

    # Top duration: bars containing the most common duration.
    dur_counts = Counter(float(n.dur) for n in vocal)
    top_dur = max(dur_counts, key=dur_counts.get) if dur_counts else None
    top_bars = []
    if top_dur is not None:
        for bar, notes in sorted(by_bar.items()):
            if any(float(n.dur) == top_dur for n in notes):
                top_bars.append(bar)

    # Unbroken runs: the longest span with no rest.
    runs = []
    cur = []
    prev_end = None
    for n in vocal:
        if cur and prev_end is not None and n.onset > prev_end:
            runs.append(cur)
            cur = []
        cur.append(n)
        prev_end = n.onset + n.dur
    if cur:
        runs.append(cur)
    run_rows = []
    for run in runs:
        start = run[0].onset
        end = run[-1].onset + run[-1].dur
        run_rows.append({"start_bar": run[0].bar + 1, "end_bar": run[-1].bar + 1,
                         "seconds": round((end - start) * unit_seconds, 2),
                         "notes": len(run)})
    longest = max(run_rows, key=lambda r: r["seconds"]) if run_rows else None

    # Tessitura: bars with notes at/above C5 (MIDI 72).
    tess_bars = [bar for bar, notes in sorted(by_bar.items())
                 if any(n.pitch >= 72 for n in notes)]

    # Phrase rest hierarchy.
    pause_rows = []
    if phrases:
        table = phrase_table.build(parsed, phrases)
        for i, row in enumerate(table["rows"]):
            gap = row.get("rest_after_s")
            if gap is None or not row.get("notes"):
                continue
            target_pause = row.get("pause_after_s")
            if target_pause is None:
                target_pause = 1.0 if i + 1 < len(table["rows"]) and \
                    table["rows"][i + 1].get("section") != row.get("section") else 0.5
            if gap + 1e-6 < float(target_pause):
                pause_rows.append({"line": row.get("line"), "bars": row.get("bars"),
                                   "actual_s": gap, "target_s": float(target_pause)})

    try:
        phrase_count = cm.measure_track(parsed).get("phrases")
    except Exception:  # short fixture; the phrase count is diagnostic only
        phrase_count = None
    return {
        "register": {"target": target, "tolerance": tol,
                      "sections": section_mean, "sections_out": register_out,
                      "bars_out": bar_out},
        "simultaneity": {"bars": overlap_bars,
                          "total_units": round(sum(overlap_bars.values()), 2)},
        "repeated": {"bars": repeated_bars},
        "distinct_bars": {"duplicates": duplicate_bars},
        "top_duration": {"duration_quarters": top_dur,
                          "share": round(dur_counts[top_dur] / len(vocal), 3) if vocal and top_dur else None,
                          "bars": top_bars},
        "unbroken": {"longest": longest, "runs": run_rows},
        "tessitura": {"bars": tess_bars},
        "pause": {"lines": pause_rows},
        "phrases": phrase_count,
    }


def _failures(report: dict, maps: dict) -> list[dict]:
    out = []
    for check in report.get("checks") or []:
        tag = check.get("tag") or check.get("status")
        name = str(check.get("name", ""))
        if tag not in ("FAIL", "WARN") and check.get("ok") is not False:
            continue
        low = name.lower()
        entry = {"check": name, "tag": tag, "detail": check.get("detail", "")}
        if "register" in low:
            entry.update(maps["register"])
        elif "simult" in low:
            entry.update(maps["simultaneity"])
        elif "repeated" in low:
            entry.update(maps["repeated"])
        elif "distinct" in low:
            entry.update(maps["distinct_bars"])
        elif "duration" in low or "top_duration" in low:
            entry.update(maps["top_duration"])
        elif "unbroken" in low:
            entry.update(maps["unbroken"])
        elif "tessitura" in low:
            entry.update(maps["tessitura"])
        elif "phrase plan" in low:
            entry.update(maps["pause"])
        out.append(entry)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--plan", type=Path)
    ap.add_argument("--phrases", type=Path)
    ap.add_argument("--json", type=Path, default=Path("repair.json"))
    args = ap.parse_args(argv)
    try:
        text = args.score.read_text(encoding="utf-8")
        score = checker.parse(text)
        parsed = cal.parse_score(args.score)
        plan = _load(args.plan)
        report = _load(args.report)
        phrases = _load(args.phrases) if args.phrases else None
        maps = _maps(score, parsed, plan, phrases)
        payload = {"ok": True, "score": str(args.score),
                   "failures": _failures(report, maps), "maps": maps}
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "score": str(args.score),
                   "error": f"{type(exc).__name__}: {exc}"}
    args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    if not payload["ok"]:
        print(f"ERROR: {payload['error']}", file=sys.stderr)
        return 2
    if payload["failures"]:
        for f in payload["failures"]:
            print(f"FAIL {f['check']}: {f.get('detail','')}")
            if f.get("bars_out") is not None:
                print(f"  register bars: {f['bars_out'][:20]}")
            if f.get("bars") is not None and isinstance(f.get("bars"), dict):
                print(f"  bars: {list(f['bars'])[:20]}")
            if f.get("longest"):
                print(f"  longest run: {f['longest']}")
            if f.get("lines"):
                print(f"  short pauses: {f['lines'][:8]}")
    else:
        print("No FAIL/WARN rows in the report; a full diagnostic map is in repair.json")
    print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
