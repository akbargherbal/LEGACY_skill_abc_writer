"""Verify declared borrowings and report remix metrics.

This module is deliberately mechanical: it compares interval and duration
sequences, reports what it found, and never claims the result is good.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from . import shared

shared.bootstrap()

from ostris.mode import key_info  # noqa: E402

from . import textcap
from .errors import RemixError
from .store import Note, Store, ranges, voice_notes
from .transforms import Expected, apply_transforms, contour as contour_tokens

MIN_UNDECLARED = 8
MIN_INFO_DISTINCT = 2
MIN_INFO_SPAN = 3


def _longest_run(left: list[int], right: list[int]) -> tuple[int, int, int]:
    """Return (length, left_start, right_start) of the longest common run."""
    if not left or not right:
        return 0, 0, 0
    previous = [0] * (len(right) + 1)
    best = (0, 0, 0)
    for i, a in enumerate(left, start=1):
        current = [0] * (len(right) + 1)
        for j, b in enumerate(right, start=1):
            if a == b:
                current[j] = previous[j - 1] + 1
                if current[j] > best[0]:
                    best = (current[j], i - current[j], j - current[j])
        previous = current
    return best


def _informative(intervals: list[int]) -> bool:
    if not intervals:
        return False
    return len(set(intervals)) >= MIN_INFO_DISTINCT


def _notes_in_ranges(notes: list[Note], requested: list[tuple[int, int]]) -> list[Note]:
    out = []
    for note in notes:
        bar = note.bar + 1
        if any(first <= bar <= last for first, last in requested):
            out.append(note)
    return out


def _target_bars(notes: list[Note], start_index: int, count: int) -> tuple[int, int]:
    end_index = min(start_index + count - 1, len(notes) - 1)
    return notes[start_index].bar + 1, notes[end_index].bar + 1


def _compare(expected: Expected, target: list[Note], start: int,
             tolerance: int) -> tuple[bool, int, bool]:
    """Return (matched, mismatches, duration_ok) for a candidate offset."""
    count = max(len(expected.intervals) + 1 if not expected.ignore_pitch else len(expected.durations),
                len(expected.durations))
    if expected.ignore_pitch:
        count = len(expected.durations)
    if start + count > len(target):
        return False, count, False
    window = target[start:start + count]
    target_intervals = [b.pitch - a.pitch for a, b in zip(window, window[1:])]
    target_durations = [round(note.duration, 6) for note in window]
    mismatches = 0

    if expected.ignore_intervals:
        got = contour_tokens(target_intervals)
        mismatches += sum(1 for a, b in zip(got, expected.contour) if a != b)
        mismatches += abs(len(got) - len(expected.contour))
        return mismatches <= tolerance, mismatches, True

    if not expected.ignore_pitch:
        got = target_intervals
        mismatches += sum(1 for a, b in zip(got, expected.intervals) if a != b)
        mismatches += abs(len(got) - len(expected.intervals))

    if not expected.ignore_intervals:
        got = target_durations
        want = expected.durations
        mismatches += sum(
            1 for a, b in zip(got, want) if abs(float(a) - float(b)) > 1e-6
        )
        mismatches += abs(len(got) - len(want))
    return mismatches <= tolerance, mismatches, True


def verify_item(store: Store, item: dict, target_notes: dict[str, list[Note]]) -> dict:
    song_id = item.get("id")
    result = {
        "id": song_id,
        "role": item.get("role"),
        "voice": item.get("voice", "both"),
        "from_bars": item.get("from_bars"),
        "to_bars": item.get("to_bars"),
        "transform": list(item.get("transform") or []),
        "status": "not_found",
        "reason": None,
        "matches": [],
        "literal": False,
    }
    try:
        if not song_id or song_id not in store.catalog_by_id():
            result["reason"] = "source_not_found"
            return result
        from_ranges = ranges(item.get("from_bars", ""))
        to_ranges = ranges(item.get("to_bars", ""))
        source_rows = [row for row in store.load_catalog() if row["song_id"] == song_id]
        if not source_rows:
            result["reason"] = "source_not_found"
            return result
        _text, score = store.load_song(song_id)
        source_voice = item.get("voice", "both")
        if source_voice == "both":
            source_voice = "Vocal" if voice_notes(score, "Vocal") else "Ins"
        source = _notes_in_ranges(voice_notes(score, source_voice), from_ranges)
        if len(source) < 2:
            result["reason"] = "source_bars_empty"
            return result
        expected = apply_transforms(
            [(note.pitch, note.duration) for note in source],
            item.get("transform") or [],
        )
        target_voice = item.get("voice", "both")
        voices = ["Vocal", "Ins"] if target_voice == "both" else [target_voice]
        tolerance = int(item.get("_tolerance", 0))
        for name in voices:
            notes = target_notes.get(name, [])
            for start in range(len(notes)):
                if notes[start].bar + 1 < min(first for first, _ in to_ranges):
                    continue
                if notes[start].bar + 1 > max(last for _, last in to_ranges):
                    break
                matched, mismatches, _ok = _compare(expected, notes, start, tolerance)
                if not matched:
                    continue
                count = len(expected.durations) if expected.ignore_pitch else len(expected.intervals) + 1
                first_bar, last_bar = _target_bars(notes, start, count)
                if not any(a <= first_bar and last_bar <= b for a, b in to_ranges):
                    continue
                result["matches"].append({
                    "voice": name,
                    "bars": [first_bar, last_bar],
                    "start_index": start,
                    "end_index": start + count - 1,
                    "notes": count,
                    "mismatches": mismatches,
                    "literal": bool(expected.literal and mismatches == 0),
                })
        if not result["matches"]:
            result["reason"] = "no_matching_run"
            return result
        result["status"] = "verified" if all(
            match["mismatches"] == 0 for match in result["matches"]
        ) else "partial"
        result["literal"] = any(match["literal"] for match in result["matches"])
    except RemixError as error:
        result["reason"] = str(error)
    return result


def undeclared(store: Store, score, declared: list[dict]) -> tuple[list[dict], int]:
    target_notes = {name: voice_notes(score, name) for name in ("Vocal", "Ins")}
    index = store.load_index()
    postings = index.get("interval_postings", {})
    declared_spans: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for item in declared:
        if item.get("status") not in ("verified", "partial"):
            continue
        for match in item.get("matches", []):
            first, last = match["bars"]
            declared_spans[item["id"]].append((match["voice"], first, last))
    cache: dict[str, object] = {}
    found = []
    total = 0
    for voice, notes in target_notes.items():
        pitches = [note.pitch for note in notes]
        intervals = [b - a for a, b in zip(pitches, pitches[1:])]
        candidates: set[str] = set()
        for start in range(max(0, len(intervals) - 3)):
            key = ",".join(map(str, intervals[start:start + 4]))
            candidates.update(postings.get(key, []))
        for candidate in sorted(candidates):
            song_id, _, source_voice = candidate.rpartition("|")
            if source_voice != voice:
                continue
            if song_id not in cache:
                try:
                    _text, source_score = store.load_song(song_id)
                except RemixError:
                    continue
                cache[song_id] = source_score
            source_notes = voice_notes(cache[song_id], source_voice)
            source_pitches = [note.pitch for note in source_notes]
            source_intervals = [b - a for a, b in zip(source_pitches, source_pitches[1:])]
            run, target_start, source_start = _longest_run(intervals, source_intervals)
            if run < MIN_UNDECLARED:
                continue
            if not _informative(intervals[target_start:target_start + run]):
                continue
            target_window = notes[target_start:target_start + run + 1]
            source_window = source_notes[source_start:source_start + run + 1]
            if len(target_window) != len(source_window):
                continue
            if any(
                abs(a.duration - b.duration) > 1e-6
                for a, b in zip(target_window, source_window)
            ):
                continue
            first_bar, last_bar = _target_bars(notes, target_start, run + 1)
            source_first = (
                source_notes[source_start].bar + 1
                if source_start < len(source_notes) else None
            )
            source_last = (
                source_notes[min(source_start + run, len(source_notes) - 1)].bar + 1
                if source_notes else None
            )
            declared_here = any(
                span_voice == voice and not (last_bar < first or first_bar > last)
                for span_voice, first, last in declared_spans.get(song_id, [])
            )
            if declared_here:
                continue
            entry = {
                "source_id": song_id,
                "voice": voice,
                "target_bars": [first_bar, last_bar],
                "source_bars": [source_first, source_last],
                "run": run,
                "declared": False,
            }
            total += 1
            if len(found) < 10:
                found.append(entry)
    found.sort(key=lambda item: (-item["run"], item["source_id"], item["target_bars"][0]))
    return found, total


def _novelty(store: Store, score) -> dict:
    target_notes = {name: voice_notes(score, name) for name in ("Vocal", "Ins")}
    target_intervals = {
        name: [b.pitch - a.pitch for a, b in zip(notes, notes[1:])]
        for name, notes in target_notes.items()
    }
    total_notes = sum(len(notes) for notes in target_notes.values())
    index = store.load_index()
    postings = index.get("interval_postings", {})
    candidates: set[str] = set()
    for voice, intervals in target_intervals.items():
        for start in range(max(0, len(intervals) - 3)):
            key = ",".join(map(str, intervals[start:start + 4]))
            candidates.update(postings.get(key, []))
    best = {"run": 0, "song_id": None, "voice": None}
    cache: dict[str, object] = {}
    for candidate in sorted(candidates):
        song_id, _, voice = candidate.rpartition("|")
        if voice not in ("Vocal", "Ins"):
            continue
        if song_id not in cache:
            try:
                _text, source_score = store.load_song(song_id)
            except RemixError:
                continue
            cache[song_id] = source_score
        source_notes = voice_notes(cache[song_id], voice)
        source_intervals = [b.pitch - a.pitch for a, b in zip(source_notes, source_notes[1:])]
        run, _ts, _ss = _longest_run(target_intervals[voice], source_intervals)
        if run > best["run"]:
            best = {"run": run, "song_id": song_id, "voice": voice}
    overlap_notes = best["run"] + 1 if best["run"] else 0
    overlap = min(1.0, overlap_notes / total_notes) if total_notes else 0.0
    return {
        "novelty": round(1.0 - overlap, 4),
        "overlap": round(overlap, 4),
        "largest_overlap_source": best["song_id"],
        "largest_overlap_voice": best["voice"],
        "largest_overlap_notes": overlap_notes,
        "total_notes": total_notes,
    }


def _metrics(store: Store, score, quotes: list[dict], undeclared_rows: list[dict], undeclared_total: int) -> dict:
    target_notes = {name: voice_notes(score, name) for name in ("Vocal", "Ins")}
    total_bars = len(score.voices["Vocal"].bars)
    total_notes = sum(len(notes) for notes in target_notes.values())
    quote_notes: dict[str, set[int]] = {"Vocal": set(), "Ins": set()}
    literal_notes: dict[str, set[int]] = {"Vocal": set(), "Ins": set()}
    literal_bars: dict[str, set[int]] = {"Vocal": set(), "Ins": set()}
    sources = set()
    mix = Counter()
    for quote in quotes:
        if quote.get("status") not in ("verified", "partial"):
            continue
        sources.add(quote["id"])
        for match in quote.get("matches", []):
            voice = match["voice"]
            notes = target_notes[voice]
            first_bar, last_bar = match["bars"]
            if "start_index" in match and "end_index" in match:
                indexes = range(match["start_index"], match["end_index"] + 1)
                quote_notes[voice].update(indexes)
                if match.get("literal"):
                    literal_notes[voice].update(indexes)
            else:
                for index, note in enumerate(notes):
                    if first_bar <= note.bar + 1 <= last_bar:
                        quote_notes[voice].add(index)
                        if match.get("literal"):
                            literal_notes[voice].add(index)
            if match.get("literal"):
                literal_bars[voice].update(range(first_bar, last_bar + 1))
            for transform in quote.get("transform") or []:
                mix[transform.split(":", 1)[0].strip().lower()] += 1
            if not quote.get("transform"):
                mix["literal"] += 1
    coverage = {
        voice: round(
            len({note.bar for index, note in enumerate(target_notes[voice])
                 if index in quote_notes[voice]} & set(range(total_bars))) / max(1, total_bars),
            4,
        )
        for voice in ("Vocal", "Ins")
    }
    literal_count = sum(len(value) for value in literal_notes.values())
    max_literal_run = 0
    for bars_set in literal_bars.values():
        run = 0
        previous = None
        for bar in sorted(bars_set):
            run = run + 1 if previous is not None and bar == previous + 1 else 1
            max_literal_run = max(max_literal_run, run)
            previous = bar
    novelty = _novelty(store, score)
    return {
        "quote_coverage": coverage,
        "quote_notes": {voice: len(value) for voice, value in quote_notes.items()},
        "literal_share": round(literal_count / total_notes, 4) if total_notes else 0.0,
        "literal_notes": literal_count,
        "max_literal_run_bars": max_literal_run,
        "source_diversity": len(sources),
        "transform_mix": dict(sorted(mix.items())),
        "undeclared_count": undeclared_total,
        "novelty": novelty,
        "total_notes": total_notes,
        "total_bars": total_bars,
    }


def _validate_block(block: dict) -> list[str]:
    errors = []
    if not isinstance(block, dict):
        return ["remix must be an object"]
    if not isinstance(block.get("concept"), str) or not block["concept"].strip():
        errors.append("remix.concept must be a non-empty string")
    sources = block.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("remix.sources must be a non-empty list")
        return errors
    for index, item in enumerate(sources):
        prefix = f"remix.sources[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in ("id", "role", "from_bars", "to_bars", "voice"):
            if not item.get(key):
                errors.append(f"{prefix}.{key} is required")
        if item.get("voice") not in ("Vocal", "Ins", "both"):
            errors.append(f"{prefix}.voice must be Vocal, Ins, or both")
        if not isinstance(item.get("transform", []), list):
            errors.append(f"{prefix}.transform must be a list")
    cap = block.get("literal_cap_bars", 4)
    if not isinstance(cap, int) or cap < 0:
        errors.append("remix.literal_cap_bars must be a non-negative integer")
    return errors


def check(store: Store, score_path: str | Path, plan_path: str | Path, *,
          require_final_rest: bool = False, strict_style: bool = False,
          strict_quotes: bool = False, fail_on_undeclared: bool = False,
          tolerance: int = 0, ostris_dir: str | Path | None = None) -> dict:
    score_path = Path(score_path)
    plan_path = Path(plan_path)
    if not score_path.is_file():
        raise RemixError(f"missing score: {score_path}", code=5)
    if not plan_path.is_file():
        raise RemixError(f"missing plan: {plan_path}", code=5)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    block = plan.get("remix")
    if block is None:
        raise RemixError("plan has no remix block; `remix check` requires one")
    block_errors = _validate_block(block)
    if block_errors:
        raise RemixError("; ".join(block_errors))

    from ostris.check import check as ostris_check

    out_dir = Path(ostris_dir) if ostris_dir else shared.ostris_data_dir()
    if not out_dir.is_dir():
        out_dir = None
    skill_report = ostris_check(
        score_path,
        plan_path,
        out_dir=out_dir,
        require_final_rest=require_final_rest,
        strict_style=strict_style,
    )
    # The target score is not a library song; load it directly.
    import abc_tools

    score = abc_tools.parse(score_path.read_text(encoding="utf-8"))
    target_notes = {name: voice_notes(score, name) for name in ("Vocal", "Ins")}

    quotes = []
    for item in block.get("sources", []):
        item = dict(item)
        item["_tolerance"] = tolerance
        quotes.append(verify_item(store, item, target_notes))
    undeclared_rows, undeclared_total = undeclared(store, score, quotes)
    metrics = _metrics(store, score, quotes, undeclared_rows, undeclared_total)

    failures = []
    warnings = []
    for item in skill_report.get("failures", []):
        failures.append({
            "code": item.get("code", "checker"),
            "class": item.get("class", "contract"),
            "detail": item.get("detail", ""),
        })
    for item in skill_report.get("warnings", []):
        warnings.append({
            "code": item.get("code", "checker"),
            "class": item.get("class", "style"),
            "detail": item.get("detail", ""),
        })
    if not skill_report.get("pass"):
        failures.append({
            "code": "checker_failed",
            "class": "contract",
            "detail": f"skill checker class={skill_report.get('class')}",
        })
    for quote in quotes:
        if quote["status"] == "not_found":
            message = f"{quote['id']} ({quote.get('role')}): {quote.get('reason')}"
            target = failures if strict_quotes else warnings
            target.append({
                "code": "quote_not_found",
                "class": "remix",
                "detail": message,
            })
        elif quote["status"] == "partial":
            warnings.append({
                "code": "quote_partial",
                "class": "remix",
                "detail": f"{quote['id']}: matched with mismatches",
            })
    cap = int(block.get("literal_cap_bars", 4))
    if metrics["max_literal_run_bars"] > cap:
        failures.append({
            "code": "literal_cap",
            "class": "remix",
            "detail": (
                f"max literal run {metrics['max_literal_run_bars']} bars > "
                f"cap {cap}"
            ),
        })
    if undeclared_rows:
        target = failures if fail_on_undeclared else warnings
        target.append({
            "code": "undeclared_quote",
            "class": "remix",
            "detail": (
                f"{undeclared_total} undeclared run(s); strongest "
                f"{undeclared_rows[0]['source_id']} run {undeclared_rows[0]['run']}"
            ),
        })

    class_name = "fail" if failures else "warn" if warnings else "pass"
    report = {
        "stage": "remix-check",
        "score": str(score_path),
        "plan": str(plan_path),
        "pass": not failures,
        "class": class_name,
        "failures": failures,
        "warnings": warnings,
        "skill_report": skill_report,
        "checker": {
            "pass": skill_report.get("pass"),
            "class": skill_report.get("class"),
            "failures": len(skill_report.get("failures", [])),
            "warnings": len(skill_report.get("warnings", [])),
        },
        "remix": {
            "concept": block.get("concept"),
            "literal_cap_bars": cap,
            "quotes": quotes,
            "undeclared": undeclared_rows,
            "undeclared_total": undeclared_total,
            "metrics": metrics,
        },
        "maqam_conditioned": False,
    }
    return report


def render(report: dict, max_chars: int = 4000) -> str:
    remix = report.get("remix", {})
    quotes = remix.get("quotes", [])
    metrics = remix.get("metrics", {})
    checker = report.get("checker", {})
    verified = sum(1 for quote in quotes if quote.get("status") == "verified")
    partial = sum(1 for quote in quotes if quote.get("status") == "partial")
    missing = sum(1 for quote in quotes if quote.get("status") == "not_found")
    coverage = metrics.get("quote_coverage", {})
    novelty = metrics.get("novelty", {})
    lines = [
        f"remix check: {str(report.get('class', '?')).upper()}",
        f"declared: {verified}/{len(quotes)} verified, {partial} partial, {missing} not found",
        f"quote coverage: Vocal {coverage.get('Vocal', 0):.1%} | "
        f"Ins {coverage.get('Ins', 0):.1%}",
        f"literal: {metrics.get('literal_share', 0):.1%} notes | "
        f"max literal run {metrics.get('max_literal_run_bars', 0)} bars "
        f"(cap {remix.get('literal_cap_bars', '?')})",
        f"novelty: {novelty.get('novelty', 0):.2f} | "
        f"largest overlap {novelty.get('overlap', 0):.1%} "
        f"({novelty.get('largest_overlap_source') or 'none'})",
        f"sources used: {metrics.get('source_diversity', 0)} | "
        f"transforms: {metrics.get('transform_mix', {})}",
        f"undeclared: {metrics.get('undeclared_count', 0)}",
        f"checker: {'PASS' if checker.get('pass') else 'FAIL'} "
        f"({checker.get('failures', 0)} hard, {checker.get('warnings', 0)} warnings)",
    ]
    for failure in report.get("failures", []):
        lines.append(f"FAIL [{failure.get('class')}] {failure.get('code')}: {failure.get('detail')}")
    for warning in report.get("warnings", []):
        lines.append(f"WARN [{warning.get('class')}] {warning.get('code')}: {warning.get('detail')}")
    return textcap.enforce("quote_report", "\n".join(lines), max_chars)
