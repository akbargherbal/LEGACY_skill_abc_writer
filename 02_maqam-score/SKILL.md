---
name: abc-score-writer
version: "0.9.0"
description: >-
  Compose a NEW ABC score from Arabic lyrics and an arabmaqamrock style prompt:
  a small, declared set of deviations from the LoRA's own default arrangement.
  Ships its own scaffolder, line writer, linter, checker, corpus snapshot and
  phrase asset bank, so the composer writes one lyric line at a time and never
  sums a bar by hand.
  Use when asked to write, compose, generate or design a score, melody, or ABC
  file from lyrics and a style. Do NOT use for editing an existing SheetSage2
  transcription.
---

# abc-score-writer

You are writing a complete two-voice score for a LoRA that already knows this
genre. The tune is the work. The tools below own the file, the bars, the
arithmetic and the checks; you own the cell, the period, the cadence, the riff,
the sayr and the arc.

**The model writes notes. The CLI writes the file.** Do not write `score.abc`
directly, do not write a parser, and do not sum a bar in your head.

## Start here

The only input is the user's prompt plus `input/lyrics.txt` and
`input/style.md`. Load this skill, then run:

```bash
python3 <skill>/scripts/score_cli.py init --tempo 80 \
  --sections "intro=7,verse 1=13,chorus=37,verse 2=46,chorus=65,outro=77"
```

`init` runs `syllabify.py`, writes `prosody.json`, `phrases.json`, a complete
`plan.json` and a `score.abc` scaffold (both voices `Z`), and
`score_state.json`. Use `--bars N` when the form length is already decided.
`--sections` is the absolute start bar of each sung section, in lyric order;
repeat a name for a repeat. The numbers above are an example: derive your own
from the lyric, or omit `--sections` and let the tool allocate the form from
the body bars. Do not copy 7/13/37 onto a different lyric. If `init` prints
`FORM BUDGET`, decide before the first line: keep the compact form and accept
the warning, or rerun with `--force --bars N` **and** `--sections` to place the
extra bars; a bare `--bars` puts them all in the outro.

Then follow the one order:

```text
init → stock pass (optional, declared) → core (first 8-16 bars)
     → core_review.md → expand line by line → check at section ends
     → release → seed → seed_sheet.md / notes.md
```

## The one unit: a lyric line

A lyric line is 2-4 bars. Write it, check it, then the next line. Never plan or
write all 86 bars in one step.

```bash
python3 <skill>/scripts/score_cli.py line 1 \
  --vocal "z:2 D:4 F:2 G:2 | A:4 G:2 F:2 z:2 | _E:8 D:4 z:4" \
  --ins   "Z|Z|Z"
```

- `|` separates bars. The number of bars must equal the line's
  `bar_start..bar_end` in `phrases.json` (the command prints it).
- `pitch:dur` is accepted (`D:4`), as is plain ABC (`D4`). Durations are
  `1,2,3,4,6,8,12,16,24,32,48`; no dots, no tuplets, no `[...]`.
- **The CLI pads the bar tail with rests.** You do not need the sum to be 16.
  Write the notes you want; the tool fills the breath. If you want a note to
  fill the bar, write its exact duration. A tie at the bar end cannot be
  padded, so close it inside the line.
- The command validates the whole file (all bars, both voices) before writing.
  A bad bar is rejected and nothing is changed.
- `--ins` defaults to rests. The guitar answers in the vocal's gaps; a whole
  bar of `Z` is a legitimate floor, not a part.

`patch B --vocal ... --ins ...` replaces one bar atomically. Use it for a
named fix; do not rewrite the score.

### The meter is part of the write

Every successful `line`/`patch` prints a four-line measurement block before the
write is committed:

```text
line 5 (bars 13-14): 10 notes / 13 syllables — deficit 3
score  75/80 notes → projected 271/361 (need 398-523)
       repeats 3%  durations 2:5 4:2 6:1 (3 of 5)  register 68.1  ties 0/1
       gap after 0.38s (target 0.50s)  overlaps 0 this line / 0 total (max 4)
```

