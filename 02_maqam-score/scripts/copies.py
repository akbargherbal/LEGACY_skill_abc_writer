#!/usr/bin/env python3
"""Item 1: exact structural comparison for declared bar copies and independent repeats."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bar_ranges  # noqa: E402

CHANGE_KINDS = {"octave", "ornament", "cadence", "density", "truncation", "other"}
VALID_VOICES = ("Vocal", "Ins")


def _normalize_voices(raw) -> list[str]:
    if isinstance(raw, str):
        items = [raw.strip()]
    elif isinstance(raw, list):
        items = [str(x).strip() for x in raw]
    else:
        raise ValueError(f"invalid voices specification: {raw!r}")
    if not items or any(v not in VALID_VOICES for v in items):
        raise ValueError(f"voices must be subset of {VALID_VOICES}, got {raw!r}")
    # Preserve order, deduplicate
    out: list[str] = []
    for v in items:
        if v not in out:
            out.append(v)
    return out


def declared_copy_bars(plan: dict, *, max_bars: int | None = None) -> set[int]:
    """Return 1-based target bar numbers covered by declared copy entries.

    Independent entries (``mode == 'independent'``) and unfilled skeletons are
    not copy bars and are not excluded from ``distinct_bar_share``.
    """
    raw = plan.get("copies")
    if not isinstance(raw, list):
        return set()
    bars: set[int] = set()
    for entry in raw:
        if not isinstance(entry, dict) or entry.get("mode") == "independent":
            continue
        if "bars" not in entry:
            continue
        try:
            bars.update(bar_ranges.expand_bar_ranges(entry["bars"], max_bars=max_bars))
        except ValueError:
            continue
    return bars


def _bar_signature(score, bar_1based: int, voice: str) -> list[tuple[int, float, float]]:
    """Return sorted (pitch, dur, offset_within_bar) note tuples for one bar."""
    bar_start = float(score.bar_starts[bar_1based - 1])
    sig = [
        (int(n.pitch), round(float(n.dur), 6), round(float(n.onset) - bar_start, 6))
        for n in score.notes_of(voice)
        if n.bar == bar_1based - 1
    ]
    sig.sort(key=lambda t: (t[2], t[0], t[1]))
    return sig


def check_copies(score, plan: dict) -> dict:
    """Validate plan.copies against the parsed score.

    Returns ``{checks, copies_checked, declared_copy_bars, undeclared_repeats}``.
    """
    checks: list[tuple[str, bool, str, str, str | None]] = []
    waivers: list[dict] = []
    has_plan_version = bool(plan.get("plan_version"))

    if "copies" not in plan:
        if has_plan_version:
            checks.append((
                "copies map",
                False,
                "missing copies declaration (add 'copies': [...] to plan.json)",
                "exact",
                None,
            ))
        else:
            checks.append((
                "copies map",
                False,
                "legacy plan missing copies: add 'copies': [...] and 'plan_version' to plan.json",
                "banded",
                "WARN",
            ))
            waivers.append({
                "check": "copies",
                "flag": "legacy",
                "detail": "legacy plan: copies were not checked; migrate with plan_version + copies",
            })
        return {
            "checks": checks,
            "copies_checked": False,
            "declared_copy_bars": [],
            "undeclared_repeats": [],
            "waivers": waivers,
        }

    raw_copies = plan["copies"]
    if isinstance(raw_copies, dict) and raw_copies.get("status") == "unfilled":
        checks.append((
            "copies map",
            False,
            "copies skeleton is unfilled; complete copies list before final check",
            "banded",
            "WARN",
        ))
        return {
            "checks": checks,
            "copies_checked": False,
            "declared_copy_bars": [],
            "undeclared_repeats": [],
            "waivers": waivers,
        }

    if not isinstance(raw_copies, list):
        checks.append((
            "copies map",
            False,
            f"copies must be a list, got {type(raw_copies).__name__}",
            "exact",
            None,
        ))
        return {
            "checks": checks,
            "copies_checked": False,
            "declared_copy_bars": [],
            "undeclared_repeats": [],
            "waivers": waivers,
        }

    covered_bars: set[int] = set()
    copy_bars_set: set[int] = set()
    errors: list[str] = []
    checked_pairs = 0

    for idx, entry in enumerate(raw_copies, 1):
        if not isinstance(entry, dict):
            errors.append(f"entry {idx}: must be an object")
            continue

        if entry.get("mode") == "independent":
            if "bars" not in entry:
                errors.append(f"entry {idx}: mode='independent' requires 'bars'")
                continue
            try:
                ind_bars = bar_ranges.expand_bar_ranges_ordered(entry["bars"], max_bars=score.n_bars)
            except ValueError as exc:
                errors.append(f"entry {idx}: {exc}")
                continue
            covered_bars.update(ind_bars)
            continue

        missing = [k for k in ("of_bars", "bars", "voices") if k not in entry]
        if missing:
            errors.append(f"entry {idx}: missing {', '.join(missing)}")
            continue

        try:
            src_bars = bar_ranges.expand_bar_ranges_ordered(entry["of_bars"], max_bars=score.n_bars)
            dst_bars = bar_ranges.expand_bar_ranges_ordered(entry["bars"], max_bars=score.n_bars)
            voices = _normalize_voices(entry["voices"])
        except ValueError as exc:
            errors.append(f"entry {idx}: {exc}")
            continue

        if len(src_bars) != len(dst_bars):
            errors.append(
                f"entry {idx}: range length mismatch ({len(src_bars)} in of_bars vs {len(dst_bars)} in bars)"
            )
            continue
        overlap = set(src_bars) & set(dst_bars)
        if overlap:
            errors.append(f"entry {idx}: of_bars and bars overlap on bar(s) {sorted(overlap)}")
            continue

        covered_bars.update(dst_bars)
        copy_bars_set.update(dst_bars)
        dst_set = set(dst_bars)

        # Parse changes: map (dst_bar) -> list of (kind, voice_or_None)
        raw_changes = entry.get("changes", [])
        if not isinstance(raw_changes, list):
            errors.append(f"entry {idx}: changes must be a list")
            continue
        change_specs: dict[int, list[tuple[str, str | None]]] = {}
        entry_bad = False
        for c_idx, ch in enumerate(raw_changes, 1):
            if not isinstance(ch, dict):
                errors.append(f"entry {idx} change {c_idx}: must be an object")
                entry_bad = True
                continue
            kind = ch.get("kind")
            if kind not in CHANGE_KINDS:
                errors.append(
                    f"entry {idx} change {c_idx}: invalid kind {kind!r} (allowed: {sorted(CHANGE_KINDS)})"
                )
                entry_bad = True
                continue
            ch_voice = ch.get("voice")
            if ch_voice is not None and ch_voice not in voices:
                errors.append(f"entry {idx} change {c_idx}: voice {ch_voice!r} not in {voices}")
                entry_bad = True
                continue
            bar_field = ch.get("bars", ch.get("bar"))
            if bar_field is None:
                errors.append(f"entry {idx} change {c_idx}: missing 'bar' or 'bars'")
                entry_bad = True
                continue
            try:
                ch_bars = bar_ranges.expand_bar_ranges(bar_field, max_bars=score.n_bars)
            except ValueError as exc:
                errors.append(f"entry {idx} change {c_idx}: {exc}")
                entry_bad = True
                continue
            outside = [b for b in ch_bars if b not in dst_set]
            if outside:
                errors.append(f"entry {idx} change {c_idx}: bar(s) {outside} not in target bars {entry['bars']!r}")
                entry_bad = True
                continue
            for cb in ch_bars:
                change_specs.setdefault(cb, []).append((kind, ch_voice))
        if entry_bad:
            continue

        # Compare each aligned bar pair
        for s_bar, d_bar in zip(src_bars, dst_bars):
            checked_pairs += 1
            if score.bar_meters[s_bar - 1] != score.bar_meters[d_bar - 1]:
                errors.append(
                    f"entry {idx} bar {d_bar} (of {s_bar}): meter {score.bar_meters[d_bar - 1]} != {score.bar_meters[s_bar - 1]}"
                )
                continue

            specs = change_specs.get(d_bar, [])
            if not specs:
                for v in voices:
                    if _bar_signature(score, s_bar, v) != _bar_signature(score, d_bar, v):
                        errors.append(
                            f"entry {idx} bar {d_bar} (copy of {s_bar}) drifted in {v}"
                        )
            else:
                # Specific voice changes vs any-voice changes
                voice_reqs = {v for _, v in specs if v is not None}
                any_voice_req = any(v is None for _, v in specs)
                differed_voices: set[str] = set()
                for v in voices:
                    differs = _bar_signature(score, s_bar, v) != _bar_signature(score, d_bar, v)
                    if differs:
                        differed_voices.add(v)
                    elif v in voice_reqs:
                        errors.append(
                            f"entry {idx} bar {d_bar} (of {s_bar}): declared change in {v} did not differ"
                        )
                if any_voice_req and not differed_voices:
                    errors.append(
                        f"entry {idx} bar {d_bar} (of {s_bar}): declared change did not differ in {voices}"
                    )

    checks.append((
        "copies map",
        not errors,
        (f"{len(raw_copies)} entry/entries, {checked_pairs} bar pair(s) exact"
         if not errors else "; ".join(errors[:5])),
        "exact",
        None,
    ))

    # Undeclared repeats: a normalized section name that repeats with no covering copies entry
    runs: list[tuple[str, set[int]]] = []
    for b_idx, sec in enumerate(score.bar_sections, 1):
        if runs and runs[-1][0] == sec:
            runs[-1][1].add(b_idx)
        else:
            runs.append((sec, {b_idx}))

    seen_sections: set[str] = set()
    undeclared: list[str] = []
    for sec, sec_bars in runs:
        if sec == "score":
            continue
        if sec in seen_sections:
            if not sec_bars.issubset(covered_bars):
                undeclared.append(f"{sec} (bars {min(sec_bars)}-{max(sec_bars)})")
        else:
            seen_sections.add(sec)

    if undeclared:
        checks.append((
            "undeclared repeats",
            False,
            "repeating section(s) with no covering copies entry: " + ", ".join(undeclared),
            "banded",
            "WARN",
        ))

    return {
        "checks": checks,
        "copies_checked": True,
        "declared_copy_bars": sorted(copy_bars_set),
        "undeclared_repeats": undeclared,
        "waivers": waivers,
    }
