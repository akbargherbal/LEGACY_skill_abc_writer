#!/usr/bin/env python3
"""Objective craft gate for a quality run.

`checker.py` is the score contract. `craft.py` is the report-only tune mirror.
This script is the middle layer: the objective, measurable craft targets a
quality run declares in `quality_targets.json`.

It does **not** judge taste. It checks only:

- longest unbroken vocal span (breath);
- rest hierarchy: the actual gap after each line vs the sidecar target, plus
  the share of identical gaps;
- the most common duration share;
- literal bar repetition;
- the share of vocal notes at/above C5.

Taste (cell identity, sayr, melisma, dialogue, ostinato, arc) belongs to the
critic, not here. See `references/critic.md`.

Usage:
    python3 quality.py score.abc --plan plan.json --phrases phrases.json \
        --targets quality_targets.json --json quality.json
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _craft_calibrate as cal  # noqa: E402
import _craft_measure as cm  # noqa: E402
import checker  # noqa: E402
import copies  # noqa: E402
import phrase_table  # noqa: E402

DEFAULT_TARGETS = {
    "unbroken_seconds_max": 10.0,
    "top_duration_share_max": 0.60,
    "distinct_bar_share_min": 0.75,
    "tessitura_share_ge_c5_max": 0.60,
    "pause": {
        "min_s": 0.50,
        "section_end_min_s": 1.00,
        "max_identical_share": 0.40,
        "min_distinct_values": 2,
    },
}


def _load(path: Path | None) -> dict:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _merged(targets: dict, plan: dict) -> dict:
    out = json.loads(json.dumps(DEFAULT_TARGETS))
    if plan.get("max_unbroken_seconds") is not None:
        out["unbroken_seconds_max"] = float(plan["max_unbroken_seconds"])
    if plan.get("max_top_duration_share") is not None:
        out["top_duration_share_max"] = min(
            float(plan["max_top_duration_share"]), out["top_duration_share_max"])
    for key in ("unbroken_seconds_max", "top_duration_share_max",
                "distinct_bar_share_min", "tessitura_share_ge_c5_max"):
        if targets.get(key) is not None:
            out[key] = targets[key]
    pause = dict(out["pause"])
    pause.update(targets.get("pause") or {})
    out["pause"] = pause
    return out


def check(score_path: Path, plan_path: Path, phrases_path: Path | None,
          targets_path: Path | None) -> dict:
    plan = _load(plan_path)
    targets = _merged(_load(targets_path), plan)
    text = score_path.read_text(encoding="utf-8")
    score = checker.parse(text)
    parsed = cal.parse_score(score_path)
    shape = checker._phrasing(score)
    craft = cm.measure_track(parsed)
    cal_measure = cal.measure(parsed)

    checks: list[dict] = []

    def add(name: str, actual, target, ok: bool, detail: str, bars=None) -> None:
        checks.append({"name": name, "actual": actual, "target": target,
                       "ok": bool(ok), "detail": detail,
                       "bars": bars or []})

    unbroken = shape.get("unbroken_seconds_max")
    t = float(targets["unbroken_seconds_max"])
    add("unbroken", unbroken, t, unbroken is not None and unbroken <= t + 1e-9,
        f"{unbroken}s vs max {t:g}s")

    top = cal_measure.get("top_duration_share")
    t = float(targets["top_duration_share_max"])
    add("top_duration_share", top, t, top is not None and top <= t + 1e-9,
        f"{top:.0%} vs max {t:.0%}")

    copy_bars_1based = copies.declared_copy_bars(plan, max_bars=score.n_bars)
    copy_bars_0based = {b - 1 for b in copy_bars_1based}
    if copy_bars_0based:
        from collections import defaultdict
        vocal_bars_map: dict[int, list[int]] = defaultdict(list)
        for note in parsed["voices"]["Vocal"].notes:
            if note["bar"] not in copy_bars_0based:
                vocal_bars_map[note["bar"]].append(note["pitch"])
        if vocal_bars_map:
            cells = [tuple(p) for p in vocal_bars_map.values()]
            distinct = len(set(cells)) / len(cells)
        else:
            distinct = craft.get("distinct_bar_share")
    else:
        distinct = craft.get("distinct_bar_share")
    t = float(targets["distinct_bar_share_min"])
    excl_note = f" (excluding {len(copy_bars_0based)} copy bar(s))" if copy_bars_0based else ""
    add("distinct_bar_share", distinct, t, distinct is not None and distinct >= t - 1e-9,
        f"{distinct:.0%} unique vs min {t:.0%}{excl_note}")

    tess = shape.get("tessitura_share_ge_c5")
    t = float(targets["tessitura_share_ge_c5_max"])
    add("tessitura_share_ge_c5", tess, t, tess is not None and tess <= t + 1e-9,
        f"{tess:.0%} at/above C5 vs max {t:.0%}")

    # Rest hierarchy: actual gap vs the sidecar target, plus variation.
    if phrases_path:
        phrases = _load(phrases_path)
        table = phrase_table.build(parsed, phrases)
        gaps = []
        pause_violations = []
        for i, row in enumerate(table["rows"]):
            gap = row.get("rest_after_s")
            if gap is None or not row.get("notes"):
                continue
            gaps.append(gap)
            target_pause = row.get("pause_after_s")
            if target_pause is None:
                target_pause = 1.0 if i + 1 < len(table["rows"]) and \
                    table["rows"][i + 1].get("section") != row.get("section") else \
                    float(targets["pause"]["min_s"])
            if gap + 1e-6 < float(target_pause):
                pause_violations.append(
                    f"line {row.get('line')}: {gap:.2f}s < {float(target_pause):.2f}s")
        counts = Counter(round(g, 2) for g in gaps)
        max_share = (max(counts.values()) / len(gaps)) if gaps else 0.0
        distinct_gaps = len(counts)
        ptarget = targets["pause"]
        ok = (not pause_violations
              and max_share <= float(ptarget["max_identical_share"]) + 1e-9
              and distinct_gaps >= int(ptarget["min_distinct_values"]))
        add("pause hierarchy", {"max_identical_share": round(max_share, 3),
                                "distinct": distinct_gaps,
                                "violations": pause_violations},
            ptarget, ok,
            f"{len(pause_violations)} short gap(s); max identical {max_share:.0%}; "
            f"{distinct_gaps} distinct value(s)",
            [v.split(":")[0].replace("line ", "") for v in pause_violations])
    else:
        add("pause hierarchy", None, targets["pause"], False,
            "no phrases.json; cannot verify the per-line rest hierarchy")

    return {"ok": all(c["ok"] for c in checks), "checks": checks,
            "targets": targets,
            "measured": {"unbroken_seconds_max": unbroken,
                         "top_duration_share": top,
                         "distinct_bar_share": distinct,
                         "tessitura_share_ge_c5": tess,
                         "phrases": craft.get("phrases")}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--phrases", type=Path)
    ap.add_argument("--targets", type=Path)
    ap.add_argument("--json", type=Path, default=Path("quality.json"))
    args = ap.parse_args(argv)
    try:
        payload = check(args.score, args.plan, args.phrases, args.targets)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {args.score}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    for c in payload["checks"]:
        print(f"{'PASS' if c['ok'] else 'FAIL':4s} {c['name']:24s} {c['detail']}")
    print(f"\n{'PASS' if payload['ok'] else 'FAIL'}  objective quality; wrote {args.json}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
