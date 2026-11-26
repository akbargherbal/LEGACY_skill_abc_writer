#!/usr/bin/env python3
"""Live measurement for one write call, not a second checker.

The composer writes one lyric line at a time. `checker.py` measures the whole
score, but it is normally invoked at section ends, so a global problem is
reported long after the bar that caused it. This module reuses the checker's
own `measured` block and adds only the two things the checker does not expose:
the per-bar overlap map and the projected note budget for the lines that have
been written.

It never writes a file, never fails a gate and never chooses a note.

Usage:
    from live_meter import measure, format_meter, guard_violations
    payload = measure(text, plan, phrases, state=state, line_no=5)
    print(format_meter(payload))
"""
from __future__ import annotations

import bisect
import math
from pathlib import Path

import checker

PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def pitch_name(midi: int) -> str:
    """Absolute scientific pitch name with the score's flat spelling."""
    return f"{PC_NAME[int(midi) % 12]}{int(midi) // 12 - 1}"


def _unit_seconds(score) -> float:
    return 4.0 / score.unit_den * 60.0 / score.tempo


def overlap_by_bar(score) -> dict[int, float]:
    """Sounding units where Vocal and Ins overlap, keyed by 1-based bar.

    This mirrors the checker's simultaneity guard; it is the one number the
    checker does not expose per bar.
    """
    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    ins = sorted(score.notes_of("Ins"), key=lambda n: n.onset)
    if not vocal or not ins:
        return {}
    starts = [n.onset for n in ins]
    out: dict[int, float] = {}
    for a in vocal:
        a0, a1 = a.onset, a.onset + a.dur
        hi = bisect.bisect_right(starts, a1)
        for b in ins[:hi]:
            b1 = b.onset + b.dur
            if b1 <= a0:
                continue
            s, e = max(a0, b.onset), min(a1, b1)
            if e > s:
                out[a.bar + 1] = out.get(a.bar + 1, 0.0) + (e - s)
    return out


def _line_def(phrases: dict, line_no: int | None) -> dict | None:
    if line_no is None:
        return None
    for line in (phrases or {}).get("lines", []):
        if int(line.get("line", -1)) == int(line_no):
            return line
    return None


def _notes_in_bars(score, start: int, end: int) -> list:
    return [n for n in score.notes_of("Vocal") if start - 1 <= n.bar <= end - 1]


def _gap_after(score, line: dict, phrases: dict) -> float | None:
    """Seconds from the line's last note to the next note or the bar end."""
    start, end = int(line["bar_start"]), int(line["bar_end"])
    notes = _notes_in_bars(score, start, end)
    if not notes:
        return None
    last = max(notes, key=lambda n: n.onset + n.dur)
    end_u = float(score.bar_starts[end])
    # A written next line may start with a pickup before its own bar line.
    later = [n for n in score.notes_of("Vocal") if n.onset >= end_u - 1e-9]
    if later:
        nxt = min(later, key=lambda n: n.onset)
        end_u = min(end_u, float(nxt.onset))
    return max(0.0, (end_u - (last.onset + last.dur)) * _unit_seconds(score))


