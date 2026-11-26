# Plan — put measurement at the line (session-13 proposal)

**Source:** `analysis/eval/inbox/deepseek_session_13/opencod_session_13.json`,
message 53 (`proposal-tools.md`, written by the composer at the end of the run).
**Target:** `abc-score-writer` 0.9.0 (source `02_maqam-score/`).
**Status:** approved for implementation; no new workflow and no quality gate.

---

## 1. What session 13 actually measured

The composer wrote all 26 lines through `score_cli.py` (0 hand scripts, 0 direct
score writes) and ran the full checker once. The first full check failed six hard
checks:

| Check | Measured | Band | Was knowable at |
|---|---|---|---|
| notes / syllable | **311/361 = 0.86** | 1.00–1.55 | line 5 |
| simultaneity | **176** overlapping 16ths, 17 bars | ≤ 4 | bar 30 |
| register mean | **68.0** | 74 ± 5 | line 3 |
| distinct durations | **3** | ≥ 4 | line 4 |
| repeated-pitch share | **4.5 %** | ≥ 20 % | line 6 |
| line note deficit | lines 5–8 short by 3 each | 0 | line 5 |
| pause after line | 23 of 26 lines short | per line | each `line` |

Reproduction: a clean `init` plus the 26 logged `line`/`patch` calls yields the
same 311 vocal notes and the same six failures. The score is 1,427 tokens and
the session generated 57,075 (`output + reasoning`), **40×**, not 10×. The
largest single waste is the two 8,000-token reasoning calls (16,000 tokens) and
the late repair loop; both are consequence of late measurement, not of bad
intent.

**Diagnosis:** the tool already computes every number above (`checker.py`,
`phrase_table.py`, `alignment.py`). The failure is **detection latency**: the
numbers are printed at `check`, long after the line that caused them.

**Boundary:** this is a tooling fix only. It does not change `checker.py`,
`calibration.json`, the ABC dialect, the one-line workflow, or any gate.

---

## 2. Scope

| ID | Item | Ship? | Where |
|---|---|---|---|
| P0-1 | live budget meter after `line` / `patch` | yes | `scripts/live_meter.py`, `score_cli.py` |
| P0-2 | `--dry-run` on `line` / `patch` | yes | `score_cli.py` |
| P0-3 | `lint` reports simultaneity per bar | yes | `score_cli.py` |
| P1-4 | pause ledger (in the meter) | yes | `live_meter.py` |
| P1-5 | duration inventory and tie hint (in the meter) | yes | `live_meter.py` |
| P1-6 | `explain-metric <name>` + `references/metrics.md` | yes | `score_cli.py`, reference |
| P1-7 | `release --dry-run` | yes | `score_cli.py` |
| P1-8 | form-budget advisor at `init` | yes | `score_cli.py` |
| P2-9 | `align` — syllable→note projection, report only | yes | `scripts/projection.py`, CLI |
| P2-10 | `view --roll` / `view --contour` | yes | `scripts/view_score.py`, CLI |
| P3-11 | capped corpus exemplars | **defer** | see §7 |

No item adds a hard gate. `--guard` is opt-in and only refuses a write when an
**existing** hard sanity rule is already violated. `lint` may exit 1 on the
existing simultaneity guard; `line`/`patch` never block on it unless `--guard`.

---

## 3. P0 — the write call carries the measurement

### 3.1 `scripts/live_meter.py`

One report function, called after the new score text exists and before it is
committed:

```python
def measure(score_text, plan, phrases, *, state=None, line_no=None,
            bars=None, lyrics_path=None) -> dict
```

- Parse with `checker.parse`; call `checker.check(..., phrase_plan=phrases,
  lyrics_path=..., score_text=...)` and reuse its `measured` block. This is the
  proposal's rule: **reuse the checker's own numbers**; no reimplementation.
- Derive only what the checker does not expose: per-bar overlap map and the
  written-line projection. Both are short loops over `score.notes_of`.
- Return a dict, never raise on a partial score; on a parse exception return
  `{"error": ...}`. The writer still owns the file.

Printed block (compact, one block per write):

```text
meter line 5 (bars 13-14): 10 notes / 13 syllables — deficit 3
score  75/80 notes → projected 271/361 (need 398-523)
       repeats 3%  durations 2:5 4:2 6:1 (3 of 5)  register 68.1  ties 0/1
       gap after 0.38s (target 0.50s)  overlaps 0 this line / 0 total
```

