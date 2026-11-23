"""Parse a transcript with the vendored runtime parser and measure it.

The parser is ``scripts/abc_tools.py``; this module only wraps it so the audit
and the future ``check`` command share one dialect.  It never invents a lenient
parser: an unsupported file is reported as a parse failure.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import abc_tools  # noqa: E402


@dataclass
class ParsedScore:
    ok: bool
    error: str | None = None
    header_key: str | None = None
    header_meter: str | None = None
    tempo: int | None = None
    bars: int = 0
    meters: list[str] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    notes: dict[str, int] = field(default_factory=dict)
    chords: int = 0
    range: dict[str, list[int] | None] = field(default_factory=dict)
    sounding_seconds: float | None = None
    duration_quarters: float | None = None
    vocal_rest_bars: int = 0
    density: float | None = None
    silence: float | None = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "error": self.error,
            "header_key": self.header_key,
            "header_meter": self.header_meter,
            "tempo": self.tempo,
            "bars": self.bars,
            "meters": self.meters,
            "keys": self.keys,
            "notes": self.notes,
            "chords": self.chords,
            "range": self.range,
            "sounding_seconds": self.sounding_seconds,
            "duration_quarters": self.duration_quarters,
            "vocal_rest_bars": self.vocal_rest_bars,
            "density": self.density,
            "silence": self.silence,
        }


def _header_fields(text: str) -> tuple[str | None, str | None]:
    key = meter = None
    for line in text.splitlines()[:10]:
        if line.startswith("K:") and key is None:
            key = line[2:].strip()
        elif line.startswith("M:") and meter is None:
            meter = line[2:].strip()
    return key, meter


def parse_abc(text: str | None) -> ParsedScore:
    """Parse and measure an ABC string.  Missing text is a clean failure."""
    if not text:
        return ParsedScore(ok=False, error="no ABC text")
    header_key, header_meter = _header_fields(text)
    try:
        score = abc_tools.parse(text)
    except Exception as error:  # AbcError and unexpected parser bugs are both failures
        return ParsedScore(
            ok=False,
            error=f"{type(error).__name__}: {error}",
            header_key=header_key,
            header_meter=header_meter,
        )

    vocal = score.voices["Vocal"]
    ins = score.voices["Ins"]
    bars = len(vocal.bars)
    meters = []
    for _, _, meter in vocal.bars:
        label = f"{meter[0]}/{meter[1]}"
        if label not in meters:
            meters.append(label)
    keys = []
    for _, key in vocal.keys:
        if key not in keys:
            keys.append(key)

    ranges: dict[str, list[int] | None] = {}
    for name, voice in (("vocal", vocal), ("ins", ins)):
        pitches = [note[1] for note in voice.notes]
        ranges[name] = [min(pitches), max(pitches)] if pitches else None

    rest_bars = 0
    for start, length, _ in vocal.bars:
        end = start + length
        if not any(start <= note[0] < end for note in vocal.notes):
            rest_bars += 1

    duration_quarters = float(vocal.time)
    sounding_seconds = duration_quarters * 60 / score.bpm if score.bpm else None
    total_notes = len(vocal.notes) + len(ins.notes)
    density = total_notes / bars if bars else None
    silence = rest_bars / bars if bars else None

    return ParsedScore(
        ok=True,
        header_key=header_key,
        header_meter=header_meter,
        tempo=score.bpm,
        bars=bars,
        meters=meters,
        keys=keys,
        notes={"vocal": len(vocal.notes), "ins": len(ins.notes)},
        chords=len(vocal.chords),
        range=ranges,
        sounding_seconds=sounding_seconds,
        duration_quarters=duration_quarters,
        vocal_rest_bars=rest_bars,
        density=density,
        silence=silence,
    )
