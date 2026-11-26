# Session 16 brief — 1.0 in a clean room, low thinking (analyst only)

> **Do not put this file in the agent's working directory.** The agent gets
> `input/`, `skills/`, `opencode.json`, `.opencode/` and `PROMPT.txt` only.

## What changed from session 15

Session 15 released a valid score but failed the economy (54.2×) and was not a
valid clean-room test: `init` hit `ERROR plan.json exists`, so the composer
inherited a 64-bar plan and never made the form decision. Session 16 changes
**one process variable** — thinking is `#low` instead of `#high` — and fixes
the correctness bugs that invalidated session 15:

| Fix | Why |
|---|---|
| Clean package: no `plan.json`/`phrases.json`/`score.abc` | `init` must run; FORM BUDGET must print |
| `#low` in `opencode.json`, every agent, and the guard `PIN` | the requested variant |
| `SKILL.md`: `A4` = A natural × 4 units, not octave 4; tie example `A2-A2` | session 15's first draft used `A4 2` and paid 45 parse errors |
| Stop if `init` reports `plan.json exists` | the dirty-room signal |
| Whole-file rewrite only; no `sed`/Python on `score.abc` | session 15 patched after the card said rewrite |
| `init`'s per-line table called out as the budget source | session 15 recomputed 26 lines by hand: 48k capped reasoning |
| Packager creates `core_draft.abc`/`core_review.md` if missing | session 15's composer had to do it after the subagent returned empty |

Not changed: checker, calibration, plan bands, steps (100), lyrics, style,
model family, 8,000-token per-call cap.

## Package

`dist/session-16-ready.zip` — SHA-256
`b5d4c46ec3287cc9da365bfc0b8c565b589a99e6d838310c98332db97650edf5` (4.7 MB).

- Skill **1.0.0** from `SKILL-v1.md`; agent `composer-v1.md`.
- `opencode.json`: `deepseek/deepseek-flash#low`, `default_agent: composer`.
- `composer.md`: `steps: 100`.
- `abc-guard.js`: pins `variant: "low"`, 8,000-token per-call cap, logs to
  `abc-session.log`.
- Clean root. `PROMPT.txt` is the one-line prompt.

Start **in a new empty directory**:

```bash
unzip dist/session-16-ready.zip -d /tmp/s16
cd /tmp/s16/session-16
opencode --auto
# paste: Write the abc score for style+lyrics in @input/lyrics.txt
```

Do not run `init` yourself. The composer must run it and print FORM BUDGET. If
you unzip over an old folder, stale `plan.json` survives and the run is dirty.

## Run validity — check before interpreting anything

- [ ] `init` ran and printed `FORM BUDGET: 64 bars vs syllabify 82 (-22%)`.
- [ ] The composer kept 64 (and accepted the warning) or reran with
      `--force --bars 82` **and** `--sections`; not a bare `--bars`.
- [ ] `abc-session.log` shows `after.variant == "low"` on every primary call.
- [ ] One session id; complete export.
- [ ] Root had only the package before the run; no pre-made plan/score.
- [ ] `steps: 100` in the packaged `composer.md`.

A validity failure means the run did not test low thinking.

## Success criteria

**Process**

- Generated (`output + reasoning`) **≤10× the final `score.abc` tokens**
  (session 15: 94,584 / 1,744 = **54.2×**).
- 0 blocking at the final `release`; no late repair after a pass.
- ≤4 whole drafts; no `sed`/Python/`edit` patches of `score.abc`.
- ≤4 scorecard runs (session 15: 18).
- Fewer than six 8,000-token reasoning calls (session 15: six = 48k).
- The six session-13 failures do not reappear at the final check.

**Partial**

- 10–20× and final check passes: low thinking helped but the loop is still too
  expensive; the next change is the budget/step process, not another tool.
- ≤10× but final check fails: economy did not buy validity; inspect the ignored
  card lines.

**Failure**

- >20×, or the same hard failure at the final check, or the run ends at
  `steps: 100` before release.
- Quality <6/10 **if audio exists**. No audio → quality suspended; do not claim
  a musical verdict.

## Stop rules (manual)

- Same failure signature twice after two different whole rewrites → stop.
- Generated >20× before the final check → stop.
- Step cap truncates before release → record it; do not rerun with more steps.
- Do not change model, prompt, skill, variant or steps mid-run.

## After the run

Export the chat JSON to
`analysis/eval/inbox/deepseek_session_16/opencode_session_16.json`, then:

```bash
python3 analysis/measure_session.py \
  analysis/eval/inbox/deepseek_session_16/opencode_session_16.json \
  --score session-16/score.abc --max-ratio 10 --max-message 8000
```

Keep `score.abc`, `plan.json`, `phrases.json`, `report.json`, `abc-session.log`,
`seed.abc`, `seed_sheet.md`, `notes.md`, `core_review.md`, `CHANGES.txt`.

**Integrity check (session 15 failure):** `score.abc` in the archive must have
the same note count and bar count as `report.json` (398/64 for session 15, not
0/82). Record `sha256sum score.abc` and the export time. Do not let a later
session's `init` overwrite the folder before zipping; if `state.json` says
`phase: "start"` while `report.json` is a release report, the archive mixes two
runs.

Expected known false warning: `section plan metrics` uses the auto plan's
`[0,3]` vocal band, which is too low for dense verse. It is not a target.

## Files

| File | What |
|---|---|
| `dist/session-16-ready.zip` | the run package |
| `analysis/eval/reports/2026-11-26-deepseek-session-15.md` | the 54.2× baseline and the artifact post-mortem |
| `analysis/eval/inbox/deepseek_session_15/reconstructed/score.abc` | session 15's real score, recovered |
