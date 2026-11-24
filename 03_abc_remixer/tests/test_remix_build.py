from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .helpers import STORE, SUNODATA, store

from remix.build import build_suno, verify  # noqa: E402


class BuildTests(unittest.TestCase):
    def test_bundled_store_verifies(self):
        result = verify(store())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["songs"], 670)

    def test_build_is_idempotent(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = build_suno(SUNODATA, first)
            b = build_suno(SUNODATA, second)
            self.assertEqual(a["counts"], b["counts"])
            self.assertTrue(a["gate_pass"])
            for name in ("catalog.tsv", "catalog_meta.json", "build_report.json", "dataset.json"):
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

    def test_suno_build_includes_all_rows(self):
        with tempfile.TemporaryDirectory() as out:
            report = build_suno(SUNODATA, out)
            self.assertEqual(report["counts"]["records"], 670)
            self.assertEqual(report["counts"]["included"], 670)
            self.assertEqual(report["counts"]["excluded"], 0)
            self.assertEqual(report["counts"]["ins_only_rows"], 26)
            self.assertTrue(report["gate_pass"])

    def test_store_contains_no_audio_or_shards(self):
        suffixes = {".mp3", ".wav", ".flac", ".m4a"}
        for path in (STORE / "songs").rglob("*"):
            self.assertNotIn(path.suffix.lower(), suffixes)
        self.assertFalse(list((STORE / "songs").glob("shard-*.json")))

    def test_store_has_only_suno_ids(self):
        rows = store().load_catalog()
        self.assertTrue(rows)
        self.assertTrue(all(row["song_id"].startswith("suno-") for row in rows))
        self.assertTrue(all(row["source"] == "suno_abc_score_dataset" for row in rows))


if __name__ == "__main__":
    unittest.main()
