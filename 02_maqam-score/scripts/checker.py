#!/usr/bin/env python3
"""Check a composed score against its plan, and print the numbers to report.

This is the skill's only verifier. It runs the vendored runtime parser
(`scripts/abc_tools.py`, a copy of `plumbing/yue2_instrumental/abc_tools.py`)
first and fails closed: anything the renderer cannot read is an error here, not
a warning. Then it measures the plan's quality targets.

    python3 checker.py score.abc --plan plan.json
    python3 checker.py score.abc --plan plan.json --json report.json
    python3 checker.py score.abc --plan plan.json --require-final-rest
    python3 checker.py score.abc --plan plan.json --strict-style

Gate classes
------------
contract   the renderer's contract: dialect, header, complete bars, voices,
           plan targets present, key/tempo/meter/bars agreement.
sanity     six broad degeneracy guards calibrated on the 177-track corpus:
           none of them prescribes a style. They pass 175/177 (98.9%).
style      targets and comparisons that describe taste, not validity:
           melisma band, high register, Ins density, tie count, chords,
           cadence, section names, silence, answer mutation, chorus lift.
           WARN by default; FAIL only with --strict-style. A cadence the plan
           explicitly declares as "tonic" is the one self-imposed exception.

The calibration lives in `calibration.json` next to this file. Every hard
threshold has a corpus basis (min/max or a 95% rule), not a single case.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# The runtime parser is vendored next to this file. It is the contract the
# renderer actually reads, so it runs first and fails closed. Do not replace it
# with the lenient metric parser below.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import abc_tools as runtime_abc  # noqa: E402

VOICES = ("Vocal", "Ins")
DURATIONS = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48}
NATURAL = dict(zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)))
KEYS = {
    **dict(zip(("Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#"),
                range(-7, 8))),
    **dict(zip(("Abm", "Ebm", "Bbm", "Fm", "Cm", "Gm", "Dm", "Am", "Em", "Bm", "F#m", "C#m",
                "G#m", "D#m", "A#m"), range(-7, 8))),
}
VOICE_HEADER = {
    "Vocal": 'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"',
    "Ins": 'V: Ins clef=treble name="Ins Melody" snm="Inst."',
}
DEFAULT_CALIBRATION = SCRIPT_DIR / "calibration.json"
TIE_TOKEN = re.compile(
    r'"(?P<chord>[^"\n]*)"|\[K:[^\]\n]+\]|'
    r"(?P<acc>\^\^|__|\^|_|=)?(?P<note>[A-Ga-gz])"
    r"(?P<oct>[,']*)(?P<dur>[0-9]*)(?P<tie>-?)"
)
SECTION_ALIASES = {
    "prechorus": "pre-chorus",
    "pre chorus": "pre-chorus",
    "chorus repeat": "chorus",
    "refrain": "chorus",
}


class AbcError(ValueError):
    pass


# ---------------------------------------------------------------------------
# key helpers (same contract as before)
# ---------------------------------------------------------------------------

def key_map(key: str) -> dict[str, int]:
    if key not in KEYS:
        raise AbcError(f"unsupported key {key!r}: use a standard major or minor K: field")
    count = KEYS[key]
    alter = {letter: 0 for letter in NATURAL}
    for letter in ("FCGDAEB" if count > 0 else "BEADGCF")[:abs(count)]:
        alter[letter] = 1 if count > 0 else -1
    return alter


def tonic_pc(key: str) -> int:
    m = re.match(r"([A-G])([#b]?)", key)
    if not m:
        raise AbcError(f"cannot read the tonic from K:{key}")
    return (NATURAL[m.group(1)] + (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0)) % 12


def key_scale(key: str) -> set[int]:
    alter = key_map(key)
    return {(NATURAL[letter] + alter[letter]) % 12 for letter in NATURAL}


# ---------------------------------------------------------------------------
# metric model
# ---------------------------------------------------------------------------

@dataclass
class Note:
    onset: float          # L-units from the start of the score
    dur: float            # L-units
    pitch: int            # MIDI
    bar: int              # 0-based
    section: str
    key: str


@dataclass
class Score:
    unit_den: int
    tempo: float
    meter: tuple[int, int]          # header meter
    key: str                        # header key
    notes: dict[str, list[Note]] = field(default_factory=dict)
    bar_sections: list[str] = field(default_factory=list)
    bar_meters: list[tuple[int, int]] = field(default_factory=list)
    bar_units: list[int] = field(default_factory=list)
    bar_starts: list[int] = field(default_factory=list)   # n_bars + 1
    chords: int = 0
    tie_groups: int = 0
    keys: list[tuple[float, str]] = field(default_factory=list)

    @property
    def n_bars(self) -> int:
        return len(self.bar_units)

    @property
    def seconds(self) -> float:
        quarters = sum(self.bar_units) * 4 / self.unit_den
        return quarters * 60 / self.tempo

    def notes_of(self, voice: str) -> list[Note]:
        return self.notes.get(voice, [])

    def final_note(self, voice: str | None = None) -> Note | None:
        pool = self.notes_of(voice) if voice else [n for v in VOICES for n in self.notes_of(v)]
        return pool[-1] if pool else None


def _norm_section(text: str) -> str:
    s = re.sub(r"\s+", " ", text.lstrip("%").strip().lower()) or "score"
    s = SECTION_ALIASES.get(s, s)
    return re.sub(r"\s*\d+$", "", s)


def _line_bar_count(line: str) -> int:
    if not line.endswith("|"):
        return 0
    bodies = [b.strip() for b in line[:-1].split("|")]
    total = 0
    for body in bodies:
        m = re.fullmatch(r"Z([2-9])?", body)
        total += int(m.group(1) or 1) if m else 1
    return total


def _sections(text: str, music_lines: dict[int, str], n_bars: int) -> list[str]:
    out = ["score"] * n_bars
    current = "score"
    vocal_bar = 0
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if s.startswith("%"):
            current = _norm_section(s)
        if music_lines.get(i) == "Vocal":
            count = _line_bar_count(s)
            for b in range(vocal_bar, min(n_bars, vocal_bar + count)):
                out[b] = current
            vocal_bar += count
    return out


def _tie_groups(text: str) -> int:
    """Count maximal tie-connected note groups in the Vocal voice.

    `d8-d8-d8` is one group, not two. A chain across a barline is one group.
    A rest or a full-bar Z resets the run.
    """
    voice = None
    in_run = False
    groups = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("V:"):
            voice = s[2:].strip().split()[0]
            continue
        if not s or s[0] in "XTLQVKM%":
            continue
        if voice != "Vocal" or not s.endswith("|"):
            continue
        for body in s[:-1].split("|"):
            if re.fullmatch(r"Z[2-9]?", body.strip()):
                in_run = False
                continue
            for mt in TIE_TOKEN.finditer(body):
                if mt.group("chord") is not None or mt.group("note") is None:
                    continue
                if mt.group("note") == "z":
                    in_run = False
                    continue
                tied = bool(mt.group("tie"))
                if tied and not in_run:
                    groups += 1
                in_run = tied
    return groups


def _key_at(keys: list[tuple[float, str]], onset: float, fallback: str) -> str:
    if not keys:
        return fallback
    times = [t for t, _ in keys]
    i = max(0, bisect.bisect_right(times, onset) - 1)
    return keys[i][1]


def parse(text: str) -> Score:
    """Parse the runtime dialect and build a metric model (bars, sections, keys)."""
    try:
        rt = runtime_abc.parse_abc(text)
    except runtime_abc.AbcError as exc:
        raise AbcError(str(exc)) from exc

    lines = text.splitlines()
    unit_den = rt.unit.denominator
    m = re.fullmatch(r"M:([1-9][0-9]*)/([1-9][0-9]*)", lines[2])
    if not m:
        raise AbcError(f"missing or unsupported M: line: {lines[2]!r}")
    meter = (int(m.group(1)), int(m.group(2)))
    key = lines[7][2:].strip().split()[0]
    key_map(key)

    vocal = rt.voices["Vocal"]
    ins = rt.voices["Ins"]
    bar_units = [int(round(float(length) * unit_den / 4)) for _, length, _ in vocal.bars]
    bar_meters = [tuple(meter_) for _, _, meter_ in vocal.bars]
    if not bar_units:
        raise AbcError("no bars")
    starts = [0]
    for u in bar_units:
        starts.append(starts[-1] + u)

    sections = _sections(text, rt.music_lines, len(bar_units))
    key_units = [(float(t) * unit_den / 4, k) for t, k in vocal.keys]
    starts_q = [float(b[0]) for b in vocal.bars]

    def convert(voice_rt) -> list[Note]:
        out: list[Note] = []
        for onset_q, pitch, dur_q in voice_rt.notes:
            bar = bisect.bisect_right(starts_q, float(onset_q)) - 1
            bar = max(0, min(len(bar_units) - 1, bar))
            onset = float(onset_q) * unit_den / 4
            dur = float(dur_q) * unit_den / 4
            out.append(Note(onset=onset, dur=dur, pitch=int(pitch), bar=bar,
                            section=sections[bar],
                            key=_key_at(key_units, onset, key)))
        return out

    return Score(
        unit_den=unit_den,
        tempo=float(rt.bpm),
        meter=meter,
        key=key,
        notes={"Vocal": convert(vocal), "Ins": convert(ins)},
        bar_sections=sections,
        bar_meters=bar_meters,
        bar_units=bar_units,
        bar_starts=starts,
        chords=len(vocal.chords),
        tie_groups=_tie_groups(text),
        keys=key_units,
    )


def finish(score: Score) -> None:
    """Kept for API compatibility; the runtime parser already resolves ties."""
    return None


# ---------------------------------------------------------------------------
# calibration
# ---------------------------------------------------------------------------

def load_calibration(path: Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_CALIBRATION
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError as exc:
        raise AbcError(f"bad calibration file {p}: {exc}") from exc


def _percentile(value: float | None, stats: dict | None) -> float | None:
    if value is None or not stats:
        return None
    pairs = []
    for p, key in ((0, "min"), (5, "p5"), (25, "p25"), (50, "median"),
                   (75, "p75"), (95, "p95"), (100, "max")):
        v = stats.get(key)
        if v is not None:
            pairs.append((p, float(v)))
    if not pairs:
        return None
    pairs.sort()
    if value <= pairs[0][1]:
        return 0.0
    if value >= pairs[-1][1]:
        return 100.0
    for (p0, v0), (p1, v1) in zip(pairs, pairs[1:]):
        if v0 <= value <= v1:
            if v1 == v0:
                return float(p0)
            return round(p0 + (p1 - p0) * (value - v0) / (v1 - v0), 1)
    return None


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def phrase_split(notes: list[Note], score: Score) -> list[list[Note]]:
    out: list[list[Note]] = []
    cur: list[Note] = []
    prev_end = None
    for note in notes:
        threshold = score.bar_units[max(0, min(score.n_bars - 1, note.bar))] / 4
        if cur and (note.section != cur[-1].section or note.onset - prev_end >= threshold):
            out.append(cur)
            cur = []
        cur.append(note)
        prev_end = note.onset + note.dur
    if cur:
        out.append(cur)
    return [p for p in out if len(p) >= 2]


NOTE_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
           "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
           "A#": 10, "Bb": 10, "B": 11}
PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _pc(name: str) -> int:
    """Pitch class of a note name such as D, Eb, F#, or Bb."""
    key = name.strip().replace("♭", "b").replace("♯", "#")
    if key not in NOTE_PC:
        raise AbcError(f"cannot read pitch class {name!r}")
    return NOTE_PC[key]


