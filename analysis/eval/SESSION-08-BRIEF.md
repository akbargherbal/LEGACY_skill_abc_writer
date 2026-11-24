# Session 08 brief — read this first

> **Analyst/assistant only. Do not put this file in the agent's working
> directory.** The agent gets `task.md`, `input/` and `skills/` only. The brief
> exists so a new session can understand the story without a long preamble.

## What we are doing

We are evaluating `abc-score-writer` with real agents. Two goals, in order:

1. **Quality.** The ear decides. The checker is a diagnostic, not the verdict.
2. **Economy.** A score is small; the thinking/process must not be arbitrarily
   larger. A 2–3 k-token score should not cost 200 k tokens of reasoning.

The immediate aim of session 08 is to test one process change: **use the
existing tools as measuring instruments, write early, and repair locally** —
without changing the model, the lyrics, the key or the tempo.

## What happened in session 07

- The DeepSeek/OpenCode run delivered everything and passed the checker, but the
  user rated the music **5.5–6 / 10**.
- `score.abc` was ~**2.1 k tokens**. The run generated **241,400** tokens
  (39,165 visible + 202,235 reasoning): **~115×** the score.
- 19 hand-written parser/stats scripts (57,425 reasoning + 14,772 output)
  duplicated what `checker.py --json report.json` already reports.
- The checker was first run **18 minutes after** the first score. Before that,
  the agent rewrote the whole score and repaired six broken bars.
- 5 checker runs, 2 full score writes, 39,930 reasoning in a tuning loop to hit
  `mean 69.1`, `2-share 0.64`, `chorus lift 5.0` — all on the limits.
- Cause was mostly **our contract**, not the model:
  - “Run the checker once at the end” made it a final exam, so the agent wrote
    its own checker.
  - “Don’t read the parser” plus no early measurement led to a buggy parser.
  - `strict_shape: true` in the manual template made shape targets hard, so the
    agent tuned numbers.
  - `syllabify.py` emitted body bars only, so the agent hand-typed 26 offsets.
  - The core draft was not defined as the opening of the score, so the agent
    designed the full piece before writing.
  - “Hum it” was impossible for a text-only, offline model.
  - The working directory contained the checklist and analyst notes; the skill
    loader also failed. Both are harness defects.

## What we changed in 0.5.3

- **Checker is a measurement instrument.** Run it after the first `score.abc`
  and after a named fix; read `report.json.measured`; no custom parser/stats;
  fix only named bars; stop after a pass.
- **`strict_shape: false` by default.** Shape targets are warnings; `true` only
  for a strict release.
- **`syllabify.py --sections`** writes absolute `bar_start`/`bar_end` from the
  section starts; no 26-entry offset dict.
- **Core = the first 8–16 bars of `score.abc`**, written before planning the
  full form.
- **Exactly 10 numbered lines** for `seed_sheet.md` and `notes.md`; no title.
- **No mental audition.** Read the cell in notation; the analyst listens.
- **10× is a manual analyst stop rule.** The analyst watches and ends the
  session if it drags; there is no automatic monitor. This is deliberate
  simplicity.

## Session 08 experiment

- **Model:** same as 07 (`deepseek-flash` / `high`). Do not change it in this
  run.
- **Skill:** 0.5.3 source; zip
  `dist/abc-score-writer.zip`, SHA-256
  `14956cec853d7b6231ea58c79f29308d40cfce252f01dba47b19c8e1fbd0242b`.
- **Task:** `analysis/eval/inbox/deepseek_session_08/task.md`; same D Kurd /
  80 BPM lyrics as 06–07.
- **Clean room:** the agent's cwd has only `task.md`, `input/`, `skills/`. No
  README, checklist, analyst notes, exporter or previous artifacts.
- **One change:** checker-first + no custom parser + targeted edits + core
  first. Not the model.
- **Stop rules:** no `core_draft.abc` by the 8th tool call → stop; full score
  rewrite → record; the analyst ends the run manually at ~10× the score.

**Success:** quality ≥6/10 by ear **and** generated / score ≤10×, with 0 custom
scripts, 1 full score write and ≤3 checker runs.

**Failure:** quality <6/10 even if cheap → change method/model, do not lower the
quality bar. Generated >10× even if good → process still wrong.

## Where the files are

| File | What |
|---|---|
| `analysis/eval/reports/2026-11-24-deepseek-session-07.md` | full 07 evidence and H1–H4 |
| `analysis/eval/inbox/deepseek_session_08/task.md` | the exact prompt for the agent |
| `analysis/eval/checklists/2026-11-24-session-08-economic.md` | run/measure/stop checklist |
| `analysis/eval/inbox/deepseek_session_08/README.md` | clean-room setup and export |
| `analysis/eval/inbox/deepseek_session_08/input/` | lyrics and style |
| `02_maqam-score/` | skill 0.5.3 source |
| `dist/abc-score-writer.zip` | packaged 0.5.3 |

## Current status

Stage 0 is done: skill/tool text fixed, `--sections` added and tested, tests and
selftest pass, acceptance passes, zip built. Session 08 has **not** been run.

Next: run session 08 clean, keep the model, let the analyst stop it if it
drags, then measure quality by ear and the generated/score ratio. If it stays
≥6/10 and ≤10×, the process fix worked; if not, the next decision is about the
method or the model — not about adding more gates.
