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
PHRASES = SKILL / "example" / "phrases.json"

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

    def test_example_passes_strict_shape_and_style(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
        results, measured = checker.check(
            score, plan, strict_style=True, strict_shape=True,
            phrase_plan=phrases, require_final_rest=True, calibration=self.cal)
        self.assertFalse([r for r in results if r[0] in ("FAIL", "WARN")], results)
        self.assertTrue(measured["phrases_checked"])

    def test_strict_shape_is_backward_compatible(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan["max_unbroken_seconds"] = 0.1
        plan.pop("strict_shape", None)
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "WARN"
                         and r[1] == "unbroken target"], results)
        plan["strict_shape"] = True
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "unbroken target"], results)

    def test_strict_shape_fails_a_long_phrase(self):
        score = checker.parse(ONE_BREATH_SCALE)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan.update({
            "bars": 16, "tempo": 74, "sections": ["verse"], "syllables": 120,
            "max_unbroken_seconds": 10, "min_phrase_endings": 3,
            "strict_shape": True,
        })
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "unbroken target"], results)

    def test_tessitura_and_register_ceilings(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan["strict_shape"] = True
        plan["tessitura_share_ge_c5_max"] = 0.2
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "tessitura share"], results)
        plan["tessitura_share_ge_c5_max"] = 0.8
        plan["register"]["max_top"] = 80
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "register max top"], results)

    def test_chorus_median_lift(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan["strict_shape"] = True
        plan["chorus_lift_min"] = 20
        results, _ = checker.check(score, plan, calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "chorus lift median"], results)

    def test_phrase_plan_checks_the_line_end_pause(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
        results, _ = checker.check(
            score, plan, strict_shape=True, phrase_plan=phrases,
            calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "PASS"
                         and r[1] == "phrase plan"], results)
        phrases["lines"][0]["pause_after_s"] = 99
        results, _ = checker.check(
            score, plan, strict_shape=True, phrase_plan=phrases,
            calibration=self.cal)
        self.assertTrue([r for r in results if r[0] == "FAIL"
                         and r[1] == "phrase plan"], results)

    def test_sanity_set_passes_the_example(self):
        score = checker.parse(EXAMPLE.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        results, _ = checker.check(score, plan, calibration=self.cal)
        sanity = [r for r in results if r[4] == "sanity"]
        self.assertGreaterEqual(len(sanity), 6)
        self.assertFalse([r for r in sanity if r[0] == "FAIL"], sanity)

    def test_shape_guards_reject_a_one_breath_scale(self):
        """A continuous scale with one phrase ending is a degeneracy, not taste.

        The 2026-11-23 Claude run was 34 s unbroken, 6% repeated and 2 endings;
        the corpus is 5.5-22.9 s, 25-43% and 4-8. These three guards make that
        run fail without touching the six validity guards.
        """
        score = checker.parse(ONE_BREATH_SCALE)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        plan.update({
            "bars": 16, "tempo": 74, "sections": ["verse"], "syllables": 120,
            "max_unbroken_seconds": 10, "min_phrase_endings": 3,
            "max_top_duration_share": 0.95, "min_distinct_durations": 4,
            "ties_min": 0, "melisma_min": 1.0, "melisma_max": 1.55,
            "register": {"mean": 70, "top": 74, "tolerance": 5},
            "deviations": [
                {"bars": "1-4", "channel": "gap rate", "before": "a", "after": "b"},
                {"bars": "5-8", "channel": "density", "before": "a", "after": "b"},
                {"bars": "9-12", "channel": "section register", "before": "a", "after": "b"},
            ],
        })
        results, measured = checker.check(score, plan, calibration=self.cal)
        failed = {name for tag, name, _ok, _detail, _cls in results if tag == "FAIL"}
        self.assertIn("unbroken singing", failed)
        self.assertIn("repeated notes", failed)
        self.assertIn("phrase endings", failed)
        self.assertGreater(measured["unbroken_seconds_max"], 23)
        self.assertLess(measured["repeated_share"], 0.20)
        self.assertLess(measured["distinct_phrase_endings"], 3)

    def test_maqam_measures_against_declared_degrees(self):
        """A defining flat must be measured against the maqam, not the key."""
        import re
        lines = []
        for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
            if not line.startswith(("X:", "T:", "M:", "L:", "Q:", "V:", "K:", "%")):
                # Am has F natural; Kurd has Eb. Re-spell F/f as Eb/eb so the
                # same note is chromatic against the key but inside the maqam.
                line = re.sub(
                    r"(?<![_^=])([EeFf])(?=[0-9,])",
                    lambda m: "_E" if m.group(1).isupper() else "_e",
                    line,
                )
            lines.append(line)
        score = checker.parse("\n".join(lines) + "\n")
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        key_chromatic = checker.check(score, plan, calibration=self.cal)[1]["chromatic_per_100"]
        self.assertGreater(key_chromatic, 0)

        plan["maqam"] = {
            "name": "kurd", "tonic": "D",
            "degrees": ["D", "Eb", "F", "G", "A", "Bb", "C"],
            "resting": ["D", "F", "A", "Bb", "C"],
        }
        _results, measured = checker.check(score, plan, calibration=self.cal)
        self.assertEqual(measured["chromatic_basis"], "maqam:kurd")
        self.assertEqual(measured["chromatic_per_100"], 0.0)
        self.assertEqual(measured["maqam_fit_share"], 1.0)


ONE_BREATH_SCALE = """X:1
T:
M:4/4
L:1/16
Q:1/4=74
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
% verse
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
z8z6 D2|Z|
% chorus
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
% verse
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
% chorus
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
% verse
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
% chorus
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
% verse
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
% chorus
V: Vocal
D2 E2 F2 G2 A2 B2 c2 d2|c2 B2 A2 G2 F2 E2 D4|
V: Ins
Z|Z|
"""


if __name__ == "__main__":
    unittest.main()
