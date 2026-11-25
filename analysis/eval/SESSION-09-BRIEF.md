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

---

## Evaluation checklist — did the 0.6.0 plan work?

Fill this after session 09. A plan component passes only when the measured
evidence passes. If a check fails, attribute it before changing anything:
**plan** (contract/order/tool), **model** (ignored a clear instruction), or
**harness** (skill load, cwd, compaction, export). Do not fix the model for a
plan defect, or the plan for a model defect.

### A. Run validity — if any fails, the run did not test the plan

- [ ] The first `skill` call succeeded.
- [ ] The cwd had only `task.md`, `input/`, `skills/`.
- [ ] The skill was 0.6.0: `SKILL.md` `d960e7b8…4892e9`; zip `a44644f6…b34888`.
- [ ] The model was `deepseek-v4.1-flash-free` / `high`.
- [ ] The export is complete; no aborted request; one session id.
- [ ] No analyst file inside `agent/`; no previous score.

**If any fails:** stop. Record the harness defect; the plan was not tested.

### B. Order fix — the pre-writing block

| Check | Pass threshold | 08 baseline | 09 result |
|---|---|---|---|
| `core_draft.abc` is the first 8–16 bars | true | true | |
| Core writing order | `seed_sheet`/`plan` do not precede the core; sheet **after** score | sheet before | |
| Largest reasoning block | <10k (08: 31,965) | 31,965 | |
| Pre-score generated | <10k (08: 47,302 to first score) | 47,302 | |
| First file | <7:13 (08) | 7:13 | |
| First score | <8:24 (08) | 8:24 | |

**Pass:** the core is a prefix, the sheet is after the score, and the largest
block is <10k. The call index is diagnostic: 08's core was the 5th
composition call but still had a 31,965 block, so **the block is the real test,
not the call count**.

### C. Checker policy

- [ ] Checker runs ≤4.
- [ ] No run after a pass.
- [ ] Every run followed a named fix (quote the fix).
- [ ] Full score writes ≤2 (1 normal + 1 global sanity rewrite).
- [ ] No full rewrite beyond the one global.
- [ ] The global rewrite, if any, is recorded with the metric that forced it.

**Pass:** all six. A global rewrite is allowed once; a second is a plan failure.

### D. Toolchain — the 14 scripts

- [ ] **0 custom parser/stats scripts.** Definition: any shell/Python heredoc
      that parses ABC or computes a measurement. `checker.py`,
      `verify_package.py`, `craft.py`, `abc_tools.py`, `syllabify.py` do not
      count; `cat`/`jq`/`diff`/`wc` do not count.
- [ ] `verify_package.py` ran; `verify.json` exists and `ok` is true.
- [ ] `craft.py` ran; `craft.json` exists.
- [ ] If a script was written, name the missing check. Was it a plan gap
      (no tool) or an agent violation (tool existed)?
- [ ] No file in `agent/` is a parser under another name.

**Pass:** 0 scripts and both tools used. If one script appears, a missing tool
is a **plan** failure, not a model failure.

### E. Register

- [ ] `plan.json` `register.mean` = 70.
- [ ] No `74` in the agent's plan or notes as the default.
- [ ] Actual `register_mean` 70–72.
- [ ] `tessitura_share_ge_c5` ≤0.60.
- [ ] The checker register sanity (69–79) and style target (67–73) both pass.

**Pass:** all five. If the mean is >73, the register lever failed; check whether
the agent used the example plan or overrode it.

### F. Economy B

- [ ] Generated (`output + reasoning`) ≤ **52,460**.
- [ ] Generated / (score + seed) ≤10×.
- [ ] Visible output <22,551 (08) and reasoning <108,587.
- [ ] No single reasoning block >10k.
- [ ] Cache share recorded; requests/tool calls counted.
- [ ] The largest block is named (what it was doing).

**Pass:** the first two. The rest are diagnostic; if the total passes but a
32k-style block returns, the order fix failed even if the sum is low.

### G. Quality levers — craft and ear

| Metric | 08 | 09 target | 09 result |
|---|---:|---|---|
| `end_long_share` | 0.04 | 0.25–0.50 | |
| `rhythm_variety` | 0.77 | ≥0.85 | |
| `distinct_bar_share` | 0.60 | ≥0.75 | |
| `top_duration_share` | 0.78 | ≤0.70 | |
| `tessitura_share_ge_c5` | 0.935 | ≤0.60 | |
| Ear (Suno render) | 6/10 | ≥6 (target 9) | |

- [ ] The ear verdict is from a **Suno render of `seed.abc`**, not the checker.
- [ ] The chorus opening is a new motif, not a sequence of the verse head
      (check the first 3 bars of each chorus).
- [ ] The final qafla is held; the last note is not an eighth.
- [ ] At least 3 of the 5 craft metrics improve; the ear is ≥6.

**Pass:** the ear ≥6 **and** at least 3/5 craft metrics improve. The target 9
is the next phase, not this gate. If the ear is <6, the quality levers failed;
the next decision is method/model, not more gates.

### H. State / compaction

- [ ] `STATE.md` exists and is updated after each milestone.
- [ ] If compaction happened: no re-run of a passed check; no scripts after it;
      the extra generated after it is <2,000.
- [ ] If no compaction: this section is PASS by default.

### I. Plan verdict — fill the table

| Fix | Pass? (yes/partial/no) | Evidence (numbers) | Attribution (plan/model/harness) |
|---|---|---|---|
| Order / pre-writing block | | largest block; pre-core tokens | |
| Checker policy | | runs; writes; post-pass | |
| Toolchain / scripts | | script count; verify/craft | |
| Register | | plan 70; mean; tessitura | |
| Economy B | | generated; ratio; 52,460 | |
| Quality levers | | craft; ear | |
| State / compaction | | STATE; post-compaction cost | |

**Plan success:** A valid, B/C/D/E/F pass, ear ≥6.
**Plan partial:** A valid, 4–5 of B–F pass; name the failed component and fix
that component only.
**Plan failure:** A invalid, or F >52,460, or ear <6. The decision is
method/model, not another gate.

### J. The three answers to write next session

1. **What worked** — three bullets with the numbers.
2. **What failed** — three bullets with the numbers and the attribution.
3. **The single next change** — one change, not a list. If the plan failed on a
   contract/tool, fix that; if the model ignored a clear instruction, change
   the model; if the harness failed, fix the install/cwd/compaction.
