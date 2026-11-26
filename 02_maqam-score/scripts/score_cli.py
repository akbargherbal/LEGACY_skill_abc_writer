#!/usr/bin/env python3
"""ABC score workflow: scaffold, whole drafts, scorecard, release.

This is the single entry point the composer uses. It owns the file; the model
owns the notes. Nothing here writes music: it writes bars the model supplies,
checks their arithmetic, and reports errors in one pass.

The 1.0 path is ``init`` -> write the whole score -> ``scorecard.py`` ->
rewrite whole -> ``release``. The line-based commands below are **legacy 0.9**:
they exist for emergency repair and auditing old runs, not for composition.

Commands
--------
    init      lyrics + style -> prosody.json, phrases.json, plan.json, score scaffold
    scorecard whole-draft card (separate script: scorecard.py)
    release   strict check + final rest (1.0 close)
    seed      build seed.abc (chords + drums) from the frozen score
    plan      plan init/lint/set/refresh/show
    status    bars, phase, last check and next action
    explain   plain-language parser diagnosis (abc_doctor.py)
    explain-metric  definition and pitfalls for one measured number
    align     positional syllable -> note projection (report only)
    view      ASCII piano roll or per-line contour (report only)

Legacy 0.9 commands (emergency repair only):
    core      snapshot/check the 8-16 bar core before expansion
    line N    write one lyric line's bars (Vocal + Ins), auto-pad the bar tail
    patch B   replace one bar in both voices
    lint      report every parse/sum error in one pass
    check     checker.py; --bars for a section report; --release for strict

The dialect is the bundled runtime parser's, not a general ABC parser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import abc_tools  # noqa: E402
import checker as checker_mod  # noqa: E402
import live_meter  # noqa: E402
import phrase_table  # noqa: E402
import projection  # noqa: E402
import view_score  # noqa: E402
import _craft_calibrate as craft_cal  # noqa: E402

HEADER = [
    "X:1",
    "T:",
    "M:4/4",
    "L:1/16",
    "Q:1/4=80",
    'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"',
    'V: Ins clef=treble name="Ins Melody" snm="Inst."',
    "K:Dm",
]

REST_SIZES = (12, 8, 6, 4, 3, 2, 1)

# A compact composition convention, not a corpus measurement. The tonic is the
# key's tonic; K: must stay a standard major/minor key (see reference.md 5.1).
MAQAM_TABLE = {
    "kurd": {
        "name": "kurd", "tonic": "D", "key": "Dm",
        "degrees": ["D", "Eb", "F", "G", "A", "Bb", "C"],
        "resting": ["D", "F", "A", "C"],
    },
    "nahawand": {
        "name": "nahawand", "tonic": "D", "key": "Dm",
        "degrees": ["D", "E", "F", "G", "A", "Bb", "C"],
        "resting": ["D", "F", "A", "C"],
    },
    "hijaz": {
        "name": "hijaz", "tonic": "D", "key": "Dm",
        "degrees": ["D", "Eb", "F#", "G", "A", "Bb", "C"],
        "resting": ["D", "F#", "A", "Bb"],
    },
    "ajam": {
        "name": "ajam", "tonic": "D", "key": "D",
        "degrees": ["D", "E", "F#", "G", "A", "B", "C#"],
        "resting": ["D", "F#", "A", "B"],
    },
}


def die(msg: str) -> "NoReturn":
    print(f"ERROR {msg}", file=sys.stderr)
    raise SystemExit(2)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"{path}: {exc}")


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def load_plan(path: Path) -> dict:
    plan = read_json(path)
    if not isinstance(plan, dict):
        die(f"{path}: missing plan.json (run: score_cli.py init)")
    return plan


def load_phrases(path: Path) -> dict:
    phrases = read_json(path)
    if not isinstance(phrases, dict) or not isinstance(phrases.get("lines"), list):
        die(f"{path}: missing phrases.json (run: score_cli.py init)")
    return phrases


def load_state(path: Path) -> dict:
    state = read_json(path, {}) or {}
    state.setdefault("written_lines", [])
    state.setdefault("written_bars", [])
    state.setdefault("core_bars", 0)
    state.setdefault("core_reviewed", False)
    state.setdefault("phase", "init")
    return state


def update_skill_state(path: Path, **fields) -> None:
    """Keep the skill's state.json in step with the CLI's score_state.json."""
    template = read_json(SKILL_DIR / "templates" / "state.json", {}) or {}
    current = read_json(path, None) or dict(template)
    current.update(fields)
    write_json(path, current)


def write_state_md(path: Path, phase: str, next_action: str) -> None:
    text = (
        "# STATE\n\n## Phase\n- " + phase + "\n\n## Done\n- see state.json\n\n"
        "## Verified\n- see state.json / report.json\n\n"
        "## Decisions\n- see notes.md and plan.json deviations\n\n"
        "## Next\n- " + next_action + "\n"
    )
    path.write_text(text, encoding="utf-8")


def units_per_bar(plan: dict) -> int:
    meter = str(plan.get("meter", "4/4"))
    unit = str(plan.get("unit", "1/16"))
    n, d = (int(x) for x in meter.split("/"))
    den = int(unit.split("/")[1])
    return n * den // d


def bar_lengths(plan: dict) -> tuple[int, int]:
    n, d = (int(x) for x in str(plan.get("meter", "4/4")).split("/"))
    den = int(str(plan.get("unit", "1/16")).split("/")[1])
    return n, d


def _voice_for(plan: dict) -> abc_tools.Voice:
    n, d = bar_lengths(plan)
    return abc_tools.Voice((n, d), str(plan.get("key", "Dm")))


def _unit(plan: dict) -> Fraction:
    den = int(str(plan.get("unit", "1/16")).split("/")[1])
    return Fraction(1, den)


def token_units(body: str) -> int:
    """Duration units in one bar body, using the runtime parser's token grammar."""
    if body.strip() == "Z":
        return -1
    total = 0
    cursor = 0
    while cursor < len(body):
        if body[cursor].isspace():
            cursor += 1
            continue
        m = abc_tools.TOKEN.match(body, cursor)
        if m is None:
            return -2
        cursor = m.end()
        if m.group("chord") is not None or m.group("key") is not None:
            continue
        total += int(m.group("duration") or "1")
    return total


def normalize_bar(body: str) -> str:
    """Accept ``pitch:dur`` as well as plain ABC (``D4``); return ABC tokens."""
    out = []
    for token in body.split():
        if token.startswith('"') or token.startswith("[K:"):
            out.append(token)
            continue
        tie = "-" if token.endswith("-") else ""
        core = token[:-1] if tie else token
        if ":" in core:
            pitch, dur = core.rsplit(":", 1)
            if not re.fullmatch(r"\d+", dur):
                raise ValueError(f"{token!r}: duration after ':' must be digits")
            if re.search(r"\d$", pitch):
                raise ValueError(f"{token!r}: write D:4 or D4, not D4:4")
            out.append(f"{pitch}{dur}{tie}")
        else:
            out.append(token)
    return " ".join(out)


