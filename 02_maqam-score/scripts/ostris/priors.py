"""M3: objective priors from the 482-track corpus.

The corpus has no reviewed maqam labels, so every prior here is conditioned on
objective features only: meter, tempo, length, density, section count, key
mode, range, and chord vocabulary.  Each file records
``maqam_conditioned: false`` and the sample size it was built from.

Strata are intentionally coarse.  A stratum below ten tracks is omitted and
served by backoff instead of being reported as if it were evidence.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .sources import SourceError
from .stats import band, clip, confidence, distribution

PRIOR_VERSION = "m3-v1"
MIN_STRATUM = 10
COMBO_STRATUM = 12

BARS_BANDS = ([120, 180], ["short", "medium", "long"])
DENSITY_BANDS = ([2.0, 4.0], ["light", "medium", "busy"])
SECTION_BANDS = ([5, 8], ["few", "mid", "many"])

METRICS = (
    "bars",
    "tempo",
    "chords",
    "chords_per_bar",
    "vocal_notes",
    "ins_notes",
    "density",
    "silence",
    "span_semitones",
    "median_midi",
    "distinct_durations",
    "top_duration_share",
    "phrase_median_bars",
    "sections",
    "ties",
    "ins_active_share",
)


def _get(mapping: dict | None, *keys, default=None):
    node = mapping
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node if node is not None else default


def metric_row(record: dict) -> dict | None:
    """Flatten one record's M2 features into prior metrics."""
    features = record.get("features")
    if not features:
        return None
    vocal = features.get("vocal") or {}
    ins = features.get("ins") or {}
    bars = features.get("bars")
    ins_silence = ins.get("silence")
    ties = features.get("ties")
    if ties is None:
        # Older M2 rows: fall back to the duration model's tie count, then 0.
        ties = _get(features, "tie_groups", default=0)
    return {
        "bars": bars,
        "tempo": _get(features, "tempo", "bpm"),
        "chords": _get(features, "harmony", "chords"),
        "chords_per_bar": _get(features, "harmony", "per_bar"),
        "vocal_notes": vocal.get("notes"),
        "ins_notes": ins.get("notes"),
        "density": vocal.get("density_per_bar"),
        "silence": vocal.get("silence"),
        "span_semitones": vocal.get("span_semitones"),
        "median_midi": vocal.get("median_midi"),
        "distinct_durations": _get(vocal, "durations", "distinct"),
        "top_duration_share": _get(vocal, "durations", "top_share"),
        "phrase_median_bars": _get(vocal, "phrases", "median_bars"),
        "sections": _get(features, "sections", "source_count"),
        "ties": ties,
        "ins_active_share": (
            round(1.0 - float(ins_silence), 4)
            if isinstance(ins_silence, (int, float))
            else None
        ),
        "meter": _get(features, "meter", "family"),
        "mode": _get(features, "key", "mode"),
        "key": _get(features, "key", "name"),
    }


def _slug_piece(value: str) -> str:
    return str(value).strip().lower().replace("/", "_").replace(" ", "_")


def _tempo_band(bpm: float | None) -> str:
    if bpm is None:
        return "unknown"
    if bpm < 80:
        return "slow"
    if bpm <= 110:
        return "medium"
    return "fast"


def _stratum(slug: str, keys: dict, rows: list[dict], excluded: int) -> dict:
    values = {metric: [row[metric] for row in rows if row.get(metric) is not None]
              for metric in METRICS}
    return {
        "version": PRIOR_VERSION,
        "stratum": slug,
        "keys": keys,
        "n": len(rows),
        "excluded": excluded,
        "confidence": confidence(len(rows)),
        "maqam_conditioned": False,
        "maqam_reviewed": False,
        "source": "records.jsonl",
        "metrics": {metric: distribution(value) for metric, value in values.items()},
    }


