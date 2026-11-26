#!/usr/bin/env python3
"""Tests for the live meter and the read-only line views (0.9.0)."""
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
sys.path.insert(0, str(ROOT / "scripts"))
import checker  # noqa: E402
import live_meter  # noqa: E402


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd,
                          text=True, capture_output=True)


def make_session(cwd: Path, *, bars: int = 8) -> None:
    (cwd / "input").mkdir()
    (cwd / "input" / "lyrics.txt").write_text(
        (EXAMPLE / "lyrics.txt").read_text(encoding="utf-8"), encoding="utf-8")
    (cwd / "input" / "style.md").write_text(
        "Maqam Kurd\n[Intro | clean guitar]\n[Verse | voice]\n[Chorus | band]\n",
        encoding="utf-8")
    proc = run(cwd, "init", "--lyrics", "input/lyrics.txt", "--style",
               "input/style.md", "--tempo", "80", "--bars", str(bars),
               "--sections", "verse=2,chorus=4")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def line_spec(cwd: Path, number: int, note: str = "D4") -> tuple[str, str, int]:
    phrases = json.loads((cwd / "phrases.json").read_text(encoding="utf-8"))
    line = next(l for l in phrases["lines"] if int(l["line"]) == number)
    count = int(line["bar_end"]) - int(line["bar_start"]) + 1
    return " | ".join([note] * count), " | ".join(["Z"] * count), count


class LiveMeterTests(unittest.TestCase):
    def test_meter_reuses_checker_numbers(self):
        text = (EXAMPLE / "score.abc").read_text(encoding="utf-8")
        plan = json.loads((EXAMPLE / "plan.json").read_text(encoding="utf-8"))
        phrases = json.loads((EXAMPLE / "phrases.json").read_text(encoding="utf-8"))
        score = checker.parse(text)
        _, measured = checker.check(score, plan, phrase_plan=phrases,
                                    lyrics_text=None, waive_lyrics=True,
                                    score_text=text)
        payload = live_meter.measure(text, plan, phrases)
        self.assertEqual(payload["register_mean"], measured["register_mean"])
        self.assertEqual(payload["repeated_share"], measured["repeated_share"])
        self.assertEqual(payload["distinct_durations"], measured["distinct_durations"])
        self.assertEqual(payload["ties"], measured["ties"])
        self.assertIsNotNone(payload["projected"])
        self.assertIn("score", live_meter.format_meter(payload))

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            make_session(cwd)
            vocal, ins, _ = line_spec(cwd, 1, "D4 F4 G4 A4")
            before_score = (cwd / "score.abc").read_bytes()
            before_state = (cwd / "score_state.json").read_bytes()
            proc = run(cwd, "line", "1", "--vocal", vocal, "--ins", ins, "--dry-run")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("meter line 1", proc.stdout)
            self.assertIn("dry run", proc.stdout)
            self.assertEqual((cwd / "score.abc").read_bytes(), before_score)
            self.assertEqual((cwd / "score_state.json").read_bytes(), before_state)

    def test_patch_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            make_session(cwd)
            before = (cwd / "score.abc").read_bytes()
            proc = run(cwd, "patch", "2", "--vocal", "D16", "--ins", "Z", "--dry-run")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("meter bars 2-2", proc.stdout)
            self.assertEqual((cwd / "score.abc").read_bytes(), before)

    def test_guard_refuses_a_deficit(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            make_session(cwd)
            vocal, ins, count = line_spec(cwd, 1, "D16")
            before = (cwd / "score.abc").read_bytes()
            proc = run(cwd, "line", "1", "--vocal", vocal, "--ins", ins, "--guard")
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("REFUSED (--guard)", proc.stderr)
            self.assertIn("deficit", proc.stderr)
            self.assertIn("gap", proc.stderr)
            self.assertEqual((cwd / "score.abc").read_bytes(), before)

    def test_lint_reports_overlap(self):
        text = """X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
V: Vocal
A8 z8|Z|
V: Ins
A8 z8|Z|
"""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "score.abc").write_text(text, encoding="utf-8")
            proc = run(cwd, "lint")
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("bar 1", proc.stdout)
            self.assertIn("overlaps", proc.stdout)

    def test_release_dry_run_keeps_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for name in ("score.abc", "plan.json", "phrases.json"):
                (cwd / name).write_bytes((EXAMPLE / name).read_bytes())
            (cwd / "input").mkdir()
            (cwd / "input" / "lyrics.txt").write_bytes((EXAMPLE / "lyrics.txt").read_bytes())
            (cwd / "score_state.json").write_text('{"phase": "expand"}\n', encoding="utf-8")
            (cwd / "state.json").write_text('{"phase": "expand"}\n', encoding="utf-8")
            before = ((cwd / "score_state.json").read_bytes(),
                      (cwd / "state.json").read_bytes())
            proc = run(cwd, "release", "--dry-run")
            self.assertIn(proc.returncode, (0, 1), proc.stdout + proc.stderr)
            self.assertEqual(((cwd / "score_state.json").read_bytes(),
                              (cwd / "state.json").read_bytes()), before)

    def test_init_warns_on_form_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "input").mkdir()
            (cwd / "input" / "lyrics.txt").write_bytes((EXAMPLE / "lyrics.txt").read_bytes())
            (cwd / "input" / "style.md").write_text("Maqam Kurd\n", encoding="utf-8")
            proc = run(cwd, "init", "--lyrics", "input/lyrics.txt", "--style",
                       "input/style.md", "--tempo", "80", "--bars", "8")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("FORM BUDGET:", proc.stdout)
            self.assertIn("--force --bars", proc.stdout)


class ReadOnlyViewTests(unittest.TestCase):
    def test_align(self):
        proc = run(ROOT, "align", "--score", "example/score.abc",
                   "--plan", "example/plan.json", "--phrases", "example/phrases.json",
                   "--lines", "1-2")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("line 1", proc.stdout)
        self.assertIn("tail", proc.stdout)

    def test_roll(self):
        proc = run(ROOT, "view", "--roll", "--bars", "2-4",
                   "--score", "example/score.abc")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("roll bars 2-4", proc.stdout)
        self.assertIn("#", proc.stdout)
        self.assertNotIn("bar 5", proc.stdout)

    def test_contour(self):
        proc = run(ROOT, "view", "--contour", "--score", "example/score.abc",
                   "--phrases", "example/phrases.json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("contour", proc.stdout)
        self.assertIn("line", proc.stdout)

    def test_explain_metric(self):
        proc = run(ROOT, "explain-metric", "end")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("relative to the tonic", proc.stdout)


if __name__ == "__main__":
    unittest.main()
