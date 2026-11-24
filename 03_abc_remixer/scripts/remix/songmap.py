"""Cheap structural overview of one song (~300 tokens)."""
from __future__ import annotations

import json
from collections import Counter

from . import shared

shared.bootstrap()

from ostris.mode import key_info  # noqa: E402

from . import textcap
from .errors import RemixError
from .store import Store, active_bars, voice_notes

DEGREE = {
    0: "1", 1: "b2", 2: "2", 3: "b3", 4: "3", 5: "4",
    6: "b5", 7: "5", 8: "b6", 9: "6", 10: "b7", 11: "7",
}


def _count_bars(line: str) -> int:
    body = line.strip()
    if not body.endswith("|"):
        return 0
    total = 0
    for part in body[:-1].split("|"):
        part = part.strip()
        if not part:
            continue
        if part.startswith("Z"):
            total += int(part[1:] or "1") if part[1:].isdigit() else 1
        else:
            total += 1
    return total


def sections(text: str, total_bars: int) -> list[dict]:
    lines = text.splitlines()
    result = []
    pending = None
    current = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("% "):
            pending = line[2:].strip() or "section"
        elif line.startswith("V: Vocal"):
            if i + 1 < len(lines):
                count = _count_bars(lines[i + 1])
                if pending:
                    result.append({"name": pending, "start": current + 1})
                    pending = None
                current += count
                i += 1
        i += 1
    if not result:
        return [{"name": "score", "start": 1, "end": max(1, total_bars)}]
    for index, item in enumerate(result):
        item["end"] = result[index + 1]["start"] - 1 if index + 1 < len(result) else total_bars
    return result


def _degree(pitch: int, key: str) -> str:
    info = key_info(key)
    tonic = info.get("tonic_pc")
    if tonic is None:
        return "?"
    return DEGREE.get((int(pitch) - tonic) % 12, "?")


def _runs(bars: set[int]) -> list[tuple[int, int]]:
    if not bars:
        return []
    ordered = sorted(bars)
    result = []
    start = previous = ordered[0]
    for index in ordered[1:]:
        if index == previous + 1:
            previous = index
            continue
        result.append((start, previous))
        start = previous = index
    result.append((start, previous))
    return result


def _hooks(notes: list, voice: str) -> list[dict]:
    intervals = [b.pitch - a.pitch for a, b in zip(notes, notes[1:])]
    pitches = [note.pitch for note in notes]
    bars = [note.bar for note in notes]
    counts: dict[tuple[int, ...], list[int]] = {}
    for size in (4, 5, 6):
        for index in range(len(intervals) - size + 1):
            cell = tuple(intervals[index:index + size])
            if len(set(cell)) < 2:
                continue
            if max(pitches[index:index + size + 1]) - min(pitches[index:index + size + 1]) < 3:
                continue
            if voice == "Ins" and bars[index + size] - bars[index] > 3:
                continue
            counts.setdefault(cell, []).append(bars[index] + 1)
    ranked = sorted(
        ((cell, locations) for cell, locations in counts.items()),
        key=lambda item: (-len(item[1]), -len(item[0]), item[1][0], item[0]),
    )
    return [
        {"intervals": list(cell), "count": len(locations), "bars": locations[:6]}
        for cell, locations in ranked[:5]
    ]


def _cadences(notes: list, active: set[int], key: str) -> list[dict]:
    result = []
    for first, last in _runs(active):
        run = [note for note in notes if first <= note.bar <= last]
        if not run:
            continue
        note = run[-1]
        result.append(
            {
                "bar": note.bar + 1,
                "midi": note.pitch,
                "degree": _degree(note.pitch, key),
            }
        )
    return result


