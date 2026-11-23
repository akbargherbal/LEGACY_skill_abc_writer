---
name: maqam-score
description: >-
  Compose a NEW ABC score from Arabic lyrics and an arabmaqamrock style prompt:
  a small, declared set of deviations from the LoRA's own default arrangement.
  Ships its own syllabifier and checker, so it runs offline in two commands.
  Use when asked to write, compose, generate or design a score, melody, or ABC
  file from lyrics and a style. Do NOT use for editing an existing SheetSage2
  transcription — that is `maqam-edit`.
---

# maqam-score — composing a score from scratch

You are writing a **complete two-voice score** for a LoRA that already knows this
genre and performs competently on its own. The score is not a sketch and not a
list of gestures: it is the full vocal line plus the guitar part, bar by bar.
**Then** you declare three or four deliberate deviations from what the LoRA would
do without it. The deviations are the only intentional changes; the arrangement
around them is still a real arrangement.

The tools are bundled. You do not write a parser, a builder, a renderer, or a
syllabifier, and you do not install anything. **Run the scripts; do not read
them.** This file and `references/reference.md` are the interface.

```
<skill>/scripts/syllabify.py       lyrics -> numbers (letters, syllables, bars)
<skill>/scripts/checker.py         score + plan -> PASS/WARN/FAIL + the measured block
<skill>/scripts/calibration.json   the 177-track thresholds (do not edit)
<skill>/scripts/abc_tools.py       vendored runtime parser (the renderer's contract)
<skill>/scripts/selftest.sh        proves both work on example/ (run once if in doubt)
<skill>/example/                   a passing 16-bar score with the shape to copy
```

`<skill>` is the directory holding this file. Run the scripts by absolute path;
write `plan.json`, `score.abc` and the reports in your working directory.

**Gate classes.** The checker has three:

- **contract** — the renderer's rules: dialect, header, complete bars, voices,
  and plan/score agreement. Always hard.
- **sanity** — six broad degeneracy guards calibrated on the 177-track corpus:
  simultaneity, register mean, duration spread, duration variety,
  notes per syllable, and Ins presence. Always hard. They pass **175/177
  (98.9%)**, because they are wide enough to describe the corpus, not a taste.
- **style** — melisma band, high register, Ins density, tie count, chords,
  cadence, sections, silence, answer mutation, chorus lift. **Warn by default.**
  `--strict-style` turns them into failures if you want that.

The final rest warns by default; pass `--require-final-rest` before rendering.
A style number that fails more than 5% of good scores is a **warning or a
prior**, never a hard gate. The calibration lives in
`scripts/calibration.json`; do not invent thresholds.

Every threshold is registered with its `class`, `basis`, `n`, and pass rate in
**`references/numbers.md`**. If you change a number, change that registry and
`scripts/calibration.json` together.

## 1. The gate

You need four things:

1. **Lyrics, vocalised** — the harakat carry the count. Stripped lyrics cannot be
   counted; stop and say so.
2. **The style block** for this run.
3. **The maqam** (and the key you will write in).
4. **The lyrics file path**, for the duration cap.

If one is missing, stop and name it. Do not reconstruct it and do not guess a
key, a tempo or a maqam.

**Mode.** You are in **offline mode** unless you can actually run the renderer
(`generate.py` with the LoRA on a GPU) and listen to the result. Offline means:
priors from `references/reference.md`, no baseline render, no listening claim, no installing
`abcmidi`/`abcm2ps`, no rendering PNGs, no web search. Say "offline" in the
report. Never claim an audition that did not happen.

## 2. The baseline you deviate from

| Default behaviour | Why |
|---|---|
| answers every sung line | fixed answer rate |
| reuses one answer shape | no mutation |
| keeps density flat | no curve |
| keeps the second voice present throughout | no priority |
| builds by adding layers | conventional build |

This table is a **hypothesis** until a bare render is measured. Offline, it is
still the prior you design against — but write "prior, unmeasured" in the report.
`references/reference.md` §7 holds the measured cases; they show what good takes did, not
what the default is.

