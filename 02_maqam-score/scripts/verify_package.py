#!/usr/bin/env python3
"""Verify a session package: score <-> seed, Drums, core, docs, plan.

`checker.py` verifies the score's contract and style. This script verifies the
files around it, because the score is not the whole delivery:

- seed.abc has the same Vocal/Ins bars as score.abc (chords stripped);
- seed.abc has a V: Drums voice, one bar per score bar, silent on the last line;
- core_draft.abc, when supplied, is the first 8-16 bars of score.abc
  (optional; the 1.0 workflow has no core);
- seed_sheet.md and notes.md are exactly 10 numbered lines;
- plan.json is complete, strict_shape is false, the register default is 70;
- report.json says ok and its bar count matches.

It is structural, not a gate on taste. It writes verify.json and exits 1 only
on a structural FAIL.

Usage:
    python3 verify_package.py --score score.abc --seed seed.abc --plan plan.json \
        --core core_draft.abc --sheet seed_sheet.md --notes notes.md \
        --report report.json --json verify.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

Z_RE = re.compile(r"^Z(\d*)$")
CHORD_RE = re.compile(r'"[^"]*"')
VOICE_RE = re.compile(r"^V:\s*(\S+)")
NOTE_RE = re.compile(r"([_^=]?[A-Ga-g][,']*)(\d*)(?:-(\d*))?|z(\d*)")


def _header(lines: list[str]) -> tuple[tuple[int, int], int]:
    meter = (4, 4)
    unit_den = 16
    for line in lines:
        s = line.strip()
        m = re.fullmatch(r"M:(\d+)/(\d+)", s)
        if m:
            meter = (int(m.group(1)), int(m.group(2)))
        m = re.fullmatch(r"L:1/(\d+)", s)
        if m:
            unit_den = int(m.group(1))
    return meter, unit_den


def parse_abc(path: Path) -> dict:
    """Parse the two-voice score and the three-voice seed with one state machine.

    Chords are stripped before comparison. `Z<n>` is expanded to n bars. The
    parser is deliberately small: it does not validate the contract (checker.py
    does that); it only needs voices, bars and bar sums.
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    meter, unit_den = _header(lines)
    voices: dict[str, list[str]] = {}
    current: str | None = None
    seen_k = False
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("V:"):
            m = VOICE_RE.match(s)
            if not m:
                continue
            current = m.group(1)
            voices.setdefault(current, [])
            continue
        if s.startswith("K:"):
            seen_k = True
            continue
        if not seen_k or current is None or s.startswith("%"):
            continue
        for tok in s.split("|"):
            tok = CHORD_RE.sub("", tok).strip()
            if not tok:
                continue
            m = Z_RE.fullmatch(tok)
            if m:
                n = int(m.group(1) or 1)
                voices[current].extend(["Z"] * n)
            else:
                voices[current].append(tok)
    if not seen_k:
        raise ValueError(f"{path}: missing K:")
    if not voices:
        raise ValueError(f"{path}: no V: voice")
    return {
        "path": str(path),
        "meter": meter,
        "unit_den": unit_den,
        "voices": voices,
    }


def units_per_bar(parsed: dict) -> int:
    num, den = parsed["meter"]
    return num * parsed["unit_den"] // den


def bar_units(bar: str) -> int | None:
    """Return the written L-units of a bar, or None for a whole-bar rest."""
    if bar == "Z":
        return None
    total = 0
    for m in NOTE_RE.finditer(bar):
        if m.group(1):
            total += int(m.group(2) or 1)
        else:
            total += int(m.group(4) or 1)
    return total


def first_diff(a: list[str], b: list[str]) -> tuple[int, str, str] | None:
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return i, x, y
    if len(a) != len(b):
        i = min(len(a), len(b)) + 1
        return i, a[i - 1] if i <= len(a) else "<missing>", b[i - 1] if i <= len(b) else "<missing>"
    return None


