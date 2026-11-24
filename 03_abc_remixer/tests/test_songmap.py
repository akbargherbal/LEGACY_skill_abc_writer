from __future__ import annotations

import unittest

from .helpers import SAMPLE_SONG, store

from remix.songmap import songmap  # noqa: E402
from remix.store import voice_notes  # noqa: E402


class SongmapTests(unittest.TestCase):
    def setUp(self):
        self.store = store()

    def test_cap_and_sections(self):
        text, payload = songmap(self.store, SAMPLE_SONG)
        self.assertLessEqual(len(text), 3000)
        self.assertNotIn("V: Vocal", text)
        sections = payload["sections"]
        self.assertEqual(sections[0]["first"], 1)
        self.assertEqual(sections[-1]["last"], payload["header"]["bars"])
        for left, right in zip(sections, sections[1:]):
            self.assertEqual(left["last"] + 1, right["first"])

    def test_hooks_occur_at_the_listed_bars(self):
        _text, payload = songmap(self.store, SAMPLE_SONG)
        _abc, score = self.store.load_song(SAMPLE_SONG)
        for voice, hooks in payload["hooks"].items():
            notes = voice_notes(score, voice)
            for hook in hooks:
                first_bar = hook["bars"][0]
                candidates = [index for index, note in enumerate(notes) if note.bar + 1 == first_bar]
                self.assertTrue(candidates, f"{voice} hook {hook} has no note at bar {first_bar}")
                found = False
                for index in candidates:
                    got = [
                        b.pitch - a.pitch
                        for a, b in zip(notes[index:index + len(hook["intervals"])],
                                        notes[index + 1:index + len(hook["intervals"]) + 1])
                    ]
                    if got == hook["intervals"]:
                        found = True
                        break
                self.assertTrue(found, hook)

    def test_json_payload_has_no_abc(self):
        _text, payload = songmap(self.store, SAMPLE_SONG)
        self.assertIn("sections", payload)
        self.assertIn("hooks", payload)
        self.assertNotIn("text", payload)


if __name__ == "__main__":
    unittest.main()
