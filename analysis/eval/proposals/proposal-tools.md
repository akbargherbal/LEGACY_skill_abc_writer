<!-- Extracted from the session-13 export (message 53). The composer
     wrote this proposal at the end of the run; it is the source for
     analysis/eval/plans/2026-11-25-session-13-tools-plan.md. -->

# Proposal: move measurement to the line, not the gate

**To:** maintainer, `abc-score-writer`
**From:** composer agent (DeepSeek V4.1 Flash), session-13
**Date:** 2026-11-25
**Subject:** eleven additions that would have prevented this session's six hard failures at the moment they were written, at no cost to the craft contract

---

## 0. Summary

The one-order workflow (`init → core → line ×26 → check → release`) is sound, and the
craft documents are the best part of the skill. The failure mode I hit is **detection
latency**: every hard failure in the first full `check` was knowable at the `line`
call that created it, but the tool surfaced it only after all 64 bars existed.

Result: 26 lines written, one full check, six hard failures, a repair map naming
~fifteen bars, and a four-run checker budget mostly spent on arithmetic I could no
longer act on cheaply.

I am not proposing new gates and I am not proposing that the tool compose. I am
proposing that the measurements the tool already makes — and the ones the checker
already computes — be printed **at the write call**, with an opt-in refusal mode.
Everything below is additive to the existing single-entry CLI and leaves the
`score.abc` contract untouched.

---

## 1. Evidence from this session

`report.json` from the first full `check` on the completed 64-bar score:

| Gate | Measured | Band | Knowable at |
|---|---|---|---|
| notes / syllable | **0.86** (311/361) | 1.00–1.55 sanity; 1.10–1.45 plan | line 5 (first deficit) |
| simultaneity | **176** overlapping 16ths, 17 bars, worst 16 | ≤ 4 | bar 30 (first pedal) |
| register mean | **68.0** | 74 ± 5 sanity; 70 ± 3 plan | line 3 (rolling mean) |
| distinct durations | **3** | ≥ 4 sanity; ≥ 5 plan | line 4 |
| repeated-pitch share | **4.5 %** | ≥ 20 % sanity | line 6 |
| ties | **0** | ≥ 1 | line 1 |
| pause violations | **23 of 26 lines** (0.00–0.38 s vs 0.50/1.00) | per-line target | each line call |
| line note deficit | lines 5–8 short by 3 each | 0 | line 5 |
| duration cap ratio | **0.689** | ≥ 0.708 corpus | `init` (form budget) |
| bars budget | 64 vs **82** recommended | ±5 % | `init` (before any note) |

The 23 pause violations are the clearest illustration: `line` pads the bar tail, so the
tool knows the resulting gap exactly at write time, but the composer sees it only in
`check --bars` after a whole section is closed.

A second, smaller item: the `check --bars` "end" column reported pitch names a whole
tone below the written last note in several lines (bar 12 ends C, reported B♭; bar 14
ends F, reported E♭; bar 25 ends B♭, reported A♭). This may be a transposition
convention, a partial-bar smoothing, or a display bug; I could not determine which,
because reading `checker.py` is prohibited. That is an argument for a documented
metric surface (P1-6), not an argument for reading the source.

---

## 2. Design principle

> **Every number that can fail a gate should be printed at the call that changes it.**

Three constraints on the implementation:

1. **No new hard gates.** Diagnostics are printed; refusal is opt-in (`--guard`) and
   defaults off, except where the existing `line`/`core` contract already refuses.
2. **No new file ownership.** The CLI still writes `score.abc`; the new output is
   `stdout` plus, where useful, a machine-readable `metrics.json` sidecar.
3. **Reuse the checker's own numbers.** Most of the list is surfacing, not new
   analysis. Only P2-9 and P2-10 need new computation.

---

## 3. P0 — would have prevented the FAILs (small effort, high effect)

### P0-1. Live budget meter on `line` and `patch`

After every successful write, print a compact block:

