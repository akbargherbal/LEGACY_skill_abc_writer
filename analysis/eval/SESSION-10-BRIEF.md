# Session 10 brief — read this first (analyst only)

> **Do not put this file in the agent's working directory.** The agent gets
> `task.md`, `input/`, `skills/`, `opencode.json` and `quality_targets.json`
> only. This brief is for the analyst.

## Where we are

Session 09 (0.6.0) produced a complete package but **did not test the plan**:
the first `skill` call failed, the cwd was the parent with `README`/`BRIEF`/
`checklist`, the model switched mid-run after a 429, and the user pasted an
external expert critique at message 125. The run was invalid under A.

The autonomous first pass was still **6/10** by ear. The external critique then
took it to **7–7.5**, at a cost of **87,118** extra generated tokens. The first
pass had already improved the five craft numbers (register, qafla, top
duration, tessitura), but the ear did not move; the aggregate `rhythm_variety`
read 1.00 on 13 merged phrases while the expert counted 17/25 lines sharing two
cells. The checker itself flagged `unbroken 14.25s` and 16 pause violations as
WARN; the skill told the agent not to rewrite for a WARN, so it passed.

Session 09 measured:

| Metric | 09 |
|---|---:|
| Generated (`output + reasoning`) | **232,396** |
| Generated / (score+seed) | **30.9×** |
| Generated / score | **111.6×** |
| Visible output | **58,974** |
| Reasoning | **173,422** |
| Largest reasoning block | **28,201** (full-form design before `craft.md`) |
| Checker runs | **17** |
| Full score writes | **5** |
| Custom scripts | **37 heredocs + 20 sed** |
| `end_long` | 0.46 |
| `rhythm_variety` | 0.96 (final; 1.00 on 13 merged phrases in the first pass) |
| `distinct_bar_share` | 0.966 (final; 0.64 first pass) |
| `top_duration` | 0.42 (final; 0.65 first pass) |
| `tessitura ≥ C5` | 0.293 (final; 0.235 first pass) |
| Ear | **6 first pass; 7–7.5 only after human critique** |

The recurring patterns across 07–09 were structural: first `skill` failed 3/3,
pre-core design block 32k/32k/28k, checker runs 7/7/17, writes 2/2/5, scripts
19/14/37+20. 0.6.0 changed the prose, not the structure.

> **Model confound:** session 10 uses the paid `deepseek/deepseek-flash#high`
> by design (no 429, no mid-session switch). Sessions 08 and 09's autonomous
> first pass used the free `deepseek-v4.1-flash-free`. Treat 08/09 as a
> baseline, not a controlled A/B. Record the exact model in A; a TUI header
> that says `DeepSeek V4.1 Flash Free` is a failed validity check, not a
> comparable run.

## What 0.7.0 changed

One contract, three acceptance layers, one tool per question, one state:

1. **One order — core first.**
   `syllabify → core (8–16) → core_review → plan → score → seed → sheet/notes`.
   `core_draft.abc` is the first composition file, not an extraction from a
   finished score. `plan.json` and `score.abc` come after the core review.
2. **Three acceptance layers.**
   - `checker.py` — contract; unchanged logic and `calibration.json`.
   - `quality.py` — objective quality targets (unbroken, pause hierarchy,
     distinct bars, top duration, tessitura). Hard in a quality run.
   - `references/critic.md` — taste: 8 points, 5 numbered notes, no gate.
   The old absolute “do not rewrite for a WARN” now applies only to a validity
   run; a quality run must close its declared objective targets.
3. **One tool per question.**
   - `craft.py --phrases` — per-line bars, syllables, start beat, rhythm cell,
     rest before/after, unbroken, register, repeats, leaps, cadence.
   - `repair.py` — turns a global failure into bars/phrases.
   - `quality.py` — objective PASS/FAIL.
   - `abc_doctor.py` — explains parser errors; `abc_tools.py` parser unchanged.
   - `verify_package.py` — score↔seed, Drums, core, docs, plan, report,
     `--state`, `--review`, `--require-core-first`.
