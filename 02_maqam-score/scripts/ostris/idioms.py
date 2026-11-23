"""M4: objective idiom bank from the canonical ABC.

An idiom is a 2-4 bar vocal phrase with its interval and rhythm sequence.
Functions are structural, not semantic:

* ``opening`` — the first phrase of the track;
* ``cadence`` — the last phrase of the track;
* ``phrase`` — a phrase in between.

No maqam label is attached.  Every row says ``reviewed: false``; the bank is
retrieval material, not a claim about what a phrase means.
"""
from __future__ import annotations

import json
import sys
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .mode import key_info
from .sources import SourceError

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import abc_tools  # noqa: E402

IDIOM_VERSION = "m4-v1"
WARNING = "unreviewed structural phrase; not a maqam label"


def _active_bars(notes: list, bars: list) -> set[int]:
    if not bars:
        return set()
    starts = [bar[0] for bar in bars]
    active = set()
    for onset, _pitch, _duration in notes:
        index = bisect_right(starts, onset) - 1
        if index < 0:
            continue
        start, length, _meter = bars[index]
        if onset < start + length:
            active.add(index)
    return active


def _runs(active: set[int]) -> list[tuple[int, int]]:
    if not active:
        return []
    ordered = sorted(active)
    runs = []
    start = previous = ordered[0]
    for index in ordered[1:]:
        if index == previous + 1:
            previous = index
            continue
        runs.append((start, previous))
        start = previous = index
    runs.append((start, previous))
    return runs


def _contour(intervals: list[int]) -> str:
    if not intervals:
        return "flat"
    up = sum(1 for value in intervals if value > 0)
    down = sum(1 for value in intervals if value < 0)
    if up > down * 2:
        return "up"
    if down > up * 2:
        return "down"
    if up and down:
        return "wave"
    return "flat"


def _idiom(track_id: str, phrase_notes: list, start_bar: int, end_bar: int,
           function: str, key: str, tonic_pc: int | None, index: int) -> dict:
    pitches = [note[1] for note in phrase_notes]
    intervals = [b - a for a, b in zip(pitches, pitches[1:])]
    durations = [round(float(note[2]), 4) for note in phrase_notes]
    tonic = tonic_pc if tonic_pc is not None else 0
    return {
        "id": f"{track_id}#{index}",
        "track_id": track_id,
        "function": function,
        "voice": "Vocal",
        "bars": end_bar - start_bar + 1,
        "start_bar": start_bar + 1,
        "end_bar": end_bar + 1,
        "notes": len(phrase_notes),
        "intervals": intervals,
        "durations": durations,
        "contour": _contour(intervals),
        "degree_start": (pitches[0] - tonic) % 12,
        "degree_end": (pitches[-1] - tonic) % 12,
        "span": max(pitches) - min(pitches),
        "key": key,
        "tonic_pc": tonic_pc,
        "reviewed": False,
        "method": "phrase_window_v1",
        "warning": WARNING,
        "source": "canonical_abc",
    }


