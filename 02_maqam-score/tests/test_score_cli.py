#!/usr/bin/env python3
"""End-to-end tests for the line-based workflow in score_cli.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "score_cli.py"
EXAMPLE = ROOT / "example"


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd,
                          text=True, capture_output=True)


class ScoreCliTest(unittest.TestCase):
    def test_lint_collects_every_error(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import abc_tools
        text = (EXAMPLE / "score.abc").read_text(encoding="utf-8")
        bad = text.replace("A,2 A,2 A,2 C2 A,2 A,2 G,2 A,2|",
                           "A,2 A,2 A,2 C2 A,2 A,2 G,2|", 1)
        bad = bad.replace("F2 F2 A8 G2 F2|", "F2 F2 A8 G2|", 1)
        errors = abc_tools.lint_text(bad)
        self.assertGreaterEqual(len(errors), 2, errors)
        self.assertTrue(any(e.get("bar") for e in errors))

    def test_init_line_core_check_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "input").mkdir()
            (cwd / "input" / "lyrics.txt").write_text(
                (EXAMPLE / "lyrics.txt").read_text(encoding="utf-8"), encoding="utf-8")
            (cwd / "input" / "style.md").write_text(
                "Maqam Kurd\n[Intro | clean guitar]\n[Verse | voice]\n[Chorus | band]\n",
                encoding="utf-8")
            proc = run(cwd, "init", "--lyrics", "input/lyrics.txt", "--style",
                       "input/style.md", "--tempo", "80", "--bars", "8",
                       "--sections", "verse=2,chorus=4")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            plan = json.loads((cwd / "plan.json").read_text(encoding="utf-8"))
            phrases = json.loads((cwd / "phrases.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["bars"], 8)
            self.assertEqual(plan["key"], "Dm")
            self.assertEqual(plan["maqam"]["name"], "kurd")
            self.assertTrue((cwd / "state.json").exists())

            # Write every lyric line with a simple two-bar cell.
            for line in phrases["lines"]:
                count = int(line["bar_end"]) - int(line["bar_start"]) + 1
                vocal = " | ".join(["D:4 F:2 G:2 z2"] * count)
                ins = " | ".join(["Z"] * count)
                proc = run(cwd, "line", str(line["line"]), "--vocal", vocal, "--ins", ins)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            proc = run(cwd, "lint")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            proc = run(cwd, "core", "--snapshot", "--bars", "8")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            (cwd / "core_review.md").write_text(
                "1. bar 2: cell stated.\n2. bar 3: consequent closes.\n"
                "3. bar 4: chorus lifts.\n4. bar 6: outro rest.\n5. bar 8: final rest.\n",
                encoding="utf-8")
            proc = run(cwd, "core", "--check")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            proc = run(cwd, "check", "--bars", "2-3")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("section report", proc.stdout)

            proc = run(cwd, "plan", "lint")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("placeholder", proc.stdout)

            proc = run(cwd, "seed")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((cwd / "seed.abc").exists())
            proc = run(cwd, "seed-check")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_init_without_sections_allocates_absolute_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "input").mkdir()
            (cwd / "input" / "lyrics.txt").write_text(
                (EXAMPLE / "lyrics.txt").read_text(encoding="utf-8"), encoding="utf-8")
            (cwd / "input" / "style.md").write_text("Maqam Kurd\n", encoding="utf-8")
            proc = run(cwd, "init", "--lyrics", "input/lyrics.txt", "--style",
                       "input/style.md", "--tempo", "80", "--bars", "16")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            phrases = json.loads((cwd / "phrases.json").read_text(encoding="utf-8"))
            first = phrases["lines"][0]
            self.assertIn("bar_start", first)
            count = int(first["bar_end"]) - int(first["bar_start"]) + 1
            vocal = " | ".join(["D:4 F:2 G:2 z2"] * count)
            proc = run(cwd, "line", "1", "--vocal", vocal,
                       "--ins", " | ".join(["Z"] * count))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_bar_padding_and_colon_syntax(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import score_cli
        plan = {"meter": "4/4", "unit": "1/16", "key": "Dm"}
        self.assertEqual(score_cli.pad_bar("D:4 F:2 G:2", plan), "D4 F2 G2 z8")
        self.assertEqual(score_cli.pad_bar("D4 F2 G2 z8", plan), "D4 F2 G2 z8")
        with self.assertRaises(ValueError):
            score_cli.pad_bar("D:20", plan)


    def test_plan_set_rejects_unknown_top_level_key(self):
        """B6: `plan set ins_entries` used to be accepted and did nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "plan.json").write_text(
                (EXAMPLE / "plan.json").read_text(encoding="utf-8"), encoding="utf-8")
            (cwd / "phrases.json").write_text(
                (EXAMPLE / "phrases.json").read_text(encoding="utf-8"), encoding="utf-8")
            bad = run(cwd, "plan", "set", "ins_entries=[15]")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("arrangement.ins_entries", bad.stderr)
            good = run(cwd, "plan", "set", "arrangement.ins_entries=[15]")
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(
                json.loads((cwd / "plan.json").read_text(encoding="utf-8"))
                ["arrangement"]["ins_entries"], [15])
            self.assertEqual(run(cwd, "plan", "set", "register.mean=72").returncode, 0)

    def test_seed_chord_keeps_accidental(self):
        """B7: a flat/sharp root used to map to the natural letter's chord."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import score_cli
        self.assertEqual(score_cli._chord_for_bar("_e4 c4 A8", "Am"), "Eb")
        self.assertEqual(score_cli._chord_for_bar("^f4 A12", "Am"), "F#")
        self.assertEqual(score_cli._chord_for_bar("=e8 a8", "Am"), "Em")
        self.assertEqual(score_cli._chord_for_bar("A,16", "Am"), "Am")
        self.assertIsNone(score_cli._chord_for_bar("Z", "Am"))

    def test_init_next_action_is_the_whole_draft_workflow(self):
        """B5: init must not tell the agent to use the 0.9 core/line workflow."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "input").mkdir()
            (cwd / "input" / "lyrics.txt").write_text(
                (EXAMPLE / "lyrics.txt").read_text(encoding="utf-8"), encoding="utf-8")
            (cwd / "input" / "style.md").write_text(
                "Maqam Kurd\n[Intro | clean guitar]\n[Verse | voice]\n[Chorus | band]\n",
                encoding="utf-8")
            proc = run(cwd, "init", "--lyrics", "input/lyrics.txt", "--style",
                       "input/style.md", "--tempo", "80", "--bars", "8",
                       "--sections", "verse=2,chorus=4")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            blob = (proc.stdout + (cwd / "score_state.json").read_text(encoding="utf-8")
                    + (cwd / "STATE.md").read_text(encoding="utf-8"))
            self.assertNotIn("core --snapshot", blob)
            self.assertNotIn("first 16 bars", blob)
            self.assertIn("scorecard.py", blob)


if __name__ == "__main__":
    unittest.main()
