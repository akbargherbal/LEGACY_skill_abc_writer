from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from .helpers import OSTRIS, SKILL, STORE, store

from remix.build import build, verify  # noqa: E402


class BuildTests(unittest.TestCase):
    def test_bundled_store_verifies(self):
        result = verify(store())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["songs"], 472)

    def test_build_is_idempotent(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = build(OSTRIS, first)
            b = build(OSTRIS, second)
            self.assertEqual(a["counts"], b["counts"])
            self.assertEqual(a["exclusions"], b["exclusions"])
            self.assertTrue(a["gate_pass"])
            for name in ("catalog.tsv", "catalog_meta.json", "build_report.json"):
                self.assertEqual(
                    (Path(first) / name).read_bytes(),
                    (Path(second) / name).read_bytes(),
                    name,
                )
            self.assertEqual(
                (Path(first) / "index" / "motif.json.gz").read_bytes(),
                (Path(second) / "index" / "motif.json.gz").read_bytes(),
            )
            first_songs = sorted((Path(first) / "songs").glob("*.abc"))
            second_songs = sorted((Path(second) / "songs").glob("*.abc"))
            self.assertEqual([path.name for path in first_songs],
                             [path.name for path in second_songs])
            for left, right in zip(first_songs, second_songs):
                self.assertEqual(left.read_bytes(), right.read_bytes(), left.name)

    def test_include_all_keeps_duplicates(self):
        with tempfile.TemporaryDirectory() as out:
            report = build(OSTRIS, out, include_all=True)
            self.assertEqual(report["counts"]["included"], 482)
            self.assertEqual(report["counts"]["excluded"], 0)
            self.assertTrue(report["gate_pass"])

    def test_store_contains_no_audio_or_shards(self):
        suffixes = {".mp3", ".wav", ".flac", ".m4a"}
        for path in (STORE / "songs").rglob("*"):
            self.assertNotIn(path.suffix.lower(), suffixes)
        self.assertFalse(list((STORE / "songs").glob("shard-*.json")))


if __name__ == "__main__":
    unittest.main()