def extract_idioms(text: str, track_id: str, key: str) -> list[dict]:
    try:
        score = abc_tools.parse(text)
    except Exception as error:  # parser failures are data failures
        raise SourceError(f"{track_id}: {type(error).__name__}: {error}") from error
    vocal = score.voices["Vocal"]
    if len(vocal.notes) < 3 or not vocal.bars:
        return []

    info = key_info(key)
    runs = _runs(_active_bars(vocal.notes, vocal.bars))
    if not runs:
        return []
    runs = [run for run in runs if run[1] - run[0] + 1 >= 2]
    if not runs:
        return []

    # Keep the bank small and comparable: opening, cadence, and at most one
    # middle phrase per track.
    selected: list[tuple[tuple[int, int], str]] = [(runs[0], "opening")]
    if len(runs) > 1:
        selected.append((runs[-1], "cadence"))
    if len(runs) > 2:
        selected.append((runs[len(runs) // 2], "phrase"))

    idioms = []
    seen: set[tuple[int, int]] = set()
    for (start_bar, end_bar), function in selected:
        if (start_bar, end_bar) in seen:
            continue
        seen.add((start_bar, end_bar))
        window_start = start_bar
        window_end = min(end_bar, start_bar + 3)
        if end_bar - start_bar + 1 > 4:
            if function == "cadence":
                window_end = end_bar
                window_start = max(start_bar, end_bar - 3)
            else:
                window_end = start_bar + 3
        lower = vocal.bars[window_start][0]
        upper = vocal.bars[window_end][0] + vocal.bars[window_end][1]
        phrase_notes = [note for note in vocal.notes if lower <= note[0] < upper]
        if len(phrase_notes) < 3:
            continue
        idioms.append(
            _idiom(
                track_id,
                phrase_notes,
                window_start,
                window_end,
                function,
                info["name"] or key,
                info["tonic_pc"],
                len(idioms),
            )
        )
    return idioms


def build_idioms(out_dir: str | Path) -> dict:
    out = Path(out_dir)
    records_path = out / "records.jsonl"
    if not records_path.is_file():
        raise SourceError(f"missing {records_path}; run `ostris_cli.py features` first")
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    rows: list[dict] = []
    failures: list[dict] = []
    no_vocal: list[str] = []
    for record in records:
        track_id = record.get("id", "")
        uri = (record.get("canonical") or {}).get("uri")
        path = out / uri if uri else None
        if not path or not path.is_file():
            failures.append({"id": track_id, "error": "no canonical ABC"})
            continue
        try:
            idioms = extract_idioms(
                path.read_text(encoding="utf-8"),
                track_id,
                record.get("key") or "",
            )
        except SourceError as error:
            failures.append({"id": track_id, "error": str(error)})
            continue
        if not idioms:
            no_vocal.append(track_id)
            continue
        rows.extend(idioms)

    idioms_path = out / "idioms.jsonl"
    with idioms_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    functions = Counter(row["function"] for row in rows)
    bars = Counter(row["bars"] for row in rows)
    covered = len({row["track_id"] for row in rows})
    summary = {
        "stage": "M4-idioms",
        "version": IDIOM_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "out": str(out.resolve()),
        "records": len(records),
        "tracks_with_idioms": covered,
        "tracks_without_vocal": len(no_vocal),
        "idioms": len(rows),
        "failures": failures,
        "functions": dict(functions.most_common()),
        "bars": {str(key): value for key, value in sorted(bars.items())},
        "maqam_conditioned": False,
        "reviewed": False,
        "limitations": [
            "Phrase function is structural (first/middle/last), not semantic.",
            "The bank is unreviewed and must not be presented as maqam examples.",
            "No audio or lyric alignment is used.",
        ],
        "files": {
            "idioms": str(idioms_path),
            "idioms_md": str(out / "idioms.md"),
        },
    }
    summary["checks"] = [
        {
            "name": "idiom_coverage",
            "required": True,
            "ok": covered + len(no_vocal) + len(failures) == len(records),
            "detail": f"{covered} with idioms + {len(no_vocal)} without vocal "
                      f"+ {len(failures)} failures = {len(records)}",
        },
        {
            "name": "no_maqam_claim",
            "required": True,
            "ok": all(row["reviewed"] is False for row in rows),
            "detail": "every idiom is marked unreviewed",
        },
        {
            "name": "phrase_shape",
            "required": True,
            "ok": all(2 <= row["bars"] <= 4 for row in rows),
            "detail": "every idiom is 2-4 bars",
        },
    ]
    summary["gate_pass"] = all(check["ok"] for check in summary["checks"])
    (out / "idioms.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "idioms.md").write_text(_markdown(summary), encoding="utf-8")
    return summary


def load_idioms(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.is_dir():
        path = path / "idioms.jsonl"
    if not path.is_file():
        raise SourceError(f"missing {path}; run `ostris_cli.py idioms` first")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def pick_idioms(rows: list[dict], *, function: str | None = None,
                bars: int | None = None, contour: str | None = None,
                limit: int = 5) -> list[dict]:
    selected = []
    for row in rows:
        if function and row.get("function") != function:
            continue
        if bars is not None and row.get("bars") != bars:
            continue
        if contour and row.get("contour") != contour:
            continue
        selected.append(row)
    selected.sort(key=lambda row: (row.get("bars", 0), len(row.get("intervals", []))))
    return selected[:limit]


def _markdown(summary: dict) -> str:
    lines = [
        "# OSTRIS M4 idiom bank",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Gate: **{'PASS' if summary['gate_pass'] else 'FAIL'}**",
        f"- Idioms: {summary['idioms']} across {summary['tracks_with_idioms']} tracks",
        f"- Tracks without vocal notes: {summary['tracks_without_vocal']}",
        "- Reviewed: **no** (structural phrases only)",
        "",
        "## Functions",
        "",
        "| Function | Idioms |",
        "|---|---:|",
    ]
    for function, count in summary["functions"].items():
        lines.append(f"| {function} | {count} |")
    lines += ["", "## Length", "", "| Bars | Idioms |", "|---|---:|"]
    for bars, count in summary["bars"].items():
        lines.append(f"| {bars} | {count} |")
    lines += ["", "## Limits", ""]
    for limitation in summary["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)
