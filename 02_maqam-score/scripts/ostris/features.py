"""M2: deterministic features and an unreviewed mode hypothesis.

The corpus has no reviewed maqam labels.  M2 therefore extracts objective,
reproducible features from the canonical ABC and adds a coarse mode descriptor
from :mod:`ostris.mode`.  The descriptor is marked ``reviewed: false`` and is
never used as a gate or as a named-maqam prior.

Run after ``audit`` and ``build``::

    ostris_cli.py features --cache ... --out ...
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .contract import SKILL_VERSION, verify
from .links import link_library, load_inventory, record_id
from .mode import classify_mode, key_info
from .sources import Cache, SourceError

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import abc_tools  # noqa: E402

FEATURE_VERSION = "m2-v1"


class FeatureError(ValueError):
    pass


def _distribution(values: list[float]) -> dict:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(clean),
        "min": round(min(clean), 3),
        "median": round(statistics.median(clean), 3),
        "max": round(max(clean), 3),
    }


def _tempo_band(bpm: int | None) -> str:
    if not bpm:
        return "unknown"
    if bpm < 80:
        return "slow"
    if bpm <= 110:
        return "medium"
    return "fast"


def _meter_family(meters: list[str]) -> str:
    unique = []
    for meter in meters:
        if meter not in unique:
            unique.append(meter)
    if not unique:
        return "unknown"
    if len(unique) == 1:
        return unique[0]
    return "mixed"


def _voices(score) -> tuple[list, list]:
    vocal = score.voices["Vocal"]
    ins = score.voices["Ins"]
    return vocal, ins


def _interval_stats(notes: list) -> dict:
    pitches = [note[1] for note in notes]
    if len(pitches) < 2:
        return {
            "n": max(len(pitches) - 1, 0),
            "steps": 0,
            "medium": 0,
            "leaps": 0,
            "repeats": 0,
            "histogram": {},
        }
    intervals = [b - a for a, b in zip(pitches, pitches[1:])]
    sizes = [abs(value) for value in intervals]
    histogram = Counter(sizes)
    return {
        "n": len(intervals),
        "steps": sum(1 for size in sizes if 1 <= size <= 2),
        "medium": sum(1 for size in sizes if 3 <= size <= 4),
        "leaps": sum(1 for size in sizes if size >= 5),
        "repeats": sum(1 for size in sizes if size == 0),
        "histogram": {str(key): value for key, value in sorted(histogram.items())},
    }


def _active_bars(notes: list, bars: list) -> set[int]:
    """Bar indices that contain at least one note onset (O(n log b))."""
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


def _phrase_stats(active: set[int]) -> dict:
    if not active:
        return {"count": 0, "median_bars": None, "max_bars": None}
    ordered = sorted(active)
    lengths = []
    current = 1
    for previous, index in zip(ordered, ordered[1:]):
        if index == previous + 1:
            current += 1
        else:
            lengths.append(current)
            current = 1
    lengths.append(current)
    return {
        "count": len(lengths),
        "median_bars": round(statistics.median(lengths), 2),
        "max_bars": max(lengths),
    }


def _voice_features(voice, bars: list) -> dict:
    notes = voice.notes
    bar_count = len(bars)
    pitches = [note[1] for note in notes]
    durations = [float(note[2]) for note in notes]
    active = _active_bars(notes, bars)
    rest_bars = bar_count - len(active)
    top_share = None
    if durations:
        top_share = max(Counter(durations).values()) / len(durations)
    return {
        "notes": len(notes),
        "density_per_bar": round(len(notes) / bar_count, 4) if bar_count else None,
        "range": [min(pitches), max(pitches)] if pitches else None,
        "span_semitones": max(pitches) - min(pitches) if pitches else None,
        "median_midi": round(statistics.median(pitches), 2) if pitches else None,
        "rest_bars": rest_bars,
        "silence": round(rest_bars / bar_count, 4) if bar_count else None,
        "intervals": _interval_stats(notes),
        "durations": {
            "distinct": len(set(durations)),
            "median": round(statistics.median(durations), 4) if durations else None,
            "top_share": round(top_share, 4) if top_share is not None else None,
        },
        "phrases": _phrase_stats(active),
    }


CHORD_ROOT = re.compile(r"^([A-G](?:bb|##|b|#)?)(.*)$")
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ACCIDENTAL = {"#": 1, "##": 2, "b": -1, "bb": -2}
TIE_TOKEN = re.compile(
    r'"(?P<chord>[^"\n]*)"|\[K:[^\]\n]+\]|'
    r"(?P<acc>\^\^|__|\^|_|=)?(?P<note>[A-Ga-gz])"
    r"(?P<oct>[,']*)(?P<dur>[0-9]*)(?P<tie>-?)"
)


def _vocal_tie_groups(text: str) -> int:
    """Count maximal tie-connected groups in the Vocal voice.

    This mirrors the skill checker's rule so a prior built from a track is
    comparable with the score it later checks: a chain ``d8-d8-d8`` is one
    group, and a rest resets the run.
    """
    voice = None
    in_run = False
    groups = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("V:"):
            voice = stripped[2:].strip().split()[0]
            continue
        if not stripped or stripped[0] in "XTLQVKM%":
            continue
        if voice != "Vocal" or not stripped.endswith("|"):
            continue
        for body in stripped[:-1].split("|"):
            if re.fullmatch(r"Z[2-9]?", body.strip()):
                in_run = False
                continue
            for match in TIE_TOKEN.finditer(body):
                if match.group("chord") is not None or match.group("note") is None:
                    continue
                if match.group("note") == "z":
                    in_run = False
                    continue
                tied = bool(match.group("tie"))
                if tied and not in_run:
                    groups += 1
                in_run = tied
    return groups


def _chord_root(symbol: str) -> tuple[str | None, int | None]:
    match = CHORD_ROOT.match(symbol)
    if not match:
        return None, None
    root, _rest = match.groups()
    pc = (NATURAL[root[0]] + ACCIDENTAL.get(root[1:], 0)) % 12
    return root, pc


def _quality(symbol: str) -> str:
    match = CHORD_ROOT.match(symbol)
    if not match:
        return "other"
    rest = match.group(2)
    if rest.startswith("/"):
        rest = ""
    if "dim" in rest:
        return "diminished"
    if "aug" in rest:
        return "augmented"
    if rest.startswith("m") and not rest.startswith("maj"):
        return "minor"
    if rest.startswith("maj"):
        return "major"
    if rest == "":
        return "major"
    if "7" in rest or "6" in rest:
        return "extended"
    if rest.startswith("sus"):
        return "suspended"
    return "other"


def _harmony(chords: list, bars: list) -> dict:
    symbols = [symbol for _onset, symbol in chords]
    roots = Counter()
    qualities = Counter()
    for symbol in symbols:
        root, _pc = _chord_root(symbol)
        roots[root or "?"] += 1
        qualities[_quality(symbol)] += 1
    top = Counter(symbols).most_common(5)
    return {
        "chords": len(symbols),
        "unique_symbols": len(set(symbols)),
        "per_bar": round(len(symbols) / len(bars), 4) if bars else None,
        "roots": dict(roots.most_common()),
        "qualities": dict(qualities.most_common()),
        "top": [{"symbol": symbol, "count": count} for symbol, count in top],
    }


def _section_comments(text: str) -> list[str]:
    labels = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("%"):
            continue
        label = " ".join(stripped[1:].strip().lower().split())
        if label and label not in labels:
            labels.append(label)
    return labels


def _meter_timeline(bars: list) -> dict:
    labels = []
    for _start, _length, (numerator, denominator) in bars:
        label = f"{numerator}/{denominator}"
        if label not in labels:
            labels.append(label)
    changes = 0
    for previous, current in zip(bars, bars[1:]):
        if previous[2] != current[2]:
            changes += 1
    return {
        "declared": labels,
        "family": _meter_family(labels),
        "changes": changes,
    }


@dataclass
class Extraction:
    features: dict
    mode: dict


def extract_features(text: str, source_sections: int | None = None) -> Extraction:
    try:
        score = abc_tools.parse(text)
    except Exception as error:  # parser bugs and AbcError are both failures
        raise FeatureError(f"{type(error).__name__}: {error}") from error

    vocal, ins = _voices(score)
    key = key_info(next((key for _onset, key in vocal.keys), None))
    notes = [(pitch, float(duration)) for _onset, pitch, duration in vocal.notes]
    notes += [(pitch, float(duration)) for _onset, pitch, duration in ins.notes]
    mode = classify_mode(key["name"], notes)
    meters = _meter_timeline(vocal.bars)

    features = {
        "version": FEATURE_VERSION,
        "bars": len(vocal.bars),
        "duration_quarters": float(vocal.time),
        "sounding_seconds": (
            float(vocal.time) * 60 / score.bpm if score.bpm else None
        ),
        "key": key,
        "tempo": {"bpm": score.bpm, "band": _tempo_band(score.bpm)},
        "meter": meters,
        "sections": {
            "source_count": source_sections,
            "comment_labels": _section_comments(text),
        },
        "vocal": _voice_features(vocal, vocal.bars),
        "ins": _voice_features(ins, ins.bars),
        "harmony": _harmony(vocal.chords, vocal.bars),
        "ties": _vocal_tie_groups(text),
        "maqam": None,
        "maqam_source": "unlabelled",
        "maqam_reviewed": False,
    }
    return Extraction(features=features, mode=mode.as_dict())


def _read_records(path: Path) -> list[dict]:
    if not path.is_file():
        raise SourceError(f"missing {path}; run `ostris_cli.py audit` then `build`")
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _write_records(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _text_for(record: dict, links: dict, out: Path) -> str | None:
    canonical = record.get("canonical") or {}
    uri = canonical.get("uri")
    if uri:
        path = out / uri
        if path.is_file():
            return path.read_text(encoding="utf-8")
    link = links.get(record.get("id", ""))
    return (link or {}).get("abc_text")


def build_features(
    cache_dir: str | Path,
    out_dir: str | Path,
    *,
    require_contract: bool = False,
) -> dict:
    cache = Cache(cache_dir)
    out = Path(out_dir)
    records = _read_records(out / "records.jsonl")
    inv = load_inventory(cache)
    links = {record_id(link): link for link in link_library(inv, cache)}

    contract_checks = verify()
    contract_ok = all(check["ok"] for check in contract_checks)

    failures: list[dict] = []
    families: Counter[str] = Counter()
    thirds: Counter[str] = Counter()
    tempo_bands: Counter[str] = Counter()
    meter_families: Counter[str] = Counter()
    bars_values: list[float] = []
    vocal_notes: list[float] = []
    chord_counts: list[float] = []

    for record in records:
        rid = record.get("id", "")
        text = _text_for(record, links, out)
        if not text:
            failures.append({"id": rid, "error": "no canonical ABC text"})
            record["features"] = None
            record["mode_hypothesis"] = None
            record["exclude_from_priors"] = True
            record.setdefault("flags", []).append("features_failed")
            continue
        try:
            extraction = extract_features(text, record.get("section_count"))
        except FeatureError as error:
            failures.append({"id": rid, "error": str(error)})
            record["features"] = None
            record["mode_hypothesis"] = None
            record["exclude_from_priors"] = True
            record.setdefault("flags", []).append("features_failed")
            continue

        features = extraction.features
        record["features"] = features
        record["mode_hypothesis"] = extraction.mode
        record["maqam"] = None
        record["maqam_confidence"] = None
        record["maqam_source"] = "unlabelled"
        families[extraction.mode["family"]] += 1
        thirds[extraction.mode["third"]] += 1
        tempo_bands[features["tempo"]["band"]] += 1
        meter_families[features["meter"]["family"]] += 1
        bars_values.append(features["bars"])
        vocal_notes.append(features["vocal"]["notes"])
        chord_counts.append(features["harmony"]["chords"])

    _write_records(out / "records.jsonl", records)

    feature_ok = len(records) - len(failures)
    reviewed_maqam = sum(1 for record in records if record.get("maqam"))
    checks = [
        {
            "name": "feature_coverage",
            "required": True,
            "ok": feature_ok == len(records),
            "detail": f"{feature_ok}/{len(records)} feature rows",
        },
        {
            "name": "mode_hypothesis_coverage",
            "required": True,
            "ok": all(record.get("mode_hypothesis") for record in records),
            "detail": f"{sum(1 for record in records if record.get('mode_hypothesis'))}/{len(records)} mode rows",
        },
        {
            "name": "no_maqam_claim",
            "required": True,
            "ok": reviewed_maqam == 0,
            "detail": f"{reviewed_maqam} records carry a maqam label (must be 0)",
        },
        {
            "name": "contract_pin",
            "required": require_contract,
            "ok": contract_ok,
            "detail": (
                f"skill {SKILL_VERSION} pins {'match' if contract_ok else 'drifted'}: "
                + ", ".join(f"{c['artifact']}={c['detail']}" for c in contract_checks)
            ),
        },
    ]

    summary = {
        "stage": "M2",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cache": str(cache.root),
        "out": str(out.resolve()),
        "skill_version": SKILL_VERSION,
        "feature_version": FEATURE_VERSION,
        "records": len(records),
        "feature_ok": feature_ok,
        "failures": failures,
        "families": dict(families.most_common()),
        "thirds": dict(thirds.most_common()),
        "tempo_bands": dict(tempo_bands.most_common()),
        "meter_families": dict(meter_families.most_common()),
        "bars": _distribution(bars_values),
        "vocal_notes": _distribution(vocal_notes),
        "chords": _distribution(chord_counts),
        "maqam_conditioned": False,
        "maqam_reviewed": False,
        "limitations": [
            "No expert maqam review is available for the 482-track corpus.",
            "mode_hypothesis is a coarse, unreviewed 12-TET template fit; it is not a maqam label.",
            "Mode families are anchored to the ABC key tonic; this is not a corpus maqam distribution.",
            "Ajam/Rast and Nahawand/Bayati are not separable in this ABC dialect.",
            "The 438 v3 labels are a separate corpus and are only a weak cross-check, never priors or eval.",
            "The 177 five_stars labels are prompts/calibration, not ground truth.",
        ],
        "contract": {"version": SKILL_VERSION, "checks": contract_checks, "ok": contract_ok},
        "checks": checks,
        "gate_pass": all(check["ok"] for check in checks if check["required"]),
        "records_file": str(out / "records.jsonl"),
    }
    summary["files"] = write_summaries(out, summary)
    return summary


def write_summaries(out: Path, summary: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "features.json"
    md_path = out / "features.md"
    summary["files"] = {"features": str(json_path), "features_md": str(md_path)}
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return summary["files"]


def _markdown(summary: dict) -> str:
    lines = [
        "# OSTRIS M2 features",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Gate: **{'PASS' if summary['gate_pass'] else 'FAIL'}**",
        f"- Features: {summary['feature_ok']}/{summary['records']}",
        f"- Named maqam labels: **0** (not claimed)",
        "",
        "## Mode hypothesis (unreviewed, key-anchored)",
        "",
        "| Coarse family | Tracks |",
        "|---|---:|",
    ]
    for family, count in summary["families"].items():
        lines.append(f"| {family} | {count} |")
    lines += ["", "| Third | Tracks |", "|---|---:|"]
    for third, count in summary["thirds"].items():
        lines.append(f"| {third} | {count} |")
    lines += [
        "",
        "## Shape",
        "",
        "| Measure | n | min | median | max |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("bars", "vocal_notes", "chords"):
        dist = summary[name]
        lines.append(
            f"| {name} | {dist['n']} | {dist['min']} | {dist['median']} | {dist['max']} |"
        )
    lines += ["", "## Checks", "", "| Check | Required | OK | Detail |", "|---|---|---|---|"]
    for check in summary["checks"]:
        lines.append(
            f"| {check['name']} | {'yes' if check['required'] else 'no'} | "
            f"{'yes' if check['ok'] else '**no**'} | {check['detail']} |"
        )
    lines += ["", "## Limits", ""]
    for limitation in summary["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)
