from __future__ import annotations

import unittest

from .helpers import SAMPLE_SONG, store

from remix.errors import RemixError  # noqa: E402
from remix.motif import query, query_contour  # noqa: E402
from remix.store import voice_notes  # noqa: E402


class MotifTests(unittest.TestCase):
    def setUp(self):
        self.store = store()

    def _pattern(self, voice="Vocal", size=8):
        _text, score = self.store.load_song(SAMPLE_SONG)
        notes = voice_notes(score, voice)
        intervals = [b.pitch - a.pitch for a, b in zip(notes, notes[1:])]
        for index in range(len(intervals) - size):
            window = intervals[index:index + size]
            if len(set(window)) >= 3 and max(window) - min(window) >= 5:
                return window
        self.skipTest("no distinctive test window")

    def test_known_pattern_ranks_source_first(self):
        pattern = self._pattern()
        rows, total = query(self.store, intervals=",".join(map(str, pattern)),
                            voice="Vocal", min_run=4, limit=10)
        self.assertGreater(total, 0)
        self.assertEqual(rows[0]["song_id"], SAMPLE_SONG)

    def test_rhythm_only(self):
        _text, score = self.store.load_song(SAMPLE_SONG)
        notes = voice_notes(score, "Vocal")
        durations = [round(note.duration, 6) for note in notes[10:15]]
        unit = min(round(note.duration, 6) for note in notes if note.duration > 0)
        query_text = ",".join(f"{value / unit:g}" for value in durations)
        rows, total = query(self.store, durations=query_text, min_run=4, limit=10,
                            song_id=SAMPLE_SONG)
        self.assertGreater(total, 0)
        self.assertTrue(any(row["song_id"] == SAMPLE_SONG for row in rows))

    def test_both_voices_are_indexed(self):
        pattern = self._pattern(voice="Ins")
        rows, total = query(self.store, intervals=",".join(map(str, pattern)),
                            voice="Ins", min_run=4, limit=10)
        self.assertGreater(total, 0)
        self.assertTrue(all(row["voice"] == "Ins" for row in rows))

    def test_trivial_pattern_is_refused(self):
        with self.assertRaises(RemixError):
            query(self.store, intervals="0,0,0,0", min_run=4)
        rows, _total = query(self.store, intervals="0,0,0,0", min_run=4,
                            allow_trivial=True)
        self.assertGreaterEqual(len(rows), 0)

    def test_query_is_deterministic(self):
        pattern = ",".join(map(str, self._pattern()))
        first, _ = query(self.store, intervals=pattern, limit=5)
        second, _ = query(self.store, intervals=pattern, limit=5)
        self.assertEqual(first, second)

    def test_contour_query(self):
        rows, total = query_contour(
            self.store, contour="wave", degree_start=7, degree_end=0,
            bars=2, voice="both", limit=5,
        )
        self.assertGreater(total, 0)
        self.assertTrue(all(row["contour"] == "wave" for row in rows))


if __name__ == "__main__":
    unittest.main()
