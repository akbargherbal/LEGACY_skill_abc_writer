"""Bounded, dialect-safe extraction of a bar range from one song."""
from __future__ import annotations

import json

from . import textcap
from .emit import render_slice
from .errors import RemixError
from .store import Store, ranges

DEFAULT_MAX_BARS = 8
CEILING_MAX_BARS = 16


def _unit_den(value: str | None) -> int | None:
    if value in (None, "auto"):
        return None
    if value in ("1/16", "16"):
        return 16
    if value in ("1/32", "32"):
        return 32
    raise RemixError("--unit must be auto, 1/16, or 1/32")


def slice_song(store: Store, song_id: str, bar_range: str, *,
               voice: str = "both", to_key: str | None = None,
               transpose: int = 0, unit: str | None = "auto",
               strip_chords: bool = True, max_bars: int = DEFAULT_MAX_BARS,
               allow_lossy: bool = False, emit: str = "abc") -> dict:
    if max_bars < 1 or max_bars > CEILING_MAX_BARS:
        raise RemixError(f"--max-bars must be between 1 and {CEILING_MAX_BARS}")
    parsed = ranges(bar_range)
    if len(parsed) != 1:
        raise RemixError("slice takes exactly one bar range; call it again for more")
    first, last = parsed[0]
    span = last - first + 1
    if span > max_bars:
        raise RemixError(
            f"slice is limited to {max_bars} bars per call; requested {span}"
        )
    if to_key and transpose:
        raise RemixError("--to-key and --transpose are mutually exclusive")

    _text, score = store.load_song(song_id)
    unit_den = _unit_den(unit)
    emission = render_slice(
        score,
        song_id,
        first,
        last,
        voice=voice,
        target_key=to_key,
        transpose=transpose,
        unit_den=unit_den,
        strip_chords=strip_chords,
    )
    if unit_den is not None and emission.quantized and not allow_lossy:
        if emission.max_error_units > 1.0 or emission.quantized > max(2, span):
            raise RemixError(
                f"forced L:1/{unit_den} would quantise {emission.quantized} notes "
                f"(max error {emission.max_error_units:g} units); use --unit auto, "
                "choose a smaller unit, or pass --allow-lossy",
                code=4,
            )
    payload = {
        "song_id": song_id,
        "bars": [first, last],
        "voice": voice,
        "unit": f"1/{unit_den or int(score.unit.denominator)}",
        "quantized": emission.quantized,
        "max_error_units": emission.max_error_units,
        "clipped": emission.clipped,
        "text": emission.text,
    }
    if emit == "abc":
        textcap.enforce("slice", emission.text)
        return {"emit": "abc", **payload}
    if emit != "json":
        raise RemixError("--emit must be abc or json")
    textcap.enforce("slice", json.dumps(payload, ensure_ascii=False))
    return {"emit": "json", **payload}