def pad_bar(body: str, plan: dict) -> str:
    """Fill a bar's tail with rests; never change a note the model wrote."""
    body = normalize_bar(body.strip())
    if not body:
        return "Z"
    if body == "Z":
        return "Z"
    if body.endswith("-"):
        raise ValueError("a tie at the bar end cannot be padded; write the exact bar")
    have = token_units(body)
    need = units_per_bar(plan)
    if have == -2:
        raise ValueError(f"unsupported token in {body!r}")
    if have > need:
        raise ValueError(f"bar has {have} units; the meter holds {need}")
    if have < 0:
        return body
    rest = need - have
    if rest == 0:
        return body
    parts = []
    for size in REST_SIZES:
        while rest >= size:
            parts.append("z" if size == 1 else f"z{size}")
            rest -= size
    return (body + " " + " ".join(parts)).strip()


def validate_line(bars: list[str], plan: dict) -> None:
    voice = _voice_for(plan)
    for i, body in enumerate(bars, 1):
        try:
            abc_tools.parse_bar(body, voice, _unit(plan), f"bar {i}")
        except abc_tools.AbcError as exc:
            raise ValueError(str(exc)) from exc
    if voice.pending is not None:
        raise ValueError("unresolved tie at the end of the line")


def split_spec(spec: str, count: int) -> list[str]:
    parts = [p.strip() for p in spec.split("|")]
    if parts and parts[-1] == "":
        parts.pop()
    if len(parts) != count:
        raise ValueError(f"expected {count} bars separated by '|', got {len(parts)}")
    return parts


def extract_groups(text: str) -> tuple[list[str], list[dict]]:
    lines = text.splitlines()
    if len(lines) < 8:
        raise ValueError("score is shorter than the 8-line header")
    header = lines[:8]
    groups: list[dict] = []
    cursor = 8
    pending_comment = None
    while cursor < len(lines):
        line = lines[cursor]
        if not line.strip():
            raise ValueError(f"blank line at {cursor + 1}; the runtime parser ends the tune")
        if line.startswith("%"):
            pending_comment = line
            cursor += 1
            continue
        group = {"comment": pending_comment, "Vocal": [], "Ins": [],
                 "Vocal_fields": [], "Ins_fields": []}
        pending_comment = None
        for name in ("Vocal", "Ins"):
            if cursor >= len(lines) or lines[cursor] != f"V: {name}":
                raise ValueError(f"expected V: {name} at line {cursor + 1}")
            cursor += 1
            fields = []
            while cursor < len(lines) and lines[cursor].startswith(("M:", "K:")):
                fields.append(lines[cursor])
                cursor += 1
            if cursor >= len(lines):
                raise ValueError(f"missing music line after V: {name}")
            music = lines[cursor]
            if not music.endswith("|"):
                raise ValueError(f"{name} music line must end with a plain |")
            cursor += 1
            bars = []
            for raw in music[:-1].split("|"):
                raw = raw.strip()
                if not raw:
                    raise ValueError(f"{name}: empty measure")
                m = re.fullmatch(r"Z([2-4])?", raw)
                if m:
                    bars.extend(["Z"] * int(m.group(1) or "1"))
                else:
                    bars.append(raw)
            group[name] = bars
            group[f"{name}_fields"] = fields
        if len(group["Vocal"]) != len(group["Ins"]):
            raise ValueError("Vocal and Ins have different bar counts")
        if not 1 <= len(group["Vocal"]) <= 4:
            raise ValueError(f"group has {len(group['Vocal'])} bars; 1-4 allowed")
        groups.append(group)
    return header, groups


def render_groups(header: list[str], groups: list[dict]) -> str:
    out = list(header)
    for group in groups:
        if group.get("comment"):
            out.append(group["comment"])
        for name in ("Vocal", "Ins"):
            out.append(f"V: {name}")
            out.extend(group.get(f"{name}_fields") or [])
            bars = group[name]
            if not bars:
                bars = ["Z"]
            out.append("|".join(bars) + "|")
    return "\n".join(out) + "\n"


def bar_map(groups: list[dict]) -> dict[int, tuple[int, int]]:
    out = {}
    bar = 1
    for gi, group in enumerate(groups):
        for local in range(len(group["Vocal"])):
            out[bar] = (gi, local)
            bar += 1
    return out


def set_bars(text: str, updates: dict[int, tuple[str, str]], plan: dict) -> str:
    header, groups = extract_groups(text)
    mapping = bar_map(groups)
    for bar, (vocal, ins) in updates.items():
        if bar not in mapping:
            raise ValueError(f"bar {bar} is outside the score (1-{len(mapping)})")
        gi, local = mapping[bar]
        group = groups[gi]
        group["Vocal"][local] = pad_bar(vocal, plan)
        group["Ins"][local] = pad_bar(ins, plan)
    # Validate every written bar in sequence before touching the file.
    vocal_voice = _voice_for(plan)
    ins_voice = _voice_for(plan)
    for group in groups:
        for body in group["Vocal"]:
            abc_tools.parse_bar(body, vocal_voice, _unit(plan), "Vocal bar")
        for body in group["Ins"]:
            abc_tools.parse_bar(body, ins_voice, _unit(plan), "Ins bar")
    return render_groups(header, groups)


def score_bars(text: str) -> int:
    _, groups = extract_groups(text)
    return sum(len(g["Vocal"]) for g in groups)


def _section_weights(phrases: dict) -> list[tuple[str, int]]:
    out: list[list] = []
    for line in phrases.get("lines", []):
        name = str(line.get("section", "verse"))
        syl = int(line.get("syllables", 0) or 0)
        if out and out[-1][0] == name:
            out[-1][1] += syl
        else:
            out.append([name, syl])
    return [(str(n), max(1, int(w))) for n, w in out] or [("verse", 1)]