Read it before the next line. A deficit means the line is short of its own
syllables: add passing notes, a repeated note, or a tie now, not at the gate. A
projection below `need` means the whole score is running short. A gap below
target means the breath is too small; add `z1` or a longer tail. An overlap
means the guitar is sounding under the voice too long; shorten or move it.
These are the same numbers the checker uses, printed at the decision.

- `line ... --dry-run` / `patch ... --dry-run` prints the padded bars and the
  meter and writes nothing.
- `--guard` refuses the write when a hard sanity rule is already broken: the
  current line has a deficit over 1, its gap is shorter than the target, the
  current line overlaps over the cap, or (on the last line) a whole-score sanity
  band is outside. Use it deliberately; it is off by default.
- `lint` also reports per-bar overlap, so the whole-file sum is visible before
  the full check.

### Stock pass (optional, declared)

Before the first line of a section, you may query the asset bank for a
rhythm/contour starting point:

```bash
python3 <skill>/scripts/asset_bank.py query \
  --role chorus --bars 2 --syllables 14 --contour up --limit 3
```

It returns 3–5 compact references, not a score. You still write the line with
`score_cli.py line`. If you use an asset, declare it in `loans.json` and run
`verify_loans.py`; no reason, no loan; no transform, no loan. If nothing fits,
compose. The query is optional; the line workflow is not. See
`references/assets.md`.

### Core first

Write the first 8-16 bars (the opening lines) with `line`. Then:

```bash
python3 <skill>/scripts/score_cli.py core --snapshot
# write core_review.md: exactly 5 numbered lines, one issue per line, tied to a bar
python3 <skill>/scripts/score_cli.py core --check
```

`line` refuses to expand beyond the core until `core_review.md` has five
numbered lines and the core is an exact prefix of the score. The core is the
first composition, not an extraction from a finished score.

The core uses the cell/period method in `references/craft.md`:

1. **Lyric as song.** Bayt, caesura, qāfiya, repeated line, pivot. Do not name a
   baḥr unless you scanned it.
2. **Cell.** 3-6 notes with a rhythm you can sing; one cell per section. It must
   contain a repeated note, a 4th/5th leap, or a distinctive rhythm.
3. **Period.** 2 bars antecedent ending open (5th, ♭6, 2nd); 2 bars consequent
   ending closed (tonic or 3rd). Same head, different tail.
4. **Transform.** Two or three of: sequence, inversion, truncation,
   augmentation, ornament, registral shift, fragmentation, displacement. Never
   transpose the whole verse.
5. **Cadence ladder.** Open on the 5th; ♭6/♭7 for colour; ♭3 rarely; tonic for
   the section close and the final qafla. Intermediate phrases end on resting
   tones, not the tonic.
6. **Melisma as an event.** Body 1.00-1.10 notes/syllable; 3-8 notes on chosen
   cadence syllables; overall 1.10-1.45. Do not add notes everywhere.
7. **Guitar as a part.** Two or three answer shapes, each a mutation; a 2-bar
   riff from the cell or a pedal; answers in the vocal gaps; owns the
   intro/interlude/solo/outro; changes texture at the chorus.
8. **Subtract for intensity.** Remove a layer before the chorus; let the voice
   drop for the solo; let the guitar drop for the last line. The chorus lifts
   the median about five semitones; it does not add notes.

Read `references/craft.md` before the core, `references/rhythm.md` before the
guitar and the seed, `references/critic.md` before the review, and
`references/assets.md` before the first declared stock pass. `references/plan.md`
is the one-page plan contract; `references/cli.md` is the command and
error-recovery reference. Do not read the scripts.

## The file contract

The CLI writes this header; do not retype it:

```abc
X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
```

- No blank lines anywhere in the body. A blank line ends the tune.
- Blocks alternate `V: Vocal`, `V: Ins`; a group has 1-4 bars and both voices
  have the same bar count. `score.abc` is two voices; drums go in `seed.abc`.
- `% section` goes before the `V: Vocal` block, with a space after `%`.
- `Z`/`Z2`-`Z4` are whole-bar rests and must fill the whole bar; `z16` is a
  rest inside one bar. Do not mix `Z` with notes.
- Every bar sums to its meter: 16 L-units in 4/4 at `L:1/16`, 8 in 2/4, 6 in
  3/8. The CLI pads, so you normally do not have to count.
