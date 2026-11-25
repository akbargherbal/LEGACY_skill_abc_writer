#!/usr/bin/env python3
"""Audit-probe tests for the four mechanical fixes (items 1-4).

Each probe must fail or warn exactly as the plan designs:

* Item 2 prosody: partial harakat fails, a wrong ``plan.syllables`` fails,
  an over-cap score fails, a short score warns (padding risk), and a
  hand-edited ``prosody.json`` is not trusted (the checker recomputes).
* Item 4 alignment: a note deficit of one warns, more than one fails,
  excess notes warn, orphan vocal notes fail, and ``vocalise_bars``
  prevents a false positive.
* Item 1 copies: an exact copy passes, a one-note drift fails, a declared
  mutation that did not happen fails, and a transposed copy is caught.
* Item 3 binding: section-plan tiling fails on a mismatch, deviation
  asserts are banded, unverifiable entries are listed as declared not
  verifiable, boilerplate strings fail, and legacy string deviations warn.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import checker  # noqa: E402
import copies  # noqa: E402
import prosody_check  # noqa: E402
import alignment  # noqa: E402
import binding  # noqa: E402
import syllabify  # noqa: E402

CAL = checker.load_calibration()

VOCAL = 'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"'
INS = 'V: Ins clef=treble name="Ins Melody" snm="Inst."'


def header() -> str:
    return (
        "X:1\nT:\nM:4/4\nL:1/16\nQ:1/4=80\n"
        f"{VOCAL}\n{INS}\nK:Am\n"
    )


def parse(text: str):
    return checker.parse(header() + text)


SMALL_PLAN = {
    "key": "Am", "tempo": 80, "meter": "4/4", "unit": "1/16",
    "bars": 4, "syllables": 8, "plan_version": "0.8.0",
    "sections": ["verse"],
    "melisma_min": 1.0, "melisma_max": 1.55,
    "register": {"mean": 70, "top": 80, "max_top": 84, "tolerance": 3},
    "max_top_duration_share": 0.85, "min_distinct_durations": 1,
    "ties_min": 0, "min_fill_notes": 1, "ins_active_share_min": 0.0,
    "chords_min": 0, "strict_shape": False, "maqam": None,
    "deviations": [],
}

LYRICS_MARKED = "[Verse]\nyَا حَبيبي\nقَدْ تَبَتَّرْ\n"  # fully vocalised
LYRICS_UNMARKED = "[Verse]\nyا حبيبي\nقد تتברر\n"  # no harakat


class ProsodyTests(unittest.TestCase):
    def test_partial_harakat_fails(self):
        """Every Arabic word must carry at least one vowel mark."""
        plan = dict(SMALL_PLAN)
        res = prosody_check.check_prosody(
            parse("V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"),
            plan, lyrics_text=LYRICS_UNMARKED, lyrics_present=True,
            calibration=CAL,
        )
        names = [n for n, ok, _d, _c, _t in res["checks"]]
        self.assertIn("vocalisation coverage", names)
        fail = [d for n, ok, d, c, _t in res["checks"]
                if n == "vocalisation coverage" and not ok]
        self.assertTrue(fail, res["checks"])

    def test_wrong_syllable_total_fails(self):
        """plan.syllables must equal the recomputed total."""
        plan = dict(SMALL_PLAN, syllables=99)  # recomputed is 8
        res = prosody_check.check_prosody(
            parse("V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"),
            plan, lyrics_text=LYRICS_MARKED, lyrics_present=True,
            calibration=CAL,
        )
        fails = [(n, d) for n, ok, d, _c, _t in res["checks"]
                 if n == "lyrics syllables" and not ok]
        self.assertTrue(fails, res["checks"])

    def test_short_score_warns_padding_risk(self):
        """A score far below the raw cap warns (padding risk, banded)."""
        plan = dict(SMALL_PLAN)
        # few letters -> large raw cap; short score -> ratio below corpus min
        res = prosody_check.check_prosody(
            parse("V: Vocal\nZ|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"),
            plan, lyrics_text=LYRICS_MARKED, lyrics_present=True,
            calibration=CAL,
        )
        caps = [(d, c) for n, ok, d, c, _t in res["checks"] if n == "duration cap"]
        self.assertTrue(caps, res["checks"])
        _detail, cls = caps[0]
        self.assertEqual(cls, "banded")

    def test_hand_copied_total_is_not_trusted(self):
        """The checker recomputes from lyrics; a hand-copied total loses."""
        plan = dict(SMALL_PLAN, syllables=6)  # LYRICS_MARKED carries 6 harakat
        res = prosody_check.check_prosody(
            parse("V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"),
            plan, lyrics_text=LYRICS_MARKED, lyrics_present=True,
            calibration=CAL,
        )
        self.assertTrue(res["prosody_checked"])
        self.assertEqual(res["recomputed"]["syllables"], 6)
        syllables_checks = [(ok) for n, ok, _d, _c, _t in res["checks"]
                            if n == "lyrics syllables"]
        self.assertTrue(syllables_checks and all(syllables_checks))

    def test_stale_prosody_json_is_ignored_by_the_cli(self):
        """A hand-edited prosody.json next to the inputs cannot change the verdict."""
        plan = dict(
            SMALL_PLAN,
            syllables=6,
            copies=[],
            arrangement={
                "section_plan": [{
                    "bars": "1-4",
                    "vocal_notes_per_bar": [0, 4],
                    "ins_notes_per_bar": [0, 0],
                    "ins_active_share": [0, 0],
                    "answer_rate": [0, 1],
                }],
                "ins_entries": [],
            },
        )
        score_text = header() + "V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "score.abc").write_text(score_text, encoding="utf-8")
            (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (tmp_path / "lyrics.txt").write_text(LYRICS_MARKED, encoding="utf-8")
            # A stale/hand-edited sidecar with the wrong total; the checker must
            # recompute from lyrics.txt and never read this file.
            (tmp_path / "prosody.json").write_text(
                json.dumps({"syllables": 999}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "checker.py"),
                 str(tmp_path / "score.abc"),
                 "--plan", str(tmp_path / "plan.json"),
                 "--lyrics", str(tmp_path / "lyrics.txt")],
                capture_output=True, text=True, cwd=tmp_path,
            )
        # This tiny fixture may fail unrelated sanity targets; the point is that
        # the syllable check comes from lyrics.txt, not the stale prosody.json.
        self.assertNotIn("FAIL  [exact       ]  lyrics syllables", result.stdout)
        self.assertIn("PASS  [exact       ]  lyrics syllables", result.stdout)


def rest_score(n_bars: int, tempo: int = 40) -> str:
    """A full score of ``n_bars`` rest bars per voice, in <=4-bar blocks."""
    parts = ["X:1\nT:\nM:4/4\nL:1/16\nQ:1/4={tempo}\n{VOCAL}\n{INS}\nK:Am\n% verse"]
    remaining = n_bars
    while remaining > 0:
        chunk = min(4, remaining)
        parts.append("V: Vocal\n" + "Z|" * chunk)
        parts.append("V: Ins\n" + "Z|" * chunk)
        remaining -= chunk
    return "\n".join(parts).format(tempo=tempo, VOCAL=VOCAL, INS=INS) + "\n"


LYRICS_ONE_LETTER = "[Verse]\nأَ\n"  # 1 letter, 1 harakah


class CapTests(unittest.TestCase):
    def test_over_cap_fails_when_confirmed(self):
        """Over the confirmed ceiling (1.00 of raw cap) is a hard FAIL."""
        plan = dict(SMALL_PLAN, tempo=40, syllables=1)
        # 19 bars at Q=40 -> 114 s; one-letter cap ~111.4 s; ratio 1.023.
        # Above 1.00 confirmed ceiling but below 1.15 margin -> exact FAIL only
        # when cap_confirmed.
        res = prosody_check.check_prosody(
            checker.parse(rest_score(19, 40)), plan,
            lyrics_text=LYRICS_ONE_LETTER, lyrics_present=True,
            cap_confirmed_override=True, calibration=CAL,
        )
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "duration cap" and not ok and c == "exact"]
        self.assertTrue(fails, res["checks"])

    def test_between_p95_and_margin_warns(self):
        """Ratio between corpus P95 and the fail margin warns (banded)."""
        plan = dict(SMALL_PLAN, tempo=40, syllables=1)
        # 21 bars at Q=40, M:4/4, L:1/16 -> 6 s/bar = 126 s; one-letter cap ~111.4 s
        # ratio 1.13: above P95 1.003, below fail margin 1.15 -> banded WARN.
        res = prosody_check.check_prosody(
            checker.parse(rest_score(21, 40)), plan,
            lyrics_text=LYRICS_ONE_LETTER, lyrics_present=True,
            calibration=CAL,
        )
        warns = [d for n, ok, d, c, _t in res["checks"]
                 if n == "duration cap" and not ok and c == "banded"]
        self.assertTrue(warns, res["checks"])

    def test_over_cap_fail_ratio_fails_without_confirmation(self):
        """Above cap_fail_ratio (1.15) is a hard FAIL by default."""
        plan = dict(SMALL_PLAN, tempo=40, syllables=1)
        # 24 bars at Q=40 -> 144 s; one-letter raw cap ~111.4 s -> ratio 1.29.
        res = prosody_check.check_prosody(
            checker.parse(rest_score(24, 40)), plan,
            lyrics_text=LYRICS_ONE_LETTER, lyrics_present=True,
            calibration=CAL,
        )
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "duration cap" and not ok and c == "exact"]
        self.assertTrue(fails, res["checks"])
        self.assertIn("1.15", fails[0])


class CopiesTests(unittest.TestCase):
    def _copies_plan(self, entry):
        return dict(SMALL_PLAN, copies=[entry])

    def test_exact_copy_passes(self):
        plan = self._copies_plan({"of_bars": "1", "bars": "2",
                                  "voices": ["Vocal"]})
        res = copies.check_copies(parse(
            "V: Vocal\nD4 E4 F4 G4|D4 E4 F4 G4|A4 A4 A4 A4|Z|\n"
            "V: Ins\nZ|Z|Z|Z|\n"), plan)
        ok = [ok for n, ok, _d, _c, _t in res["checks"]
              if n == "copies map" and ok]
        self.assertTrue(ok, res["checks"])

    def test_one_note_drift_fails(self):
        plan = self._copies_plan({"of_bars": "1", "bars": "2",
                                  "voices": ["Vocal"]})
        res = copies.check_copies(parse(
            "V: Vocal\nD4 E4 F4 G4|D4 E4 F4 A4|A4 A4 A4 A4|Z|\n"
            "V: Ins\nZ|Z|Z|Z|\n"), plan)
        fails = [(n, d) for n, ok, d, _c, _t in res["checks"]
                 if n == "copies map" and not ok]
        self.assertTrue(fails, res["checks"])
        self.assertIn("bar 2", fails[0][1])

    def test_transposed_copy_is_caught(self):
        plan = self._copies_plan({"of_bars": "1", "bars": "2",
                                  "voices": ["Vocal"]})
        res = copies.check_copies(parse(
            "V: Vocal\nD4 E4 F4 G4|E4 F4 G4 A4|A4 A4 A4 A4|Z|\n"
            "V: Ins\nZ|Z|Z|Z|\n"), plan)
        fails = [(n, d) for n, ok, d, _c, _t in res["checks"]
                 if n == "copies map" and not ok]
        self.assertTrue(fails, res["checks"])

    def test_declared_mutation_that_did_not_happen_fails(self):
        plan = self._copies_plan({"of_bars": "1", "bars": "2",
                                  "voices": ["Vocal"],
                                  "changes": [{"kind": "ornament",
                                               "bar": 2, "voice": "Vocal"}]})
        res = copies.check_copies(parse(
            "V: Vocal\nD4 E4 F4 G4|D4 E4 F4 G4|A4 A4 A4 A4|Z|\n"
            "V: Ins\nZ|Z|Z|Z|\n"), plan)
        fails = [(n, d) for n, ok, d, _c, _t in res["checks"]
                 if n == "copies map" and not ok]
        self.assertTrue(fails, res["checks"])
        self.assertIn("did not differ", fails[0][1])


class AlignmentTests(unittest.TestCase):
    def _align_plan(self, bars=4, **kw):
        p = dict(SMALL_PLAN)
        p["bars"] = bars
        p.update(kw)
        return p

    def test_note_deficit_one_warns(self):
        """Deficit of <= 1 against syllables warns (elision/merge)."""
        phrase_plan = {"lines": [
            {"line": 1, "bar_start": 1, "bar_end": 2, "syllables": 5},
        ]}
        score = parse("V: Vocal\nD4 E4 F4 G4|Z|\nV: Ins\nZ|Z|\n")
        res = alignment.check_alignment(
            score, self._align_plan(), phrase_plan,
            score_text=header() + "V: Vocal\nD4 E4 F4 G4|Z|\nV: Ins\nZ|Z|\n",
            recomputed_prosody={"syllables_per_line": [5],
                                "lines_text": ["يَا حَبيبي"]},
            calibration=CAL,
        )
        warns = [d for n, ok, d, c, _t in res["checks"]
                 if n == "line elision deficit" and not ok and c == "banded"]
        self.assertTrue(warns, res["checks"])

    def test_note_deficit_more_than_one_fails(self):
        """Deficit of more than 1 fails (exact)."""
        phrase_plan = {"lines": [
            {"line": 1, "bar_start": 1, "bar_end": 2, "syllables": 5},
        ]}
        score = parse("V: Vocal\nD4 E4 F4 G4|Z|\nV: Ins\nZ|Z|\n")
        res = alignment.check_alignment(
            score, self._align_plan(), phrase_plan,
            score_text=header() + "V: Vocal\nD4 E4 F4 G4|Z|\nV: Ins\nZ|Z|\n",
            recomputed_prosody={"syllables_per_line": [7],
                                "lines_text": ["يَا حَبيبي"]},
            calibration=CAL,
        )
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "line note deficit" and not ok and c == "exact"]
        self.assertTrue(fails, res["checks"])
        self.assertIn("deficit", fails[0])

    def test_sidecar_syllables_must_match_lyrics(self):
        """A hand-copied sidecar syllable count is an exact FAIL."""
        phrase_plan = {"lines": [
            {"line": 1, "bar_start": 1, "bar_end": 2, "syllables": 4},
        ]}
        score = parse("V: Vocal\nD4 E4 F4 G4|Z|\nV: Ins\nZ|Z|\n")
        res = alignment.check_alignment(
            score, self._align_plan(), phrase_plan,
            score_text=header() + "V: Vocal\nD4 E4 F4 G4|Z|\nV: Ins\nZ|Z|\n",
            recomputed_prosody={"syllables_per_line": [5],
                                "lines_text": ["يَا حَبيبي"]},
            calibration=CAL,
        )
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "sidecar syllables" and not ok and c == "exact"]
        self.assertTrue(fails, res["checks"])
        self.assertIn("sidecar 4", fails[0])

    def test_orphan_vocal_note_fails(self):
        """A vocal note outside every line window and vocalise_bars fails."""
        phrase_plan = {"lines": [
            {"line": 1, "bar_start": 1, "bar_end": 1, "syllables": 1},
        ], "vocalise_bars": []}
        # bar 2 has a vocal note not covered by line 1 (bar 1 only) -> orphan
        score = parse("V: Vocal\nD4 E4 F4 G4|A4 A4 A4 A4|\nV: Ins\nZ|Z|\n")
        res = alignment.check_alignment(
            score, self._align_plan(bars=2), phrase_plan,
            score_text=header() + "V: Vocal\nD4 E4 F4 G4|A4 A4 A4 A4|\nV: Ins\nZ|Z|\n",
            calibration=CAL,
        )
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "orphan vocal notes" and not ok and c == "exact"]
        self.assertTrue(fails, res["checks"])

    def test_vocalise_bars_prevents_orphan_false_positive(self):
        """Declared wordless bars keep a legitimate 'ah' from failing."""
        phrase_plan = {"lines": [
            {"line": 1, "bar_start": 1, "bar_end": 1, "syllables": 1},
        ], "vocalise_bars": "2"}
        score = parse("V: Vocal\nD4 E4 F4 G4|A4 A4 A4 A4|\nV: Ins\nZ|Z|\n")
        res = alignment.check_alignment(
            score, self._align_plan(bars=2), phrase_plan,
            score_text=header() + "V: Vocal\nD4 E4 F4 G4|A4 A4 A4 A4|\nV: Ins\nZ|Z|\n",
            calibration=CAL,
        )
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "orphan vocal notes" and not ok]
        self.assertFalse(fails, res["checks"])


class BindingTests(unittest.TestCase):
    def _bind_plan(self, **kw):
        return dict(SMALL_PLAN, bars=4, **kw)

    def test_section_plan_tiling_mismatch_fails(self):
        """section_plan must tile exactly 1-bars."""
        plan = self._bind_plan(arrangement={
            "section_plan": [{"bars": "1-3", "vocal_notes_per_bar": [0, 1],
                              "ins_notes_per_bar": [1, 2],
                              "ins_active_share": [0.5, 1.0]}],
            "ins_entries": [],
        })
        res = binding.check_binding(parse(
            "V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"), plan)
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "section plan tiling" and not ok]
        self.assertTrue(fails, res["checks"])

    def test_small_sample_answer_rate_has_no_verdict(self):
        """Fewer than 4 eligible phrases reports 'insufficient sample'."""
        plan = self._bind_plan(arrangement={
            "section_plan": [{
                "bars": "1-4",
                "vocal_notes_per_bar": [0, 4],
                "ins_notes_per_bar": [0, 0],
                "ins_active_share": [0, 0],
                "answer_rate": [0.5, 1.0],
            }],
            "ins_entries": [],
        })
        res = binding.check_binding(parse(
            "V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"), plan)
        answer_rows = [r for r in res["table"] if r["metric"] == "answer_rate"]
        self.assertTrue(answer_rows, res["table"])
        self.assertEqual(answer_rows[0]["verdict"], "insufficient sample")
        self.assertIn("insufficient sample", str(answer_rows[0]["measured"]))

    def test_deviation_assert_is_banded(self):
        """Deviation asserts follow the banded rule (WARN, FAIL under strict_shape)."""
        plan = self._bind_plan(deviations=[
            {"bars": "1-2", "channel": "density",
             "assert": {"metric": "vocal_notes_per_bar", "range": "1-2",
                        "op": ">=", "value": 0}}
        ])
        res = binding.check_binding(parse(
            "V: Vocal\nD4 E4 F4 G4|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"), plan)
        banded = [(c, t) for n, ok, d, c, t in res["checks"]
                  if n == "deviation 1 (vocal_notes_per_bar)"]
        self.assertTrue(banded, res["checks"])
        self.assertEqual(banded[0][0], "banded")

    def test_unverifiable_deviation_listed(self):
        """unverifiable: true with a reason is 'declared, not verifiable'."""
        plan = self._bind_plan(deviations=[
            {"bars": "1-2", "channel": "gap rate",
             "unverifiable": True,
             "reason": "renderer cannot be heard offline"}]
        )
        res = binding.check_binding(parse(
            "V: Vocal\nZ|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"), plan)
        unv = [d for n, ok, d, c, _t in res["checks"]
               if n == "deviation 1" and c == "unverifiable"]
        self.assertTrue(unv, res["checks"])
        self.assertIn("declared, not verifiable", unv[0])

    def test_boilerplate_string_deviation_fails(self):
        plan = self._bind_plan(deviations=[
            "plan generated from objective corpus priors",
        ])
        res = binding.check_binding(parse(
            "V: Vocal\nZ|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"), plan)
        fails = [d for n, ok, d, c, _t in res["checks"]
                 if n == "deviation 1" and not ok and c == "exact"]
        self.assertTrue(fails, res["checks"])

    def test_legacy_string_deviation_warns_without_plan_version(self):
        """Without plan_version a string deviation warns (migration rule)."""
        plan = dict(SMALL_PLAN)  # no plan_version
        plan.pop("plan_version", None)
        plan["deviations"] = ["some free-form note"]
        plan["bars"] = 4
        plan["arrangement"] = {
            "section_plan": [{"bars": "1-4", "vocal_notes_per_bar": [0, 1],
                              "ins_notes_per_bar": [1, 2],
                              "ins_active_share": [0.5, 1.0],
                              "answer_rate": [0.0, 1.0]}],
            "ins_entries": [],
        }
        res = binding.check_binding(parse(
            "V: Vocal\nZ|Z|Z|Z|\nV: Ins\nZ|Z|Z|Z|\n"), plan)
        warns = [d for n, ok, d, c, _t in res["checks"]
                 if n == "deviation 1" and not ok and c == "banded" and _t == "WARN"]
        self.assertTrue(warns, res["checks"])


if __name__ == "__main__":
    unittest.main()