def section_ranges(plan: dict, phrases: dict) -> list[tuple[str, int, int]]:
    """Return (name, first_bar, last_bar) ranges that tile 1..plan.bars."""
    total = int(plan["bars"])
    sections = [str(s) for s in (plan.get("sections") or [])]
    lengths = plan.get("section_bars")
    if sections and isinstance(lengths, list) and len(lengths) == len(sections) and sum(lengths) == total:
        out, start = [], 1
        for name, length in zip(sections, lengths):
            out.append((name, start, start + int(length) - 1))
            start += int(length)
        return out
    # Absolute bars from syllabify --sections.
    lines = phrases.get("lines", [])
    if lines and all("bar_start" in l and "bar_end" in l for l in lines):
        starts = []
        for line in lines:
            name = str(line.get("section", "verse"))
            if not starts or starts[-1][0] != name:
                starts.append([name, int(line["bar_start"])])
        if starts and starts[0][1] >= 1 and starts[-1][1] <= total:
            out = []
            for i, (name, start) in enumerate(starts):
                end = (starts[i + 1][1] - 1) if i + 1 < len(starts) else total
                out.append((name, start, end))
            if out[0][1] > 1:
                out.insert(0, ("intro", 1, out[0][1] - 1))
            if out[-1][2] < total:
                out.append(("outro", out[-1][2] + 1, total))
            return out
    # No absolute bars: allocate the total by syllable weight.
    weights = _section_weights(phrases)
    if sections and len(sections) == len(weights):
        weights = [(sections[i], w) for i, (_, w) in enumerate(weights)]
    total_w = sum(w for _, w in weights)
    alloc = [max(1, round(w / total_w * total)) for _, w in weights]
    delta = total - sum(alloc)
    i = 0
    while delta != 0 and alloc:
        idx = i % len(alloc)
        if delta > 0:
            alloc[idx] += 1
            delta -= 1
        elif alloc[idx] > 1:
            alloc[idx] -= 1
            delta += 1
        i += 1
        if i > 10000:
            break
    out, start = [], 1
    for (name, _), length in zip(weights, alloc):
        out.append((name, start, start + length - 1))
        start += length
    return out


INSTRUMENTAL = ("intro", "interlude", "solo", "outro", "close", "break", "instrumental")


def arrangement_from_sections(plan: dict, phrases: dict) -> dict:
    ranges = section_ranges(plan, phrases)
    lyric_ranges = []
    for line in phrases.get("lines", []):
        if "bar_start" in line and "bar_end" in line:
            lyric_ranges.append((int(line["bar_start"]), int(line["bar_end"])))
    section_plan = []
    for name, start, end in ranges:
        # A range with no lyric line is instrumental; a gap before the first
        # sung line is the instrumental intro.
        sung_here = any(s <= end and e >= start for s, e in lyric_ranges)
        instrumental = not sung_here and any(k in name.lower() for k in INSTRUMENTAL)
        row = {
            "bars": str(start) if start == end else f"{start}-{end}",
            "role": name,
            "vocal_notes_per_bar": [0, 0] if instrumental else [0, 3],
            "ins_notes_per_bar": [0, 8],
            "ins_active_share": [0, 1],
        }
        if not instrumental:
            row["answer_rate"] = [0, 1]
        section_plan.append(row)
    return {"section_plan": section_plan, "ins_entries": []}


def default_plan(plan: dict, phrases: dict, prosody: dict, key: str,
                 maqam: dict | None) -> dict:
    bars = int(plan["bars"])
    sections = []
    for line in phrases.get("lines", []):
        name = str(line.get("section", "verse"))
        if not sections or sections[-1] != name:
            sections.append(name)
    if not sections:
        sections = ["verse"]
    syllables = int(prosody.get("syllables") or prosody.get("total_syllables") or 0)
    if not syllables:
        syllables = sum(int(l.get("syllables", 0)) for l in phrases.get("lines", []))
    out = {
        "plan_version": "0.8.1",
        "key": key,
        "tempo": int(plan["tempo"]),
        "meter": str(plan["meter"]),
        "unit": str(plan["unit"]),
        "bars": bars,
        "syllables": syllables,
        "sections": sections,
        "simultaneity_exception": None,
        "cadence": "tonic",
        "melisma_min": 1.10,
        "melisma_max": 1.45,
        "register": {"mean": 70, "top": 82, "max_top": 84, "tolerance": 3},
        "tessitura_share_ge_c5_max": 0.80,
        "chorus_lift_min": 5,
        "max_top_duration_share": 0.65,
        "min_distinct_durations": 5,
        "ties_min": 1,
        "min_fill_notes": 3,
        "ins_active_share_min": 0.20,
        "chords_min": 0,
        "max_unbroken_seconds": 10,
        "min_phrase_endings": 3,
        "strict_shape": False,
        "maqam": maqam,
        "maqam_fit_min": 0.95,
        "copies": [],
        "arrangement": arrangement_from_sections({"bars": bars}, phrases),
        "deviations": [
            {"bars": "1-2", "channel": "density", "before": "guitar under the voice",
             "after": "guitar owns the intro", "placeholder": True,
             "unverifiable": True, "reason": "placeholder: declare the deviation before release"},
            {"bars": "3-8", "channel": "gap rate", "before": "an answer after every line",
             "after": "answers thin out", "placeholder": True,
             "unverifiable": True, "reason": "placeholder: declare the deviation before release"},
            {"bars": "9-16", "channel": "section register", "before": "one register",
             "after": "the chorus lifts the median", "placeholder": True,
             "unverifiable": True, "reason": "placeholder: declare the deviation before release"},
        ],
    }
    return out


def infer_maqam(style_text: str, key_override: str | None) -> tuple[str, dict | None]:
    low = style_text.lower()
    for name, entry in MAQAM_TABLE.items():
        if name in low:
            key = key_override or entry["key"]
            return key, {
                "name": entry["name"], "tonic": entry["tonic"],
                "degrees": entry["degrees"], "resting": entry["resting"],
            }
    return key_override or "Am", None


def build_scaffold(plan: dict, phrases: dict) -> str:
    bars = int(plan["bars"])
    sections = section_ranges(plan, phrases)
    starts = {start: name for name, start, _ in sections}
    section_starts = sorted(starts)
    groups = []
    bar = 1
    while bar <= bars:
        end = min(bars, bar + 3)
        # A section comment can only sit at a group boundary: break the group
        # before the next section start instead of losing the section.
        nxt = next((s for s in section_starts if bar < s <= end), None)
        if nxt is not None:
            end = nxt - 1
        n = end - bar + 1
        groups.append({
            "comment": f"% {starts[bar]}" if bar in starts else None,
            "Vocal": ["Z"] * n, "Ins": ["Z"] * n,
            "Vocal_fields": [], "Ins_fields": [],
        })
        bar = end + 1
    header = list(HEADER)
    header[2] = f"M:{plan['meter']}"
    header[3] = f"L:{plan['unit']}"
    header[4] = f"Q:1/4={int(plan['tempo'])}"
    header[7] = f"K:{plan['key']}"
    return render_groups(header, groups)


