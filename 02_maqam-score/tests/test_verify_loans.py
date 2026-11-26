#!/usr/bin/env python3
"""Tests for verify_loans.py."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import asset_bank  # noqa: E402
import verify_loans  # noqa: E402

EXAMPLE = SKILL / "example" / "score.abc"


class LoanTests(unittest.TestCase):
    def _index(self, tmp: Path) -> tuple[Path, dict]:
        songs = tmp / "songs"
        songs.mkdir()
        shutil.copy(EXAMPLE, songs / "suno-test.abc")
        index = tmp / "assets.jsonl.gz"
        asset_bank.main([
            "build", "--songs", str(songs), "--out", str(index),
            "--meta", str(tmp / "meta.json"),
        ])
        rows = asset_bank.load_index(index)
        return index, rows[0]

    def _loan(self, asset: dict) -> dict:
        return {
            "asset": asset["id"],
            "source": asset["source"],
            "bars": f"{asset['start_bar']}-{asset['end_bar']}",
            "borrowed": ["rhythm", "contour"],
            "role": asset["role"],
            "fit": {"bars": asset["bars"], "cadence": asset["cadence_degree"],
                    "register": f"{asset['low']}-{asset['high']}"},
            "transform": ["remap to Kurd", "cadence degree 0"],
            "why": "two-bar phrase with a clear contour and a cadence that fits the section",
        }

    def test_valid_loan(self):
        with tempfile.TemporaryDirectory() as tmp:
            index, asset = self._index(Path(tmp))
            result = verify_loans.verify([self._loan(asset)], asset_bank.load_index(index))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["errors"], [])

    def test_bad_loan_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            index, asset = self._index(Path(tmp))
            loan = self._loan(asset)
            loan["asset"] = "missing"
            result = verify_loans.verify([loan], asset_bank.load_index(index))
        self.assertFalse(result["ok"])
        self.assertTrue(any("not found" in error for error in result["errors"]))

    def test_copy_without_transform_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            index, asset = self._index(Path(tmp))
            loan = self._loan(asset)
            loan["transform"] = ["none"]
            result = verify_loans.verify([loan], asset_bank.load_index(index))
        self.assertFalse(result["ok"])
        self.assertTrue(any("transform" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