def _phrasing(score: Score) -> dict:
    """Shape metrics the listener hears: breath, repetition, endings.

    A *rest phrase* is a contiguous run of vocal notes (one breath). A *beat
    phrase* is the checker's phrase boundary (a rest of at least one beat, or a
    section change) used for answer rates and endings. Seconds are wall-clock at
    the score's tempo, so the same rule works for L:1/16 and L:1/32.
    """
    vocal = sorted(score.notes_of("Vocal"), key=lambda n: n.onset)
    if not vocal:
        return {"intervals": [], "unbroken_seconds_max": None,
                "phrase_seconds_median": None, "repeated_share": None,
                "stepwise_share": None, "distinct_phrase_endings": None,
                "phrase_endings": {}, "breaths_per_bar": None,
                "tessitura_share_ge_c5": None}
    unit_seconds = 4.0 / score.unit_den * 60.0 / score.tempo

    runs: list[list[Note]] = []
    cur: list[Note] = []
    prev_end = None
    for note in vocal:
        if cur and prev_end is not None and note.onset > prev_end:
            runs.append(cur)
            cur = []
        cur.append(note)
        prev_end = note.onset + note.dur
    if cur:
        runs.append(cur)

    def span(run: list[Note]) -> float:
        return ((run[-1].onset + run[-1].dur - run[0].onset) * unit_seconds)

    gaps = []
    for a, b in zip(runs, runs[1:]):
        end = a[-1].onset + a[-1].dur
        if b[0].onset > end:
            gaps.append((b[0].onset - end) * unit_seconds)
    breaths = [g for g in gaps if g >= 0.3]

    intervals = [b.pitch - a.pitch for run in runs for a, b in zip(run, run[1:])]
    beat = phrase_split(vocal, score)
    endings = [PC_NAME[p[-1].pitch % 12] for p in beat]
    counts: dict[str, int] = {}
    for e in endings:
        counts[e] = counts.get(e, 0) + 1

    return {
        "intervals": intervals,
        "unbroken_seconds_max": round(max(span(r) for r in runs), 2),
        "phrase_seconds_median": round(statistics.median(span(r) for r in runs), 2),
        "repeated_share": (round(sum(1 for i in intervals if i == 0) / len(intervals), 3)
                           if intervals else None),
        "stepwise_share": (round(sum(1 for i in intervals if abs(i) <= 2) / len(intervals), 3)
                           if intervals else None),
        "distinct_phrase_endings": len(counts),
        "phrase_endings": counts,
        "breaths_per_bar": round(len(breaths) / score.n_bars, 3) if score.n_bars else None,
        "tessitura_share_ge_c5": round(
            sum(1 for n in vocal if n.pitch >= 72) / len(vocal), 3),
    }


