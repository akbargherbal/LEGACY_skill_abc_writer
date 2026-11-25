#!/usr/bin/env python3
"""Item 3: binding arrangement plan, Ins entry positions, and deviation assertions."""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bar_ranges  # noqa: E402

ALLOWED_METRICS = {
    "answer_rate",
    "ins_notes_per_bar",
    "vocal_notes_per_bar",
    "vocal_median_pitch",
    "ins_active_share",
    "silence_share",
}

CHANNEL_METRICS: dict[str, set[str]] = {
    "gap rate": {"answer_rate", "silence_share", "ins_active_share", "ins_notes_per_bar"},
    "silence / gap placement": {"answer_rate", "silence_share", "ins_active_share", "ins_notes_per_bar"},
    "silence": {"silence_share", "answer_rate"},
    "answer rate": {"answer_rate", "ins_active_share", "ins_notes_per_bar"},
    "density": {"vocal_notes_per_bar", "ins_notes_per_bar", "ins_active_share", "silence_share", "answer_rate"},
    "instrumentation": {"ins_notes_per_bar", "ins_active_share", "answer_rate"},
    "section register": {"vocal_median_pitch"},
    "register": {"vocal_median_pitch"},
    "repetition rate": set(),
    "repetition": set(),
    "phrase shape mutation": set(),
    "mutation": set(),
}

BOILERPLATE_DEVIATIONS = {
    "plan generated from objective corpus priors",
    "no maqam label is claimed or implied",
    "section names are structural, not maqam functions",
}

VALID_OPS = {"<", "<=", ">", ">=", "==", "=", "!=", "between", "in"}


def _cfg_val(cfg: dict, key: str, default):
    entry = cfg.get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return default if entry is None else entry


def _parse_band(raw, name: str) -> tuple[float, float]:
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        lo, hi = float(raw[0]), float(raw[1])
    elif isinstance(raw, dict) and "min" in raw and "max" in raw:
        lo, hi = float(raw["min"]), float(raw["max"])
    else:
        raise ValueError(f"{name}: band must be [min, max], got {raw!r}")
    if lo > hi:
        raise ValueError(f"{name}: band min {lo} > max {hi}")
    return lo, hi


def _phrase_split_local(vocal: list, score) -> list[list]:
    out: list[list] = []
    cur: list = []
    prev_end = None
    for note in vocal:
        threshold = score.bar_units[max(0, min(score.n_bars - 1, note.bar))] / 4
        if cur and (note.section != cur[-1].section or note.onset - prev_end >= threshold):
            out.append(cur)
            cur = []
        cur.append(note)
        prev_end = note.onset + note.dur
    if cur:
        out.append(cur)
    return [p for p in out if len(p) >= 2]


def _range_answer_rate(score, vocal: list, ins: list, bars_set: set[int]) -> tuple[int, int]:
    """Return (answered_count, eligible_count) for phrases ending in bars_set."""
    phrases = _phrase_split_local(vocal, score)
    max_bar = max(bars_set)
    range_end = float(score.bar_starts[max_bar])
    answered = 0
    eligible = 0
    for i, phrase in enumerate(phrases):
        if (phrase[-1].bar + 1) not in bars_set:
            continue
        start = phrase[-1].onset + phrase[-1].dur
        if i + 1 < len(phrases):
            nxt = phrases[i + 1][0].onset
            if (phrases[i + 1][0].bar + 1) not in bars_set:
                nxt = min(nxt, range_end)
        else:
            nxt = range_end
        threshold = score.bar_units[max(0, min(score.n_bars - 1, phrase[-1].bar))] / 4
        if nxt - start < threshold:
            continue
        eligible += 1
        if any(start <= n.onset < nxt for n in ins):
            answered += 1
    return answered, eligible


