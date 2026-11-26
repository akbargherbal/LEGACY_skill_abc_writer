#!/usr/bin/env python3
"""Per-line phrase table for a two-voice score.

This is the table the aggregate `craft.py` report cannot show: for every lyric
line, the bar range, the rhythm cell, the rest before/after, the unbroken span,
the register, the repeated-pitch share, the leaps, and the cadence degree.

It is deliberately **report-only**. It does not fail; `quality.py` turns the
objective targets into PASS/FAIL, and `repair.py` turns the failures into bars.

Usage:
    from phrase_table import build
    table = build(parsed_score, phrases_payload)
"""
from __future__ import annotations

import statistics as st
from fractions import Fraction

PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _bar_index(bars: list[dict], onset: Fraction) -> int:
    """0-based bar index for an onset (bars are sorted by start)."""
    lo, hi = 0, len(bars) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if bars[mid]["start"] <= onset:
            lo = mid
        else:
            hi = mid - 1
    return max(0, min(len(bars) - 1, lo))


def _split_phrases(vocal: list[dict], bars: list[dict]) -> list[list[dict]]:
    """The craft.py phrase split: section change or a rest of at least one beat."""
    out: list[list[dict]] = []
    cur: list[dict] = []
    prev_end = None
    for note in vocal:
        bi = _bar_index(bars, note["onset"])
        threshold = bars[bi]["length"] / 4
        split = bool(cur) and (
            note["section"] != cur[-1]["section"]
            or (prev_end is not None and note["onset"] - prev_end >= threshold)
        )
        if split:
            out.append(cur)
            cur = []
        cur.append(note)
        prev_end = note["onset"] + note["dur"]
    if cur:
        out.append(cur)
    return [p for p in out if len(p) >= 3]


def _pc(name: str) -> int:
    key = name.strip().replace("♭", "b").replace("♯", "#")
    # Accept a key such as Dm, F#m, Bb, or a bare pitch class.
    import re
    m = re.match(r"^([A-Ga-g])([#b]?)", key)
    if not m:
        raise ValueError(f"cannot read pitch class {name!r}")
    key = (m.group(1).upper() + m.group(2))
    table = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
             "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
             "A#": 10, "Bb": 10, "B": 11}
    return table[key]


def _defs_from_phrases(phrases: dict) -> list[dict]:
    lines = phrases.get("lines") if isinstance(phrases, dict) else None
    if not isinstance(lines, list):
        return []
    out = []
    for i, line in enumerate(lines, 1):
        if not isinstance(line, dict):
            continue
        try:
            start = int(line["bar_start"])
            end = int(line["bar_end"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({
            "line": int(line.get("line", i)),
            "section": str(line.get("section", "")),
            "syllables": line.get("syllables"),
            "bar_start": start,
            "bar_end": end,
            "pause_after_s": line.get("pause_after_s"),
        })
    return out


def _defs_from_score(vocal: list[dict], bars: list[dict]) -> list[dict]:
    groups = _split_phrases(vocal, bars)
    out = []
    for i, group in enumerate(groups, 1):
        out.append({
            "line": i,
            "section": group[0]["section"],
            "syllables": None,
            "bar_start": group[0]["bar"] + 1,
            "bar_end": group[-1]["bar"] + 1,
            "pause_after_s": None,
        })
    return out


def build(parsed: dict, phrases: dict | None = None) -> dict:
    """Return {rows, summary} for every lyric line (or detected phrase)."""
    vocal = sorted(parsed["voices"]["Vocal"].notes, key=lambda n: n["onset"])
    bars = parsed["voices"]["Vocal"].bars
    unit = parsed["unit"]
    tempo = parsed["tempo"]
    # _craft_calibrate onsets/durations are in quarter notes; one quarter is
    # 60/tempo seconds. `unit` is only the quarter-per-L-unit scale for cells.
    unit_seconds = 60.0 / tempo
    tonic = _pc(parsed["key"])

    defs = _defs_from_phrases(phrases or {})
    if not defs:
        defs = _defs_from_score(vocal, bars)

    rows: list[dict] = []
    n_bars = len(bars)
    missing = 0
    for d in defs:
        start, end = d["bar_start"], d["bar_end"]
        if start > n_bars or end > n_bars:
            missing += 1
            rows.append({**d, "notes": None, "status": "not written",
                         "bars": f"{start}-{end}", "end_name": None})
            continue
        notes = [n for n in vocal if start - 1 <= n["bar"] <= end - 1]
        if not notes:
            rows.append({**d, "notes": 0, "status": "empty",
                         "bars": f"{start}-{end}", "end_name": None})
            continue
        first, last = notes[0], notes[-1]
        bar0 = bars[min(len(bars) - 1, start - 1)]
        intervals = [b["pitch"] - a["pitch"] for a, b in zip(notes, notes[1:])]
        durations = [int(round(float(n["dur"] / unit))) for n in notes]
        rows.append({
            **d,
            "bars": f"{start}-{end}",
            "notes": len(notes),
            "start_beat": round(float(first["onset"] - bar0["start"]) + 1, 2),
            "rhythm_cell": "-".join(str(x) for x in durations),
            "rest_before_s": None,
            "rest_after_s": None,
            "unbroken_s": round(float(last["onset"] + last["dur"] - first["onset"]) * unit_seconds, 2),
            "register_mean": round(st.mean(n["pitch"] for n in notes), 1),
            "repeated": round(sum(1 for i in intervals if i == 0) / len(intervals), 3) if intervals else None,
            "leaps": round(sum(1 for i in intervals if abs(i) >= 5) / len(intervals), 3) if intervals else None,
            "start_pitch": first["pitch"],
            "end_pitch": last["pitch"],
            "end_pitch_name": f"{PC_NAME[last['pitch'] % 12]}{last['pitch'] // 12 - 1}",
            "end_degree": (last["pitch"] - tonic) % 12,
            "end_name": PC_NAME[(last["pitch"] - tonic) % 12],
        })

    # Actual gaps between neighbouring rows: this is the ear's rest hierarchy.
    for i, row in enumerate(rows):
        if not row.get("notes"):
            continue
        notes = [n for n in vocal if row["bar_start"] - 1 <= n["bar"] <= row["bar_end"] - 1]
        first, last = notes[0], notes[-1]
        if i > 0:
            prev_notes = [n for n in vocal
                          if rows[i - 1]["bar_start"] - 1 <= n["bar"] <= rows[i - 1]["bar_end"] - 1]
            if prev_notes:
                prev_last = prev_notes[-1]
                row["rest_before_s"] = round(
                    max(0.0, float(first["onset"] - (prev_last["onset"] + prev_last["dur"])) * unit_seconds), 2)
        if i + 1 < len(rows):
            next_notes = [n for n in vocal
                          if rows[i + 1]["bar_start"] - 1 <= n["bar"] <= rows[i + 1]["bar_end"] - 1]
            if next_notes:
                next_first = next_notes[0]
                row["rest_after_s"] = round(
                    max(0.0, float(next_first["onset"] - (last["onset"] + last["dur"])) * unit_seconds), 2)

    detected = _split_phrases(vocal, bars)
    return {
        "rows": rows,
        "summary": {
            "lyric_lines": len(rows),
            "detected_phrases": len(detected),
            "merged_lines": max(0, len(rows) - len(detected)),
            "bars": len(bars),
            "tempo": tempo,
            "missing_lines": missing,
            "complete": missing == 0,
        },
    }
