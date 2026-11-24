# Session 08 — economic contract (one change)

**Skill:** `abc-score-writer` 0.5.3 source (contract 0.4.0; checker/calibration
unchanged). Zip: `dist/abc-score-writer.zip`, SHA-256
`14956cec853d7b6231ea58c79f29308d40cfce252f01dba47b19c8e1fbd0242b`.
**Harness:** OpenCode.
**Model:** same as session 07 (`deepseek-flash` `high`) for attribution; do not
change the model in this run.
**Task:** `task.md`, same D Kurd / 80 BPM lyrics as session 06–07.
**Date:** 2026-11-24.

**Goal 1:** score excellence; the ear is the verdict.
**Goal 2:** economic feasibility. The score is the artifact; the process must be
proportionate.

**This run changes one thing:** the **economic contract** — checker-first
measurement, no custom parser, targeted edits only, and a 10× generated-token
budget. The skill text/tool fixes in Stage 0 (checker role, `strict_shape`,
absolute bars, core definition, wording, clean room) are corrections, not the
experiment.

---

## 0. Non-negotiables

- [ ] The ear decides the music; the checker is a measurement instrument.
- [ ] No gate for taste; no metric as the goal; no token cap on the artifact.
- [ ] No retrieval: no exemplar, no phrase bank, no corpus idiom call.
- [ ] Do not edit `checker.py`, `calibration.json` or `abc_tools.py` during the run.
- [ ] Same input as session 07: D Kurd, 80 BPM, same lyrics.

---

## 1. Clean room (must pass before the prompt)

- [ ] The skill is installed and **loadable** as `abc-score-writer`; the first
      `skill` tool call must succeed. If it fails, stop: it is a harness defect.
- [ ] The working directory contains **only** `task.md`, `input/` and `skills/`.
      No `README.md`, `checklist.md`, analyst `notes.md`, exporter, previous
      score, seed, sheet or report.
- [ ] `task.md` pasted verbatim; the agent receives D Kurd / 80 BPM.
- [ ] Model + variant recorded; offline/no renderer recorded.
- [ ] The analyst has the 10× budget rule and a stopwatch on generated tokens.

---

## 2. Process checks

- [ ] `lyrics.txt` saved once; `syllabify.py` run once.
- [ ] `syllabify.py --sections ...` wrote absolute `bar_start`/`bar_end`; no
      hand-typed offset table.
- [ ] `seed_sheet.md` is exactly 10 numbered lines (no title/blank).
- [ ] `plan.json` exists; `strict_shape` is false; gate targets at defaults.
- [ ] `core_draft.abc` exists (8–16 bars) and is the opening of `score.abc`.
- [ ] **No task list.**
- [ ] `score.abc` is two voices (`Vocal` + `Ins`), no third voice.
- [ ] `seed.abc` is the same melody + chords + `V: Drums`.
- [ ] **No custom ABC parser or statistics script.** The only measurement is
      `checker.py --json report.json`; read `report.json.measured`.
- [ ] The checker is run **after the first `score.abc`**, not only at the end.
- [ ] Repairs are targeted `edit` calls on the named bars/headers; **no full
      score rewrite** after the first complete file.
- [ ] Checker runs: **≤3** (first measurement, one after a repair, optional
      final). No re-run after a pass.
- [ ] `notes.md` is exactly 10 numbered lines, written after the score.

**Stop rule:** no `core_draft.abc` by the 8th tool call → stop and record
"process still front-loaded". Do not wait for a design block.

**Budget stop (manual):** the analyst watches the session. If generated tokens
(`output + reasoning`) exceed **10×** the token size of `score.abc`, end the
session manually and keep the current artifacts. No automatic monitor; the
analyst's judgment is the stop. This is a process stop, not a quality failure by
itself.

---

## 3. Measure exactly

From the native OpenCode session export (`info.tokens`, `messages[].tokens`):

| Field | Session 07 | Session 08 |
|---|---:|---:|
| Score tokens (`score.abc`) | ~2.1 k | |
| Seed tokens (`seed.abc`) | ~3.0 k | |
| Generated (`output + reasoning`) | 241,400 | |
| Ratio generated / score | 115× | |
| 10× budget (score only) | 21 k | |
| Cache read / traffic | 98.2% | |
| Requests / tool calls | 75 / 86 | |
| Custom parser/stats scripts | 19 | **0** |
| Full score writes | 2 | **1** |
| Checker runs | 5 | **≤3** |
| Quality (ear) | 6/10 | **≥6/10** |

- [ ] `cache_share = cache_read / (input + cache_read)`.
- [ ] Largest reasoning block: what it was doing.
- [ ] Every tool call counted; tag W1–W12 where applicable.
- [ ] Quoted evidence for any finding; no claim without a check.

---

## 4. Success and failure

**Success:** quality ≥6/10 by ear **and** generated / score ≤10×, with 0 custom
parsers, 1 full score write and ≤3 checker runs.

**Quality failure:** quality <6/10 even if the budget is met. Do not lower the
quality bar; change the method or the model.

**Economic failure:** generated / score >10× even if quality is good. Do not
declare success; the process is still the problem.

**Attribution:** if the agent writes a custom parser despite the contract, record
it as `agent_capability` and consider another model. If the contract is
ambiguous, fix the contract, not the model.

---

## 5. Blind listen

Same A/B/C protocol as session 07: A no seed, B old v2 seed, C new `seed.abc`.
The score is graded by ear, never by the checker. If no audio can be rendered,
mark goal 1 pending; do not claim an audition.

---

## 6. What not to change

- The checker, calibration, corpus numbers, lyrics, key and tempo.
- The music's target (the ear).
- No hard gate for taste; no "0 warnings" target.