4. **One state.** `state.json` + `STATE.md` from the start; after compaction,
   read `state.json` first; no re-run of a passed check.
5. **One harness config.** `opencode.json` in the session folder registers the
   skill from `./skills` and fixes the paid model. No global symlink, no
   `@path`, no `/skill`, no late model addition. A smoke test on the extracted
   package printed `SKILL_OK`; the first `skill` call now succeeds.
6. **One critic pass.** The core is reviewed before expansion. The 09 external
   critique is the template; the review costs ~2k on 8–16 bars, not 20k+ on 82.

## The economy rule

The denominator is **B: 10× (score + seed)**, not score-only. The 09 score+seed
was 7,513 → the 09 10× line was **75,130**; the final line for session 10 is
computed from its own score+seed. score-only is recorded as a diagnostic: in 09
the first-pass visible output alone was 1.53× the score-only line, so score-only
10× is impossible even with zero reasoning.

Pass: generated (`output + reasoning`) ≤ 10× (score + seed). Visible output,
reasoning, largest block and cache are diagnostics; the largest block must not
return to the 28k style even if the sum passes.

## What session 10 should answer

1. **Validity.** Did the first `skill` call succeed? Was the cwd clean? Was the
   model the paid `deepseek/deepseek-flash#high`, with no switch? Is the export
   complete and one session?
2. **Order.** Is `core_draft.abc` the first composition file? Did
   `plan.json`/`score.abc` come after `core_review.md`? Is the largest reasoning
   block <10k, and pre-score generated <10k?
3. **Checker/quality policy.** ≤4 checker runs, one full score write, no run
   after a pass; `quality.py` one verification after the fix.
4. **Toolchain.** Zero custom parser/stats scripts; `craft --phrases`,
   `repair`, `quality`, `verify`, `doctor` used.
5. **Economy B.** Generated ≤10× (score+seed); visible/reasoning/largest block
   recorded.
6. **Quality.** Do all five `quality.py` targets pass? Does the per-line table
   show varied cells/rests? Does the ear reach ≥7.5 (target 9)? Is the chorus
   a new motif and the final qafla held?
7. **State/compaction.** `state.json`/`STATE.md` fresh; no re-run of a passed
   check; post-compaction cost <2k.

## What to compare

| Metric | 08 | 09 | 10 target |
|---|---:|---:|---|
| Generated (`output+reasoning`) | 131,138 | 232,396 | **≤10× (score+seed)** |
| Generated / (score+seed) | 25.0× | 30.9× | **≤10×** |
| Visible output | 22,551 | 58,974 | <22,551 (08) |
| Reasoning | 108,587 | 173,422 | <108,587 |
| Largest reasoning block | 31,965 | 28,201 | **<10k** |
| Checker runs | 7 | 17 | **≤4** |
| Full score writes | 2 | 5 | **1** (2 max) |
| Custom scripts | 14 | 37+20 | **0** |
| `end_long` | 0.04 | 0.46 | 0.25–0.50 |
| `rhythm_variety` | 0.77 | 0.96 | ≥0.85 |
| `distinct_bar_share` | 0.60 | 0.966 | ≥0.75 |
| `top_duration` | 0.78 | 0.42 | ≤0.60 |
| `tessitura ≥ C5` | 0.935 | 0.293 | ≤0.60 |
| `quality.py` | — | 4/5 (pause fails) | **5/5** |
| Ear | 6 | 6 first / 7–7.5 human | **≥7.5, target 9** |

The 09 final's only objective miss was `pause hierarchy`: 0 short gaps but 48%
identical > the 40% target. Session 10's `quality_targets.json` sets 40% and at
least 3 distinct values; that is the gap to close.

## Files

