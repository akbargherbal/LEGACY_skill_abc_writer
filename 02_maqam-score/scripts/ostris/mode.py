"""Heuristic mode descriptors for the 482-track corpus.

There is no reviewed maqam label set for this corpus.  This module therefore
does not emit a ``maqam``.  It returns a coarse, transparent pitch-class
template fit, marked ``reviewed: false`` and excluded from gates and priors.

The 12-TET ABC dialect cannot distinguish pairs that differ mainly by
microtonal intonation or emphasis (Ajam vs Rast, Nahawand vs Bayati).  The
coarse families below are the honest maximum: major-like, minor-like,
phrygian-like, and hijaz-like.  Even those are hypotheses, not labels.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KEY = re.compile(r"^([A-G](?:bb|##|b|#)?)(m)?$")
SHARP = {"#": 1, "##": 2, "b": -1, "bb": -2}

# Coarse families.  Named maqams are deliberately not separated when the
# 12-TET template is identical or near-identical.
TEMPLATES = {
    "major_like": {0, 2, 4, 5, 7, 9, 11},   # Ajam / Rast in 12-TET
    "minor_like": {0, 2, 3, 5, 7, 8, 10},   # Nahawand / Bayati in 12-TET
    "phrygian_like": {0, 1, 3, 5, 7, 8, 10},  # Kurd
    "hijaz_like": {0, 1, 4, 5, 7, 8, 10},   # Hijaz
}

WARNING = "unreviewed heuristic; not a maqam label"


@dataclass
class ModeHypothesis:
    tonic: str | None
    tonic_pc: int | None
    family: str
    score: float
    coverage: float
    degree_shares: list[float] = field(default_factory=list)
    third: str = "unknown"
    augmented_second: bool = False
    alternatives: list[dict] = field(default_factory=list)
    reviewed: bool = False
    method: str = "pitch_class_template_v1"
    warning: str = WARNING

    def as_dict(self) -> dict:
        return {
            "tonic": self.tonic,
            "tonic_pc": self.tonic_pc,
            "family": self.family,
            "score": round(self.score, 4),
            "coverage": round(self.coverage, 4),
            "degree_shares": [round(value, 4) for value in self.degree_shares],
            "third": self.third,
            "augmented_second": self.augmented_second,
            "alternatives": [
                {"family": item["family"], "score": round(item["score"], 4)}
                for item in self.alternatives
            ],
            "reviewed": self.reviewed,
            "method": self.method,
            "anchored_to": "key_header",
            "warning": self.warning,
        }


def key_info(key: str | None) -> dict:
    """Split a key header into tonic, pitch class, and mode."""
    if not key:
        return {"name": None, "tonic": None, "tonic_pc": None, "mode": "unknown"}
    text = key.strip()
    match = KEY.match(text)
    if not match:
        return {"name": text, "tonic": None, "tonic_pc": None, "mode": "unknown"}
    tonic, minor = match.group(1), match.group(2)
    letter = tonic[0]
    accidental = tonic[1:]
    pc = (NATURAL[letter] + SHARP.get(accidental, 0)) % 12
    return {
        "name": text,
        "tonic": tonic,
        "tonic_pc": pc,
        "mode": "minor" if minor else "major",
    }


def classify_mode(key: str | None, notes: list[tuple[int, float]]) -> ModeHypothesis:
    """Fit coarse pitch-class templates around the key tonic.

    ``notes`` is ``(midi_pitch, duration_quarters)``.  Duration weighting keeps
    sustained scale degrees from being drowned out by passing notes.
    """
    info = key_info(key)
    tonic_pc = info["tonic_pc"]
    if tonic_pc is None or not notes:
        return ModeHypothesis(
            tonic=info["tonic"],
            tonic_pc=tonic_pc,
            family="unknown",
            score=0.0,
            coverage=0.0,
        )

    histogram = [0.0] * 12
    total = 0.0
    for pitch, duration in notes:
        weight = max(float(duration), 0.0)
        if weight == 0:
            continue
        histogram[pitch % 12] += weight
        total += weight
    if total == 0:
        return ModeHypothesis(
            tonic=info["tonic"],
            tonic_pc=tonic_pc,
            family="unknown",
            score=0.0,
            coverage=0.0,
        )

    relative = [histogram[(tonic_pc + degree) % 12] / total for degree in range(12)]
    scored = []
    for family, template in TEMPLATES.items():
        coverage = sum(relative[degree] for degree in template)
        outside = 1.0 - coverage
        score = max(0.0, coverage - 0.5 * outside)
        scored.append({"family": family, "score": score, "coverage": coverage})
    scored.sort(key=lambda item: item["score"], reverse=True)
    best = scored[0]
    alternatives = scored[1:3]

    third = "neutral"
    if relative[4] > relative[3] * 1.2:
        third = "major"
    elif relative[3] > relative[4] * 1.2:
        third = "minor"
    augmented_second = (
        relative[1] > 0.02
        and relative[4] > 0.02
        and relative[2] + relative[3] < relative[1] + relative[4]
    )

    return ModeHypothesis(
        tonic=info["tonic"],
        tonic_pc=tonic_pc,
        family=best["family"],
        score=best["score"],
        coverage=best["coverage"],
        degree_shares=relative,
        third=third,
        augmented_second=augmented_second,
        alternatives=alternatives,
    )
