#!/usr/bin/env python3
"""Item 4: line-level alignment between lyrics, phrases sidecar, and Vocal notes."""
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bar_ranges  # noqa: E402
import phrase_table  # noqa: E402
import syllabify  # noqa: E402

_TIE_TOKEN = re.compile(
    r'"(?P<chord>[^"\n]*)"|\[K:[^\]\n]+\]|'
    r"(?P<acc>\^\^|__|\^|_|=)?(?P<note>[A-Ga-gz])"
    r"(?P<oct>[,']*)(?P<dur>[0-9]*)(?P<tie>-?)"
)
_SHADDA = "\u0651"
_SUKUN = "\u0652"
_MARKS = set(syllabify.VOWEL_MARKS) | {_SHADDA, _SUKUN}


def _cfg_val(cfg: dict, key: str, default):
    entry = cfg.get(key)
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return default if entry is None else entry


def heavy_syllable_proxy(line: str) -> int:
    """Count heavy-syllable indicators: long vowels, shadda, closed syllables (sukun)."""
    total = 0
    for word in syllabify.extract_arabic_words(line):
        chars = list(word)
        n = len(chars)
        for idx, ch in enumerate(chars):
            if ch in (_SHADDA, _SUKUN, "\u0622"):
                total += 1
                continue
            nxt = chars[idx + 1] if idx + 1 < n else None
            if ch in ("\u0627", "\u0649") and idx > 0 and nxt not in _MARKS:
                total += 1
            elif ch in ("\u0648", "\u064a") and idx > 0 and nxt not in _MARKS:
                total += 1
    return total


def _vocal_tie_groups(score_text: str, score) -> list[dict]:
    """Return Vocal tie groups with exact onset (in score L-units) and 1-based bar."""
    if not score_text:
        return []
    voice = None
    bar_idx = 0
    offset = 0.0
    in_run = False
    run_start_onset = 0.0
    run_start_bar = 1
    groups: list[dict] = []

    for line in score_text.splitlines():
        s = line.strip()
        if s.startswith("V:"):
            voice = s[2:].strip().split()[0]
            continue
        if not s or s[0] in "XTLQVKM%":
            continue
        if voice != "Vocal" or not s.endswith("|"):
            continue
        for body in s[:-1].split("|"):
            body_s = body.strip()
            m_z = re.fullmatch(r"Z([2-4])?", body_s)
            if m_z:
                count = int(m_z.group(1) or 1)
                in_run = False
                bar_idx += count
                offset = 0.0
                continue
            bar_start_u = score.bar_starts[bar_idx] if bar_idx < len(score.bar_starts) else offset
            cur_u = float(bar_start_u)
            for mt in _TIE_TOKEN.finditer(body_s):
                if mt.group("chord") is not None or mt.group("note") is None:
                    continue
                units = float(mt.group("dur") or 1)
                if mt.group("note") == "z":
                    in_run = False
                    cur_u += units
                    continue
                tied = bool(mt.group("tie"))
                if tied and not in_run:
                    run_start_onset = cur_u
                    run_start_bar = bar_idx + 1
                if not tied and in_run:
                    groups.append({
                        "onset": run_start_onset,
                        "bar": run_start_bar,
                    })
                in_run = tied
                cur_u += units
            bar_idx += 1
            offset = cur_u
    if in_run:
        groups.append({"onset": run_start_onset, "bar": run_start_bar})
    return groups


def _one_beat_units(score, bar_1based: int) -> float:
    if bar_1based <= 1:
        return 0.0
    prev_idx = min(max(0, bar_1based - 2), len(score.bar_meters) - 1)
    meter_den = score.bar_meters[prev_idx][1]
    return float(score.unit_den) / float(meter_den)


