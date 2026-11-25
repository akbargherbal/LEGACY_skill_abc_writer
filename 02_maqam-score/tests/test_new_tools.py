#!/usr/bin/env python3
"""Tests for the 0.7.0 tools: phrase table, quality, repair, doctor, state."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import abc_doctor  # noqa: E402
import craft  # noqa: E402
import phrase_table  # noqa: E402
import quality  # noqa: E402
import repair  # noqa: E402
import verify_package as vp  # noqa: E402
import _craft_calibrate as cal  # noqa: E402

EXAMPLE = SKILL / "example" / "score.abc"
PLAN = SKILL / "example" / "plan.json"
PHRASES = SKILL / "example" / "phrases.json"


class PhraseTableTests(unittest.TestCase):
    def test_example_lines(self):
        parsed = cal.parse_score(EXAMPLE)
        payload = json.loads(PHRASES.read_text(encoding="utf-8"))
        table = phrase_table.build(parsed, payload)
        self.assertEqual(table["summary"]["lyric_lines"], 4)
        self.assertGreater(table["summary"]["detected_phrases"], 0)
        self.assertTrue(any(r.get("notes", 0) > 0 for r in table["rows"]))
        row = next(r for r in table["rows"] if r.get("notes"))
        for key in ("bars", "rhythm_cell", "rest_after_s", "unbroken_s",
                    "register_mean", "repeated", "leaps", "end_name"):
            self.assertIn(key, row)


class QualityTests(unittest.TestCase):
    def test_checks_exist(self):
        payload = quality.check(EXAMPLE, PLAN, PHRASES, None)
        names = {c["name"] for c in payload["checks"]}
        self.assertEqual(names, {"unbroken", "top_duration_share",
                                 "distinct_bar_share", "tessitura_share_ge_c5",
                                 "pause hierarchy"})
        self.assertIsInstance(payload["ok"], bool)


class RepairTests(unittest.TestCase):
    def test_map_without_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "repair.json"
            code = repair.main([str(EXAMPLE), "--plan", str(PLAN),
                                "--phrases", str(PHRASES), "--json", str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertIn("maps", payload)
        self.assertIn("register", payload["maps"])


class DoctorTests(unittest.TestCase):
    def test_good_score(self):
        payload = abc_doctor.diagnose(EXAMPLE)
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["bars"], 0)

    def test_bad_block(self):
        text = """X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
V: Vocal
D4 E4 F4 G4|A4 B4 c4 d4|
V: Ins
D4 E4 F4 G4|
"""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.abc"
            p.write_text(text, encoding="utf-8")
            payload = abc_doctor.diagnose(p)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["mismatches"])


class VerifyStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.report = self.dir / "report.json"
        self.report.write_text(json.dumps({"ok": True, "measured": {"bars": 16}}),
                               encoding="utf-8")
        self.state = self.dir / "state.json"
        self.state.write_text(json.dumps({
            "phase": "checks", "last_artifact": "score.abc",
            "last_check": "checker 1", "pass": True,
            "report_sha": hashlib.sha256(self.report.read_bytes()).hexdigest(),
            "next_action": "seed", "open_issues": [], "files": ["score.abc"],
        }), encoding="utf-8")
        self.review = self.dir / "core_review.md"
        self.review.write_text("\n".join(f"{i}. bar {i}: issue" for i in range(1, 6)) + "\n",
                               encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_vp(self, extra):
        out = self.dir / "verify.json"
        code = vp.main(["--score", str(EXAMPLE), "--plan", str(PLAN),
                        "--report", str(self.report), "--state", str(self.state),
                        "--review", str(self.review), "--json", str(out)] + extra)
        return code, json.loads(out.read_text(encoding="utf-8"))

    def test_state_and_review_pass(self):
        code, payload = self.run_vp([])
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])

    def test_review_must_be_five_lines(self):
        self.review.write_text("\n".join(f"{i}. bar {i}: issue" for i in range(1, 5)) + "\n",
                               encoding="utf-8")
        code, payload = self.run_vp([])
        self.assertEqual(code, 1)
        self.assertTrue(any(c["name"] == "core_review.md" and c["tag"] == "FAIL"
                            for c in payload["checks"]))

    def test_core_order(self):
        core = self.dir / "core.abc"
        score = self.dir / "score.abc"
        core.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        score.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        os.utime(core, (1000, 1000))
        os.utime(score, (2000, 2000))
        out = self.dir / "verify.json"
        code = vp.main(["--score", str(score), "--plan", str(PLAN),
                        "--core", str(core), "--require-core-first",
                        "--json", str(out)])
        self.assertEqual(code, 0, json.loads(out.read_text(encoding="utf-8")))
        os.utime(core, (3000, 3000))
        code = vp.main(["--score", str(score), "--plan", str(PLAN),
                        "--core", str(core), "--require-core-first",
                        "--json", str(out)])
        self.assertEqual(code, 1)
        self.assertTrue(any(c["name"] == "core order" and c["tag"] == "FAIL"
                            for c in json.loads(out.read_text(encoding="utf-8"))["checks"]))


if __name__ == "__main__":
    unittest.main()