def _measure_range(score, vocal: list, ins: list, bars_list: list[int]) -> dict:
    bars_set = set(bars_list)
    n_bars = len(bars_list)
    v_notes = [n for n in vocal if (n.bar + 1) in bars_set]
    i_notes = [n for n in ins if (n.bar + 1) in bars_set]
    total_units = sum(score.bar_units[b - 1] for b in bars_list)
    answered, eligible = _range_answer_rate(score, vocal, ins, bars_set)
    return {
        "vocal_notes_per_bar": len(v_notes) / n_bars,
        "ins_notes_per_bar": len(i_notes) / n_bars,
        "ins_active_share": len({n.bar + 1 for n in i_notes}) / n_bars,
        "vocal_median_pitch": statistics.median(n.pitch for n in v_notes) if v_notes else None,
        "silence_share": (1.0 - sum(n.dur for n in v_notes) / total_units) if total_units > 0 else 0.0,
        "answer_eligible": eligible,
        "answer_answered": answered,
        "answer_rate": (answered / eligible) if eligible > 0 else None,
    }


def _eval_op(measured: float, op: str, value) -> bool:
    eps = 1e-9
    if op in ("between", "in"):
        lo, hi = float(value[0]), float(value[1])
        return lo - eps <= measured <= hi + eps
    v = float(value)
    if op == "<":
        return measured < v - eps
    if op == "<=":
        return measured <= v + eps
    if op == ">":
        return measured > v + eps
    if op == ">=":
        return measured >= v - eps
    if op in ("==", "="):
        return abs(measured - v) <= eps
    if op == "!=":
        return abs(measured - v) > eps
    raise ValueError(f"unsupported op {op!r}")


def _detect_ins_entries(score, ins: list, min_silent: int = 2) -> list[int]:
    """Return 1-based bars where Ins starts after at least ``min_silent`` silent bars."""
    active = [any(n.bar == b for n in ins) for b in range(score.n_bars)]
    entries: list[int] = []
    for b_idx in range(min_silent, score.n_bars):
        if active[b_idx] and all(not active[b_idx - k] for k in range(1, min_silent + 1)):
            entries.append(b_idx + 1)
    return entries


