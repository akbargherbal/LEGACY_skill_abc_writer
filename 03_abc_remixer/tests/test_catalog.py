from __future__ import annotations

import unittest

from .helpers import store

from remix import catalog as catalog_mod  # noqa: E402


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.store = store()

    def _filters(self, **kwargs):
        values = dict(key=None, mode=None, meter=None, tempo=None, bars=None,
                      density=None, title=None, artist=None, source=None)
        values.update(kwargs)
        if values.get("tempo") is None:
            values["tempo"] = (None, None)
        elif not isinstance(values["tempo"], tuple):
            values["tempo"] = tuple(values["tempo"])
        if values.get("bars") is None:
            values["bars"] = (None, None)
        elif not isinstance(values["bars"], tuple):
            values["bars"] = tuple(values["bars"])
        return catalog_mod.Filters(**values)

    def test_limit_and_total(self):
        rows, total, bands = catalog_mod.select(self.store, self._filters(), limit=5)
        self.assertEqual(len(rows), 5)
        self.assertEqual(total, 670)
        self.assertIn("light_max", bands)
        rows, total, _ = catalog_mod.select(self.store, self._filters(), limit=999)
        self.assertEqual(len(rows), 40)
        self.assertEqual(total, 670)

    def test_key_and_mode_filter(self):
        rows, total, _ = catalog_mod.select(
            self.store, self._filters(key="Dm", mode="minor"), limit=40
        )
        self.assertGreater(total, 0)
        self.assertTrue(all(row["key"] == "Dm" and row["mode"] == "minor" for row in rows))

    def test_tempo_and_bars_filter(self):
        rows, total, _ = catalog_mod.select(
            self.store, self._filters(tempo=(70.0, 90.0), bars=(60, 120)), limit=40
        )
        self.assertGreater(total, 0)
        for row in rows:
            self.assertTrue(70 <= row["tempo"] <= 90)
            self.assertTrue(60 <= row["bars"] <= 120)

    def test_random_is_deterministic(self):
        a, _ta, _ = catalog_mod.select(
            self.store, self._filters(), limit=10, random_seed=7
        )
        b, _tb, _ = catalog_mod.select(
            self.store, self._filters(), limit=10, random_seed=7
        )
        self.assertEqual([row["song_id"] for row in a], [row["song_id"] for row in b])
        c, _tc, _ = catalog_mod.select(
            self.store, self._filters(), limit=10, random_seed=8
        )
        self.assertNotEqual([row["song_id"] for row in a], [row["song_id"] for row in c])

    def test_lines_are_capped(self):
        text = catalog_mod.render(self.store, self._filters(), limit=40)
        self.assertLessEqual(len(text), 8000)
        for line in text.splitlines()[1:]:
            self.assertLessEqual(len(line), 160)

    def test_density_band(self):
        rows, total, bands = catalog_mod.select(
            self.store, self._filters(density="light"), limit=40
        )
        self.assertGreater(total, 0)
        for row in rows:
            self.assertLessEqual(row["density"], bands["light_max"])

    def test_source_filter(self):
        rows, total, _ = catalog_mod.select(
            self.store, self._filters(source="suno_abc_score_dataset"), limit=40
        )
        self.assertEqual(total, 670)
        self.assertTrue(all(row["source"] == "suno_abc_score_dataset" for row in rows))


if __name__ == "__main__":
    unittest.main()