- End with a full-bar rest in both voices (`Z`). The last music line still ends
  with a plain `|`; do not use `]`.
- No `w:` lines, no tuplets, no `[...]` chords, no microtonal `^/2`.
- A tie joins the same pitch inside one syllable; every tie is one written note.

## Plan

`init` writes a complete plan. `plan lint` explains what is missing;
`plan refresh` re-derives `arrangement.section_plan` and `ins_entries` from the
score; `plan set path=value` edits one value. The full field list and defaults
are in `references/plan.md`.

The plan is the brief, not a bar-by-bar design. It carries:

- `key` (a standard major/minor key; `K:Dphr` is a contract failure), `tempo`,
  `meter`, `unit`, `bars`, `syllables`, `sections` (in lyric order, repeats);
- `melisma_min/max` (1.10-1.45), `register` mean/top/max_top/tolerance,
  `tessitura_share_ge_c5_max` 0.80, `chorus_lift_min` 5,
  `max_top_duration_share` 0.65, `min_distinct_durations` 5, `ties_min` 1,
  `min_fill_notes` 3, `ins_active_share_min` 0.20, `chords_min` 0,
  `max_unbroken_seconds` 10, `min_phrase_endings` 3, `strict_shape` false;
- `maqam`: required when the prompt names one (`name`, `tonic`, `degrees`,
  `resting`). Kurd as `K:Dm` + `_E`; declare it or the chromatic count is wrong.
- `copies`: `[]` when every repeated section is newly composed; otherwise one
  `{"mode": "independent", "bars": "..."}` entry per by-ear-identical copy.
- `arrangement.section_plan`: ranges that tile 1..bars. `plan init` writes it;
  edit only the bands you mean to change.
- `deviations`: **3-4** from the high-bandwidth channels, positioned by bar
  (register, density, gap rate, answer shape, texture). Each carries either an
  `assert {metric, range, op, value}` or `unverifiable: true` with a real
  reason. `plan lint` fails while a placeholder remains.

## Checks

Before the first full check, run `plan refresh` so `arrangement.ins_entries`
and the section ranges describe the written score. Then run the checker at
section ends and at the end; do not run it after every bar.

```bash
python3 <skill>/scripts/score_cli.py check --bars 9-16     # section report
python3 <skill>/scripts/score_cli.py check                 # full, non-strict
python3 <skill>/scripts/score_cli.py release               # strict + final rest
```

`check --bars` reports bar sums, the per-line table, register, rest and cadence
for that range; it does not run the full gate. `check` runs `checker.py` and, on
a hard failure, prints the `repair.py` bar/phrase map. Fix only the named bars
with `patch`, then check once. `release` is strict-style plus final-rest; it is
the only run that should treat style warnings as failures. `release --dry-run`
prints the strict verdicts without changing `score_state.json`.

Three read-only tools answer the questions the numbers cannot:

```bash
python3 <skill>/scripts/score_cli.py explain-metric end     # what a metric means
python3 <skill>/scripts/score_cli.py align --lines 3-6      # syllable -> note (heuristic)
python3 <skill>/scripts/score_cli.py view --roll --bars 3-5 # ASCII piano roll
python3 <skill>/scripts/score_cli.py view --contour         # one line per phrase
```

`align` is positional: one note per syllable, surplus notes printed as a tail.
It shows where a melisma possibly lands; it cannot prove the word alignment.
`view` is for sight-reading contour and repeated cells, not for scoring.

The checker has four classes:

- **contract** — dialect, header, complete bars, voices, plan/score agreement.
  Always hard.
- **sanity** — nine broad degeneracy guards: simultaneity, register mean,
  duration spread, duration variety, notes per syllable, Ins presence,
  unbroken singing, repeated-pitch share, distinct phrase endings. Always hard.
- **structure** — the plan's declared shape: breath, duration mix, tessitura,
  register ceiling, chorus median lift, silence, maqam fit, phrase plan. Hard
  under `strict_shape`; otherwise a style warning. `cadence: "tonic"` is
  always hard.
- **style** — melisma band, high register, Ins density, ties, chords, sections,
  answer mutation, chorus max lift. Warnings unless `release`.