```
line 5  bars 13-14  10 notes / 13 syllables   deficit 3
score   75/80 notes  —  projected 271/361 (need 398-523)
        repeats 3%   durations {2,4,6}   register mean 68.1
        end gap 0.38s (target 0.50s)      overlaps 0
```

- Hook: `line`, `patch` (after write, before exit).
- Source: existing parse + `prosody.json` syllable counts + the checker's own
  helpers. No new metric.
- Why it matters: catches P0-1, P0-5, P0-6, P1-4 in one glance, at the line.
- Effort: **S** (~1 day). Acceptance: on replay of this session's 26 `line` calls, the
  block shows the deficit at line 5 and the register slide by line 7.

### P0-2. `--dry-run` for `line` and `patch`

Print the padded bars, the per-bar sums, the overlap count, and the meter block, then
exit without writing. An invalid duration token fails at dry-run, not after a
half-applied chained command.

- Why: `z14` and `z10` are legal-looking but unsupported; each rejection aborted the
  rest of a shell chain and cost a re-run with duplicate-write risk.
- Effort: **S** (hours — the write path already validates before committing).

### P0-3. `lint` reports simultaneity per bar

`lint` runs on every write but does not check overlap; `check` does, and fails at 4
units. Add a line per offending bar:

```
lint: bar 30 Ins overlaps Vocal 14 sixteenths (max 4)
```

- Why: this was the largest hard failure (176 units) and the one I could only learn
  by failing the whole-file check. The cap is a hard sanity rule; it belongs in the
  linter, not only in the checker.
- Effort: **S** (call the existing function; cap already in `plan.json`).

---

## 4. P1 — cheap precision, prevents warnings I cannot retro-fix

### P1-4. Pause ledger and `--min-gap`

Per line: `end gap 0.38s; caesura target 0.50s, bayt target 1.00s — try z1`.
Optionally `line --min-gap 0.5` reserves the tail instead of padding it.

- Why: 23/26 lines violated `phrases.json` targets; nothing in `line` mentions gaps.
- Effort: **S**.

### P1-5. Duration inventory and tie hint

```
durations: 2 (69%), 4 (21%), 6 (10%)  — 3 of 5 required; add a 1 or 8
ties: 0 of 1 — bars 6/7 both hold A across the barline
```

- Why: `min_distinct_durations` and `ties_min` are hard/style gates that are trivially
  checkable at write time and completely invisible while writing.
- Effort: **S**.

### P1-6. `explain-metric <name>` — the documented black box

One screen per metric: definition, formula, which gates use it, known pitfalls.
At minimum: `end`, `cadence_pc`, `register_mean` (note-weighted or duration-weighted?),
`top_duration_share`, `simultaneities`, `silence_share`, `answer_rate`,
`vocal_median_pitch`.

- Why: the "end" discrepancy above; the coexistence of sanity 74±5 and plan 70±3 for
  the same quantity; the `check --bars` table labels ("mean", "rep") which are not
  defined anywhere. This is the sanctioned alternative to reading the source.
- Effort: **S–M** (documentation; no code beyond a `--list`/`--show`).

### P1-7. `release --dry-run`

Print the strict-style verdicts without freezing the score. Today the first strict
pass is also the only one.

- Effort: **S**.

### P1-8. Form-budget advisor at `init`

```
361 syllables at 80 BPM → 82 bars (±5%); 64 is -22%, expect a budget warning.
Suggested: init --bars 82, or --sections "intro=9,verse 1=14,..."
```

- Why: `syllabify` computed 82; `init` chose 64; the mismatch was baked into
  `plan.json` before I wrote a note and cannot be repaired without re-initialising.
- Effort: **S** (syllabify already returns the number).

---

## 5. P2 — new analysis, for the thing I genuinely cannot do

### P2-9. Syllable → note projection (`align`)

A table projecting `prosody.json` syllable indices onto written note positions, per
line, with melisma groups marked:

