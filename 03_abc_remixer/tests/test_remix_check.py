from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .helpers import SAMPLE_SONG, plan_payload, store, write_json

from remix.quotecheck import check  # noqa: E402
from remix.slice import slice_song  # noqa: E402


class RemixCheckTests(unittest.TestCase):
    def setUp(self):
        self.store = store()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _score(self, bars="34-37"):
        result = slice_song(self.store, SAMPLE_SONG, bars)
        path = self.root / "score.abc"
        path.write_text(result["text"], encoding="utf-8")
        return path

    def _plan(self, source=SAMPLE_SONG, literal_cap=4):
        remix = {
            "concept": "test",
            "sources": [
                {
                    "id": source,
                    "role": "test",
                    "from_bars": "34-37",
                    "to_bars": "1-4",
                    "transform": [],
                    "voice": "both",
                }
            ],
            "literal_cap_bars": literal_cap,
        }
        return write_json(self.root / "plan.json", plan_payload(remix=remix))

    def test_declared_quote_is_verified(self):
        report = check(self.store, self._score(), self._plan())
        quote = report["remix"]["quotes"][0]
        self.assertEqual(quote["status"], "verified")
        self.assertTrue(report["remix"]["metrics"]["literal_share"] > 0)

    def test_literal_cap_is_a_hard_failure(self):
        report = check(self.store, self._score(), self._plan(literal_cap=1))
        codes = [item["code"] for item in report["failures"]]
        self.assertIn("literal_cap", codes)
        self.assertFalse(report["pass"])

    def test_undeclared_quote_is_detected(self):
        # Use a score from one song but declare a different source.
        score = self._score()
        plan = self._plan(source="suno-0000")
        report = check(self.store, score, plan)
        self.assertGreater(report["remix"]["undeclared_total"], 0)
        codes = [item["code"] for item in report["warnings"]]
        self.assertIn("undeclared_quote", codes)

    def test_strict_quotes_turns_not_found_into_failure(self):
        score = self._score()
        plan = self._plan(source="suno-0000")
        report = check(self.store, score, plan,
                       strict_quotes=True)
        quote = report["remix"]["quotes"][0]
        self.assertEqual(quote["status"], "not_found")
        codes = [item["code"] for item in report["failures"]]
        self.assertIn("quote_not_found", codes)

    def test_fail_on_undeclared_turns_it_into_failure(self):
        score = self._score()
        plan = self._plan(source="suno-0000")
        report = check(self.store, score, plan,
                       fail_on_undeclared=True)
        codes = [item["code"] for item in report["failures"]]
        self.assertIn("undeclared_quote", codes)


if __name__ == "__main__":
    unittest.main()
