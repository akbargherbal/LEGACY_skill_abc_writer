#!/usr/bin/env python3
"""Asset bank: index phrase-level material for declared, justified borrowing.

The library is a quarry, not a template.  This tool builds a compact index of
phrases, cadences and cells from the SUNO store, and lets the composer query a
few candidates and preview a transformed fragment.  It never writes score.abc
and never dumps the library.

    python3 asset_bank.py build --songs <dir> --out data/assets/assets.jsonl.gz
    python3 asset_bank.py query --role chorus --bars 2 --syllables 14 --contour up
    python3 asset_bank.py apply --id a-suno-0024-0031-0032-abc123 --to-key Dm

Every returned asset carries the metadata needed to explain *why* it fits:
role, bars, contour, cadence degree, register, syllable range and quality flags.
The composer records the choice in loans.json; verify_loans.py checks it.
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import abc_tools  # noqa: E402

ROOT = SCRIPT_DIR.parents[1]
DEFAULT_SONGS = ROOT / "03_abc_remixer" / "data" / "remix" / "songs"
DEFAULT_INDEX = SCRIPT_DIR.parent / "data" / "assets" / "assets.jsonl.gz"
DEFAULT_META = SCRIPT_DIR.parent / "data" / "assets" / "assets.meta.json"

DURATIONS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48)
NOTE_NAMES = ("C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B")
KEY_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SECTION_ALIASES = {
    "prechorus": "pre-chorus",
    "pre chorus": "pre-chorus",
    "chorus repeat": "chorus",
    "verse 1": "verse",
    "verse 2": "verse",
    "verse 3": "verse",
    "refrain": "chorus",
}
MAQAM_SCALES = {
    "kurd": (0, 2, 3, 5, 7, 8, 10),
    "nahawand": (0, 2, 3, 5, 7, 8, 10),
    "bayati": (0, 1, 3, 5, 7, 8, 10),
    "rast": (0, 2, 4, 5, 7, 9, 11),
    "hijaz": (0, 1, 4, 5, 7, 8, 10),
    "saba": (0, 1, 3, 4, 6, 8, 10),
    "ajam": (0, 2, 4, 5, 7, 9, 11),
}


# --------------------------------------------------------------------------- io


def _open_index(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def load_index(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists():
        raise SystemExit(
            f"asset index not found: {path}\n"
            f"build it with: python3 {Path(__file__).name} build"
        )
    with _open_index(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def asset_by_id(assets: list[dict], asset_id: str) -> dict | None:
    for asset in assets:
        if asset.get("id") == asset_id:
            return asset
    return None


def _write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


# ------------------------------------------------------------------------ music


def key_pc(key: str | None) -> int | None:
    match = re.match(r"^\s*([A-G])([#b]?)", key or "")
    if not match:
        return None
    pc = KEY_PC[match.group(1)]
    pc += {"#": 1, "b": -1, "": 0}[match.group(2)]
    return pc % 12


def _norm_section(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip().lower())
    text = SECTION_ALIASES.get(text, text)
    text = re.sub(r"\s+\d+$", "", text)
    text = text.replace("_", "-")
    return text or "unknown"


def _section_map(text: str, score: abc_tools.Score) -> tuple[dict[str, list[str]], int]:
    """Return a section label for every parsed bar of every voice."""
    out: dict[str, list[str]] = {name: [] for name in score.voices}
    mismatches = 0
    current = "unknown"
    voice: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("%"):
            current = _norm_section(line.lstrip("% ").strip())
            continue
        match = re.match(r"V:\s*(Vocal|Ins)\b", line)
        if match:
            voice = match.group(1)
            continue
        if re.match(r"^[A-Za-z]:", line):
            continue
        if voice is None:
            continue
        body = re.sub(r"\[K:[^\]]*\]", "", line)
        parts = [part.strip() for part in body.split("|") if part.strip()]
        if not parts and body.strip():
            parts = [body.strip()]
        for part in parts:
            rest = re.fullmatch(r"Z([2-4])?", part)
            count = int(rest.group(1) or "1") if rest else 1
            out[voice].extend([current] * count)
    for name, parsed in score.voices.items():
        labels = out[name]
        expected = len(parsed.bars)
        if len(labels) != expected:
            mismatches += 1
            if len(labels) < expected:
                labels.extend([labels[-1] if labels else "unknown"] * (expected - len(labels)))
            else:
                del labels[expected:]
    return out, mismatches


def _bar_notes(score: abc_tools.Score, voice: str) -> dict[int, list[tuple[float, int, float]]]:
    parsed = score.voices[voice]
    starts = [bar[0] for bar in parsed.bars]
    out: dict[int, list[tuple[float, int, float]]] = defaultdict(list)
    for onset, pitch, duration in parsed.notes:
        index = bisect.bisect_right(starts, onset) - 1
        if index < 0 or index >= len(starts):
            continue
        bar_len = float(parsed.bars[index][1])
        beat = float(onset) - float(starts[index])
        duration = min(float(duration), bar_len - beat)
        if duration <= 0:
            continue
        out[index].append((round(beat, 4), int(pitch), round(duration, 4)))
    for index in out:
        out[index].sort()
    return out


def _meter_of(score: abc_tools.Score, bar: int) -> str:
    meter = score.voices["Vocal"].bars[bar][2]
    return f"{meter[0]}/{meter[1]}"


def _contour(pitches: list[int]) -> str:
    if len(pitches) < 2:
        return "flat"
    first, last = pitches[0], pitches[-1]
    span = max(pitches) - min(pitches)
    if span <= 2:
        return "flat"
    if last - first >= 3:
        return "up"
    if first - last >= 3:
        return "down"
    return "wave"


def _syllables(notes: int) -> tuple[int, int]:
    low = max(1, math.ceil(notes / 1.55))
    high = max(low, math.floor(notes / 1.0))
    return low, high


def _asset_id(source: str, start: int, end: int, kind: str, notes: list) -> str:
    seed = "|".join(
        f"{bar}:{beat}:{pitch}:{duration}" for bar, beat, pitch, duration in notes
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]
    return f"a-{source}-{start + 1:04d}-{end + 1:04d}-{kind}-{digest}"


def _make_asset(
    *,
    source: str,
    score: abc_tools.Score,
    sections: dict[str, list[str]],
    vocal_bars: dict[int, list],
    ins_bars: dict[int, list],
    start: int,
    end: int,
    kind: str,
    function: str,
) -> dict | None:
    notes: list[tuple[int, float, int, float]] = []
    for bar in range(start, end + 1):
        for beat, pitch, duration in vocal_bars.get(bar, []):
            notes.append((bar - start, beat, pitch, duration))
    if len(notes) < 2:
        return None
    notes.sort(key=lambda row: (row[0], row[1]))

    pitches = [pitch for _, _, pitch, _ in notes]
    durations = [duration for _, _, _, duration in notes]
    intervals = [pitches[i] - pitches[i - 1] for i in range(1, len(pitches))]
    bar_count = end - start + 1
    bar_len = float(score.voices["Vocal"].bars[start][1])
    span = bar_len * bar_count
    sounding = sum(durations)
    tonic = key_pc(score.voices["Vocal"].key) or 0
    pcs = [(pitch - tonic) % 12 for pitch in pitches]
    top_share = 0.0
    if durations:
        counts = Counter(round(duration, 4) for duration in durations)
        top_share = max(counts.values()) / len(durations)
    longest_run = 1
    run = 1
    for index in range(1, len(pitches)):
        if pitches[index] == pitches[index - 1]:
            run += 1
            longest_run = max(longest_run, run)
        else:
            run = 1
    ins_notes = sum(len(ins_bars.get(bar, [])) for bar in range(start, end + 1))
    low, high = min(pitches), max(pitches)
    mean = statistics.mean(pitches)
    register_ok = 55 <= mean <= 84
    distinct_durations = len(set(round(duration, 4) for duration in durations))
    # A phrase is not a whole score: two duration values can be a real cell.
    # "Clean" means no hard degeneracy, not "radio-ready".
    clean = (
        bar_count <= 4
        and top_share <= 0.90
        and distinct_durations >= 2
        and longest_run <= 8
        and max([abs(value) for value in intervals] or [0]) <= 12
        and register_ok
        and len(notes) / bar_count >= 1.0
    )
    syll_min, syll_max = _syllables(len(notes))
    section = sections["Vocal"][start] if start < len(sections["Vocal"]) else "unknown"
    meter = _meter_of(score, start)
    return {
        "id": _asset_id(source, start, end, kind, notes),
        "source": source,
        "start_bar": start + 1,
        "end_bar": end + 1,
        "bars": bar_count,
        "section": section,
        "role": section,
        "function": function,
        "kind": kind,
        "meter": meter,
        "tempo": score.bpm,
        "unit": str(score.unit),
        "key": score.voices["Vocal"].key,
        "tonic_pc": tonic,
        "notes": [[bar, round(beat, 4), pitch, round(duration, 4)] for bar, beat, pitch, duration in notes],
        "intervals": intervals,
        "durations": [round(duration, 4) for duration in durations],
        "contour": _contour(pitches),
        "degree_start": pcs[0],
        "degree_end": pcs[-1],
        "low": low,
        "high": high,
        "range": high - low,
        "mean_pitch": round(mean, 2),
        "density": round(len(notes) / bar_count, 2),
        "rest_ratio": round(max(0.0, span - sounding) / span, 3) if span else 0.0,
        "cadence_degree": pcs[-1],
        "syllables_min": syll_min,
        "syllables_max": syll_max,
        "quality": {
            "top_dur": round(top_share, 3),
            "distinct_durations": distinct_durations,
            "longest_run": longest_run,
            "leap_max": max([abs(value) for value in intervals] or [0]),
            "register_ok": register_ok,
            "vocal_activity": round(len(notes) / bar_count, 2),
            "ins_activity": round(ins_notes / bar_count, 2),
            "monotone": top_share > 0.85,
            "repetitive": longest_run > 6,
            "clean": clean,
        },
        "dedupe_group": hashlib.sha1(
            (" ".join(map(str, intervals)) + "|" + " ".join(map(str, durations))).encode("utf-8")
        ).hexdigest()[:12],
        "tags": ["stock", "clean" if clean else "raw", section, function, kind],
    }


def _extract_song(path: Path, *, cells: bool = False) -> tuple[list[dict], int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    score = abc_tools.parse(text)
    sections, mismatches = _section_map(text, score)
    vocal_bars = _bar_notes(score, "Vocal")
    ins_bars = _bar_notes(score, "Ins")
    source = path.stem
    bar_total = len(score.voices["Vocal"].bars)
    section_first: dict[str, int] = {}
    section_last: dict[str, int] = {}
    for bar in range(bar_total):
        label = sections["Vocal"][bar]
        section_first.setdefault(label, bar)
        section_last[label] = bar

    groups: list[list[int]] = []
    current: list[int] = []
    for bar in range(bar_total):
        if vocal_bars.get(bar):
            if current and (
                bar - current[-1] > 1
                or sections["Vocal"][bar] != sections["Vocal"][current[-1]]
            ):
                groups.append(current)
                current = []
            current.append(bar)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    assets: list[dict] = []
    for group in groups:
        if len(group) <= 4:
            chunks = [group]
        else:
            chunks = [group[index:index + 2] for index in range(0, len(group), 2)]
        for chunk in chunks:
            start, end = chunk[0], chunk[-1]
            if end - start + 1 > 4:
                continue
            first = section_first.get(sections["Vocal"][start], start)
            last = section_last.get(sections["Vocal"][start], end)
            function = "opening" if start == first else "cadence" if end == last else "phrase"
            asset = _make_asset(
                source=source, score=score, sections=sections,
                vocal_bars=vocal_bars, ins_bars=ins_bars,
                start=start, end=end, kind="phrase", function=function,
            )
            if asset:
                assets.append(asset)
        # A cadence is the closing two bars of the section; keep it separate so
        # the composer can borrow a close without borrowing the whole phrase.
        label = sections["Vocal"][group[-1]]
        if len(group) >= 2 and group[-1] == section_last.get(label, -1):
            cadence_start = group[-2]
            cadence = _make_asset(
                source=source, score=score, sections=sections,
                vocal_bars=vocal_bars, ins_bars=ins_bars,
                start=cadence_start, end=group[-1], kind="cadence", function="cadence",
            )
            if cadence:
                assets.append(cadence)

    if cells:
        used = 0
        for bar in range(bar_total):
            if used >= 8:
                break
            notes = vocal_bars.get(bar, [])
            if len(notes) < 3:
                continue
            if len({round(duration, 4) for _, _, duration in notes}) < 2:
                continue
            cell = _make_asset(
                source=source, score=score, sections=sections,
                vocal_bars=vocal_bars, ins_bars=ins_bars,
                start=bar, end=bar, kind="cell", function="phrase",
            )
            if cell:
                assets.append(cell)
                used += 1

    # Remove exact duplicate ids inside one song while keeping the first.
    seen: set[str] = set()
    unique = []
    for asset in assets:
        if asset["id"] in seen:
            continue
        seen.add(asset["id"])
        unique.append(asset)
    return unique, mismatches


# ----------------------------------------------------------------------- query


def _parse_span(text: str | None) -> tuple[float, float] | None:
    if not text:
        return None
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:-\s*(-?\d+(?:\.\d+)?))?\s*", text)
    if not match:
        raise SystemExit(f"expected a number or a-b: {text!r}")
    low = float(match.group(1))
    high = float(match.group(2)) if match.group(2) is not None else low
    if low > high:
        low, high = high, low
    return low, high


def _maqam_fit(asset: dict, maqam: str) -> float:
    scale = MAQAM_SCALES[maqam]
    pcs = [(pitch - asset["tonic_pc"]) % 12 for pitch in
           [int(round(note[2])) for note in asset["notes"]]]
    if not pcs:
        return 0.0
    return sum(1 for pc in pcs if pc in scale) / len(pcs)


def _score(asset: dict, args) -> tuple[float, list[str]]:
    score = 0.0
    why: list[str] = []
    if args.role and asset["role"] != args.role:
        return -1e9, []
    if args.function and asset["function"] != args.function:
        return -1e9, []
    if args.kind and asset["kind"] != args.kind:
        return -1e9, []
    if args.source and asset["source"] != args.source:
        return -1e9, []
    if args.quality != "all" and bool(asset["quality"]["clean"]) != (args.quality == "clean"):
        return -1e9, []
    if not args.allow_monotone and asset["quality"].get("monotone"):
        return -1e9, []
    if not args.allow_repetitive and asset["quality"].get("repetitive"):
        return -1e9, []
    bars = _parse_span(args.bars)
    if bars and not (bars[0] <= asset["bars"] <= bars[1]):
        return -1e9, []
    if args.meter and asset["meter"] != args.meter:
        return -1e9, []
    if args.tempo:
        tolerance = max(4.0, args.tempo * 0.10)
        if abs(asset["tempo"] - args.tempo) > tolerance:
            return -1e9, []
    if args.contour and asset["contour"] != args.contour:
        return -1e9, []
    if args.syllables:
        if not (asset["syllables_min"] <= args.syllables <= asset["syllables_max"]):
            return -1e9, []
        score += 2.0
        why.append(f"syllables {asset['syllables_min']}-{asset['syllables_max']}")
    register = _parse_span(args.register)
    if register:
        if asset["high"] < register[0] or asset["low"] > register[1]:
            return -1e9, []
        score += 2.0
        why.append(f"register {asset['low']}-{asset['high']}")
    if args.cadence is not None:
        if asset["cadence_degree"] != args.cadence:
            return -1e9, []
        score += 2.0
        why.append(f"cadence degree {asset['cadence_degree']}")
    if args.maqam:
        fit = _maqam_fit(asset, args.maqam)
        if fit < args.maqam_min:
            return -1e9, []
        score += 2.0 * fit
        why.append(f"{args.maqam} fit {fit:.0%}")
    score += 2.0 if asset["quality"]["clean"] else 0.0
    score += 1.0 if asset["bars"] == 2 else 0.0
    score += 0.5 * min(asset["density"], 6.0) / 6.0
    return score, why


def _why(asset: dict, extra: list[str]) -> str:
    parts = [
        f"{asset['role']}/{asset['function']}",
        f"{asset['bars']} bars",
        f"contour {asset['contour']}",
        f"cadence {asset['cadence_degree']}",
        f"reg {asset['low']}-{asset['high']}",
        f"syll {asset['syllables_min']}-{asset['syllables_max']}",
        "clean" if asset["quality"]["clean"] else "raw",
    ]
    parts.extend(extra)
    return "; ".join(parts)


def cmd_build(args) -> int:
    songs = Path(args.songs)
    if not songs.exists():
        raise SystemExit(f"songs directory not found: {songs}")
    files = sorted(songs.glob("*.abc"))
    if not files:
        raise SystemExit(f"no .abc files in {songs}")
    rows: list[dict] = []
    errors: list[dict] = []
    mismatches = 0
    per_song: Counter = Counter()
    for path in files:
        try:
            assets, mismatch = _extract_song(path, cells=args.cells)
        except Exception as exc:  # noqa: BLE001 - report, do not stop the build
            errors.append({"file": path.name, "error": str(exc)})
            continue
        mismatches += mismatch
        rows.extend(assets)
        per_song[path.stem] = len(assets)
    out = Path(args.out)
    _write_jsonl_gz(out, rows)
    kinds = Counter(asset["kind"] for asset in rows)
    roles = Counter(asset["role"] for asset in rows)
    functions = Counter(asset["function"] for asset in rows)
    clean = sum(1 for asset in rows if asset["quality"]["clean"])
    meta = {
        "index": str(out),
        "songs": len(files),
        "songs_indexed": sum(1 for value in per_song.values() if value),
        "assets": len(rows),
        "clean": clean,
        "raw": len(rows) - clean,
        "kinds": dict(kinds),
        "roles": dict(roles),
        "functions": dict(functions),
        "dedupe_groups": len({asset["dedupe_group"] for asset in rows}),
        "section_mismatches": mismatches,
        "errors": errors[:20],
        "error_count": len(errors),
        "per_song_median": statistics.median(per_song.values()) if per_song else 0,
        "bytes": out.stat().st_size if out.exists() else 0,
    }
    meta_path = Path(args.meta)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(meta, indent=1, ensure_ascii=False))
    else:
        print(f"assets: {meta['assets']} ({meta['clean']} clean, {meta['raw']} raw)")
        print(f"songs: {meta['songs_indexed']}/{meta['songs']} | kinds: {dict(kinds)}")
        print(f"index: {out} ({meta['bytes'] / 1024 / 1024:.1f} MiB)")
        print(f"meta: {meta_path}")
        if errors:
            print(f"errors: {len(errors)} (first: {errors[0]})")
    return 0 if not errors else 1


def cmd_query(args) -> int:
    assets = load_index(args.index)
    candidates = []
    for asset in assets:
        score, extra = _score(asset, args)
        if score > -1e8:
            candidates.append((score, asset, extra))
    candidates.sort(key=lambda row: (-row[0], row[1]["source"], row[1]["start_bar"]))
    selected = []
    per_source: Counter = Counter()
    seen_span: set[tuple[str, int, int]] = set()
    seen_group: set[str] = set()
    for score, asset, extra in candidates:
        span = (asset["source"], asset["start_bar"], asset["end_bar"])
        if span in seen_span or asset["dedupe_group"] in seen_group:
            continue
        if args.diversity and per_source[asset["source"]] >= args.diversity:
            continue
        selected.append((score, asset, extra))
        seen_span.add(span)
        seen_group.add(asset["dedupe_group"])
        per_source[asset["source"]] += 1
        if len(selected) >= args.limit:
            break
    if args.json:
        print(json.dumps(
            [{"score": round(score, 2), "why": _why(asset, extra), "asset": asset}
             for score, asset, extra in selected],
            indent=1, ensure_ascii=False))
        return 0
    if not selected:
        print("no asset matched; compose instead of forcing a loan")
        return 0
    print(f"assets: {len(selected)} (query: {args.role or 'any'}/{args.function or 'any'})")
    for score, asset, extra in selected:
        print(
            f"{asset['id']} | {asset['source']} {asset['start_bar']}-{asset['end_bar']} | "
            f"{asset['role']}/{asset['function']} | {asset['bars']}b | "
            f"{asset['contour']} | cad {asset['cadence_degree']} | "
            f"reg {asset['low']}-{asset['high']} | syll {asset['syllables_min']}-{asset['syllables_max']} | "
            f"{'clean' if asset['quality']['clean'] else 'raw'} | {score:.1f}"
        )
        print(f"  why: {_why(asset, extra)}")
    return 0


# ----------------------------------------------------------------------- apply


def _abc_pitch(midi: int) -> str:
    name = NOTE_NAMES[midi % 12]
    octave = midi // 12 - 1
    if octave >= 5:
        return name.lower() + "'" * (octave - 5)
    if octave <= 3:
        return name + "," * (4 - octave)
    return name


def _split_units(units: int) -> list[int]:
    if units <= 0:
        return []
    for allowed in DURATIONS:
        if units == allowed:
            return [units]
    out: list[int] = []
    remaining = units
    for allowed in (48, 32, 24, 16, 12, 8, 6, 4, 3, 2, 1):
        while remaining >= allowed:
            out.append(allowed)
            remaining -= allowed
    if remaining:
        out.append(remaining)
    return out


def _token(pitch: int | None, units: int) -> list[str]:
    parts = _split_units(units)
    tokens = []
    for index, part in enumerate(parts):
        tie = "-" if index < len(parts) - 1 else ""
        if pitch is None:
            tokens.append(f"z{part}{tie}")
        else:
            tokens.append(f"{_abc_pitch(pitch)}{part}{tie}")
    return tokens


def _render(asset: dict, notes: list[list[float]], *, meter: str, tempo: int, key: str) -> str:
    bar_len = float(abc_tools.meter_value(meter)[0]) / float(abc_tools.meter_value(meter)[1]) * 4
    bars = int(asset["bars"])
    span = bar_len * bars
    # Keep every note inside the fragment; a preview, not a final score.
    laid: list[tuple[float, int, float]] = []
    cursor = 0.0
    for bar, beat, pitch, duration in sorted(notes, key=lambda row: (row[1], row[2])):
        beat = max(float(beat), cursor)
        duration = min(float(duration), span - beat)
        if duration <= 0:
            continue
        laid.append((beat, int(round(pitch)), duration))
        cursor = beat + duration
    lines: list[str] = []
    for bar in range(bars):
        start = bar * bar_len
        end = start + bar_len
        cursor = start
        tokens: list[str] = []
        for beat, pitch, duration in laid:
            if beat < start:
                continue
            if beat >= end:
                break
            if beat > cursor:
                tokens.extend(_token(None, int(round((beat - cursor) * 4))))
                cursor = beat
            duration = min(duration, end - cursor)
            if duration <= 0:
                continue
            tokens.extend(_token(pitch, int(round(duration * 4))))
            cursor += duration
        if cursor < end:
            tokens.extend(_token(None, int(round((end - cursor) * 4))))
        lines.append("".join(tokens) + "|")
    header = [
        f"% asset {asset['id']} source {asset['source']} bars {asset['start_bar']}-{asset['end_bar']}",
        f"% section {asset['section']}; function {asset['function']}; contour {asset['contour']}",
        "X:1", "T:", f"M:{meter}", "L:1/16", f"Q:1/4={tempo}", f"K:{key}",
        "V: Vocal",
    ]
    return "\n".join(header + lines + ["V: Ins"] + ["Z|"] * bars) + "\n"


def _snap_maqam(pitch: int, tonic: int, maqam: str) -> int:
    scale = MAQAM_SCALES[maqam]
    relative = (pitch - tonic) % 12
    nearest = min(scale, key=lambda degree: min((relative - degree) % 12, (degree - relative) % 12))
    distance = (nearest - relative) % 12
    if distance > 6:
        distance -= 12
    return pitch + distance


def _apply_transform(asset: dict, args) -> tuple[list[list[float]], list[str]]:
    notes = [list(note) for note in asset["notes"]]
    transforms: list[str] = []
    tonic = key_pc(args.to_key) if args.to_key else (key_pc(args.tonic) if args.tonic else asset["tonic_pc"])
    if args.to_key and tonic is not None:
        delta = (tonic - asset["tonic_pc"]) % 12
        if delta > 6:
            delta -= 12
        for note in notes:
            note[2] = int(note[2]) + delta
        transforms.append(f"transpose {delta:+d} to {args.to_key}")
    elif args.transpose:
        for note in notes:
            note[2] = int(note[2]) + args.transpose
        transforms.append(f"transpose {args.transpose:+d}")
    if args.maqam and tonic is not None:
        for note in notes:
            note[2] = _snap_maqam(int(note[2]), tonic, args.maqam)
        transforms.append(f"remap to {args.maqam}")
    if args.rhythm_only:
        first = int(notes[0][2]) if notes else tonic or 60
        for note in notes:
            note[2] = first
        transforms.append("rhythm-only")
    if args.contour_only:
        median = statistics.median([float(note[3]) for note in notes]) if notes else 0.5
        for note in notes:
            note[3] = median
        transforms.append("contour-only")
    if args.retrograde:
        notes = list(reversed(notes))
        cursor = 0.0
        for note in notes:
            note[1] = cursor
            cursor += float(note[3])
        transforms.append("retrograde")
    if args.augment and args.augment != 1.0:
        for note in notes:
            note[3] = float(note[3]) * args.augment
        transforms.append(f"augment x{args.augment:g}")
    if args.max_notes:
        notes = notes[:args.max_notes]
        transforms.append(f"fragment {args.max_notes} notes")
    if args.syllables:
        target = args.syllables
        low, high = math.ceil(target * 1.0), math.floor(target * 1.55)
        while len(notes) > high and len(notes) > 2:
            # merge the shortest adjacent pair, keeping the first pitch
            index = min(range(len(notes) - 1), key=lambda i: notes[i][3] + notes[i + 1][3])
            notes[index][3] = notes[index][3] + notes[index + 1][3]
            del notes[index + 1]
        while len(notes) < low and notes:
            index = max(range(len(notes)), key=lambda i: notes[i][3])
            duration = notes[index][3] / 2
            notes[index][3] = duration
            notes.insert(index + 1, [notes[index][0], notes[index][1] + duration, notes[index][2], duration])
        transforms.append(f"fit {target} syllables")
    if args.cadence_degree is not None:
        if notes and tonic is not None:
            notes[-1][2] = tonic + args.cadence_degree
            transforms.append(f"cadence degree {args.cadence_degree}")
    if not transforms:
        transforms.append("none (preview only)")
    return notes, transforms


def cmd_apply(args) -> int:
    assets = load_index(args.index)
    asset = asset_by_id(assets, args.id)
    if asset is None:
        raise SystemExit(f"asset not found: {args.id}")
    notes, transforms = _apply_transform(asset, args)
    if args.to_key:
        key = args.to_key
    elif args.tonic:
        minor = args.maqam not in {"rast", "ajam"}
        key = f"{args.tonic}{'m' if minor else ''}"
    else:
        key = asset["key"]
    meter = args.meter or asset["meter"]
    abc = _render(asset, notes, meter=meter, tempo=asset["tempo"], key=key)
    if args.json:
        print(json.dumps({
            "asset": asset,
            "transforms": transforms,
            "target_key": key,
            "meter": meter,
            "notes": notes,
            "abc": abc,
        }, indent=1, ensure_ascii=False))
    else:
        print(f"% transforms: {'; '.join(transforms)}")
        print(abc, end="")
    return 0


def cmd_stats(args) -> int:
    assets = load_index(args.index)
    clean = sum(1 for asset in assets if asset["quality"]["clean"])
    print(f"assets {len(assets)} | clean {clean} | raw {len(assets) - clean}")
    print(f"sources {len({asset['source'] for asset in assets})}")
    for key in ("kind", "role", "function", "contour"):
        counts = Counter(asset[key] for asset in assets)
        print(f"{key}: {dict(counts.most_common(8))}")
    return 0


# ----------------------------------------------------------------------- entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="build the asset index from a directory of ABC files")
    build.add_argument("--songs", type=Path, default=DEFAULT_SONGS)
    build.add_argument("--out", type=Path, default=DEFAULT_INDEX)
    build.add_argument("--meta", type=Path, default=DEFAULT_META)
    build.add_argument("--cells", action="store_true", help="also index up to 8 one-bar cells per song")
    build.add_argument("--json", action="store_true")
    build.set_defaults(func=cmd_build)

    query = sub.add_parser("query", help="find a few assets that fit a section or line")
    query.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    query.add_argument("--role")
    query.add_argument("--function", choices=["opening", "phrase", "cadence"])
    query.add_argument("--kind", choices=["phrase", "cadence", "cell"])
    query.add_argument("--source")
    query.add_argument("--bars", help="exact bars or a-b")
    query.add_argument("--syllables", type=int)
    query.add_argument("--contour", choices=["up", "down", "wave", "flat"])
    query.add_argument("--register", help="low-high MIDI, e.g. 67-74")
    query.add_argument("--cadence", type=int, help="pitch class relative to the tonic, 0-11")
    query.add_argument("--maqam", choices=sorted(MAQAM_SCALES))
    query.add_argument("--maqam-min", type=float, default=0.80)
    query.add_argument("--meter")
    query.add_argument("--tempo", type=int)
    query.add_argument("--quality", choices=["clean", "raw", "all"], default="clean")
    query.add_argument("--allow-monotone", action="store_true",
                       help="include phrases with one duration covering >85%% of notes")
    query.add_argument("--allow-repetitive", action="store_true",
                       help="include phrases with a same-pitch run longer than 6")
    query.add_argument("--limit", type=int, default=5)
    query.add_argument("--diversity", type=int, default=2, help="max assets from one source")
    query.add_argument("--json", action="store_true")
    query.set_defaults(func=cmd_query)

    apply = sub.add_parser("apply", help="preview a transformed asset as an ABC fragment")
    apply.add_argument("--id", required=True)
    apply.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    apply.add_argument("--to-key", help="target key, e.g. Dm")
    apply.add_argument("--transpose", type=int, default=0)
    apply.add_argument("--tonic", help="target tonic letter, e.g. D")
    apply.add_argument("--maqam", choices=sorted(MAQAM_SCALES))
    apply.add_argument("--rhythm-only", action="store_true")
    apply.add_argument("--contour-only", action="store_true")
    apply.add_argument("--retrograde", action="store_true")
    apply.add_argument("--augment", type=float, default=1.0)
    apply.add_argument("--max-notes", type=int)
    apply.add_argument("--syllables", type=int)
    apply.add_argument("--cadence-degree", type=int)
    apply.add_argument("--meter")
    apply.add_argument("--json", action="store_true")
    apply.set_defaults(func=cmd_apply)

    stats = sub.add_parser("stats", help="print index coverage")
    stats.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