### 2.1 What a complete score contains

The **177-track corpus** is the shape reference. The numbers below are
distributions, not targets. Only the six `sanity` guards are hard; everything
else is a warning or a prior.

| Property | Corpus (n=177) | Gate |
|---|---|---|
| vocal mean MIDI | 71.7–75.1 (median 73.5) | **sanity 74 ± 5** |
| vocal top | 81–86 (median 84) | style floor 80; target 82–85 |
| notes per syllable | 1.12–1.44 (median 1.28) | **sanity 1.0–1.55** |
| most common duration | 50.5–75.6% (median 61.4%) | **sanity ≤ 85%** |
| distinct durations | 5–9 (median 7) | **sanity ≥ 4** |
| ties per 10 bars | 0.23–2.31 (median 1.07) | style; plan target |
| Ins active bars | 14.1–41.2% (median 25.3%) | **sanity ≥ 5%** |
| answer length | floor 3; answers can run long | style |
| chord symbols | no chords in the 177 ABCs | style / optional |
| final rest | 92.1% | warn; `--require-final-rest` before render |

The six sanity guards pass **175/177 (98.9%)**. A number that fails more than 5%
of good scores is a warning or a prior, not a gate. A declared deviation may
leave a style range; it may not fail a sanity guard.

The 177 are SheetSage2 transcripts of Suno renders, not human compositions.
They describe **what the model rendered**, not what a score must be. The five
`p01`–`p05` takes in `references/reference.md` came from an older pipeline
(p02 is a YuE2 render); they are a case study, not the corpus norm.

Who owns what — do not fight another row:

| Layer | Owns |
|---|---|
| Prompt | idiom, genre, mood, production words |
| LoRA | mix, timbre, arrangement, harmonies, choir, performance |
| Score | structure, prosody, gaps, density, register, repetition |
| Listener | whether it is beautiful |

Density is yours; balance is not. Never write a busy part to "fix" the mix — the
score can only avoid causing the problem.

## 3. The pipeline — one pass

### 3.1 Numbers

```bash
python3 <skill>/scripts/syllabify.py <lyrics> --tempo <Q> --json prosody.json
```

It prints letters, syllables (marks), the duration cap and token cap, the bar
budget, the section table, and syllables per line. Copy those numbers; do not
recount by hand. If it exits 1, the lyrics need more bars than the duration
allows — raise the tempo or cut lines, do not compress the syllables. Pass
`--duration` when a render length is known, or `--bars` when the length is
already decided.

The defaults come from `calibration.json`, not from one case: **tempo 80 BPM**
(with a warning — pass `--tempo` when the render is known), **pace 2.8
sixteenths per sung syllable** (corpus median 2.84), and **cap ratio 0.884**
(corpus median `audio/cap`). The old 73 BPM / 2.29 / 0.87 were a single-case
prior; they compressed the vocal.

### 3.2 Plan — one JSON file

Write `plan.json`. This is the brief; every value is a number or a name. The
checker fails a plan that omits a required target, so write the complete object
before the first bar.

```json
{
  "key": "Dm", "tempo": 73, "meter": "4/4", "unit": "1/16",
  "bars": 74,
  "syllables": 361,
  "sections": ["intro", "verse 1", "chorus", "verse 2", "chorus", "outro"],
  "simultaneity_exception": null,
  "cadence": "any",
  "melisma_min": 1.10,
  "melisma_max": 1.45,
  "register": {"mean": 74, "top": 82, "tolerance": 5},
  "max_top_duration_share": 0.85,
  "min_distinct_durations": 4,
  "ties_min": 3,
  "min_fill_notes": 3,
  "ins_active_share_min": 0.15,
  "chords_min": 0,
  "deviations": [
    {"bars": "9-32", "channel": "gap rate", "before": "an answer after every line", "after": "answers thin from 5/6 to 1/2, then stop"},
    {"bars": "33-44", "channel": "density", "before": "guitar present throughout", "after": "Ins rests through the first chorus"},
    {"bars": "45-60", "channel": "section register", "before": "verse level", "after": "verse 2 drops a fourth and stays there"},
    {"bars": "61-74", "channel": "repetition rate", "before": "the hook returns", "after": "voice stops; the guitar closes alone"}
  ]
}
```