def cmd_init(args) -> int:
    lyrics = Path(args.lyrics)
    style = Path(args.style)
    if not lyrics.exists():
        die(f"missing lyrics file {lyrics}")
    if not style.exists():
        die(f"missing style file {style}")
    if Path(args.plan).exists() and not args.force:
        die(f"{args.plan} exists; pass --force to rebuild")
    if Path(args.score).exists() and not args.force:
        die(f"{args.score} exists; pass --force to rebuild")

    cmd = [sys.executable, str(SCRIPT_DIR / "syllabify.py"), str(lyrics),
           "--tempo", str(args.tempo), "--json", args.prosody, "--phrases", args.phrases]
    if args.sections:
        cmd += ["--sections", args.sections]
    if args.duration:
        cmd += ["--duration", str(args.duration)]
    proc = subprocess.run(cmd, cwd=args.workdir, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        die("syllabify failed; fix the lyrics or pass --tempo/--bars")
    sys.stdout.write(proc.stdout)

    prosody = read_json(Path(args.prosody), {}) or {}
    phrases = load_phrases(Path(args.phrases))
    body_bars = int(phrases.get("body_bars") or 0)
    last_end = max((int(l.get("bar_end", 0)) for l in phrases.get("lines", [])), default=0)
    if args.bars:
        bars = int(args.bars)
    elif body_bars:
        bars = body_bars + 6
    else:
        bars = last_end + 6
    bars = max(bars, last_end + 1, 4)

    # Without --sections, syllabify writes body-relative bars. Allocate an
    # absolute form once: two instrumental intro bars, the body, then the tail.
    # This is what makes `line N` usable from a one-line prompt.
    if not args.sections and any("bar_start" not in l for l in phrases.get("lines", [])):
        if not body_bars:
            body_bars = sum(max(1, int(l.get("bars", 1))) for l in phrases.get("lines", []))
        intro = 2 if bars >= body_bars + 3 else 0
        tail = max(1, bars - body_bars - intro)
        for line in phrases.get("lines", []):
            bs = int(line.get("body_bar_start", 1))
            be = int(line.get("body_bar_end", line.get("bars", bs)))
            line["bar_start"] = bs + intro
            line["bar_end"] = be + intro
        last_end = max((int(l.get("bar_end", 0)) for l in phrases.get("lines", [])), default=0)

    style_text = style.read_text(encoding="utf-8")
    key, maqam = infer_maqam(style_text, args.key)
    # The form length is baked into plan.json and phrases.json; warn before the
    # scaffold exists. This is an advisor, not a gate.
    recommended = int(prosody.get("bars") or 0)
    if recommended > 0 and abs(bars - recommended) / recommended > 0.05:
        delta = (bars - recommended) / recommended
        print(f"FORM BUDGET: {bars} bars vs syllabify {recommended} "
              f"({delta:+.0%}, tol ±5%)")
        print(f"  the form is baked into plan.json/phrases.json. Accepting "
              f"{bars} keeps a compact form and expects a bars-budget warning. "
              f"To use {recommended}, rerun with --force --bars {recommended} "
              f"and place the extra bars with --sections; otherwise they all "
              f"land in the outro.")
    plan = default_plan({"bars": bars, "tempo": args.tempo, "meter": args.meter,
                         "unit": args.unit}, phrases, prosody, key, maqam)
    if args.sections:
        starts = []
        for part in args.sections.split(","):
            if "=" not in part:
                continue
            name, start = part.rsplit("=", 1)
            starts.append([name.strip(), int(start)])
        if starts:
            total = int(args.bars) if args.bars else max(
                int(plan["bars"]), max((int(l.get("bar_end", 0)) for l in phrases.get("lines", [])), default=0) + 6,
                starts[-1][1] + 2)
            named = [name for name, _ in starts]
            if starts[0][1] > 1:
                # Bars before the first sung section are the instrumental intro;
                # the score carries an extra section the plan does not list.
                starts.insert(0, ["intro", 1])
            plan["bars"] = total
            plan["sections"] = named
            plan.pop("section_bars", None)
            plan["arrangement"] = arrangement_from_sections(plan, phrases)

    write_json(Path(args.plan), plan)
    write_json(Path(args.phrases), phrases)  # normalized (same lines)
    Path(args.score).write_text(build_scaffold(plan, phrases), encoding="utf-8")

    state = {
        "phase": "init", "bars": plan["bars"], "written_lines": [],
        "written_bars": [], "core_bars": 0, "core_reviewed": False,
        "last_check": None,
        "next_action": "write the whole score.abc (one pass, or at most three "
                        "sections), then run scorecard.py",
    }
    write_json(Path(args.state), state)
    update_skill_state(Path(args.skill_state), phase="start", last_artifact="score.abc",
                       next_action=state["next_action"],
                       files=[args.score, args.plan, args.phrases, args.prosody])
    write_state_md(Path(args.skill_state).with_name("STATE.md"), "start", state["next_action"])
    print(f"\nplan: {args.plan}: {plan['bars']} bars, {plan['syllables']} syllables, "
          f"key {plan['key']}, maqam {plan['maqam']['name'] if plan['maqam'] else 'none'}")
    print(f"score: {args.score}: {plan['bars']} bars of rests (scaffold)")
    print(f"lines: {len(phrases.get('lines', []))}; next: write the whole score.abc, then scorecard.py")
    return 0


def cmd_core(args) -> int:
    score = Path(args.score)
    plan = load_plan(Path(args.plan))
    state = load_state(Path(args.state))
    total = int(plan.get("bars", 0))
    bars = min(int(args.bars or 16), total)
    text = score.read_text(encoding="utf-8")
    header, groups = extract_groups(text)
    flat = [(g, i, name) for g in groups for name in ("Vocal", "Ins") for i in range(len(g[name]))]
    if args.snapshot:
        keep = []
        count = 0
        for group in groups:
            n = min(len(group["Vocal"]), max(0, bars - count))
            if n <= 0:
                break
            keep.append({"comment": group.get("comment"), "Vocal": group["Vocal"][:n],
                         "Ins": group["Ins"][:n], "Vocal_fields": group.get("Vocal_fields", []),
                         "Ins_fields": group.get("Ins_fields", [])})
            count += n
        Path(args.core).write_text(render_groups(header, keep), encoding="utf-8")
        state["core_bars"] = count
        state["phase"] = "core"
        state["next_action"] = (
            "legacy: write core_review.md (5 numbered lines), then core --check; "
            "a 1.0 run writes the whole score and runs scorecard.py"
        )
        write_json(Path(args.state), state)
        print(f"wrote {args.core}: {count} bars; now write core_review.md (5 numbered lines)")
        return 0
    if args.check:
        core = Path(args.core)
        if not core.exists():
            die(f"missing {args.core}; run core --snapshot")
        _, core_groups = extract_groups(core.read_text(encoding="utf-8"))
        core_bars = [b for g in core_groups for b in g["Vocal"]]
        score_bars_list = [b for g in groups for b in g["Vocal"]]
        if core_bars != score_bars_list[:len(core_bars)]:
            print("FAIL core is not an exact prefix of score.abc", file=sys.stderr)
            return 1
        review = Path(args.review)
        if not review.exists():
            print(f"FAIL missing {args.review}: write 5 numbered lines", file=sys.stderr)
            return 1
        lines = [l for l in review.read_text(encoding="utf-8").splitlines() if l.strip()]
        numbered = [l for l in lines if re.match(r"^[1-5][.)]\s+", l.strip())]
        if len(numbered) < 5:
            print(f"FAIL {args.review}: expected 5 numbered lines, got {len(numbered)}", file=sys.stderr)
            return 1
        state["core_reviewed"] = True
        state["core_bars"] = len(core_bars)
        state["phase"] = "expand"
        state["next_action"] = (
            "legacy: write the next lyric line (score_cli.py line <n>); "
            "a 1.0 run rewrites the whole score, then scorecard.py"
        )
        write_json(Path(args.state), state)
        update_skill_state(Path(args.skill_state), phase="expand",
                           last_artifact="core_review.md",
                           next_action=state["next_action"])
        print(f"PASS core: {len(core_bars)} bars, review has 5 lines; expansion unlocked")
        return 0
    die("core: pass --snapshot or --check")


def _line_by_number(phrases: dict, number: int) -> dict:
    for line in phrases.get("lines", []):
        if int(line.get("line", -1)) == number:
            return line
    die(f"line {number} not in phrases.json (lines 1-{len(phrases.get('lines', []))})")


def _measure(text: str, plan: dict, phrases: dict, state: dict, *,
             line_no: int | None = None, bars: list[int] | None = None) -> dict:
    lyrics = Path("input/lyrics.txt")
    return live_meter.measure(text, plan, phrases, state=state, line_no=line_no,
                              bars=bars, lyrics_path=lyrics if lyrics.exists() else None)


def _print_write_meter(payload: dict, *, guard: bool) -> bool:
    """Print the meter. Return False when --guard refuses the write."""
    try:
        print(live_meter.format_meter(payload))
        if not guard:
            return True
        problems = live_meter.guard_violations(payload)
    except Exception as exc:  # noqa: BLE001 - never break a write on a diagnostic
        print(f"meter unavailable: {type(exc).__name__}: {exc}")
        return True
    if not problems:
        return True
    for problem in problems:
        print(f"REFUSED (--guard): {problem}", file=sys.stderr)
    return False


def cmd_line(args) -> int:
    score = Path(args.score)
    plan = load_plan(Path(args.plan))
    phrases = load_phrases(Path(args.phrases))
    state = load_state(Path(args.state))
    line = _line_by_number(phrases, args.line)
    start = int(line["bar_start"])
    end = int(line["bar_end"])
    count = end - start + 1
    core_bars = int(state.get("core_bars") or 0)
    core_limit = core_bars or 16
    if not state.get("core_reviewed") and start > core_limit:
        die("legacy core not reviewed; write the first 16 bars, then core --snapshot, "
            "write core_review.md, and run core --check. A 1.0 run does not use core: "
            "write the whole score and run scorecard.py")
    try:
        vocal = split_spec(args.vocal, count) if args.vocal is not None else ["Z"] * count
        ins = split_spec(args.ins, count) if args.ins is not None else ["Z"] * count
        text = score.read_text(encoding="utf-8")
        updates = {}
        for i in range(count):
            updates[start + i] = (vocal[i], ins[i])
        new_text = set_bars(text, updates, plan)
        # Whole-file lint: one bad bar cannot hide behind a good one.
        errors = abc_tools.lint_text(new_text) if hasattr(abc_tools, "lint_text") else []
        if errors:
            for e in errors:
                print(f"FAIL {e.get('voice', '?')} bar {e.get('bar', '?')}: {e.get('message', e)}",
                      file=sys.stderr)
            return 1
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"line {args.line}: bars {start}-{end} ({count} bars), {line.get('syllables', '?')} syllables")
    for i in range(count):
        print(f"  {start + i:>3} V: {pad_bar(vocal[i], plan)}")
        print(f"      I: {pad_bar(ins[i], plan)}")
    written = sorted(set(state["written_bars"]) | set(range(start, end + 1)))
    next_line = args.line + 1 if args.line < len(phrases["lines"]) else "check"
    proposed = dict(state)
    proposed["written_bars"] = written
    proposed["written_lines"] = sorted(set(state["written_lines"]) | {args.line})
    payload = _measure(new_text, plan, phrases, proposed, line_no=args.line)
    if not _print_write_meter(payload, guard=args.guard):
        return 1
    if args.dry_run:
        print("dry run: score.abc and score_state.json unchanged")
        return 0
    score.write_text(new_text, encoding="utf-8")
    state["written_bars"] = written
    state["written_lines"] = proposed["written_lines"]
    state["phase"] = "expand"
    state["next_action"] = (
        f"legacy: write line {next_line}; a 1.0 run rewrites the whole score, then scorecard.py"
        if next_line != "check"
        else "legacy: check the next bars; a 1.0 run runs scorecard.py"
    )
    write_json(Path(args.state), state)
    update_skill_state(Path(args.skill_state), phase="expand",
                       last_artifact=f"score.abc (line {args.line})",
                       next_action=state["next_action"])
    print(f"written lines: {len(state['written_lines'])}/{len(phrases['lines'])}; next: {state['next_action']}")
    return 0


