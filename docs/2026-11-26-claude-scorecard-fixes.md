# Claude fix pass on 1.0.0 (applied as 1.0.1)

Received as `claude_fixes.zip` (`abc-score-writer-fixes.patch` + `CHANGES.md`).
The patch applied cleanly on `02_maqam-score/`; the fixed tree in that zip was
byte-identical to the patched source. Repo test run after merge: **128 passed,
1 skipped** (the zip baseline counted 121/125 because the repo also carries the
live-meter, asset-bank and scorecard tests). The original report follows
verbatim.


# CHANGES: bug-fix pass on abc-score-writer 1.0.0 (from abc-score-writer.zip)

Baseline: 121 tests passed. After: 125 passed (4 new regression tests), 4 skipped as before.
Claim: each defect below is gone. Nothing here claims better musical output (one run, one model).

## Edits

| # | File | Change | Finding |
|---|------|--------|---------|
| 1 | scripts/scorecard.py | Run `checker.check` a second time with `strict_style=True, require_final_rest=True` (what `release` does). Items that FAIL only there print in a new `RELEASE-BLOCKING` block (payload key `release_blocking`). `POLISH` now lists only warnings that stay WARN in the strict pass. Exit code 1 when BLOCKING or RELEASE-BLOCKING. `NEXT` no longer says "No blocking" when release would fail. No threshold touched. | B1 |
| 2 | SKILL.md | Card has five parts; names `RELEASE-BLOCKING`; mentions `release --dry-run`; exit-code and stop rules updated. | B1 |
| 3 | tests/test_scorecard.py | New test: a score whose last bar sounds is RELEASE-BLOCKING (`final rest`), not POLISH; example still has none. | B1 |
| 4 | SKILL.md | One sentence in section 2: after a call that ends with no output, rewrite by sections (max three), thinking less per section. | B2 (skill text only) |
| 5 | SKILL.md | Contract: `Z2/Z3/Z4` = 2-4 whole-bar rests counting toward the 4-bar limit (parser: `re.fullmatch(r"Z([2-4])?")` in abc_tools.py); section-comment rule (every `%` line is a section name; use plan names); blank `T:` explicit. Example left unchanged: it is valid. | B3 |
| 6 | scripts/score_cli.py | `init` wrote the 0.9 next step ("write the first 16 bars ... core --snapshot") into `score_state.json`, `state.json` and `STATE.md`, and printed "write the core". Now: write the whole score, then `scorecard.py`. A failed `release` wrote "fix the named bars with patch"; now "rewrite the whole score from the card (no patch)". | B5 |
| 7 | templates/STATE.md, templates/state.json | Phases and next action match the 1.0 loop (no `core`/`critic`/`syllabify`). | B5 |
| 8 | tests/test_score_cli.py | New test: `init` output and STATE files contain no `core --snapshot` / "first 16 bars". | B5 |
| 9 | scripts/score_cli.py | `plan set` rejects a top-level key that is neither in plan.json nor in plan.schema.json, with a "did you mean arrangement.ins_entries?" hint. | B6 |
| 10 | SKILL.md, references/cli.md | Documented `--sections` (`name=start_bar`, repeat the name, not `chorus2`) and the dotted path for `plan set`. | B6 |
| 11 | tests/test_score_cli.py | New test for the `plan set` rejection and valid paths. | B6 |
| 12 | scripts/score_cli.py `_chord_for_bar` | Accidental-aware root: `_e` -> `Eb`, `^f` -> `F#`. Before: `_e` -> `Em`, `^f` and `=e` -> `C`. Naturals unchanged. No maqam check added. | B7 |
| 13 | tests/test_score_cli.py | New test for the chord mapping. | B7 |

## Acceptance
- `example/score.abc`: `scorecard.py` exit 0 and `release --dry-run` exit 0.
- A score with a sounding last bar: card exit 1 (RELEASE-BLOCKING `final rest`), `release --dry-run` exit 1. They agree.

## B8 (read, not changed: by design)
- `unbroken`: "unbroken singing" (sanity cap 23 s) and "unbroken target" (plan 10 s) are two separate checks in checker.py; the card band shows the worse one.
- `register`: "register mean" (sanity 74 +/- 5) and "register target mean" (plan 70 +/- 3) are separate checks; SKILL.md already says the plan target is separate.
- Chorus `32-64` vs 16 bars: not confirmed. `chorus lift` pools every `%` section named chorus (a trailing number is stripped), so two choruses count as one pool. The `32-64` source could not be found without the session data.

## Not changed on purpose
- Not in the zip, so not touched: composer/packager/verifier agent files, `abc-guard.js`, the session template, `SKILL-v1.md`. This covers B2's false comment, all of B4, and the canonical-location question.
- No "do not read the skill's scripts" rule exists in this SKILL.md; it must live in the agent prompts.
- Out of scope per section 4: pre-write lint, draft counters, generating notes/CHANGES from report.json, maqam check in `seed-check`, threshold retuning, `measure_session.py`.
- Pre-existing, unrelated: `scripts/selftest.sh` exits 1 because `asset_bank.py stats | head -3` hits BrokenPipe. Same result on the untouched files.
- Legacy `check` (non-release) still writes "write the next line" on pass; it is the 0.9 path.

---

## Second pass: B2, B4 and the consistency sweep (1.0.2)

Claude's own note said the fixed zip was **not final** because it did not carry
the session layer. This pass closes those items in the repository:

| Item | Resolution |
|---|---|
| B2 (guard comment) | `abc-guard.js` comment now states the 1.0 reason for the 8,000-token cap; the code is unchanged |
| B4 (permissions) | agents now follow the last-match rule: broad allow first, specific denies last; packager denies `score.abc`/`plan.json`/`phrases.json`, verifier denies reading `scripts/**`; shell allowlists gain `scorecard.py`, `ls`, `pwd` |
| B4 (content) | packager has no `core` step and calls `verify_package.py` without `--core`; verifier uses `scorecard.py` + `release --dry-run`; composer reads `RELEASE-BLOCKING` |
| Template version | `session_template` was already promoted to 1.0 in `6a2e015`; this pass removes its remaining 0.9 instructions |
| Sweep | every `must` / `never` / `do not` / `at most` line in `SKILL.md`, the three active agents, `templates/STATE.md` and `opencode.json` was checked; the only prose-only rule left is "whole-file writes only", because OpenCode's `edit` action covers `write`, `edit` and `patch` |
| Decision: token cap | **8,000** output tokens per call kept: a 2-4k-token draft fits, a runaway burst is cut |
| Decision: composer steps | **100** in the template, matching the value session 16 ran with (`package_session.sh` still overrides it per session) |

Still outside this pass by design: `composer-v0.9.md` and `SKILL-v0.9.md` are
archives and are excluded from every package and session drop.