def _collect_strata(rows: list[dict], excluded: int) -> dict[str, dict]:
    strata: dict[str, dict] = {"global": _stratum("global", {}, rows, excluded)}

    def add(slug: str, keys: dict, subset: list[dict], minimum: int = MIN_STRATUM) -> None:
        if len(subset) < minimum:
            return
        strata[slug] = _stratum(slug, keys, subset, excluded)

    by_meter: dict[str, list[dict]] = {}
    by_tempo: dict[str, list[dict]] = {}
    by_bars: dict[str, list[dict]] = {}
    by_density: dict[str, list[dict]] = {}
    by_sections: dict[str, list[dict]] = {}
    by_mode: dict[str, list[dict]] = {}
    for row in rows:
        by_meter.setdefault(row.get("meter") or "unknown", []).append(row)
        by_tempo.setdefault(_tempo_band(row.get("tempo")), []).append(row)
        by_bars.setdefault(band(row.get("bars"), *BARS_BANDS), []).append(row)
        by_density.setdefault(band(row.get("density"), *DENSITY_BANDS), []).append(row)
        by_sections.setdefault(band(row.get("sections"), *SECTION_BANDS), []).append(row)
        by_mode.setdefault(row.get("mode") or "unknown", []).append(row)

    for name, subset in by_meter.items():
        add(f"meter-{_slug_piece(name)}", {"meter": name}, subset)
    for name, subset in by_tempo.items():
        add(f"tempo-{_slug_piece(name)}", {"tempo_band": name}, subset)
    for name, subset in by_bars.items():
        add(f"bars-{_slug_piece(name)}", {"bars_band": name}, subset)
    for name, subset in by_density.items():
        add(f"density-{_slug_piece(name)}", {"density_band": name}, subset)
    for name, subset in by_sections.items():
        add(f"sections-{_slug_piece(name)}", {"sections_band": name}, subset)
    for name, subset in by_mode.items():
        add(f"mode-{_slug_piece(name)}", {"mode": name}, subset)

    # One interaction each for the two strongest signals, only when the cell
    # is big enough to be worth reporting.
    by_meter_tempo: dict[tuple[str, str], list[dict]] = {}
    by_meter_mode: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        meter = row.get("meter") or "unknown"
        by_meter_tempo.setdefault((meter, _tempo_band(row.get("tempo"))), []).append(row)
        by_meter_mode.setdefault((meter, row.get("mode") or "unknown"), []).append(row)
    for (meter, tempo), subset in by_meter_tempo.items():
        slug = f"meter-{_slug_piece(meter)}_tempo-{_slug_piece(tempo)}"
        add(slug, {"meter": meter, "tempo_band": tempo}, subset, COMBO_STRATUM)
    for (meter, mode), subset in by_meter_mode.items():
        slug = f"meter-{_slug_piece(meter)}_mode-{_slug_piece(mode)}"
        add(slug, {"meter": meter, "mode": mode}, subset, COMBO_STRATUM)

    return strata


def _meta(rows: list[dict]) -> dict:
    def top(values) -> list[dict]:
        return [
            {"value": value, "count": count}
            for value, count in Counter(values).most_common(10)
        ]

    return {
        "meters": top([row.get("meter") or "unknown" for row in rows]),
        "tempo_bands": top([_tempo_band(row.get("tempo")) for row in rows]),
        "modes": top([row.get("mode") or "unknown" for row in rows]),
        "keys": top([row.get("key") or "unknown" for row in rows]),
        "tempo": distribution([row["tempo"] for row in rows if row.get("tempo") is not None]),
        "sections": distribution(
            [row["sections"] for row in rows if row.get("sections") is not None]
        ),
    }