def check_alignment(
    score,
    plan: dict,
    phrase_plan: dict,
    *,
    score_text: str = "",
    recomputed_prosody: dict | None = None,
    calibration: dict | None = None,
) -> dict:
    """Check line-level alignment, note deficits/excess, pace, orphans, ties, weight."""
    cal = calibration or {}
    cfg = cal.get("alignment_check", {})
    max_deficit_warn = int(_cfg_val(cfg, "max_note_deficit_warn", 1))
    max_excess = int(plan.get("max_excess_notes_per_line", _cfg_val(cfg, "max_excess_notes_per_line", 8)))
    pace_p5 = float(_cfg_val(cfg, "pace_p5", 2.2369668246445498))
    pace_p95 = float(_cfg_val(cfg, "pace_p95", 4.885714285714286))
    max_span_delta = int(_cfg_val(cfg, "max_bar_span_delta", 1))
    pickup_beats = float(_cfg_val(cfg, "pickup_beats", 1))
    iqr_factor = float(_cfg_val(cfg, "heavy_outlier_iqr_factor", 1.5))

    checks: list[tuple[str, bool, str, str, str | None]] = []
    line_defs = phrase_table._defs_from_phrases(phrase_plan)
    raw_lines = phrase_plan.get("lines") if isinstance(phrase_plan, dict) else None

    if not isinstance(raw_lines, list) or not raw_lines or len(line_defs) != len(raw_lines):
        checks.append((
            "alignment sidecar",
            False,
            "phrases sidecar has missing or malformed line entries",
            "exact",
            None,
        ))
        return {
            "checks": checks,
            "alignment_checked": False,
            "lines": [],
            "orphans": [],
            "mid_line_ties": [],
            "line_end_ties": [],
            "ambiguities": [],
        }

    # Parse vocalise_bars (optional wordless bars in sidecar or plan)
    vocalise_spec = phrase_plan.get("vocalise_bars", plan.get("vocalise_bars"))
    vocalise_set: set[int] = set()
    if vocalise_spec is not None and vocalise_spec != [] and vocalise_spec != "":
        try:
            vocalise_set = set(bar_ranges.expand_bar_ranges(vocalise_spec, max_bars=score.n_bars))
        except ValueError as exc:
            checks.append(("vocalise_bars", False, str(exc), "exact", None))

    # Recomputed lyrics syllables check
    recomp_sylls: list[int] | None = None
    recomp_texts: list[str] | None = None
    if recomputed_prosody is not None:
        recomp_sylls = recomputed_prosody.get("syllables_per_line")
        recomp_texts = recomputed_prosody.get("lines_text")
        if recomp_sylls is not None:
            if len(line_defs) != len(recomp_sylls):
                checks.append((
                    "sidecar syllables",
                    False,
                    f"phrases sidecar has {len(line_defs)} line(s), lyrics have {len(recomp_sylls)}",
                    "exact",
                    None,
                ))
            else:
                mismatches = []
                for idx, (ld, exp_s) in enumerate(zip(line_defs, recomp_sylls), 1):
                    side_s = ld.get("syllables")
                    if side_s is not None and int(side_s) != int(exp_s):
                        mismatches.append(f"line {idx}: sidecar {side_s} != lyrics {exp_s}")
                checks.append((
                    "sidecar syllables",
                    not mismatches,
                    "matches lyrics" if not mismatches else "; ".join(mismatches[:5]),
                    "exact",
                    None,
                ))

    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    tie_groups = _vocal_tie_groups(score_text, score)

    # Assign notes to pickup-aware windows
    covered_indices: set[int] = set()
    prev_end_onset = 0.0
    line_reports: list[dict] = []
    deficit_fails: list[str] = []
    deficit_warns: list[str] = []
    excess_warns: list[str] = []
    pace_warns: list[str] = []
    span_warns: list[str] = []
    mid_line_ties: list[dict] = []
    line_end_ties: list[dict] = []
    ambiguities: list[str] = []

    for i, ld in enumerate(line_defs):
        start_b = ld["bar_start"]
        end_b = ld["bar_end"]
        if start_b < 1 or end_b < start_b or end_b > score.n_bars:
            continue
        bar_start_u = float(score.bar_starts[start_b - 1])
        bar_end_u = float(score.bar_starts[end_b])
        one_beat = _one_beat_units(score, start_b) * pickup_beats
        win_start = max(0.0, bar_start_u - one_beat, prev_end_onset)

        # Look ahead to avoid swallowing an adjacent next line's pickup
        win_end = bar_end_u
        if i + 1 < len(line_defs) and line_defs[i + 1]["bar_start"] == end_b + 1:
            next_start_u = float(score.bar_starts[end_b])
            next_beat = _one_beat_units(score, end_b + 1) * pickup_beats
            pickup_cut = next_start_u - next_beat
            tail_idxs = [
                idx for idx, n in enumerate(vocal)
                if idx not in covered_indices and pickup_cut <= n.onset < bar_end_u
            ]
            if tail_idxs:
                first_tail = vocal[tail_idxs[0]]
                earlier = [
                    n for idx, n in enumerate(vocal)
                    if idx not in covered_indices and win_start <= n.onset < pickup_cut
                ]
                later_next = [n for n in vocal if n.bar == end_b]
                gap_before = (
                    first_tail.onset - (earlier[-1].onset + earlier[-1].dur)
                    if earlier else next_beat
                )
                gap_after = (
                    later_next[0].onset - (vocal[tail_idxs[-1]].onset + vocal[tail_idxs[-1]].dur)
                    if later_next else next_beat
                )
                if gap_before >= next_beat - 1e-6 and gap_after < next_beat - 1e-6:
                    win_end = pickup_cut

        note_idxs = [
            idx for idx, n in enumerate(vocal)
            if idx not in covered_indices and win_start - 1e-6 <= n.onset < win_end - 1e-6
        ]
        covered_indices.update(note_idxs)
        line_notes = [vocal[idx] for idx in note_idxs]
        if line_notes:
            prev_end_onset = line_notes[-1].onset + line_notes[-1].dur

        raw_item = raw_lines[i]
        allocated_bars = int(raw_item.get("bars") or (end_b - start_b + 1))
        syll_count = None
        if recomp_sylls is not None and i < len(recomp_sylls):
            syll_count = int(recomp_sylls[i])
        elif ld.get("syllables") is not None:
            syll_count = int(ld["syllables"])

        # Span bars (excluding a pickup beat in bar_start - 1)
        main_bars = [
            n.bar for n in line_notes
            if not (n.bar == start_b - 2 and n.onset < bar_start_u - 1e-6)
        ]
        if main_bars:
            span_min_b, span_max_b = min(main_bars), max(main_bars)
            actual_span_bars = span_max_b - span_min_b + 1
        else:
            span_min_b, span_max_b = start_b - 1, end_b - 1
            actual_span_bars = end_b - start_b + 1

        sidecar_span = end_b - start_b + 1
        reported_span = max(actual_span_bars, sidecar_span)
        span_sixteenths = sum(
            score.bar_units[b] * 16.0 / score.unit_den
            for b in range(span_min_b, span_max_b + 1)
        )
        pace = (span_sixteenths / syll_count) if syll_count else None

        # Ties for this line
        note_onsets = {round(n.onset, 4): idx for idx, n in enumerate(line_notes)}
        line_ties = []
        for tg in tie_groups:
            pos = note_onsets.get(round(tg["onset"], 4))
            if pos is not None:
                kind = "line_end" if pos == len(line_notes) - 1 else "mid_line"
                rec = {"line": ld["line"], "bar": tg["bar"], "kind": kind}
                line_ties.append(rec)
                if kind == "mid_line":
                    mid_line_ties.append(rec)
                else:
                    line_end_ties.append(rec)

        # Evaluate line checks
        n_notes = len(line_notes)
        if syll_count is not None and syll_count > 0:
            deficit = syll_count - n_notes
            excess = n_notes - syll_count
            if deficit > max_deficit_warn:
                deficit_fails.append(f"line {ld['line']}: {n_notes} notes < {syll_count} syllables (deficit {deficit})")
            elif 0 < deficit <= max_deficit_warn:
                deficit_warns.append(f"line {ld['line']}: {n_notes} notes < {syll_count} syllables (deficit {deficit})")
            if excess > max_excess:
                excess_warns.append(f"line {ld['line']}: {n_notes} notes - {syll_count} syllables = +{excess} > cap {max_excess}")
            if pace is not None and (pace < pace_p5 - 1e-6 or pace > pace_p95 + 1e-6):
                pace_warns.append(f"line {ld['line']}: pace {pace:.2f} outside {pace_p5:.2f}-{pace_p95:.2f}")
            if any(t["kind"] == "mid_line" for t in line_ties) and excess > 0:
                ambiguities.append(
                    f"line {ld['line']}: mid-line tie with +{excess} excess notes (tie may hide behind melisma)"
                )

        if abs(reported_span - allocated_bars) > max_span_delta:
            span_warns.append(
                f"line {ld['line']}: span {reported_span} bars vs allocated {allocated_bars}"
            )

        heavy = heavy_syllable_proxy(recomp_texts[i]) if (recomp_texts and i < len(recomp_texts)) else None
        line_reports.append({
            "line": ld["line"],
            "bars": f"{start_b}-{end_b}",
            "allocated_bars": allocated_bars,
            "actual_span_bars": reported_span,
            "syllables": syll_count,
            "notes": n_notes,
            "pace": round(pace, 2) if pace is not None else None,
            "ties": line_ties,
            "heavy_proxy": heavy,
        })

    # Per-line check summaries
    checks.append((
        "line note deficit",
        not deficit_fails,
        "none > 1" if not deficit_fails else "; ".join(deficit_fails[:4]),
        "exact",
        None,
    ))
    if deficit_warns:
        checks.append((
            "line elision deficit",
            False,
            "; ".join(deficit_warns[:4]),
            "banded",
            None,
        ))
    checks.append((
        "line excess notes",
        not excess_warns,
        f"all <= +{max_excess}" if not excess_warns else "; ".join(excess_warns[:4]),
        "banded",
        None,
    ))
    checks.append((
        "line pace",
        not pace_warns,
        f"all within {pace_p5:.2f}-{pace_p95:.2f} sixteenths/syll" if not pace_warns else "; ".join(pace_warns[:4]),
        "banded",
        None,
    ))
    checks.append((
        "line bar span",
        not span_warns,
        f"all within +/-{max_span_delta} bar of allocated" if not span_warns else "; ".join(span_warns[:4]),
        "banded",
        None,
    ))

    # Orphan notes
    orphans = [
        {"bar": n.bar + 1, "onset": n.onset, "pitch": n.pitch}
        for idx, n in enumerate(vocal)
        if idx not in covered_indices and (n.bar + 1) not in vocalise_set
    ]
    orphan_bars = sorted({o["bar"] for o in orphans})
    checks.append((
        "orphan vocal notes",
        not orphans,
        "0 orphan notes" if not orphans else f"{len(orphans)} note(s) outside line windows/vocalise_bars in bar(s) {orphan_bars[:10]}",
        "exact",
        None,
    ))

    # Ambiguous mid-line tie + melisma
    if ambiguities:
        checks.append((
            "tie melisma ambiguity",
            False,
            "; ".join(ambiguities[:4]),
            "banded",
            None,
        ))
    if mid_line_ties:
        checks.append((
            "mid-line ties",
            False,
            f"{len(mid_line_ties)} mid-line tie(s) for review: bars {sorted({t['bar'] for t in mid_line_ties})}",
            "banded",
            "WARN",
        ))

    # Heavy-syllable within-song outlier (partial fix, no corpus)
    heavy_vals = [r["heavy_proxy"] for r in line_reports if r["heavy_proxy"] is not None]
    heavy_outliers: list[int] = []
    if len(heavy_vals) >= 4:
        svals = sorted(heavy_vals)
        q1 = svals[int(0.25 * (len(svals) - 1))]
        q3 = svals[int(0.75 * (len(svals) - 1))]
        iqr = q3 - q1
        med = statistics.median(svals)
        cutoff = (q3 + iqr_factor * iqr) if iqr > 0 else max(med * 2.0, med + 4.0)
        for r in line_reports:
            if r["heavy_proxy"] is not None and r["heavy_proxy"] > cutoff:
                heavy_outliers.append(r["line"])
        if heavy_outliers:
            checks.append((
                "heavy syllable outlier",
                False,
                f"line(s) {heavy_outliers} heavy-syllable proxy outlier (> {cutoff:.1f})",
                "banded",
                None,
            ))

    return {
        "checks": checks,
        "alignment_checked": True,
        "lines": line_reports,
        "orphans": orphans,
        "mid_line_ties": mid_line_ties,
        "line_end_ties": line_end_ties,
        "ambiguities": ambiguities,
        "heavy_outliers": heavy_outliers,
        "vocalise_bars": sorted(vocalise_set),
    }
