#!/usr/bin/env python3
"""Syllable -> note projection, report only.

The score has no `w:` lines, so the only honest way to show where a melisma
lands is a positional projection: one note per syllable in order, and any
surplus notes printed as a named tail. The header says it is a heuristic. It is
not a gate and it does not claim the text alignment is known.

Usage:
    score_cli.py align --lines 3-6
"""
from __future__ import annotations

import alignment
import checker

PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def pitch_name(midi: int) -> str:
    return f"{PC_NAME[int(midi) % 12]}{int(midi) // 12 - 1}"


def parse_lines(spec: str | None, count: int) -> list[int]:
    if not spec:
        return list(range(1, count + 1))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(part))
    return sorted({x for x in out if 1 <= x <= count})


def _note_label(note, ties: set[float]) -> str:
    label = pitch_name(note.pitch)
    if round(note.onset, 4) in ties:
        label += "~"
    return label


def project(score_text: str, plan: dict, phrases: dict,
            lines_spec: str | None = None) -> dict:
    score = checker.parse(score_text)
    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    tie_onsets = {round(t.get("onset", -1), 4)
                  for t in alignment._vocal_tie_groups(score_text, score)}
    defs = list((phrases or {}).get("lines", []))
    wanted = set(parse_lines(lines_spec, len(defs)))
    rows = []
    for line in defs:
        number = int(line.get("line", 0))
        if number not in wanted:
            continue
        start, end = int(line["bar_start"]), int(line["bar_end"])
        notes = [n for n in vocal if start - 1 <= n.bar <= end - 1]
        syllables = line.get("syllables")
        syllables = int(syllables) if syllables is not None else None
        row = {
            "line": number,
            "bars": f"{start}-{end}",
            "syllables": syllables,
            "notes": len(notes),
            "status": "ok",
            "groups": [],
            "tail": [],
            "elided": [],
        }
        if not notes:
            row["status"] = "empty"
            rows.append(row)
            continue
        if syllables is None:
            syllables = len(notes)
        labels = [_note_label(n, tie_onsets) for n in notes]
        if len(notes) <= syllables:
            # One note per syllable; the unmet syllables have no written note.
            for i, label in enumerate(labels, 1):
                row["groups"].append((i, i, label))
            if len(notes) < syllables:
                row["status"] = "deficit"
                row["elided"] = list(range(len(notes) + 1, syllables + 1))
        else:
            body = syllables
            for i in range(body):
                row["groups"].append((i + 1, i + 1, labels[i]))
            row["tail"] = labels[body:]
            row["status"] = "tail"
        rows.append(row)
    return {"rows": rows, "heuristic": True}


def format_projection(payload: dict) -> str:
    out = ["align (positional projection: one note per syllable; surplus notes are a cadence tail)"]
    for row in payload.get("rows", []):
        if row.get("status") == "empty":
            out.append(f"line {row['line']} bars {row['bars']}: no vocal notes")
            continue
        head = (f"line {row['line']} bars {row['bars']}  "
                f"{row['syllables']} syl / {row['notes']} notes")
        if row.get("tail"):
            head += f"  +{len(row['tail'])} tail"
        if row.get("elided"):
            head += f"  elided {row['elided'][0]}-{row['elided'][-1]}"
        out.append(head)
        # Five syllables per line keeps the projection readable in a terminal.
        chunk: list[tuple[int, int, str]] = []
        for group in row.get("groups", []):
            chunk.append(group)
            if len(chunk) == 5:
                out.append("  " + ", ".join(f"{a}:{label}" for a, _, label in chunk))
                chunk = []
        if chunk:
            out.append("  " + ", ".join(f"{a}:{label}" for a, _, label in chunk))
        if row.get("tail"):
            out.append("  tail on last syllable: " + " ".join(row["tail"]))
        if row.get("elided"):
            out.append("  no written note for syllables " + ", ".join(str(x) for x in row["elided"]))
    return "\n".join(out)
