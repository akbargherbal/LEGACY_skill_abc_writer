#!/usr/bin/env python3
"""Whole-draft scorecard: one ranked report after a full score write.

This is the validator for the whole-draft workflow, not a composer. It reuses
``checker.py`` (the oracle) and reports only what a rewrite needs:

    python3 scorecard.py score.abc --plan plan.json --phrases phrases.json
    python3 scorecard.py score.abc --plan plan.json --phrases phrases.json --json card.json
    python3 scorecard.py score.abc --plan plan.json --phrases phrases.json --all-seams

Output:

    SCORE  82 bars | 406 notes | 361 syllables | 1.12 notes/syll
    CHECKS 48 pass | 3 blocking | 0 release-blocking | 2 polish

    KEY BANDS (FAIL = hard, WARN = plan/polish)
      register mean   mean 68.2 vs sanity 74 +/- 5          FAIL
      ...

    BLOCKING
      1. [sanity] register mean: ...
         fix: ...

    SEAMS (flagged 4 of 25)
      4->5  bars 13-14->15-16  A4->A4 (0)  rest 0.19/0.50  reg +0.4  ovl 0  REST SAME

It never writes a note, never changes checker.py or calibration.json, and
never fails a score by itself. Exit codes: 0 nothing blocks, 1 BLOCKING or
RELEASE-BLOCKING (the strict pass `release` runs), 2 parse error.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import abc_tools  # noqa: E402
import checker  # noqa: E402
import live_meter  # noqa: E402

CLASS_ORDER = {
    "contract": 0,
    "sanity": 1,
    "exact": 1,
    "structure": 2,
    "banded": 2,
    "style": 3,
}
TAG_RANK = {"FAIL": 0, "WARN": 1, "PASS": 2, "INFO": 3}

# label -> (primary check, secondary check). The worst verdict of the two is
# shown; the detail comes from that check, so the thresholds are the checker's.
BAND_ROWS = [
    ("notes / syllable", "notes per syllable", "melisma target"),
    ("register mean", "register mean", "register target mean"),
    ("register top", "register target top", "register top floor"),
    ("repeated notes", "repeated notes", None),
    ("durations", "duration variety", "duration variety target"),
    ("top duration", "duration spread", "duration spread target"),
    ("simultaneity", "simultaneity", None),
    ("ties", "ties floor", "ties target"),
    ("final rest", "final rest", None),
    ("unbroken", "unbroken singing", "unbroken target"),
    ("phrase endings", "phrase endings", "phrase endings target"),
    ("ins activity", "ins activity", "ins activity target"),
    ("cadence", "cadence on tonic", None),
]

HINTS = {
    "register mean": "move the median into the hard band; lift the verses/chorus",
    "repeated notes": "repeat a pitch at phrase heads and cadences; the floor is 20%",
    "simultaneity": "pull Ins out of Vocal; the cap is 4 units TOTAL, not per bar",
    "notes per syllable": "add or remove notes; target the plan melisma band",
    "melisma target": "the ratio is outside the plan's melisma band",
    "duration variety": "use at least 4 (plan 5) distinct durations",
    "duration spread": "the most common duration is too dominant; add longer notes",
    "duration spread target": "the plan wants a broader duration mix",
    "unbroken singing": "insert a breath; the line runs too long without rest",
    "unbroken target": "the plan's unbroken target is tighter than the sanity cap",
    "phrase plan": "fix the named line(s): deficit, excess, pace or bar span",
    "line note deficit": "add notes to the named line(s)",
    "line excess notes": "remove notes from the named line(s)",
    "cadence on tonic": "end the vocal on the tonic",
    "final rest": "end with Z| in both voices",
    "ins activity": "let the guitar sound in more bars",
    "register top floor": "reach the top-register floor at least once",
    "register target mean": "the mean is outside the plan's register band",
    "register target top": "the top note is below the plan target",
    "register max top": "the top note is above the plan ceiling",
}


def _worst_tag(tags: list[str]) -> str:
    return min(tags, key=lambda t: TAG_RANK.get(t, 9)) if tags else "PASS"


def _check_map(checks):
    out: dict[str, tuple[str, str, str]] = {}
    for tag, name, _ok, detail, cls in checks:
        old = out.get(name)
        if old is None or TAG_RANK.get(tag, 9) < TAG_RANK.get(old[0], 9):
            out[name] = (tag, detail, cls)
    return out


def _hint(name: str, cls: str) -> str:
    if name in HINTS:
        return HINTS[name]
    if cls == "contract":
        return "fix the syntax/header first; no other metric is meaningful"
    if cls == "exact":
        return "the plan, lyrics and score disagree; fix the exact agreement"
    if cls == "sanity":
        return "this is a hard band; fix it in the next full rewrite"
    if cls in ("structure", "banded"):
        return "a plan-shape target; fix it or declare it as a deviation"
    return "polish; not blocking unless release"


def _line_rows(score, phrases: dict) -> list[dict]:
    """One row per lyric line: notes, register, end/start pitch, overlap, gap."""
    unit_s = 4.0 / score.unit_den * 60.0 / score.tempo
    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    overlaps = live_meter.overlap_by_bar(score)
    rows: list[dict] = []
    for line in (phrases or {}).get("lines", []):
        try:
            number = int(line.get("line"))
            start = int(line["bar_start"])
            end = int(line["bar_end"])
        except (TypeError, KeyError, ValueError):
            continue
        notes = [n for n in vocal if start - 1 <= n.bar <= end - 1]
        bars_label = str(start) if start == end else f"{start}-{end}"
        if not notes:
            rows.append({"line": number, "bars": bars_label, "section": line.get("section", ""),
                         "start": start, "end": end, "empty": True})
            continue
        first, last = notes[0], notes[-1]
        rows.append({
            "line": number,
            "bars": bars_label,
            "section": line.get("section", ""),
            "start": start,
            "end": end,
            "empty": False,
            "syllables": line.get("syllables"),
            "pause": line.get("pause_after_s"),
            "notes": len(notes),
            "start_pitch": first.pitch,
            "end_pitch": last.pitch,
            "first_onset": first.onset,
            "last_end": last.onset + last.dur,
            "mean_pitch": statistics.mean(n.pitch for n in notes),
            "overlap": sum(overlaps.get(b, 0.0) for b in range(start, end + 1)),
        })
    for i, row in enumerate(rows):
        if row.get("empty"):
            continue
        nxt = next((r for r in rows[i + 1:] if not r.get("empty")), None)
        row["rest_after_s"] = (
            round(max(0.0, (nxt["first_onset"] - row["last_end"]) * unit_s), 2)
            if nxt else None
        )
    return rows


def _seams(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for a, b in zip(rows, rows[1:]):
        if a.get("empty") or b.get("empty"):
            continue
        delta = int(b["start_pitch"] - a["end_pitch"])
        reg = float(b["mean_pitch"] - a["mean_pitch"])
        rest = a.get("rest_after_s")
        target = a.get("pause")
        flags: list[str] = []
        same_section = (a.get("section") or "") == (b.get("section") or "")
        if target is not None and rest is not None and rest + 0.01 < float(target):
            flags.append("REST")
        if same_section:
            if delta == 0:
                flags.append("SAME")
            if abs(delta) >= 7:
                flags.append("LEAP" if delta > 0 else "DROP")
            if abs(reg) >= 6:
                flags.append("REG")
        elif (a.get("section") or b.get("section")):
            flags.append("SECTION")
        if (a.get("overlap") or 0) > 0 or (b.get("overlap") or 0) > 0:
            flags.append("OVL")
        out.append({
            "from": a["line"],
            "to": b["line"],
            "bars": f"{a['bars']}->{b['bars']}",
            "end_pitch": a["end_pitch"],
            "start_pitch": b["start_pitch"],
            "delta": delta,
            "rest_s": rest,
            "target_s": target,
            "register_delta": round(reg, 2),
            "overlap": round(float(a.get("overlap") or 0) + float(b.get("overlap") or 0), 2),
            "flags": flags,
            "severity": len(flags),
        })
    return out


def build(score_path: Path, plan_path: Path, phrases_path: Path | None = None,
          lyrics_path: Path | None = None,
          calibration: dict | None = None) -> dict:
    """Build one scorecard payload. Never raises on a malformed draft."""
    try:
        text = score_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "parse_errors": [],
                "score": str(score_path)}

    lint: list[dict] = []
    try:
        lint = abc_tools.lint_text(text) or []
    except Exception as exc:  # noqa: BLE001 - a diagnostic must not break
        lint = [{"message": f"{type(exc).__name__}: {exc}"}]

    try:
        score = checker.parse(text)
    except Exception as exc:  # noqa: BLE001 - a malformed draft is the point
        return {"error": f"{type(exc).__name__}: {exc}",
                "parse_errors": lint or [{"message": str(exc)}],
                "score": str(score_path), "bars": None, "vocal_notes": None,
                "syllables": None, "bands": [], "blocking": [],
                "release_blocking": [], "polish": [],
                "seams": [], "summary": {}}

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"plan: {type(exc).__name__}: {exc}",
                "parse_errors": lint, "score": str(score_path),
                "bands": [], "blocking": [], "release_blocking": [],
                "polish": [], "seams": [], "summary": {}}

    phrases = None
    if phrases_path is not None and Path(phrases_path).exists():
        try:
            phrases = json.loads(Path(phrases_path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            phrases = None
            lint = lint + [{"message": f"phrases: {type(exc).__name__}: {exc}"}]

    lyrics_text = None
    if lyrics_path is not None and Path(lyrics_path).exists():
        lyrics_text = Path(lyrics_path).read_text(encoding="utf-8")

    checks, measured = checker.check(
        score, plan, phrase_plan=phrases, calibration=calibration,
        lyrics_text=lyrics_text, waive_lyrics=lyrics_text is None,
        score_text=text,
    )

    # The release run is stricter (style warnings -> FAIL, final rest is a
    # contract). Run the same pass here so the card and `release` agree.
    strict_checks, _ = checker.check(
        score, plan, phrase_plan=phrases, calibration=calibration,
        lyrics_text=lyrics_text, waive_lyrics=lyrics_text is None,
        score_text=text, strict_style=True, require_final_rest=True,
    )
    hard_keys = {(name, detail) for tag, name, _ok, detail, _cls in checks
                 if tag == "FAIL"}

    by_name = _check_map(checks)
    blocking = [
        {"tag": tag, "name": name, "detail": detail, "class": cls,
         "hint": _hint(name, cls)}
        for tag, name, _ok, detail, cls in checks if tag == "FAIL"
    ]
    release_blocking = [
        {"tag": "FAIL", "name": name, "detail": detail, "class": cls,
         "hint": HINTS.get(name, "fails at release; fix it in the next whole rewrite")}
        for tag, name, _ok, detail, cls in strict_checks
        if tag == "FAIL" and (name, detail) not in hard_keys
    ]
    polish = [
        {"tag": tag, "name": name, "detail": detail, "class": cls,
         "hint": _hint(name, cls)}
        for tag, name, _ok, detail, cls in strict_checks if tag == "WARN"
    ]
    blocking.sort(key=lambda x: (CLASS_ORDER.get(x["class"], 9), x["name"]))
    release_blocking.sort(key=lambda x: (CLASS_ORDER.get(x["class"], 9), x["name"]))
    polish.sort(key=lambda x: (CLASS_ORDER.get(x["class"], 9), x["name"]))

    bands: list[dict] = []
    for label, primary, secondary in BAND_ROWS:
        names = [n for n in (primary, secondary) if n and n in by_name]
        if not names:
            if label == "repeated notes" and measured.get("repeated_share") is not None:
                share = float(measured["repeated_share"])
                bands.append({
                    "metric": label,
                    "detail": f"{share:.0%} of intervals repeat a pitch "
                              "(sample too small for the hard check)",
                    "verdict": "INFO",
                    "class": "sanity",
                })
            continue
        worst = min(names, key=lambda n: TAG_RANK.get(by_name[n][0], 9))
        tag, detail, cls = by_name[worst]
        bands.append({"metric": label, "detail": detail,
                      "verdict": tag, "class": cls})

    rows = _line_rows(score, phrases or {})
    seams = _seams(rows)
    flagged = [s for s in seams if s["flags"]]

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0}
    for tag, *_ in checks:
        counts[tag] = counts.get(tag, 0) + 1
    syllables = plan.get("syllables")
    return {
        "score": str(score_path),
        "plan": str(plan_path),
        "phrases": str(phrases_path) if phrases_path else None,
        "error": None,
        "parse_errors": lint,
        "summary": {
            "bars": score.n_bars,
            "vocal_notes": len(score.notes_of("Vocal")),
            "ins_notes": len(score.notes_of("Ins")),
            "syllables": syllables,
            "notes_per_syllable": measured.get("notes_per_syllable"),
            "pass": counts.get("PASS", 0),
            "warn": len(polish),
            "fail": counts.get("FAIL", 0),
            "release_fail": len(release_blocking),
            "checks": len(checks),
            "seams": len(seams),
            "flagged_seams": len(flagged),
        },
        "measured": {
            "register_mean": measured.get("register_mean"),
            "repeated_share": measured.get("repeated_share"),
            "distinct_durations": measured.get("distinct_durations"),
            "top_duration_share": measured.get("top_duration_share"),
            "simultaneities": measured.get("simultaneities"),
            "ties": measured.get("ties"),
            "final_rest": measured.get("final_rest"),
            "unbroken_seconds_max": measured.get("unbroken_seconds_max"),
        },
        "bands": bands,
        "blocking": blocking,
        "release_blocking": release_blocking,
        "polish": polish,
        "seams": seams,
        "flagged_seams": flagged,
    }


def _fmt_seam(seam: dict) -> str:
    end = live_meter.pitch_name(int(seam["end_pitch"]))
    start = live_meter.pitch_name(int(seam["start_pitch"]))
    rest = seam.get("rest_s")
    target = seam.get("target_s")
    rest_txt = (f"{rest:.2f}/{float(target):.2f}" if rest is not None and target is not None
                else ("-" if rest is None else f"{rest:.2f}"))
    flags = " ".join(seam.get("flags") or []) or "ok"
    return (f"  {seam['from']:>2}->{seam['to']:<2} {seam['bars']:<14} "
            f"{end}->{start} ({seam['delta']:+d})  rest {rest_txt}  "
            f"reg {seam['register_delta']:+.1f}  ovl {seam['overlap']:.0f}  {flags}")


def format_card(payload: dict, *, max_issues: int = 10,
                all_seams: bool = False) -> str:
    if payload.get("error"):
        out = [f"SCORE PARSE ERROR  {payload.get('score', '')}",
               f"  {payload['error']}"]
        errors = payload.get("parse_errors") or []
        for i, err in enumerate(errors[:max_issues], 1):
            detail = err.get("message", err)
            out.append(f"  {i}. {detail}")
        if len(errors) > max_issues:
            out.append(f"  ... {len(errors) - max_issues} more")
        out.append("NEXT  Fix the syntax/bar sums first. No other metric is meaningful.")
        return "\n".join(out)

    s = payload["summary"]
    nps = s.get("notes_per_syllable")
    nps_txt = f" | {nps:.2f} notes/syll" if isinstance(nps, float) else ""
    syll = s.get("syllables")
    syll_txt = f"{syll} syllables" if syll is not None else "syllables -"
    out = [
        f"SCORE  {s['bars']} bars | {s['vocal_notes']} notes | {syll_txt}{nps_txt}",
        f"CHECKS {s['pass']} pass | {s['fail']} blocking | "
        f"{s.get('release_fail', 0)} release-blocking | {s['warn']} polish",
        "FAIL = hard | RELEASE-BLOCKING = fails only in `release` | "
        "WARN = plan/polish | INFO = small sample",
        "",
        "KEY BANDS",
    ]
    for band in payload.get("bands", []):
        out.append(f"  {band['metric']:<16} {band['detail']:<58} {band['verdict']}")

    out.append("")
    if payload.get("blocking"):
        out.append("BLOCKING")
        for i, item in enumerate(payload["blocking"][:max_issues], 1):
            out.append(f"  {i}. [{item['class']}] {item['name']}: {item['detail']}")
            if item.get("hint"):
                out.append(f"     fix: {item['hint']}")
        left = len(payload["blocking"]) - max_issues
        if left > 0:
            out.append(f"  ... {left} more blocking check(s)")
    else:
        out.append("BLOCKING  none")

    out.append("")
    if payload.get("release_blocking"):
        out.append("RELEASE-BLOCKING  (pass the card, fail `release`; fix before release)")
        for i, item in enumerate(payload["release_blocking"][:max_issues], 1):
            out.append(f"  {i}. [{item['class']}] {item['name']}: {item['detail']}")
            if item.get("hint"):
                out.append(f"     fix: {item['hint']}")
        left = len(payload["release_blocking"]) - max_issues
        if left > 0:
            out.append(f"  ... {left} more release-blocking check(s)")
    else:
        out.append("RELEASE-BLOCKING  none")

    out.append("")
    if payload.get("polish"):
        out.append("POLISH")
        for i, item in enumerate(payload["polish"][:max_issues], 1):
            out.append(f"  {i}. [{item['class']}] {item['name']}: {item['detail']}")
    else:
        out.append("POLISH  none")

    seams = payload.get("seams") or []
    flagged = payload.get("flagged_seams") or []
    if seams:
        out.append("")
        out.append(f"SEAMS  (flagged {len(flagged)} of {len(seams)})")
        show = seams if all_seams else (flagged or seams)[:8]
        for seam in show:
            out.append(_fmt_seam(seam))
        if not flagged:
            out.append("  no flagged seams")

    out.append("")
    if payload.get("blocking"):
        n = min(len(payload["blocking"]), max_issues)
        out.append(f"NEXT  Rewrite the whole score once, fixing BLOCKING 1-{n}. "
                   "Do not patch bar by bar.")
    elif payload.get("release_blocking"):
        n = min(len(payload["release_blocking"]), max_issues)
        out.append(f"NEXT  No hard failures, but release would fail: fix "
                   f"RELEASE-BLOCKING 1-{n} in one whole rewrite, then rescore.")
    else:
        out.append("NEXT  No blocking. Polish the flagged seams, then release.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--plan", type=Path, default=Path("plan.json"))
    ap.add_argument("--phrases", type=Path, default=Path("phrases.json"))
    ap.add_argument("--lyrics", type=Path, default=None,
                    help="default: input/lyrics.txt when it exists")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--max-issues", type=int, default=10)
    ap.add_argument("--all-seams", action="store_true")
    args = ap.parse_args(argv)

    lyrics = args.lyrics
    if lyrics is None and Path("input/lyrics.txt").exists():
        lyrics = Path("input/lyrics.txt")

    payload = build(args.score, args.plan, args.phrases, lyrics)
    print(format_card(payload, max_issues=args.max_issues,
                      all_seams=args.all_seams))
    if args.json:
        args.json.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"\nwrote {args.json}")
    if payload.get("error"):
        return 2
    return 1 if payload.get("blocking") or payload.get("release_blocking") else 0


if __name__ == "__main__":
    raise SystemExit(main())