- `sections` in order, with repeats. Names are **normalized** (`Verse 1` →
  `verse`); the score may have extra instrumental sections (`interlude`,
  `intro`, `outro`) that the lyrics do not. Sections warn by default; keep the
  plan honest, but do not invent a section to satisfy a string match.
- `deviations`: **3–4**, from the high-bandwidth channels only (`references/reference.md`
  §6). Position by bar. "At the chorus" is not a position. Keep `before`/`after`
  qualitative unless the number is already in `MEASURED`; a plan that claims
  "3/10" while the checker measures "4/4" is a false brief.
- `simultaneity_exception`: `null`, or one bar number you spend deliberately
  (≤ 4 sixteenths, one short note). The sanity guard allows at most 4
  overlapping sixteenths in total.
- `melisma_min` / `melisma_max`: notes per syllable band. The corpus runs
  **1.12–1.44** (median 1.28); use **1.10–1.45** as a broad band. 1.26 is a
  center, not a target; 1.0 is only for a deliberately syllabic line. Ties do
  not count as extra notes. This is a **style** target: it warns by default.
- `register`: the verse mean and the highest note the take should reach. The
  corpus mean is 73.5 and the top median is 84. Use `{"mean": 74, "top": 82,
  "tolerance": 5}`; 85 is a stretch, not a default.
- `max_top_duration_share`: the corpus median is 61% and P95 is 76%. The sanity
  ceiling is **0.85**; 0.78 is a style target. Do not write 90% one duration.
- `min_distinct_durations`: the sanity floor is **4**; 5 is a style target.
  Values come from `1,2,3,4,6,8,12,16,24,32,48`.
- `ties_min`: the sanity floor is **1**; 0 is valid for a syllabic style. A
  style target for a 74-bar score is **3** (`round(0.4 × bars / 10)`); the
  corpus median is 1.07 per 10 bars.
- `min_fill_notes`: the shortest guitar answer. Use 3; answers can run much
  longer than 8 (the 3–8 upper bound is not measured). A two-note tag is still
  a tag, not an answer.
- `ins_active_share_min`: the sanity floor is **5%**; 15% is a style target and
  25% is the corpus median. Do not force the guitar through the whole score.
- `chords_min`: **0 by default**. The 177 ABCs carry no chord symbols. If you
  want a harmony line, declare about 1.0 per bar and write it; otherwise leave
  harmony to the LoRA.
- `cadence`: `"any"` by default. If you deliberately want the final vocal note
  on the tonic, write `"tonic"`; then it becomes a hard check you chose.

Two or three answer shapes, each mutating; a rate that rises, falls, and partly
returns; the guitar owns the intro/interlude/outro outright. That plan lives in
the bars, not in prose.

### 3.3 Material — six decisions, before a pitch

- **Maqam and cadence figure.** The phrase that says "this maqam", used once or
  twice, entered and left by step.
- **Two or three motifs.** The vocal's cells, 3–6 notes each; every phrase
  derives from one. Write each with the transformation you will use.
- **Register.** From a bare render; offline, the `references/reference.md` §7 prior,
  labelled unmeasured. The corpus verse mean is **71.7–75.1 MIDI** (median 73.5)
  and the top is **81–86** (median 84). Use 74 mean and 82–85 top; 88 is a
  stretch, not a default. Put the chorus inside the same ceiling and do not
  write the verse an octave below it.
- **Cadence note.** The tonic at each phrase end; the final vocal note is the
  tonic (the checker enforces only the last one).
- **Rhythm profile.** A sung phrase is not a row of eighth notes. Mix sixteenths
  and eighths, repeat a note, hold a long note at the phrase end, and tie it
  when it crosses a beat. Every phrase needs one gesture from the rhythm list:
  a repeated cell, a long note, a tie, or a short rest inside the phrase.
  If you can sing it as "one, two, three, four" in every bar, it is a scale,
  not a melody.
