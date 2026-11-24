"""Whole-song motif search over both voices.

The index is a 4-gram postings table of interval sequences and duration-ratio
sequences.  It stores unique ``song_id|voice`` postings; the query re-reads the
small candidate set to find exact bars and offsets.  That keeps the index
compact while still returning provenance.
"""
from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

from . import shared

shared.bootstrap()

from ostris.mode import key_info  # noqa: E402

from . import textcap
from .errors import RemixError
from .store import Note, Store, voice_notes
from .transforms import contour as contour_tokens

K = 4
VOICES = ("Vocal", "Ins")


def _grams(values: list, size: int = K):
    if len(values) < size:
        return
    for index in range(len(values) - size + 1):
        yield tuple(values[index:index + size])


def _ratio_sequence(notes: list[Note]) -> list[float]:
    durations = [note.duration for note in notes if note.duration > 0]
    if not durations:
        return []
    unit = min(durations)
    return [round(note.duration / unit, 6) for note in notes]


def build_index(store: Store, rows: list[dict]) -> dict:
    interval_postings: dict[str, set[str]] = defaultdict(set)
    rhythm_postings: dict[str, set[str]] = defaultdict(set)
    songs = 0
    notes_total = 0
    for row in rows:
        song_id = row["song_id"]
        _text, score = store.load_song(song_id)
        songs += 1
        for voice in VOICES:
            notes = voice_notes(score, voice)
            notes_total += len(notes)
            intervals = [b.pitch - a.pitch for a, b in zip(notes, notes[1:])]
            for gram in _grams(intervals):
                interval_postings[",".join(map(str, gram))].add(f"{song_id}|{voice}")
            for gram in _grams(_ratio_sequence(notes)):
                rhythm_postings[",".join(f"{value:g}" for value in gram)].add(f"{song_id}|{voice}")
    payload = {
        "version": shared.STORE_VERSION,
        "k": K,
        "interval_postings": {
            key: sorted(value) for key, value in sorted(interval_postings.items())
        },
        "rhythm_postings": {
            key: sorted(value) for key, value in sorted(rhythm_postings.items())
        },
    }
    store.index_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    data = text.encode("utf-8")
    (store.index_dir / "motif.json.gz").write_bytes(gzip.compress(data, mtime=0))
    manifest = {
        "store_version": shared.STORE_VERSION,
        "k": K,
        "songs": songs,
        "notes": notes_total,
        "interval_grams": len(payload["interval_postings"]),
        "interval_postings": sum(len(value) for value in payload["interval_postings"].values()),
        "rhythm_grams": len(payload["rhythm_postings"]),
        "rhythm_postings": sum(len(value) for value in payload["rhythm_postings"].values()),
        "bytes": len(data),
        "gzip_bytes": len(gzip.compress(data, mtime=0)),
    }
    (store.index_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_intervals(text: str | None) -> list[int]:
    if text is None:
        return []
    try:
        values = [int(value.strip()) for value in str(text).split(",") if value.strip()]
    except ValueError as error:
        raise RemixError(f"invalid interval sequence: {text!r}") from error
    if not values:
        raise RemixError("interval sequence is empty")
    return values


def _parse_durations(text: str | None) -> list[float]:
    if text is None:
        return []
    try:
        values = [float(value.strip()) for value in str(text).split(",") if value.strip()]
    except ValueError as error:
        raise RemixError(f"invalid duration sequence: {text!r}") from error
    if not values:
        raise RemixError("duration sequence is empty")
    if any(value <= 0 for value in values):
        raise RemixError("duration values must be positive")
    unit = min(values)
    return [round(value / unit, 6) for value in values]


def _trivial(intervals: list[int]) -> bool:
    return bool(intervals) and len(set(intervals)) == 1


def _find_offsets(notes: list[Note], intervals: list[int],
                  durations: list[float]) -> list[int]:
    if not intervals and not durations:
        return []
    if intervals:
        pitches = [note.pitch for note in notes]
        expected = intervals
        if durations:
            ratios = _ratio_sequence(notes)
        else:
            ratios = []
        result = []
        for index in range(len(pitches) - len(expected)):
            got = [b - a for a, b in zip(pitches[index:index + len(expected) + 1],
                                         pitches[index + 1:index + len(expected) + 1])]
            if got != expected:
                continue
            if durations:
                if len(ratios) < index + len(durations):
                    continue
                candidate = ratios[index:index + len(durations)]
                if candidate != durations:
                    continue
            result.append(index)
        return result
    # Rhythm-only query.
    ratios = _ratio_sequence(notes)
    result = []
    for index in range(len(ratios) - len(durations) + 1):
        if ratios[index:index + len(durations)] == durations:
            result.append(index)
    return result


def query(store: Store, *, intervals: str | None = None,
          durations: str | None = None, voice: str = "both",
          min_run: int = 4, limit: int = 10,
          allow_trivial: bool = False, song_id: str | None = None
          ) -> tuple[list[dict], int]:
    interval_values = _parse_intervals(intervals)
    duration_values = _parse_durations(durations)
    if not interval_values and not duration_values:
        raise RemixError("pass --intervals, --durations, or --contour")
    if interval_values and len(interval_values) < min_run:
        raise RemixError(f"pattern has {len(interval_values)} intervals; --min-run is {min_run}")
    if duration_values and len(duration_values) < min_run:
        raise RemixError(f"pattern has {len(duration_values)} durations; --min-run is {min_run}")
    if interval_values and _trivial(interval_values) and not allow_trivial:
        raise RemixError("trivial all-equal interval pattern; pass --allow-trivial to search it")
    if voice not in ("Vocal", "Ins", "both"):
        raise RemixError("voice must be Vocal, Ins, or both")

    index = store.load_index()
    candidates: set[str] = set()
    if interval_values:
        key = ",".join(map(str, interval_values[:K]))
        candidates.update(index.get("interval_postings", {}).get(key, []))
    if duration_values:
        key = ",".join(f"{value:g}" for value in duration_values[:K])
        candidates.update(index.get("rhythm_postings", {}).get(key, []))
    if voice != "both":
        candidates = {item for item in candidates if item.endswith("|" + voice)}
    if song_id:
        candidates = {item for item in candidates if item.startswith(song_id + "|")}

    catalog = store.catalog_by_id()
    cache: dict[str, object] = {}
    rows = []
    span_notes = len(interval_values) + 1 if interval_values else len(duration_values)
    for candidate in sorted(candidates):
        song_id, _, candidate_voice = candidate.rpartition("|")
        if candidate_voice not in VOICES:
            continue
        if song_id not in cache:
            _text, score = store.load_song(song_id)
            cache[song_id] = score
        notes = voice_notes(cache[song_id], candidate_voice)
        offsets = _find_offsets(notes, interval_values, duration_values)
        if not offsets:
            continue
        occurrences = []
        for offset in offsets[:6]:
            last_note = min(offset + span_notes - 1, len(notes) - 1)
            occurrences.append({
                "start_bar": notes[offset].bar + 1,
                "end_bar": notes[last_note].bar + 1,
            })
        catalog_row = catalog.get(song_id, {})
        rows.append({
            "song_id": song_id,
            "voice": candidate_voice,
            "occurrences": len(offsets),
            "bars": occurrences,
            "match_length": len(interval_values) or len(duration_values),
            "key": catalog_row.get("key"),
            "density": catalog_row.get("density"),
            "slice_hint": (
                f"slice {song_id} --bars {occurrences[0]['start_bar']}-"
                f"{occurrences[0]['end_bar']} --voice {candidate_voice}"
            ),
        })
    rows.sort(key=lambda row: (-row["occurrences"], row["song_id"],
                               row["bars"][0]["start_bar"], row["voice"]))
    total = len(rows)
    return rows[: max(1, min(limit, 20))], total


def _contour_label(intervals: list[int]) -> str:
    tokens = contour_tokens(intervals)
    ups = sum(1 for token in tokens if token.startswith("u"))
    downs = sum(1 for token in tokens if token.startswith("d"))
    if ups > downs * 2:
        return "up"
    if downs > ups * 2:
        return "down"
    if ups and downs:
        return "wave"
    return "flat"


def query_contour(store: Store, *, contour: str, degree_start: int | None,
                  degree_end: int | None, bars: int = 2,
                  voice: str = "both", limit: int = 10,
                  source_song: str | None = None) -> tuple[list[dict], int]:
    if contour not in ("up", "down", "wave", "flat"):
        raise RemixError("--contour must be up, down, wave, or flat")
    if bars < 1:
        raise RemixError("--bars must be positive")
    rows = []
    for catalog_row in store.load_catalog():
        if source_song and catalog_row["song_id"] != source_song:
            continue
        song_id = catalog_row["song_id"]
        _text, score = store.load_song(song_id)
        total_bars = len(score.voices["Vocal"].bars)
        for name in VOICES:
            if voice != "both" and voice != name:
                continue
            notes = voice_notes(score, name)
            for start in range(0, max(0, total_bars - bars + 1)):
                end = start + bars
                window = [note for note in notes if start <= note.bar < end]
                if len(window) < 2:
                    continue
                intervals = [b.pitch - a.pitch for a, b in zip(window, window[1:])]
                if _contour_label(intervals) != contour:
                    continue
                info = key_info(catalog_row.get("key") or score.voices["Vocal"].key)
                tonic = info.get("tonic_pc")
                if tonic is None:
                    continue
                first = (window[0].pitch - tonic) % 12
                last = (window[-1].pitch - tonic) % 12
                if degree_start is not None and first != degree_start:
                    continue
                if degree_end is not None and last != degree_end:
                    continue
                rows.append({
                    "song_id": song_id,
                    "voice": name,
                    "start_bar": start + 1,
                    "end_bar": end,
                    "contour": contour,
                    "degree_start": first,
                    "degree_end": last,
                    "notes": len(window),
                    "key": catalog_row.get("key"),
                })
    rows.sort(key=lambda row: (row["song_id"], row["start_bar"], row["voice"]))
    total = len(rows)
    return rows[: max(1, min(limit, 20))], total


def render(rows: list[dict], total: int, *, as_json: bool = False,
           contour: bool = False) -> str:
    if as_json:
        text = json.dumps({"matched": total, "shown": len(rows), "matches": rows},
                          ensure_ascii=False)
        return textcap.enforce("motif", text)
    lines = [f"matched={total} shown={len(rows)}"]
    for row in rows:
        if contour:
            lines.append(
                f"{row['song_id']} | {row['voice']} | bars={row['start_bar']}-{row['end_bar']} "
                f"| {row['contour']} | deg {row['degree_start']}->{row['degree_end']} "
                f"| {row['notes']} notes"
            )
        else:
            bars = ",".join(f"{item['start_bar']}-{item['end_bar']}" for item in row["bars"])
            lines.append(
                f"{row['song_id']} | {row['voice']} | bars={bars} | "
                f"match_len={row['match_length']} | occurrences={row['occurrences']} | "
                f"{row.get('key') or '?'} | dens {row.get('density') or '?'}"
            )
    return textcap.enforce("motif", "\n".join(lines))
