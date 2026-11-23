#!/usr/bin/env python3
"""Run the calibrated checker over the 177-track corpus.

This is the integration test for M2: the checker must parse all 177 files
(including inline M: changes), and the six sanity gates must pass >=95%.

Usage:
    python3 analysis/test_checker_corpus.py \
        --corpus ~/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_maqam-score" / "scripts"))
import checker  # noqa: E402

VOWEL_MARKS = "\u064e\u064f\u0650\u064b\u064c\u064d\u0670"


def syllables(text: str) -> int:
    return sum(1 for c in text if c in VOWEL_MARKS)


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def plan_for(score: checker.Score, syl: int) -> dict:
    sections = [s for i, s in enumerate(score.bar_sections)
                if i == 0 or s != score.bar_sections[i - 1]]
    return {
        "key": score.key,
        "tempo": score.tempo,
        "meter": f"{score.meter[0]}/{score.meter[1]}",
        "unit": f"1/{score.unit_den}",
        "bars": score.n_bars,
        "syllables": syl,
        "sections": sections,
        "simultaneity_exception": None,
        "cadence": "any",
        "melisma_min": 1.10,
        "melisma_max": 1.45,
        "register": {"mean": 74, "top": 82, "tolerance": 5},
        "max_top_duration_share": 0.85,
        "min_distinct_durations": 4,
        "ties_min": 1,
        "min_fill_notes": 3,
        "ins_active_share_min": 0.05,
        "chords_min": 0,
        "deviations": [{"bars": "1-2", "channel": "x", "before": "a", "after": "b"}] * 3,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=pathlib.Path, required=True)
    args = ap.parse_args()

    root = args.corpus
    lyrics = {r["track_id"]: r for r in load_jsonl(root / "lyrics.jsonl")}
    cal = checker.load_calibration()
    hard_fail = collections.Counter()
    style_warn = collections.Counter()
    hard_fail_with_rest = collections.Counter()
    passed = passed_with_rest = 0
    n = 0
    parse_errors = []

    for path in sorted((root / "transcripts").glob("*.abc")):
        tid = path.stem
        try:
            score = checker.parse(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            parse_errors.append((tid, f"{type(exc).__name__}: {exc}"))
            continue
        syl = sum(syllables(l) for s in (lyrics.get(tid, {}).get("sections") or [])
                  for l in (s.get("lines") or []))
        plan = plan_for(score, syl)
        results, _ = checker.check(score, plan, calibration=cal)
        fails = [r for r in results if r[0] == "FAIL"]
        warns = [r for r in results if r[0] == "WARN"]
        n += 1
        if not fails:
            passed += 1
        for r in fails:
            hard_fail[(r[4], r[1])] += 1
        for r in warns:
            style_warn[(r[4], r[1])] += 1
        results_rest, _ = checker.check(score, plan, calibration=cal,
                                        require_final_rest=True)
        fails_rest = [r for r in results_rest if r[0] == "FAIL"]
        if not fails_rest:
            passed_with_rest += 1
        for r in fails_rest:
            hard_fail_with_rest[(r[4], r[1])] += 1

    print(f"parsed {n}/177; parse errors {len(parse_errors)}")
    for e in parse_errors[:10]:
        print("  ", e)
    print(f"hard gates (default, final rest warns): {passed}/{n} = {passed/n:.1%}")
    print(f"hard gates (+ --require-final-rest):    {passed_with_rest}/{n} = {passed_with_rest/n:.1%}")
    print("default hard failures:", dict(hard_fail))
    print("with final-rest contract failures:", dict(hard_fail_with_rest))
    print("top style warnings:", style_warn.most_common(12))
    return 0 if n == 177 and passed / n >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