def check_deviations(score, plan: dict, *, calibration: dict | None = None) -> dict:
    """Evaluate plan.deviations (assert, unverifiable, migration rule)."""
    cal = calibration or {}
    cfg = cal.get("binding_check", {})
    min_eligible = int(_cfg_val(cfg, "min_eligible_phrases_for_answer_rate", 4))
    has_plan_version = bool(plan.get("plan_version"))

    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    ins = sorted(score.notes_of("Ins"), key=lambda n: n.onset)
    devs = plan.get("deviations")
    if devs is None:
        return {"checks": [], "rows": [], "unverifiable": []}
    if not isinstance(devs, list):
        return {
            "checks": [("deviations syntax", False, "deviations must be a list", "exact", None)],
            "rows": [],
            "unverifiable": [],
        }

    checks: list[tuple[str, bool, str, str, str | None]] = []
    rows: list[dict] = []
    unverifiable: list[dict] = []

    for idx, dev in enumerate(devs, 1):
        label = f"deviation {idx}"
        if isinstance(dev, str):
            norm = dev.strip().lower()
            if not norm or norm in BOILERPLATE_DEVIATIONS:
                checks.append((
                    label,
                    False,
                    f"boilerplate string deviation is not allowed: {dev!r}",
                    "exact",
                    None,
                ))
            elif has_plan_version:
                checks.append((
                    label,
                    False,
                    f"string deviation not allowed with plan_version: {dev!r} (use object with assert or unverifiable)",
                    "exact",
                    None,
                ))
            else:
                checks.append((
                    label,
                    False,
                    "legacy string deviation: replace with {bars, channel, before, after, assert|unverifiable} and add plan_version",
                    "banded",
                    "WARN",
                ))
            continue

        if not isinstance(dev, dict):
            checks.append((label, False, "deviation entry must be an object", "exact", None))
            continue

        has_assert = dev.get("assert") is not None
        has_unv = dev.get("unverifiable") is True

        if has_assert and has_unv:
            checks.append((label, False, "cannot set both 'assert' and 'unverifiable: true'", "exact", None))
            continue

        if not has_assert and not has_unv:
            if has_plan_version:
                checks.append((
                    label,
                    False,
                    "deviation must carry 'assert' or 'unverifiable: true' with 'reason'",
                    "exact",
                    None,
                ))
            else:
                checks.append((
                    label,
                    False,
                    "legacy deviation missing assert/unverifiable: add 'assert' or 'unverifiable: true' + 'reason' and plan_version",
                    "banded",
                    "WARN",
                ))
            continue

        if has_unv:
            reason = dev.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                checks.append((label, False, "unverifiable: true requires a non-empty 'reason'", "exact", None))
                continue
            detail = f"declared, not verifiable: {reason.strip()}"
            checks.append((label, False, detail, "unverifiable", "INFO"))
            unverifiable.append({"index": idx, "channel": dev.get("channel"), "reason": reason.strip()})
            rows.append({
                "scope": f"deviation {idx}",
                "metric": dev.get("channel") or "unverifiable",
                "range": dev.get("bars", "-"),
                "planned": "unverifiable",
                "measured": reason.strip(),
                "verdict": "INFO",
                "class": "unverifiable",
            })
            continue

        # Assert resolution (exact FAIL)
        assertion = dev["assert"]
        if not isinstance(assertion, dict):
            checks.append((f"{label} assert", False, "assert must be an object", "exact", None))
            continue

        channel = str(dev.get("channel") or "").strip().lower()
        metric = assertion.get("metric")
        rng = assertion.get("range")
        op = assertion.get("op")
        val = assertion.get("value")

        if metric not in ALLOWED_METRICS:
            checks.append((
                f"{label} assert",
                False,
                f"unknown assert metric {metric!r} (allowed: {sorted(ALLOWED_METRICS)})",
                "exact",
                None,
            ))
            continue
        if channel not in CHANNEL_METRICS:
            checks.append((
                f"{label} assert",
                False,
                f"unknown channel {dev.get('channel')!r} for assert",
                "exact",
                None,
            ))
            continue
        if metric not in CHANNEL_METRICS[channel]:
            checks.append((
                f"{label} assert",
                False,
                f"metric {metric!r} not allowed for channel {dev.get('channel')!r} "
                f"(allowed: {sorted(CHANNEL_METRICS[channel])})",
                "exact",
                None,
            ))
            continue
        if rng is None or op not in VALID_OPS or val is None:
            checks.append((
                f"{label} assert",
                False,
                "assert requires metric, range, op, and value",
                "exact",
                None,
            ))
            continue
        try:
            bars_list = bar_ranges.expand_bar_ranges(rng, max_bars=score.n_bars)
            if op in ("between", "in"):
                if not isinstance(val, (list, tuple)) or len(val) != 2:
                    raise ValueError("between/in requires [min, max]")
                float(val[0])
                float(val[1])
            else:
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(f"value must be numeric, got {val!r}")
        except ValueError as exc:
            checks.append((f"{label} assert", False, str(exc), "exact", None))
            continue

        m = _measure_range(score, vocal, ins, bars_list)
        if metric == "answer_rate" and m["answer_eligible"] < min_eligible:
            detail = (
                f"insufficient sample ({m['answer_eligible']} eligible phrase(s) < {min_eligible}) "
                f"in bars {rng}"
            )
            checks.append((f"{label} ({metric})", False, detail, "unverifiable", "INFO"))
            rows.append({
                "scope": f"deviation {idx}",
                "metric": metric,
                "range": str(rng),
                "planned": f"{op} {val}",
                "measured": f"insufficient sample ({m['answer_eligible']}/{min_eligible})",
                "verdict": "insufficient sample",
                "class": "banded",
            })
            continue

        measured_val = m[metric]
        if measured_val is None:
            checks.append((
                f"{label} ({metric})",
                False,
                f"no vocal notes in bars {rng} to measure {metric}",
                "banded",
                None,
            ))
            rows.append({
                "scope": f"deviation {idx}",
                "metric": metric,
                "range": str(rng),
                "planned": f"{op} {val}",
                "measured": "none",
                "verdict": "MISS",
                "class": "banded",
            })
            continue

        ok = _eval_op(float(measured_val), op, val)
        checks.append((
            f"{label} ({metric})",
            ok,
            f"bars {rng}: {measured_val:.3g} {op} {val}",
            "banded",
            None,
        ))
        rows.append({
            "scope": f"deviation {idx}",
            "metric": metric,
            "range": str(rng),
            "planned": f"{op} {val}",
            "measured": round(float(measured_val), 3),
            "verdict": "PASS" if ok else "MISS",
            "class": "banded",
        })

    return {"checks": checks, "rows": rows, "unverifiable": unverifiable}