Rules:
- `deficit` counts notes in the current line vs its `syllables`.
- `projected = round(notes_written / syllables_written * plan.syllables)`.
- `need` = `ceil(syllables * melisma_min)` … `floor(syllables * melisma_max)`.
- `durations` are written 16th units with counts; the parenthetical is
  `distinct / plan.min_distinct_durations`.
- `register` is `measured.register_mean`.
- `ties` is `measured.ties` / `plan.ties_min`.
- `gap after` is the line-tail rest in seconds; target is
  `phrases.lines[i].pause_after_s`. If the next line is written, use the actual
  gap to its first note.
- `overlaps` is the sum of overlapping sounding units in the line's bars / the
  whole score; cap is `calibration.sanity.simultaneity_le4.max` (4) or the
  plan's `simultaneity_exception`.

The block is printed by `line` and `patch`. It is not written to a file; the
checker's `report.json` stays the artifact of record.

### 3.2 `--dry-run`

`line N ... --dry-run` and `patch B ... --dry-run` build the same `new_text`,
lint it, print the padded bars and the meter, then exit 0 **without writing
score.abc or the state**. A bad duration fails at dry-run, not after a
half-applied shell chain.

### 3.3 `lint` overlap

After the existing parse/sum pass, parse with `checker.parse` and print one line
per offending bar:

```text
lint: bar 30 Ins overlaps Vocal 14 sixteenths (max 4)
lint: simultaneity 176 units in 17 bars
```

Exit 1 if any bar exceeds the cap. This surfaces the existing hard sanity rule;
it does not create a new one. `line`/`patch` keep their current lint-only write.

### 3.4 `--guard`

Optional on `line` / `patch`. Refuse the write (exit 1, nothing changed) if,
after the write would have happened:

- the current line has a note deficit > 1;
- the current line's gap is shorter than its `pause_after_s` target;
- the current line's overlap exceeds the cap;
- on the last lyric line, any existing whole-score sanity band is already
  violated (notes/syllable, register mean, repeated share, distinct durations,
  top-duration share). Early partial means are not judged: a low verse is
  legitimate until the chorus has been written.

The guard prints the same meter plus `REFUSED (--guard): ...`.

---

## 4. P1 — cheap precision

### 4.1 Pause ledger and duration/tie hints

Part of the meter block (§3.1). No `--min-gap` reservation in this pass: it
changes how the writer pads, and the proposal marks it optional. The hint is
`gap after 0.38s (target 0.50s) — add z1`; no automatic move.

### 4.2 `explain-metric`

New `references/metrics.md`, one `## name` section per metric. New command:

```bash
score_cli.py explain-metric --list
score_cli.py explain-metric end
```

Needed definitions (the ones that actually caused confusion):
`notes_per_syllable`, `register_mean`, `register_top`, `repeated_share`,
`top_duration_share`, `distinct_durations`, `simultaneities`, `silence_share`,
`answer_rate`, `vocal_median_pitch`, `unbroken_seconds_max`, `end`,
`cadence_pc`, `cap_ratio`, `chorus_lift`.

The `end` entry documents the session-13 discrepancy: the `check --bars` `end`
column is a **pitch class relative to the tonic** (`(pitch - tonic) % 12`), so
a written C in Dm displays `Bb`; it is not the written pitch. Also rename the
table header to `end°` and add an absolute `pitch` column so the confusion
cannot recur.

### 4.3 `release --dry-run`

Run the strict check and final-rest check, print the verdicts and the repair map
on failure, but **do not update `score_state.json` or the skill state**. The
report is still written for diagnosis. This makes the first strict pass
repeatable.

### 4.4 `init` form-budget advisor

Before the scaffold is written, compare the chosen `bars` with
`prosody.json["bars"]` (the syllabify budget). If the difference exceeds ±5 %,
print:

```text
FORM BUDGET: 64 bars vs syllabify 82 (-22%, tol ±5%)
  the form is baked into plan.json and phrases.json; to change it, rerun
  init --bars 82 (or pass --sections). Continue with --bars 64 to accept.
```

It does not block and does not silently change the requested form.

---

## 5. P2 — the two reports the composer cannot compute in its head

### 5.1 `align` (P2-9)

`scripts/projection.py`, report only:

```bash
score_cli.py align --lines 3-6
```