def build_priors(out_dir: str | Path, *, require_contract: bool = False) -> dict:
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
    excluded = 0
    missing_features = 0
    for record in records:
        if record.get("exclude_from_priors"):
            excluded += 1
            continue
        row = metric_row(record)
        if row is None or row.get("bars") is None:
            missing_features += 1
            excluded += 1
            continue
        row["track_id"] = record.get("id")
        rows.append(row)

    if not rows:
        raise SourceError("no eligible records with M2 features; run `ostris_cli.py features`")

    strata = _collect_strata(rows, excluded)
    priors = {
        "stage": "M3",
        "version": PRIOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "out": str(out.resolve()),
        "records": len(records),
        "eligible": len(rows),
        "excluded": excluded,
        "missing_features": missing_features,
        "maqam_conditioned": False,
        "maqam_reviewed": False,
        "strata_count": len(strata),
        "global": "global",
        "meta": _meta(rows),
        "strata": strata,
        "limitations": [
            "Priors are conditioned on objective features only; no maqam labels exist.",
            "Strata below ten tracks are omitted; callers must use the backoff chain.",
            "Quantiles describe this corpus, not a target style or a correctness bound.",
        ],
    }
    checks = [
        {
            "name": "prior_coverage",
            "required": True,
            "ok": len(rows) + excluded == len(records),
            "detail": f"{len(rows)} eligible + {excluded} excluded = {len(records)} records",
        },
        {
            "name": "maqam_conditioned",
            "required": True,
            "ok": not priors["maqam_conditioned"],
            "detail": "every prior is objective-only",
        },
        {
            "name": "global_sample",
            "required": True,
            "ok": strata["global"]["n"] == len(rows),
            "detail": f"{strata['global']['n']} tracks in the global prior",
        },
        {
            "name": "no_empty_metric",
            "required": True,
            "ok": all(
                strata["global"]["metrics"][metric]["n"] > 0
                for metric in ("bars", "tempo")
            ),
            "detail": "the global prior has bars and tempo observations",
        },
    ]
    if require_contract:
        from .contract import verify

        contract_checks = verify()
        checks.append(
            {
                "name": "contract_pin",
                "required": True,
                "ok": all(check["ok"] for check in contract_checks),
                "detail": ", ".join(
                    f"{check['artifact']}={check['detail']}" for check in contract_checks
                ),
            }
        )
    priors["checks"] = checks
    priors["gate_pass"] = all(check["ok"] for check in checks if check["required"])
    priors["files"] = write_priors(out, priors)
    return priors


