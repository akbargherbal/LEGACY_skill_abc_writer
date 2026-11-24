from __future__ import annotations

import sys
import unittest

from .helpers import REPO

sys.path.insert(0, str(REPO / "tools"))

import build_suno_library  # noqa: E402


class SunoLibraryTests(unittest.TestCase):
    def test_existing_bundle_matches_the_pickle(self):
        summary = build_suno_library._check(
            REPO / "data" / "SUNO_ABC_SCORE_DATASET.pkl",
            REPO / "data" / "suno",
        )
        self.assertTrue(summary["ok"], summary["errors"])
        self.assertEqual(summary["rows"], 670)
        self.assertEqual(summary["parse_ok"], 670)
        self.assertEqual(summary["vocal_rows"], 644)
        self.assertEqual(summary["ins_only_rows"], 26)

    def test_ids_are_stable_and_prefixed(self):
        from remix.store import Store

        rows = Store(REPO / "03_abc_remixer" / "data" / "remix").load_catalog()
        self.assertEqual(rows[0]["song_id"], "suno-0000")
        self.assertEqual(rows[-1]["song_id"], "suno-0669")
        self.assertTrue(all(row["source"] == "suno_abc_score_dataset" for row in rows))


if __name__ == "__main__":
    unittest.main()
