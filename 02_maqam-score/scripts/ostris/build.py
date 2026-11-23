"""M1 build: write canonical ABC files and upgrade ``records.jsonl``.

Run after ``audit``.  Every library track is canonicalized with
:mod:`ostris.canonical` (structure only; ``M:``/``[K:...]`` preserved), the
canonical text is parsed again with the vendored parser, and the canonical
files are written under ``<out>/work/canonical/abc/``.  The per-track hash and
validation result are added to ``records.jsonl``.

The work directory is reproducible from the cache and is gitignored; the small
``canonical.json`` / ``canonical.md`` summaries are committed as evidence.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .canonical import canonicalize
from .contract import SKILL_VERSION, verify
from .links import link_library, load_inventory, record_id
from .parse import parse_abc
from .sources import Cache, SourceError

WORK_DIR = "work/canonical"
ABC_DIR = f"{WORK_DIR}/abc"

UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def canonical_filename(rid: str) -> str:
    return f"{UNSAFE.sub('_', rid)}.abc"


def _read_records(path: Path) -> list[dict]:
    if not path.is_file():
        raise SourceError(f"missing {path}; run `ostris_cli.py audit` first")
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


def build(
    cache_dir: str | Path,
    out_dir: str | Path,
    *,
    require_contract: bool = False,
) -> dict:
    cache = Cache(cache_dir)
    out = Path(out_dir)
    records_path = out / "records.jsonl"
    records = _read_records(records_path)

    inv = load_inventory(cache)
    links = {record_id(link): link for link in link_library(inv, cache)}

    contract_checks = verify()
    contract_ok = all(check["ok"] for check in contract_checks)

    abc_dir = out / ABC_DIR
    abc_dir.mkdir(parents=True, exist_ok=True)

    failures: list[dict] = []
    warnings: Counter[str] = Counter()
    voice_shapes: Counter[str] = Counter()
    meter_shapes: Counter[str] = Counter()
    hashes: Counter[str] = Counter()

    for record in records:
        rid = record.get("id", "")
        link = links.get(rid)
        canonical = canonicalize((link or {}).get("abc_text") or "")
        parsed = parse_abc(canonical.text) if canonical.ok else None

        filename = canonical_filename(rid)
        relative = f"{ABC_DIR}/{filename}"
        if canonical.ok:
            (out / relative).write_text(canonical.text, encoding="utf-8")
            hashes[canonical.sha256] += 1

        ok = canonical.ok and bool(parsed and parsed.ok)
        errors = list(canonical.errors)
        parse_error = parsed.error if parsed else "canonicalization failed"
        if parsed and not parsed.ok:
            errors.append(f"canonical parse failed: {parsed.error}")

        record["canonical"] = {
            **canonical.as_dict(),
            "uri": relative if canonical.ok else None,
            "bytes": len(canonical.text.encode("utf-8")) if canonical.ok else 0,
            "parse_ok": bool(parsed and parsed.ok),
            "parse_error": parse_error,
        }
        if not ok:
            record["exclude_from_priors"] = True
            if "canonical_failed" not in record.get("flags", []):
                record.setdefault("flags", []).append("canonical_failed")
            failures.append(
                {
                    "id": rid,
                    "out_name": record.get("out_name"),
                    "source": record.get("source"),
                    "errors": errors,
                    "parse_error": parse_error,
                }
            )
        for warning in canonical.warnings:
            warnings[warning] += 1
        if canonical.voices:
            voice_shapes["+".join(canonical.voices)] += 1
        meter_shapes[";".join(canonical.meters_declared)] += 1

    _write_records(records_path, records)

    duplicate_hashes = [
        {"sha256": digest, "count": count, "ids": [
            r["id"] for r in records if r.get("canonical", {}).get("sha256") == digest
        ]}
        for digest, count in hashes.items()
        if count > 1
    ]

    canonical_ok = len(records) - len(failures)
    checks = [
        {
            "name": "canonical_coverage",
            "required": True,
            "ok": canonical_ok == len(records),
            "detail": f"{canonical_ok}/{len(records)} canonical and re-parsed",
        },
        {
            "name": "two_voice_shape",
            "required": True,
            "ok": all(set(r.get("canonical", {}).get("voices", [])) >= {"Vocal", "Ins"} for r in records),
            "detail": "; ".join(f"{k}: {v}" for k, v in voice_shapes.items()),
        },
        {
            "name": "contract_pin",
            "required": require_contract,
            "ok": contract_ok,
            "detail": (
                f"skill {SKILL_VERSION} pins {'match' if contract_ok else 'drifted'}: "
                + ", ".join(
                    f"{c['artifact']}={c['detail']}" for c in contract_checks
                )
            ),
        },
        {
            "name": "unique_canonical_hashes",
            "required": False,
            "ok": not duplicate_hashes,
            "detail": (
                "all canonical hashes unique"
                if not duplicate_hashes
                else f"{len(duplicate_hashes)} repeated hashes"
            ),
        },
    ]

    summary = {
        "stage": "M1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cache": str(cache.root),
        "out": str(out.resolve()),
        "skill_version": SKILL_VERSION,
        "records": len(records),
        "canonical_ok": canonical_ok,
        "canonical_bytes": sum(
            r.get("canonical", {}).get("bytes", 0) for r in records
        ),
        "failures": failures,
        "warnings": dict(warnings),
        "voice_shapes": dict(voice_shapes),
        "meter_shapes": dict(meter_shapes.most_common()),
        "duplicate_hashes": duplicate_hashes,
        "contract": {"version": SKILL_VERSION, "checks": contract_checks, "ok": contract_ok},
        "checks": checks,
        "gate_pass": all(c["ok"] for c in checks if c["required"]),
        "records_file": str(records_path),
    }
    summary["files"] = write_summaries(out, summary)
    return summary


def write_summaries(out: Path, summary: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "canonical.json"
    md_path = out / "canonical.md"
    summary["files"] = {"canonical": str(json_path), "canonical_md": str(md_path)}
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return summary["files"]


def _markdown(summary: dict) -> str:
    lines = [
        "# OSTRIS M1 canonical build",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Gate: **{'PASS' if summary['gate_pass'] else 'FAIL'}**",
        f"- Canonical ABCs: {summary['canonical_ok']}/{summary['records']} "
        f"({summary['canonical_bytes'] / 1_000_000:.1f} MB)",
        f"- Skill contract: v{summary['skill_version']} "
        f"({'pinned' if summary['contract']['ok'] else '**drifted**'})",
        "",
        "## Checks",
        "",
        "| Check | Required | OK | Detail |",
        "|---|---|---|---|",
    ]
    for check in summary["checks"]:
        lines.append(
            f"| {check['name']} | {'yes' if check['required'] else 'no'} | "
            f"{'yes' if check['ok'] else '**no**'} | {check['detail']} |"
        )
    lines += ["", "## Voice / meter shape", ""]
    for name, count in summary["voice_shapes"].items():
        lines.append(f"- voices `{name}`: {count}")
    for name, count in summary["meter_shapes"].items():
        lines.append(f"- declared meters `{name}`: {count}")
    if summary["failures"]:
        lines += ["", "## Failures", ""]
        for failure in summary["failures"]:
            lines.append(
                f"- `{failure['id']}`: {'; '.join(failure['errors']) or failure['parse_error']}"
            )
    lines += [
        "",
        "Canonicalization is structural: line endings and trailing whitespace are",
        "normalized; music lines, per-bar `M:`, and inline `[K:...]` are preserved.",
        "The per-track hash is in `records.jsonl` under `canonical`.",
        "",
    ]
    return "\n".join(lines)
