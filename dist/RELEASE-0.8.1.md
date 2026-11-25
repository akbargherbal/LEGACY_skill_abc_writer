# Release 0.8.1 — the line is the unit; the CLI owns the file

**Date:** 2026-11-25
**Skill:** `abc-score-writer` 0.8.1 (contract pin 0.4.0)
**Session drop:** `session-12-ready.zip`
**Prompt:** `Write the abc score for style+lyrics in @input/lyrics.txt`
**No `task.md`.**

## Evidence

Session 11 spent **219,533 generated tokens** for a **1,941-token** `score.abc`
(**113×**). 42% was three whole-score reasoning messages (m9 32,000, m21 32,000,
m39 28,348); the composer ran `checker.py` 13 times (budget 4), wrote two full
scores and seven helper scripts, read the checker source 11 times, and used
`repair.py`/`quality.py`/`abc_doctor.py` zero times. 80% of the tokens ran on
`deepseek-v4.1-flash-free`, not the configured `deepseek-flash`.

## Changes

- `scripts/score_cli.py`: `init`, `core`, `line`, `patch`, `lint`, `check`,
  `release`, `seed`, `seed-check`, `plan`, `status`, `explain`.
- `line N` writes one lyric line (2–4 bars), **pads the bar tail with rests**,
  and lints the whole file before writing. `patch B` replaces one bar
  atomically. `score.abc` is never written by the model.
- `core`: snapshot the first 16 bars, require `core_review.md` (5 numbered
  lines) and an exact prefix before expansion.
- `abc_tools.lint_text`: every header/group/bar error in one pass with voice and
  bar; `checker.py` keeps its fail-closed `parse`.
- `checker.py --release`: strict style + final rest in one flag; `--strict-style`
  remains an alias.
- `check`: prints the `repair.py` bar/phrase map on a hard failure, with a
  guard for a parse failure that never wrote `report.json`.
- `phrase_table.py`: unwritten lines are `notes: null`; `craft.py` no longer
  infers endings for bars that do not exist and prints `INCOMPLETE`.
- `plan`: `init` writes a complete 0.8.1 plan; `plan lint` names missing fields
  and placeholders; `plan refresh` re-derives `section_plan` and `ins_entries`.
  One page: `references/plan.md`.
- `seed`: copies the melody, adds one chord per Vocal bar and a `V: Drums`
  2-bar groove/fill/close; `seed-check` proves bar alignment.
- `SKILL.md`: 967 lines / 15,138 tokens -> 292 lines / 3,866 tokens.
- Session template: `.opencode/agents/{composer,verifier,packager}.md` and
  `.opencode/plugins/abc-guard.js`. The guard forces
  `deepseek/deepseek-flash#high`, caps a primary model call at 8,000 output
  tokens, and logs the actual model to `abc-session.log`. The composer cannot
  edit `score.abc` directly.

## Verification

- `make test`: **103 tests OK**.
- `make selftest`: **PASS** (including the new `score_cli` lint/section/plan/
  seed checks).
- `make acceptance`: **0 failed** (example, phrase failure, old mediocre score,
  one-screen contract, 177 corpus).
- `make offline-check`: **PASS**.
- The session-11 final 86-bar score passes the new CLI's
  `check --release` (60 checks, 0 fail, 0 warning).
- `measure_session.py` reproduces the session-11 baseline: 219,533 generated,
  113.1×, max message 32,000, 13 checker runs, 2 score writes, 11 script
  writes, 30 source reads.

## Hashes

```text
cbff5132aa21c9594bac5fd91c3f5720ef8592f2bf8ab4660792ad90f4c79027  abc-score-writer-0.8.1.zip
b323b32b9cf13ea5b16f35b6616f39e456f8ae55ba5e97b539b29836cccddb1d  session-12-ready.zip
```

## Session 12

```bash
unzip session-12-ready.zip
cd session-12
opencode --auto
# paste PROMPT.txt (outside the directory)
```

Measure after the run:

```bash
python3 analysis/measure_session.py opencode_session_12.json \
  --score session-12/score.abc --max-ratio 10 --max-message 8000
```

Targets: **≤25,000 generated (≤13×)**, stretch **≤19,400 (10×)**; no message
above 8,000; 0 hand scripts; ≤4 checker runs; 0 direct score writes; 100% of
tokens on the pinned model. The ear remains the only quality gate; this release
claims process and token economy, not a listening verdict.