def _section_stats(name: str, first: int, last: int, score, total_bars: int) -> dict:
    span = max(1, last - first + 1)
    vocal_active = active_bars(score, "Vocal") & set(range(first - 1, last))
    ins_active = active_bars(score, "Ins") & set(range(first - 1, last))
    notes = len(score.voices["Vocal"].notes) + len(score.voices["Ins"].notes)
    # Density for the section, not the whole song.
    section_notes = 0
    for voice in ("Vocal", "Ins"):
        for note in voice_notes(score, voice):
            if first - 1 <= note.bar < last:
                section_notes += 1
    return {
        "name": name,
        "first": first,
        "last": last,
        "vocal_active": round(len(vocal_active) / span, 3),
        "ins_active": round(len(ins_active) / span, 3),
        "density": round(section_notes / span, 3),
    }


def songmap(store: Store, song_id: str, *, max_chars: int = 3000) -> tuple[str, dict]:
    text, score = store.load_song(song_id)
    row = store.catalog_by_id().get(song_id, {})
    total_bars = len(score.voices["Vocal"].bars)
    secs = sections(text, total_bars)
    stats = [_section_stats(item["name"], item["start"], item["end"], score, total_bars) for item in secs]

    vocal_notes = voice_notes(score, "Vocal")
    ins_notes = voice_notes(score, "Ins")
    vocal_active = active_bars(score, "Vocal")
    ins_active = active_bars(score, "Ins")
    key = row.get("key") or score.voices["Vocal"].key
    hooks_vocal = _hooks(vocal_notes, "Vocal")
    hooks_ins = _hooks(ins_notes, "Ins")
    cadences = _cadences(vocal_notes, vocal_active, key)

    def hook_text(items, label):
        if not items:
            return f"{label}: none"
        pieces = []
        for item in items:
            bars = ",".join(str(bar) for bar in item["bars"])
            pieces.append(f"[{','.join(map(str, item['intervals']))}] x{item['count']} @ {bars}")
        return f"{label}: " + " | ".join(pieces)

    lines = [
        f"{song_id} | {row.get('title', '')} | {row.get('artist', '')} | "
        f"{key} {row.get('meter', '')} {row.get('tempo', '?')}bpm | {total_bars} bars | "
        f"q{row.get('quality', '?')}",
        "sections: " + " | ".join(
            f"{item['name']} {item['first']}-{item['last']}" for item in stats
        ),
    ]
    for item in stats:
        lines.append(
            f"  {item['name']}: vocal {item['vocal_active']:.0%} | "
            f"ins {item['ins_active']:.0%} | dens {item['density']:.2f}"
        )
    lines.append(hook_text(hooks_vocal, "hooks Vocal"))
    lines.append(hook_text(hooks_ins, "hooks Ins"))
    lines.append(
        "cadences: " + (" | ".join(
            f"{item['bar']}:{item['midi']}:{item['degree']}" for item in cadences
        ) or "none")
    )
    note = (
        f"ranges: vocal {row.get('vocal_low', '?')}-{row.get('vocal_high', '?')} "
        f"| ins {row.get('ins_low', '?')}-{row.get('ins_high', '?')}"
    )
    lines.insert(2, note)
    output = "\n".join(lines)
    if len(output) > max_chars:
        # Drop section detail lines first, then cadences, then hook locations.
        while len(output) > max_chars and len(lines) > 5:
            removable = [i for i, line in enumerate(lines) if line.startswith("  ")]
            if not removable:
                break
            lines.pop(removable[0])
            output = "\n".join(lines)
    if len(output) > max_chars:
        lines = [line for line in lines if not line.startswith("cadences:")]
        output = "\n".join(lines)
    textcap.enforce("songmap", output, max_chars)
    payload = {
        "song_id": song_id,
        "header": {
            "title": row.get("title"),
            "artist": row.get("artist"),
            "key": key,
            "meter": row.get("meter"),
            "tempo": row.get("tempo"),
            "bars": total_bars,
            "quality": row.get("quality"),
        },
        "sections": stats,
        "hooks": {"Vocal": hooks_vocal, "Ins": hooks_ins},
        "cadences": cadences,
    }
    return output, payload
