from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from remix.errors import RemixError  # noqa: E402
from remix.ledger import Ledger  # noqa: E402


class LedgerTests(unittest.TestCase):
    def test_charge_and_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger"
            ledger = Ledger(path, 100)
            ledger.charge("catalog", None, "x" * 20)
            ledger.charge("slice", "song", "y" * 30)
            self.assertEqual(ledger.total(), 50)
            summary = ledger.summary()
            self.assertEqual(summary["calls"], 2)
            self.assertEqual(summary["per_tool"], {"catalog": 20, "slice": 30})

    def test_cap_crossing_fails_and_prints_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(Path(tmp) / "ledger", 10)
            ledger.charge("catalog", None, "x" * 8)
            with self.assertRaises(RemixError) as context:
                ledger.charge("songmap", "song", "y" * 8)
            self.assertEqual(context.exception.code, 3)
            self.assertEqual(ledger.total(), 8)

    def test_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(Path(tmp) / "ledger", 100)
            ledger.charge("catalog", None, "x")
            self.assertEqual(ledger.total(), 1)
            ledger.reset()
            self.assertEqual(ledger.total(), 0)
            self.assertFalse(ledger.path.exists())


if __name__ == "__main__":
    unittest.main()
