#!/usr/bin/env python3
"""Tests for asset_bank.py: build, query, apply, and the shipped index."""
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

EXAMPLE = SKILL / "example" / "score.abc"
SHIPPED = SKILL / "data" / "assets" / "assets.jsonl.gz"


class AssetBankTests(unittest.TestCase):
    def test_build_query_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            songs = Path(tmp) / "songs"
            songs.mkdir()
            shutil.copy(EXAMPLE, songs / "suno-test.abc")
            index = Path(tmp) / "assets.jsonl.gz"
            meta = Path(tmp) / "assets.meta.json"
            code = asset_bank.main([
                "build", "--songs", str(songs), "--out", str(index), "--meta", str(meta), "--cells",
            ])
            self.assertEqual(code, 0)
            payload = json.loads(meta.read_text(encoding="utf-8"))
            self.assertGreater(payload["assets"], 0)
            rows = asset_bank.load_index(index)
            self.assertTrue(any(row["quality"]["clean"] for row in rows))
            asset = rows[0]
            for key in ("id", "source", "bars", "role", "contour", "cadence_degree",
                        "syllables_min", "syllables_max", "quality"):
                self.assertIn(key, asset)
            # Query is read-only and must find at least one candidate or say so.
            code = asset_bank.main([
                "query", "--index", str(index), "--quality", "all", "--limit", "3",
            ])
            self.assertEqual(code, 0)
            # Apply returns a standalone ABC fragment, not a score write.
            code = asset_bank.main([
                "apply", "--index", str(index), "--id", asset["id"], "--to-key", "Dm",
            ])
            self.assertEqual(code, 0)

    def test_preview_keeps_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            songs = Path(tmp) / "songs"
            songs.mkdir()
            shutil.copy(EXAMPLE, songs / "suno-test.abc")
            index = Path(tmp) / "assets.jsonl.gz"
            meta = Path(tmp) / "assets.meta.json"
            asset_bank.main(["build", "--songs", str(songs), "--out", str(index), "--meta", str(meta)])
            rows = asset_bank.load_index(index)
            asset = rows[0]
            notes = [list(note) for note in asset["notes"]]
            text = asset_bank._render(
                asset, notes, meter=asset["meter"], tempo=asset["tempo"], key=asset["key"],
            )
            self.assertIn("V: Vocal", text)
            self.assertIn("V: Ins", text)
            self.assertEqual(text.count("|"), asset["bars"] * 2)

    def test_shipped_index_if_present(self):
        if not SHIPPED.exists():
            self.skipTest("shipped asset index not built")
        rows = asset_bank.load_index(SHIPPED)
        self.assertGreater(len(rows), 1000)
        self.assertGreater(sum(1 for row in rows if row["quality"]["clean"]), 100)
        self.assertEqual(len({row["source"] for row in rows}), 644)


if __name__ == "__main__":
    unittest.main()
