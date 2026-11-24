"""Re-emit parsed notes as dialect-valid ABC bars.

This module never rewrites source text.  It works from ``abc_tools`` events
(onset/duration in quarter notes, MIDI pitches) and emits a complete two-voice
score fragment that the same parser can read back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from . import shared

shared.bootstrap()

import abc_tools  # noqa: E402
from ostris.mode import key_info  # noqa: E402

from .errors import RemixError  # noqa: E402
from .pitch import spell_pitch  # noqa: E402
from .store import bar_meter, key_at  # noqa: E402

HEADER = (
    "X:1\n"
    "T:\n"
    "M:{meter}\n"
    "L:1/{unit}\n"
    "Q:1/4={bpm}\n"
    'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"\n'
    'V: Ins clef=treble name="Ins Melody" snm="Inst."\n'
    "K:{key}\n"
)

ALLOWED = sorted(abc_tools.DURATIONS)


@dataclass
class Segment:
    start: float
    end: float
    pitch: int
    tie_out: bool = False


@dataclass
class Emission:
    text: str
    quantized: int = 0
    max_error_units: float = 0.0
    clipped: int = 0
    skipped_overlaps: int = 0
    warnings: list[str] = field(default_factory=list)

    def provenance(self, song_id: str, first: int, last: int, voice: str,
                   transpose: int, unit_den: int) -> str:
        line = (
            f"% src={song_id} bars={first}-{last} voice={voice} "
            f"transpose={transpose:+d} unit=1/{unit_den}"
        )
        if self.quantized:
            line += f" quantized={self.quantized} max_error={self.max_error_units:g}u"
        if self.clipped:
            line += f" clipped={self.clipped}"
        if self.skipped_overlaps:
            line += f" overlap_skipped={self.skipped_overlaps}"
        for warning in self.warnings:
            line += f" warning={warning.replace(' ', '_')}"
        return line


def split_units(units: int) -> list[int]:
    """Split an integer unit count into legal ABC durations, largest first."""
    if units <= 0:
        return []
    result = []
    remaining = units
    for value in reversed(ALLOWED):
        while remaining >= value:
            result.append(value)
            remaining -= value
    if remaining:  # ALLOWED contains 1, so this is defensive only
        result.append(remaining)
    return result


def _units(duration: float, unit_den: int) -> tuple[int, float]:
    exact = Fraction(str(float(duration))) * unit_den / 4
    nearest = int(round(float(exact)))
    error = abs(float(exact) - nearest)
    return nearest, error


def _token(pitch: int, units: int, key: str, previous: int | None,
           following: int | None, tie: bool) -> str:
    token = spell_pitch(pitch, key, previous, following)
    if units != 1:
        token += str(units)
    if tie:
        token += "-"
    return token


def _bar_segments(score, voice: str, first_bar: int, last_bar: int,
                  transpose: int, emission: Emission) -> dict[int, list[Segment]]:
    bars = score.voices[voice].bars
    range_start = float(bars[first_bar][0])
    range_end = float(bars[last_bar][0] + bars[last_bar][1])
    result: dict[int, list[Segment]] = {i: [] for i in range(first_bar, last_bar + 1)}
    for onset, pitch, duration in score.voices[voice].notes:
        new_pitch = int(pitch) + transpose
        if not 0 <= new_pitch <= 127:
            raise RemixError(f"transposition moves a pitch outside MIDI range in {voice}")
        start = float(onset)
        end = start + float(duration)
        if end <= range_start or start >= range_end:
            continue
        clipped_start = max(start, range_start)
        clipped_end = min(end, range_end)
        if clipped_start > start + 1e-9 or clipped_end < end - 1e-9:
            emission.clipped += 1
        for bar in range(first_bar, last_bar + 1):
            bar_start = float(bars[bar][0])
            bar_end = bar_start + float(bars[bar][1])
            if clipped_end <= bar_start:
                break
            if clipped_start >= bar_end:
                continue
            seg_start = max(clipped_start, bar_start)
            seg_end = min(clipped_end, bar_end)
            if seg_end > seg_start + 1e-9:
                result[bar].append(
                    Segment(
                        seg_start,
                        seg_end,
                        new_pitch,
                        tie_out=(seg_end < end - 1e-9
                                 and seg_end < range_end - 1e-9),
                    )
                )
    # The dialect is monophonic per voice.  If the transcript overlaps, keep
    # the first note and truncate the one that starts under it.
    for bar, segments in result.items():
        segments.sort(key=lambda item: (item.start, item.pitch))
        cleaned: list[Segment] = []
        for segment in segments:
            if cleaned and segment.start < cleaned[-1].end - 1e-9:
                emission.skipped_overlaps += 1
                if segment.start >= cleaned[-1].end - 1e-9:
                    cleaned.append(segment)
                continue
            cleaned.append(segment)
        result[bar] = cleaned
    return result


def _render_music_line(segments: list[Segment], bar_start: float, bar_end: float,
                       unit_den: int, key: str,
                       chords: list[tuple[float, str]] | None,
                       emission: Emission, previous: int | None) -> tuple[str, int | None]:
    cursor = bar_start
    tokens: list[str] = []
    chord_cursor = 0
    chords = chords or []
    for segment in segments:
        if segment.start > cursor + 1e-9:
            units, error = _units(segment.start - cursor, unit_den)
            if error > 1e-6:
                emission.max_error_units = max(emission.max_error_units, error)
            for split in split_units(units):
                tokens.append("z" if split == 1 else f"z{split}")
        while chord_cursor < len(chords) and chords[chord_cursor][0] <= segment.start + 1e-9:
            tokens.append('"' + chords[chord_cursor][1] + '"')
            chord_cursor += 1
        units, error = _units(segment.end - segment.start, unit_den)
        if error > 1e-6:
            emission.quantized += 1
            emission.max_error_units = max(emission.max_error_units, error)
        parts = split_units(units)
        if not parts:
            cursor = segment.end
            continue
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            tie = (not last) or segment.tie_out
            tokens.append(
                _token(segment.pitch, part, key, previous, segment.pitch, tie)
            )
        previous = segment.pitch
        cursor = segment.end
    if cursor < bar_end - 1e-9:
        units, error = _units(bar_end - cursor, unit_den)
        if error > 1e-6:
            emission.max_error_units = max(emission.max_error_units, error)
        for split in split_units(units):
            tokens.append("z" if split == 1 else f"z{split}")
    if not tokens:
        return "Z|", previous
    return "".join(tokens) + "|", previous


def _key_shift(key: str, semitones: int) -> str:
    info = key_info(key)
    if info.get("tonic_pc") is None:
        raise RemixError(f"cannot transpose unsupported key {key!r}")
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    pc = (info["tonic_pc"] + semitones) % 12
    tonic = names[pc]
    return tonic + ("m" if info.get("mode") == "minor" else "")


def render_slice(score, song_id: str, first_bar: int, last_bar: int, *,
                 voice: str = "both", target_key: str | None = None,
                 transpose: int = 0, unit_den: int | None = None,
                 strip_chords: bool = True) -> Emission:
    bars = score.voices["Vocal"].bars
    if not bars:
        raise RemixError(f"{song_id}: empty score")
    if first_bar < 1 or last_bar > len(bars) or last_bar < first_bar:
        raise RemixError(f"{song_id}: bars {first_bar}-{last_bar} outside 1-{len(bars)}")
    first = first_bar - 1
    last = last_bar - 1
    if unit_den is None:
        unit_den = int(score.unit.denominator)
    if unit_den not in (16, 32):
        raise RemixError("only L:1/16 and L:1/32 are supported targets")
    if voice not in ("Vocal", "Ins", "both"):
        raise RemixError("voice must be Vocal, Ins, or both")

    source_key = key_at(score, first)
    if target_key:
        if target_key not in abc_tools.KEYS:
            raise RemixError(f"unsupported target key {target_key!r}")
        source_tonic = key_info(source_key).get("tonic_pc")
        target_tonic = key_info(target_key).get("tonic_pc")
        if source_tonic is None or target_tonic is None:
            raise RemixError(f"cannot compute a transposition from {source_key!r}")
        delta = (target_tonic - source_tonic) % 12
        if delta > 6:
            delta -= 12
        if delta == -6:
            delta = 6
        transpose = delta
        out_key = target_key
    elif transpose:
        out_key = _key_shift(source_key, transpose)
    else:
        out_key = source_key

    if not strip_chords and transpose:
        raise RemixError(
            "--keep-chords cannot be combined with transposition; "
            "strip chord symbols or transpose the score yourself"
        )

    for at, changed in score.voices["Vocal"].keys:
        if changed == source_key:
            continue
        if bars[first][0] <= at < bars[last][0] + bars[last][1]:
            changed_bar = next(
                (i + 1 for i, b in enumerate(bars) if b[0] >= at), "?"
            )
            raise RemixError(
                f"{song_id}: the range crosses an inline key change at bar "
                f"{changed_bar}; choose a sub-range inside one key"
            )

    emission = Emission(text="")
    per_voice = {
        name: _bar_segments(score, name, first, last, transpose, emission)
        for name in ("Vocal", "Ins")
    }
    chords_by_bar: dict[int, list[tuple[float, str]]] = {
        i: [] for i in range(first, last + 1)
    }
    if not strip_chords:
        for onset, symbol in score.voices["Vocal"].chords:
            onset = float(onset)
            for bar in range(first, last + 1):
                start = float(bars[bar][0])
                end = start + float(bars[bar][1])
                if start <= onset < end:
                    chords_by_bar[bar].append((onset, symbol))
                    break

    header_meter = bar_meter(score, first)
    lines = [
        HEADER.format(
            meter=f"{header_meter[0]}/{header_meter[1]}",
            unit=unit_den,
            bpm=int(round(score.bpm)),
            key=out_key,
        ).rstrip("\n")
    ]
    lines.append(
        emission.provenance(song_id, first_bar, last_bar, voice, transpose, unit_den)
    )

    previous: dict[str, int | None] = {"Vocal": None, "Ins": None}
    voice_meter = {"Vocal": header_meter, "Ins": header_meter}
    for bar in range(first, last + 1):
        meter = bar_meter(score, bar)
        for name in ("Vocal", "Ins"):
            segments = [] if voice not in ("both", name) else per_voice[name][bar]
            chords = (
                chords_by_bar[bar]
                if name == "Vocal" and not strip_chords
                else []
            )
            start = float(bars[bar][0])
            end = start + float(bars[bar][1])
            lines.append(f"V: {name}")
            if meter != voice_meter[name]:
                lines.append(f"M:{meter[0]}/{meter[1]}")
                voice_meter[name] = meter
            line, previous[name] = _render_music_line(
                segments, start, end, unit_den, out_key, chords, emission,
                previous[name],
            )
            lines.append(line)

    text = "\n".join(lines) + "\n"
    try:
        abc_tools.parse(text)
    except Exception as error:
        raise RemixError(f"internal re-emission bug for {song_id}: {error}", code=6) from error
    emission.text = text
    return emission
