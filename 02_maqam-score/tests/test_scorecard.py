#!/usr/bin/env python3
"""Tests for the whole-draft scorecard (1.0)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "scorecard.py"
EXAMPLE = ROOT / "example"
sys.path.insert(0, str(ROOT / "scripts"))
import scorecard  # noqa: E402


class ScorecardTests(unittest.TestCase):
    def test_example_has_no_blocking(self):
        payload = scorecard.build(EXAMPLE / "score.abc",
                                  EXAMPLE / "plan.json",
                                  EXAMPLE / "phrases.json",
                                  EXAMPLE / "lyrics.txt")
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["parse_errors"], [])
        self.assertEqual(payload["blocking"], [])
        self.assertEqual(payload["summary"]["bars"], 16)
        self.assertEqual(len(payload["seams"]), 3)
        self.assertTrue(payload["bands"])
        card = scorecard.format_card(payload)
        self.assertIn("KEY BANDS", card)
        self.assertIn("BLOCKING  none", card)
        self.assertIn("RELEASE-BLOCKING  none", card)
        self.assertEqual(payload["release_blocking"], [])
        self.assertIn("SEAMS", card)

    def test_blocking_band_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = json.loads((EXAMPLE / "plan.json").read_text(encoding="utf-8"))
            plan["syllables"] = 40  # 20/40 = 0.50, below the 1.00 sanity floor
            plan_path = Path(tmp) / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            payload = scorecard.build(EXAMPLE / "score.abc", plan_path,
                                      EXAMPLE / "phrases.json",
                                      EXAMPLE / "lyrics.txt")
            names = {item["name"] for item in payload["blocking"]}
            self.assertIn("notes per syllable", names)
            card = scorecard.format_card(payload)
            self.assertIn("BLOCKING", card)
            self.assertIn("fix:", card)

    def test_release_only_failure_is_not_hidden(self):
        """B1: a score the card passes but `release` fails must say so."""
        text = (EXAMPLE / "score.abc").read_text(encoding="utf-8").rstrip("\n")
        self.assertTrue(text.endswith("F,2 F,2 A,2 G,2 F,8|Z|"))
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad_end.abc"
            bad.write_text(text[:-2] + "A,16|\n", encoding="utf-8")
            payload = scorecard.build(bad, EXAMPLE / "plan.json",
                                      EXAMPLE / "phrases.json",
                                      EXAMPLE / "lyrics.txt")
            self.assertEqual(payload["blocking"], [])
            names = {i["name"] for i in payload["release_blocking"]}
            self.assertIn("final rest", names)
            self.assertNotIn("final rest", {i["name"] for i in payload["polish"]})
            card = scorecard.format_card(payload)
            self.assertIn("RELEASE-BLOCKING  (", card)
            self.assertNotIn("NEXT  No blocking", card)

    def test_parse_error_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.abc"
            text = (EXAMPLE / "score.abc").read_text(encoding="utf-8")
            bad.write_text(text.replace("F2 F2 A8 G2 F2|",
                                        "F2 F2 A8 G2 F2 F2|", 1),
                           encoding="utf-8")
            payload = scorecard.build(bad, EXAMPLE / "plan.json",
                                      EXAMPLE / "phrases.json")
            self.assertIsNotNone(payload["error"])
            self.assertTrue(payload["parse_errors"])
            card = scorecard.format_card(payload)
            self.assertIn("SCORE PARSE ERROR", card)

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "card.json"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(EXAMPLE / "score.abc"),
                 "--plan", str(EXAMPLE / "plan.json"),
                 "--phrases", str(EXAMPLE / "phrases.json"),
                 "--lyrics", str(EXAMPLE / "lyrics.txt"),
                 "--json", str(out)],
                text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["bars"], 16)
            self.assertEqual(payload["blocking"], [])


if __name__ == "__main__":
    unittest.main()
