"""The remix transform vocabulary and its exact matching representation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import RemixError

FRAGMENT = re.compile(r"^(?:first|last)-([0-9]+)-notes$")
FRAGMENT_RANGE = re.compile(r"^([0-9]+)-([0-9]+)$")
SCALE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)x?$")


@dataclass
class Expected:
    pitches: list[int]
    durations: list[float]
    intervals: list[int]
    duration_ratios: list[float]
    contour: list[str]
    ignore_pitch: bool = False
    ignore_intervals: bool = False
    literal: bool = True
    ops: list[str] = field(default_factory=list)


def _parse_number(text: str, transform: str) -> float:
    try:
        return float(text)
    except ValueError as error:
        raise RemixError(f"invalid {transform} value: {text!r}") from error


def _ratios(durations: list[float]) -> list[float]:
    positive = [value for value in durations if value > 0]
    if not positive:
        return []
    unit = min(positive)
    return [round(value / unit, 6) for value in durations]


def contour(intervals: list[int]) -> list[str]:
    tokens = []
    for interval in intervals:
        if interval == 0:
            tokens.append("R")
            continue
        size = abs(interval)
        if size <= 2:
            token = "1"
        elif size <= 4:
            token = "2"
        else:
            token = "3"
        tokens.append(("u" if interval > 0 else "d") + token)
    return tokens


def apply_transforms(notes: list[tuple[int, float]], transforms: list[str]) -> Expected:
    pitches = [int(pitch) for pitch, _duration in notes]
    durations = [float(duration) for _pitch, duration in notes]
    ops: list[str] = []
    ignore_pitch = False
    ignore_intervals = False
    literal = True

    for raw in transforms or []:
        text = str(raw).strip()
        if not text:
            continue
        name, _, value = text.partition(":")
        name = name.strip().lower()
        value = value.strip()
        if name == "transpose":
            if not value:
                raise RemixError("transpose needs a semitone value")
            delta = int(_parse_number(value, "transpose"))
            pitches = [pitch + delta for pitch in pitches]
            ops.append("transpose")
            continue
        if name == "invert":
            if pitches:
                pivot = pitches[0]
                pitches = [2 * pivot - pitch for pitch in pitches]
            ops.append("invert")
            literal = False
            continue
        if name == "retrograde":
            pitches.reverse()
            durations.reverse()
            ops.append("retrograde")
            literal = False
            continue
        if name in ("augment", "diminish"):
            if not value:
                raise RemixError(f"{name} needs a ratio, e.g. 2x or 0.5x")
            match = SCALE.match(value)
            if not match:
                raise RemixError(f"invalid {name} ratio: {value!r}")
            ratio = float(match.group(1))
            if ratio <= 0:
                raise RemixError(f"{name} ratio must be positive")
            durations = [duration * ratio for duration in durations]
            ops.append(name)
            literal = False
            continue
        if name == "fragment":
            match = FRAGMENT.match(value)
            if match:
                count = int(match.group(1))
                if count <= 0:
                    raise RemixError("fragment length must be positive")
                if value.startswith("first"):
                    pitches = pitches[:count]
                    durations = durations[:count]
                else:
                    pitches = pitches[-count:]
                    durations = durations[-count:]
            else:
                match = FRAGMENT_RANGE.match(value)
                if not match:
                    raise RemixError(
                        f"invalid fragment {value!r}; use first-N-notes, "
                        "last-N-notes, or A-B"
                    )
                first, last = int(match.group(1)), int(match.group(2))
                if first < 1 or last < first:
                    raise RemixError(f"invalid fragment range: {value!r}")
                pitches = pitches[first - 1:last]
                durations = durations[first - 1:last]
            ops.append("fragment")
            literal = False
            continue
        if name == "rhythm-only":
            ignore_pitch = True
            ops.append("rhythm-only")
            literal = False
            continue
        if name == "contour-only":
            ignore_intervals = True
            ops.append("contour-only")
            literal = False
            continue
        raise RemixError(f"unknown transform: {raw!r}")

    intervals = [b - a for a, b in zip(pitches, pitches[1:])]
    return Expected(
        pitches=pitches,
        durations=durations,
        intervals=intervals,
        duration_ratios=_ratios(durations),
        contour=contour(intervals),
        ignore_pitch=ignore_pitch,
        ignore_intervals=ignore_intervals,
        literal=literal and all(op == "transpose" for op in ops),
        ops=ops,
    )