Stop after a pass. A global sanity failure allows one scoped rewrite and one
verification; a contract error after that is a named fix. Maximum four checker
runs. `repair.py` and `abc_doctor.py` exist; use them, do not read the checker
source. `explain` wraps the doctor:

```bash
python3 <skill>/scripts/score_cli.py explain
```

Quality is not a number. The checker proves the score is readable and inside the
corpus; it cannot tell you the tune is worth hearing. The craft mirror is a
diagnostic, not a gate:

```bash
python3 <skill>/scripts/craft.py score.abc --phrases phrases.json --json craft.json
```

It reports phrase-rhythm variety, unique bars, contour, cadence ladder,
end-long share and tessitura. Read it before `release`; if a line is a
metronome grid or the phrase rhythm is below the corpus P10, fix that line with
`patch` and say so. This is a declared quality decision, not a reason to add a
new gate.

## Seed and delivery

When the target is a cover model or the user asks for chords, instruments or
backing voices, deliver two files:

| File | What it is |
|---|---|
| `score.abc` | the two-voice source of truth; the only file the checker gates |
| `seed.abc` | free ABC: chords, `%%MIDI`, and a `V: Drums` voice |

Write and check `score.abc` first. Then:

```bash
python3 <skill>/scripts/score_cli.py seed
python3 <skill>/scripts/score_cli.py seed-check
```

`seed` copies the melody, adds one chord per Vocal bar, and writes a 2-bar
drum groove per section, a fill at a 4/8-bar group end, and silence for the
close. Edit the seed's orchestration; do not change the melody. `seed-check`
proves Vocal/Ins/Drums align bar-for-bar. The seed is not contract-checked;
say so in the report.

Write `seed_sheet.md` after `score.abc`, as exactly 10 numbered lines (frame,
cell, period rule, cadence rule, melisma rule, riff, subtraction, one 2-bar
groove per section, three interaction events, weakest bar). Rules, not a line
table; `phrases.json` owns the line table. `notes.md` is exactly 10 numbered
lines: frame, offline status, tempo assumption, what each section does, and the
open risk. `core_review.md` is 5 numbered critic lines. `CHANGES.txt` is the
plan's deviations plus the checker's `MEASURED` block plus any open warnings.

## Traps

- Writing `score.abc` directly, or a parser/barsum/transform script. The CLI
  owns the file; use `lint`, `patch`, `check`.
- Planning all 86 bars in one reasoning step. Write one line, check it, move on.
- Counting bars or notes by hand. `lint` counts; `check --bars` reports.
- A skeleton that passes the counts: one note per syllable, guitar on whole-bar
  rests, two-note answers, no ties, no chords. A whole-bar arpeggio is a floor,
  not a riff.
- A scale (`D F G A B A G F` every bar). Start from a 3-6 note motif, repeat
  notes, hold a long note, mutate the cell.
- A phrase grid: every line the same 2-2-1-2, starting on beat 1, ending on beat
  3 or 4. Vary the start, the length and the cadence beat.
- Drums left to the model. The seed must carry `V: Drums`, a 2-bar groove, a
  fill and a drop.
- A fill in every gap. Leave one 2-beat hole per 4 bars, at a group end.
- Looping a bar or transposing the verse. Reuse the cell, not the bar.
- Ending every phrase on the tonic. Only the final qafla is tonic; intermediate
  phrases use the maqam's resting tones; aim for 5-7 distinct endings.
- Sitting above C5 throughout. The chorus lifts the median; keep
  `tessitura_share_ge_c5` at or below 0.80.
- Splitting notes to fix duration spread. Write longer notes and rests.
- Tying across a word boundary. The consonant lives in the transition.
- Making melisma an average. Put 3-8 notes on chosen cadence syllables; keep
  the body syllabic.
- Naming a baḥr without scanning it.
- Claiming a listening result that did not happen. Offline: say "offline".

## Cost

The score is about 2,000 tokens. The budget is 10x generated tokens. The CLI
makes the cheap path the correct one: one line per step, the tool pads the
bars, the linter reports all errors once, and the checker runs at section ends.
The stock query is capped at 3–5 assets per section; never dump the index.
Do not spend the budget on parsers, source reading, or a second full write.
Spend it on the cell, the period, the cadence ladder, the riff and the arc.
