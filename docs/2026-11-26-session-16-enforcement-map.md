# Session 16 — enforcement map and priority check

**Date:** 2026-11-26 · **Scope:** the six priorities proposed for the skill audit
**Sources:** session 1.0 files in `FINAL_session-16.zip` (not the repo's 0.9 files),
`SKILL.md` 1.0.0, `.opencode/agents/*`, `abc-guard.js`, `scorecard.py`, `score_cli.py`,
`checker.py`, `example/score.abc`, `STATE.md`, log m0–m68.
**Convention:** `enforced` = a tool, plugin, parser or permission makes the rule happen;
`prose` = no mechanism; `contradicted` = a mechanism does the opposite; `absent` = not in 1.0.

---

## 1. Enforcement map (grep of must / never / do not / at most)

| Rule (quoted or paraphrased) | Source | Mechanism | Verdict |
|---|---|---|---|
| "At most **4 drafts**" | SKILL L26; composer L59 | none | prose |
| "Maximum four checker runs" | 0.9 SKILL L270 only | none, and **removed in 1.0** | absent |
| "≤24 steps" | goal §4 | none; composer `steps: 100` | prose, contradicted |
| Per-call ceiling 8,000 | `abc-guard.js` L9 | plugin hook | enforced, too low |
| "Do not edit `score.abc` with `sed`, Python, or piecemeal `edit`" | SKILL L109 | `edit score.abc: allow` | contradicted |
| "The only score write is a whole-file rewrite" | SKILL L110 | no `write` command; `write` and `edit` both allowed | prose |
| "No `line`, no `patch`, no `core`" | SKILL L51; composer L68 | commands still exist; no deny | prose |
| "No Python parser, no hand sums" | SKILL L52; composer L69 | shell unrestricted; no exec deny | prose |
| "Do not read the skill's scripts" | composer L70 | `read` deny | enforced, bypassed by `cat` (m3) |
| "Do not lower the checker or `calibration.json`" | SKILL L112 | no edit deny on those files | prose |
| "Stop when no blocking"; "stop after two rewrites" | SKILL L113, L26 | none | prose |
| "`plan.json` exists → stop" | SKILL L43 | `init` dies without `--force` (`score_cli.py` L570–573) | **enforced** |
| Header `X:1` + blank `T:`; bar sums; `Z` | SKILL L120–128 | runtime parser | **enforced** |
| Packager: "Do not touch `score.abc`" | packager L41 | `edit score.abc: deny` | **enforced** |
| Packager: "Do not touch `plan.json` or `phrases.json`" | packager L41 | `edit "*": allow` | contradicted |
| Verifier: "Do not read the skill's scripts" | verifier L33 | `read "*": allow` | contradicted |
| Packager shell only `score_cli.py` / `verify_package.py` | packager L13–21 | permission | enforced, too narrow (`ls` denied) |
| Packager 15 steps | packager L5 | harness | enforced, too low |
| Seed: "Never change the melody" | packager L33 | `verify_package` compares seed bars to score | **enforced** |
| "If there is no audio, do not claim a musical verdict" | SKILL L101 | no audio path | prose / unverifiable |
| STATE "next: 16 bars + `core --check`" | `STATE.md` | none; 1.0 forbids `core` | stale |

**Counts:** 7 enforced (three with the wrong value or scope), 1 enforced-but-bypassed,
4 contradicted (including `≤24` vs `steps: 100`), 1 absent, 1 stale, 7 prose-only.
The common thread in items 1, 3, 5 and 6 is that the 1.0 prose was tightened while the
mechanism was not.

---

## 2. The six priorities, verified

### 2.1 Cap × whole draft — confirmed, and unhandled

- 3 calls end `finish: "length"`, `output: 0`, `reasoning: 8000` (m10, m27, m34) = **24,000 tokens, 26.3%**.
- 1.0 has no instruction for a capped call. The only cap mention is "it fits the call cap" (SKILL L49).
- The harness reply is **"Break the remaining work into smaller pieces"** (m11, m28, m35). The skill says
  whole score, no `line`, no `patch` (D2, D3). The agent followed the skill and repeated the burn.
- The plugin comment claims "the composer's step limit forces a tool call" (`abc-guard.js` L6–7). It does not:
  the 8k completion ceiling cuts the reasoning before any tool call.
- **Verdict:** pure config conflict. Fix the cap or make the three-section split mandatory after one `length`.

### 2.2 No hand sums vs 16-unit bars — confirmed; highest-value fix

- 468 occurrences of `=16`, 307 `✓`, 623 arithmetic reasoning lines (**23.5%** of 2,650), `motif` 2, `arc` 0.
- No pre-write sum tool exists. `scorecard.py` and `lint` read an existing file; the only pre-write
  validators are `line` and `patch`, both forbidden by 1.0 (SKILL L51).
- `init`'s per-line table gives syllables/bars/pace, not note counts or bar sums (SKILL L39–40).
- **Verdict:** the skill bans the offloading tool and supplies no replacement. A `write --check`
  (or `lint --stdin`) is the single highest-value edit.

### 2.3 Card vs release — confirmed, one code-path bug

- `scorecard.py` L258–263 calls `checker.check(...)` with defaults: `strict_style=False`,
  `require_final_rest=False`; `strict_shape` comes from the plan and is `false`.
- `release` sets `strict_style=... or args.release`, `require_final_rest=... or args.release`
  (`checker.py` L1117–1121).
- The card's own hint already says **"polish; not blocking unless release"** (`scorecard.py` L121).
  It knows the item will be hard, prints it as `POLISH`, then says "No blocking… then release."
- `release --dry-run` exists (`references/cli.md` L116) but 1.0's SKILL and composer never mention it.
- **Verdict:** not a design choice; a missing second pass. One `strict_style=True` call would close it.

### 2.4 Example vs contract — confirmed

- `example/score.abc` writes `Z3|` (L20), `Z4|` (L29, L31), `Z2|` (L34). 1.0 says only "`Z` is a
  whole-bar rest" (SKILL L122). Nothing states that `Z2` counts two bars.
- Section comments (`% intro`, `% verse`, `% chorus`, `% outro`) appear only in the example; 1.0's
  contract omits them. m41 invents `% bars 1-4`; release then fails "sections".
- Blank `T:` is shown in the scaffold and the example; the agent still wrote `T:Ka's al-Furaq` (m12).
- The 4-bar maximum is stated (L121), but the example uses 1–3-bar blocks; the first draft used a
  22-bar Ins block (m12). The parser error named neither the block length nor the `Z2` count.
- **Verdict:** the example contradicts the short contract on the one token the first draft used.

### 2.5 Limits — one correction

- **4 drafts:** prose only (SKILL L26, composer L59); 10 happened.
- **4 cards:** **not a 1.0 rule.** It is 0.9's "Maximum four checker runs" (0.9 SKILL L270), removed in
  1.0. The 12 cards are a cost, not a violated 1.0 limit. The first audit's "4/4/24" shorthand is wrong.
- **24 steps:** user goal only (goal §4); composer `steps: 100`; 61 tool calls used.
- No counter anywhere. m43: "This is draft 4 (max)"; m53: "I've likely exceeded."
- **Verdict:** two prose limits (4 drafts, 24 steps), one absent (4 cards), one hard config that is 4×
  the user cap (100 steps).

### 2.6 Permissions and stale files — confirmed, plus repo drift

- `edit score.abc: allow` vs "no piecemeal edit" (composer L6–9 vs L63). m29 sees the clash, m30 patches.
- Packager `edit "*": allow` vs "do not touch `plan.json` or `phrases.json`" (L12 vs L41).
- Verifier `read "*": allow` vs "do not read the skill's scripts" (L19–21 vs L33).
- Packager 15 steps and a shell allowlist that excludes `ls`/`pwd` (L5, L13–21); m58 could not start.
- `STATE.md` still says "write the first 16 bars, `core --snapshot`, `core --check`" — the 0.9 workflow
  that 1.0 forbids (m9).
- **New:** the repo's `session_template/.opencode/agents/composer.md` is still 0.9 (`high`, `steps: 40`,
  edit denied, one lyric line per call); the active `02_maqam-score/SKILL.md` is 0.9.0; the 1.0 skill is
  `02_maqam-score/SKILL-v1.md` and inside `dist/session-16-ready.zip`.
  A re-run built from `session_template` tests 0.9, not 1.0.
