"""MIDI -> ABC spelling for a target key.

The source ABCs are 12-TET transcriptions.  Transposition is chromatic; this
module chooses a deterministic, key-aware spelling instead of rewriting tokens.
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import shared

shared.bootstrap()

import abc_tools  # noqa: E402

LETTERS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ORDER = {letter: index for index, letter in enumerate(LETTERS)}
ACCIDENTAL = {-2: "__", -1: "_", 0: "=", 1: "^", 2: "^^"}


def _octave_token(letter: str, octave: int) -> str:
    if octave == 0:
        return letter.upper()
    if octave == 1:
        return letter.lower()
    if octave > 1:
        return letter.lower() + "'" * (octave - 1)
    return letter.upper() + "," * (-octave)


def _candidates(pitch: int) -> list[tuple[int, str, int, int]]:
    """Return (score_hint, letter, accidental, octave) for a MIDI pitch."""
    result = []
    for letter in LETTERS:
        natural = NATURAL[letter]
        base = 60 + natural
        # The accidental is the signed semitone offset in [-2, 2].  Every
        # pitch class is within two semitones of at least one natural letter.
        for accidental in range(-2, 3):
            remaining = pitch - base - accidental
            if remaining % 12:
                continue
            octave = remaining // 12
            if -2 <= octave <= 6:
                result.append((abs(accidental), letter, accidental, octave))
    return result


def spell_pitch(pitch: int, key: str, previous: int | None = None,
                following: int | None = None) -> str:
    """Spell one MIDI pitch as an ABC token for ``key``.

    Preference: key-signature accidental, then fewer accidentals, then a scale
    degree, then melodic direction, then a stable letter/octave order.
    """
    if not 0 <= int(pitch) <= 127:
        raise ValueError(f"pitch {pitch} is outside MIDI 0-127")
    key_acc = abc_tools.key_accidentals(key)
    scale_pcs = {(NATURAL[letter] + key_acc[letter]) % 12 for letter in LETTERS}
    candidates = _candidates(int(pitch))
    if not candidates:
        raise ValueError(f"cannot spell pitch {pitch}")

    def rank(item: tuple[int, str, int, int]):
        _distance, letter, accidental, octave = item
        in_key = accidental == key_acc[letter]
        degree = ((NATURAL[letter] + accidental) % 12) in scale_pcs
        direction = 0
        if previous is not None and following is not None:
            if pitch > previous and accidental > 0:
                direction -= 1
            if pitch < previous and accidental < 0:
                direction -= 1
        # Prefer the octave range used by the composing dialect (0/1), then
        # shorter spellings, then a stable letter order.
        octave_penalty = 0 if octave in (0, 1) else 1
        return (
            0 if in_key else 1,
            abs(accidental),
            0 if degree else 1,
            direction,
            octave_penalty,
            ORDER[letter],
            octave,
        )

    _distance, letter, accidental, octave = min(candidates, key=rank)
    key_default = key_acc[letter]
    token = ""
    if accidental != key_default:
        token += ACCIDENTAL[accidental]
    token += _octave_token(letter, octave)
    return token


def spell_sequence(pitches: list[int], key: str) -> list[str]:
    result = []
    for index, pitch in enumerate(pitches):
        previous = pitches[index - 1] if index else None
        following = pitches[index + 1] if index + 1 < len(pitches) else None
        result.append(spell_pitch(pitch, key, previous, following))
    return result
