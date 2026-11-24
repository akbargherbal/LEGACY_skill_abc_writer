"""Read the prebuilt remixer store.

The store is deliberately boring: one ABC file per song, one TSV catalog, one
JSON/gzip motif index.  The model never reads these files directly; the tools
do, and only return capped summaries.
"""
from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import shared

shared.bootstrap()

import abc_tools  # noqa: E402
from ostris.mode import key_info  # noqa: E402

from .errors import RemixError  # noqa: E402

CATALOG_COLUMNS = [
    "song_id",
    "title",
    "artist",
    "key",
    "mode",
    "meter",
    "meters",
    "tempo",
    "bars",
    "section_count",
    "density",
    "silence",
    "vocal_low",
    "vocal_high",
    "ins_low",
    "ins_high",
    "vocal_mean",
    "vocal_top",
    "ins_active_share",
    "repeated_pitch_share",
    "duration_variety",
    "notes_vocal",
    "notes_ins",
    "unit",
    "quality",
    "source",
    "flags",
    "ins_only",
    "excluded_reason",
    "abc_sha256",
]

INT_COLUMNS = {
    "tempo",
    "bars",
    "section_count",
    "vocal_low",
    "vocal_high",
    "ins_low",
    "ins_high",
    "vocal_mean",
    "vocal_top",
    "duration_variety",
    "notes_vocal",
    "notes_ins",
}
FLOAT_COLUMNS = {
    "density",
    "silence",
    "ins_active_share",
    "repeated_pitch_share",
    "quality",
}
BOOL_COLUMNS = {"ins_only"}


def _safe(value: str) -> str:
    return value.replace("\t", "\\t").replace("\n", "\\n")


def _unsafe(value: str) -> str:
    return value.replace("\\t", "\t").replace("\\n", "\n")


def _number(value: str, kind):
    if value == "":
        return None
    try:
        return kind(value)
    except (TypeError, ValueError):
        return None


def tsv_line(row: dict) -> str:
    fields = []
    for name in CATALOG_COLUMNS:
        value = row.get(name, "")
        if value is None:
            value = ""
        if isinstance(value, bool):
            value = "1" if value else "0"
        fields.append(_safe(str(value)))
    return "\t".join(fields)


def parse_catalog_line(header: list[str], line: str) -> dict:
    values = line.split("\t")
    if len(values) != len(header):
        raise RemixError(f"catalog row has {len(values)} fields, expected {len(header)}")
    row = {}
    for name, raw in zip(header, values):
        value = _unsafe(raw)
        if name in INT_COLUMNS:
            row[name] = _number(value, int)
        elif name in FLOAT_COLUMNS:
            row[name] = _number(value, float)
        elif name in BOOL_COLUMNS:
            row[name] = value in {"1", "true", "True"}
        else:
            row[name] = value
    return row


@dataclass
class Note:
    onset: float
    pitch: int
    duration: float
    bar: int

    @property
    def end(self) -> float:
        return self.onset + self.duration


def _bar_index_for_onset(bars: list, onset: float) -> int:
    starts = [bar[0] for bar in bars]
    lo, hi = 0, len(starts) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= onset:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(0, hi)


def voice_notes(score, voice: str) -> list[Note]:
    v = score.voices[voice]
    result = []
    for onset, pitch, duration in v.notes:
        bar = _bar_index_for_onset(v.bars, float(onset))
        result.append(Note(float(onset), int(pitch), float(duration), bar))
    return result


def active_bars(score, voice: str) -> set[int]:
    bars = score.voices[voice].bars
    active: set[int] = set()
    for onset, _pitch, duration in score.voices[voice].notes:
        start = float(onset)
        end = start + float(duration)
        index = _bar_index_for_onset(bars, start)
        while index < len(bars) and bars[index][0] < end - 1e-9:
            active.add(index)
            index += 1
    return active


def bar_meter(score, index: int) -> tuple[int, int]:
    return score.voices["Vocal"].bars[index][2]


