# Session 09 brief — read this first (analyst only)

> **Do not put this file in the agent's working directory.** The agent gets
> `task.md`, `input/` and `skills/` only. This brief is for the analyst.

## Where we are

Session 08 (0.5.3) delivered a complete, checker-passing package and the user
rated the music **6/10**. The process improved: the first checker ran 2:30
after the first score (08) vs 18 minutes (07), the first score came 8:24 in vs
15:38, and generated tokens fell 46% (241,400 → 131,138). But it was still
**69.3×** the 1,891-token score. The visible output alone was 11.9×.

The measured causes were structural, not model laziness:

| Cause | Cost in 08 |
|---|---:|
| `seed_sheet`/`plan` before `core`; designing the whole form first | 47,302 (36.1%) |
| A global `repeated_share` failure forced a full rewrite | 34,132 (26.0%) |
| No verifier for seed/drums/docs; 14 hand-written scripts | 12,170 (9.3%) |
| First `skill` call failed; stale compaction summary | 13 calls + 12k |

The craft profile was also still around 6/10: `end_long 0.04` (25/26 lines end
on an eighth), `rhythm_variety 0.77`, `unique bars 0.60`, tonic endings 35%,
`tessitura 93.5% ≥ C5`, a chorus that opens as a sequence of the verse.

## What 0.6.0 changed

One contract, one toolchain, one state:

1. **One order.** `syllabify → plan → core (8–16) → score → seed → sheet/notes`.
   `seed_sheet.md` is written after `score.abc`; the 82-bar frame is not a
   precondition for the core.
2. **One checker policy.** After the first score; each later run follows a
   named fix; stop after a pass; a global sanity failure allows one full
   rewrite + one verification; max 4.
3. **One register default.** 70 (the example plan); the sanity band 74 ± 5
   stays; 74 is not the composing default.
4. **One toolchain.** `checker.py` (score), `verify_package.py`
   (score↔seed, Drums, core, docs, plan), `craft.py` (report-only tune mirror).
   No hand-written parsers.
5. **One state.** `STATE.md` after each artifact/check; read it first after a
   compaction.

The quality experiment in session 09 has three levers: **register 70**,
**held qafla**, **rhythm variety**; plus a **new chorus opening**. No new
gates; the ear is the verdict.

## The economy rule

The user chose **B**: generated (`output + reasoning`) ≤ **52,460** = 10×
(score + seed). The score-only ratio (69.3× in 08) is recorded as a diagnostic,
not the pass/fail line, because the visible output alone exceeded it.

## What session 09 should answer

1. Did the order fix remove the pre-writing block? (First `core` by the 8th
   composition call; first score time; the largest reasoning block.)
2. Did the toolchain remove the 14 scripts? (0 scripts; `verify_package` and
   `craft` outputs.)
3. Did the checker policy keep the runs ≤4? (The global rewrite allowance.)
4. Did the three quality levers move the craft numbers and the ear? (Compare
   `end_long`, `rhythm_variety`, `distinct_bar_share`, `tessitura` with 08.)
5. Did the run stay ≤52,460 generated? (The B denominator.)
6. Was the first `skill` call successful and the cwd clean? (If not, the run is
   invalid.)

## What to compare next session

| Metric | 08 | 09 | What it means |
|---|---:|---:|---|
| Generated (output+reasoning) | 131,138 | | economy |
| Generated / (score+seed) | 25.0× | | ≤10× goal |
| Visible output | 22,551 | | writing floor |
| Reasoning | 108,587 | | thinking share |
| Largest reasoning block | 31,965 | | pre-writing design |
| Checker runs | 7 | | ≤4 |
| Full score writes | 2 | | 1 (2 max) |
| Custom scripts | 14 | | 0 |
| `end_long` | 0.04 | | qafla |
| `rhythm_variety` | 0.77 | | grid |
| `distinct_bar_share` | 0.60 | | literal loops |
| `tessitura ≥ C5` | 0.935 | | register |
| Ear | 6/10 | | the verdict |

## Files

| File | What |
|---|---|
| `analysis/eval/inbox/deepseek_session_09/agent/task.md` | the exact prompt |
| `.../agent/input/` | lyrics and style |
| `.../abc-score-writer.zip` | 0.6.0, SHA-256 `a44644f6…b34888` |
| `.../README.md` | clean-room setup and export |
| `.../VM-SETUP.md` | VM commands |
| `.../checklist.md` | run/measure/stop |
| `analysis/eval/plans/2026-11-24-session-09-skill-repair.md` | the repair plan |
| `analysis/eval/reports/2026-11-24-skill-0.6.0.md` | what changed and the tests |
| `02_maqam-score/` | the 0.6.0 source |
| `dist/abc-score-writer-0.6.0.zip` | the release zip |
