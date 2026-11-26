#!/usr/bin/env python3
"""Read-only views: an ASCII piano roll and a per-line contour line.

These are sight-reading aids for the composer, not measurements and not gates.
The roll uses one column per L-unit, the same unit the writer already counts.

Usage:
    score_cli.py view --roll --bars 3-5
    score_cli.py view --contour
"""
from __future__ import annotations

import math

import checker

PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def pitch_name(midi: int) -> str:
    return f"{PC_NAME[int(midi) % 12]}{int(midi) // 12 - 1}"


def parse_bar_range(spec: str | None, n_bars: int, *, default_bars: int = 16,
                    max_bars: int = 32) -> tuple[int, int]:
    if not spec:
        return 1, min(n_bars, default_bars)
    if "-" in spec:
        lo, hi = (int(x) for x in spec.split("-", 1))
    else:
        lo = hi = int(spec)
    lo = max(1, lo)
    hi = min(n_bars, hi)
    if lo > hi:
        raise ValueError(f"empty bar range {spec!r}")
    if hi - lo + 1 > max_bars:
        raise ValueError(f"range {lo}-{hi} is wider than {max_bars} bars; narrow it")
    return lo, hi


def roll(text: str, bars_spec: str | None = None) -> str:
    score = checker.parse(text)
    lo, hi = parse_bar_range(bars_spec, score.n_bars)
    vocal = score.notes_of("Vocal")
    if not vocal:
        return f"roll bars {lo}-{hi}: no vocal notes"
    in_range = [n for n in vocal
                if score.bar_starts[lo - 1] <= n.onset < score.bar_starts[hi]]
    if not in_range:
        return f"roll bars {lo}-{hi}: no vocal notes"
    pitches = sorted({n.pitch for n in in_range})
    min_p, max_p = min(pitches), max(pitches)
    span_start = float(score.bar_starts[lo - 1])
    widths = [int(score.bar_units[b - 1]) for b in range(lo, hi + 1)]
    # A sounding note may cross a bar line after the runtime resolves ties.
    cells: dict[int, list[list[str]]] = {
        p: [["."] * width for width in widths] for p in range(min_p, max_p + 1)
    }
    for note in in_range:
        u0 = int(math.ceil(note.onset - span_start - 1e-9))
        u1 = int(math.ceil(note.onset + note.dur - span_start - 1e-9))
        for u in range(max(0, u0), min(sum(widths), u1)):
            # Locate the bar and the column inside it.
            acc = 0
            for bi, width in enumerate(widths):
                if u < acc + width:
                    cells[note.pitch][bi][u - acc] = "#"
                    break
                acc += width
    header_cells = []
    for b, width in zip(range(lo, hi + 1), widths):
        label = str(b)[:width].center(width)
        header_cells.append(label)
    lines = ["roll bars %d-%d (1 char = 1 L-unit; # = sounding)" % (lo, hi),
             "      |" + "|".join(header_cells) + "|"]
    for p in range(max_p, min_p - 1, -1):
        row = "".join("".join(chars) + "|" for chars in cells[p])
        lines.append(f"{pitch_name(p):>5} |{row}")
    lines.append("      |" + "|".join("-" * w for w in widths) + "|")
    return "\n".join(lines)


def contour(text: str, phrases: dict) -> str:
    score = checker.parse(text)
    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    out = ["contour (per lyric line; pitch names are absolute)"]
    for line in (phrases or {}).get("lines", []):
        start, end = int(line["bar_start"]), int(line["bar_end"])
        notes = [n for n in vocal if start - 1 <= n.bar <= end - 1]
        if not notes:
            out.append(f"line {line.get('line')} bars {start}-{end}: empty")
            continue
        first, last = notes[0].pitch, notes[-1].pitch
        low, high = min(n.pitch for n in notes), max(n.pitch for n in notes)
        delta = last - first
        if high - low <= 2:
            shape = "flat"
        elif delta >= 3:
            shape = "up"
        elif delta <= -3:
            shape = "down"
        else:
            shape = "wave"
        intervals = [b.pitch - a.pitch for a, b in zip(notes, notes[1:])]
        repeats = (sum(1 for i in intervals if i == 0) / len(intervals)) if intervals else 0.0
        out.append(
            f"line {line.get('line'):>2} bars {start}-{end:<2} notes {len(notes):>2} "
            f"{pitch_name(first)}->{pitch_name(last)} {shape:<4} "
            f"range {pitch_name(low)}-{pitch_name(high)} repeats {repeats:.0%}"
        )
    return "\n".join(out)
