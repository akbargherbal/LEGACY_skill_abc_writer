#!/usr/bin/env python3
"""Shared bar-range parser used by copies, prosody_check, alignment and binding."""
from __future__ import annotations

import re

_RANGE_RE = re.compile(r"^(\d+)(?:\s*-\s*(\d+))?$")


def parse_bar_ranges(spec: str | int | list, *, max_bars: int | None = None) -> list[tuple[int, int]]:
    """Parse bar ranges like ``'1-2, 15-16'`` into 1-based ``(start, end)`` pairs."""
    if isinstance(spec, int) and not isinstance(spec, bool):
        tokens = [str(spec)]
    elif isinstance(spec, list):
        tokens = [str(item).strip() for item in spec if str(item).strip()]
    elif isinstance(spec, str):
        tokens = [part.strip() for part in spec.split(",") if part.strip()]
    else:
        raise ValueError(f"unsupported bar range specification: {spec!r}")

    if not tokens:
        raise ValueError("empty bar range specification")

    ranges: list[tuple[int, int]] = []
    for tok in tokens:
        m = _RANGE_RE.match(tok)
        if not m:
            raise ValueError(f"invalid bar range token {tok!r} in {spec!r}")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) is not None else start
        if start < 1 or end < start:
            raise ValueError(f"invalid bar range {start}-{end} in {spec!r}")
        if max_bars is not None and end > max_bars:
            raise ValueError(f"bar range {start}-{end} exceeds score length {max_bars}")
        ranges.append((start, end))
    return ranges


def expand_bar_ranges_ordered(
    spec: str | int | list, *, max_bars: int | None = None, allow_duplicates: bool = False
) -> list[int]:
    """Expand bar ranges into an ordered list of 1-based bar numbers."""
    out: list[int] = []
    seen: set[int] = set()
    for start, end in parse_bar_ranges(spec, max_bars=max_bars):
        for b in range(start, end + 1):
            if not allow_duplicates and b in seen:
                raise ValueError(f"duplicate bar {b} in range {spec!r}")
            seen.add(b)
            out.append(b)
    return out


def expand_bar_ranges(spec: str | int | list, *, max_bars: int | None = None) -> list[int]:
    """Expand bar ranges into sorted unique 1-based bar numbers."""
    out: set[int] = set()
    for start, end in parse_bar_ranges(spec, max_bars=max_bars):
        out.update(range(start, end + 1))
    return sorted(out)
