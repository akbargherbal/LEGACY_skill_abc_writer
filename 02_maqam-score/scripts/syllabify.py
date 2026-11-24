#!/usr/bin/env python3
"""Count lyrics and turn them into the numbers a score plan needs.

One job: given the lyrics file (optionally with the style line on top), print
the letter count, the duration cap, the tempo-derived bar budget, the section
table and the syllables per line. No scansion, no transliteration, no guessing.

Syllable rule (same convention as `check_abc.py:lyric_stats`):
    one syllable = one vowel mark (fatha, damma, kasra, tanwin, dagger alif).
    A long vowel (ا و ي) extends a nucleus; it does not start a new one.
    Shadda is gemination, not a syllable.
This assumes the text is vocalised, which is the skill's input gate. If a line
is off by one from the median, that is a variant -- report it, do not scan the
poem (see references/reference.md §3).

Usage:
    python3 syllabify.py lyrics.md
    python3 syllabify.py lyrics.md --tempo 73 --json prosody.json
    python3 syllabify.py lyrics.md --duration 262.15   # known render length
    python3 syllabify.py lyrics.md --phrases phrases.json \\
        --sections "intro=7,verse 1=13,chorus=37,verse 2=46,chorus=65,outro=77"
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata
from pathlib import Path

VOWEL_MARKS = "\u064e\u064f\u0650\u064b\u064c\u064d\u0670"

# duration_cap.py (canonical): q=0.95 fit, token cap = rounded_10s * 25
DUR_CAP_A, DUR_CAP_B = 111.1, 0.3126
SECONDS_PER_LETTER_TOKENS = 25
# Corpus medians over the 177 five_stars scores (2026-11-23):
#   audio / cap = 0.884, and 2.84 sixteenths per sung syllable.
# These are central priors, not rules; pass --duration or --bars when known.
CASE_RATIO = 0.884
PACE = 2.8
TEMPO_DEFAULT = 80
DEFAULT_CALIBRATION = Path(__file__).resolve().parent / "calibration.json"


def arabic_letters(text: str) -> int:
    """Letters only: Lo in the Arabic block. Harakat are Mn and do not count."""
    return sum(
        1 for c in text
        if 0x0600 <= ord(c) <= 0x06FF and unicodedata.category(c) == "Lo"
    )


def syllables(text: str) -> int:
    return sum(1 for c in text if c in VOWEL_MARKS)


def norm_section(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def parse_section_starts(spec: str) -> list[tuple[str, int]]:
    """Parse ``intro=7,verse 1=13,chorus=37,...`` into ordered starts.

    A repeated section name is consumed in order, so the first ``chorus`` entry
    belongs to the first chorus and the second to the second chorus.
    """
    starts: list[tuple[str, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"expected section=bar, got {part!r}")
        name, bar = part.split("=", 1)
        name = norm_section(name)
        if not name:
            raise ValueError(f"empty section name in {part!r}")
        try:
            bar = int(bar.strip())
        except ValueError as exc:
            raise ValueError(f"bar must be an integer in {part!r}") from exc
        if bar < 1:
            raise ValueError(f"bar must be >= 1 in {part!r}")
        starts.append((name, bar))
    if not starts:
        raise ValueError("no section starts given")
    return starts


def apply_section_starts(
    line_rows: list[dict], starts: list[tuple[str, int]]
) -> None:
    """Add absolute ``bar_start``/``bar_end`` from ordered section starts.

    The body bars are global (1..body_bars). A section start is the absolute
    bar of that section's first sung line; the offset is applied to every line
    in the section. This keeps the section layout a musical decision while the
    arithmetic stays in the tool.
    """
    groups: list[tuple[str, list[dict]]] = []
    for row in line_rows:
        if not groups or groups[-1][0] != row["section"]:
            groups.append((row["section"], [row]))
        else:
            groups[-1][1].append(row)
    if len(starts) != len(groups):
        names = ", ".join(f"{name}@{bar}" for name, bar in starts)
        got = ", ".join(name for name, _ in groups)
        raise ValueError(
            f"--sections has {len(starts)} entries ({names}) but the lyrics "
            f"have {len(groups)} sung section(s): {got}"
        )
    previous_end = 0
    for (name, rows), (expected, absolute_start) in zip(groups, starts):
        if name != expected:
            raise ValueError(
                f"--sections order mismatch: expected {name!r}, got {expected!r}"
            )
        if absolute_start <= previous_end:
            raise ValueError(
                f"section {name!r} starts at bar {absolute_start}, "
                f"but the previous section ends at {previous_end}"
            )
        offset = absolute_start - rows[0]["body_bar_start"]
        for row in rows:
            row["bar_start"] = row["body_bar_start"] + offset
            row["bar_end"] = row["body_bar_end"] + offset
        previous_end = rows[-1]["bar_end"]


def load_calibration(path: Path | None) -> dict:
    p = Path(path) if path else DEFAULT_CALIBRATION
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}


def parse_lyrics(text: str) -> tuple[list[dict], list[str]]:
    """Split into lyric lines under their section tags.

    A line is a lyric line when it contains Arabic letters. Bracketed lines are
    section tags; anything else (the style paragraph) is ignored and reported.
    """
    sections: list[dict] = [{"name": "score", "lines": []}]
    ignored: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            name = norm_section(line[1:-1].split("|")[0])
            sections.append({"name": name, "lines": []})
            continue
        if not arabic_letters(line):
            ignored.append(line[:60])
            continue
        sections[-1]["lines"].append(line)
    # A section tag with no lyric lines is an instrumental section: keep it so
    # the plan can name it, but it contributes no lines or bars.
    return [s for s in sections if s["lines"] or s["name"] != "score"], ignored


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lyrics", type=Path)
    ap.add_argument("--tempo", type=float, default=None,
                    help="quarter-note BPM; default 80 from calibration.json (a warning)")
    ap.add_argument("--meter", default="4/4")
    ap.add_argument("--unit", default="1/16", help="ABC L: unit, e.g. 1/16")
    ap.add_argument("--duration", type=float, default=None,
                    help="known sung duration in seconds; overrides the prior")
    ap.add_argument("--bars", type=int, default=None,
                    help="explicit bar count; overrides every duration estimate")
    ap.add_argument("--calibration", type=Path, default=None,
                    help="calibration.json (default: next to this script)")
    ap.add_argument("--json", type=Path, default=None, help="write prosody JSON here")
    ap.add_argument("--phrases", type=Path, default=None,
                    help="write the per-line phrase sidecar here")
    ap.add_argument("--sections", "--layout", dest="sections", default=None,
                    help="comma-separated section=absolute_bar starts in lyric "
                         "section order (e.g. 'verse 1=13,chorus=37,chorus=65'); "
                         "writes absolute bar_start/bar_end. Repeat a section "
                         "name for repeats.")
    args = ap.parse_args(argv)

    text = args.lyrics.read_text(encoding="utf-8")
    sections, ignored = parse_lyrics(text)
    if not sections or not any(s["lines"] for s in sections):
        print("FAIL  no Arabic lyric lines found", file=sys.stderr)
        return 2
    if ignored:
        print(f"(ignored {len(ignored)} non-lyric line(s), e.g. {ignored[0]!r})")

    cal = load_calibration(args.calibration)
    defaults = cal.get("style_defaults", {})
    tempo_given = args.tempo is not None
    tempo = args.tempo if tempo_given else float(defaults.get("tempo_default", TEMPO_DEFAULT))
    if not tempo_given:
        print(f"(tempo not given: using {tempo:g} BPM from calibration; pass --tempo when the render is known)")
    case_ratio = float(defaults.get("case_ratio", CASE_RATIO))
    pace = float(defaults.get("pace", PACE))
    meter_num, meter_den = (int(x) for x in args.meter.split("/"))
    # `pace` is in sixteenths per syllable, independent of the L: unit.
    # A bar has 16 * n/d sixteenths (16 in 4/4, 8 in 2/4, 6 in 3/8).
    sixteenths_per_bar = 16 * meter_num / meter_den
    seconds_per_bar = (4 * meter_num / meter_den) * 60 / tempo

    lines = [line for sec in sections for line in sec["lines"]]
    letters = arabic_letters(text)
    words = sum(len(re.findall(r"[\u0600-\u06FF]+", line)) for line in lines)
    sylls = [syllables(line) for line in lines]
    total_syll = sum(sylls)
    if total_syll == 0:
        print("FAIL  no vowel marks (harakat) found in lyrics: stripped text cannot be counted", file=sys.stderr)
        return 1
    median_syll = statistics.median(sylls)
    ordered = sorted(sylls)
    p25_syll = ordered[max(0, int(0.25 * (len(ordered) - 1)))]
    p75_syll = ordered[min(len(ordered) - 1, int(0.75 * (len(ordered) - 1)))]

    cap = DUR_CAP_A + DUR_CAP_B * letters
    cap_10 = round(cap / 10) * 10
    tokens = int(round(cap_10 * SECONDS_PER_LETTER_TOKENS))

    if args.duration is not None:
        duration, source = args.duration, "--duration"
    elif args.bars is not None:
        duration, source = args.bars * seconds_per_bar, "--bars"
    else:
        duration, source = cap * case_ratio, f"prior: {case_ratio:.3f} x cap (corpus median)"

    bars = args.bars or round(duration / seconds_per_bar)
    bars_cap = round(cap / seconds_per_bar)

    # Corpus median: 2.84 sixteenths per sung syllable (2.8 after rounding).
    # Round to whole bars, at least one per line; longer lines get more bars
    # rather than being silently compressed.
    per_line_bars = [max(1, round(n * pace / sixteenths_per_bar)) for n in sylls]
    body_bars = sum(per_line_bars)
    instrumental = bars - body_bars

    # Per-line phrase plan: the lines are hemistichs in the source lyrics.
    # The first line of a pair gets a short breath; the second (bayt end) gets
    # a longer one. These are minimums, not a transcription of the score.
    line_sections = [sec["name"] for sec in sections for _ in sec["lines"]]
    line_rows: list[dict] = []
    section_seen: dict[str, int] = {}
    body_start = 1
    for i, (n, b, section) in enumerate(
            zip(sylls, per_line_bars, line_sections), 1):
        pair_index = section_seen.get(section, 0)
        section_seen[section] = pair_index + 1
        line_rows.append({
            "line": i,
            "section": section,
            "syllables": n,
            "bars": b,
            "body_bar_start": body_start,
            "body_bar_end": body_start + b - 1,
            "pause_after_s": 0.5 if pair_index % 2 == 0 else 1.0,
        })
        body_start += b

    absolute_sections = False
    if args.sections:
        try:
            starts = parse_section_starts(args.sections)
            apply_section_starts(line_rows, starts)
        except ValueError as exc:
            print(f"FAIL  --sections: {exc}", file=sys.stderr)
            return 2
        absolute_sections = True

    print("INPUTS")
    print(f"  lines            {len(lines)}")
    print(f"  words            {words}")
    print(f"  letters (Lo)     {letters}")
    print(f"  syllables        {total_syll}  (marks; median {median_syll}/line, "
          f"P25-P75 {p25_syll:g}-{p75_syll:g})")
    print(f"  duration cap     {cap:.1f}s -> {cap_10:.0f}s -> {tokens} tokens")
    print(f"  duration used    {duration:.1f}s  (from {source})")
    print(f"  tempo / meter    {tempo:g} BPM, {args.meter}, L:{args.unit}")
    print(f"  calibration      {cal.get('version', 'none')}  (pace {pace:.2f}, cap ratio {case_ratio:.3f})")
    print(f"  bars             {bars}  (cap-based {bars_cap}; 1 bar = {seconds_per_bar:.2f}s)")
    print(f"  body bars        {body_bars}  (sung bars; {total_syll} syllables)")
    print(f"  free bars        {instrumental}  (intro, interludes, outro, answer-only bars)")
    if instrumental < 0:
        print("FAIL  the lyrics need more bars than the duration allows: "
              "raise tempo or cut lines", file=sys.stderr)
        return 1

    print("\nSECTIONS")
    offset = 0
    for sec in sections:
        n_lines = len(sec["lines"])
        n_syll = sum(syllables(line) for line in sec["lines"])
        n_bars = sum(per_line_bars[offset:offset + n_lines])
        offset += n_lines
        print(f"  {sec['name']:<12} {n_lines:2d} lines  {n_syll:3d} syllables  {n_bars:3d} bars")

    print("\nLINES  syllables  bars  sixteenths/syllable  pause_s")
    for i, (line, n, b) in enumerate(zip(lines, sylls, per_line_bars), 1):
        flag = ""
        if n > p75_syll + 1:
            flag = "  <-- long line: consider more bars"
        elif n < p25_syll - 1:
            flag = "  <-- short line: consider fewer bars"
        pause = line_rows[i - 1]["pause_after_s"]
        if n == 0:
            print(f"  {i:2d}        0      {b}     N/A                  {pause:.2f}"
                  "  <-- line has no harakat")
        else:
            per = b * sixteenths_per_bar / n
            print(f"  {i:2d}      {n:3d}      {b}     {per:.2f}                "
                  f"{pause:.2f}{flag}")

    if instrumental < 6:
        print("\nwarn  fewer than 6 instrumental bars: the intro/outro have no room")

    if args.json:
        data = {
            "tempo": tempo,
            "tempo_source": "--tempo" if tempo_given else "calibration_default",
            "meter": args.meter,
            "unit": args.unit,
            "calibration_version": cal.get("version"),
            "pace": pace,
            "case_ratio": case_ratio,
            "seconds_per_bar": round(seconds_per_bar, 3),
            "sixteenths_per_bar": sixteenths_per_bar,
            "lines": len(lines),
            "words": words,
            "letters": letters,
            "syllables": total_syll,
            "syllables_p25": p25_syll,
            "syllables_p75": p75_syll,
            "syllables_per_line": sylls,
            "duration_cap_s": round(cap, 1),
            "duration_cap_rounded_s": cap_10,
            "token_cap": tokens,
            "duration_used_s": round(duration, 1),
            "duration_source": source,
            "bars": bars,
            "bars_from_cap": bars_cap,
            "body_bars": body_bars,
            "instrumental_bars": instrumental,
            "sections": [
                {"name": sec["name"], "lines": len(sec["lines"]),
                 "syllables": sum(syllables(l) for l in sec["lines"])}
                for sec in sections
            ],
            "prosody": [{"line": l, "syllables": n} for l, n in zip(lines, sylls)],
            "phrase_plan": {"body_bars": body_bars, "lines": line_rows},
        }
        args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        print(f"\nwrote {args.json}")
    if args.phrases:
        sidecar = {
            "tempo": tempo,
            "meter": args.meter,
            "unit": args.unit,
            "body_bars": body_bars,
            "lines": line_rows,
        }
        args.phrases.write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        if absolute_sections:
            print(f"\nwrote {args.phrases} (absolute bar_start/bar_end from --sections)")
        else:
            print(f"\nwrote {args.phrases} (body bars only; pass --sections "
                  "to write absolute bar_start/bar_end)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
