"""M0 audit: verify the corpus inventory, link every library track, parse it.

Outputs (written under ``--out``):

* ``audit.json`` — machine-readable inventory, link coverage, parse failures,
  quality flags, held-out list, and gate checks;
* ``audit.md`` — a short human summary;
* ``manifest_links.csv`` — one row per library track (482 rows);
* ``records.jsonl`` — one M0 ``track_record`` per library track;
* ``held_out.jsonl`` — the 35 YT500 transcripts not used by the library.

This is the only stage the plan allows before the pre-execution decisions are
resolved.  It does not build priors, idioms, or an online plan.
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .links import (
    FADL_OUT_NAME,
    YT_OUT_NAME,
    duplicate_groups,
    held_out_yt500,
    link_library,
    load_inventory,
    record_id,
)
from .parse import parse_abc
from .quality import assess
from .sources import Cache, SourceError

EXPECTED = {
    "instrumental": 482,
    "audio_bytes": 3_162_110_202,
    "audio_hours": 36.6,
    "yt500_transcribed": 495,
    "yt500_matched": 460,
    "fadl_matched": 22,
    "held_out": 35,
    "duplicate_groups": 5,
    "duplicate_tracks": 10,
    "v3": 438,
    "v3_by_maqam": {"Ajam": 118, "Nahawand": 112, "Hijaz": 107, "Kurd": 101},
}


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def _distribution(values: list[float]) -> dict:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return {"n": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None}
    return {
        "n": len(clean),
        "min": round(min(clean), 3),
        "p25": round(_quantile(clean, 0.25), 3),
        "median": round(statistics.median(clean), 3),
        "p75": round(_quantile(clean, 0.75), 3),
        "max": round(max(clean), 3),
    }


def _counter(values) -> dict:
    return dict(Counter(values).most_common())


def _summary_qc(qc: dict | None) -> dict:
    qc = qc or {}
    return {
        "coverage": qc.get("coverage"),
        "flags": qc.get("flags") or [],
        "measures": qc.get("measures"),
        "chord_symbols": qc.get("chord_symbols"),
        "sections": qc.get("sections"),
        "instrumental": qc.get("instrumental"),
        "vocal_median_midi": qc.get("vocal_median_midi"),
    }


def build_records(links: list[dict]) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    failures: list[dict] = []
    for link in links:
        rid = record_id(link)
        parsed = parse_abc(link.get("abc_text"))
        quality = assess(
            parsed,
            audio_duration_s=link.get("audio_duration_s"),
            transcribe_status=link.get("transcribe_status"),
            source_qc=link.get("source_qc"),
            duplicate_of=link.get("duplicate_of"),
            duplicate_group=link.get("duplicate_group"),
            selected_status=link.get("selected_transcribe_status"),
        )
        if not link.get("matched"):
            quality.flags.append("unmatched")
        if not link.get("abc_text"):
            quality.flags.append("abc_missing")
        abc_sha = (
            hashlib.sha256(link["abc_text"].encode("utf-8")).hexdigest()
            if link.get("abc_text")
            else None
        )
        record = {
            "id": rid,
            "source": link.get("source_dataset"),
            "source_rank": link.get("source_rank"),
            "video_id": link.get("video_id"),
            "out_name": link.get("out_name"),
            "title": link.get("title"),
            "artist": link.get("artist"),
            "duration_s": link.get("audio_duration_s"),
            "audio_uri": link.get("audio_uri"),
            "abc_uri": link.get("abc_uri"),
            "abc_kind": link.get("abc_kind"),
            "abc_sha256": abc_sha,
            "reference_abc_uri": link.get("reference_abc_uri"),
            "selected_transcript_uri": link.get("selected_transcript_uri"),
            "key": parsed.header_key,
            "tempo": parsed.tempo,
            "meter": parsed.header_meter,
            "meters": parsed.meters,
            "keys": parsed.keys,
            "bars": parsed.bars,
            "section_count": (link.get("source_qc") or {}).get("sections"),
            "voices": ["Vocal", "Ins"],
            "range": parsed.range,
            "notes": parsed.notes,
            "chords": parsed.chords,
            "density": round(parsed.density, 4) if parsed.density is not None else None,
            "silence": round(parsed.silence, 4) if parsed.silence is not None else None,
            "sounding_seconds": (
                round(parsed.sounding_seconds, 3)
                if parsed.sounding_seconds is not None
                else None
            ),
            "quality_score": round(quality.score, 3),
            "flags": quality.flags,
            "exclude_from_priors": quality.exclude_from_priors,
            "duplicate_of": link.get("duplicate_of"),
            "duplicate_group": link.get("duplicate_group"),
            "maqam": None,
            "maqam_confidence": None,
            "maqam_source": "unlabelled",
            "provenance": {
                "abc": link.get("abc_uri"),
                "abc_kind": link.get("abc_kind"),
                "abc_sha256": abc_sha,
                "audio": link.get("audio_uri"),
                "audio_duration_s": link.get("audio_duration_s"),
                "link_method": link.get("match_method"),
                "transcript_id": link.get("transcript_id"),
                "source_qc": _summary_qc(link.get("source_qc")),
            },
            "qc": {
                "duration_mismatch": quality.duration_mismatch,
                "parse_ok": parsed.ok,
                "parse_error": parsed.error,
                "notes": link.get("notes") or [],
            },
        }
        records.append(record)
        if not parsed.ok:
            failures.append(
                {
                    "id": rid,
                    "out_name": link.get("out_name"),
                    "title": link.get("title"),
                    "source": link.get("source_dataset"),
                    "abc_uri": link.get("abc_uri"),
                    "abc_kind": link.get("abc_kind"),
                    "error": parsed.error,
                    "notes": link.get("notes") or [],
                }
            )
    return records, failures


def _inventory(inv, records: list[dict], links: list[dict], failures: list[dict], shard_files: int) -> dict:
    inst = inv.instrumental
    yt_counts = inv.yt_header.get("counts", {})
    yt_status = Counter(t.get("transcribe_status") for t in inv.yt_tracks)
    fadl_selected_tracks = inv.fadl_selected.get("tracks", [])
    fadl_selected_ok = sum(1 for t in fadl_selected_tracks if t.get("abc"))
    album_tracks = [
        track for album in inv.fadl_albums for track in album.get("tracks", [])
    ]
    v3_tracks = inv.v3.get("tracks", [])
    v3_by_maqam = Counter(t.get("maqam") for t in v3_tracks)

    by_source = Counter(link.get("source_dataset") for link in links)
    matched = sum(1 for link in links if link.get("matched"))
    abc_missing = sum(1 for link in links if not link.get("abc_text"))
    selected_missing = sum(
        1
        for link in links
        if link.get("source_dataset") == "fadhl_shaker_shortlist"
        and not link.get("selected_abc_text")
    )
    return {
        "instrumental": {
            "count": inst.get("count"),
            "audio_bytes": inst.get("audio_bytes"),
            "audio_hours": inst.get("audio_hours"),
            "sources": inst.get("sources"),
            "checks": inst.get("checks"),
        },
        "yt500": {
            "manifest_counts": yt_counts,
            "manifest_tracks": len(inv.yt_manifest),
            "shard_tracks": len(inv.yt_tracks),
            "shard_files": shard_files,
            "transcript_status": dict(yt_status),
            "missing_abc": sum(1 for t in inv.yt_tracks if not t.get("abc")),
            "duplicate_groups": len(duplicate_groups(inv)),
            "duplicate_tracks": sum(len(g["tracks"]) for g in duplicate_groups(inv)),
        },
        "fadl": {
            "shortlist_count": len(inv.fadl_shortlist.get("tracks", [])),
            "shortlist_counts": inv.fadl_shortlist.get("counts"),
            "selected_tracks": len(fadl_selected_tracks),
            "selected_with_abc": fadl_selected_ok,
            "selected_missing_abc": len(fadl_selected_tracks) - fadl_selected_ok,
            "albums": len(inv.fadl_albums),
            "album_tracks": len(album_tracks),
            "album_with_abc": sum(1 for t in album_tracks if t.get("abc")),
        },
        "v3_labels": {
            "count": inv.v3.get("count"),
            "by_maqam": dict(v3_by_maqam),
            "excluded_from_priors": True,
            "role": "cross-check only; never priors or eval",
        },
        "links": {
            "total": len(links),
            "matched": matched,
            "unmatched": len(links) - matched,
            "by_source": dict(by_source),
            "abc_missing": abc_missing,
            "fadl_selected_transcript_missing": selected_missing,
        },
        "parse": {
            "ok": len(records) - len(failures),
            "failed": len(failures),
            "ok_rate": round((len(records) - len(failures)) / len(records), 4)
            if records
            else 0.0,
        },
    }


def _distributions(records: list[dict]) -> dict:
    parsed = [r for r in records if r["qc"]["parse_ok"]]
    flags = Counter(flag for record in records for flag in record.get("flags", []))
    return {
        "bars": _distribution([r["bars"] for r in parsed]),
        "tempo": _distribution([r["tempo"] for r in parsed]),
        "notes_vocal": _distribution([r["notes"]["vocal"] for r in parsed]),
        "notes_ins": _distribution([r["notes"]["ins"] for r in parsed]),
        "chords": _distribution([r["chords"] for r in parsed]),
        "density": _distribution([r["density"] for r in parsed]),
        "silence": _distribution([r["silence"] for r in parsed]),
        "duration_mismatch": _distribution(
            [record["qc"]["duration_mismatch"] for record in records]
        ),
        "quality_score": _distribution([r["quality_score"] for r in records]),
        "meters": _counter(m for r in parsed for m in r["meters"]),
        "keys": _counter(r["key"] for r in parsed),
        "flags": dict(flags.most_common()),
        "exclude_from_priors": sum(1 for r in records if r["exclude_from_priors"]),
    }


def _checks(inv, records: list[dict], links: list[dict], failures: list[dict]) -> list[dict]:
    counts = inv.yt_header.get("counts", {})
    v3_by = Counter(t.get("maqam") for t in inv.v3.get("tracks", []))
    by_source = Counter(link.get("source_dataset") for link in links)
    matched_by_source = Counter(
        link.get("source_dataset") for link in links if link.get("matched")
    )
    held = held_out_yt500(inv)
    groups = duplicate_groups(inv)
    dup_tracks = sum(len(g["tracks"]) for g in groups)
    parse_ok = len(records) - len(failures)
    quality_ok = sum(1 for r in records if not r["exclude_from_priors"])
    checks = [
        {
            "name": "instrumental_count",
            "required": True,
            "ok": inv.instrumental.get("count") == EXPECTED["instrumental"],
            "detail": f"{inv.instrumental.get('count')} (expected {EXPECTED['instrumental']})",
        },
        {
            "name": "audio_inventory",
            "required": True,
            "ok": inv.instrumental.get("audio_bytes") == EXPECTED["audio_bytes"]
            and abs((inv.instrumental.get("audio_hours") or 0) - EXPECTED["audio_hours"]) < 0.1,
            "detail": f"{inv.instrumental.get('audio_bytes')} bytes, {inv.instrumental.get('audio_hours')} h",
        },
        {
            "name": "yt500_transcribed",
            "required": True,
            "ok": counts.get("n_transcribed") == EXPECTED["yt500_transcribed"],
            "detail": f"{counts.get('n_transcribed')} transcribed (expected {EXPECTED['yt500_transcribed']})",
        },
        {
            "name": "yt500_link_coverage",
            "required": True,
            "ok": matched_by_source.get("yt500") == EXPECTED["yt500_matched"],
            "detail": f"{matched_by_source.get('yt500')}/{by_source.get('yt500')} matched",
        },
        {
            "name": "fadl_link_coverage",
            "required": True,
            "ok": matched_by_source.get("fadhl_shaker_shortlist") == EXPECTED["fadl_matched"],
            "detail": (
                f"{matched_by_source.get('fadhl_shaker_shortlist')}/"
                f"{by_source.get('fadhl_shaker_shortlist')} matched"
            ),
        },
        {
            "name": "held_out_count",
            "required": True,
            "ok": len(held) == EXPECTED["held_out"],
            "detail": f"{len(held)} unused YT500 transcripts (expected {EXPECTED['held_out']})",
        },
        {
            "name": "duplicate_inventory",
            "required": True,
            "ok": len(groups) == EXPECTED["duplicate_groups"]
            and dup_tracks == EXPECTED["duplicate_tracks"],
            "detail": f"{len(groups)} groups / {dup_tracks} tracks",
        },
        {
            "name": "v3_label_counts",
            "required": True,
            "ok": inv.v3.get("count") == EXPECTED["v3"]
            and dict(v3_by) == EXPECTED["v3_by_maqam"],
            "detail": f"{inv.v3.get('count')} labels: {dict(v3_by)}",
        },
        {
            "name": "parse_coverage",
            "required": True,
            "ok": parse_ok / len(records) >= 0.95 if records else False,
            "detail": f"{parse_ok}/{len(records)} = {parse_ok / len(records):.1%}" if records else "no records",
        },
        {
            "name": "prior_candidate_coverage",
            "required": False,
            "ok": quality_ok / len(records) >= 0.90 if records else False,
            "detail": f"{quality_ok}/{len(records)} not excluded from priors",
        },
    ]
    return checks


def write_outputs(out_dir: Path, records: list[dict], links: list[dict], summary: dict, inv) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "audit": out_dir / "audit.json",
        "audit_md": out_dir / "audit.md",
        "links": out_dir / "manifest_links.csv",
        "records": out_dir / "records.jsonl",
        "held_out": out_dir / "held_out.jsonl",
    }
    summary["files"] = {key: str(path) for key, path in files.items()}
    files["audit"].write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with files["records"].open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with files["held_out"].open("w", encoding="utf-8") as handle:
        for track in held_out_yt500(inv):
            handle.write(json.dumps(track, ensure_ascii=False) + "\n")

    columns = [
        "out_name",
        "source_dataset",
        "title",
        "artist",
        "matched",
        "match_method",
        "transcript_id",
        "abc_uri",
        "abc_kind",
        "transcribe_status",
        "parse_ok",
        "bars",
        "notes_vocal",
        "notes_ins",
        "chords",
        "quality_score",
        "exclude_from_priors",
        "flags",
        "notes",
    ]
    by_id = {r["out_name"]: r for r in records}
    with files["links"].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for link in links:
            record = by_id.get(link.get("out_name"), {})
            row = {
                "out_name": link.get("out_name"),
                "source_dataset": link.get("source_dataset"),
                "title": link.get("title"),
                "artist": link.get("artist"),
                "matched": link.get("matched"),
                "match_method": link.get("match_method"),
                "transcript_id": link.get("transcript_id"),
                "abc_uri": link.get("abc_uri"),
                "abc_kind": link.get("abc_kind"),
                "transcribe_status": link.get("transcribe_status"),
                "parse_ok": record.get("qc", {}).get("parse_ok"),
                "bars": record.get("bars"),
                "notes_vocal": record.get("notes", {}).get("vocal"),
                "notes_ins": record.get("notes", {}).get("ins"),
                "chords": record.get("chords"),
                "quality_score": record.get("quality_score"),
                "exclude_from_priors": record.get("exclude_from_priors"),
                "flags": ";".join(record.get("flags", [])),
                "notes": ";".join(link.get("notes", [])),
            }
            writer.writerow(row)
    files["audit_md"].write_text(_markdown(summary), encoding="utf-8")
    return summary["files"]


def _markdown(summary: dict) -> str:
    inv = summary["inventory"]
    counts = inv["links"]
    parse = inv["parse"]
    lines = [
        "# OSTRIS M0 audit",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Cache: `{summary['cache']}`",
        f"- Gate: **{'PASS' if summary['gate_pass'] else 'FAIL'}**",
        "",
        "## Inventory",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Instrumental library | {inv['instrumental']['count']} |",
        f"| YT500 manifest tracks | {inv['yt500']['manifest_tracks']} |",
        f"| YT500 shard tracks | {inv['yt500']['shard_tracks']} |",
        f"| YT500 transcripts missing ABC | {inv['yt500']['missing_abc']} |",
        f"| FADL shortlist | {inv['fadl']['shortlist_count']} |",
        f"| FADL selected-score tracks | {inv['fadl']['selected_tracks']} |",
        f"| FADL album set | {inv['fadl']['albums']} albums / {inv['fadl']['album_tracks']} tracks |",
        f"| v3 maqam labels (excluded from priors) | {inv['v3_labels']['count']} |",
        "",
        "## Links and parse",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Library tracks | {counts['total']} |",
        f"| Matched | {counts['matched']} |",
        f"| Unmatched | {counts['unmatched']} |",
        f"| Missing primary ABC | {counts['abc_missing']} |",
        f"| FADL tracks without a selected transcript | {counts['fadl_selected_transcript_missing']} |",
        f"| ABC parse OK | {parse['ok']} ({parse['ok_rate']:.1%}) |",
        f"| ABC parse failures | {parse['failed']} |",
        f"| Excluded from priors | {summary['distributions']['exclude_from_priors']} |",
        "",
    ]
    failures = summary.get("parse_failures", [])
    if failures:
        lines += ["## Parse failures", ""]
        for failure in failures:
            lines.append(
                f"- `{failure['id']}` — {failure['error']} ({failure.get('abc_kind')})"
            )
        lines.append("")
    lines += ["## Gate checks", "", "| Check | OK | Detail |", "|---|---|---|"]
    for check in summary["checks"]:
        mark = "yes" if check["ok"] else "**no**"
        lines.append(f"| {check['name']} | {mark} | {check['detail']} |")
    lines += [
        "",
        "## Notes",
        "",
        "- The 35 YT500 transcripts absent from the 482-track library are the natural held-out set.",
        "- The 5 duplicate groups (10 tracks) are excluded from priors and eval.",
        "- The 438 v3 maqam labels are audio+caption labels, not ABC; they are cross-check only.",
        "- The 22 FADL shortlist tracks link to the selected-scores transcript when it exists,",
        "  otherwise to the reference conditioner ABC used for the instrumental render.",
        "- `TRANSCRIPTS/FADL_SHAKER` is a broader 15-album set; the exact 22-track source is",
        "  `TRANSCRIPTS/fadhl_shaker_selected_scores` plus the shortlist reference ABCs.",
        "",
    ]
    return "\n".join(lines)


def audit(cache_dir: str | Path, out_dir: str | Path) -> dict:
    cache = Cache(cache_dir)
    inv = load_inventory(cache)
    links = link_library(inv, cache)
    records, failures = build_records(links)
    shard_files = len(list(cache.glob("TRANSCRIPTS/YT500/YT500/abc/shard-*.json")))
    summary = {
        "stage": "M0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cache": str(cache.root),
        "inventory": _inventory(inv, records, links, failures, shard_files),
        "distributions": _distributions(records),
        "parse_failures": failures,
        "duplicates": duplicate_groups(inv),
        "held_out": held_out_yt500(inv),
        "fadl_mapping": [
            {
                "out_name": link.get("out_name"),
                "stem": link.get("fadl_stem"),
                "reference_abc_uri": link.get("reference_abc_uri"),
                "selected_transcript_uri": link.get("selected_transcript_uri"),
                "selected_transcribe_status": link.get("selected_transcribe_status"),
                "abc_kind": link.get("abc_kind"),
                "parse_ok": next(
                    (r["qc"]["parse_ok"] for r in records if r["out_name"] == link.get("out_name")),
                    None,
                ),
                "flags": next(
                    (r["flags"] for r in records if r["out_name"] == link.get("out_name")),
                    [],
                ),
            }
            for link in links
            if link.get("source_dataset") == "fadhl_shaker_shortlist"
        ],
    }
    summary["checks"] = _checks(inv, records, links, failures)
    summary["gate_pass"] = all(c["ok"] for c in summary["checks"] if c["required"])
    write_outputs(Path(out_dir), records, links, summary, inv)
    return summary
