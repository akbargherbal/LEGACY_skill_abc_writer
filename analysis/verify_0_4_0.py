#!/usr/bin/env python3
"""0.4.0 acceptance harness.

Checks the things the release notes claim, without listening:

1. the bundled example passes --strict-style + --strict-shape + phrases;
2. the phrase sidecar can fail a missing line-end pause;
3. the 2026-11-23 mediocre score still fails the three hard shape guards;
4. SKILL.md's plan template no longer carries that run's frame (78 bars,
   361 syllables, 74 BPM, or the four deviation ranges);
5. the 177-track corpus still parses and passes the nine hard guards, when the
   corpus path is available.

Usage:
    python3 analysis/verify_0_4_0.py
    CORPUS=~/.../five_stars python3 analysis/verify_0_4_0.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "02_maqam-score"
CHECKER = SKILL / "scripts" / "checker.py"
EXAMPLE_PLAN = SKILL / "example" / "plan.json"
EXAMPLE_SCORE = SKILL / "example" / "score.abc"
EXAMPLE_PHRASES = SKILL / "example" / "phrases.json"
MEDIOCRE = ROOT / "analysis" / "eval" / "inbox" / "claude_session_02" / "mediocre.abc"
MEDIOCRE_PLAN = (
    ROOT
    / "analysis"
    / "eval"
    / "runs"
    / "2026-11-23-claude-session-01"
    / "output"
    / "plan_final.json"
)
DEFAULT_CORPUS = (
    Path.home()
    / "Jupyter_Notebooks"
    / "OpenCode"
    / "arabmaqamrock"
    / "datasets"
    / "five_stars"
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT)


def check_example() -> tuple[bool, str]:
    result = run(
        sys.executable,
        str(CHECKER),
        str(EXAMPLE_SCORE),
        "--plan",
        str(EXAMPLE_PLAN),
        "--phrases",
        str(EXAMPLE_PHRASES),
        "--require-final-rest",
        "--strict-style",
    )
    ok = result.returncode == 0 and "0 warning(s)" in result.stdout
    return ok, "example strict shape/style + phrases"


def check_phrase_failure() -> tuple[bool, str]:
    data = json.loads(EXAMPLE_PHRASES.read_text(encoding="utf-8"))
    data["lines"][0]["pause_after_s"] = 99
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(data, handle)
        path = handle.name
    try:
        result = run(
            sys.executable,
            str(CHECKER),
            str(EXAMPLE_SCORE),
            "--plan",
            str(EXAMPLE_PLAN),
            "--phrases",
            path,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    ok = result.returncode != 0 and "phrase plan" in result.stdout
    return ok, "phrase sidecar rejects a missing line-end pause"


def check_mediocre() -> tuple[bool, str]:
    if not MEDIOCRE.is_file() or not MEDIOCRE_PLAN.is_file():
        return True, "old mediocre score (artifact absent; skipped)"
    plan = json.loads(MEDIOCRE_PLAN.read_text(encoding="utf-8"))
    plan["strict_shape"] = True
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(plan, handle)
        path = handle.name
    try:
        result = run(
            sys.executable,
            str(CHECKER),
            str(MEDIOCRE),
            "--plan",
            path,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    needed = ("unbroken singing", "repeated notes", "phrase endings")
    ok = result.returncode != 0 and all(name in result.stdout for name in needed)
    return ok, "old mediocre score still fails unbroken/repeated/endings"


def check_template() -> tuple[bool, str]:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    start = text.index("### 3.2 Plan")
    end = text.index("### 3.3 Material", start)
    block = text[start:end]
    forbidden = ('"bars": 78', '"tempo": 74', "361", "5-58", "34-38", "66-78")
    hits = [item for item in forbidden if item in block]
    return not hits, "plan template has no session-01 frame" + (
        f" (found {hits})" if hits else ""
    )


def check_corpus() -> tuple[bool, str]:
    corpus = Path(os.environ.get("CORPUS", DEFAULT_CORPUS))
    if not corpus.is_dir():
        return True, f"177 corpus (absent: {corpus}; skipped)"
    result = run(
        sys.executable,
        str(ROOT / "analysis" / "test_checker_corpus.py"),
        "--corpus",
        str(corpus),
    )
    ok = result.returncode == 0
    return ok, "177 corpus parse + hard gates"


def main() -> int:
    checks = [
        check_example(),
        check_phrase_failure(),
        check_mediocre(),
        check_template(),
        check_corpus(),
    ]
    failed = 0
    for ok, label in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += not ok
    print(f"\n{'PASS' if failed == 0 else 'FAIL'}  {failed} acceptance check(s) failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
