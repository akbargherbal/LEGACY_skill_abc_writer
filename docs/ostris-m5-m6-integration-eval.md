# OSTRIS M5–M6 — integration and objective evaluation

**Date:** 2026-11-23 · **Stage:** M5 (integration) and M6 (objective evaluation)

## M5 — integration

The skill surface is now three commands plus a wrapper:

```bash
scripts/ostris_cli.py plan     --manifest song.json --out plans/song
scripts/ostris_cli.py exemplar --function cadence --bars 2
scripts/ostris_cli.py check    score.abc --plan plans/song/skill_plan.json --report report.json
```

- `scripts/ostris` resolves the repository root and runs
  `02_maqam-score/scripts/ostris_cli.py` on the CPU; it works from any directory.
- `SKILL.md` §8 documents the three commands and the limits.
- `check` accepts `--require-final-rest` and passes it to the pinned checker.
- `brief.json` is never passed to `check`; the command rejects it and asks for
  `skill_plan.json`.
- `make ostris-plan` / `ostris-check` wrap the same calls with `MANIFEST`,
  `PLAN_OUT`, `SCORE`, and `REPORT` variables.

End-to-end coverage in tests: a manifest → `plan` → a known-good 8-bar score →
`check`, and the same score with `--require-final-rest` failing as expected.
The gate “plan → write → check → patch without corpus in context” is satisfied
at the CLI level; a live composition session is outside CI.

## M6 — evaluation

`ostris eval --build-split` is deterministic and uses only the 35 held-out
YT500 tracks, which never entered the library or the priors.

| Item | Result |
|---|---|
| Held out | 35 |
| Usable (ABC present) | 31 |
| No ABC | 4 |
| Generation reserve | 14 (first by source rank; D13 default 12–16) |
| Retrieval reserve | 17 |
| Overlap | none |

`ostris eval --runs runs/` scores supplied run folders. Each run is
`<id>/score.abc` + `<id>/skill_plan.json` (or `plan.json`). It reports the
checker class, contract+sanity pass, bars deviation, characters, and a
`tokens_proxy` (characters ÷ 4 for the score only).

Measured:

| Metric | Value |
|---|---|
| Runs scored (smoke run) | 1 |
| Contract+sanity pass | 1/1 |
| Median bars deviation | 0 |
| Quality evaluated | **no** |
| Token reduction measured | **no** |

## What is deliberately missing

- **Blind quality / non-inferiority.** Needs human listeners or a judge; the
  report sets `quality_evaluated: false` instead of inventing a result.
- **Token reduction.** Needs both prompt-only and tool-assisted model runs with
  real token accounting; `tokens_proxy` is not substituted for it.
- **Maqam-stratified evaluation.** No reviewed labels, so the split is
  unlabelled by construction.

The M6 gate is therefore the objective half only: 100% contract+sanity on
supplied runs, a deterministic disjoint split, and an explicit record of what
was not measured.