def key_at(score, index: int) -> str:
    bars = score.voices["Vocal"].bars
    onset = bars[index][0]
    key = score.voices["Vocal"].key
    for at, value in score.voices["Vocal"].keys:
        if at <= onset:
            key = value
    return key


class Store:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root).expanduser().resolve() if root else shared.data_dir().resolve()

    # -- paths ---------------------------------------------------------
    @property
    def songs_dir(self) -> Path:
        return self.root / "songs"

    @property
    def catalog_path(self) -> Path:
        return self.root / "catalog.tsv"

    @property
    def meta_path(self) -> Path:
        return self.root / "catalog_meta.json"

    @property
    def report_path(self) -> Path:
        return self.root / "build_report.json"

    @property
    def index_dir(self) -> Path:
        return self.root / "index"

    def require(self) -> "Store":
        missing = []
        for path in (self.songs_dir, self.catalog_path, self.index_dir):
            if not path.exists():
                missing.append(str(path))
        if missing:
            raise RemixError(
                "remixer library is missing: " + ", ".join(missing)
                + "; build it with `remix_cli.py library build`",
                code=5,
            )
        return self

    # -- catalog -------------------------------------------------------
    def load_catalog(self) -> list[dict]:
        if not self.catalog_path.is_file():
            raise RemixError(f"missing catalog: {self.catalog_path}", code=5)
        lines = self.catalog_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise RemixError("catalog is empty", code=5)
        header = lines[0].split("\t")
        if header != CATALOG_COLUMNS:
            raise RemixError("catalog header does not match the remixer schema", code=5)
        return [parse_catalog_line(header, line) for line in lines[1:] if line.strip()]

    def catalog_by_id(self) -> dict[str, dict]:
        return {row["song_id"]: row for row in self.load_catalog()}

    def load_meta(self) -> dict:
        if not self.meta_path.is_file():
            return {}
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    # -- songs ---------------------------------------------------------
    def song_path(self, song_id: str) -> Path:
        if not song_id or "/" in song_id or "\\" in song_id or ".." in song_id:
            raise RemixError(f"invalid song id: {song_id!r}")
        return self.songs_dir / f"{song_id}.abc"

    def load_song(self, song_id: str):
        path = self.song_path(song_id)
        if not path.is_file():
            raise RemixError(f"unknown song: {song_id}", code=5)
        text = path.read_text(encoding="utf-8")
        try:
            return text, abc_tools.parse(text)
        except Exception as error:
            raise RemixError(f"{song_id}: stored ABC does not parse: {error}", code=6) from error

    def song_text(self, song_id: str) -> str:
        return self.load_song(song_id)[0]

    # -- index ---------------------------------------------------------
    def load_index(self) -> dict:
        candidates = [self.index_dir / "motif.json", self.index_dir / "motif.json.gz"]
        for path in candidates:
            if not path.is_file():
                continue
            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    return json.load(handle)
            return json.loads(path.read_text(encoding="utf-8"))
        raise RemixError(f"missing motif index under {self.index_dir}", code=5)

    def load_index_manifest(self) -> dict:
        path = self.index_dir / "manifest.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))


def ranges(text: str) -> list[tuple[int, int]]:
    """Parse ``17-24`` or ``5-6, 21-22`` into one-based inclusive ranges."""
    result = []
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
        else:
            start = end = part
        try:
            first, last = int(start), int(end)
        except ValueError as error:
            raise RemixError(f"invalid bar range: {part!r}") from error
        if first < 1 or last < first:
            raise RemixError(f"invalid bar range: {part!r}")
        result.append((first, last))
    if not result:
        raise RemixError("empty bar range")
    return result


def bars_in_ranges(ranges_list: Iterable[tuple[int, int]], total: int | None = None) -> set[int]:
    result: set[int] = set()
    for first, last in ranges_list:
        if total is not None and last > total:
            raise RemixError(f"bar range {first}-{last} exceeds {total} bars")
        result.update(range(first, last + 1))
    return result


def key_mode(key: str | None) -> tuple[str, str]:
    info = key_info(key)
    return info.get("name") or (key or ""), info.get("mode") or "unknown"


def close(a: float, b: float, tolerance: float = 1e-6) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance)
