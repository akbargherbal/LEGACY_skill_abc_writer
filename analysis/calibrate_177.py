#!/usr/bin/env python3
"""Calibrate the maqam-score constraints against the 177-track ABC corpus.

The skill's thresholds are measured from one lyric set and five takes. This
script asks the same questions of the 177 SheetSage2 transcripts that the
project actually curates, using the *same* definitions the checker uses.

Why a dedicated parser: 121/177 corpus scores carry inline ``M:`` changes
and nine different meters. ``checker.parse`` rejects inline meter changes by
design, so it cannot read the corpus it is supposed to describe. This parser
accepts them and otherwise follows checker semantics (tie merging, accidental
scope, bar arithmetic, chord placement).

Outputs (under ``--out``):

    tracks.jsonl     one row per track: raw metrics + gate verdicts
    summary.json     distributions and pass rates for every inventory number
    budget.json      the A-series: cap, letters, bars, units per syllable

Usage:
    python3 analysis/calibrate_177.py \
        --corpus ~/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars \
        --out analysis/out
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import re
import statistics as st
import unicodedata
from fractions import Fraction
from pathlib import Path

VOWEL_MARKS = "\u064e\u064f\u0650\u064b\u064c\u064d\u0670"  # same rule as syllabify.py

NATURAL = dict(zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)))
SHARP_ORDER = "FCGDAEB"
FLAT_ORDER = "BEADGCF"
_MAJOR = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7}
_MINOR = {"A": 0, "E": 1, "B": 2, "F#": 3, "C#": 4, "G#": 5, "D#": 6, "A#": 7}
_MAJOR_FLAT = {"F": -1, "BB": -2, "EB": -3, "AB": -4, "DB": -5, "GB": -6, "CB": -7}
_MINOR_FLAT = {"D": -1, "G": -2, "C": -3, "F": -4, "BB": -5, "EB": -6, "AB": -7}

TOKEN = re.compile(
    r'"(?P<chord>[^"\n]*)"|'
    r"(?P<acc>\^\^|__|\^|_|=)?(?P<note>[A-Ga-gz])"
    r"(?P<oct>[,']*)(?P<dur>[0-9]*)(?P<tie>-?)"
)


class AbcError(ValueError):
    pass


# ---------------------------------------------------------------------------
# header / key helpers (identical to checker.py)
# ---------------------------------------------------------------------------

def key_sharps(key: str) -> int:
    v = key.strip().split()[0]
    m = re.match(r"^([A-Ga-g])([#b]?)(.*)$", v)
    if not m:
        raise AbcError(f"unparseable key {key!r}")
    letter, acc, mode = m.group(1).upper(), m.group(2), m.group(3).lower()
    if mode in {"dor", "phr", "lyd", "mix"}:
        raise AbcError(f"unsupported mode in {key!r}")
    name = (letter + acc).upper()
    minor = mode.startswith("m")
    table = _MINOR if minor else _MAJOR
    flat = _MINOR_FLAT if minor else _MAJOR_FLAT
    if name in table:
        return table[name]
    if name in flat:
        return flat[name]
    raise AbcError(f"unknown key {key!r}")


def key_alterations(key: str) -> dict[str, int]:
    count = key_sharps(key)
    alter = {k: 0 for k in NATURAL}
    for letter in (SHARP_ORDER if count > 0 else FLAT_ORDER)[:abs(count)]:
        alter[letter] = 1 if count > 0 else -1
    return alter


def key_scale(key: str) -> set[int]:
    alter = key_alterations(key)
    return {(NATURAL[letter] + alter[letter]) % 12 for letter in NATURAL}


def tonic_pc(key: str) -> int:
    m = re.match(r"([A-G])([#b]?)", key)
    if not m:
        raise AbcError(f"cannot read tonic from {key!r}")
    return (NATURAL[m.group(1)] + (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0)) % 12


def parse_key(value: str) -> str:
    return value.strip().split()[0]


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------

class Voice:
    def __init__(self, name: str):
        self.name = name
        self.time = Fraction(0)
        self.bars: list[dict] = []
        self.notes: list[dict] = []
        self.pending: dict | None = None
        self.chords = 0
        self.key = "C"
        self.keys: list[tuple[Fraction, str]] = [(Fraction(0), "C")]
        self.meter = (4, 4)


def parse_score(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 9:
        raise AbcError("incomplete score")
    if lines[0:2] != ["X:1", "T:"]:
        raise AbcError("header must start X:1, T:")
    m = re.fullmatch(r"M:([1-9][0-9]*)/([1-9][0-9]*)", lines[2])
    if not m:
        raise AbcError(f"bad M: {lines[2]!r}")
    meter = (int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"L:1/([1-9][0-9]*)", lines[3])
    if not m:
        raise AbcError(f"bad L: {lines[3]!r}")
    unit_den = int(m.group(1))
    unit = Fraction(4, unit_den)  # one L-unit in quarter notes
    m = re.fullmatch(r"Q:1/4=([1-9][0-9]*)", lines[4])
    if not m:
        raise AbcError(f"bad Q: {lines[4]!r}")
    tempo = int(m.group(1))
    if not lines[5].startswith("V: Vocal") or not lines[6].startswith("V: Ins"):
        raise AbcError("voice header mismatch")
    if not lines[7].startswith("K:"):
        raise AbcError("missing K:")
    key = parse_key(lines[7][2:])
    key_sharps(key)

    voices = {"Vocal": Voice("Vocal"), "Ins": Voice("Ins")}
    for v in voices.values():
        v.key = key
        v.keys = [(Fraction(0), key)]
        v.meter = meter

    section = "score"
    current = "Vocal"
    block_sizes: list[int] = []
    meter_changes = 0
    seen_key_changes = 0

    for raw in lines[8:]:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("%"):
            section = re.sub(r"\s+", " ", s.lstrip("%").strip().lower()) or section
            continue
        if s.startswith("V:"):
            current = s[2:].strip().split()[0]
            if current not in voices:
                raise AbcError(f"unknown voice {current!r}")
            continue
        m = re.fullmatch(r"M:([1-9][0-9]*)/([1-9][0-9]*)", s)
        if m:
            voices[current].meter = (int(m.group(1)), int(m.group(2)))
            meter_changes += 1
            continue
        m = re.fullmatch(r"K:(.+)", s)
        if m:
            k = parse_key(m.group(1))
            key_sharps(k)
            voices[current].key = k
            voices[current].keys.append((voices[current].time, k))
            seen_key_changes += 1
            continue
        if re.match(r"^[A-Za-z]:", s):
            raise AbcError(f"unexpected field {s[:40]!r}")
        if not s.endswith("|"):
            raise AbcError(f"music line must end with '|': {s[:40]!r}")
        bodies = [b.strip() for b in s[:-1].split("|")]
        if not bodies or any(not b for b in bodies):
            raise AbcError(f"empty measure in {s[:40]!r}")
        block_sizes.append(sum(
            int(b[1:] or 1) if re.fullmatch(r"Z[2-9]?", b) else 1 for b in bodies))
        v = voices[current]
        for body in bodies:
            n, d = v.meter
            length = Fraction(4 * n, d)
            start = v.time
            local: dict[str, int] = {}
            if re.fullmatch(r"Z[2-9]?", body):
                reps = int(body[1:] or 1)
                for _ in range(reps):
                    v.bars.append({"start": v.time, "length": length,
                                   "meter": v.meter, "section": section,
                                   "voice": v.name})
                    v.time += length
                v.pending = None
                continue
            offset = Fraction(0)
            cursor = 0
            while cursor < len(body):
                if body[cursor].isspace():
                    cursor += 1
                    continue
                inline = re.match(r"\[(K|M):([^\]]+)\]", body[cursor:])
                if inline:
                    field, value = inline.group(1), inline.group(2).strip()
                    cursor += inline.end()
                    if field == "K":
                        k = parse_key(value)
                        key_sharps(k)
                        v.key = k
                        v.keys.append((start + offset, k))
                        seen_key_changes += 1
                    else:
                        mm = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)", value)
                        if not mm:
                            raise AbcError(f"bad inline meter {value!r}")
                        v.meter = (int(mm.group(1)), int(mm.group(2)))
                        meter_changes += 1
                    continue
                mt = TOKEN.match(body, cursor)
                if not mt:
                    raise AbcError(f"unsupported token {body[cursor:cursor + 20]!r}")
                cursor = mt.end()
                chord = mt.group("chord")
                if chord is not None:
                    if v.name == "Vocal":
                        v.chords += 1
                    continue
                note, acc, octave = mt.group("note"), mt.group("acc"), mt.group("oct")
                dur = unit * int(mt.group("dur") or 1)
                tie = bool(mt.group("tie"))
                if offset + dur > length:
                    raise AbcError(f"{v.name} bar passes bar end")
                if note == "z":
                    if v.pending is not None:
                        raise AbcError("tie enters a rest")
                    v.pending = None
                else:
                    letter = note.upper()
                    written = 60 + NATURAL[letter] + (12 if note.islower() else 0)
                    written += 12 * (octave.count("'") - octave.count(","))
                    alter = key_alterations(v.key)
                    value = local.get(letter, alter[letter])
                    if acc:
                        value = {"=": 0, "_": -1, "__": -2, "^": 1, "^^": 2}[acc]
                        local[letter] = value
                    pitch = written + value
                    if v.pending is not None:
                        old = v.pending
                        if not acc and written == old["written"]:
                            pitch = old["pitch"]
                        if pitch != old["pitch"]:
                            raise AbcError(f"tie changes pitch {old['pitch']}->{pitch}")
                        old["note"]["dur"] += dur
                        old["note"]["tied"] = True
                    else:
                        note_obj = {"onset": start + offset, "dur": dur, "pitch": pitch,
                                    "bar": len(v.bars), "section": section,
                                    "tied": False, "key": v.key, "voice": v.name}
                        v.notes.append(note_obj)
                    v.pending = {"pitch": pitch, "written": written,
                                 "note": v.notes[-1]} if tie else None
                offset += dur
            if offset != length:
                raise AbcError(f"{v.name} bar sums to {offset} not {length}")
            v.bars.append({"start": start, "length": length, "meter": v.meter,
                           "section": section, "voice": v.name})
            v.time += length

    if voices["Vocal"].pending is not None or voices["Ins"].pending is not None:
        raise AbcError("unresolved tie")
    return {
        "path": str(path),
        "tempo": tempo,
        "unit_den": unit_den,
        "unit": unit,
        "header_meter": meter,
        "key": key,
        "voices": voices,
        "block_sizes": block_sizes,
        "meter_changes": meter_changes,
        "key_changes": seen_key_changes,
        "lines": lines,
    }


# ---------------------------------------------------------------------------
# measurement (checker semantics)
# ---------------------------------------------------------------------------

def bar_index(bars: list[dict], t: Fraction) -> int:
    starts = [b["start"] for b in bars]
    return max(0, min(len(bars) - 1, bisect.bisect_right(starts, t) - 1))


def band(values: list[float]) -> dict:
    v = sorted(x for x in values if x is not None)
    if not v:
        return {"n": 0}
    n = len(v)

    def q(f):
        return v[min(n - 1, max(0, int(round(f * (n - 1)))))]

    return {"n": n, "min": v[0], "p5": q(.05), "p10": q(.10), "p25": q(.25),
            "median": st.median(v), "p75": q(.75), "p90": q(.90), "p95": q(.95),
            "max": v[-1]}


def measure(parsed: dict) -> dict:
    v: Voice = parsed["voices"]["Vocal"]
    ins: Voice = parsed["voices"]["Ins"]
    unit: Fraction = parsed["unit"]
    bars = v.bars
    n_bars = len(bars)
    if n_bars == 0:
        raise AbcError("no bars")
    vnotes = sorted(v.notes, key=lambda n: n["onset"])
    inotes = sorted(ins.notes, key=lambda n: n["onset"])

    def units(x: Fraction) -> float:
        return float(x / unit)

    # pitch / register
    pitches = [n["pitch"] for n in vnotes]
    mean_pitch = st.mean(pitches) if pitches else None
    top_pitch = max(pitches) if pitches else None
    p05 = sorted(pitches)[max(0, int(.05 * len(pitches)) - 1)] if pitches else None
    p95 = sorted(pitches)[min(len(pitches) - 1, int(.95 * len(pitches)))] if pitches else None

    # durations
    durs = [units(Fraction(n["dur"])) for n in vnotes]
    from collections import Counter
    dur_counts = Counter(durs)
    top_share = (max(dur_counts.values()) / len(durs)) if durs else None
    distinct_durs = len(dur_counts)
    ties = sum(1 for n in vnotes if n["tied"])

    # chords
    chords = getattr(v, "chords", 0)

    # ins activity on the vocal bar grid
    ins_bars = {bar_index(bars, n["onset"]) for n in inotes}
    ins_active = len(ins_bars) / n_bars

    # silence over the sung span
    if vnotes:
        first = min(n["onset"] for n in vnotes)
        last = max(n["onset"] + n["dur"] for n in vnotes)
        silence = float(1 - sum(n["dur"] for n in vnotes) / (last - first)) if last > first else 0.0
    else:
        silence = None

    # chromatic
    chrom = sum(1 for n in vnotes if n["pitch"] % 12 not in key_scale(n["key"]))
    chrom_per_100 = 100 * chrom / len(vnotes) if vnotes else None

    # cadence + final rest
    cadence_ok = bool(vnotes) and vnotes[-1]["pitch"] % 12 == tonic_pc(vnotes[-1]["key"])
    last_bar = bars[-1]
    final_sounding = [n for n in vnotes + inotes
                      if n["onset"] < last_bar["start"] + last_bar["length"]
                      and n["onset"] + n["dur"] > last_bar["start"]]
    final_rest = not final_sounding

    # simultaneity (in L-units)
    overlap_units = 0.0
    overlap_bars: set[int] = set()
    if vnotes and inotes:
        in_starts = [n["onset"] for n in inotes]
        for a in vnotes:
            a0, a1 = a["onset"], a["onset"] + a["dur"]
            hi = bisect.bisect_right(in_starts, a1)
            for b in inotes[:hi]:
                b1 = b["onset"] + b["dur"]
                if b1 <= a0:
                    continue
                s, e = max(a0, b["onset"]), min(a1, b1)
                if e > s:
                    overlap_units += units(e - s)
                    overlap_bars.add(a["bar"])

    # phrase / answer / fill (checker logic)
    def phrase_split(notes: list[dict]) -> list[list[dict]]:
        out, cur = [], []
        prev_end = None
        for n in notes:
            bi = bar_index(bars, n["onset"])
            thresh = bars[bi]["length"] / 4
            if cur and (n["section"] != cur[-1]["section"]
                        or n["onset"] - prev_end >= thresh):
                out.append(cur)
                cur = []
            cur.append(n)
            prev_end = n["onset"] + n["dur"]
        if cur:
            out.append(cur)
        return [p for p in out if len(p) >= 2]

    phrases = phrase_split(vnotes)
    section_end: dict[str, Fraction] = {}
    for b in bars:
        section_end[b["section"]] = max(section_end.get(b["section"], Fraction(0)),
                                        b["start"] + b["length"])
    answer_lengths: list[int] = []
    for i, ph in enumerate(phrases):
        start = ph[-1]["onset"] + ph[-1]["dur"]
        nxt = phrases[i + 1][0]["onset"] if i + 1 < len(phrases) else section_end[ph[-1]["section"]]
        if nxt - start < 4 * unit:
            continue
        cand = [n for n in inotes if start <= n["onset"] < nxt]
        if cand:
            answer_lengths.append(len(cand))

    sung_sections = {n["section"] for n in vnotes}
    fills: list[list[dict]] = []
    for n in [x for x in inotes if x["section"] in sung_sections]:

        if fills and n["section"] == fills[-1][-1]["section"] and \
                n["onset"] - (fills[-1][-1]["onset"] + fills[-1][-1]["dur"]) <= 4 * unit:
            fills[-1].append(n)
        else:
            fills.append([n])
    fill_lengths = [len(f) for f in fills]
    shapes = [tuple(b["pitch"] - a["pitch"] for a, b in zip(f, f[1:]))
              for f in fills if len(f) > 1]
    shape_counts = {s: shapes.count(s) for s in set(shapes)}
    mutation_ok = (max(shape_counts.values()) <= math.ceil(len(fills) / 2)) if len(fills) >= 3 else None

    # section registers, for the chorus-lift warning
    section_pitch: dict[str, list[int]] = {}
    for n in vnotes:
        section_pitch.setdefault(n["section"], []).append(n["pitch"])
    section_top = {k: max(v) for k, v in section_pitch.items()}
    section_mean = {k: st.mean(v) for k, v in section_pitch.items()}
    verse_key = "verse 1" if "verse 1" in section_top else ("verse" if "verse" in section_top else None)
    chorus_lift = (None if not (verse_key and "chorus" in section_top)
                   else section_top["chorus"] >= section_top[verse_key])

    sections = []
    for b in bars:
        if not sections or sections[-1] != b["section"]:
            sections.append(b["section"])
    meter_sequence = []
    for b in bars:
        if not meter_sequence or meter_sequence[-1] != b["meter"]:
            meter_sequence.append(b["meter"])

    nominal_quarters = sum(b["length"] for b in bars)
    nominal_seconds = float(nominal_quarters * 60 / parsed["tempo"])

    return {
        "bars": n_bars,
        "vocal_notes": len(vnotes),
        "ins_notes": len(inotes),
        "sections": sections,
        "meter_sequence": [f"{n}/{d}" for n, d in meter_sequence],
        "meter_changes": parsed["meter_changes"],
        "max_block_bars": max(parsed["block_sizes"]) if parsed["block_sizes"] else 0,
        "unit": f"1/{parsed['unit_den']}",
        "tempo": parsed["tempo"],
        "header_meter": f"{parsed['header_meter'][0]}/{parsed['header_meter'][1]}",
        "key": parsed["key"],
        "register_mean": mean_pitch,
        "register_top": top_pitch,
        "register_p05": p05,
        "register_p95": p95,
        "top_duration_share": top_share,
        "distinct_durations": distinct_durs,
        "duration_counts": {str(k): n for k, n in sorted(dur_counts.items())},
        "ties": ties,
        "ties_per_10_bars": 10 * ties / n_bars,
        "chords": chords,
        "chords_per_bar": chords / n_bars,
        "ins_active_share": ins_active,
        "silence_share": silence,
        "chromatic_per_100": chrom_per_100,
        "cadence_on_tonic": cadence_ok,
        "final_rest": final_rest,
        "simultaneity_units": overlap_units,
        "simultaneity_bars": len(overlap_bars),
        "phrases": len(phrases),
        "answer_lengths": answer_lengths,
        "shortest_answer": min(answer_lengths) if answer_lengths else None,
        "fills": len(fills),
        "fill_lengths": fill_lengths,
        "shortest_fill": min(fill_lengths) if fill_lengths else None,
        "mutation_ok": mutation_ok,
        "section_mean": section_mean,
        "section_top": section_top,
        "chorus_lift": chorus_lift,
        "nominal_seconds": nominal_seconds,
        "nominal_quarters": float(nominal_quarters),
        "lines_abc": len(parsed["lines"]),
    }


# ---------------------------------------------------------------------------
# lyrics / budget side
# ---------------------------------------------------------------------------

def arabic_letters(text: str) -> int:
    return sum(1 for c in text if 0x0600 <= ord(c) <= 0x06FF and unicodedata.category(c) == "Lo")


def syllables(text: str) -> int:
    return sum(1 for c in text if c in VOWEL_MARKS)


def lyric_facts(rec: dict) -> dict:
    lines = [l for s in rec.get("sections") or [] for l in (s.get("lines") or [])]
    sylls = [syllables(l) for l in lines]
    letters = arabic_letters(rec.get("plain") or "")
    med = st.median(sylls) if sylls else 0
    flagged = sum(1 for n in sylls if abs(n - med) > 1) if sylls else 0
    return {
        "lyric_lines": len(lines),
        "syllables": sum(sylls),
        "letters": letters,
        "syllables_per_line": sylls,
        "median_syllables_per_line": med,
        "lines_flagged_break": flagged,
        "flagged_share": flagged / len(sylls) if sylls else None,
    }


# ---------------------------------------------------------------------------
# gate simulation
# ---------------------------------------------------------------------------

INVENTORY = {
    "melisma_min": 1.12,
    "melisma_max": 1.30,
    "register_mean": 74.0,
    "register_tolerance": 4.0,
    "register_top": 85,
    "max_top_duration_share": 0.75,
    "min_distinct_durations": 4,
    "ties_min": 5,
    "min_fill_notes": 3,
    "ins_active_share_min": 0.30,
    "chords_min": 37,
}


SANITY_CORE = {
    "simultaneity_le4": "overlap <= 4 sixteenths (corpus max 8; 99.4% pass)",
    "register_mean_74_5": "74 +/- 5 semitones (corpus 69.6-75.9)",
    "top_duration_share_le_0.85": "<= 0.85 (corpus max 0.86)",
    "distinct_durations_ge4": ">= 4 (corpus min 4)",
    "notes_per_syllable_1.0_1.55": "1.0-1.55 (corpus 1.03-1.52)",
    "ins_active_share_ge0.05": ">= 0.05 (corpus min 0.08)",
}

SANITY_EXTRA = {
    "register_top_ge80": ">= 80 (corpus min 80; no corpus track fails)",
    "ties_ge1": ">= 1 (1/177 has none; 0 is valid for a syllabic style)",
}


def sanity_gates(m: dict, syllables_n: int) -> dict:
    """Six broad degeneracy guards, not style targets.

    They catch an octave error, a monotone rhythm, a missing second voice, an
    extreme melisma ratio, or voices that overlap everywhere. They do not
    prescribe melisma level, high register, Ins density, tie count, chord
    symbols, or cadence.
    """
    ratio = (m["vocal_notes"] / syllables_n) if syllables_n else None
    return {
        "simultaneity_le4": m["simultaneity_units"] <= 4,
        "register_mean_74_5": (
            None if m["register_mean"] is None else abs(m["register_mean"] - 74) <= 5),
        "top_duration_share_le_0.85": (
            None if m["top_duration_share"] is None else m["top_duration_share"] <= 0.85),
        "distinct_durations_ge4": m["distinct_durations"] >= 4,
        "notes_per_syllable_1.0_1.55": (
            None if ratio is None else 1.0 <= ratio <= 1.55),
        "ins_active_share_ge0.05": m["ins_active_share"] >= 0.05,
    }


def sanity_extended_gates(m: dict, syllables_n: int) -> dict:
    out = sanity_gates(m, syllables_n)
    out["register_top_ge80"] = None if m["register_top"] is None else m["register_top"] >= 80
    out["ties_ge1"] = m["ties"] >= 1
    return out


def gates(m: dict, syllables_n: int) -> dict:
    ratio = (m["vocal_notes"] / syllables_n) if syllables_n else None
    out = {}
    out["notes_per_syllable"] = (
        None if ratio is None else INVENTORY["melisma_min"] <= ratio <= INVENTORY["melisma_max"])
    out["register_mean"] = (
        None if m["register_mean"] is None else
        abs(m["register_mean"] - INVENTORY["register_mean"]) <= INVENTORY["register_tolerance"])
    out["register_top"] = (
        None if m["register_top"] is None else m["register_top"] >= INVENTORY["register_top"])
    out["duration_spread"] = (
        None if m["top_duration_share"] is None else
        m["top_duration_share"] <= INVENTORY["max_top_duration_share"])
    out["duration_variety"] = m["distinct_durations"] >= INVENTORY["min_distinct_durations"]
    out["ties"] = m["ties"] >= INVENTORY["ties_min"]
    out["ties_per_10"] = m["ties_per_10_bars"] >= (10 * INVENTORY["ties_min"] / 74)
    out["fill_length"] = (
        None if m["shortest_answer"] is None else m["shortest_answer"] >= INVENTORY["min_fill_notes"])
    out["fill_length_all"] = (
        None if m["shortest_fill"] is None else m["shortest_fill"] >= INVENTORY["min_fill_notes"])
    out["ins_activity"] = m["ins_active_share"] >= INVENTORY["ins_active_share_min"]
    out["chords_abs"] = m["chords"] >= INVENTORY["chords_min"]
    out["chords_per_bar_0.5"] = m["chords_per_bar"] >= 0.5
    out["chords_per_bar_1.0"] = m["chords_per_bar"] >= 1.0
    out["cadence"] = m["cadence_on_tonic"]
    out["final_rest"] = m["final_rest"]
    out["simultaneity_zero"] = m["simultaneity_units"] == 0
    out["simultaneity_le4"] = m["simultaneity_units"] <= 4
    out["silence_warn"] = None if m["silence_share"] is None else m["silence_share"] >= 0.25
    return out


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("analysis/out"))
    args = ap.parse_args()

    root = args.corpus
    transcripts = sorted((root / "transcripts").glob("*.abc"))
    lyrics = {r["track_id"]: r for r in load_jsonl(root / "lyrics.jsonl")}
    manifest = {r["track_id"]: r for r in load_jsonl(root / "manifest.jsonl")}
    args.out.mkdir(parents=True, exist_ok=True)

    rows, errors = [], []
    for p in transcripts:
        tid = p.stem
        ly = lyrics.get(tid, {})
        man = manifest.get(tid, {})
        lf = lyric_facts(ly)
        try:
            parsed = parse_score(p)
            m = measure(parsed)
        except Exception as exc:  # noqa: BLE001
            errors.append({"track_id": tid, "error": f"{type(exc).__name__}: {exc}"})
            continue
        m["notes_per_syllable"] = (
            m["vocal_notes"] / lf["syllables"] if lf["syllables"] else None)
        g = gates(m, lf["syllables"])

        def base_name(name: str) -> str:
            return re.sub(r"\s*\d+$", "", str(name).strip().lower())

        lyric_types = [base_name(s.get("type")) for s in (ly.get("sections") or [])]
        abc_sections = [base_name(s) for s in m["sections"]]
        it = iter(lyric_types)
        section_subseq = all(any(x == y for y in it) for x in abc_sections)
        row = {"track_id": tid, "maqam": man.get("maqam") or ly.get("maqam"),
               **lf, **m, "gates": g, "sanity": sanity_gates(m, lf["syllables"]),
               "sanity_extended": sanity_extended_gates(m, lf["syllables"]),
               "section_subsequence": section_subseq,
               "section_exact": abc_sections == lyric_types}
        # budget side
        audio_s = man.get("duration_s")
        cap = 111.1 + 0.3126 * lf["letters"] if lf["letters"] else None
        row["audio_duration_s"] = audio_s
        row["duration_cap_s"] = cap
        row["audio_over_cap"] = (audio_s / cap) if audio_s and cap else None
        row["cap_covers_audio"] = (cap >= audio_s) if audio_s and cap else None
        row["audio_over_nominal"] = (audio_s / m["nominal_seconds"]) if audio_s and m["nominal_seconds"] else None
        # sixteenths per syllable over the whole score and over vocal-sounding bars
        total_q = m["nominal_quarters"]
        row["units16_per_syllable_total"] = (4 * total_q / lf["syllables"]) if lf["syllables"] else None
        vbars_q = None
        # vocal-sounding bars: recompute from bar map
        try:
            v = parsed["voices"]["Vocal"]
            vbar_idx = {bar_index(v.bars, n["onset"]) for n in v.notes}
            vbars_q = sum(float(v.bars[i]["length"]) for i in vbar_idx)
        except Exception:
            pass
        row["units16_per_syllable_vocal_bars"] = (4 * vbars_q / lf["syllables"]) if vbars_q and lf["syllables"] else None
        rows.append(row)

    # ------------------------------------------------------------------
    # aggregates
    # ------------------------------------------------------------------
    def vals(key):
        return [r[key] for r in rows if r.get(key) is not None]

    gate_names = sorted({k for r in rows for k, v in r["gates"].items() if v is not None})
    gate_pass = {}
    for k in gate_names:
        seen = [r["gates"][k] for r in rows if r["gates"].get(k) is not None]
        gate_pass[k] = {"n": len(seen), "pass": sum(1 for x in seen if x),
                        "rate": sum(1 for x in seen if x) / len(seen) if seen else None}

    metrics = [
        "notes_per_syllable",
        "bars", "vocal_notes", "ins_notes", "register_mean", "register_top",
        "register_p05", "register_p95", "top_duration_share", "distinct_durations",
        "ties", "ties_per_10_bars", "chords", "chords_per_bar", "ins_active_share",
        "silence_share", "chromatic_per_100", "shortest_answer", "shortest_fill",
        "simultaneity_units", "lyric_lines", "syllables", "letters",
        "audio_duration_s", "duration_cap_s", "audio_over_cap", "audio_over_nominal",
        "units16_per_syllable_total", "units16_per_syllable_vocal_bars",
        "flagged_share", "max_block_bars", "meter_changes", "phrases",
    ]
    summary = {k: band(vals(k)) for k in metrics}
    summary["n_tracks"] = len(rows)
    summary["errors"] = errors
    summary["gate_pass"] = gate_pass
    summary["units"] = {k: sorted({r[k] for r in rows if r.get(k)}) for k in ("unit", "header_meter")}
    summary["meters_seen"] = sorted({m for r in rows for m in r["meter_sequence"]})
    summary["tracks_with_meter_changes"] = sum(1 for r in rows if r["meter_changes"] > 0)
    summary["tracks_multi_meter"] = sum(1 for r in rows if len(r["meter_sequence"]) > 1)
    summary["sections_seen"] = sorted({s for r in rows for s in r["sections"]})
    summary["final_rest_rate"] = gate_pass.get("final_rest")
    summary["cadence_rate"] = gate_pass.get("cadence")
    summary["unit_counts"] = {u: sum(1 for r in rows if r["unit"] == u) for u in summary["units"]["unit"]}
    summary["header_meter_counts"] = {m: sum(1 for r in rows if r["header_meter"] == m)
                                      for m in summary["units"]["header_meter"]}
    summary["maqam_counts"] = {q: sum(1 for r in rows if r["maqam"] == q)
                               for q in sorted({r["maqam"] for r in rows if r["maqam"]})}
    summary["section_subsequence_rate"] = sum(1 for r in rows if r["section_subsequence"]) / len(rows)
    summary["section_exact_rate"] = sum(1 for r in rows if r["section_exact"]) / len(rows)
    summary["chorus_lift_rate"] = (
        sum(1 for r in rows if r["chorus_lift"]) /
        sum(1 for r in rows if r["chorus_lift"] is not None))
    summary["answer_mutation_rate"] = (
        sum(1 for r in rows if r["mutation_ok"]) /
        sum(1 for r in rows if r["mutation_ok"] is not None))
    chrom = vals("chromatic_per_100")
    summary["chromatic"] = {"mean": st.mean(chrom), "zero_tracks": sum(1 for x in chrom if x == 0),
                            "n": len(chrom)}

    # the 95% rule: a hard gate set must pass at least 95% of good tracks
    def evaluate(prefix: str, thresholds: dict) -> dict:
        names = [k for k in thresholds if any(r[prefix].get(k) is not None for r in rows)]
        fails = {k: sum(1 for r in rows if r[prefix].get(k) is False) for k in names}
        passed = sum(1 for r in rows if all(r[prefix].get(k) is not False for k in names))
        return {
            "rule": "joint pass >= 95% of the 177",
            "thresholds": thresholds,
            "n": len(rows),
            "pass": passed,
            "rate": passed / len(rows),
            "meets_95": passed / len(rows) >= 0.95,
            "failures_by_gate": fails,
            "note": "broad degeneracy guards; style targets stay warnings/priors",
        }

    summary["sanity_gate_set"] = evaluate("sanity", SANITY_CORE)
    summary["sanity_extended"] = evaluate("sanity_extended", {**SANITY_CORE, **SANITY_EXTRA})
    default_hard = ["notes_per_syllable", "register_mean", "register_top",
                    "duration_spread", "duration_variety", "ties", "fill_length",
                    "ins_activity", "cadence", "final_rest", "simultaneity_zero"]
    default_pass = sum(1 for r in rows
                       if all(r["gates"].get(k) is not False for k in default_hard))
    summary["current_defaults"] = {
        "hard_gates": default_hard,
        "pass": default_pass,
        "rate": default_pass / len(rows),
        "with_chords": sum(1 for r in rows
                           if all(r["gates"].get(k) is not False for k in default_hard)
                           and r["gates"].get("chords_abs") is not False),
    }

    # pass rate at candidate thresholds — what a calibrated gate would allow
    grid = {}
    ratios = [r["vocal_notes"] / r["syllables"] for r in rows if r["syllables"]]
    grid["melisma_max"] = {str(x): sum(1 for v in ratios if v <= x) / len(ratios)
                           for x in (1.30, 1.35, 1.40, 1.45, 1.50)}
    grid["melisma_min"] = {str(x): sum(1 for v in ratios if v >= x) / len(ratios)
                           for x in (1.00, 1.05, 1.10, 1.12, 1.15)}
    grid["register_top"] = {str(x): sum(1 for r in rows if r["register_top"] >= x) / len(rows)
                            for x in (78, 79, 80, 81, 82, 83, 84, 85)}
    grid["ins_active_share_min"] = {str(x): sum(1 for r in rows if r["ins_active_share"] >= x) / len(rows)
                                    for x in (0.10, 0.15, 0.20, 0.25, 0.30)}
    grid["max_top_duration_share"] = {str(x): sum(1 for r in rows if r["top_duration_share"] <= x) / len(rows)
                                      for x in (0.65, 0.70, 0.75, 0.80, 0.85, 0.90)}
    grid["min_distinct_durations"] = {str(x): sum(1 for r in rows if r["distinct_durations"] >= x) / len(rows)
                                      for x in (3, 4, 5, 6, 7)}
    grid["ties_min_abs"] = {str(x): sum(1 for r in rows if r["ties"] >= x) / len(rows)
                            for x in (2, 3, 5, 8, 10, 14)}
    grid["ties_per_10_bars_min"] = {str(x): sum(1 for r in rows if r["ties_per_10_bars"] >= x) / len(rows)
                                    for x in (0.2, 0.3, 0.5, 0.6, 0.7, 1.0)}
    grid["silence_share_min"] = {str(x): sum(1 for r in rows if r["silence_share"] >= x) / len(rows)
                                 for x in (0.20, 0.25, 0.30, 0.35)}
    summary["threshold_grid"] = grid

    # A6 on the pure-4/4 subset
    pure44 = [r for r in rows if r["header_meter"] == "4/4" and len(r["meter_sequence"]) == 1
              and r["meter_sequence"][0] == "4/4" and r["audio_duration_s"]]
    pred = []
    for r in pure44:
        predicted = round(r["audio_duration_s"] * r["tempo"] / 240)
        pred.append({"track_id": r["track_id"], "actual": r["bars"],
                     "predicted_from_audio": predicted,
                     "error": predicted - r["bars"],
                     "rel_error": (predicted - r["bars"]) / r["bars"]})
    summary["A6_pure44"] = {
        "n": len(pred),
        "error": band([p["error"] for p in pred]),
        "abs_error": band([abs(p["error"]) for p in pred]),
        "rel_error": band([p["rel_error"] for p in pred]),
        "within_10pct": sum(1 for p in pred if abs(p["rel_error"]) <= 0.10) / len(pred) if pred else None,
        "within_5pct": sum(1 for p in pred if abs(p["rel_error"]) <= 0.05) / len(pred) if pred else None,
    }

    # A-set verdicts by subgroup
    summary["A_audio_over_cap_p5_p95"] = {
        "n": len(vals("audio_over_cap")),
        "p5": band(vals("audio_over_cap")).get("p5"),
        "median": band(vals("audio_over_cap")).get("median"),
        "p95": band(vals("audio_over_cap")).get("p95"),
        "coverage": (sum(1 for r in rows if r.get("cap_covers_audio")) /
                     sum(1 for r in rows if r.get("cap_covers_audio") is not None)),
    }
    # lines per track and syllables per line
    line_counts = [r["lyric_lines"] for r in rows]
    summary["lyric_lines_min"] = min(line_counts) if line_counts else None
    summary["lyric_lines_max"] = max(line_counts) if line_counts else None
    summary["tracks_under_12_lines"] = sum(1 for n in line_counts if n < 12)
    summary["tracks_under_9_lines"] = sum(1 for n in line_counts if n < 9)

    # per-track output
    with (args.out / "tracks.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    # short console report
    print(f"tracks {len(rows)}  errors {len(errors)}")
    for k in ("notes_per_syllable", "register_mean", "register_top", "duration_spread",
              "duration_variety", "ties", "ties_per_10", "fill_length", "ins_activity",
              "chords_abs", "chords_per_bar_0.5", "chords_per_bar_1.0", "cadence",
              "final_rest", "simultaneity_zero", "simultaneity_le4", "silence_warn"):
        g = gate_pass.get(k)
        if g:
            print(f"  {k:<22} {g['pass']:>3}/{g['n']:<3}  {g['rate']:.0%}")
    sg = summary["sanity_gate_set"]
    se = summary["sanity_extended"]
    print(f"sanity core (6): {sg['pass']}/{sg['n']} ({sg['rate']:.1%}) meets95={sg['meets_95']}")
    print(f"sanity extended (8): {se['pass']}/{se['n']} ({se['rate']:.1%}) meets95={se['meets_95']}")
    print(f"current defaults: {summary['current_defaults']['pass']}/{len(rows)} "
          f"({summary['current_defaults']['rate']:.1%}); "
          f"with chords {summary['current_defaults']['with_chords']}")
    b = summary["audio_over_cap"]
    print("audio/cap", b)
    print("units16/syll total", summary["units16_per_syllable_total"])
    print("A6 pure44", summary["A6_pure44"])
    print("meters", summary["meters_seen"])
    print("tracks with meter changes", summary["tracks_with_meter_changes"],
          "multi-meter", summary["tracks_multi_meter"])
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
