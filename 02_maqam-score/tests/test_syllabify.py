#!/usr/bin/env python3
"""Tests for the per-line phrase sidecar in syllabify.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SYLLABIFY = SKILL / "scripts" / "syllabify.py"
LYRICS = SKILL / "example" / "lyrics.txt"


class SyllabifyTests(unittest.TestCase):
    def test_phrase_sidecar_has_lines_and_pauses(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "phrases.json"
            result = subprocess.run(
                [sys.executable, str(SYLLABIFY), str(LYRICS),
                 "--tempo", "80", "--phrases", str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["tempo"], 80)
        self.assertEqual(data["body_bars"], 4)
        self.assertEqual(len(data["lines"]), 4)
        self.assertEqual(data["lines"][0]["pause_after_s"], 0.5)
        self.assertEqual(data["lines"][1]["pause_after_s"], 1.0)
        self.assertEqual(data["lines"][0]["body_bar_start"], 1)
        self.assertEqual(data["lines"][0]["body_bar_end"], 1)

    def test_sections_write_absolute_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "phrases.json"
            result = subprocess.run(
                [sys.executable, str(SYLLABIFY), str(LYRICS),
                 "--tempo", "80", "--phrases", str(out),
                 "--sections", "verse=2,chorus=8"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
        bars = [(row["bar_start"], row["bar_end"]) for row in data["lines"]]
        self.assertEqual(bars, [(2, 2), (3, 3), (8, 8), (9, 9)])
        self.assertEqual(data["lines"][0]["body_bar_start"], 1)
        self.assertEqual(data["lines"][0]["bar_start"], 2)

    def test_sections_reject_bad_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "phrases.json"
            result = subprocess.run(
                [sys.executable, str(SYLLABIFY), str(LYRICS),
                 "--tempo", "80", "--phrases", str(out),
                 "--sections", "chorus=2,verse=8"],
                capture_output=True, text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("order mismatch", result.stderr)

    def test_sections_reject_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "phrases.json"
            result = subprocess.run(
                [sys.executable, str(SYLLABIFY), str(LYRICS),
                 "--tempo", "80", "--phrases", str(out),
                 "--sections", "verse=2,chorus=2"],
                capture_output=True, text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("previous section ends", result.stderr)


if __name__ == "__main__":
    unittest.main()