| File | What |
|---|---|
| `analysis/eval/inbox/deepseek_session_10/agent/task.md` | the exact prompt |
| `.../agent/input/` | lyrics and style |
| `.../agent/opencode.json` | skill discovery + paid model |
| `.../agent/quality_targets.json` | the five objective targets |
| `.../session-10-ready.zip` | the ready zip, SHA-256 `80b930…1c53e` |
| `.../abc-score-writer-0.7.0.zip` | 0.7.0, SHA-256 `65a953…e3c1a` |
| `.../README.md` | package and start |
| `.../VM-SETUP.md` | VM commands |
| `.../checklist.md` | run/measure/stop |
| `analysis/eval/plans/2026-11-25-root-repair-v2.md` | the repair plan |
| `analysis/eval/reports/2026-11-25-session-10-package.md` | what was built and W5 |
| `02_maqam-score/` | the 0.7.0 source |
| `dist/abc-score-writer-0.7.0.zip` | release zip |

---

## Evaluation checklist — did the 0.7.0 plan work?

Fill this after session 10. A component passes only when the measured evidence
passes. Attribute a failure before changing anything:
**plan** (contract/order/tool), **model** (ignored a clear instruction), or
**harness** (skill load, cwd, model, compaction, export).

### A. Run validity — if any fails, the run did not test the plan

- [ ] The first `skill` call succeeded.
- [ ] The cwd had only `task.md`, `input/`, `skills/`, `opencode.json`,
      `quality_targets.json`; no `README`/`BRIEF`/`checklist`.
- [ ] The skill was 0.7.0: `SKILL.md` `ebc040…545fdd`; zip `65a953…e3c1a`.
- [ ] The model was `deepseek/deepseek-flash#high` (paid), not the free
      `DeepSeek V4.1 Flash Free`; no mid-session switch.
- [ ] The export is complete; one session id; no aborted request.
- [ ] No analyst file inside `agent/`; no previous score.
- [ ] `opencode.json` is present and has `skills: ["./skills"]`.

**If any fails:** stop. Record the harness defect; the plan was not tested.

### B. Order fix — the pre-writing block

| Check | Pass threshold | 09 baseline | 10 result |
|---|---|---|---|
| `core_draft.abc` first composition file | true | false (score then core) | |
| `core_review.md` before `plan.json`/`score.abc` | true | no critic | |
| `plan.json`/`score.abc` before core | false | plan/score before core | |
| Largest reasoning block | <10k | 28,201 | |
| Pre-score generated | <10k | 48,374 | |
| First file | <3:39 (09) | 3:39 | |
| First score | <3:42 (09) | 3:42 | |

**Pass:** the core is first, the review precedes the plan/score, the sheet is
after the score, and the largest block is <10k. The call index is diagnostic;
the block is the test.

### C. Checker/quality policy

- [ ] Checker runs ≤4.
- [ ] No run after a pass.
- [ ] Every run followed a named fix (quote it).
- [ ] Full score writes 1 (2 max: one global sanity rewrite).
- [ ] No full rewrite beyond the one global.
- [ ] `quality.py` one verification after its fix; no loop.
- [ ] The global rewrite, if any, is recorded with the metric that forced it.

**Pass:** all. A second full rewrite is a plan failure.

### D. Toolchain — the scripts

- [ ] **0 custom parser/stats scripts.** Definition: any shell/Python heredoc
      that parses ABC or computes a measurement. `checker.py`, `quality.py`,
      `repair.py`, `craft.py`, `abc_tools.py`, `abc_doctor.py`, `syllabify.py`
      do not count; `cat`/`jq`/`diff`/`wc` do not count.
- [ ] `craft.py --phrases` ran; the per-line table exists (in `craft.json` or
      `core_table.json`).
- [ ] `quality.py` ran; `quality.json` exists.
- [ ] `repair.py` ran on each global failure; `repair.json` exists.
- [ ] `verify_package.py` ran with `--state` and `--review`; `verify.json` ok.
- [ ] If a script appears, name the missing check. Plan gap or agent
      violation?
- [ ] No file in `agent/` is a parser under another name.

**Pass:** 0 scripts and the tools used. If one script appears, a missing tool
is a **plan** failure, not a model failure.

### E. Register