def cmd_patch(args) -> int:
    score = Path(args.score)
    plan = load_plan(Path(args.plan))
    phrases = load_phrases(Path(args.phrases))
    state = load_state(Path(args.state))
    try:
        text = score.read_text(encoding="utf-8")
        new_text = set_bars(text, {args.bar: (args.vocal, args.ins)}, plan)
        errors = abc_tools.lint_text(new_text) if hasattr(abc_tools, "lint_text") else []
        if errors:
            for e in errors:
                print(f"FAIL {e.get('voice', '?')} bar {e.get('bar', '?')}: {e.get('message', e)}",
                      file=sys.stderr)
            return 1
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"patched bar {args.bar}: V {pad_bar(args.vocal, plan)} | I {pad_bar(args.ins, plan)}")
    payload = _measure(new_text, plan, phrases, state, bars=[args.bar])
    if not _print_write_meter(payload, guard=args.guard):
        return 1
    if args.dry_run:
        print("dry run: score.abc and score_state.json unchanged")
        return 0
    score.write_text(new_text, encoding="utf-8")
    return 0


def cmd_lint(args) -> int:
    path = Path(args.score)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        die(str(exc))
    errors = abc_tools.lint_text(text) if hasattr(abc_tools, "lint_text") else []
    # Structural check: bar counts and 1-4 bar groups.
    try:
        header, groups = extract_groups(text)
        bars = sum(len(g["Vocal"]) for g in groups)
        print(f"structure: {len(groups)} groups, {bars} bars, header {'OK' if header else '?'}")
    except ValueError as exc:
        errors.append({"voice": "?", "bar": "?", "message": str(exc)})
    if errors:
        for e in errors:
            print(f"FAIL {e.get('voice', '?')} bar {e.get('bar', '?')}: {e.get('message', e)}")
        print(f"{len(errors)} error(s)")
        return 1
    # The existing hard sanity guard, surfaced before the full check.
    try:
        parsed = checker_mod.parse(text)
        overlaps = live_meter.overlap_by_bar(parsed)
        cal = checker_mod.load_calibration()
        cap = float((cal.get("sanity", {}).get("simultaneity_le4", {}) or {}).get("max", 4))
        bad = {b: v for b, v in overlaps.items() if v > cap}
        if bad:
            for b in sorted(bad):
                print(f"lint: bar {b} Ins overlaps Vocal {bad[b]:g} units (max {cap:g})")
            print(f"lint: simultaneity {sum(overlaps.values()):g} units in {len(bad)} bar(s) over cap")
            return 1
    except Exception:  # noqa: BLE001 - overlap is diagnostic; parse/sum already passed
        pass
    print("lint PASS: every bar parses and sums to its meter")
    return 0


