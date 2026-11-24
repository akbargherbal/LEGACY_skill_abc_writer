#!/usr/bin/env python3
"""Build the canonical SUNO ABC library from ``data/SUNO_ABC_SCORE_DATASET.pkl``.

This is the single raw-data entry point for the remixer migration.  It does not
read ``02_maqam-score/data`` and it does not write a remixer store; it writes a
small, deterministic canonical bundle that the remixer build consumes.

Usage::

    python3 tools/build_suno_library.py --pkl data/SUNO_ABC_SCORE_DATASET.pkl \
        --out data/suno

    python3 tools/build_suno_library.py --pkl ... --out data/suno --check

The output contains::

    dataset.json           dataset id, source sha256, counts, artifact hashes
    manifest.json          per-file hashes and the same counts
    songs/suno-0000.abc    canonical ABC, one per source row
    catalog_source.jsonl   one row per score, ready for the remixer catalog

The builder is deliberately standard-library + pandas only, and is byte-for-byte
reproducible for the same input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

DATASET_ID = "suno_abc_score_dataset"
DATASET_VERSION = "1"
ID_PREFIX = "suno-"
BUILDER_VERSION = "suno-library-v1"
SECTION_LINE = re.compile(r"^%\s*(.+?)\s*$", re.M)
REQUIRED_COLUMNS = ("SUNO_ID", "abc", "abc_lines", "abc_encoding")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _setup_path() -> Path:
    scripts = _repo_root() / "02_maqam-score" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    return scripts


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, value) -> None:
    path.write_bytes(_json_bytes(value))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    body = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _section_names(text: str) -> list[str]:
    return [match.group(1).strip() for match in SECTION_LINE.finditer(text) if match.group(1).strip()]


def _row_id(source_id: str) -> str:
    return f"{ID_PREFIX}{str(source_id).strip()}"


def _load_rows(pkl: Path):
    import pandas as pd  # imported lazily so --help does not need pandas

    frame = pd.read_pickle(pkl)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise SystemExit(f"{pkl}: missing columns: {', '.join(missing)}")
    rows = []
    seen_ids = set()
    seen_abc = set()
    for index, row in frame.iterrows():
        source_id = str(row["SUNO_ID"]).strip()
        text = row["abc"]
        if not source_id:
            raise SystemExit(f"{pkl}: row {index} has an empty SUNO_ID")
        if not isinstance(text, str) or not text.strip():
            raise SystemExit(f"{pkl}: {source_id} has empty ABC text")
        if str(row.get("abc_encoding") or "utf-8").lower() not in {"utf-8", "utf8"}:
            raise SystemExit(f"{pkl}: {source_id} is not utf-8")
        song_id = _row_id(source_id)
        if song_id in seen_ids:
            raise SystemExit(f"{pkl}: duplicate id {song_id}")
        digest = _sha256_bytes(text.encode("utf-8"))
        if digest in seen_abc:
            raise SystemExit(f"{pkl}: duplicate ABC text at {song_id}")
        seen_ids.add(song_id)
        seen_abc.add(digest)
        rows.append({"source_id": source_id, "song_id": song_id, "abc": text, "index": index})
    rows.sort(key=lambda item: item["song_id"])
    return rows


def _build(pkl: Path, out: Path) -> dict:
    _setup_path()
    import abc_tools  # noqa: E402
    from ostris.canonical import canonicalize  # noqa: E402
    from ostris.parse import parse_abc  # noqa: E402

    source_hash = _sha256_file(pkl)
    raw_rows = _load_rows(pkl)

    songs_dir = out / "songs"
    songs_dir.mkdir(parents=True, exist_ok=True)
    for old in songs_dir.glob("*.abc"):
        old.unlink()

    catalog_rows: list[dict] = []
    failures: list[dict] = []
    section_counter = Counter()
    flags_counter = Counter()
    vocal_rows = 0
    ins_only_rows = 0
    ins_rows_without_notes = 0
    unit_counts = Counter()

    for item in raw_rows:
        song_id = item["song_id"]
        canonical = canonicalize(item["abc"])
        if not canonical.ok:
            failures.append({"id": song_id, "stage": "canonical", "errors": canonical.errors})
            continue
        parsed = parse_abc(canonical.text)
        if not parsed.ok:
            failures.append({"id": song_id, "stage": "parse", "error": parsed.error})
            continue
        try:
            score = abc_tools.parse(canonical.text)
        except Exception as error:  # pragma: no cover - parse_abc already checked
            failures.append({"id": song_id, "stage": "abc_tools", "error": f"{type(error).__name__}: {error}"})
            continue

        vocal_notes = len(score.voices["Vocal"].notes)
        ins_notes = len(score.voices["Ins"].notes)
        if vocal_notes:
            vocal_rows += 1
        else:
            ins_only_rows += 1
        if not ins_notes:
            ins_rows_without_notes += 1

        sections = _section_names(canonical.text)
        section_counter.update(sections)
        flags = []
        if not vocal_notes:
            flags.append("no_vocal_notes")
        if not ins_notes:
            flags.append("no_ins_notes")
        flags_counter.update(flags)

        text_path = songs_dir / f"{song_id}.abc"
        text_path.write_text(canonical.text, encoding="utf-8")
        text_sha = _sha256_bytes(canonical.text.encode("utf-8"))

        key = parsed.header_key or ""
        meter = parsed.header_meter or ""
        unit = f"1/{score.unit.denominator}"
        unit_counts[unit] += 1

        catalog_rows.append(
            {
                "song_id": song_id,
                "source_id": item["source_id"],
                "source_index": item["index"],
                "source": DATASET_ID,
                "title": "",
                "artist": "",
                "key": key,
                "mode": "minor" if key.endswith("m") else ("major" if key else "unknown"),
                "meter": meter,
                "meters": parsed.meters,
                "tempo": parsed.tempo,
                "bars": parsed.bars,
                "section_count": len(sections),
                "sections": sections,
                "density": None,
                "silence": None,
                "vocal_notes": vocal_notes,
                "ins_notes": ins_notes,
                "unit": unit,
                "quality": None,
                "flags": flags,
                "ins_only": not bool(vocal_notes),
                "exclude_from_priors": not bool(vocal_notes),
                "abc_sha256": text_sha,
                "abc_path": f"songs/{song_id}.abc",
            }
        )

    if failures:
        out.joinpath("failures.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(
            f"{len(failures)} row(s) failed canonicalization/parsing; see {out / 'failures.json'}"
        )

    catalog_path = out / "catalog_source.jsonl"
    _write_jsonl(catalog_path, catalog_rows)

    counts = {
        "rows": len(raw_rows),
        "parse_ok": len(catalog_rows),
        "vocal_rows": vocal_rows,
        "ins_only_rows": ins_only_rows,
        "ins_rows_without_notes": ins_rows_without_notes,
        "excluded_from_priors": ins_only_rows,
        "units": dict(sorted(unit_counts.items())),
        "sections": dict(section_counter.most_common()),
        "flags": dict(sorted(flags_counter.items())),
    }
    try:
        source_label = str(pkl.relative_to(_repo_root()))
    except ValueError:
        source_label = str(pkl)
    dataset = {
        "dataset": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "id_prefix": ID_PREFIX,
        "builder": BUILDER_VERSION,
        "source": source_label,
        "source_sha256": source_hash,
        "source_bytes": pkl.stat().st_size,
        "license_status": "pending-clearance",
        "counts": counts,
        "files": {
            "catalog_source": "catalog_source.jsonl",
            "songs": "songs/",
        },
        "artifacts": {
            "catalog_source.jsonl": _sha256_file(catalog_path),
            "songs": _sha256_bytes(
                "".join(
                    f"{row['song_id']}\t{row['abc_sha256']}\n"
                    for row in sorted(catalog_rows, key=lambda row: row["song_id"])
                ).encode("utf-8")
            ),
        },
    }
    _write_json(out / "dataset.json", dataset)

    manifest = {
        "dataset": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "builder": BUILDER_VERSION,
        "source_sha256": source_hash,
        "counts": counts,
        "songs": {
            row["song_id"]: row["abc_sha256"]
            for row in sorted(catalog_rows, key=lambda row: row["song_id"])
        },
    }
    _write_json(out / "manifest.json", manifest)
    return dataset


def _check(pkl: Path, out: Path) -> dict:
    if not (out / "dataset.json").is_file():
        raise SystemExit(f"{out}: missing dataset.json; run the builder first")
    dataset = json.loads((out / "dataset.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    catalog_rows = _read_jsonl(out / "catalog_source.jsonl")
    errors: list[str] = []

    expected_hash = _sha256_file(pkl)
    if dataset.get("source_sha256") != expected_hash:
        errors.append("dataset.json source_sha256 does not match the pickle")
    if manifest.get("source_sha256") != expected_hash:
        errors.append("manifest.json source_sha256 does not match the pickle")
    if len(catalog_rows) != len(manifest.get("songs", {})):
        errors.append("catalog_source row count differs from the manifest")
    for row in catalog_rows:
        song_id = row.get("song_id", "")
        path = out / row.get("abc_path", "")
        if not path.is_file():
            errors.append(f"{song_id}: missing {path}")
            continue
        actual = _sha256_file(path)
        if actual != row.get("abc_sha256"):
            errors.append(f"{song_id}: song hash differs")
        if manifest.get("songs", {}).get(song_id) != actual:
            errors.append(f"{song_id}: manifest hash differs")

    counts = dataset.get("counts", {})
    summary = {
        "dataset": dataset.get("dataset"),
        "rows": counts.get("rows"),
        "parse_ok": counts.get("parse_ok"),
        "vocal_rows": counts.get("vocal_rows"),
        "ins_only_rows": counts.get("ins_only_rows"),
        "source_sha256": dataset.get("source_sha256"),
        "ok": not errors,
        "errors": errors,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pkl", type=Path, default=_repo_root() / "data" / "SUNO_ABC_SCORE_DATASET.pkl")
    parser.add_argument("--out", type=Path, default=_repo_root() / "data" / "suno")
    parser.add_argument("--check", action="store_true", help="validate an existing bundle")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    pkl = args.pkl.expanduser().resolve()
    out = args.out.expanduser().resolve()
    if not pkl.is_file():
        raise SystemExit(f"missing pickle: {pkl}")

    if args.check:
        summary = _check(pkl, out)
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            state = "PASS" if summary["ok"] else "FAIL"
            counts = summary
            print(
                f"SUNO library: {state} | rows {counts['rows']} | parse {counts['parse_ok']} | "
                f"vocal {counts['vocal_rows']} | ins-only {counts['ins_only_rows']}"
            )
            for error in summary["errors"]:
                print(f"  {error}")
        return 0 if summary["ok"] else 1

    dataset = _build(pkl, out)
    if args.json:
        print(json.dumps(dataset, indent=2, ensure_ascii=False))
    else:
        counts = dataset["counts"]
        print(
            f"wrote {out} | rows {counts['rows']} | parse {counts['parse_ok']} | "
            f"vocal {counts['vocal_rows']} | ins-only {counts['ins_only_rows']}"
        )
        print(f"source sha256 {dataset['source_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
