# Session 13 — measured cost and the measurement-latency fix

**Run:** `analysis/eval/inbox/deepseek_session_13/opencod_session_13.json`
**Model:** `deepseek/deepseek-flash#high`, agent `composer`
**Skill:** `abc-score-writer` 0.8.1 (session start), `deepseek-flash#high`
**Task:** D Kurd, 80 BPM, 4/4, 26 lines, 361 syllables.
**Outcome:** the run stopped at the 40-step guard after writing 26/26 lines;
the score was never repaired or released. No audio, so no ear verdict.

## Measured

| Field | Value |
|---|---|
| Generated tokens | **57,075** (output 13,196 + reasoning 43,879) |
| Score | 1,427 tokens (64 bars, 311 vocal notes) |
| Ratio | **40.0×** (10× budget 14,270) |
| Largest messages | 8,000 reasoning (m6), 8,000 reasoning (m23), 4,758 (m11) |
| Direct score writes | 0 |
| Hand parsers/stats | 0 |
| CLI writes | 26 `line` + 11 `patch` |
| Checker runs | 1 full + 3 `--bars` (budget 4) |

The economy failed even though the tool discipline improved: the waste is not
scripts, it is **detection latency** and two capped reasoning calls.

## First full `check` (reproduced exactly)

| Check | Measured | Band |
|---|---|---|
| notes / syllable | 311/361 = **0.86** | 1.00–1.55 |
| simultaneity | **176** units, 17 bars | ≤ 4 |
| register mean | **68.0** | 74 ± 5 |
| distinct durations | **3** | ≥ 4 |
| repeated-pitch share | **4.5 %** | ≥ 20 % |
| line note deficit | lines 5–8 short by 3 | 0 |
| pause after line | 23 of 26 short | per line |

A clean `init` plus the logged 26 `line` / 11 `patch` calls reproduces the same
311 vocal notes and the same six hard failures, so the numbers are verified,
not inferred.

## Why it happened

The composer wrote correctly through `score_cli.py`, but the only measurement
arrived at the full check. The score ran 0.86 notes/syllable from line 5, the
guitar pedals overlapped the voice from bar 30, the register sat at 68 and the
duration set was `{2,4,6}` — all visible in the checker's own numbers, none
printed at the write call. The late repair then competed with the 8,000-token
per-call ceiling; two reasoning calls alone consumed 16,000 tokens.

## Fix implemented (0.9.0)

- `line` / `patch` now print a live meter: line deficit, projected ratio, need
  band, repeated share, duration inventory, register mean, ties, gap, overlaps.
- `--dry-run` and opt-in `--guard`.
- `lint` reports per-bar simultaneity.
- `release --dry-run`; `init` form-budget advisor.
- `explain-metric` + `references/metrics.md`; `align`; `view --roll/--contour`.

Plan and acceptance test:
`analysis/eval/plans/2026-11-25-session-13-tools-plan.md`.

## Not claimed

- No musical quality change. The score is still unlistened and unrepaired.
- The 40× ratio is the baseline this tool change is measured against; the next
  session must show the reduction, not this report.