For every lyric line: bars, syllables, notes, then the projection in order.
One note per syllable; if notes > syllables the surplus is printed as a cadence
tail (the heuristic is named in the header, never treated as fact); if notes <
syllables the elided syllables are marked. Ties are marked `~`. This is the
sanctioned alternative to claiming a melisma the score cannot show.

### 5.2 `view --roll` / `view --contour` (P2-10)

`scripts/view_score.py`, read only:

```bash
score_cli.py view --roll --bars 3-5
score_cli.py view --contour
```

`--roll` prints an ASCII piano roll, one column per L-unit (16 in 4/4 `L:1/16`),
pitch rows labelled `C4`, `D4`, …; `#` = sounding. `--contour` prints one line
per lyric line: bars, rising/falling/wave/flat, start→end pitch, note count.
Both cap output (default 16 bars for `--roll`, all lines for `--contour`).

---

## 6. Files and tests

**New**
- `02_maqam-score/scripts/live_meter.py`
- `02_maqam-score/scripts/projection.py`
- `02_maqam-score/scripts/view_score.py`
- `02_maqam-score/references/metrics.md`
- `02_maqam-score/tests/test_live_tools.py`

**Changed**
- `02_maqam-score/scripts/score_cli.py` (meter, dry-run, guard, lint overlap,
  explain-metric, release dry-run, init advisor, align, view)
- `02_maqam-score/scripts/phrase_table.py` (absolute `end_pitch`, keep `end_name`
  as the degree; header `end°`)
- `02_maqam-score/SKILL.md` (one short “measure at the line” block; no new order)
- `02_maqam-score/references/cli.md` (commands and flags)
- `02_maqam-score/CHANGELOG.md`, `scripts/ostris/contract.py`, `README.md`,
  `Makefile` (`SKILL_RELEASE`) → 0.9.0
- `02_maqam-score/tests/test_score_cli.py` (dry-run/guard cases)

**Tests**
1. `live_meter.measure` on the example score returns the checker's
   `register_mean`, `repeated_share`, `distinct_durations`, `ties` and a
   projected note count; no exception on a partially written score.
2. `line --dry-run` prints `deficit` and does not change `score.abc` or state.
3. `lint` reports `bar … overlaps …` on a synthetic 2-voice collision and exits 1.
4. `--guard` refuses a line with a deficit > 1 and leaves the file byte-identical.
5. `release --dry-run` leaves `score_state.json` unchanged.
6. `init` on the session-13 lyrics prints `FORM BUDGET: 64 … 82`.
7. `align` prints one row per line and marks a surplus tail.
8. `view --roll` returns the requested bar range only.
9. `explain-metric end` mentions tonic-relative pitch class.

**Replay acceptance (manual, not unit):** replay the 26 logged `line` calls in
a clean directory and assert:
- `line 5` output contains `deficit 3`;
- the meter after line 5 contains `projected` below 398;
- `lint` after bar 30 reports the bar-30 overlap;
- every line output contains a `gap after` value and its target;
- `init` warns `64` vs `82` before writing the scaffold.
No score content changes; only diagnostics differ.

---

## 7. Deferred

- **P3-11 `asset_bank exemplars`.** The proposal asks for 2-voice excerpts from
  the 177-track corpus, but the 177 ABC files are not bundled (only their
  statistics) and `docs/DECISIONS.md` D5 forbids using the 670 SUNO tracks as a
  primary melodic baseline. Shipping a 670-only “exemplar” would mislabel the
  source. Defer until a curated, licensed 177 excerpt pack exists; the asset
  bank already covers the reference use case.
- **`line --min-gap` reservation.** Optional in the proposal; the hint is enough
  until the meter shows it changes behavior in a real run.
- **Automatic token/step enforcement.** The owner monitors the session
  (`MY_MAIN_GOALS.md` §2); this plan does not add a budget monitor.

---

## 8. Order of work

1. `live_meter.py` + meter in `line`/`patch` (P0-1).
2. `--dry-run` + `--guard` (P0-2, P0-3 guard).
3. `lint` overlap (P0-3).
4. `explain-metric` + `references/metrics.md` (P1-6).
5. `release --dry-run` (P1-7), `init` advisor (P1-8).
6. `align` (P2-9), `view` (P2-10).
7. docs, changelog, tests, replay acceptance, `make test`, `make selftest`.

**Done when:** the replay shows the six session-13 failures at the line that
caused them, all existing tests pass, and `checker.py`/`calibration.json` are
byte-identical to the 0.8.1 release.