def _partial_rows(args, plan: dict, phrases: dict) -> int:
    path = Path(args.score)
    errors = abc_tools.lint_text(path.read_text(encoding="utf-8")) if hasattr(abc_tools, "lint_text") else []
    if errors:
        for e in errors:
            print(f"FAIL {e.get('voice', '?')} bar {e.get('bar', '?')}: {e.get('message', e)}")
        return 1
    lo, hi = (int(x) for x in args.bars.split("-", 1)) if "-" in args.bars else (int(args.bars), int(args.bars))
    try:
        parsed = craft_cal.parse_score(path)
        table = phrase_table.build(parsed, phrases)
    except Exception as exc:  # noqa: BLE001
        die(f"craft table failed: {exc}")
    print(f"section report bars {lo}-{hi}")
    print("  line section      bars    syl  notes rest_after  unbroken  mean  rep  end° pitch")
    for row in table["rows"]:
        b = str(row.get("bars", ""))
        m = re.match(r"(\d+)(?:-(\d+))?", b)
        if not m:
            continue
        s = int(m.group(1)); e = int(m.group(2) or s)
        if e < lo or s > hi:
            continue
        print(f"  {row.get('line', '?'):>4} {str(row.get('section', ''))[:12]:<12} "
              f"{b:<7} {str(row.get('syllables', '-')):>4} {row.get('notes', 0):>5} "
              f"{str(row.get('rest_after_s', '-')):>10} {str(row.get('unbroken_s', '-')):>8} "
              f"{str(row.get('register_mean', '-')):>5} {str(row.get('repeated', '-')):>5} "
              f"{str(row.get('end_name', '-')):>4} {str(row.get('end_pitch_name', '-')):>5}")
    return 0


