#!/usr/bin/env python3
"""Explain a two-voice ABC parse error in plain language.

The vendored parser (`abc_tools.py`) is the contract; it is not edited. This
script imports it, catches the error, and adds the context a composer needs:

- which `V:` block has the wrong number of bars;
- blank lines (the parser reads them as end-of-tune);
- unsupported durations and the legal list;
- ties that enter a rest or change pitch.

Usage:
    python3 abc_doctor.py score.abc [--json doctor.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abc_tools  # noqa: E402

ALLOWED = "1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48"


def _groups(lines: list[str]) -> list[dict]:
    groups = []
    current = None
    seen_k = False
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("K:"):
            seen_k = True
            continue
        if not seen_k:
            continue
        if s.startswith("V:"):
            name = s[2:].strip().split()[0] if s[2:].strip() else "?"
            current = name
            continue
        if s.startswith("%") or s.startswith("M:") or s.startswith("L:") or s.startswith("Q:"):
            continue
        if not s.endswith("|"):
            continue
        bars = [b.strip() for b in s[:-1].split("|") if b.strip()]
        expanded = 0
        for b in bars:
            m = re.fullmatch(r"Z([2-9])?", b)
            expanded += int(m.group(1) or 1) if m else 1
        if current:
            groups.append({"line": i, "voice": current, "bars": expanded})
    return groups


def _group_mismatches(groups: list[dict]) -> list[dict]:
    out = []
    # Pair consecutive Vocal/Ins lines; a group starts at Vocal.
    i = 0
    while i + 1 < len(groups):
        a, b = groups[i], groups[i + 1]
        if a["voice"] == "Vocal" and b["voice"] == "Ins":
            if a["bars"] != b["bars"]:
                out.append({"vocal_line": a["line"], "ins_line": b["line"],
                            "vocal_bars": a["bars"], "ins_bars": b["bars"]})
            i += 2
        else:
            i += 1
    return out


def diagnose(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    blanks = [i for i, line in enumerate(lines, 1) if not line.strip()]
    groups = _groups(lines)
    mismatches = _group_mismatches(groups)
    try:
        score = abc_tools.parse(text)
    except abc_tools.AbcError as exc:
        error = str(exc)
        hints = []
        if blanks:
            hints.append(f"blank line(s) at {blanks}; the parser reads a blank line as end-of-tune")
        if mismatches:
            hints.append("block bar counts differ: " + ", ".join(
                f"Vocal line {m['vocal_line']} has {m['vocal_bars']} bars, "
                f"Ins line {m['ins_line']} has {m['ins_bars']}" for m in mismatches))
        if "duration" in error.lower():
            hints.append(f"legal durations are {ALLOWED}; a 10-unit rest is z8z2, a 5-unit note is 3-2")
        if "tie" in error.lower():
            hints.append("a tie must join the same pitch, must not enter a rest, and must resolve before the end")
        if "V:" in error or "voice" in error.lower():
            hints.append("each group must be V: Vocal then V: Ins, with the same bar count")
        if "bar" in error.lower() and "sum" in error.lower():
            hints.append("every bar must sum to its meter; count rests as well as notes")
        return {"ok": False, "path": str(path), "error": error,
                "blanks": blanks, "groups": groups, "mismatches": mismatches,
                "hints": hints}
    return {"ok": True, "path": str(path), "bars": len(score.voices["Vocal"].bars),
            "vocal_notes": len(score.voices["Vocal"].notes),
            "ins_notes": len(score.voices["Ins"].notes),
            "groups": groups, "mismatches": mismatches,
            "hints": ["parse OK; no dialect problem"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    try:
        payload = diagnose(args.score)
    except OSError as exc:
        payload = {"ok": False, "path": str(args.score), "error": str(exc), "hints": []}
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    print(f"{'OK' if payload['ok'] else 'FAIL'} {args.score}")
    if payload.get("error"):
        print(f"  {payload['error']}")
    for hint in payload.get("hints", []):
        print(f"  - {hint}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