- **Verdict:** the experiment's files exist only in the zip; the repo's runnable template is a different
  workflow.

---

## 3. Revised order

1. **Cap × whole draft.** Pure config; 24k with no artifact. Decide whether 8k, whole-file and the
   reasoning budget can coexist; if not, raise the cap or force the three-section split after one `length`.
2. **Pre-write arithmetic.** Add `write --check` / `lint --stdin`; report per-bar sums, voice counts,
   line deficits and rest runs before commit. Removes the 23.5% arithmetic tax and #1/#4/#7.
3. **Card = release.** One strict pass or a `RELEASE-BLOCKING` block. Removes #9/#10 and 4 drafts.
4. **Example = contract.** Fix `Z2` in the example, or document multi-bar `Z`; add the section-comment
   rule; keep blank `T:` explicit. Removes the first-draft class.
5. **Enforce limits.** Count drafts and steps in the plugin; decide whether the 4-card rule returns.
6. **Permissions and stale state.** Deny `edit score.abc`, deny packager edits on plan/phrases, allow
   `ls`/`pwd`, raise packager steps, replace `STATE.md`, and switch the repo template to 1.0.

**Deferred, as proposed:** prose/docs, seed harmony, threshold tuning, and a full prose rewrite. The
first three are correctness polish; the last is not needed to explain the cost.

---

## 4. Corrections to the main audit

- First audit #21: "10 drafts, 12 cards, 61 tool calls vs 4/4/24" should read
  **"10 drafts, 61 calls vs 4 drafts / 24 steps"**; 1.0 has no card cap.
- Skill-audit tags **D8, D29, D32** were marked `UE` (unenforced). They are tool/harness-enforced:
  `init` refuses an existing plan (D8), `steps: 100` is a hard cap (D29), packager 15 steps is a hard
  cap (D32). Correct distribution: **15 process, 16 outcome, 6 unenforced, 5 strength-blocking,
  3 weakness-demanding, 1 strength-aligned**.
- The main audit's §6 ranking is superseded by §3 above if the cap is treated as the first variable.
