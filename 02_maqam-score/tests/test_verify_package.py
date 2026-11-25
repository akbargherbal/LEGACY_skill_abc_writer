#!/usr/bin/env python3
"""Tests for verify_package.py: the package around the score.

Run:
    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import checker  # noqa: E402
import verify_package as vp  # noqa: E402

EXAMPLE = SKILL / "example" / "score.abc"
PLAN = SKILL / "example" / "plan.json"

SCORE = """X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
V: Vocal
Z16|
V: Ins
Z16|
"""

CORE = """X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
V: Vocal
Z8|
V: Ins
Z8|
"""

SEED = """X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
V: Drums clef=perc name="Drums" snm="Drums"
%%MIDI channel 10
K:Dm
V: Vocal
Z16|
V: Ins
Z16|
V: Drums
B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 C2 D2|
Z6|
"""

TEN = "\n".join(f"{i}. line {i}" for i in range(1, 11)) + "\n"
PLAN_16 = {"bars": 16, "strict_shape": False,
           "register": {"mean": 70, "top": 80, "max_top": 84, "tolerance": 3}}
REPORT_16 = {"ok": True, "measured": {"bars": 16}}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "score.abc").write_text(SCORE, encoding="utf-8")
        (self.dir / "core.abc").write_text(CORE, encoding="utf-8")
        (self.dir / "seed.abc").write_text(SEED, encoding="utf-8")
        (self.dir / "plan.json").write_text(json.dumps(PLAN_16), encoding="utf-8")
        (self.dir / "sheet.md").write_text(TEN, encoding="utf-8")
        (self.dir / "notes.md").write_text(TEN, encoding="utf-8")
        (self.dir / "report.json").write_text(json.dumps(REPORT_16), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_vp(self):
        out = self.dir / "verify.json"
        code = vp.main([
            "--score", str(self.dir / "score.abc"),
            "--seed", str(self.dir / "seed.abc"),
            "--plan", str(self.dir / "plan.json"),
            "--core", str(self.dir / "core.abc"),
            "--sheet", str(self.dir / "sheet.md"),
            "--notes", str(self.dir / "notes.md"),
            "--report", str(self.dir / "report.json"),
            "--json", str(out),
        ])
        return code, json.loads(out.read_text(encoding="utf-8"))

    def test_full_package_passes(self):
        code, payload = self.run_vp()
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["drums_under_vocal"], 0)

    def test_seed_alignment_fails(self):
        (self.dir / "seed.abc").write_text(
            SEED.replace("V: Vocal\nZ16|", "V: Vocal\nD2|Z15|", 1),
            encoding="utf-8")
        code, payload = self.run_vp()
        self.assertEqual(code, 1)
        self.assertTrue(any(c["tag"] == "FAIL" and c["name"] == "seed Vocal"
                            for c in payload["checks"]))

    def test_strict_shape_true_fails(self):
        plan = dict(PLAN_16)
        plan["strict_shape"] = True
        (self.dir / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        code, payload = self.run_vp()
        self.assertEqual(code, 1)
        self.assertTrue(any(c["tag"] == "FAIL" and c["name"] == "strict_shape"
                            for c in payload["checks"]))

    def test_docs_must_be_ten_numbered_lines(self):
        (self.dir / "notes.md").write_text("\n".join(
            f"{i}. line {i}" for i in range(1, 10)) + "\n", encoding="utf-8")
        code, payload = self.run_vp()
        self.assertEqual(code, 1)
        self.assertTrue(any(c["tag"] == "FAIL" and c["name"] == "notes.md"
                            for c in payload["checks"]))


class UnitTests(unittest.TestCase):
    def test_bar_units_tie_and_rests(self):
        self.assertEqual(vp.bar_units("d2-d2 z4 f2"), 10)
        self.assertEqual(vp.bar_units("z2z4"), 6)
        self.assertIsNone(vp.bar_units("Z"))

    def test_bar_units_full_bar(self):
        self.assertEqual(vp.bar_units("d3 d1 c2 d2 _e2 d2 d2 c2"), 16)

    def test_numbered_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ok.md"
            p.write_text(TEN, encoding="utf-8")
            self.assertEqual(len(vp.numbered_lines(p)), 10)
            p.write_text(TEN.replace("10. line 10\n", ""), encoding="utf-8")
            with self.assertRaises(ValueError):
                vp.numbered_lines(p)
            p.write_text(TEN.replace("3. line 3", "3) line 3"), encoding="utf-8")
            with self.assertRaises(ValueError):
                vp.numbered_lines(p)


class ExampleTests(unittest.TestCase):
    def test_example_score_and_plan_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "verify.json"
            code = vp.main(["--score", str(EXAMPLE), "--plan", str(PLAN),
                            "--json", str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])

    def test_legacy_plan_waivers_do_not_fail_package(self):
        """A legacy plan warns in checker and passes verify_package via waivers."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan = json.loads(PLAN.read_text(encoding="utf-8"))
            for key in ("plan_version", "copies", "arrangement"):
                plan.pop(key, None)
            legacy_plan = tmp_path / "legacy_plan.json"
            legacy_plan.write_text(json.dumps(plan), encoding="utf-8")
            lyrics = (SKILL / "example" / "lyrics.txt").read_text(encoding="utf-8")
            results, measured = checker.check(
                checker.parse(EXAMPLE.read_text(encoding="utf-8")),
                plan, lyrics_text=lyrics,
                calibration=checker.load_calibration(),
            )
            self.assertFalse([r for r in results if r[0] == "FAIL"], results)
            self.assertFalse(measured["copies_checked"])
            self.assertFalse(measured["binding_checked"])
            report = {
                "ok": True,
                "waivers": measured["waivers"],
                "prosody_checked": measured["prosody_checked"],
                "copies_checked": measured["copies_checked"],
                "binding_checked": measured["binding_checked"],
                "measured": measured,
            }
            report_path = tmp_path / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            out = tmp_path / "verify.json"
            code = vp.main([
                "--score", str(EXAMPLE),
                "--plan", str(legacy_plan),
                "--report", str(report_path),
                "--json", str(out),
            ])
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, payload)
        self.assertTrue(any(c["name"] == "copies_checked" and c["tag"] == "WARN"
                            for c in payload["checks"]), payload["checks"])
        self.assertTrue(any(c["name"] == "binding_checked" and c["tag"] == "WARN"
                            for c in payload["checks"]), payload["checks"])

    def test_bad_bar_sum_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken.abc"
            broken.write_text(EXAMPLE.read_text(encoding="utf-8").replace(
                "F2 F2 A8 G2 F2|", "F2 F2 A8 G2|"), encoding="utf-8")
            out = Path(tmp) / "verify.json"
            code = vp.main(["--score", str(broken), "--plan", str(PLAN),
                            "--json", str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertTrue(any(c["tag"] == "FAIL" and c["name"] == "bar sums"
                            for c in payload["checks"]))


if __name__ == "__main__":
    unittest.main()