def measure(score_text: str, plan: dict, phrases: dict, *, state: dict | None = None,
            line_no: int | None = None, bars: list[int] | None = None,
            lyrics_path: Path | str | None = None,
            calibration: dict | None = None) -> dict:
    """Return one compact measurement bundle. Never raises on a partial score."""
    cal = calibration if calibration is not None else checker.load_calibration()
    try:
        score = checker.parse(score_text)
    except Exception as exc:  # noqa: BLE001 - a diagnostic must not break a write
        return {"error": f"{type(exc).__name__}: {exc}"}

    lyrics_text = None
    if lyrics_path:
        p = Path(lyrics_path)
        if p.exists():
            lyrics_text = p.read_text(encoding="utf-8")
    try:
        _, measured = checker.check(
            score, plan, plan_present=bool(plan), strict_style=False,
            strict_shape=bool(plan.get("strict_shape", False)),
            require_final_rest=False, phrase_plan=phrases, calibration=cal,
            lyrics_text=lyrics_text, waive_lyrics=lyrics_text is None,
            score_text=score_text,
        )
    except Exception as exc:  # noqa: BLE001
        measured = {}
        measured["_error"] = f"{type(exc).__name__}: {exc}"

    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    durations = [int(round(n.dur)) for n in vocal]
    duration_counts: dict[int, int] = {}
    for d in durations:
        duration_counts[d] = duration_counts.get(d, 0) + 1

    lines = list((phrases or {}).get("lines", []))
    total_syllables = int(plan.get("syllables") or sum(int(l.get("syllables", 0)) for l in lines))
    written = {int(x) for x in (state or {}).get("written_lines", [])}
    if not written:
        written = {
            int(l["line"]) for l in lines
            if int(l.get("bar_start", 0)) <= score.n_bars
            and _notes_in_bars(score, int(l["bar_start"]), int(l["bar_end"]))
        }
    syllables_written = sum(int(l.get("syllables", 0)) for l in lines
                            if int(l.get("line", -1)) in written)
    notes_written = len(vocal)
    projected = (round(notes_written / syllables_written * total_syllables)
                 if syllables_written else None)

    mel_min = float(plan.get("melisma_min", 1.0))
    mel_max = float(plan.get("melisma_max", 1.55))
    need_low = int(math.ceil(total_syllables * mel_min)) if total_syllables else None
    need_high = int(math.floor(total_syllables * mel_max)) if total_syllables else None

    overlaps = overlap_by_bar(score)
    cap = float((cal.get("sanity", {}).get("simultaneity_le4", {}) or {}).get("max", 4))
    exception = plan.get("simultaneity_exception")

    line_payload = None
    line = _line_def(phrases, line_no)
    if line is not None:
        start, end = int(line["bar_start"]), int(line["bar_end"])
        notes = _notes_in_bars(score, start, end)
        syl = line.get("syllables")
        line_payload = {
            "line": int(line.get("line", line_no)),
            "bars": [start, end],
            "notes": len(notes),
            "syllables": int(syl) if syl is not None else None,
            "deficit": (int(syl) - len(notes)) if syl is not None else None,
            "gap_s": _gap_after(score, line, phrases),
            "gap_target_s": line.get("pause_after_s"),
            "overlap": sum(overlaps.get(b, 0.0) for b in range(start, end + 1)),
        }
    elif bars:
        line_payload = {
            "line": None,
            "bars": [min(bars), max(bars)],
            "notes": sum(len(_notes_in_bars(score, b, b)) for b in bars),
            "syllables": None,
            "deficit": None,
            "gap_s": None,
            "gap_target_s": None,
            "overlap": sum(overlaps.get(b, 0.0) for b in bars),
        }

    sanity = (cal.get("sanity") or {})
    return {
        "bars": score.n_bars,
        "unit_seconds": round(_unit_seconds(score), 4),
        "vocal_notes": len(vocal),
        "notes_written": notes_written,
        "syllables_written": syllables_written,
        "syllables_total": total_syllables,
        "projected": projected,
        "need_low": need_low,
        "need_high": need_high,
        "ratio": measured.get("notes_per_syllable"),
        "register_mean": measured.get("register_mean"),
        "repeated_share": measured.get("repeated_share"),
        "distinct_durations": measured.get("distinct_durations"),
        "duration_counts": duration_counts,
        "top_duration_share": measured.get("top_duration_share"),
        "ties": measured.get("ties"),
        "ties_min": plan.get("ties_min"),
        "min_distinct": plan.get("min_distinct_durations"),
        "max_top_share": plan.get("max_top_duration_share"),
        "overlaps": overlaps,
        "overlap_total": round(sum(overlaps.values()), 1),
        "overlap_cap": cap,
        "overlap_exception": exception,
        "line": line_payload,
        "written_lines": len(written),
        "total_lines": len(lines),
        "error": measured.get("_error"),
        "sanity": {
            "notes_min": float((sanity.get("notes_per_syllable_1.0_1.55") or {}).get("min", 1.0)),
            "notes_max": float((sanity.get("notes_per_syllable_1.0_1.55") or {}).get("max", 1.55)),
            "register_mean": float((sanity.get("register_mean_74_5") or {}).get("mean", 74)),
            "register_tolerance": float((sanity.get("register_mean_74_5") or {}).get("tolerance", 5)),
            "repeated_min": float((sanity.get("repeated_share_ge_0.20") or {}).get("min", 0.20)),
            "distinct_min": int((sanity.get("distinct_durations_ge4") or {}).get("min", 4)),
            "top_share_max": float((sanity.get("top_duration_share_le_0.85") or {}).get("max", 0.85)),
        },
    }


def _fmt_durations(payload: dict) -> str:
    counts = payload.get("duration_counts") or {}
    if not counts:
        return "durations -"
    parts = [f"{d}:{n}" for d, n in sorted(counts.items())]
    distinct = payload.get("distinct_durations") or len(counts)
    target = payload.get("min_distinct")
    tail = f" ({distinct} of {target})" if target else f" ({distinct})"
    if target and distinct < int(target):
        tail += " add a 1 or 8"
    return "durations " + " ".join(parts) + tail


