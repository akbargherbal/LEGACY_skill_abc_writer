"""Build the remixer store from the bundled OSTRIS source cache."""
from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from . import shared

shared.bootstrap()

import abc_tools  # noqa: E402
from ostris.canonical import canonicalize  # noqa: E402
from ostris.links import link_library, load_inventory, record_id  # noqa: E402
from ostris.parse import parse_abc  # noqa: E402
from ostris.sources import Cache, SourceError  # noqa: E402

from . import textcap  # noqa: E402
from .errors import RemixError  # noqa: E402
from .motif import build_index  # noqa: E402
from .store import (  # noqa: E402
    CATALOG_COLUMNS, Store, active_bars, key_mode, tsv_line, voice_notes,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_hash(value) -> str:
    return _sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _catalog_row(record: dict, score, canonical_text: str) -> dict:
    vocal = score.voices["Vocal"]
    ins = score.voices["Ins"]
    vocal_notes = voice_notes(score, "Vocal")
    ins_notes = voice_notes(score, "Ins")
    pitches = [note.pitch for note in vocal_notes]
    intervals = [b.pitch - a.pitch for a, b in zip(vocal_notes, vocal_notes[1:])]
    bars = len(vocal.bars)
    meters = []
    for _start, _length, meter in vocal.bars:
        label = f"{meter[0]}/{meter[1]}"
        if label not in meters:
            meters.append(label)
    key, mode = key_mode(record.get("key") or vocal.key)
    density = record.get("density")
    if density is None:
        density = (len(vocal.notes) + len(ins.notes)) / max(1, bars)
    silence = record.get("silence")
    if silence is None:
        rest_bars = sum(
            1 for index in range(bars)
            if index not in {note.bar for note in vocal_notes}
        )
        silence = rest_bars / max(1, bars)
    row = {
        "song_id": record["id"],
        "title": record.get("title") or "",
        "artist": record.get("artist") or "",
        "key": key,
        "mode": mode,
        "meter": record.get("meter") or f"{vocal.meter[0]}/{vocal.meter[1]}",
        "meters": ";".join(meters),
        "tempo": int(score.bpm),
        "bars": bars,
        "section_count": record.get("section_count") or 0,
        "density": round(float(density), 4),
        "silence": round(float(silence), 4),
        "vocal_low": min(pitches) if pitches else None,
        "vocal_high": max(pitches) if pitches else None,
        "ins_low": min(note.pitch for note in ins_notes) if ins_notes else None,
        "ins_high": max(note.pitch for note in ins_notes) if ins_notes else None,
        "vocal_mean": round(sum(pitches) / len(pitches)) if pitches else None,
        "vocal_top": max(pitches) if pitches else None,
        "ins_active_share": round(len(active_bars(score, "Ins")) / max(1, bars), 4),
        "repeated_pitch_share": round(
            sum(1 for value in intervals if value == 0) / max(1, len(intervals)), 4
        ),
        "duration_variety": len({round(float(note.duration), 6) for note in vocal_notes}),
        "notes_vocal": len(vocal_notes),
        "notes_ins": len(ins_notes),
        "unit": f"1/{score.unit.denominator}",
        "quality": record.get("quality_score"),
        "source": record.get("source") or "",
        "flags": ";".join(record.get("flags") or []),
        "ins_only": 1 if not vocal_notes else 0,
        "excluded_reason": "",
        "abc_sha256": _sha256(canonical_text.encode("utf-8")),
    }
    return row


def _density_bands(rows: list[dict]) -> dict:
    values = sorted(float(row["density"]) for row in rows if row.get("density") is not None)
    if not values:
        return {"light_max": 0.0, "busy_min": 0.0}

    def q(fraction):
        index = min(len(values) - 1, max(0, int(round(fraction * (len(values) - 1)))))
        return round(values[index], 4)

    return {"light_max": q(1 / 3), "busy_min": q(2 / 3)}


def _suno_record(row: dict) -> dict:
    """Map one ``catalog_source.jsonl`` row to the legacy record shape."""
    return {
        "id": row["song_id"],
        "title": row.get("title") or "",
        "artist": row.get("artist") or "",
        "key": row.get("key"),
        "meter": row.get("meter"),
        "section_count": row.get("section_count"),
        "density": row.get("density"),
        "silence": row.get("silence"),
        "quality_score": row.get("quality"),
        "source": row.get("source") or "suno_abc_score_dataset",
        "flags": list(row.get("flags") or []),
    }


def build_suno(dataset_dir: str | Path, out: str | Path, *,
               timestamp: bool = False) -> dict:
    """Build the remixer store from ``tools/build_suno_library.py`` output.

    This path never reads ``02_maqam-score/data``.  It expects the canonical
    bundle to contain ``dataset.json``, ``catalog_source.jsonl`` and
    ``songs/<song_id>.abc``.
    """
    dataset_dir = Path(dataset_dir).expanduser().resolve()
    out = Path(out).expanduser().resolve()
    dataset_path = dataset_dir / "dataset.json"
    catalog_source = dataset_dir / "catalog_source.jsonl"
    songs_source = dataset_dir / "songs"
    if not dataset_path.is_file() or not catalog_source.is_file() or not songs_source.is_dir():
        raise RemixError(
            f"missing SUNO canonical bundle under {dataset_dir}; "
            "run tools/build_suno_library.py first",
            code=5,
        )

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    source_rows = [
        json.loads(line)
        for line in catalog_source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    out.mkdir(parents=True, exist_ok=True)
    store = Store(out)
    if store.songs_dir.exists():
        shutil.rmtree(store.songs_dir)
    if store.index_dir.exists():
        shutil.rmtree(store.index_dir)
    store.songs_dir.mkdir(parents=True, exist_ok=True)
    store.index_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    parse_failures: list[dict] = []
    missing: list[dict] = []
    for source_row in source_rows:
        song_id = source_row.get("song_id", "")
        text_path = songs_source / f"{song_id}.abc"
        if not text_path.is_file():
            missing.append({"song_id": song_id, "reason": "missing song file"})
            continue
        text = text_path.read_text(encoding="utf-8")
        try:
            score = abc_tools.parse(text)
        except Exception as error:
            parse_failures.append({"song_id": song_id, "error": f"{type(error).__name__}: {error}"})
            continue
        row = _catalog_row(_suno_record(source_row), score, text)
        rows.append(row)
        (store.songs_dir / f"{song_id}.abc").write_text(text, encoding="utf-8")

    rows.sort(key=lambda row: row["song_id"])
    catalog_text = "\n".join(["\t".join(CATALOG_COLUMNS)] + [tsv_line(row) for row in rows]) + "\n"
    store.catalog_path.write_text(catalog_text, encoding="utf-8")

    manifest = build_index(store, rows)
    catalog_sha = _sha256(catalog_text.encode("utf-8"))
    index_path = store.index_dir / "motif.json.gz"
    index_sha = _sha256(index_path.read_bytes()) if index_path.is_file() else None
    bands = _density_bands(rows)
    units = Counter(row["unit"] for row in rows)
    meta = {
        "store_version": shared.STORE_VERSION,
        "baseline_skill_version": shared.BASELINE_SKILL_VERSION,
        "dataset": dataset.get("dataset"),
        "dataset_version": dataset.get("dataset_version"),
        "source": dataset.get("source"),
        "source_sha256": dataset.get("source_sha256"),
        "included": len(rows),
        "excluded": 0,
        "records": len(source_rows),
        "density_bands": bands,
        "unit_counts": dict(sorted(units.items())),
        "catalog_sha256": catalog_sha,
        "index_sha256": index_sha,
        "index": manifest,
    }
    store.meta_path.write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    dataset_record = {
        "dataset": dataset.get("dataset"),
        "dataset_version": dataset.get("dataset_version"),
        "source": dataset.get("source"),
        "source_sha256": dataset.get("source_sha256"),
        "license_status": dataset.get("license_status"),
        "store_version": shared.STORE_VERSION,
        "counts": {
            "records": len(source_rows),
            "included": len(rows),
            "excluded": 0,
            "vocal_rows": sum(1 for row in rows if not row["ins_only"]),
            "ins_only_rows": sum(1 for row in rows if row["ins_only"]),
        },
        "artifacts": {
            "catalog.tsv": catalog_sha,
            "index/motif.json.gz": index_sha,
        },
    }
    (out / "dataset.json").write_text(
        json.dumps(dataset_record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    checks = [
        {
            "name": "coverage",
            "required": True,
            "ok": len(rows) > 0 and not parse_failures and not missing,
            "detail": f"{len(rows)} included; {len(parse_failures)} parse failures; "
                      f"{len(missing)} missing",
        },
        {
            "name": "dataset",
            "required": True,
            "ok": all(row["source"] == dataset.get("dataset") for row in rows)
                  and all(row["song_id"].startswith("suno-") for row in rows),
            "detail": "every catalog row comes from the SUNO dataset",
        },
        {
            "name": "reparse",
            "required": True,
            "ok": all(
                abc_tools.parse((store.songs_dir / f"{row['song_id']}.abc").read_text(encoding="utf-8"))
                is not None
                for row in rows
            ),
            "detail": f"{len(rows)}/{len(rows)} stored songs re-parse",
        },
    ]
    report = {
        "stage": "remix-build",
        "store_version": shared.STORE_VERSION,
        "baseline_skill_version": shared.BASELINE_SKILL_VERSION,
        "dataset": dataset.get("dataset"),
        "dataset_version": dataset.get("dataset_version"),
        "source_sha256": dataset.get("source_sha256"),
        "counts": {
            "records": len(source_rows),
            "included": len(rows),
            "excluded": 0,
            "parse_ok": len(rows),
            "vocal_rows": sum(1 for row in rows if not row["ins_only"]),
            "ins_only_rows": sum(1 for row in rows if row["ins_only"]),
        },
        "missing": sorted(missing, key=lambda item: item["song_id"]),
        "parse_failures": sorted(parse_failures, key=lambda item: item["song_id"]),
        "dialect": dict(sorted(Counter(row["unit"] for row in rows).items())),
        "quality": {"min": None, "flags": {}, "ins_only": sum(1 for row in rows if row["ins_only"])},
        "density_bands": bands,
        "outputs": {
            "songs": len(rows),
            "catalog_bytes": len(catalog_text.encode("utf-8")),
            "index_bytes": index_path.stat().st_size if index_path.is_file() else 0,
            "songs_bytes": sum(
                (store.songs_dir / f"{row['song_id']}.abc").stat().st_size for row in rows
            ),
        },
        "checks": checks,
        "gate_pass": all(check["ok"] for check in checks if check["required"]),
    }
    if timestamp:
        from datetime import datetime, timezone
        report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store.report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def build(ostris_data: str | Path, out: str | Path, *, include_all: bool = False,
          quality_min: float = 0.8, timestamp: bool = False) -> dict:
    ostris_data = Path(ostris_data).expanduser().resolve()
    out = Path(out).expanduser().resolve()
    records_path = ostris_data / "records.jsonl"
    source = ostris_data / "source"
    if not records_path.is_file():
        raise RemixError(f"missing {records_path}", code=5)
    if not source.is_dir():
        raise RemixError(f"missing source cache {source}", code=5)

    records = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        raise RemixError("records.jsonl contains duplicate ids", code=5)

    try:
        inv = load_inventory(Cache(source))
        links = {record_id(link): link for link in link_library(inv, Cache(source))}
    except (SourceError, OSError) as error:
        raise RemixError(f"cannot read the OSTRIS source cache: {error}", code=5) from error

    out.mkdir(parents=True, exist_ok=True)
    store = Store(out)
    if store.songs_dir.exists():
        shutil.rmtree(store.songs_dir)
    if store.index_dir.exists():
        shutil.rmtree(store.index_dir)
    store.songs_dir.mkdir(parents=True, exist_ok=True)

    join_failures = []
    no_abc = []
    canonical_failures = []
    parse_failures = []
    exclusions = []
    rows = []
    dialect = Counter()
    quality_flags = Counter()
    input_material = []

    for record in records:
        rid = record["id"]
        link = links.get(rid)
        if not link:
            join_failures.append({"song_id": rid, "reason": "record not present in link inventory"})
            continue
        text = link.get("abc_text") or ""
        if not text:
            no_abc.append({"song_id": rid, "reason": "no ABC text in transcript"})
            continue
        canonical = canonicalize(text)
        if not canonical.ok:
            canonical_failures.append({"song_id": rid, "errors": canonical.errors})
            continue
        parsed = parse_abc(canonical.text)
        if not parsed.ok:
            parse_failures.append({"song_id": rid, "error": parsed.error})
            continue
        raw = abc_tools.parse(canonical.text)
        dialect[f"L:1/{raw.unit.denominator}"] += 1
        input_material.append((rid, canonical.text))

        reason = None
        if not include_all:
            if record.get("exclude_from_priors"):
                reason = "exclude_from_priors"
            elif record.get("duplicate_of"):
                reason = f"duplicate of {record['duplicate_of']}"
            elif record.get("quality_score") is not None and float(record["quality_score"]) < quality_min:
                reason = f"quality_below_{quality_min:g}"
        if reason:
            exclusions.append({"song_id": rid, "reason": reason})
            continue

        row = _catalog_row(record, raw, canonical.text)
        rows.append(row)
        for flag in record.get("flags") or []:
            quality_flags[flag] += 1
        (store.songs_dir / f"{rid}.abc").write_text(canonical.text, encoding="utf-8")

    rows.sort(key=lambda row: row["song_id"])
    catalog_text = "\n".join(["\t".join(CATALOG_COLUMNS)] + [tsv_line(row) for row in rows]) + "\n"
    store.catalog_path.write_text(catalog_text, encoding="utf-8")

    manifest = build_index(store, rows)
    catalog_sha = _sha256(catalog_text.encode("utf-8"))
    index_path = store.index_dir / "motif.json.gz"
    index_sha = _sha256(index_path.read_bytes()) if index_path.is_file() else None
    inputs_sha = _json_hash(sorted(input_material))
    bands = _density_bands(rows)
    units = Counter(row["unit"] for row in rows)
    meta = {
        "store_version": shared.STORE_VERSION,
        "baseline_skill_version": shared.BASELINE_SKILL_VERSION,
        "included": len(rows),
        "excluded": len(exclusions),
        "records": len(records),
        "density_bands": bands,
        "unit_counts": dict(sorted(units.items())),
        "catalog_sha256": catalog_sha,
        "index_sha256": index_sha,
        "inputs_sha256": inputs_sha,
        "index": manifest,
    }
    store.meta_path.write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    checks = [
        {
            "name": "coverage",
            "required": True,
            "ok": len(rows) > 0 and all(not failure for failure in parse_failures),
            "detail": f"{len(rows)} included; {len(parse_failures)} parse failures",
        },
        {
            "name": "join",
            "required": True,
            "ok": not join_failures and not no_abc,
            "detail": f"{len(records) - len(join_failures)}/{len(records)} joined; "
                      f"{len(no_abc)} without ABC",
        },
        {
            "name": "reparse",
            "required": True,
            "ok": all(
                parse_abc((store.songs_dir / f"{row['song_id']}.abc").read_text(encoding="utf-8")).ok
                for row in rows
            ),
            "detail": f"{len(rows)}/{len(rows)} stored songs re-parse",
        },
    ]
    report = {
        "stage": "remix-build",
        "store_version": shared.STORE_VERSION,
        "baseline_skill_version": shared.BASELINE_SKILL_VERSION,
        "counts": {
            "records": len(records),
            "linked": len(records) - len(join_failures),
            "with_abc": len(records) - len(join_failures) - len(no_abc),
            "canonical_ok": len(records) - len(join_failures) - len(no_abc) - len(canonical_failures),
            "parse_ok": len(records) - len(join_failures) - len(no_abc) - len(canonical_failures) - len(parse_failures),
            "included": len(rows),
            "excluded": len(exclusions),
        },
        "exclusions": sorted(exclusions, key=lambda item: item["song_id"]),
        "join_failures": sorted(join_failures, key=lambda item: item["song_id"]),
        "no_abc": sorted(no_abc, key=lambda item: item["song_id"]),
        "canonical_failures": sorted(canonical_failures, key=lambda item: item["song_id"]),
        "parse_failures": sorted(parse_failures, key=lambda item: item["song_id"]),
        "dialect": dict(sorted(dialect.items())),
        "quality": {
            "min": quality_min,
            "flags": dict(sorted(quality_flags.items())),
            "ins_only": sum(1 for row in rows if row["ins_only"]),
        },
        "density_bands": bands,
        "outputs": {
            "songs": len(rows),
            "catalog_bytes": len(catalog_text.encode("utf-8")),
            "index_bytes": index_path.stat().st_size if index_path.is_file() else 0,
            "songs_bytes": sum(
                (store.songs_dir / f"{row['song_id']}.abc").stat().st_size for row in rows
            ),
        },
        "checks": checks,
        "gate_pass": all(check["ok"] for check in checks if check["required"]),
    }
    if timestamp:
        from datetime import datetime, timezone
        report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store.report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def verify(store: Store | None = None) -> dict:
    store = (store or Store()).require()
    rows = store.load_catalog()
    errors = []
    hashes = {}
    for row in rows:
        song_id = row["song_id"]
        path = store.song_path(song_id)
        if not path.is_file():
            errors.append({"song_id": song_id, "error": "missing song file"})
            continue
        text = path.read_text(encoding="utf-8")
        try:
            parsed = abc_tools.parse(text)
        except Exception as error:
            errors.append({"song_id": song_id, "error": f"parse: {error}"})
            continue
        if len(parsed.voices["Vocal"].bars) != row["bars"]:
            errors.append({"song_id": song_id, "error": "bar count differs from catalog"})
        hashes[song_id] = _sha256(text.encode("utf-8"))
    meta = store.load_meta()
    if meta.get("catalog_sha256"):
        actual = _sha256(store.catalog_path.read_bytes())
        if actual != meta["catalog_sha256"]:
            errors.append({"error": "catalog hash differs from catalog_meta.json"})
    return {
        "ok": not errors,
        "songs": len(rows),
        "errors": errors,
        "catalog_sha256": meta.get("catalog_sha256"),
        "index_sha256": meta.get("index_sha256"),
        "store_version": meta.get("store_version"),
    }
