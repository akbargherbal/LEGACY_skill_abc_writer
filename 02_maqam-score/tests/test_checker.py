#!/usr/bin/env python3
"""Regression tests for the calibrated checker.

Run:
    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import checker  # noqa: E402

EXAMPLE = SKILL / "example" / "score.abc"
PLAN = SKILL / "example" / "plan.json"

MULTI_METER = """X:1
T:
M:4/4
L:1/16
Q:1/4=73
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
% intro
V: Vocal
M:1/4
D4|
V: Ins
M:1/4
Z|
% verse
V: Vocal
M:4/4
Z|
V: Ins
M:4/4
Z|
"""


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.cal = checker.load_calibration()

    def test_example_passes(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        results, measured = checker.check(score, plan, calibration=self.cal)
        self.assertFalse([r for r in results if r[0] == "FAIL"], results)
        self.assertEqual(measured["bars"], 16)
        self.assertEqual(measured["syllables"], 16)

    def test_multi_meter_parses(self):
        score = checker.parse(MULTI_METER)
        self.assertEqual(score.n_bars, 2)
        self.assertEqual(score.bar_units, [4, 16])
        self.assertEqual(score.bar_meters, [(1, 4), (4, 4)])

    def test_style_warning_does_not_fail_by_default(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan["min_fill_notes"] = 99  # impossible style target
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertFalse([r for r in results if r[0] == "FAIL"], results)
        self.assertTrue([r for r in results if r[0] == "WARN"
                         and r[1] == "answer fill length"], results)

    def test_style_target_fails_with_strict_style(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan["min_fill_notes"] = 99
        results, _ = checker.check(score, plan, calibration=self.cal, strict_style=True)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "answer fill length"], results)

    def test_final_rest_is_optional(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        # remove the final rest in the Ins voice (the last |Z| in the file)
        text = EXAMPLE.read_text(encoding="utf-8")
        pos = text.rfind("|Z|")
        text = text[:pos] + "|D,16|" + text[pos + 3:]
        score = checker.parse(text)
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertFalse([r for r in results if r[0] == "FAIL"
                          and r[1] == "final rest"], results)
        results, _ = checker.check(score, plan, calibration=self.cal,
                                   require_final_rest=True)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "final rest"], results)

    def test_sanity_set_passes_the_example(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        results, _ = checker.check(score, plan, calibration=self.cal)
        sanity = [r for r in results if r[4] == "sanity"]
        self.assertEqual(len(sanity), 6)
        self.assertFalse([r for r in sanity if r[0] == "FAIL"], sanity)


if __name__ == "__main__":
    unittest.main()
