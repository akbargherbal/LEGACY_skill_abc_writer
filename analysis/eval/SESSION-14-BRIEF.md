# Session 14 brief — the meter pilot (analyst only)

> **Do not put this file in the agent's working directory.** The agent gets
> `input/`, `skills/`, `opencode.json`, `.opencode/` and `PROMPT.txt` only.
> This brief is for the analyst.

## What we are testing

Session 13 proved the model can write all 26 lines through `score_cli.py`, but
it learned six hard failures only at the first full `check`:

| Failure | Session 13 measured |
|---|---:|
| notes / syllable | **0.86** (311/361) |
| simultaneity | **176** units, 17 bars |
| register mean | **68.0** |
| distinct durations | **3** |
| repeated-pitch share | **4.5 %** |
| line note deficit | lines 5–8 short by 3 |
| pause after line | 23 of 26 short |

Generated: **57,075** tokens for a 1,427-token score = **40×**. The composer hit
`steps: 40` at message 44, before it could repair or release. The run is
reproducible: a clean `init` plus the logged 26 `line` and 11 `patch` calls
yields the same 311 vocal notes and the same six failures.

Session 14 tests **one process change**: 0.9.0 prints the checker's own numbers
after every `line`/`patch`, so the failure is visible at the line that caused
it. The model, lyrics, key, tempo and `steps: 40` are unchanged.

## Package

`dist/session-14-ready.zip` — SHA-256
`4b2db319…bc7a08` (4.7 MB).

- Skill **0.9.0**; `SKILL.md` SHA-256 `0e68623a…c6f3c6`.
- `opencode.json`: `default_agent: composer`, model
  `deepseek/deepseek-flash#high`.
- `composer.md`: `steps: 40` — same as session 13.
- `abc-guard.js`: 8,000-token per-call cap; writes `abc-session.log`.
- Clean root: **no** `plan.json`, `phrases.json` or `score.abc`. The composer
  must run `init` itself.
- `PROMPT.txt`: same one-line prompt as session 13.

If you want the longer cap instead, rebuild with:

```bash
make session14 SESSION_STEPS=55
```

That overwrites the zip; record which one was used.

## Run validity — check before interpreting anything

- [ ] The first `skill` call succeeded.
- [ ] The model is `deepseek/deepseek-flash#high`; no mid-run switch.
- [ ] The cwd has only the package contents; no analyst files, no previous
      score.
- [ ] The composer runs `init` itself; it does not find a pre-made plan.
- [ ] `init` prints `FORM BUDGET: 64 bars vs syllabify 82 (-22%)`.
- [ ] The composer either keeps 64 (and accepts the warning) or reruns with
      `--force --bars 82` **and** `--sections`. A bare `--bars 82` is a form
      error (all extra bars land in the outro).
- [ ] One session id; complete export.
- [ ] `steps: 40` in the packaged `composer.md`.

If a validity item fails, the run did not test the meter.

## What the meter should show

Every `line`/`patch` must print a block like:

```text
meter line 5 (bars 13-14): 10 notes / 13 syllables — deficit 3
score  65/67 notes → projected 350/361 (need 398-523)
       repeats 10%  durations 2:47 4:17 6:1 (3 of 5) add a 1 or 8  register 67.1  ties 0/1
       gap after 0.38s (target 0.50s — add z1)  overlaps 6 this line / 18 total (max 4)
```

The exact numbers will differ; the presence and use of the block is the test.

Record for each of the six session-13 failures:

| Failure | First visible at | Was it fixed before the next line? | How |
|---|---|---|---|
| note deficit | | | |
| projected ratio | | | |
| repeats | | | |
| distinct durations | | | |
| register mean | | | |
| pause gap | | | |
| overlap | | | |

A failure is **caught** only if the composer changes the line (or patches it
immediately) after the meter reports it. A printed number that is ignored is
not a catch.

## Success criteria

**Process success**

- Generated (`output + reasoning`) **≤10× the final `score.abc` tokens**.
- 0 hand-written parser/stats scripts; 0 direct score writes.
- ≤4 checker runs; target ≤3.
- Final full `check` has **0 hard failures**.
- No late repair loop: no repeated full-score rewrite, no `check` after a pass.
- The six session-13 failures do not reappear at the final check.

**Partial**

- 10–20× and final check passes: the meter helped but the process is still too
  expensive; next change is step/process, not another tool.
- ≤10× but final check fails: economy did not buy validity; inspect which meter
  lines were ignored.

**Failure**

- \>20×, or the same hard failure appears at the final check, or the run ends
  at the step cap before a final check.
- Quality <6/10 **if audio exists**. If there is no audio, quality stays
  suspended; do not claim a musical verdict.

## Stop rules (manual, yours)

- If the **same failure signature** appears twice after two different patches,
  stop. That is the design-bug signal, not a reason to try a third patch.
- If generated exceeds 10× and the final check has not run, stop.
- If `steps: 40` truncates before the final check, record it as a harness cap
  issue; do not immediately rerun with more steps.
- Do not change the model, prompt, skill or steps mid-run.

## After the run

Export the chat JSON to
`analysis/eval/inbox/deepseek_session_14/opencode_session_14.json`, then:

```bash
python3 analysis/measure_session.py \
  analysis/eval/inbox/deepseek_session_14/opencode_session_14.json \
  --score session-14/score.abc --max-ratio 10 --max-message 8000
```

Also keep:

- `session-14/report.json` — the final `check` measurement.
- `session-14/score.abc`, `plan.json`, `phrases.json`.
- `session-14/abc-session.log` — model audit.
- `core_review.md`, `seed.abc`, `seed_sheet.md`, `notes.md` if produced.
- Any audio render and the listening verdict, if you make one.

Optional diagnostics:

```bash
python3 02_maqam-score/scripts/score_cli.py check        # from session-14/
python3 02_maqam-score/scripts/craft.py score.abc --phrases phrases.json
```

## What to decide afterwards

1. **Did the meter move the failure to the line?** If yes, the tool is right;
   the next work is musical quality.
2. **Did the model ignore a printed number?** If yes, the instruction or the
   meter's phrasing is wrong, not the model alone.
3. **Did the same failure repeat?** If yes, that is the first evidence for the
   small circuit-breaker plugin.
4. **Did 40 steps truncate again?** If yes, the next single change is
   `SESSION_STEPS=55` or a derived cap; do not add it before this evidence.

## Files

| File | What |
|---|---|
| `dist/session-14-ready.zip` | the run package |
| `02_maqam-score/` | 0.9.0 source |
| `analysis/eval/plans/2026-11-25-session-13-tools-plan.md` | what was implemented |
| `analysis/eval/reports/2026-11-25-deepseek-session-13.md` | session-13 baseline and reproduction |
| `analysis/eval/proposals/proposal-tools.md` | the composer's proposal |
