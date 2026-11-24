"""Filtered, capped discovery over the remixer catalog."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass

from . import textcap
from .errors import RemixError
from .store import Store

DEFAULT_LIMIT = 15
HARD_LIMIT = 40


@dataclass
class Filters:
    key: str | None = None
    mode: str | None = None
    meter: str | None = None
    tempo: tuple[float | None, float | None] = (None, None)
    bars: tuple[int | None, int | None] = (None, None)
    density: str | None = None
    title: str | None = None
    artist: str | None = None
    source: str | None = None


def _range(value: str | None, kind):
    if value in (None, ""):
        return (None, None)
    text = str(value).strip()
    if "-" in text:
        first, last = text.split("-", 1)
    else:
        first = last = text
    try:
        return (kind(first), kind(last))
    except ValueError as error:
        raise RemixError(f"invalid range {value!r}") from error


def parse_filters(args) -> Filters:
    return Filters(
        key=args.key,
        mode=args.mode,
        meter=args.meter,
        tempo=_range(args.tempo, float),
        bars=_range(args.bars, int),
        density=args.density,
        title=args.title,
        artist=args.artist,
        source=args.source,
    )


def _in_range(value, bounds) -> bool:
    low, high = bounds
    if value is None:
        return low is None and high is None
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def _density_bands(store: Store, rows: list[dict]) -> dict:
    meta = store.load_meta()
    bands = meta.get("density_bands")
    if bands:
        return bands
    values = sorted(float(row["density"]) for row in rows if row.get("density") is not None)
    if not values:
        return {"light_max": 0.0, "busy_min": 0.0}

    def q(fraction):
        index = min(len(values) - 1, max(0, int(round(fraction * (len(values) - 1)))))
        return values[index]

    return {"light_max": q(1 / 3), "busy_min": q(2 / 3)}


def select(store: Store, filters: Filters, *, limit: int = DEFAULT_LIMIT,
           sort: str = "quality", random_seed: int | None = None
           ) -> tuple[list[dict], int, dict]:
    if limit < 1:
        raise RemixError("--limit must be positive")
    if limit > HARD_LIMIT:
        limit = HARD_LIMIT
    rows = store.load_catalog()
    bands = _density_bands(store, rows)
    selected = []
    for row in rows:
        if filters.key and row.get("key") != filters.key:
            continue
        if filters.mode and row.get("mode") != filters.mode:
            continue
        if filters.meter:
            meters = str(row.get("meters") or row.get("meter") or "").split(";")
            if filters.meter not in meters and filters.meter != row.get("meter"):
                continue
        if not _in_range(row.get("tempo"), filters.tempo):
            continue
        if not _in_range(row.get("bars"), filters.bars):
            continue
        if filters.density:
            density = row.get("density")
            if density is None:
                continue
            if filters.density == "light" and not density <= bands["light_max"]:
                continue
            if filters.density == "medium" and not (bands["light_max"] < density <= bands["busy_min"]):
                continue
            if filters.density == "busy" and not density > bands["busy_min"]:
                continue
        if filters.title and filters.title.casefold() not in str(row.get("title", "")).casefold():
            continue
        if filters.artist and filters.artist.casefold() not in str(row.get("artist", "")).casefold():
            continue
        if filters.source and row.get("source") != filters.source:
            continue
        selected.append(row)

    reverse = True
    if sort == "quality":
        key = lambda row: (row.get("quality") or 0.0, row.get("song_id") or "")
    elif sort == "density":
        key = lambda row: (row.get("density") or 0.0, row.get("song_id") or "")
    elif sort == "bars":
        key = lambda row: (row.get("bars") or 0, row.get("song_id") or "")
    elif sort == "tempo":
        key = lambda row: (row.get("tempo") or 0, row.get("song_id") or "")
    elif sort == "title":
        key = lambda row: (str(row.get("title") or "").casefold(), row.get("song_id") or "")
        reverse = False
    else:
        raise RemixError(f"unknown sort: {sort}")
    selected.sort(key=key, reverse=reverse)
    total = len(selected)
    if random_seed is not None:
        random.Random(random_seed).shuffle(selected)
    return selected[:limit], total, bands


def _line(row: dict) -> str:
    title = textcap.clip(str(row.get("title") or ""), 26)
    artist = textcap.clip(str(row.get("artist") or ""), 20)
    key = row.get("key") or "?"
    meter = row.get("meter") or "?"
    tempo = row.get("tempo")
    tempo_text = f"{int(tempo)}bpm" if tempo is not None else "?bpm"
    bars = row.get("bars")
    density = row.get("density")
    density_text = f"dens {density:.2f}" if density is not None else "dens ?"
    silence = row.get("silence")
    silence_text = f"sil {silence:.2f}" if silence is not None else "sil ?"
    quality = row.get("quality")
    quality_text = f"q{quality:g}" if quality is not None else "q?"
    tail = [
        f"{key} {meter} {tempo_text}",
        f"{bars} bars" if bars is not None else "? bars",
        silence_text,
        density_text,
        quality_text,
    ]
    for include_artist, title_width in ((True, 26), (False, 26), (False, 14), (False, 8)):
        if title_width != 26:
            title = textcap.clip(str(row.get("title") or ""), title_width)
        parts = [row.get("song_id") or "?", title]
        if include_artist and artist:
            parts.append(artist)
        parts.extend(tail)
        line = " | ".join(part for part in parts if part)
        if len(line) <= textcap.LIMITS["catalog_line"]:
            return line
    return textcap.clip(line, textcap.LIMITS["catalog_line"])


def render(store: Store, filters: Filters, *, limit: int = DEFAULT_LIMIT,
           sort: str = "quality", random_seed: int | None = None,
           as_json: bool = False) -> str:
    rows, total, bands = select(
        store, filters, limit=limit, sort=sort, random_seed=random_seed
    )
    if as_json:
        text = json.dumps(
            {
                "matched": total,
                "shown": len(rows),
                "density_bands": bands,
                "songs": rows,
            },
            ensure_ascii=False,
        )
        return textcap.enforce("catalog", text)
    lines = [f"matched={total} shown={len(rows)}"]
    lines.extend(_line(row) for row in rows)
    return textcap.enforce("catalog", "\n".join(lines))
