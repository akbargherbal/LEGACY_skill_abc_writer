"""Small, dependency-free statistics shared by the priors and check layers.

Everything here is a pure function of a list, so a prior built from the same
records is byte-for-byte reproducible.
"""
from __future__ import annotations

import math


def quantile(values: list[float], fraction: float) -> float | None:
    """Linear-interpolated quantile (same rule the M0 audit uses)."""
    clean = sorted(float(value) for value in values if value is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    position = (len(clean) - 1) * min(max(fraction, 0.0), 1.0)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(clean) - 1)
    weight = position - lower
    return clean[lower] * (1 - weight) + clean[upper] * weight


def distribution(values: list[float]) -> dict:
    """A compact five-number summary plus mean, used in every prior."""
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return {
            "n": 0,
            "min": None,
            "p10": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "max": None,
            "mean": None,
        }
    return {
        "n": len(clean),
        "min": round(min(clean), 4),
        "p10": round(quantile(clean, 0.10), 4),
        "p25": round(quantile(clean, 0.25), 4),
        "median": round(quantile(clean, 0.50), 4),
        "p75": round(quantile(clean, 0.75), 4),
        "p90": round(quantile(clean, 0.90), 4),
        "max": round(max(clean), 4),
        "mean": round(sum(clean) / len(clean), 4),
    }


def percentile_of(value: float | None, dist: dict | None) -> float | None:
    """Approximate percentile of ``value`` inside a stored distribution.

    Uses the five-number summary, so it is coarse by design: the report says
    where a score falls, never that it is correct.
    """
    if value is None or not dist or dist.get("n", 0) < 2:
        return None
    points = []
    for name, fraction in (
        ("min", 0.0),
        ("p10", 0.10),
        ("p25", 0.25),
        ("median", 0.50),
        ("p75", 0.75),
        ("p90", 0.90),
        ("max", 1.0),
    ):
        point = dist.get(name)
        if point is not None:
            points.append((float(point), fraction))
    if not points:
        return None
    if value <= points[0][0]:
        return round(points[0][1] * 100, 1)
    for (low, low_f), (high, high_f) in zip(points, points[1:]):
        if value <= high:
            if high == low:
                return round(high_f * 100, 1)
            share = (value - low) / (high - low)
            return round((low_f + share * (high_f - low_f)) * 100, 1)
    return round(points[-1][1] * 100, 1)


def confidence(n: int, *, high: int = 60, medium: int = 25, low: int = 10) -> str:
    if n >= high:
        return "high"
    if n >= medium:
        return "medium"
    if n >= low:
        return "low"
    return "insufficient"


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def band(value: float | None, edges: list[float], labels: list[str]) -> str:
    """Map a number to a named band; ``None`` maps to ``unknown``."""
    if value is None:
        return "unknown"
    for edge, label in zip(edges, labels):
        if value < edge:
            return label
    return labels[-1]
