# Session 16 — skill and harness audit

**Date:** 2026-11-26 · **Model:** `deepseek/deepseek-flash#low` · **Skill:** `abc-score-writer` 1.0.0
**Sources:** `opencode_session_16.json` (m0–m68), `FINAL_session-16.zip`, `SKILL.md` 1.0.0,
`.opencode/agents/{composer,packager,verifier}.md`, `.opencode/plugins/abc-guard.js`,
`plan.json`, `STATE.md`, `MY_MAIN_GOALS.md`, first audit `#1`–`#23`.
**(H) = hypothesis under §7.**

---

### 1. Summary

- **46 directives**: 15 process, 16 outcome, 6 unenforced, 5 strength-blocking, 3 weakness-demanding, **1 strength-aligned**.
- **16 Critical/Major failures**: 9 **Caused (H)**, 6 **Contributed (H)**, 1 **Unrelated**, 0 Indeterminate.
- **Most harmful:** the 8k cap (D39) over the whole-draft rule (D2): 3 zero-output turns, 24,000 tokens (26.3%), #12.
- **Second:** card vs release (D10/D16): `0 blocking` twice, then 3 and 1 hard failures; 4 drafts, ~20k (#9, #10).

---

### 2. Directive inventory

Tags: SA strength-aligned · WD weakness-demanding · SB strength-blocking · PP process · OS outcome · UE unenforced.
`Inh` = inherent weakness touched; `Off` = offloadable to tooling. `Y:x` / `N`.

| ID | Source | Directive (short) | Tag | Inh | Off | Log status | Cost |
|---|---|---|---|---|---|---|---|
| D1 | SKILL Loop; composer L59; goal §1.2 | 1–4 whole drafts; stop after two failed rewrites | UE | N | Y | violated: 10 drafts; m43 "draft 4 (max)" then 3 | +6 drafts, ~30k |
| D2 | SKILL §2; composer L34 | Whole score in one pass or ≤3 sections; keep cell/arc in head | SA | N | N | followed: 10 writes | 52,431 tok |
| D3 | SKILL §2, Legacy; composer L68 | No `line`, `patch`, `core`, live meter | SB | N | n/a | followed | 0 |
| D4 | SKILL §2, Rules; composer L36 | No parser, no hand sums; scorecard is the measurement | SB | Y:arith | Y:lint | violated: hand-summed 82 bars (m10,12,29); m53 "forbidden" | ~20k |
| D5 | SKILL §1 | `init` first; read plan/phrases; use `--sections` | OS | N | Y | followed (m5, m7) | 0 |
| D6 | SKILL §1 | FORM BUDGET: compact or `--force --bars N` + `--sections` | OS | N | Y | followed (m7) | 1 failed init (m6) |
| D7 | SKILL §1; composer L39 | Use init's line table; do not recompute | PP | N | Y | violated: line 23 15<16 (m42) | minor |
| D8 | SKILL §1 | `plan.json` exists → stop, dirty room | OS | N | Y | never triggered | 0 |
| D9 | SKILL §3; composer L45 | Scorecard after every draft; exit 1 blocking, 2 parse | PP | N | Y | followed (12 cards) | 2.4k |
| D10 | SKILL §3 | Card: FAIL hard, WARN plan/polish; BLOCKING/POLISH/SEAMS | OS | N | Y | followed | #9, #10 |
| D11 | SKILL §3; composer L65 | `section plan metrics` is a false band; do not chase | PP | N | Y | followed | 0 |
| D12 | SKILL §4 | Rewrite the whole file or section, not one bar; 1–4 times | PP | N | N | followed | 49k loop |
| D13 | SKILL §4 | Simultaneity cap 4 total; pull Ins or declare a bar | WD | Y:overlap | Y | worked around: `ins_entries` (m21–26) | ~4k, #23 |
| D14 | SKILL §4 | Parse error → fix bar sums first | PP | Y:arith | Y:lint | followed (m30, m33) | 2 rewrites |
| D15 | SKILL §5; composer L73 | No blocking → polish seams, release once | PP | N | N | violated: 3 releases (m40,45,54) | 2 extra releases |
| D16 | SKILL §5; cli.md | `release` = strict style + final rest | OS | N | Y | followed | 3 hard failures |
| D17 | SKILL §5; goal §1.1 | Ear is judge; no audio → no musical verdict | OS | Y:no ear | N | followed | quality suspended |
| D18 | SKILL Rules | Tools never compose | PP | N | N | followed | 0 |
| D19 | SKILL Rules; composer L69 | No hand parsers or metric scripts | SB | Y:measure | Y:read-only cmd | followed; m53 "forbidden" | 2 drafts, #11 |
| D20 | SKILL Rules | No micro-edits, no 26-line loop, no patch-by-patch | PP | N | Y | violated: 4 edits (m13,15,17,30) | 3 parse failures |
| D21 | SKILL Rules; composer L62 | Whole-file write only; no `sed`, Python, piecemeal edit | PP | N | Y | violated | #3 |
| D22 | SKILL Rules | Do not lower checker/calibration; no taste gates | UE | N | Y | never triggered | 0 |
| D23 | SKILL Rules; composer L78 | Stop when no blocking and released | UE | N | Y | violated: m41 "final" then 3 | 3 drafts, #19 |
| D24 | SKILL Rules | Same blocking survives two rewrites → stop and report | UE | N | Y | violated | #21 |
| D25 | SKILL Contract; composer L31 | Use scaffold header; do not invent | OS | N | Y | violated: `T:Ka's al-Furaq` (m12) | 1 patch, #2 |
| D26 | SKILL Contract | V block ≤4 bars; bar sums 16; `Z` is one whole-bar rest | WD | Y:count | Y:lint | violated: 22-bar block, `Z2` (m12) | 2 rewrites, #1 |
| D27 | SKILL Contract | Last bar `Z`; pitch/duration grammar; ties `A2-A2` | WD | Y:grammar | Y:parser | followed | 0 |
| D28 | SKILL Contract; composer L129 | Read `example/score.abc`; it is the dialect | PP | Y:mimicry | Y:docs | followed (m2); example teaches `Z2/Z3/Z4` | #1 |
| D29 | composer L5 | `steps: 100` | OS | N | Y | never triggered (61 calls) | enabled #21 |
| D30 | composer L6–27 | `edit score.abc: allow`; read scripts deny; subagent allowlist | SB | N | Y | worked around: `cat` bypass (m3); edit used | #3, #20 |
| D31 | composer L75 | Packager fails → package yourself and say so | PP | N | Y | followed (m59–67) | 3,868 tok |
| D32 | packager L5; verifier L5 | Packager 15 steps; verifier 8 | OS | N | Y | violated: packager steps exhausted (m58); verifier unused | #14 |
| D33 | packager L6–25 | Shell deny; only `*score_cli.py*` and `*verify_package.py*` | SB | N | Y | worked around: composer packaged; `ls`/`pwd` denied (m58) | #14 |
| D34 | packager L32 | `seed` then `seed-check` | OS | N | Y | followed (m59) | 0 |
| D35 | packager L33 | Edit seed only for orchestration; never melody | PP | N | Y | followed (m60) | #15 |
| D36 | packager L35–37 | `seed_sheet`/`notes` 10 lines; CHANGES = deviations + MEASURED + warnings | PP | N | Y | followed (m63, m64) | false prose, #16 |
| D37 | packager L38 | Run `verify_package.py` with all files | OS | N | Y | followed (m65) | 0 |
| D38 | verifier L24–33 | Run lint/check/plan lint; 10-line diagnosis | PP | N | Y | never triggered | 0 |
| D39 | abc-guard.js L6–9 | Cap every call at 8,000 tokens; comment says step limit forces a tool call | OS | N | Y | violated: cap hit 3× with output 0 (m10,27,34) | 24,000, #12 |
| D40 | STATE.md; state.json | Next: 16 bars, `core --snapshot`, `core_review`, `core --check` | PP | N | Y | worked around (ignored, m9) | 0 |
| D41 | cli.md; SKILL §1 | `--sections` absolute starts; repeat a name for a repeat | OS | N | Y | violated: `chorus2` (m6) | 2,139 tok |
| D42 | goal §4 | ≤24 steps | UE | N | Y | violated: 61 tool calls | #21 |
| D43 | goal §1.2 | ≤10× generated tokens | UE | N | N | violated: 53.1× | #12, #21 |
| D44 | plan.json | Floors: melisma 1.10, register 70±3, lift 5, top-duration 65%, durations 5, ties 1, Ins 20%, unbroken 10 s, endings 3 | OS | N | Y | followed; unbroken 10 vs card 23 | #8, #5 |
| D45 | checker; SKILL §3 | Contract/sanity hard; structure hard only under `strict_shape`; style warnings unless release | OS | N | Y | followed | #9, #10 |
| D46 | verify_package.py | Structural check only, not taste | OS | N | Y | followed (m65) | 0 |

---

### 3. Failure attribution

| # | Verdict | Directive(s) | Reason |
|---|---|---|---|
| 1 | Caused (H) | D26, D28 | The contract says `Z` is one bar; the example uses `Z2/Z3/Z4`. |
| 2 | Unrelated | — | D25 is explicit and the example shows blank `T:`; the agent added a title anyway. |
| 3 | Caused (H) | D30 vs D21 | Permission allows `edit score.abc`; D21 forbids it. m29 sees the clash, m30 patches. |
| 4 | Contributed (H) | D4, D7 | No per-line note check after a whole draft; the data existed. |
| 5 | Contributed (H) | D2, D4 | 82 bars are written before any measurement, so an 81 s run surfaces only at the card. |
| 6 | Contributed (H) | D12, D44 | Whole-file rewrites move every metric at once; the card gives no per-metric delta. |
| 7 | Caused (H) | D4, D26 | D4 forbids hand sums; D26 needs 16 units per bar; 1.0 has no padding tool. |
| 8 | Contributed (H) | D44 | The floor (20% repeats, 69 register) is below the style; no audio (D17) leaves the floor as the goal. |
| 9 | Caused (H) | D10, D16 | The card prints release-hard items as `POLISH`; both are presented as the same gate. |
| 10 | Caused (H) | D10, D16 | Chorus lift +4 is `POLISH` at m44 and hard at m45. |
| 11 | Caused (H) | D19 | m53: "compute from the ABC? That would be writing a metric script — forbidden." The card prints only the delta. |
| 12 | Caused (H) | D39, D2 | The cap cuts whole-score reasoning before a tool call; the plugin assumes it cannot. |
| 14 | Caused (H) | D32, D33 | 15 steps and a shell allowlist excluding `ls`/`pwd`; the subagent could not run a command. |
| 15 | Contributed (H) | D34, D35 | `seed-check` proves alignment only; `_chord_for_bar` maps `_E` to `Em`. |
| 16 | Contributed (H) | D36 | Prose has no source of truth; "call-and-response" contradicts `answer_rate.verse` 0/18. |
| 21 | Caused (H) | D1, D29, D42 | 4-draft and 24-step limits are prose; 100 steps and 10 drafts had no counter. |

---

### 4. Conflicts, gaps, harness mismatches, disagreements, Goodhart

**4.1 Conflicts**

- **D21 vs D30:** no piecemeal edit, but `edit score.abc: allow`. m29: "piecemeal edits forbidden?" Then m30 edits.
- **D10 vs D16:** card WARN = polish, release strict; m39 `0 blocking`, m40 `3 hard`.
- **D4 vs D26:** no hand sums, but raw bars must sum to 16. m12: "checking bar sums."
- **D2 vs D39:** "it fits the call cap" vs `MAX_TOKENS=8000`; m10, m27, m34 end `finish: length`.
- **D1 vs D29:** "At most 4 drafts" vs `steps: 100`; m43 "draft 4 (max)", then m48 and m53.
- **D26 vs D28:** `Z` is one bar, but the example writes `Z3`, `Z4`. m13: "I used Z2 which is not valid?"
- **D40 vs D2/D3:** STATE.md says 16 bars + `core --check`; the skill says whole draft, no `core`. m9 ignores it.
- **D33 vs task:** only two scripts allowed, but step 0 needs `ls`; m58 "Permission denied: shell."

**4.2 Gaps**

- **G1 no documented `ins_entries` path.** D13 says "declare a bar"; 1.0 never mentions `plan set`. m23 writes top level; m26 needs `arrangement.ins_entries`.
- **G2 no section-comment rule.** 1.0 omits `% section`; the example is the only teacher. m41 invents `% bars 1-4`; release fails sections.
- **G3 `lint` exists but is absent from 1.0.** m19: "I could use `lint` … Allowed?" It never runs it; the parse error names 2 errors.
- **G4 no per-line note/rest preflight;** deficits appear only after a full draft (#4, #5).
- **G5 no deviation-clearing step.** Three placeholders pass release; CHANGES.txt claims "3 declared deviations" (#18).
- **G6 no prose source of truth** for `notes.md`/`seed_sheet.md`/`CHANGES.txt` (#16, #17, #22).
- **G7 no chord/maqam check;** `seed-check` is bar alignment only (#15).
- **G8 no draft counter;** m43 cannot tell whether a parse-fix write counts.
- **G9 repeated `% chorus` is undefined;** m45 says `chorus 32-64`, report says 16 bars.

**4.3 Harness mismatches**

- 8k cap (D39) vs whole-82-bar reasoning: 3 burns, 24k.
- `steps: 100` (D29) vs ≤24 (D42): 61 calls used.
- Packager 15 steps + allowlist (D32, D33) cannot perform its step 0.
- Verifier (D38) is never called; 1.0's composer omits it.
- No audio renderer; D17 asks for an ear judgment the workflow cannot produce.

**4.4 Validator disagreements**

- **V1** m39 card `0 blocking` vs m40 release `3 hard`.
- **V2** m44 card `0 blocking` vs m45 release `1 hard`; lift +4 is `POLISH` then hard.
- **V3** plan `max_unbroken_seconds` 10 (D44) vs card `sanity max 23s` (m20); the plan number is never enforced.
- **V4** plan `register.mean` 70±3 (67–73) vs card `sanity 74 ± 5` (69–79); 67.7 fails the card but passes the plan.
- **V5** release measures chorus as `32-64` (m45) while `report.json` says 16 bars.

**4.5 Goodhart risks**

- repeats **21%** vs 20%; ties **1** vs 1; durations **6** vs 5; chorus lift **+5.0** vs 5; register **70.8** vs 69 (P2.9); notes/syll **1.11** vs 1.10 (P4.1) — m54 report.
- The style asks "melismatic, belting"; the score sits at P3–P4. The floor became the goal.

---

### 5. Pitfall frequency

| Pitfall | Count | D# / m# |
|---|---:|---|
| 1 Process over outcome | 3 | D2, D12, D19; #8, #11, #21 |
| 2 Banning the offloading tool | 4 | D4, D19, D30, D33; #7, #11, #12, #20 |
| 3 Contradictory rules/permissions | 8 | D21/D30, D10/D16, D4/D26, D2/D39, D1/D29, D26/D28, D40/D2, D33; #1,3,7,9,10,12,14,20 |
| 4 Validators disagree | 3 | D10/D16, D44, V5; #5, #9, #10 |
| 5 Limits stated, not enforced | 3 | D1, D23, D42; #19, #21 |
| 6 Ignoring harness limits | 2 | D39, D32/D33; #12, #14 |
| 7 Thresholds become targets | 2 | D44, D10; #8, #11 |
| 8 Convention only by example | 2 | D28, D26; #1, #2 |
| 9 Proxy verification | 3 | D17, D34, D37; #8, #15, #16 |
| 10 Prose with no source | 4 | D36; #16, #17, #18, #22 |
| 11 Unhelpful interfaces | 3 | D41, D28, parse error; #1, #13, #21 |
| 12 Checkers miss the failure | 3 | D34, D10, D37; #9, #10, #15 |
| 13 Rule accretion | 1 | 46 directives across skill/agents; #21 |
| 14 Tuned on one setting | 1 | D39 low/8k; #12 |
| 15 Other: stale state | 1 | D40; m9 |

---

### 6. Ranked skill edits

1. **Unify card and release.** Add a `RELEASE-BLOCKING` block to `scorecard.py` using the strict path; keep `POLISH` for taste. **D10, D16.** Removes **#9, #10**; H: ~20k, 4 drafts. Risk: earlier hard signal; safeguard: print both blocks, no new gate.
2. **Give whole-draft a validator.** `score_cli.py write --check` reports per-bar sums, voice counts, line deficits, rest runs and block lengths before commit. **D4, D14, D26, G3, G4.** Removes **#1, #4, #7**, part of **#5**; H: ~20k. Risk: `line` reopens micro-editing; safeguard: validate whole files only, never compose.
3. **Bound the 8k cap.** Raise it for the compose call or force a tool call at ~6k. **D39, D2.** Removes **#12**; H: −24k. Risk: longer calls; safeguard: per-call cap plus "write now".
4. **Enforce counters and deny `edit` on score.abc.** Plugin counts drafts/cards/steps; whole-file writes only. **D1, D21, D29, D30, D42.** Removes **#3, #19, #21**; H: −30k. Risk: blocks seam fixes; safeguard: one extra draft with a written reason.
5. **Print the gated values.** Card shows verse/chorus medians, per-section register, notes per line, and the corpus median beside each floor. **D19, D10, D44.** Removes **#11**, part of **#4, #6**; H: −10k, 2 drafts. Risk: threshold-chasing; safeguard: show the median, not the floor.
6. **Generate the prose from `report.json`.** A `docs` command emits `seed_sheet`, `notes`, `CHANGES` from plan + report, and lints "call-and-response" against `answer_rate`. **D36, G5, G6.** Removes **#16, #17, #18, #22**. Risk: generic prose; safeguard: one free human line.
7. **Fix the packager or fold it in.** Allow `ls`/`pwd`/`cat`, set a workdir, steps 25. **D32, D33.** Removes **#14**; H: −3.9k, one subagent. Risk: broad shell; safeguard: read-only allowlist.
8. **Check seed harmony.** `_chord_for_bar` maps `_E` to an Eb chord; `seed-check` tests chord roots against the maqam. **D34, D35, G7.** Removes **#15**. Risk: changes all seeds; safeguard: fixture on `example/score.abc`.

---

### 7. Re-run plan

**First change:** edit 1 only (card = release). **Hold constant:** flash#low, 8k cap, whole-draft prompt,
`steps: 100`, same lyrics/style, clean room, same skill otherwise.
**Baseline:** 91,243 generated; 53.1×; 10 drafts; 12 cards; 3 releases; 3 burns; 2 splits; 2 release failures.
**Confirm if:** splits 0, drafts ≤6, generated ≤75k, ratio ≤43×, burns ≤3, no unpredicted release failure.
**Refute if:** any split remains, drafts ≥8, or generated >85k; then edit 3 moves first.