def _sections_match(want: list[str], got: list[str]) -> bool:
    """Plan section types must appear in order in the score; extra score
    sections (interludes, instrumental intros) are allowed."""
    p = [_norm_section(str(x)) for x in want]
    q = [_norm_section(str(x)) for x in got]
    it = iter(q)
    return all(any(x == y for y in it) for x in p)


def check(score: Score, plan: dict, runtime_ok: bool = True, plan_present: bool = True,
          strict_style: bool = False, require_final_rest: bool = False,
          calibration: dict | None = None) -> tuple[list[tuple[str, str, bool, str, str]], dict]:
    """Return (checks, measured).

    A check is (tag, name, ok, detail, class). `tag` is PASS, FAIL or WARN.
    """
    cal = calibration if calibration is not None else load_calibration()
    sanity = cal.get("sanity", {})
    vocal = score.notes_of("Vocal")
    ins = score.notes_of("Ins")
    results: list[tuple[str, str, bool, str, str]] = []

    def add(name: str, ok: bool, detail: str, cls: str = "style") -> None:
        if ok:
            tag = "PASS"
        elif cls in ("contract", "sanity", "structure"):
            tag = "FAIL"
        elif strict_style:
            tag = "FAIL"
        else:
            tag = "WARN"
        results.append((tag, name, bool(ok), detail, cls))

    if runtime_ok:
        add("runtime parse", True, "abc_tools.parse accepted the file", "contract")

    # ---- contract: plan/score agreement --------------------------------
    def plan_value(key):
        return plan.get(key)

    add("key", "key" not in plan or score.key == plan["key"],
        f"K:{score.key}" + (f" (plan {plan['key']})" if "key" in plan else ""), "contract")
    add("meter", "meter" not in plan or plan["meter"] == f"{score.meter[0]}/{score.meter[1]}",
        f"{score.meter[0]}/{score.meter[1]}" + (f" (plan {plan['meter']})" if "meter" in plan else ""),
        "contract")
    add("unit", "unit" not in plan or plan["unit"] == f"1/{score.unit_den}",
        f"L:1/{score.unit_den}" + (f" (plan {plan['unit']})" if "unit" in plan else ""), "contract")
    add("tempo", "tempo" not in plan or abs(score.tempo - float(plan["tempo"])) < 1e-9,
        f"Q:{score.tempo:g}" + (f" (plan {plan['tempo']})" if "tempo" in plan else ""), "contract")
    bars = plan.get("bars")
    add("bars", bars is None or int(bars) == score.n_bars,
        f"{score.n_bars}" + (f" (plan {bars})" if bars is not None else ""), "contract")

    required = ("key", "tempo", "meter", "unit", "bars", "syllables", "sections",
                "melisma_min", "melisma_max", "register", "max_top_duration_share",
                "min_distinct_durations", "ties_min", "min_fill_notes", "chords_min")
    missing = [k for k in required if k not in plan]
    if plan_present:
        add("plan targets", bool(plan) and not missing,
            "complete" if bool(plan) and not missing else (
                "empty plan" if not plan else "missing: " + ", ".join(missing)),
            "contract")
    else:
        add("plan targets", False,
            "missing --plan: every score requires a plan with quality targets", "contract")

    # ---- sanity: six broad degeneracy guards ---------------------------
    max_overlap = float(sanity.get("simultaneity_le4", {}).get("max", 4))
    overlap_units = 0.0
    overlap_bars: set[int] = set()
    if vocal and ins:
        in_starts = [n.onset for n in ins]
        for a in vocal:
            a0, a1 = a.onset, a.onset + a.dur
            hi = bisect.bisect_right(in_starts, a1)
            for b in ins[:hi]:
                b1 = b.onset + b.dur
                if b1 <= a0:
                    continue
                s, e = max(a0, b.onset), min(a1, b1)
                if e > s:
                    overlap_units += e - s
                    overlap_bars.add(a.bar)
    exception = plan.get("simultaneity_exception")
    if exception is None:
        simul_ok = overlap_units <= max_overlap
    else:
        simul_ok = (all(b == int(exception) for b in overlap_bars)
                    and overlap_units <= max_overlap)
    add("simultaneity", simul_ok,
        f"{overlap_units:g} overlapping sixteenths"
        + (f" in bars {sorted(overlap_bars)}" if overlap_bars else "")
        + f" (max {max_overlap:g})", "sanity")

    syllables = plan.get("syllables")
    ratio = (len(vocal) / syllables) if syllables else None
    if ratio is not None:
        lo = float(sanity.get("notes_per_syllable_1.0_1.55", {}).get("min", 1.0))
        hi = float(sanity.get("notes_per_syllable_1.0_1.55", {}).get("max", 1.55))
        add("notes per syllable", lo <= ratio <= hi,
            f"{len(vocal)}/{syllables} = {ratio:.2f} (sanity {lo:.2f}-{hi:.2f})",
            "sanity")
        floor = float(plan.get("melisma_min", 1.0))
        budget = float(plan.get("melisma_max", 1.55))
        add("melisma target", floor <= ratio <= budget,
            f"{ratio:.2f} (plan {floor:.2f}-{budget:.2f})", "style")

    vp = [n.pitch for n in vocal]
    mean_pitch = statistics.mean(vp) if vp else None
    top_pitch = max(vp) if vp else None
    if mean_pitch is not None:
        target_mean = float(sanity.get("register_mean_74_5", {}).get("mean", 74))
        tolerance = float(sanity.get("register_mean_74_5", {}).get("tolerance", 5))
        add("register mean", abs(mean_pitch - target_mean) <= tolerance,
            f"mean {mean_pitch:.1f} vs sanity {target_mean:g} +/- {tolerance:g}",
            "sanity")
        # optional floor: catches a score that never reaches the corpus floor
        top_floor = float(cal.get("sanity_optional", {})
                          .get("register_top_ge80", {}).get("min", 80))
        add("register top floor", top_pitch >= top_floor,
            f"top {top_pitch} vs floor {top_floor:g}", "style")

    reg = plan.get("register")
    if reg and mean_pitch is not None:
        target_mean = float(reg.get("mean", 74))
        tolerance = float(reg.get("tolerance", 4))
        add("register target mean", abs(mean_pitch - target_mean) <= tolerance,
            f"mean {mean_pitch:.1f} vs plan {target_mean:g} +/- {tolerance:g}", "style")
        target_top = reg.get("top")
        if target_top is not None:
            add("register target top", top_pitch >= int(target_top),
                f"top {top_pitch} vs plan >={target_top}", "style")

    durations = [n.dur for n in vocal]
    duration_counts = Counter(durations)
    top_duration_share = (max(duration_counts.values()) / len(durations)
                          if durations else None)
    if top_duration_share is not None:
        cap = float(sanity.get("top_duration_share_le_0.85", {}).get("max", 0.85))
        add("duration spread", top_duration_share <= cap,
            f"most common duration {top_duration_share:.0%} of notes (sanity max {cap:.0%})",
            "sanity")
        style_cap = float(plan.get("max_top_duration_share", cap))
        add("duration spread target", top_duration_share <= style_cap,
            f"{top_duration_share:.0%} (plan max {style_cap:.0%})", "style")

    distinct_floor = int(sanity.get("distinct_durations_ge4", {}).get("min", 4))
    add("duration variety", len(duration_counts) >= distinct_floor,
        f"{len(duration_counts)} distinct durations (sanity min {distinct_floor})", "sanity")
    if "min_distinct_durations" in plan:
        floor_n = int(plan["min_distinct_durations"])
        add("duration variety target", len(duration_counts) >= floor_n,
            f"{len(duration_counts)} distinct durations (plan min {floor_n})", "style")

    ties = score.tie_groups
    tie_floor = int(cal.get("sanity_optional", {}).get("ties_ge1", {}).get("min", 1))
    add("ties floor", ties >= tie_floor,
        f"{ties} tied vocal notes (floor {tie_floor})", "style")
    if "ties_min" in plan:
        add("ties target", ties >= int(plan["ties_min"]),
            f"{ties} tied vocal notes (plan min {plan['ties_min']})", "style")

    ins_floor = float(sanity.get("ins_active_share_ge0.05", {}).get("min", 0.05))
    ins_active = (len({n.bar for n in ins}) / score.n_bars) if score.n_bars else 0.0
    add("ins activity", ins_active >= ins_floor,
        f"Ins sounds in {ins_active:.0%} of bars (sanity min {ins_floor:.0%})", "sanity")
    if "ins_active_share_min" in plan:
        floor_share = float(plan["ins_active_share_min"])
        add("ins activity target", ins_active >= floor_share,
            f"Ins sounds in {ins_active:.0%} of bars (plan min {floor_share:.0%})", "style")

    if "chords_min" in plan:
        add("chords target", score.chords >= int(plan["chords_min"]),
            f"{score.chords} chord symbols (plan min {plan['chords_min']})", "style")
    elif score.chords == 0:
        add("chords", False,
            "0 chord symbols; the measured takes carry about 1.2 per bar", "style")

    # ---- sections (normalized; extra score sections allowed) -----------
    want_sections = [re.sub(r"\s+", " ", str(s).strip().lower()) for s in plan.get("sections", [])]
    score_sections = [s for i, s in enumerate(score.bar_sections)
                      if i == 0 or s != score.bar_sections[i - 1]]
    if want_sections:
        add("sections", _sections_match(want_sections, score_sections),
            " -> ".join(score_sections), "style")

    # ---- cadence -------------------------------------------------------
    last_pc = vocal[-1].pitch % 12 if vocal else None
    cadence_ok = last_pc == tonic_pc(vocal[-1].key if vocal else score.key)
    declared = plan.get("cadence")
    if declared != "any":
        cls = "structure" if declared == "tonic" else "style"
        add("cadence on tonic", cadence_ok,
            f"final pc {last_pc}, tonic {tonic_pc(vocal[-1].key if vocal else score.key)}",
            cls)

    # ---- final rest ----------------------------------------------------
    last_start = score.bar_starts[-2] if score.n_bars else 0
    last_end = score.bar_starts[-1] if score.n_bars else 0
    sounding = [n for n in vocal + ins
                if n.onset < last_end and n.onset + n.dur > last_start]
    final_rest = not sounding
    add("final rest", final_rest,
        f"final bar {score.n_bars}: " + ("rest in both voices" if final_rest
                                        else "has notes; end with Z| in both voices"),
        "contract" if require_final_rest else "style")

    # ---- style warnings ------------------------------------------------
    phrases = phrase_split(vocal, score)
    section_end: dict[str, float] = {}
    for i, sec in enumerate(score.bar_sections):
        section_end[sec] = max(section_end.get(sec, 0.0), float(score.bar_starts[i + 1]))
    answered: dict[str, list[int]] = {}
    answer_lengths: list[int] = []
    for i, phrase in enumerate(phrases):
        start = phrase[-1].onset + phrase[-1].dur
        nxt = (phrases[i + 1][0].onset if i + 1 < len(phrases)
               else section_end[phrase[-1].section])
        if nxt - start < 4:
            continue
        candidates = [n for n in ins if start <= n.onset < nxt]
        answered.setdefault(phrase[-1].section, []).append(int(bool(candidates)))
        if candidates:
            answer_lengths.append(len(candidates))

    sung_sections = {n.section for n in vocal}
    fills: list[list[Note]] = []
    for note in [n for n in ins if n.section in sung_sections]:
        if fills and note.section == fills[-1][-1].section and \
                note.onset - (fills[-1][-1].onset + fills[-1][-1].dur) <= 4:
            fills[-1].append(note)
        else:
            fills.append([note])
    shapes = [tuple(b.pitch - a.pitch for a, b in zip(f, f[1:])) for f in fills if len(f) > 1]
    shape_counts = {s: shapes.count(s) for s in set(shapes)}

    if "min_fill_notes" in plan and (answer_lengths or fills):
        floor_n = int(plan["min_fill_notes"])
        groups = answer_lengths or [len(f) for f in fills]
        shortest = min(groups)
        add("answer fill length", shortest >= floor_n,
            f"shortest answer {shortest} notes (plan min {floor_n}); lengths {groups}",
            "style")

    silence = 1 - sum(n.dur for n in vocal) / (max((n.onset + n.dur for n in vocal), default=0)
                                               - min((n.onset for n in vocal), default=0)) \
        if vocal and max((n.onset + n.dur for n in vocal), default=0) > min((n.onset for n in vocal), default=0) \
        else 0.0
    silence_floor = float(cal.get("style_defaults", {}).get("silence_share_min", 0.22))
    add("silence", silence >= silence_floor,
        f"{silence:.0%} of the sung span is rest (floor {silence_floor:.0%}; corpus ~30%)",
        "style")
    if len(fills) >= 3:
        top = max(shape_counts.values()) if shape_counts else 0
        add("answer mutation", top <= math.ceil(len(fills) / 2),
            f"{len(fills)} fills, {len(shapes)} shapes, most repeated {top}x", "style")
    devs = plan.get("deviations") or []
    if plan:
        add("deviations", 3 <= len(devs) <= 4, f"{len(devs)} declared (target 3-4)", "style")
    verse_sec = "verse 1" if "verse 1" in set(score.bar_sections) else (
        "verse" if "verse" in set(score.bar_sections) else None)
    if "chorus" in set(score.bar_sections) and verse_sec:
        verse = [n.pitch for n in vocal if n.section == verse_sec]
        chorus = [n.pitch for n in vocal if n.section == "chorus"]
        add("chorus lift", not verse or not chorus or max(chorus) >= max(verse),
            f"verse max {max(verse) if verse else '-'}, chorus max {max(chorus) if chorus else '-'}",
            "style")

    # ---- shape: breath, repetition, phrase endings ----------------------
    shape = _phrasing(score)
    unbroken = shape["unbroken_seconds_max"]
    if unbroken is not None:
        cap = float(sanity.get("unbroken_seconds_le_23", {}).get("max", 23))
        add("unbroken singing", unbroken <= cap,
            f"longest unbroken {unbroken:g}s (sanity max {cap:g}s; corpus max 22.9s)",
            "sanity")
        if "max_unbroken_seconds" in plan:
            target = float(plan["max_unbroken_seconds"])
            add("unbroken target", unbroken <= target,
                f"{unbroken:g}s (plan max {target:g}s)", "style")

    repeated = shape["repeated_share"]
    if repeated is not None and len(shape["intervals"]) >= 20:
        floor = float(sanity.get("repeated_share_ge_0.20", {}).get("min", 0.20))
        add("repeated notes", repeated >= floor,
            f"{repeated:.0%} of intervals repeat a pitch (sanity min {floor:.0%}; "
            f"corpus min 25%)", "sanity")

    endings = shape["distinct_phrase_endings"]
    beat_phrases = phrase_split(vocal, score)
    if endings is not None and len(beat_phrases) >= 6:
        floor_n = int(sanity.get("phrase_endings_ge_3", {}).get("min", 3))
        add("phrase endings", endings >= floor_n,
            f"{endings} distinct ending(s) {shape['phrase_endings']} "
            f"(sanity min {floor_n}; corpus min 4)", "sanity")
    if endings is not None and "min_phrase_endings" in plan:
        target_n = int(plan["min_phrase_endings"])
        add("phrase endings target", endings >= target_n,
            f"{endings} distinct ending(s) (plan min {target_n})", "style")

    # ---- maqam: measure against the declared pitch set, not the K: key ---
    maqam = plan.get("maqam")
    maqam_scale: set[int] | None = None
    maqam_name = None
    if isinstance(maqam, dict):
        maqam_name = str(maqam.get("name") or "maqam")
        degrees = maqam.get("degrees") or []
        if degrees:
            try:
                maqam_scale = {_pc(str(d)) for d in degrees}
            except AbcError:
                maqam_scale = None
                add("maqam degrees", False,
                    f"cannot read the declared degrees {degrees!r}; use note names "
                    f"such as D, Eb, F#", "style")
        else:
            add("maqam degrees", False,
                "maqam block has no degrees; chromatic falls back to K:", "style")
        if maqam_scale and vocal:
            chromat = sum(1 for n in vocal if n.pitch % 12 not in maqam_scale)
            fit = 1 - chromat / len(vocal)
            floor_fit = float(plan.get("maqam_fit_min", 0.95))
            add("maqam fit", fit >= floor_fit,
                f"{fit:.0%} of vocal notes in {maqam_name} (min {floor_fit:.0%})",
                "style")
            tonic = maqam.get("tonic")
            if tonic:
                add("maqam tonic", _pc(str(tonic)) == tonic_pc(score.key),
                    f"K:{score.key} tonic {tonic_pc(score.key)}, maqam tonic "
                    f"{_pc(str(tonic))} ({tonic})", "style")

    # ---- measured ------------------------------------------------------
    sec_bars: dict[str, int] = {}
    for sec in score.bar_sections:
        sec_bars[sec] = sec_bars.get(sec, 0) + 1
    if maqam_scale is not None:
        chromatic = sum(1 for n in vocal if n.pitch % 12 not in maqam_scale)
        chromatic_basis = f"maqam:{maqam_name}"
    else:
        chromatic = sum(1 for n in vocal if n.pitch % 12 not in key_scale(n.key))
        chromatic_basis = f"key:{score.key}"
    maqam_fit = (round(1 - chromatic / len(vocal), 3)
                 if maqam_scale is not None and vocal else None)
    register_vocal = {s: (
        f"{min(p)}-{max(p)} mean {statistics.mean(p):.0f}"
        if (p := [n.pitch for n in vocal if n.section == s]) else "-")
        for s in sec_bars}
    measured = {
        "bars": score.n_bars,
        "seconds": round(score.seconds, 1),
        "vocal_notes": len(vocal),
        "ins_notes": len(ins),
        "syllables": syllables,
        "notes_per_syllable": round(ratio, 2) if ratio is not None else None,
        "sections": sec_bars,
        "meters_seen": len({m for m in score.bar_meters}),
        "answer_rate": {k: f"{sum(v)}/{len(v)}" for k, v in answered.items()},
        "fills": len(fills),
        "shapes": len(shape_counts),
        "shape_repeats": sorted(shape_counts.values(), reverse=True),
        "register_vocal": register_vocal,
        "register_mean": round(mean_pitch, 1) if mean_pitch is not None else None,
        "register_top": top_pitch,
        "register_range": f"{min(vp)}-{max(vp)}" if vp else None,
        "chromatic_per_100": round(100 * chromatic / len(vocal), 2) if vocal else None,
        "chromatic_basis": chromatic_basis,
        "maqam": maqam_name,
        "maqam_fit_share": maqam_fit,
        "unbroken_seconds_max": unbroken,
        "phrase_seconds_median": shape["phrase_seconds_median"],
        "breaths_per_bar": shape["breaths_per_bar"],
        "repeated_share": shape["repeated_share"],
        "stepwise_share": shape["stepwise_share"],
        "distinct_phrase_endings": shape["distinct_phrase_endings"],
        "phrase_endings": shape["phrase_endings"],
        "tessitura_share_ge_c5": shape["tessitura_share_ge_c5"],
        "simultaneities": overlap_units,
        "ties": ties,
        "ties_per_10_bars": round(10 * ties / score.n_bars, 2) if score.n_bars else None,
        "cadence_pc": last_pc,
        "final_rest": final_rest,
        "silence_share": round(silence, 2),
        "chords": score.chords,
        "chords_per_bar": round(score.chords / score.n_bars, 2) if score.n_bars else None,
        "deviations": len(devs),
        "top_duration_share": round(top_duration_share, 2) if top_duration_share is not None else None,
        "distinct_durations": len(duration_counts),
        "ins_active_share": round(ins_active, 2),
        "fill_lengths": [len(f) for f in fills],
        "answer_lengths": answer_lengths,
    }
    stats = cal.get("metrics", {})
    measured["percentiles"] = {
        k: _percentile(measured.get(k), stats.get(k))
        for k in ("notes_per_syllable", "register_mean", "register_top", "top_duration_share",
                  "distinct_durations", "ties_per_10_bars", "ins_active_share",
                  "silence_share", "chromatic_per_100", "unbroken_seconds_max",
                  "phrase_seconds_median", "repeated_share", "distinct_phrase_endings",
                  "tessitura_share_ge_c5")
    }
    return results, measured


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--plan", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--calibration", type=Path, default=None)
    ap.add_argument("--strict-style", action="store_true",
                    help="turn style warnings into failures")
    ap.add_argument("--require-final-rest", action="store_true",
                    help="treat the final full-bar rest as a render contract")
    args = ap.parse_args(argv)

    try:
        text = args.score.read_text(encoding="utf-8")
        runtime_abc.parse_abc(text)
    except runtime_abc.AbcError as exc:
        print(f"FAIL  [contract] runtime parse  {exc}")
        return 1
    except OSError as exc:
        print(f"FAIL  [contract] parse  {exc}")
        return 1

    try:
        score = parse(text)
        finish(score)
    except (AbcError, OSError) as exc:
        print(f"FAIL  [contract] parse  {exc}")
        return 1

    try:
        calibration = load_calibration(args.calibration)
    except AbcError as exc:
        print(f"FAIL  [contract] calibration  {exc}")
        return 1

    plan_present = args.plan is not None
    plan = json.loads(args.plan.read_text(encoding="utf-8")) if plan_present else {}
    results, measured = check(score, plan, plan_present=plan_present,
                              strict_style=args.strict_style,
                              require_final_rest=args.require_final_rest,
                              calibration=calibration)
    width = max(len(name) for _, name, _, _, _ in results)
    failed = warned = 0
    for tag, name, _, detail, cls in results:
        print(f"{tag:<4}  [{cls:<8}]  {name:<{width}}  {detail}")
        failed += tag == "FAIL"
        warned += tag == "WARN"

    print("\nMEASURED")
    for key, value in measured.items():
        if isinstance(value, dict):
            value = " | ".join(f"{k} {v}" for k, v in value.items())
        print(f"  {key:<18} {value}")

    if args.json:
        args.json.write_text(json.dumps(
            {"ok": failed == 0,
             "strict_style": args.strict_style,
             "require_final_rest": args.require_final_rest,
             "calibration_version": calibration.get("version"),
             "checks": [{"tag": t, "name": n, "ok": o, "class": c, "detail": d}
                        for t, n, o, d, c in results],
             "measured": measured}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")
    print(f"\n{'PASS' if failed == 0 else 'FAIL'}  {failed} hard check(s) failed, "
          f"{warned} warning(s)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