- [ ] `plan.json` `register.mean` = 70.
- [ ] No `74` as the composing default.
- [ ] Actual `register_mean` 70–72.
- [ ] `tessitura_share_ge_c5` ≤0.60.
- [ ] Checker register sanity (69–79) and style target (67–73) pass.

**Pass:** all five.

### F. Economy B

- [ ] Generated (`output + reasoning`) ≤ **10× (score + seed)**. Record the
      exact line; the 09 reference line was 75,130.
- [ ] Generated / (score + seed) ≤10×; score-only ratio recorded as diagnostic.
- [ ] Visible output <22,551 (08) and reasoning <108,587.
- [ ] No single reasoning block >10k.
- [ ] Cache share recorded; requests/tool calls counted.
- [ ] The largest block is named (what it was doing).

**Pass:** the first two. If the total passes but a 28k-style block returns, the
order fix failed even if the sum is low.

### G. Quality levers — craft, critic, ear

| Metric | 08 | 09 | 10 target |
|---|---:|---:|---|
| `end_long_share` | 0.04 | 0.46 | 0.25–0.50 |
| `rhythm_variety` | 0.77 | 0.96 | ≥0.85 |
| `distinct_bar_share` | 0.60 | 0.966 | ≥0.75 |
| `top_duration_share` | 0.78 | 0.42 | ≤0.60 |
| `tessitura_share_ge_c5` | 0.935 | 0.293 | ≤0.60 |
| `quality.py` | — | 4/5 (pause) | **5/5** |
| Ear (Suno render) | 6 | 6 first / 7–7.5 human | **≥7.5, target 9** |

- [ ] `quality.py` passes all five objective targets.
- [ ] The per-line table shows varied cells and rests; no 13-vs-25 merge.
- [ ] `core_review.md` has exactly 5 numbered lines, each tied to a bar; the
      composer addressed them.
- [ ] The chorus opening is a new motif, not a sequence of the verse head
      (check the first 3 bars of each chorus).
- [ ] The final qafla is held; the last note is not an eighth.
- [ ] The ear verdict is from a **Suno render of `seed.abc`**, not the checker.
- [ ] At least 3/5 craft metrics improve; the ear is ≥7.5.

**Pass:** `quality.py` 5/5 **and** ear ≥7.5. The target 9 is the next phase;
6 is failure. If the ear is <7.5, the quality experiment failed; the next
decision is method/model, not more gates.

### H. State / compaction

- [ ] `state.json` and `STATE.md` exist and are updated after each milestone.
- [ ] After a pass, no check is re-run.
- [ ] If compaction happened: no re-run of a passed check; no scripts after it;
      extra generated after it <2,000.
- [ ] If no compaction: PASS by default.

### I. Plan verdict — fill the table

| Fix | Pass? (yes/partial/no) | Evidence (numbers) | Attribution (plan/model/harness) |
|---|---|---|---|
| Order / pre-writing block | | core first; largest block; pre-core tokens | |
| Checker/quality policy | | runs; writes; post-pass; quality | |
| Toolchain / scripts | | script count; craft/repair/quality/verify | |
| Register | | plan 70; mean; tessitura | |
| Economy B | | generated; ratio; 10× line | |
| Quality levers | | quality.py; craft; ear | |
| State / compaction | | state; post-compaction cost | |

**Plan success:** A valid, B/C/D/E/F pass, `quality.py` 5/5, ear ≥7.5.
**Plan partial:** A valid, 4–5 of B–F pass; name the failed component and fix
that component only.
**Plan failure:** A invalid, or F >10×, or `quality.py` <5/5, or ear <7.5.
The decision is method/model, not another gate.

### J. The three answers to write next session

1. **What worked** — three bullets with the numbers.
2. **What failed** — three bullets with the numbers and the attribution.
3. **The single next change** — one change, not a list. If the plan failed on a
   contract/tool, fix that; if the model ignored a clear instruction, change the
   model; if the harness failed, fix the config/cwd/model/compaction.