def write_priors(out: Path, priors: dict) -> dict:
    folder = out / "priors"
    folder.mkdir(parents=True, exist_ok=True)
    index_path = folder / "priors.json"
    md_path = folder / "priors.md"
    files = {"priors": str(index_path), "priors_md": str(md_path), "strata": {
        slug: str(folder / f"{slug}.json") for slug in priors["strata"]
    }}
    index = {key: value for key, value in priors.items() if key != "files"}
    index["files"] = files
    index_path.write_text(
        json.dumps(index, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for slug, stratum in priors["strata"].items():
        path = folder / f"{slug}.json"
        path.write_text(
            json.dumps(stratum, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    md_path.write_text(_markdown(priors), encoding="utf-8")
    return files


def load_priors(path: str | Path) -> dict:
    path = Path(path)
    if path.is_dir():
        for candidate in (path / "priors.json", path / "priors" / "priors.json"):
            if candidate.is_file():
                path = candidate
                break
        else:
            path = path / "priors" / "priors.json"
    if not path.is_file():
        raise SourceError(f"missing {path}; run `ostris_cli.py priors` first")
    priors = json.loads(path.read_text(encoding="utf-8"))
    if priors.get("maqam_conditioned"):
        raise SourceError(f"{path} is maqam-conditioned; this build must stay objective")
    return priors


def select_prior(
    priors: dict,
    *,
    meter: str | None = None,
    tempo: float | None = None,
    bars: float | None = None,
    mode: str | None = None,
) -> dict:
    """Return the best available stratum plus the backoff chain that was tried."""
    strata = priors["strata"]
    meter_piece = _slug_piece(meter) if meter else None
    tempo_piece = _slug_piece(_tempo_band(tempo)) if tempo is not None else None
    bars_piece = _slug_piece(band(bars, *BARS_BANDS)) if bars is not None else None
    mode_piece = _slug_piece(mode) if mode else None

    candidates: list[str] = []
    if meter_piece and tempo_piece:
        candidates.append(f"meter-{meter_piece}_tempo-{tempo_piece}")
    if meter_piece and mode_piece:
        candidates.append(f"meter-{meter_piece}_mode-{mode_piece}")
    if meter_piece:
        candidates.append(f"meter-{meter_piece}")
    if tempo_piece:
        candidates.append(f"tempo-{tempo_piece}")
    if bars_piece:
        candidates.append(f"bars-{bars_piece}")
    if mode_piece:
        candidates.append(f"mode-{mode_piece}")
    candidates.append("global")

    for slug in candidates:
        stratum = strata.get(slug)
        if stratum and stratum.get("n", 0) >= MIN_STRATUM:
            return {
                "stratum": slug,
                "n": stratum["n"],
                "confidence": stratum["confidence"],
                "backoff": candidates,
                "data": stratum,
            }
    return {
        "stratum": "global",
        "n": strata["global"]["n"],
        "confidence": strata["global"]["confidence"],
        "backoff": candidates,
        "data": strata["global"],
    }


def _markdown(priors: dict) -> str:
    lines = [
        "# OSTRIS M3 priors (objective features only)",
        "",
        f"- Generated: `{priors['generated_at']}`",
        f"- Gate: **{'PASS' if priors['gate_pass'] else 'FAIL'}**",
        f"- Eligible tracks: {priors['eligible']} / {priors['records']}",
        f"- Excluded: {priors['excluded']} (duplicates, unparsed, no features)",
        f"- Strata: {priors['strata_count']}",
        "- Maqam-conditioned: **no** (no reviewed labels exist)",
        "",
        "## Global shape",
        "",
        "| Metric | n | min | p10 | median | p90 | max |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for metric in METRICS:
        dist = priors["strata"]["global"]["metrics"][metric]
        lines.append(
            f"| {metric} | {dist['n']} | {dist['min']} | {dist['p10']} | "
            f"{dist['median']} | {dist['p90']} | {dist['max']} |"
        )
    lines += [
        "",
        "## Strata",
        "",
        "| Stratum | n | Confidence |",
        "|---|---:|---|",
    ]
    for slug, stratum in sorted(priors["strata"].items()):
        lines.append(f"| `{slug}` | {stratum['n']} | {stratum['confidence']} |")
    lines += ["", "## Limits", ""]
    for limitation in priors["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)


def plan_targets(priors: dict, *, bars: int, meter: str, tempo: float,
                 mode: str | None = None) -> dict:
    """Build the numeric targets a plan needs from one prior stratum.

    Values are quantile-derived and clamped to ranges the skill checker treats
    as sane, so a generated plan cannot ask for a degenerate score.
    """
    selected = select_prior(priors, meter=meter, tempo=tempo, bars=bars, mode=mode)
    data = selected["data"]
    metrics = data["metrics"]

    def median(metric: str, fallback: float) -> float:
        value = metrics.get(metric, {}).get("median")
        return float(value) if value is not None else fallback

    def quantile(metric: str, name: str, fallback: float) -> float:
        value = metrics.get(metric, {}).get(name)
        return float(value) if value is not None else fallback

    prior_bars = median("bars", float(bars))
    scale = bars / prior_bars if prior_bars else 1.0
    vocal_notes = median("vocal_notes", bars * 3.0) * scale
    melisma = 1.30

    return {
        "selection": selected,
        "syllables": max(8, int(round(vocal_notes / melisma))),
        "melisma_min": 1.20,
        "melisma_max": 1.45,
        "register": {
            "mean": int(round(median("median_midi", 74.0))),
            "top": max(80, int(math.ceil(quantile("median_midi", "p90", 82.0)))),
            "tolerance": 5,
        },
        "max_top_duration_share": round(
            clip(quantile("top_duration_share", "p75", 0.35), 0.20, 0.60), 2
        ),
        "min_distinct_durations": max(
            4, int(math.floor(quantile("distinct_durations", "p25", 6.0)))
        ),
        "ties_min": max(4, int(math.floor(quantile("ties", "p25", 8.0)))),
        "min_fill_notes": 2,
        "chords_min": max(
            4, int(math.floor(median("chords_per_bar", 1.2) * bars))
        ),
    }
