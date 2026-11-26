---
name: abc-score-writer
version: "1.0.1"
description: >-
  Write a complete two-voice ABC score from Arabic lyrics and an arabmaqamrock
  style prompt in whole drafts, then validate it with one scorecard. The model
  composes; the tools validate. Use when asked to write, compose, generate or
  design a score, melody, or ABC file from lyrics and a style. Do NOT use for
  editing an existing SheetSage2 transcription.
---

# abc-score-writer

You are the composer. The tune is the work. The tools measure and reject; they
never choose a note.

**Write the whole score. Then fix it whole. Do not patch bar by bar.**

## The loop

```text
init -> draft (whole) -> scorecard -> rewrite (whole) -> scorecard
     -> polish seams -> release
```

At most **4 drafts**. If the same blocking issue survives two full rewrites,
stop and report: the model or the plan is the limit, not the card.

## 1. Init

```bash
python3 <skill>/scripts/score_cli.py init --tempo 80
```

Read `plan.json` and `phrases.json`. Use `--sections` when the form is decided:
`name=start_bar`, one entry per section in lyric order, repeating the name for a
repeat (`chorus=37,...,chorus=65`, not `chorus2`).
If `FORM BUDGET` appears, decide before the first draft: keep the compact form
and accept the warning, or rerun with `--force --bars N` **and** `--sections`.

`init` also prints the per-line table (syllables, bars, pace, pause). Use it;
do not recompute bar sums or note counts by hand.

If `init` reports `plan.json exists`, **stop and report**: the room is dirty.
Do not compose on a plan you did not create; the run is invalid.

## 2. Draft the whole score

Write `score.abc` in **one pass**, or at most **three large sections**
(intro+verse 1, chorus+verse 2, chorus 2+outro). A 2-4k-token score is one
draft; it fits the call cap.

- No `line`, no `patch`, no per-bar meter.
- No Python parser, no hand sums. The scorecard is the measurement.
- Keep the cell, period, cadence ladder, register arc and texture in your head
  or in a short note. Do not write a DSL or a composition compiler.

If the draft is long, split by **section**, not by lyric line. If a call ends
with no output (cut off while thinking), do not retry the whole file in one call:
write it again by sections (at most three), thinking less per section.

## 3. Scorecard

```bash
python3 <skill>/scripts/scorecard.py score.abc --plan plan.json --phrases phrases.json
```

The card has five parts:

- `KEY BANDS` — the checker's numbers and their verdicts (`FAIL` hard, `WARN`
  plan/polish).
- `BLOCKING` — hard failures. Fix all of them in the next draft.
- `RELEASE-BLOCKING` — pass the card but fail `release` (style checks and the
  final rest are strict there). Fix them in the same rewrite as `BLOCKING`.
- `POLISH` — warnings that stay non-blocking at release. Fix what the ear hears.
- `SEAMS` — line-to-line joints: cadence -> start, rest, register, overlap.

Exit code `1` means `BLOCKING` or `RELEASE-BLOCKING`; `2` means a parse error. Read the card, not the
exit code alone.

`section plan metrics` is a known banded warning: the auto plan's
`vocal_notes_per_bar` band is too low for dense syllabic verse. It is not a
target and not a blocking issue; do not rewrite the score to chase it.

## 4. Rewrite the whole score

Use the card. Fix **blocking first**. Rewrite the **whole file** (or a whole
section), not one bar. A 3k rewrite is cheaper and safer than 45 patches.
Repeat 1-4 times.

- `simultaneity` — the cap is **4 units total**, not per bar. Pull `Ins` out of
  the vocal, or declare a `simultaneity_exception` bar.
- `repeated notes` — repeat pitches at phrase heads and cadences; the floor is
  **20%**.
- `register mean` — the hard band is **69-79**; the plan target is separate.
- `parse error` — fix the bar sums first; no other number is meaningful.

## 5. Polish seams, release

When `BLOCKING` and `RELEASE-BLOCKING` are empty, polish the flagged seams: section transitions,
same-pitch joints, register jumps, short rests, guitar under the voice. Then:

```bash
python3 <skill>/scripts/score_cli.py release --dry-run   # same verdicts, no state change
python3 <skill>/scripts/score_cli.py release
```

The ear is the judge. The card is the guard. If there is no audio, do not claim
a musical verdict.

## Rules

- **The model writes notes. The tools never compose.**
- No hand-written parsers or metric scripts; the scorecard is the measurement.
- No micro-edits; no 26-line loop; no patch-by-patch repair.
- Do not edit `score.abc` with `sed`, Python, or piecemeal `edit` calls. The
  only score write is a whole-file rewrite. If the card says "rewrite the whole
  score", the next write must be a complete file.
- Do not lower the checker or `calibration.json`; do not add taste gates.
- Stop when the card has no blocking or release-blocking and the ear is satisfied. Do not keep
  editing after a pass.
- If the same blocking issue survives two full rewrites, stop and report.

## ABC contract (short)

- Header: use the scaffold header that `init` writes (`X:1`, a blank `T:`, `M:4/4`,
  `L:1/16`, `Q:1/4=<tempo>`, the two `V:` lines, `K:<key>`). Do not invent it.
- Each `V:` block is followed by up to 4 bars; every bar sums to **16 units**;
  `Z` is a whole-bar rest, and `Z2`, `Z3`, `Z4` alone in a bar slot are 2-4
  whole-bar rests that count toward the 4-bar limit (`Z3|` is three bars).
- Put one comment line before each group of `V:` blocks, named for a section in
  `plan.json` (`% intro`, `% verse`, `% chorus`, `% outro`). Every `%` line is read
  as a section name; do not write other comments (`% bars 1-4`).
- The last bar is `Z` in both voices.
- Pitch is a letter plus octave marks: `A,` = A3, `A` = A4, `a` = A5. The
  number after a note is its **duration in units**, not its octave: `A4` is
  A natural for 4 units; `A4 2` is not valid.
- Durations: `1,2,3,4,6,8,12,16,24,32,48`. Ties: `A2-A2` (same pitch, two
  lengths; the sum is held); no dots, no tuplets, no `[...]`.
- Read `example/score.abc` before the first draft; it is the dialect reference.

## Legacy

`line`, `patch`, `core` and the live meter still exist in `score_cli.py` for
emergency repair and for the 0.9 archive. They are **not** this workflow. Do
not use them to compose a new score.