def numbered_lines(path: Path) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    raw = text.splitlines()
    lines = [l for l in raw if l.strip()]
    if len(lines) != 10:
        raise ValueError(f"{path}: {len(lines)} non-empty lines, expected 10")
    if len(lines) != len(raw):
        raise ValueError(f"{path}: blank line present")
    for i, line in enumerate(lines, 1):
        if not re.match(rf"^{i}\.\s", line):
            raise ValueError(f"{path}: line {i} does not start with '{i}. '")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--score", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--seed", type=Path)
    ap.add_argument("--core", type=Path)
    ap.add_argument("--sheet", type=Path)
    ap.add_argument("--notes", type=Path)
    ap.add_argument("--review", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--state", type=Path)
    ap.add_argument("--require-core-first", action="store_true",
                    help="FAIL if core_draft.abc was written after score.abc")
    ap.add_argument("--json", type=Path, default=Path("verify.json"))
    args = ap.parse_args(argv)

    checks: list[dict] = []

    def add(tag: str, name: str, detail: str) -> None:
        checks.append({"tag": tag, "name": name, "detail": detail})

    try:
        score = parse_abc(args.score)
    except Exception as exc:  # noqa: BLE001
        add("FAIL", "parse score", f"{type(exc).__name__}: {exc}")
        score = None
    try:
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        add("FAIL", "parse plan", f"{type(exc).__name__}: {exc}")
        plan = None

    if score is None or plan is None:
        payload = {"ok": False, "checks": checks}
        Path(args.json).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
        print("FAIL verify_package: cannot parse score/plan")
        return 1

    n_bars = len(score["voices"].get("Vocal", []))
    plan_bars = plan.get("bars")
    if plan_bars == n_bars:
        add("PASS", "bar count", f"{n_bars} bars")
    else:
        add("FAIL", "bar count", f"score {n_bars} vs plan {plan_bars}")

    expected = units_per_bar(score)
    bad = []
    for voice, bars in score["voices"].items():
        for i, bar in enumerate(bars, 1):
            u = bar_units(bar)
            if u is not None and u != expected:
                bad.append(f"{voice} b{i}: {u} != {expected}")
    if bad:
        add("FAIL", "bar sums", "; ".join(bad[:5]))
    else:
        add("PASS", "bar sums", f"every written bar = {expected}")

    if plan.get("strict_shape") is False:
        add("PASS", "strict_shape", "false")
    else:
        add("FAIL", "strict_shape", f"{plan.get('strict_shape')!r} (expected false)")

    reg = plan.get("register") or {}
    mean = reg.get("mean")
    if mean == 70:
        add("PASS", "register default", "70")
    elif mean == 74:
        add("WARN", "register default", "74 is the old default; 70 is the 0.6.0 plan")
    else:
        add("WARN", "register default", f"{mean!r} (expected 70)")

    summary = {"score_bars": n_bars, "plan_bars": plan_bars}

    if args.seed:
        try:
            seed = parse_abc(args.seed)
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "parse seed", f"{type(exc).__name__}: {exc}")
            seed = None
        if seed is not None:
            seed_bars = len(seed["voices"].get("Vocal", []))
            if seed_bars == n_bars:
                add("PASS", "seed bars", f"{seed_bars}")
            else:
                add("FAIL", "seed bars", f"{seed_bars} vs score {n_bars}")
            for voice in ("Vocal", "Ins"):
                d = first_diff(score["voices"].get(voice, []), seed["voices"].get(voice, []))
                if d is None:
                    add("PASS", f"seed {voice}", "same bars as score")
                else:
                    add("FAIL", f"seed {voice}", f"bar {d[0]}: score {d[1]!r} vs seed {d[2]!r}")
            drums = seed["voices"].get("Drums")
            if not drums:
                add("FAIL", "seed Drums", "no V: Drums voice")
            else:
                if len(drums) == n_bars:
                    add("PASS", "seed Drums", f"{len(drums)} bars")
                else:
                    add("FAIL", "seed Drums", f"{len(drums)} bars vs score {n_bars}")
                tail_start = max(1, n_bars - 5)
                silent_tail = [i + 1 for i, b in enumerate(drums)
                               if b == "Z" and i + 1 >= tail_start]
                if silent_tail == list(range(tail_start, n_bars + 1)):
                    add("PASS", "drums out", f"silent {tail_start}-{n_bars}")
                else:
                    add("FAIL", "drums out", f"silent tail {silent_tail}")
                active = sum(1 for b in drums if b != "Z")
                under = sum(1 for i, b in enumerate(drums)
                            if b != "Z" and i < n_bars
                            and score["voices"].get("Vocal", ["Z"] * n_bars)[i] != "Z")
                summary.update({"drums_active": active, "drums_under_vocal": under})
                add("PASS", "drums activity", f"{active} active bars; {under} under the voice")

    if args.core:
        try:
            core = parse_abc(args.core)
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "parse core", f"{type(exc).__name__}: {exc}")
            core = None
        if core is not None:
            n = len(core["voices"].get("Vocal", []))
            summary["core_bars"] = n
            if 8 <= n <= 16:
                add("PASS", "core length", f"{n} bars")
            else:
                add("FAIL", "core length", f"{n} (expected 8-16)")
            for voice in ("Vocal", "Ins"):
                if core["voices"].get(voice, [])[:n] == score["voices"].get(voice, [])[:n]:
                    add("PASS", f"core {voice}", f"first {n} bars of score")
                else:
                    add("FAIL", f"core {voice}", "not a prefix of score")
            if args.require_core_first:
                try:
                    if Path(args.core).stat().st_mtime > Path(args.score).stat().st_mtime + 1:
                        add("FAIL", "core order", "core_draft.abc was written after score.abc")
                    else:
                        add("PASS", "core order", "core predates score")
                except OSError as exc:
                    add("FAIL", "core order", str(exc))

    if args.sheet:
        try:
            numbered_lines(args.sheet)
            add("PASS", "seed_sheet.md", "10 numbered lines")
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "seed_sheet.md", str(exc))
    if args.notes:
        try:
            numbered_lines(args.notes)
            add("PASS", "notes.md", "10 numbered lines")
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "notes.md", str(exc))
    if args.review:
        try:
            raw = [l for l in Path(args.review).read_text(encoding="utf-8").splitlines() if l.strip()]
            if len(raw) != 5:
                raise ValueError(f"{args.review}: {len(raw)} non-empty lines, expected 5")
            for i, line in enumerate(raw, 1):
                if not re.match(rf"^{i}\.\s", line):
                    raise ValueError(f"{args.review}: line {i} does not start with '{i}. '")
            add("PASS", "core_review.md", "5 numbered lines")
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "core_review.md", str(exc))

    if args.report:
        try:
            report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "report.json", f"{type(exc).__name__}: {exc}")
        else:
            measured = report.get("measured") or {}
            if report.get("ok") and measured.get("bars") == n_bars:
                add("PASS", "report.json", f"ok; measured bars {measured.get('bars')}")
            else:
                add("FAIL", "report.json", f"ok={report.get('ok')}; bars={measured.get('bars')}")

            waivers = report.get("waivers")
            if waivers is None:
                waivers = measured.get("waivers") or []
            if waivers:
                summary["waivers"] = waivers
                waiver_text = "; ".join(
                    f"{w.get('flag') or w.get('check')}: {w.get('detail', '')}"
                    for w in waivers
                )
                add("WARN", "waivers", waiver_text)

            has_plan_ver = bool(plan.get("plan_version"))
            for flag_key, waiver_key in (
                ("prosody_checked", "prosody"),
                ("copies_checked", "copies"),
                ("binding_checked", "binding"),
            ):
                val = report.get(flag_key, measured.get(flag_key))
                if val is True:
                    add("PASS", flag_key, "true")
                elif val is False:
                    waived = any(
                        w.get("check") == waiver_key
                        or (waiver_key == "prosody" and (w.get("check") == "lyrics" or w.get("flag") == "--waive-lyrics"))
                        for w in waivers
                    )
                    if waived:
                        add("WARN", flag_key, "false (waived)")
                    else:
                        add("FAIL", flag_key, "false without a waiver")
                elif has_plan_ver:
                    add("FAIL", flag_key, "missing in report.json for plan_version plan")

    if args.state:
        try:
            state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "state.json", f"{type(exc).__name__}: {exc}")
        else:
            required = ("phase", "last_artifact", "last_check", "pass",
                        "report_sha", "next_action", "open_issues", "files")
            missing = [k for k in required if k not in state]
            if missing:
                add("FAIL", "state.json", f"missing keys: {', '.join(missing)}")
            else:
                add("PASS", "state.json", f"phase {state.get('phase')!r}")
                if args.report:
                    digest = hashlib.sha256(Path(args.report).read_bytes()).hexdigest()
                    if state.get("report_sha") and state["report_sha"] != digest:
                        add("FAIL", "state check", "report_sha does not match report.json")
                    else:
                        add("PASS", "state check", "report hash matches (or is unset)")
                if state.get("pass") is not True:
                    add("FAIL", "state pass", f"pass={state.get('pass')!r}; update state after a PASS")
                else:
                    add("PASS", "state pass", "true")

    fails = sum(1 for c in checks if c["tag"] == "FAIL")
    warns = sum(1 for c in checks if c["tag"] == "WARN")
    payload = {"ok": fails == 0, "checks": checks, "summary": summary}
    Path(args.json).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    for c in checks:
        print(f"{c['tag']:4s} {c['name']:18s} {c['detail']}")
    print(f"\n{'PASS' if fails == 0 else 'FAIL'}  {fails} fail, {warns} warn; wrote {args.json}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
