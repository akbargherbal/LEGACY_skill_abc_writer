"""Quality flags for a linked transcript.

The rules are deliberately simple and visible.  They are a QC filter for the
offline corpus, not a musical gate: ``checker.py`` remains the only score gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .parse import ParsedScore


@dataclass
class Quality:
    score: float
    flags: list[str] = field(default_factory=list)
    exclude_from_priors: bool = False
    duration_mismatch: float | None = None

    def as_dict(self) -> dict:
        return {
            "quality_score": round(self.score, 3),
            "flags": self.flags,
            "exclude_from_priors": self.exclude_from_priors,
            "duration_mismatch": (
                round(self.duration_mismatch, 3)
                if self.duration_mismatch is not None
                else None
            ),
        }


def assess(
    parsed: ParsedScore,
    *,
    audio_duration_s: float | None,
    transcribe_status: str | None,
    source_qc: dict | None,
    duplicate_of: str | None = None,
    duplicate_group: str | None = None,
    selected_status: str | None = None,
) -> Quality:
    flags: list[str] = []
    score = 1.0
    mismatch = None

    if not parsed.ok:
        flags.append("abc_parse_failed")
        score = 0.0
    else:
        if parsed.bars < 8:
            flags.append("too_few_bars")
            score -= 0.30
        if parsed.notes.get("ins", 0) < 8:
            flags.append("sparse_ins")
            score -= 0.20
        if parsed.notes.get("vocal", 0) == 0:
            flags.append("no_vocal_notes")
            score -= 0.05
        if parsed.chords == 0:
            flags.append("no_chords")
            score -= 0.05
        if audio_duration_s and parsed.sounding_seconds:
            mismatch = abs(parsed.sounding_seconds - audio_duration_s) / audio_duration_s
            if mismatch > 0.35:
                flags.append("duration_mismatch_major")
                score -= 0.30
            elif mismatch > 0.15:
                flags.append("duration_mismatch_minor")
                score -= 0.10

    if transcribe_status not in (None, "ok"):
        flags.append(f"status_{transcribe_status}")
        score -= 0.25
    if selected_status not in (None, "ok"):
        flags.append(f"selected_status_{selected_status}")
        score -= 0.10
    if duplicate_of or duplicate_group:
        flags.append("duplicate")
        score -= 0.10

    qc = source_qc or {}
    for flag in qc.get("flags") or []:
        label = f"qc_{flag}" if not str(flag).startswith("qc_") else str(flag)
        if label not in flags:
            flags.append(label)
    coverage = qc.get("coverage")
    if isinstance(coverage, (int, float)) and coverage < 0.9:
        flags.append("low_coverage")
        score -= 0.10

    score = max(0.0, min(1.0, score))
    exclude = bool(
        not parsed.ok
        or parsed.bars < 8
        or parsed.notes.get("ins", 0) < 8
        or transcribe_status not in (None, "ok")
        or duplicate_of
        or duplicate_group
        or (mismatch is not None and mismatch > 0.35)
    )
    return Quality(
        score=score,
        flags=flags,
        exclude_from_priors=exclude,
        duration_mismatch=mismatch,
    )
