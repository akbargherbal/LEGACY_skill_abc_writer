from __future__ import annotations

import unittest

from .helpers import SAMPLE_SONG, store

from remix.quotecheck import verify_item  # noqa: E402
from remix.store import Note, voice_notes  # noqa: E402
from remix.transforms import apply_transforms  # noqa: E402


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.store = store()
        _text, score = self.store.load_song(SAMPLE_SONG)
        self.source = [
            note for note in voice_notes(score, "Vocal") if 33 <= note.bar <= 36
        ]
        self.item = {
            "id": SAMPLE_SONG,
            "role": "test",
            "from_bars": "34-37",
            "to_bars": "1-1",
            "voice": "Vocal",
            "transform": [],
            "_tolerance": 0,
        }

    def _target(self, pitches, durations):
        return [Note(float(index), int(pitch), float(duration), 0)
                for index, (pitch, duration) in enumerate(zip(pitches, durations))]

    def _verify(self, transform):
        item = dict(self.item)
        item["transform"] = transform
        expected = apply_transforms(
            [(note.pitch, note.duration) for note in self.source], transform
        )
        target = self._target(expected.pitches, expected.durations)
        return verify_item(self.store, item, {"Vocal": target, "Ins": []})

    def test_exact_quote(self):
        result = self._verify([])
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["literal"])

    def test_transposed_quote_is_literal(self):
        result = self._verify(["transpose:+2"])
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["literal"])

    def test_inverted_quote(self):
        result = self._verify(["invert"])
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["literal"])

    def test_retrograde_quote(self):
        result = self._verify(["retrograde"])
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["literal"])

    def test_augmented_quote(self):
        result = self._verify(["augment:2x"])
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["literal"])

    def test_fragmented_quote(self):
        result = self._verify(["fragment:first-4-notes"])
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["literal"])

    def test_rhythm_only_quote(self):
        item = dict(self.item)
        item["transform"] = ["rhythm-only"]
        durations = [note.duration for note in self.source]
        target = self._target([60 + index for index in range(len(durations))], durations)
        result = verify_item(self.store, item, {"Vocal": target, "Ins": []})
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["literal"])

    def test_contour_only_quote(self):
        item = dict(self.item)
        item["transform"] = ["contour-only"]
        expected = apply_transforms(
            [(note.pitch, note.duration) for note in self.source], ["contour-only"]
        )
        target = self._target(expected.pitches, expected.durations)
        result = verify_item(self.store, item, {"Vocal": target, "Ins": []})
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["literal"])

    def test_unrelated_target_is_not_found(self):
        target = [Note(float(index), 60 + (index % 3), 1.0, 0) for index in range(len(self.source))]
        result = verify_item(self.store, self.item, {"Vocal": target, "Ins": []})
        self.assertEqual(result["status"], "not_found")

    def test_unknown_source_is_reported(self):
        item = dict(self.item)
        item["id"] = "no-such-song"
        result = verify_item(self.store, item, {"Vocal": [], "Ins": []})
        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["reason"], "source_not_found")


if __name__ == "__main__":
    unittest.main()