- **Answer shapes.** Two or three, 3–8 notes each, each a transformation of the
  last. The guitar owns the intro/interlude/outro outright; in the chorus it may
  become a low bed instead of an answer. A two-note tag at the barline is not
  an answer.

The checker cannot see motifs, so do not claim it did. If a motif carries an
answer shape, name that shape in the deviation list.

### 3.4 Write `score.abc`

Write the ABC directly. Do not generate it with a script and do not build one.

The dialect is fixed by the runtime parser (`abc_tools.py`). Header, exactly:

```abc
X:1
T:
M:4/4
L:1/16
Q:1/4=73
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
% intro
V: Vocal
Z4|
V: Ins
z8 D2 E2 F2 E2|D8-D4 z4|z4 G2 F2 E2 D2 z4|D2 E2 F2 G2 A4 G4|
```

Rules that save a repair pass:

- **No blank lines anywhere in the body.** The runtime parser treats a blank
  line as the end of the tune. The checker runs the vendored parser before it
  measures anything; a blank line is a hard FAIL, not a warning.
- `% section` goes **before** the `V: Vocal` block, with a space after the
  percent (`% intro`). A `%` inside a block is an annotation and is ignored.
- Blocks alternate `V: Vocal`, `V: Ins`, each 1–4 bars, music line ending in `|`.
  Both blocks in a pair have the same bar count. Do not insert blank lines
  between pairs.
- **Meter changes are allowed.** `M:2/4` may appear after `V:` and before the
  music line; `[K:...]` may appear inside a bar. The corpus uses nine meters and
  121/177 scores change meter; the checker parses per-bar meter instead of
  rejecting it.
- **End with silence.** The final bar should be a full-bar rest in both voices
  (`Z|`), after the final cadence. The last music line still ends with a plain
  `|`. Do **not** use `]`: the runtime parser rejects it. The checker **warns**
  on a missing final rest by default; pass `--require-final-rest` before
  rendering to make it a render contract. The final rest is the only clean
  place for the renderer/cap to stop.
- Durations are only `1,2,3,4,6,8,12,16,24,32,48` L-units. A 10-sixteenth rest
  is `z8z2`, not `z10`; a 5-sixteenth note is `3-2` tied, not `5`. No dots.
- Every bar sums to its meter: 16 L-units at L:1/16 in 4/4, 8 in 2/4, 6 in
  3/8. Count rests, not just notes.
- `Z` / `Z2`–`Z4` are whole-bar rests and must be the **whole** bar; `z16` is a
  rest inside one bar. Do not mix `Z` with notes in the same bar.
- Chord symbols (`"Dm"`) only in Vocal. They are optional: the 177 ABCs carry
  none, so `chords_min` defaults to 0. Declare about 1.0 per bar only if you
  deliberately want a harmony line.
- **No `w:` lines.** The score carries no lyrics; the renderer takes them
  separately. No tuplets, no `[...]` chords, no microtonal `^/2`.
- A tie must join the same pitch and stay inside one syllable — in practice, the
  long note at a line end. Every tie is one written note.

### 3.5 Check

```bash
python3 <skill>/scripts/checker.py score.abc --plan plan.json --json report.json --require-final-rest
```

Exit 0 means no **hard** check failed; `WARN` lines are style diagnostics and
do not fail. Add `--strict-style` only if you want style targets to fail too.
The checker runs the vendored runtime parser first; if it prints
`FAIL runtime parse`, the renderer cannot read the file at all — fix the dialect
(usually a blank line, a header line, or a tie), not the checker.

On a sanity `FAIL`, fix **only** the bars named, then run it once more. No other
edits. If a style warning matters for the brief, write the missing music or
declare the deviation; do not lower a sanity threshold. If a check can only be
satisfied by changing the plan, change the plan and say so; never fake a number.

## 4. What the checks mean

**Contract — the file is unusable or the brief is empty (always FAIL):**

- `runtime parse`: the vendored `abc_tools.parse` accepts the file. A blank
  line, a wrong header, a mixed `Z` bar, or a bad tie fails here.