def _run_repair(score: str, plan: str, phrases: str, report: str) -> None:
    cmd = [sys.executable, str(SCRIPT_DIR / "repair.py"), score,
           "--plan", plan, "--phrases", phrases, "--report", report,
           "--json", "repair.json"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        return
    data = read_json(Path("repair.json"), {}) or {}
    print("\nREPAIR MAP (fix only these bars/phrases)")
    for name, item in (data.get("maps") or {}).items():
        if not isinstance(item, dict):
            continue
        parts = []
        for key in ("bars", "bars_out", "sections_out", "duplicates", "runs", "lines"):
            value = item.get(key)
            if value:
                parts.append(f"{key}={value}")
        if parts:
            print(f"  {name}: " + " ".join(parts))
    if data.get("failures"):
        print("  failures: " + ", ".join(str(x) for x in data["failures"]))
    print("  repair.json holds the full map")


def cmd_check(args) -> int:
    plan_path = Path(args.plan)
    plan = load_plan(plan_path)
    phrases_path = Path(args.phrases)
    phrases = load_phrases(phrases_path)
    if args.bars:
        return _partial_rows(args, plan, phrases)
    report = Path(args.report)
    argv = [args.score, "--plan", str(plan_path), "--phrases", str(phrases_path),
            "--json", str(report)]
    lyrics = Path(args.lyrics)
    if lyrics.exists():
        argv += ["--lyrics", str(lyrics)]
    else:
        argv += ["--waive-lyrics"]
    if args.release:
        argv += ["--release"]
    dry_run = bool(getattr(args, "dry_run", False))
    rc = checker_mod.main(argv)
    if rc == 0:
        data = read_json(report, {}) or {}
        print(f"\nCHECK PASS: {len(data.get('checks', []))} checks; report {report}")
        if dry_run:
            print("dry run: score_state.json and skill state unchanged")
            return 0
        state = load_state(Path(args.state))
        state["phase"] = "done" if args.release else "expand"
        state["last_check"] = {"pass": True, "release": bool(args.release),
                               "report": str(report)}
        state["next_action"] = (
            "seed"
            if args.release
            else "run scorecard.py on the whole score; rewrite whole if blocking"
        )
        write_json(Path(args.state), state)
        update_skill_state(Path(args.skill_state),
                           phase="done" if args.release else "expand",
                           last_artifact=str(report), **{"pass": True},
                           last_check={"pass": True, "release": bool(args.release),
                                       "report": str(report)},
                           report_sha=hashlib.sha256(report.read_bytes()).hexdigest(),
                           next_action=state["next_action"])
        return 0
    if dry_run:
        print("\ndry run: score_state.json and skill state unchanged")
        if report.exists():
            _run_repair(args.score, str(plan_path), str(phrases_path), str(report))
        return rc
    update_skill_state(Path(args.skill_state), **{"pass": False},
                       last_check={"pass": False, "report": str(report)},
                       next_action="rewrite the whole score from the card (no patch); then scorecard.py")
    if not report.exists():
        print("\nCHECK FAILED before measurement; run `lint` or `explain` for the parse error")
        return rc
    print("\nCHECK FAILED; building the bar/phrase repair map")
    _run_repair(args.score, str(plan_path), str(phrases_path), str(report))
    return rc


def cmd_release(args) -> int:
    args.release = True
    return cmd_check(args)


def _chord_for_bar(body: str, key: str) -> str | None:
    if body.strip() == "Z":
        return None
    m = re.search(r"([_=^]?)([A-Ga-g])", body)
    if not m:
        return None
    accidental, letter = m.group(1), m.group(2).upper()
    if accidental in ("_", "^"):
        # a flat or sharp root keeps its accidental: _e -> Eb, ^f -> F#
        return letter + ("b" if accidental == "_" else "#")
    table = {"C": "C", "D": "Dm", "E": "Em", "F": "F", "G": "G", "A": "Am", "B": "Bdim"}
    return table.get(letter, "C")


DRUM_VERSE = ["B,2 D2 C2 D2 B,2 D2 C2 D2",
              "B,2 D2 C2 D2 B,2 D2 z4"]
DRUM_CHORUS = ["E4 B,4 C4 B,4", "B,4 C4 B,4 E4"]
DRUM_FILL = "C2 C2 C2 C2 E4 z4"


def cmd_seed(args) -> int:
    score = Path(args.score)
    plan = load_plan(Path(args.plan))
    text = score.read_text(encoding="utf-8")
    header, groups = extract_groups(text)
    out = ["X:1", "T:", header[2], header[3], header[4],
           'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"',
           'V: Ins clef=treble name="Ins Melody" snm="Inst."',
           'V: Drums clef=perc name="Drums" snm="Drums"',
           "%%MIDI channel 10",
           "%%MIDI drummap B, 36", "%%MIDI drummap C 38",
           "%%MIDI drummap D 42", "%%MIDI drummap E 49",
           header[7]]
    bar_no = 1
    for group in groups:
        section = (group.get("comment") or "").lstrip("% ").strip().lower()
        if section:
            out.append(f"%% {section}")
        for name in ("Vocal", "Ins"):
            out.append(f"V: {name}")
            bars = []
            for body in group[name]:
                if name == "Vocal":
                    chord = _chord_for_bar(body, plan.get("key", "Dm"))
                    bars.append((f'"{chord}"{body}' if chord else body))
                else:
                    bars.append(body)
            out.append("|".join(bars) + "|")
        out.append("V: Drums")
        drums = []
        for i, body in enumerate(group["Vocal"]):
            absolute = bar_no + i
            if "close" in section or absolute >= int(plan["bars"]) - 5:
                drums.append("Z")
            elif "chorus" in section:
                drums.append(DRUM_CHORUS[i % 2])
            elif i == len(group["Vocal"]) - 1 and (bar_no // 4) % 2 == 1:
                drums.append(DRUM_FILL)
            else:
                drums.append(DRUM_VERSE[i % 2])
        out.append("|".join(drums) + "|")
        bar_no += len(group["Vocal"])
    Path(args.seed).write_text("\n".join(out) + "\n", encoding="utf-8")
    update_skill_state(Path(args.skill_state), phase="package", last_artifact=f"seed.abc",
                       next_action="write seed_sheet.md, notes.md, CHANGES.txt; run verify_package")
    print(f"wrote {args.seed}: {bar_no - 1} bars, 3 voices; edit it, then seed --check")
    return 0


def voice_bar_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("V: "):
            current = line[3:].split()[0]
            counts.setdefault(current, 0)
            continue
        if current is None or not line or line.startswith(("%%", "%", "X:", "T:", "M:", "L:", "Q:", "K:")):
            continue
        if not line.endswith("|"):
            raise ValueError(f"{current}: music line must end with |")
        for raw in line[:-1].split("|"):
            raw = raw.strip()
            if not raw:
                continue
            m = re.fullmatch(r"Z([2-4])?", raw)
            counts[current] += int(m.group(1) or "1") if m else 1
    return counts


def cmd_seed_check(args) -> int:
    score = Path(args.score)
    seed = Path(args.seed)
    _, groups = extract_groups(score.read_text(encoding="utf-8"))
    text = seed.read_text(encoding="utf-8")
    if "V: Drums" not in text:
        print("FAIL seed has no V: Drums voice", file=sys.stderr)
        return 1
    try:
        counts = voice_bar_counts(text)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    total = sum(len(g["Vocal"]) for g in groups)
    for name in ("Vocal", "Ins", "Drums"):
        if counts.get(name) != total:
            print(f"FAIL seed {name} has {counts.get(name)} bars; score has {total}",
                  file=sys.stderr)
            return 1
    print(f"PASS seed: {total} bars, V: Drums present, Vocal/Ins/Drums align")
    return 0


def _dotted_get(plan: dict, path: str):
    cur = plan
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _dotted_set(plan: dict, path: str, value) -> None:
    parts = path.split(".")
    cur = plan
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
        if not isinstance(cur, dict):
            die(f"{path}: {part} is not an object")
    try:
        cur[parts[-1]] = json.loads(value)
    except json.JSONDecodeError:
        cur[parts[-1]] = value


def _check_plan_path(plan: dict, path: str) -> None:
    """Refuse a top-level key that plan.json does not have (silent typo/wrong path)."""
    top = path.split(".")[0]
    schema = read_json(SKILL_DIR / "schemas" / "plan.schema.json", {}) or {}
    if top in plan or top in (schema.get("properties") or {}):
        return
    nested = [f"{k}.{top}" for k, v in plan.items() if isinstance(v, dict) and top in v]
    hint = f"; did you mean {nested[0]}?" if nested else ""
    die(f"plan set: unknown plan key {top!r}{hint} (run `plan show` for the keys)")


def cmd_plan(args) -> int:
    plan_path = Path(args.plan)
    plan = load_plan(plan_path)
    phrases = load_phrases(Path(args.phrases))
    if args.action == "show":
        print(json.dumps(plan, indent=1, ensure_ascii=False))
        return 0
    if args.action == "set":
        if "=" not in args.value:
            die("plan set expects path=value, e.g. register.mean=72")
        path, value = args.value.split("=", 1)
        _check_plan_path(plan, path)
        _dotted_set(plan, path, value)
        write_json(plan_path, plan)
        print(f"plan: {path} = {_dotted_get(plan, path)}")
        return 0
    if args.action == "refresh":
        score = Path(args.score)
        text = score.read_text(encoding="utf-8")
        _, groups = extract_groups(text)
        # Ins entries: first active bar after two silent bars.
        ins_active = []
        for group in groups:
            for body in group["Ins"]:
                ins_active.append(body.strip() != "Z")
        entries = []
        for i in range(2, len(ins_active)):
            if ins_active[i] and not any(ins_active[i - k] for k in (1, 2)):
                entries.append(i + 1)
        plan.setdefault("arrangement", {})["ins_entries"] = entries
        plan["arrangement"]["section_plan"] = arrangement_from_sections(plan, phrases)["section_plan"]
        write_json(plan_path, plan)
        print(f"plan refreshed: arrangement.section_plan ({len(plan['arrangement']['section_plan'])} ranges), "
              f"ins_entries {entries}")
        return 0
    if args.action == "lint":
        problems = []
        required = ["key", "tempo", "meter", "unit", "bars", "syllables", "sections",
                    "melisma_min", "melisma_max", "register", "max_top_duration_share",
                    "min_distinct_durations", "ties_min", "min_fill_notes", "chords_min"]
        for key in required:
            if key not in plan:
                problems.append(f"missing {key}")
        devs = plan.get("deviations") or []
        if not 3 <= len(devs) <= 4:
            problems.append(f"deviations: {len(devs)} (need 3-4)")
        if any(d.get("placeholder") for d in devs if isinstance(d, dict)):
            problems.append("deviations contain placeholders; replace them before release")
        rows = ((plan.get("arrangement") or {}).get("section_plan") or [])
        if not rows:
            problems.append("arrangement.section_plan is empty")
        covered = 0
        for row in rows:
            m = re.match(r"(\d+)(?:-(\d+))?", str(row.get("bars", "")))
            if not m:
                problems.append(f"bad bars range {row.get('bars')!r}")
                continue
            s, e = int(m.group(1)), int(m.group(2) or m.group(1))
            if s != covered + 1:
                problems.append(f"section_plan gap at {covered + 1} (next {s})")
            covered = max(covered, e)
        if rows and covered != int(plan.get("bars", 0)):
            problems.append(f"section_plan ends at {covered}, plan.bars {plan.get('bars')}")
        if problems:
            for p in problems:
                print(f"WARN {p}")
            return 1
        print("plan lint PASS: required fields, 3-4 deviations, arrangement tiles 1..bars")
        return 0
    die("plan: use show/set/refresh/lint")


def cmd_status(args) -> int:
    plan = load_plan(Path(args.plan))
    load_phrases(Path(args.phrases))  # validate the scaffold is present
    state = load_state(Path(args.state))
    total = int(plan.get("bars", 0))
    try:
        text = Path(args.score).read_text(encoding="utf-8")
        bars = score_bars(text)
    except (OSError, ValueError) as exc:
        bars = f"? ({exc})"
    last = state.get("last_check")
    print(f"bars {bars}/{total}; phase {state.get('phase')}; "
          f"last check {last or 'none'}")
    print(f"next: {state.get('next_action') or 'none'}")
    return 0


def cmd_explain(args) -> int:
    cmd = [sys.executable, str(SCRIPT_DIR / "abc_doctor.py"), args.score]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def cmd_explain_metric(args) -> int:
    path = SKILL_DIR / "references" / "metrics.md"
    if not path.exists():
        die(f"missing {path}")
    text = path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(body).strip()
            current = line[3:].strip()
            body = []
        elif current:
            body.append(line)
    if current:
        sections[current] = "\n".join(body).strip()
    if args.list or not args.name:
        print("metrics: " + ", ".join(sorted(sections)))
        return 0
    if args.name not in sections:
        die(f"unknown metric {args.name!r}; use --list")
    print(f"## {args.name}\n\n{sections[args.name]}")
    return 0


def cmd_align(args) -> int:
    text = Path(args.score).read_text(encoding="utf-8")
    phrases = load_phrases(Path(args.phrases))
    plan = load_plan(Path(args.plan))
    try:
        payload = projection.project(text, plan, phrases, args.lines)
    except Exception as exc:  # noqa: BLE001
        die(f"align: {exc}")
    print(projection.format_projection(payload))
    return 0


def cmd_view(args) -> int:
    text = Path(args.score).read_text(encoding="utf-8")
    if args.roll == args.contour:
        die("view: pass exactly one of --roll or --contour")
    try:
        if args.roll:
            print(view_score.roll(text, args.bars))
        else:
            phrases = load_phrases(Path(args.phrases))
            print(view_score.contour(text, phrases))
    except ValueError as exc:
        die(f"view: {exc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, score=True):
        if score:
            p.add_argument("--score", default="score.abc")
        p.add_argument("--plan", default="plan.json")
        p.add_argument("--phrases", default="phrases.json")
        p.add_argument("--state", default="score_state.json")
        p.add_argument("--skill-state", default="state.json")

    p = sub.add_parser("init", help="lyrics + style -> prosody, phrases, plan, scaffold")
    p.add_argument("--lyrics", default="input/lyrics.txt")
    p.add_argument("--style", default="input/style.md")
    p.add_argument("--tempo", type=float, default=80)
    p.add_argument("--meter", default="4/4")
    p.add_argument("--unit", default="1/16")
    p.add_argument("--bars", type=int, default=None)
    p.add_argument("--sections", default=None,
                   help='absolute starts, e.g. "intro=7,verse 1=13,chorus=37,outro=77"')
    p.add_argument("--key", default=None)
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--prosody", default="prosody.json")
    p.add_argument("--score", default="score.abc")
    p.add_argument("--plan", default="plan.json")
    p.add_argument("--phrases", default="phrases.json")
    p.add_argument("--state", default="score_state.json")
    p.add_argument("--skill-state", default="state.json")
    p.add_argument("--workdir", default=".")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("core", help="snapshot/check the 8-16 bar core")
    p.add_argument("--bars", type=int, default=16)
    p.add_argument("--snapshot", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--core", default="core_draft.abc")
    p.add_argument("--review", default="core_review.md")
    common(p)
    p.set_defaults(func=cmd_core)

    p = sub.add_parser("line", help="write one lyric line")
    p.add_argument("line", type=int)
    p.add_argument("--vocal", default=None, help="bars separated by |; pitch:dur tokens")
    p.add_argument("--ins", default=None, help="bars separated by |; defaults to rests")
    p.add_argument("--dry-run", action="store_true", help="measure and print; write nothing")
    p.add_argument("--guard", action="store_true",
                   help="refuse the write when a measured target is already broken")
    common(p)
    p.set_defaults(func=cmd_line)

    p = sub.add_parser("patch", help="replace one bar in both voices")
    p.add_argument("bar", type=int)
    p.add_argument("--vocal", required=True)
    p.add_argument("--ins", required=True)
    p.add_argument("--dry-run", action="store_true", help="measure and print; write nothing")
    p.add_argument("--guard", action="store_true",
                   help="refuse the write when a measured target is already broken")
    common(p)
    p.set_defaults(func=cmd_patch)

    p = sub.add_parser("lint", help="report every parse/sum error in one pass")
    common(p)
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("check", help="checker.py; --bars for a section report")
    p.add_argument("--bars", default=None, help="e.g. 9-16; section report only")
    p.add_argument("--report", default="report.json")
    p.add_argument("--lyrics", default="input/lyrics.txt")
    p.add_argument("--release", action="store_true")
    common(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("release", help="strict check + final rest")
    p.add_argument("--report", default="report.json")
    p.add_argument("--lyrics", default="input/lyrics.txt")
    p.add_argument("--bars", default=None)
    p.add_argument("--dry-run", action="store_true",
                   help="run the strict verdicts without changing score_state.json")
    common(p)
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("seed", help="build seed.abc from the frozen score")
    common(p)
    p.add_argument("--seed", default="seed.abc")
    p.set_defaults(func=cmd_seed)
    p = sub.add_parser("seed-check", help="Vocal/Ins/Drums bar alignment")
    common(p)
    p.add_argument("--seed", default="seed.abc")
    p.set_defaults(func=cmd_seed_check)

    p = sub.add_parser("plan", help="plan show/set/refresh/lint")
    p.add_argument("action", choices=["show", "set", "refresh", "lint"])
    p.add_argument("value", nargs="?", default="")
    common(p)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("status", help="bars, lines, core, last check")
    common(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("explain", help="plain-language parser diagnosis")
    p.add_argument("--score", default="score.abc")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("explain-metric", help="definition and pitfalls for one measured number")
    p.add_argument("name", nargs="?", default="")
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_explain_metric)

    p = sub.add_parser("align", help="positional syllable -> note projection (report only)")
    p.add_argument("--lines", default=None, help="e.g. 3-6 or 1,4,7")
    common(p)
    p.set_defaults(func=cmd_align)

    p = sub.add_parser("view", help="ASCII piano roll or per-line contour (report only)")
    p.add_argument("--roll", action="store_true")
    p.add_argument("--contour", action="store_true")
    p.add_argument("--bars", default=None, help="roll range, e.g. 3-5")
    common(p)
    p.set_defaults(func=cmd_view)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
