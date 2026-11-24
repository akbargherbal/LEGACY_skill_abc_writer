#!/usr/bin/env python3
"""Tests for craft.py: the report-only tune mirror.

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
import craft  # noqa: E402

EXAMPLE = SKILL / "example" / "score.abc"


class CraftTests(unittest.TestCase):
    def test_example_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "craft.json"
            code = craft.main([str(EXAMPLE), "--json", str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(payload["errors"], [])
        row = payload["rows"][0]
        self.assertEqual(row["bars"], 16)
        for key in ("rhythm_variety", "end_long_share", "distinct_bar_share",
                    "repeat_share", "end_degrees"):
            self.assertIn(key, row)

    def test_bad_score_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.abc"
            bad.write_text("X:1\nT:\n", encoding="utf-8")
            code = craft.main([str(bad)])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