def check_binding(score, plan: dict, *, calibration: dict | None = None) -> dict:
    """Validate arrangement.section_plan, arrangement.ins_entries, and deviations."""
    cal = calibration or {}
    cfg = cal.get("binding_check", {})
    min_eligible = int(_cfg_val(cfg, "min_eligible_phrases_for_answer_rate", 4))
    min_silent = int(_cfg_val(cfg, "ins_entry_silent_bars_min", 2))
    default_tol = int(_cfg_val(cfg, "ins_entry_default_tolerance_bars", 0))

    has_plan_version = bool(plan.get("plan_version"))
    checks: list[tuple[str, bool, str, str, str | None]] = []
    table_rows: list[dict] = []
    waivers: list[dict] = []

    dev_res = check_deviations(score, plan, calibration=cal)
    checks.extend(dev_res["checks"])
    table_rows.extend(dev_res["rows"])

    if "arrangement" not in plan:
        if has_plan_version:
            checks.append((
                "arrangement",
                False,
                "missing arrangement declaration (add 'arrangement': {'section_plan': [...], 'ins_entries': [...]})",
                "exact",
                None,
            ))
        else:
            checks.append((
                "arrangement",
                False,
                "legacy plan missing arrangement: add 'arrangement': {'section_plan': [...], 'ins_entries': [...]} and 'plan_version' to plan.json",
                "banded",
                "WARN",
            ))
            waivers.append({
                "check": "binding",
                "flag": "legacy",
                "detail": "legacy plan: binding plan was not checked; migrate with plan_version + arrangement",
            })
        return {
            "checks": checks,
            "binding_checked": False,
            "table": table_rows,
            "ins_entries": None,
            "unverifiable": dev_res["unverifiable"],
            "waivers": waivers,
        }

    arr = plan["arrangement"]
    if not isinstance(arr, dict):
        checks.append(("arrangement", False, "arrangement must be an object", "exact", None))
        return {
            "checks": checks,
            "binding_checked": False,
            "table": table_rows,
            "ins_entries": None,
            "unverifiable": dev_res["unverifiable"],
            "waivers": waivers,
        }

    if arr.get("status") == "unfilled":
        checks.append((
            "arrangement",
            False,
            "arrangement skeleton is unfilled; complete section_plan and ins_entries before final check",
            "banded",
            "WARN",
        ))
        return {
            "checks": checks,
            "binding_checked": False,
            "table": table_rows,
            "ins_entries": None,
            "unverifiable": dev_res["unverifiable"],
            "waivers": waivers,
        }

    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    ins = sorted(score.notes_of("Ins"), key=lambda n: n.onset)
    target_bars = int(plan.get("bars", score.n_bars))

    # 1. section_plan tiling and band checks
    sec_plan = arr.get("section_plan")
    tiling_errors: list[str] = []
    covered: list[int] = []
    parsed_ranges: list[tuple[dict, list[int]]] = []

    if not isinstance(sec_plan, list) or not sec_plan:
        tiling_errors.append("section_plan must be a non-empty list")
    else:
        seen_bars: set[int] = set()
        for idx, item in enumerate(sec_plan, 1):
            if not isinstance(item, dict):
                tiling_errors.append(f"range {idx}: must be an object")
                continue
            if "bars" not in item:
                tiling_errors.append(f"range {idx}: missing 'bars'")
                continue
            try:
                b_list = bar_ranges.expand_bar_ranges_ordered(item["bars"], max_bars=score.n_bars)
            except ValueError as exc:
                tiling_errors.append(f"range {idx}: {exc}")
                continue
            overlap = seen_bars & set(b_list)
            if overlap:
                tiling_errors.append(f"range {idx}: overlaps bars {sorted(overlap)}")
                continue
            seen_bars.update(b_list)
            covered.extend(b_list)
            parsed_ranges.append((item, b_list))

        if not tiling_errors:
            expected_set = set(range(1, target_bars + 1))
            if seen_bars != expected_set:
                missing = sorted(expected_set - seen_bars)
                extra = sorted(seen_bars - expected_set)
                parts = []
                if missing:
                    parts.append(f"missing bars {missing[:10]}")
                if extra:
                    parts.append(f"extra bars {extra[:10]}")
                tiling_errors.append(
                    f"section_plan covers {len(seen_bars)} bar(s) != plan {target_bars}: " + ", ".join(parts)
                )

    checks.append((
        "section plan tiling",
        not tiling_errors,
        f"tiles 1-{target_bars} ({len(parsed_ranges)} range(s))" if not tiling_errors else "; ".join(tiling_errors[:4]),
        "exact",
        None,
    ))

    # Band declarations and measurements per range
    band_decl_errors: list[str] = []
    band_misses: list[str] = []
    for idx, (item, b_list) in enumerate(parsed_ranges, 1):
        rng_label = str(item.get("bars"))
        m = _measure_range(score, vocal, ins, b_list)

        parsed_bands: dict[str, tuple[float, float]] = {}
        for key in ("vocal_notes_per_bar", "ins_notes_per_bar", "ins_active_share"):
            if key not in item:
                band_decl_errors.append(f"range {rng_label}: missing {key}")
                continue
            try:
                parsed_bands[key] = _parse_band(item[key], f"{rng_label}.{key}")
            except ValueError as exc:
                band_decl_errors.append(str(exc))

        v_band = parsed_bands.get("vocal_notes_per_bar")
        is_sung = (m["vocal_notes_per_bar"] > 0) or (v_band is not None and v_band[1] > 0)
        if is_sung and "answer_rate" not in item:
            band_decl_errors.append(f"range {rng_label}: sung range must declare answer_rate band")
        elif "answer_rate" in item and item["answer_rate"] is not None:
            try:
                parsed_bands["answer_rate"] = _parse_band(item["answer_rate"], f"{rng_label}.answer_rate")
            except ValueError as exc:
                band_decl_errors.append(str(exc))

        for key in ("vocal_notes_per_bar", "ins_notes_per_bar", "ins_active_share"):
            if key not in parsed_bands:
                continue
            lo, hi = parsed_bands[key]
            actual = m[key]
            ok = lo - 1e-9 <= actual <= hi + 1e-9
            if not ok:
                band_misses.append(f"{rng_label} {key}: {actual:.2f} not in [{lo:g}, {hi:g}]")
            table_rows.append({
                "scope": rng_label,
                "metric": key,
                "range": rng_label,
                "planned": f"[{lo:g}, {hi:g}]",
                "measured": round(actual, 3),
                "verdict": "PASS" if ok else "MISS",
                "class": "banded",
            })

        if "answer_rate" in parsed_bands:
            lo, hi = parsed_bands["answer_rate"]
            if m["answer_eligible"] < min_eligible:
                table_rows.append({
                    "scope": rng_label,
                    "metric": "answer_rate",
                    "range": rng_label,
                    "planned": f"[{lo:g}, {hi:g}]",
                    "measured": f"insufficient sample ({m['answer_eligible']}/{min_eligible})",
                    "verdict": "insufficient sample",
                    "class": "banded",
                })
            else:
                actual = float(m["answer_rate"])
                ok = lo - 1e-9 <= actual <= hi + 1e-9
                if not ok:
                    band_misses.append(
                        f"{rng_label} answer_rate: {actual:.2f} ({m['answer_answered']}/{m['answer_eligible']}) not in [{lo:g}, {hi:g}]"
                    )
                table_rows.append({
                    "scope": rng_label,
                    "metric": "answer_rate",
                    "range": rng_label,
                    "planned": f"[{lo:g}, {hi:g}]",
                    "measured": round(actual, 3),
                    "verdict": "PASS" if ok else "MISS",
                    "class": "banded",
                })

    if band_decl_errors:
        checks.append((
            "section plan bands",
            False,
            "; ".join(band_decl_errors[:4]),
            "exact",
            None,
        ))
    elif not tiling_errors:
        checks.append((
            "section plan metrics",
            not band_misses,
            "all ranges within declared bands" if not band_misses else "; ".join(band_misses[:4]),
            "banded",
            None,
        ))

    # 2. ins_entries deterministic bar position check
    actual_entries = _detect_ins_entries(score, ins, min_silent=min_silent)
    raw_entries = arr.get("ins_entries")
    entry_errors: list[str] = []
    decl_pairs: list[tuple[int, int]] = []
    if raw_entries is None:
        entry_errors.append("missing ins_entries in arrangement")
    elif not isinstance(raw_entries, list):
        entry_errors.append("ins_entries must be a list")
    else:
        for e_idx, item in enumerate(raw_entries, 1):
            if isinstance(item, int) and not isinstance(item, bool):
                b, tol = item, default_tol
            elif isinstance(item, dict) and "bar" in item:
                b = int(item["bar"])
                tol = int(item.get("tolerance_bars", default_tol))
            else:
                entry_errors.append(f"entry {e_idx}: must be bar int or {{bar, tolerance_bars}}")
                continue
            if not (1 <= b <= score.n_bars) or tol < 0:
                entry_errors.append(f"entry {e_idx}: invalid bar {b} or tolerance {tol}")
                continue
            decl_pairs.append((b, tol))

    if not entry_errors:
        decl_sorted = sorted(decl_pairs, key=lambda x: x[0])
        if len(actual_entries) != len(decl_sorted):
            entry_errors.append(
                f"detected Ins entries {actual_entries} != declared {[b for b, _ in decl_sorted]}"
            )
        else:
            for act, (decl_b, tol) in zip(actual_entries, decl_sorted):
                if abs(act - decl_b) > tol:
                    entry_errors.append(
                        f"Ins entry bar {act} outside declared {decl_b} +/- {tol}"
                    )

    checks.append((
        "ins entries",
        not entry_errors,
        (f"entries {actual_entries} match" if not entry_errors else "; ".join(entry_errors[:4])),
        "exact",
        None,
    ))
    table_rows.append({
        "scope": "ins_entries",
        "metric": "entry_bars",
        "range": f"1-{score.n_bars}",
        "planned": [b if tol == 0 else f"{b}+/-{tol}" for b, tol in decl_pairs] if decl_pairs else [],
        "measured": actual_entries,
        "verdict": "PASS" if not entry_errors else "FAIL",
        "class": "exact",
    })

    return {
        "checks": checks,
        "binding_checked": True,
        "table": table_rows,
        "ins_entries": {"declared": decl_pairs, "measured": actual_entries},
        "unverifiable": dev_res["unverifiable"],
        "waivers": waivers,
    }