- exact dialect and headers, complete bars, both voices with equal length;
- key, tempo, meter, unit, and bars agree with the plan;
- a complete plan: every target key present;
- **final rest**: only with `--require-final-rest` (before rendering). Without
  the flag it is a style warning.

**Sanity — six broad degeneracy guards (always FAIL; pass 175/177):**

- at most 4 overlapping sixteenths between the two voices;
- vocal mean within 74 ± 5 MIDI;
- no single duration is more than 85% of the vocal notes;
- at least 4 distinct vocal durations;
- notes per syllable between 1.0 and 1.55;
- the Ins sounds in at least 5% of the bars.

These catch an octave error, a monotone rhythm, a missing second voice, or a
score that is not in the corpus universe. They do **not** prescribe a style.

**Style — WARN by default; `--strict-style` makes them FAIL:**

- the plan's melisma band, register mean/top, duration spread, duration
  variety, ties, answer fill, Ins activity, chords, and sections;
- cadence: a warning unless the plan declares `"cadence": "tonic"`; that one is
  a self-imposed hard target;
- silence, answer mutation, chorus lift, deviations.

**Listening is the only aesthetic gate, and it needs audio.** The sanity guards
ask "is this a score in the same universe?"; the style warnings ask "is it the
brief you declared?" Neither is a verdict on beauty. Offline, say so.

## 5. Report

`CHANGES.txt` = the plan's deviation list plus the checker's `MEASURED` block,
copied verbatim. `report.json` is the `--json` output. Never retype a number.
The measured block includes `register_mean`, `register_top`, `register_range`,
`top_duration_share`, `distinct_durations`, `ties`, `fill_lengths`,
`ins_active_share`, `chords`, and a `percentiles` line that places each value in
the 177-track distribution. Quote them; do not restate them from memory. Every
check also carries its `class` (`contract`, `sanity`, `style`).

If a measured value leaves the reference range, write the reason in the file.
A silent overrun is a defect; a declared one is a decision.

The checker cannot see motifs, orchestration, timbre, or harmony that is not
written as chord symbols. Do not claim it measured them; the 177 ABCs carry no
chords at all. See `references/reference.md` §9 for the boundary.

## 6. Traps

- Building a parser, a syllabifier, or a renderer. They are in `scripts/`.
- Installing an ABC toolchain or rendering sheet images to "look" at the score.
- Writing before the plan, then rationalising the bars against it.
- **Writing a skeleton that passes the counts.** One note per syllable, the
  guitar on whole-bar rests, two-note answers, no ties, no chords: every bar can
  add up and the result is not a score. The sanity guards and style warnings
  exist for this.
- **Copying the example as a template.** It is a 16-bar shape, not a melody.
  Copy the shape (intro/verse/chorus/outro, answers in the rests, a tied
  cadence), never the pitches.
- **Writing a scale.** `D2 F2 G2 A2 B2 A2 G2 F2` in every bar is a finger
  exercise. Start from a 3–6 note motif, repeat notes, hold a long note, and
  mutate the cell.
- **A blank line in the body.** The runtime parser ends the tune there; the
  renderer never sees the rest.
- **Ending on a note with no final rest.** The cap then has no clean place to
  cut, and the model keeps filling. Close the score with `Z|` in both voices,
  and pass `--require-final-rest` before rendering.
- **Lowering a sanity threshold to pass.** The sanity guards are corpus-wide
  floors. If the score misses one, write the missing music. Style targets are
  the brief: fix them or declare the deviation; do not edit the calibration.
- Deviating everywhere, or on a low-bandwidth channel (one note in a phrase) and
  waiting to hear a difference.
- A busy second voice under the vocal, then blaming the mix.
- Tying across a word boundary — the consonant lives in the transition.
- Counting bars or notes by hand and reporting the hand count.
- Claiming a listening result that was never heard.

## 7. Cost

One `syllabify` run, one plan, one score, one check, at most one repair. If you
are past that, the plan was wrong — go back to 3.2, not to the parser.