```
line 1  bars 3-5  15 syl / 16 notes
  syl 1-5   A A G F A      body
  syl 14-15 c B A G A      cadence melisma (5 notes)
```

- Why: with no `w:` lines, "melisma on the qāfiya" is currently a prose claim the
  composer cannot verify and the checker cannot see. This closes the only
  unverifiable-by-construction gap in the workflow.
- Effort: **M** (alignment heuristic; must be a report, not a gate).

### P2-10. `view --roll` — an ASCII piano roll

16 columns per bar, pitch rows, one character per sounding unit; a second mode
collapsing to a contour sparkline per phrase.

- Why: I can read a grid far better than I can infer contour from `pitch:duration`
  token lists. This is the difference between seeing that lines 1–8 all "descend from
  A and end on A" (the habit behind the 4 % repeated-pitch share) and reading a
  scalar that only says 4 %.
- Effort: **M**. Read-only, no scoring.

---

## 6. P3 — calibration material

### P3-11. Corpus exemplars with metrics (`asset_bank exemplars`)

Three to five short *two-voice* excerpts from the 177, each annotated with its own
numbers (repeated share, endings, notes/bar), returned as text fragments under the
same 5-item cap as `query`.

- Why: medians describe a distribution; a legal, good excerpt shows what 33 % repeated
  pitch or a 2+2 period actually looks like. The `example/` score is a four-line toy
  and the asset bank returned nothing for a 3-bar, 16-syllable, rising chorus.
- Effort: **M** (curation + redaction of the library behind a capped interface).

---

## 7. Non-goals

- No automatic composition, no "suggest a melody" button.
- No relaxation of any gate, and no new hard gates (except P0-3, which surfaces an
  existing hard sanity rule earlier).
- No change to the `score.abc` dialect, the header, or the voice contract.
- The meter is not a target vector. It reports the band; the composer still owns the
  cell, the period and the cadence ladder.

---

## 8. Recommended order

| Order | Item | Effort | Expected effect |
|---|---|---|---|
| 1 | P0-1 meter | S | prevents 4 of 6 hard FAILs |
| 2 | P0-3 lint overlap | S | prevents the largest FAIL |
| 3 | P0-2 dry-run | S | removes abort/retry loop |
| 4 | P1-4 pause ledger | S | 23 warnings → 2–3 |
| 5 | P1-5 duration/tie hint | S | 2 gates |
| 6 | P1-8 init advisor | S | unrepairable plan mismatch |
| 7 | P1-6 explain-metric | S–M | unblocks all future diagnosis |
| 8 | P1-7 release dry-run | S | one-shot strict pass |
| 9 | P2-9 align | M | verifiable melisma claim |
| 10 | P2-10 roll | M | contour sight-reading |
| 11 | P3-11 exemplars | M | calibration |

If only three things ship, ship **P0-1, P0-3, P1-4**: they address 5 of the 6 hard
failures and 21 of the 23 warnings in this session's first check, and each is a
function call into code that already exists.

---

## 9. Acceptance test

A replay harness: run this session's `input/lyrics.txt` with the 26 committed `line`
specs, and assert that

1. the `line 5` meter output contains `deficit 3` and `projected … < 398`;
2. `lint` after bar 30 reports `bar 30 … overlaps … 14`;
3. the pause ledger reports `line 1 … 0.00s … 0.50s`;
4. `init` prints a bar-budget warning for 64 vs 82 **before** writing the scaffold;
5. with `--guard`, the same run refuses the first offending line instead of writing it.

No score content changes in the replay; only the diagnostics differ.

---

## 10. One paragraph for the changelog

Composition failures in the current workflow are detected at the gate, not at the
line. This proposal adds a per-write budget meter, a dry run, simultaneity reporting
in `lint`, a pause ledger, duration/tie hints, a documented metric surface, a strict
dry run, an `init` form-budget advisor, a syllable-to-note projection, an ASCII
piano roll and capped corpus exemplars. It adds no new hard gates, no new file
ownership and no automatic composition; it moves existing measurements to the point
of decision.
