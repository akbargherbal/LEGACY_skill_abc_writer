# Session 15 — the 1.0 whole-draft loop, first measured run

**Run:** `analysis/eval/inbox/deepseek_session_15/20261126-…ses_de9e4598fffeDDIOXoQ2fhvgnL.json`
**Model:** `deepseek/deepseek-flash` (agent #high; session metadata says `variant: low`);
the guard rewrote every call to `high` (see `abc-session.log`).
**Skill:** `abc-score-writer` 1.0.0, composer `steps: 100`.
**Task:** D Kurd, 80 BPM, 4/4, 26 lines / 361 syllables.
**Outcome:** the composer's real score was written, released (60 checks, 0 hard
failures, 4 warnings). No audio, so no ear verdict. Economy **54×** → fail.

## Verdict

- The 1.0 loop **can** reach 0 blocking: 4 drafts, then release.
- It did **not** approach 10×. The change moved tokens from 26 line decisions to
  4 whole-score rewrites + 6 patch rounds; the total is the same or worse than
  session 14 (50×).
- The run **did not test a clean 1.0 start**: `init` failed because `plan.json`
  already existed. The 64-bar form (vs syllabify's 82) was inherited and never
  decided.
- The packaged `score.abc` is **not** this run's score. It is an empty 82-bar
  scaffold written later (see *Artifact integrity*).

## Measured

| Field | Value |
|---|---|
| Generated | **94,584** (output 17,783 + reasoning 76,801) |
| Final score | **1,744 tokens** (2,603 bytes, 64 bars, 398 vocal + 137 Ins notes) |
| Ratio | **54.2×** (10× budget 17,440; 20× partial 34,880) |
| `measure_session.py` | 158.7× — divides by the empty 596-token scaffold in the zip, not the real score |
| 8,000-cap reasoning calls | **6** (m28, m30, m32, m42, m47, m51) = **48,000 = 50.8 %** of generated |
| Before the first note | m1–32 = **31,784 = 33.6 %** |
| Drafting | m35–49 = 30,709 = 32.5 % |
| Repair | m50–61 = 25,350 = 26.8 % |
| Release + packaging | m62–84 = 6,736 = 7.1 % |
| Tool calls | 70 (55 shell, 10 write, 2 read, 1 edit, 1 skill, 1 subagent) |
| Scorecard runs | **18** |
| Score mutations after the last full draft | 6 (m54, m55, m56, m58, m60, m61) |
| Duration | 16.6 min, $0.0885 |

## The 1.0 gates

| Gate | Result |
|---|---|
| ≤10× (or ≤20× partial) | **fail** — 54× |
| 0 blocking at the end | **pass** — `release` 60 checks, 0 fail |
| No late micro-repair | **fail** — the card said "rewrite the whole score", the model patched |
| 1–4 drafts | 4 full/partial rewrites, then 6 patch rounds |
| repeats ≥20 % | pass — 34 % |
| register 69–79 | pass — 69.3 (sanity floor is exactly 69) |
| simultaneity ≤4 | pass — 0 |
| ≤24 steps | **fail** — 70 tool calls |
| Form decided at `init` | **fail** — `init` returned `ERROR plan.json exists` |

## What the card did fix

All six session-13 hard failures are gone in the released score:

| Failure (session 13) | Session 15 |
|---|---|
| notes / syllable 0.86 | **1.10** (398/361) |
| simultaneity 176 | **0** |
| register mean 68.0 | **69.3** |
| distinct durations 3 | **6** |
| repeated share 4.5 % | **34 %** |
| line deficit | **none > 1** |
| pause after line | rests 0.75–1.50 s on the card |

The model read the card and acted on it; the tool is not the failure.

## Where the 94.6k went

1. **Manual arithmetic (47.2k, 50 %).** Five capped 8k blocks and one 7.2k
   block are the model tabulating 26 windows, note counts and bar sums by hand.
   m28–m32 is 24k (25 %) before a single note was written; m42 repeats the same
   calculation after the first draft.
2. **An invented notation (≈6k).** m35 wrote `A4 2` (octave + duration) instead
   of `A2`; 45 parse errors. The skill's own line "Ties are `A4-A2`" reads like
   octave notation. This is our documentation bug.
3. **Patch rounds after "rewrite" (6 rounds, m54–m61).** The card printed
   `NEXT Rewrite the whole score once … Do not patch bar by bar`; the model did
   `sed -i` and Python string replacements instead.
4. **Source archaeology (7.8k, m1–m27).** 32 `sed`/`grep` reads of
   `checker.py`, `alignment.py`, `binding.py`, `score_cli.py` to recover
   thresholds the skill should state in one page.

## Ours, not the model's

- **The package was not clean.** `plan.json`/`phrases.json`/`score.abc` were
  present at start; `init` exited 2. The FORM BUDGET decision never ran, so the
  64-bar plan and two permanent warnings (bars 64 vs 82; cap 0.689) were
  inherited, not chosen.
- **The plan's section bands are impossible.** `[0, 3]` vocal notes/bar against
  361 syllables in 58 bars (≈6.2/bar). Every score will WARN on `section plan
  metrics`. The model spent ~2k tokens discovering this.
- **The tie example is ambiguous.** `A4-A2` needs the explicit rule: the digit
  after a note is duration; octave is `,`/`'`, so `A4` = A natural × 4 units.
- **The packager subagent returned nothing.** m64 started it; m68 found no
  files. `verify_package` then required `core_draft.abc`/`core_review.md`, which
  the composer is told not to produce. The composer did packaging itself.
- **The seed's chord metadata is not maqam-checked.** `seed.abc` carries
  `Am`×22, `C`×13, `G`×11, `Em`×5 — 18 bars with E natural against kurd's Eb.
  If those symbols are rendered or used by the arranger, the harmony contradicts
  the 99.7 % vocal maqam fit. The checker only sees `score.abc`, where
  `chords = 0`.
- **The second composer session overwrote the folder.** `ses_de9ced274…` ran
  04:50:52–04:52:54 and left an 82-bar init scaffold. The exported JSON ends at
  04:43:55.

## Artifact integrity (important)

| File | In zip | Reviewed run (m68 `ls`, 04:43) |
|---|---|---|
| `score.abc` | **914 B, all `Z`, 82 bars, 0 notes** | **2,603 B, 64 bars, 398 notes** |
| `plan.json` | 3,171 B, 82 bars, placeholder deviations, `ins_entries: []` | 3,502 B, 64 bars, 3 declared deviations, entries `[8,33,55]` |
| `state.json` | `phase: "start"`, 82-bar `score_state.json` | `phase: "package"`, 64-bar |
| `report.json` | 64 bars / 398 notes (the real release report) | same |

The zip mixes two runs. Running `check` on the archived `score.abc` gives
`0/361` notes and hard FAILs while `state.json` still says `pass: true` — a
false green. `verify_package` hashes `report.json` but not `score.abc`.

A replay of the logged mutations (5 writes, 1 heredoc append, 1 `edit`, 3 `sed`,
4 Python passes) reproduces exactly **2,603 bytes / 64 bars / 398 vocal / 137
Ins** and matches `report.json`.
Saved at `analysis/eval/inbox/deepseek_session_15/reconstructed/score.abc`
(SHA-256 `9737fb50…`).

## Musical observations (not a verdict)

- Every one of the 26 lines starts with the same first-bar rhythm
  `1,1,2,2,1,1,2,2`; only **9 distinct rhythm signatures** exist in 26 lines,
  and **13 lines share one signature**. Pitch sequences differ (25/26), so the
  melody varies over a metronomic grid. This is the main listening risk.
- Metrics hug their floors: notes/syllable 1.10 (floor 1.10), register 69.3
  (sanity floor 69), silence 23 % (floor 22 %), repeated 34 %. The score is
  tuned to pass, not to a musical target.
- No audio exists. Quality stays **suspended**; 6/10 and 9/10 are both
  unclaimed.

## Next single change

1. **Validity first:** ship a clean package (no `plan.json`/`phrases.json`/
   `score.abc`), fail closed if the composer does not run `init`, and record the
   chosen form in the report. Without this, the next run again measures an
   inherited form.
2. **Then the economy:** print a one-page **line budget table** at `init`
   (line → bars, syllables, min/target notes, end-rest) plus the notation rule,
   and deny shell/file mutations of `score.abc` (whole-file `write` only). The
   first removes the 47k of arithmetic; the second removes the 25k repair band.
3. **Then listen.** No further process change should be judged until there is
   audio.

## Not claimed

- No musical quality verdict; there is no audio.
- No claim that the 1.0 loop is economically viable: at 54× it is not, and the
  100-step cap is not the binding constraint (70 tool calls were used).
