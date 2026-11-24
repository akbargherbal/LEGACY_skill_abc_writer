from __future__ import annotations

import unittest

from .helpers import SAMPLE_SONG, store

from remix.errors import RemixError  # noqa: E402
from remix.slice import slice_song  # noqa: E402
from remix.store import voice_notes  # noqa: E402

import abc_tools  # noqa: E402


class SliceTests(unittest.TestCase):
    def setUp(self):
        self.store = store()

    def _slice(self, song_id, bars, **kwargs):
        return slice_song(self.store, song_id, bars, **kwargs)

    def test_refuses_more_than_the_cap(self):
        with self.assertRaises(RemixError):
            self._slice(SAMPLE_SONG, "1-9")
        result = self._slice(SAMPLE_SONG, "1-8", max_bars=8)
        self.assertIn("X:1", result["text"])

    def test_output_parses_and_preserves_intervals(self):
        result = self._slice(SAMPLE_SONG, "34-37", voice="Vocal")
        score = abc_tools.parse(result["text"])
        source = self.store.load_song(SAMPLE_SONG)[1]
        source_notes = [note for note in voice_notes(source, "Vocal") if 33 <= note.bar <= 36]
        target_notes = voice_notes(score, "Vocal")
        self.assertEqual(
            [b.pitch - a.pitch for a, b in zip(source_notes, source_notes[1:])],
            [b.pitch - a.pitch for a, b in zip(target_notes, target_notes[1:])],
        )
        self.assertEqual(score.voices["Vocal"].chords, [])

    def test_to_key_keeps_intervals(self):
        result = self._slice(SAMPLE_SONG, "34-37", voice="Vocal", to_key="Dm")
        score = abc_tools.parse(result["text"])
        self.assertEqual(score.voices["Vocal"].key, "Dm")
        source = self.store.load_song(SAMPLE_SONG)[1]
        source_notes = [note for note in voice_notes(source, "Vocal") if 33 <= note.bar <= 36]
        target_notes = voice_notes(score, "Vocal")
        self.assertEqual(
            [b.pitch - a.pitch for a, b in zip(source_notes, source_notes[1:])],
            [b.pitch - a.pitch for a, b in zip(target_notes, target_notes[1:])],
        )

    def test_transpose_label_and_pitch(self):
        result = self._slice(SAMPLE_SONG, "34-37", voice="Vocal", transpose=2)
        score = abc_tools.parse(result["text"])
        source = self.store.load_song(SAMPLE_SONG)[1]
        source_notes = [note for note in voice_notes(source, "Vocal") if 33 <= note.bar <= 36]
        target_notes = voice_notes(score, "Vocal")
        self.assertEqual([note.pitch for note in target_notes],
                         [note.pitch + 2 for note in source_notes])
        self.assertIn("transpose=+2", result["text"])

    def test_one_voice_still_emits_two_voices(self):
        result = self._slice(SAMPLE_SONG, "34-37", voice="Vocal")
        score = abc_tools.parse(result["text"])
        self.assertEqual(set(score.voices), {"Vocal", "Ins"})
        self.assertEqual([note.pitch for note in voice_notes(score, "Ins")], [])

    def test_one_32nd_source_auto_unit_roundtrip(self):
        rows = {row["song_id"]: row for row in self.store.load_catalog()}
        song_id = next(row for row in rows.values() if row["unit"] == "1/32")["song_id"]
        result = self._slice(song_id, "1-4")
        self.assertIn("L:1/32", result["text"])
        abc_tools.parse(result["text"])

    def test_forced_unit_reports_and_parses(self):
        rows = {row["song_id"]: row for row in self.store.load_catalog()}
        song_id = next(row for row in rows.values() if row["unit"] == "1/32")["song_id"]
        result = self._slice(song_id, "2-4", unit="1/16", allow_lossy=True)
        self.assertIn("L:1/16", result["text"])
        self.assertGreaterEqual(result["quantized"], 0)
        abc_tools.parse(result["text"])

    def test_key_change_is_refused_by_default(self):
        with self.assertRaises(RemixError):
            self._slice("suno-0211", "34-40")

    def test_meter_change_roundtrip(self):
        result = self._slice("suno-0000", "1-8")
        score = abc_tools.parse(result["text"])
        self.assertEqual(len(score.voices["Vocal"].bars), 8)


if __name__ == "__main__":
    unittest.main()