def format_meter(payload: dict) -> str:
    if payload.get("error"):
        return f"meter unavailable: {payload['error']}"
    out: list[str] = []
    line = payload.get("line")
    if line:
        if line.get("line") is not None:
            out.append(
                f"meter line {line['line']} (bars {line['bars'][0]}-{line['bars'][1]}): "
                f"{line['notes']} notes / {line['syllables']} syllables"
                + (f" — deficit {line['deficit']}" if (line.get("deficit") or 0) > 0
                   else (f" — +{abs(line['deficit'])}" if (line.get("deficit") or 0) < 0 else ""))
            )
        else:
            out.append(
                f"meter bars {line['bars'][0]}-{line['bars'][1]}: "
                f"{line['notes']} notes"
            )
    written = payload.get("notes_written", 0)
    syll_written = payload.get("syllables_written", 0)
    total = payload.get("syllables_total", 0)
    if syll_written:
        proj = payload.get("projected")
        proj_txt = f" → projected {proj}/{total}" if proj is not None else ""
        band = ""
        if payload.get("need_low") is not None:
            band = f" (need {payload['need_low']}-{payload['need_high']})"
        out.append(f"score  {written}/{syll_written} notes{proj_txt}{band}")
    parts = []
    if payload.get("repeated_share") is not None:
        parts.append(f"repeats {payload['repeated_share']:.0%}")
    parts.append(_fmt_durations(payload))
    if payload.get("register_mean") is not None:
        parts.append(f"register {payload['register_mean']:.1f}")
    if payload.get("ties") is not None and payload.get("ties_min") is not None:
        parts.append(f"ties {payload['ties']}/{payload['ties_min']}")
    out.append("       " + "  ".join(parts))
    tail = []
    if line and line.get("gap_s") is not None and line.get("gap_target_s") is not None:
        gap = line["gap_s"]
        target = float(line["gap_target_s"])
        hint = ""
        if gap + 0.01 < target:
            unit_s = float(payload.get("unit_seconds") or 0)
            need = max(1, math.ceil((target - gap) / unit_s - 1e-9)) if unit_s else 1
            hint = f" — add z{need}"
        tail.append(f"gap after {gap:.2f}s (target {target:.2f}s{hint})")
    if line:
        tail.append(f"overlaps {line.get('overlap', 0):g} this line / "
                    f"{payload.get('overlap_total', 0):g} total (max {payload.get('overlap_cap', 4):g})")
    if tail:
        out.append("       " + "  ".join(tail))
    return "\n".join(out)


def guard_violations(payload: dict) -> list[str]:
    """Existing hard sanity rules, checked at the write call. Opt-in only."""
    if payload.get("error"):
        return []
    out: list[str] = []
    line = payload.get("line") or {}
    if (line.get("deficit") or 0) > 1:
        out.append(f"line {line.get('line')}: note deficit {line['deficit']} > 1")
    if (line.get("gap_s") is not None and line.get("gap_target_s") is not None
            and line["gap_s"] + 0.01 < float(line["gap_target_s"])):
        out.append(f"line {line.get('line')}: gap {line['gap_s']:.2f}s < "
                   f"target {float(line['gap_target_s']):.2f}s")
    cap = float(payload.get("overlap_cap", 4))
    if line and (line.get("overlap") or 0) > cap:
        out.append(f"line {line.get('line')}: {line['overlap']:g} overlapping 16ths > {cap:g}")
    if (payload.get("written_lines", 0) >= payload.get("total_lines", 1)
            and not payload.get("error")):
        s = payload.get("sanity") or {}
        ratio = payload.get("ratio")
        if ratio is not None and not (s.get("notes_min", 1.0) <= ratio <= s.get("notes_max", 1.55)):
            out.append(f"notes/syllable {ratio:.2f} outside {s.get('notes_min')}-{s.get('notes_max')}")
        reg = payload.get("register_mean")
        if reg is not None and abs(reg - s.get("register_mean", 74)) > s.get("register_tolerance", 5):
            out.append(f"register mean {reg:.1f} outside {s.get('register_mean')}±{s.get('register_tolerance')}")
        rep = payload.get("repeated_share")
        if rep is not None and rep < s.get("repeated_min", 0.20):
            out.append(f"repeated share {rep:.0%} < {s.get('repeated_min') or 0.20:.0%}")
        distinct = payload.get("distinct_durations")
        if distinct is not None and distinct < s.get("distinct_min", 4):
            out.append(f"distinct durations {distinct} < {s.get('distinct_min')}")
        top = payload.get("top_duration_share")
        if top is not None and top > s.get("top_share_max", 0.85):
            out.append(f"top duration share {top:.0%} > {s.get('top_share_max'):.0%}")
    return out
