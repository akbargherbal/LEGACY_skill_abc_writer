#!/usr/bin/env python3
"""Item 2: recompute lyrics prosody in checker.py and check against the raw cap."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import syllabify  # noqa: E402


def _cfg_val(cfg: dict, key: str, default):
    entry = cfg.get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return default if entry is None else entry


def check_prosody(
    score,
    plan: dict,
    *,
    lyrics_text: str | None = None,
    lyrics_present: bool = False,
    waive_lyrics: bool = False,
    allow_unmarked: list[str] | set[str] | None = None,
    cap_confirmed_override: bool | None = None,
    calibration: dict | None = None,
) -> dict:
    """Recompute lyrics prosody and evaluate vocalisation, syllables, and raw cap.

    Returns ``{checks, prosody_checked, waivers, recomputed, cap_confirmed}``.
    Each check is ``(name, ok, detail, cls, tag_override)``.
    """
    cal = calibration or {}
    cap_cfg = cal.get("cap_check", {})
    aoc = cal.get("metrics", {}).get("audio_over_cap", {})
    cap_confirmed = (
        bool(cap_confirmed_override)
        if cap_confirmed_override is not None
        else bool(_cfg_val(cap_cfg, "cap_confirmed", False))
    )

    checks: list[tuple[str, bool, str, str, str | None]] = []
    waivers: list[dict] = []
    has_plan_version = bool(plan.get("plan_version"))

    if cap_confirmed_override:
        waivers.append({
            "check": "cap_confirmed",
            "flag": "--cap-confirmed",
            "detail": "cap FAIL threshold promoted to 1.00 of raw cap",
        })

    if not lyrics_present or lyrics_text is None:
        if waive_lyrics:
            waivers.append({
                "check": "prosody",
                "flag": "--waive-lyrics",
                "detail": "lyrics prosody check waived by caller",
            })
            checks.append((
                "lyrics prosody",
                False,
                "waived via --waive-lyrics (prosody not recomputed)",
                "banded",
                "WARN",
            ))
        elif has_plan_version:
            checks.append((
                "lyrics prosody",
                False,
                "missing --lyrics (required when plan_version is declared; pass --lyrics <file> or --waive-lyrics)",
                "exact",
                None,
            ))
        else:
            checks.append((
                "lyrics prosody",
                False,
                "legacy plan missing --lyrics: pass --lyrics <file> (or --waive-lyrics) and add plan_version",
                "banded",
                "WARN",
            ))
            waivers.append({
                "check": "prosody",
                "flag": "legacy",
                "detail": "legacy plan: lyrics prosody was not checked; migrate with plan_version + --lyrics",
            })
        return {
            "checks": checks,
            "prosody_checked": False,
            "waivers": waivers,
            "recomputed": None,
            "cap_confirmed": cap_confirmed,
        }

    allow_set = syllabify.normalize_allow_unmarked(
        list(allow_unmarked or []) + list(plan.get("allow_unmarked") or [])
    )
    plan_tempo = plan.get("tempo")
    tempo = float(plan_tempo) if plan_tempo is not None else float(score.tempo)
    meter = str(plan.get("meter") or f"{score.meter[0]}/{score.meter[1]}")
    unit = str(plan.get("unit") or f"1/{score.unit_den}")

    try:
        info = syllabify.analyze_lyrics(
            lyrics_text,
            tempo=tempo,
            meter=meter,
            unit=unit,
            calibration=cal,
            allow_unmarked=allow_set,
        )
    except ValueError as exc:
        checks.append(("vocalisation coverage", False, f"contract: {exc}", "exact", None))
        return {
            "checks": checks,
            "prosody_checked": True,
            "waivers": waivers,
            "recomputed": None,
            "cap_confirmed": cap_confirmed,
        }

    # 1. Vocalisation coverage
    if info["unmarked"]:
        summary = "; ".join(
            f"line {u['line']}: {', '.join(u['words'])}"
            for u in info["unmarked"][:5]
        )
        if len(info["unmarked"]) > 5:
            summary += f" (+{len(info['unmarked']) - 5} more line(s))"
        checks.append((
            "vocalisation coverage",
            False,
            f"contract: unmarked Arabic word(s) without vowel marks: {summary}",
            "exact",
            None,
        ))
    else:
        allowed_n = len(info["unmarked_words_allowed"])
        extra = f" ({allowed_n} allowed)" if allowed_n else ""
        checks.append((
            "vocalisation coverage",
            True,
            f"all {info['words']} Arabic word(s) carry vowel marks{extra}",
            "exact",
            None,
        ))

    # 2. Tempo / meter agreement and assumed default tempo
    tempo_assumed = (
        plan_tempo is None
        or plan.get("tempo_source") == "calibration_default"
        or bool(plan.get("tempo_assumed"))
    )
    if tempo_assumed:
        checks.append((
            "assumed tempo",
            False,
            f"assumed default tempo {tempo:g} BPM; declare explicit tempo",
            "banded",
            "WARN",
        ))
    if plan_tempo is not None and abs(float(plan_tempo) - score.tempo) >= 1e-9:
        checks.append((
            "lyrics tempo",
            False,
            f"plan tempo {plan_tempo} != score Q:{score.tempo:g}",
            "exact",
            None,
        ))
    if meter != f"{score.meter[0]}/{score.meter[1]}":
        checks.append((
            "lyrics meter",
            False,
            f"plan meter {meter} != score M:{score.meter[0]}/{score.meter[1]}",
            "exact",
            None,
        ))

    # 3. Recomputed syllable total must equal plan.syllables
    plan_syll = plan.get("syllables")
    if plan_syll is not None:
        syll_ok = int(plan_syll) == info["syllables"]
        checks.append((
            "lyrics syllables",
            syll_ok,
            f"plan {plan_syll} vs recomputed {info['syllables']}",
            "exact",
            None,
        ))

    # 4. Raw duration cap check
    raw_cap = float(info["raw_cap_s"])
    score_s = float(score.seconds)
    cap_ratio = score_s / raw_cap if raw_cap > 0 else 0.0
    cap_p95 = float(_cfg_val(cap_cfg, "cap_warn_ratio", aoc.get("p95", 1.0034852782857882)))
    cap_fail = float(_cfg_val(cap_cfg, "cap_fail_ratio", 1.15))
    cap_min = float(_cfg_val(cap_cfg, "cap_min_ratio", aoc.get("min", 0.7080330333089541)))
    budget_tol = float(_cfg_val(cap_cfg, "bars_budget_tolerance", 0.05))

    if cap_confirmed:
        if cap_ratio > 1.00:
            checks.append((
                "duration cap",
                False,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} > 1.000 (cap confirmed)",
                "exact",
                None,
            ))
        elif cap_ratio < cap_min:
            checks.append((
                "duration cap",
                False,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} < {cap_min:.3f} (padding risk)",
                "banded",
                None,
            ))
        else:
            checks.append((
                "duration cap",
                True,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} (confirmed ceiling 1.000)",
                "exact",
                None,
            ))
    else:
        if cap_ratio > cap_fail:
            checks.append((
                "duration cap",
                False,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} > {cap_fail:.2f} (above unvalidated cap margin)",
                "exact",
                None,
            ))
        elif cap_ratio > cap_p95:
            checks.append((
                "duration cap",
                False,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} > corpus P95 {cap_p95:.3f} (FAIL at {cap_fail:.2f})",
                "banded",
                None,
            ))
        elif cap_ratio < cap_min:
            checks.append((
                "duration cap",
                False,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} < corpus min {cap_min:.3f} (padding risk)",
                "banded",
                None,
            ))
        else:
            checks.append((
                "duration cap",
                True,
                f"{score_s:.1f}s / raw cap {raw_cap:.1f}s = {cap_ratio:.3f} (P95 {cap_p95:.3f}, fail {cap_fail:.2f})",
                "banded",
                None,
            ))

    # 5. plan.bars within +/-5% of syllabify budget
    budget_bars = int(info["bars"])
    plan_bars = plan.get("bars")
    if plan_bars is not None and budget_bars > 0:
        delta = abs(int(plan_bars) - budget_bars) / budget_bars
        budget_ok = delta <= budget_tol + 1e-9
        checks.append((
            "bars budget",
            budget_ok,
            f"plan {plan_bars} vs syllabify budget {budget_bars} ({(int(plan_bars) - budget_bars) / budget_bars:+.1%}, tol +/-{budget_tol:.0%})",
            "banded",
            None,
        ))

    info["cap_ratio"] = round(cap_ratio, 4)
    return {
        "checks": checks,
        "prosody_checked": True,
        "waivers": waivers,
        "recomputed": info,
        "cap_confirmed": cap_confirmed,
    }
