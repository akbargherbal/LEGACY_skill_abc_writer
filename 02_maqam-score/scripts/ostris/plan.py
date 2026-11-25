"""M3: generate ``brief.json`` + ``skill_plan.json`` from objective priors.

A manifest supplies the creative brief (key, tempo, length, sections).  Anything
it leaves out is filled from the matching prior stratum and recorded as an
assumption.  The output never claims a maqam: ``maqam`` is null and
``maqam_conditioned`` is false.

Run after ``priors``::

    ostris_cli.py plan --manifest song.json --out plans/song
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from .priors import load_priors, plan_targets
from .sources import SourceError

PLAN_VERSION = "0.8.0"
REQUIRED_PLAN_KEYS = (
    "key",
    "tempo",
    "meter",
    "unit",
    "bars",
    "syllables",
    "sections",
    "melisma_min",
    "melisma_max",
    "register",
    "max_top_duration_share",
    "min_distinct_durations",
    "ties_min",
    "min_fill_notes",
    "chords_min",
)
METER = re.compile(r"^(\d+)/(\d+)$")
DEFAULT_SECTIONS = (
    ("intro", 0.08),
    ("verse 1", 0.22),
    ("chorus", 0.20),
    ("verse 2", 0.20),
    ("chorus", 0.20),
    ("outro", 0.10),
)


def validate_plan(plan: dict) -> list[str]:
    """Return human-readable errors; an empty list means the plan is valid."""
    errors = []
    missing = [key for key in REQUIRED_PLAN_KEYS if key not in plan]
    if missing:
        errors.append("missing: " + ", ".join(missing))
        return errors
    if not isinstance(plan["bars"], int) or plan["bars"] <= 0:
        errors.append("bars must be a positive integer")
    if not isinstance(plan["tempo"], (int, float)) or plan["tempo"] <= 0:
        errors.append("tempo must be positive")
    if not METER.match(str(plan["meter"])):
        errors.append("meter must look like 4/4")
    if not re.match(r"^1/\d+$", str(plan["unit"])):
        errors.append("unit must look like 1/16")
    sections = plan["sections"]
    if not isinstance(sections, list) or not sections or not all(
        isinstance(item, str) and item.strip() for item in sections
    ):
        errors.append("sections must be a non-empty list of names")
    if "section_bars" in plan and sum(int(value) for value in plan["section_bars"]) != plan["bars"]:
        errors.append("section_bars must sum to bars")
    if not isinstance(plan["syllables"], int) or plan["syllables"] <= 0:
        errors.append("syllables must be a positive integer")
    if float(plan["melisma_min"]) >= float(plan["melisma_max"]):
        errors.append("melisma_min must be below melisma_max")
    register = plan["register"]
    if not isinstance(register, dict) or not {"mean", "top", "tolerance"} <= set(register):
        errors.append("register needs mean, top, and tolerance")
    elif int(register["top"]) <= int(register["mean"]):
        errors.append("register.top must exceed register.mean")
    for key, minimum in (
        ("max_top_duration_share", 0.0),
        ("min_distinct_durations", 1),
        ("ties_min", 0),
        ("min_fill_notes", 0),
        ("chords_min", 0),
        ("max_unbroken_seconds", 0.1),
        ("min_phrase_endings", 1),
        ("tessitura_share_ge_c5_max", 0.0),
        ("chorus_lift_min", 0.0),
        ("maqam_fit_min", 0.0),
    ):
        if key in plan and float(plan[key]) < minimum:
            errors.append(f"{key} must be >= {minimum}")
    maqam = plan.get("maqam")
    if maqam is not None:
        if not isinstance(maqam, dict):
            errors.append("maqam must be null or an object")
        elif not {"name", "tonic", "degrees"} <= set(maqam):
            errors.append("maqam needs name, tonic, and degrees")
    return errors


def _bar_seconds(meter: str, tempo: float) -> float:
    match = METER.match(str(meter))
    if not match or tempo <= 0:
        return 2.0
    numerator, denominator = int(match.group(1)), int(match.group(2))
    quarters = numerator * 4 / denominator
    return quarters * 60 / tempo


def _derive_bars(manifest: dict, tempo: float, meter: str) -> tuple[int, bool]:
    if manifest.get("bars"):
        return int(manifest["bars"]), False
    seconds = manifest.get("target_duration_s") or manifest.get("duration_s")
    if not seconds:
        return 64, True
    per_bar = _bar_seconds(meter, tempo)
    bars = max(8, int(round(float(seconds) / per_bar / 4)) * 4)
    return bars, False


def _normalize_sections(manifest: dict, bars: int) -> list[dict]:
    raw = manifest.get("sections")
    max_sections = max(1, bars // 2)
    if isinstance(raw, list) and raw:
        if all(isinstance(item, dict) for item in raw):
            weights = [
                (str(item.get("name") or f"section {index + 1}"), item.get("bars"))
                for index, item in enumerate(raw)
            ]
            declared = sum(int(value) for _name, value in weights if value)
            if declared:
                scale = bars / declared
                sections = []
                for name, value in weights:
                    target = int(value) if value else 0
                    sections.append({"name": name, "bars": max(2, int(round(target * scale)))})
                return _balance(sections[:max_sections], bars)
        names = [item.get("name") if isinstance(item, dict) else item for item in raw]
        weights = [(str(name), None) for name in names]
    else:
        weights = list(DEFAULT_SECTIONS)
    weights = weights[:max_sections]
    total_weight = sum(weight for _name, weight in weights if weight is not None) or len(weights)
    sections = []
    for name, weight in weights:
        share = (weight if weight is not None else 1.0) / total_weight
        sections.append({"name": name, "bars": max(2, int(round(bars * share)))})
    return _balance(sections, bars)


def _balance(sections: list[dict], bars: int) -> list[dict]:
    """Force the section bars to sum to ``bars`` with a minimum of two each."""
    total = sum(section["bars"] for section in sections)
    guard = 0
    while total != bars and guard < 10_000:
        guard += 1
        if total < bars:
            index = max(range(len(sections)), key=lambda i: sections[i]["bars"])
            sections[index]["bars"] += 1
            total += 1
        else:
            candidates = [i for i, section in enumerate(sections) if section["bars"] > 2]
            if not candidates:
                break
            index = max(candidates, key=lambda i: sections[i]["bars"])
            sections[index]["bars"] -= 1
            total -= 1
    return sections


def _top_value(meta: dict, name: str, skip: set[str] | None = None) -> str | None:
    skip = skip or set()
    for item in meta.get(name, []):
        value = item.get("value")
        if value and value not in skip:
            return str(value)
    return None


def build_plan(manifest: dict, priors: dict, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assumptions: list[str] = []
    warnings: list[str] = []
    meta = priors.get("meta", {})

    meter = manifest.get("meter") or _top_value(meta, "meters", {"mixed", "unknown"}) or "4/4"
    if not manifest.get("meter"):
        assumptions.append(f"meter taken from the prior: {meter}")

    tempo = manifest.get("tempo")
    if tempo is None:
        tempo = (meta.get("tempo") or {}).get("median") or 100
        assumptions.append(f"tempo taken from the prior median: {tempo}")
    tempo = int(round(float(tempo)))

    key = manifest.get("key")
    if not key:
        key = _top_value(meta, "keys", {"unknown"}) or "C"
        assumptions.append(f"key taken from the most common corpus key: {key}")

    bars, bars_assumed = _derive_bars(manifest, tempo, meter)
    if bars_assumed:
        assumptions.append("bars defaulted to 64 because no bars or duration was given")
    sections = _normalize_sections(manifest, bars)

    targets = plan_targets(priors, bars=bars, meter=meter, tempo=tempo)
    selection = targets["selection"]

    plan = {
        "plan_version": PLAN_VERSION,
        "key": key,
        "tempo": tempo,
        "meter": meter,
        "unit": "1/16",
        "bars": bars,
        "syllables": targets["syllables"],
        "sections": [section["name"] for section in sections],
        "section_bars": [section["bars"] for section in sections],
        "melisma_min": targets["melisma_min"],
        "melisma_max": targets["melisma_max"],
        "register": targets["register"],
        "max_top_duration_share": targets["max_top_duration_share"],
        "min_distinct_durations": targets["min_distinct_durations"],
        "ties_min": targets["ties_min"],
        "min_fill_notes": targets["min_fill_notes"],
        "chords_min": targets["chords_min"],
        "max_unbroken_seconds": 10,
        "min_phrase_endings": 3,
        "tessitura_share_ge_c5_max": targets["tessitura_share_ge_c5_max"],
        "chorus_lift_min": targets["chorus_lift_min"],
        # The generated plan is objective; strict_shape is an opt-in brief
        # decision. The composer template keeps it false by default.
        "strict_shape": False,
        "maqam_fit_min": 0.95,
        "voices": "vocal+ins",
        "cadence": manifest.get("cadence") or "any",
        "deviations": manifest.get("deviations") or [
            {
                "bars": f"1-{bars}",
                "channel": "section register",
                "before": "flat prior register across sections",
                "after": "composer to shape section register arc in arrangement",
                "unverifiable": True,
                "reason": "skeleton from corpus priors; fill assert after drafting core",
            },
            {
                "bars": f"1-{bars}",
                "channel": "gap rate",
                "before": "default answer after every sung line",
                "after": "composer to thin or vary answer rate by section",
                "unverifiable": True,
                "reason": "skeleton from corpus priors; fill assert after drafting core",
            },
            {
                "bars": f"1-{bars}",
                "channel": "density",
                "before": "uniform density across the form",
                "after": "composer to declare density contrast by section",
                "unverifiable": True,
                "reason": "skeleton from corpus priors; fill assert after drafting core",
            },
        ],
        "copies": manifest.get("copies") if "copies" in manifest else {
            "status": "unfilled",
            "entries": [],
        },
        "arrangement": manifest.get("arrangement") if "arrangement" in manifest else {
            "status": "unfilled",
            "section_plan": [],
            "ins_entries": [],
        },
        "maqam": None,
        "maqam_conditioned": False,
        "source": {
            "prior": selection["stratum"],
            "n": selection["n"],
            "confidence": selection["confidence"],
            "backoff": selection["backoff"],
        },
        "warnings": warnings,
    }

    if not 3 <= len(plan["deviations"]) <= 4:
        warnings.append(
            f"checker expects 3-4 declared deviations; got {len(plan['deviations'])}"
        )
    if manifest.get("maqam"):
        warnings.append(
            "manifest maqam ignored: no reviewed labels exist in this corpus"
        )

    errors = validate_plan(plan)
    brief = {
        "plan_version": PLAN_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": manifest.get("title"),
        "artist": manifest.get("artist"),
        "request": manifest,
        "assumptions": assumptions,
        "warnings": warnings,
        "prior": {
            "stratum": selection["stratum"],
            "n": selection["n"],
            "confidence": selection["confidence"],
            "backoff": selection["backoff"],
        },
        "sections": sections,
        "targets": {
            key_name: plan[key_name]
            for key_name in REQUIRED_PLAN_KEYS
            if key_name != "sections"
        },
        "maqam": None,
        "maqam_conditioned": False,
        "limitations": [
            "No reviewed maqam labels exist; the plan is objective-only.",
            "Priors describe the corpus distribution, not a correctness bound.",
            "Section names are structural placeholders.",
        ],
        "valid": not errors,
        "errors": errors,
    }

    checks = [
        {
            "name": "plan_shape",
            "required": True,
            "ok": not errors,
            "detail": "complete" if not errors else "; ".join(errors),
        },
        {
            "name": "sections_sum",
            "required": True,
            "ok": sum(section["bars"] for section in sections) == bars,
            "detail": f"{sum(section['bars'] for section in sections)} bars across "
                      f"{len(sections)} sections vs plan bars {bars}",
        },
        {
            "name": "no_maqam_claim",
            "required": True,
            "ok": plan["maqam"] is None and not plan["maqam_conditioned"],
            "detail": "plan carries no maqam label and is not maqam-conditioned",
        },
    ]
    seconds = manifest.get("target_duration_s") or manifest.get("duration_s")
    if seconds:
        planned = bars * _bar_seconds(meter, tempo)
        deviation = abs(planned - float(seconds)) / float(seconds)
        checks.append(
            {
                "name": "duration_target",
                "required": True,
                "ok": deviation <= 0.10,
                "detail": f"planned {planned:.1f}s vs target {float(seconds):.1f}s "
                          f"({deviation:.1%} off)",
            }
        )
    brief["checks"] = checks
    brief["gate_pass"] = all(check["ok"] for check in checks if check["required"])
    brief["files"] = write_plan(out, brief, plan)
    return {"brief": brief, "plan": plan}


def write_plan(out: Path, brief: dict, plan: dict) -> dict:
    brief_path = out / "brief.json"
    plan_path = out / "skill_plan.json"
    md_path = out / "plan.md"
    brief_path.write_text(
        json.dumps(brief, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    plan_path.write_text(
        json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(_markdown(brief, plan), encoding="utf-8")
    return {"brief": str(brief_path), "plan": str(plan_path), "plan_md": str(md_path)}


def plan_from_files(manifest_path: str | Path, priors_path: str | Path,
                    out_dir: str | Path) -> dict:
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise SourceError(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return build_plan(manifest, load_priors(priors_path), out_dir)


def _markdown(brief: dict, plan: dict) -> str:
    lines = [
        "# Score plan",
        "",
        f"- Title: {brief.get('title') or '-'}",
        f"- Gate: **{'PASS' if brief['gate_pass'] else 'FAIL'}**",
        f"- Key {plan['key']} · {plan['meter']} · {plan['tempo']} BPM · {plan['bars']} bars",
        f"- Prior: `{brief['prior']['stratum']}` "
        f"(n={brief['prior']['n']}, {brief['prior']['confidence']})",
        "- Maqam: **not claimed** (objective-only plan)",
        "",
        "## Sections",
        "",
        "| Section | Bars |",
        "|---|---:|",
    ]
    for section in brief["sections"]:
        lines.append(f"| {section['name']} | {section['bars']} |")
    lines += [
        "",
        "## Targets",
        "",
        "| Target | Value |",
        "|---|---|",
        f"| syllables | {plan['syllables']} |",
        f"| melisma | {plan['melisma_min']}-{plan['melisma_max']} |",
        f"| register | mean {plan['register']['mean']} ± {plan['register']['tolerance']}, "
        f"top ≥ {plan['register']['top']}, max top {plan['register'].get('max_top', '-')} |",
        f"| max top-duration share | {plan['max_top_duration_share']} |",
        f"| distinct durations | ≥ {plan['min_distinct_durations']} |",
        f"| ties | ≥ {plan['ties_min']} |",
        f"| chords | ≥ {plan['chords_min']} |",
    ]
    if brief["assumptions"]:
        lines += ["", "## Assumptions", ""]
        lines += [f"- {item}" for item in brief["assumptions"]]
    if brief["warnings"]:
        lines += ["", "## Warnings", ""]
        lines += [f"- {item}" for item in brief["warnings"]]
    lines += ["", "## Limits", ""]
    lines += [f"- {item}" for item in brief["limitations"]]
    lines.append("")
    return "\n".join(lines)
