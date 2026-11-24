# Session 07 — DeepSeek instrumentation checklist

**Skill:** `abc-score-writer` 0.5.2, SHA-256 `e7fca141…7d0f9` (frozen)
**Harness:** OpenCode
**Model:** `deepseek-v4-pro` variant `max` (or `deepseek-flash` `high`)
**Input package:** this folder (checklist, task, inputs)
**Date:** 2026-11-24

**Goal 1:** score excellence; the ear is the verdict.
**Goal 2:** measure the real token/cost of the process — no estimates, no cap.

**This is an instrumentation run.** Only the model and harness change. The skill,
task, lyrics, key, tempo and checker are identical to session 06. A weak score
does not indict the skill; a cheap run does not excuse a bad score.

---

## 0. Non-negotiables

- [ ] The ear decides the music; the checker and craft metrics are diagnostics.
- [ ] No gate-chasing: no "0 warnings", no metric target, no token cap.
- [ ] No retrieval: no exemplar, no phrase bank, no corpus idiom call.
- [ ] No code changes during the run. Record gaps; do not patch the checker.
- [ ] Same input for A/B/C: D Kurd, 80 BPM, same lyrics and settings.
- [ ] One change per run: this run changes **model + harness only**.

---

## 1. Freeze the run

- [ ] The skill is installed and loadable as `abc-score-writer`
      (global or project-local; no machine path in the prompt).
- [ ] `task.md` pasted verbatim; the agent received **D Kurd / 80 BPM**.
- [ ] No previous `score.abc`, `seed.abc`, sheet, report or checklist attached.
- [ ] Model + variant recorded (`v4-pro/max` or `flash/high`).
- [ ] Offline/online and renderer availability recorded.
- [ ] Session started in a fresh empty directory; deliverables land there.

---

## 2. Process checks

- [ ] `lyrics.txt` saved once; no retyped copy afterwards.
- [ ] `syllabify.py --phrases` run once; the line table is not retyped.
- [ ] `seed_sheet.md` is **10 lines of rules**, not a 26-row table.
- [ ] `plan.json` exists and uses the template; targets at defaults.
- [ ] `core_draft.abc` exists (8–16 bars) and predates `score.abc`.
- [ ] **No task list.**
- [ ] `score.abc` is two voices (`Vocal` + `Ins`), no third voice.
- [ ] `seed.abc` is the same melody plus chords and `V: Drums`.
- [ ] The drum voice has a 2-bar groove per section, a fill in a vocal hole, a
      drop at the last line.
- [ ] Checker ran **once**, at the end.
- [ ] `notes.md` written **after** the score.

**Stop rule:** no ABC by the 10th tool call → stop, record "process still
front-loaded". Do not wait for another 20-minute design block.

**Loop marker:** `score.abc` rewritten twice before `seed.abc` exists → record
the call numbers and the reason given in the reasoning; let it run.

---

## 3. Save and export

```bash
opencode session list                         # find the session id
opencode session export <ses_id> > session.json
```

- [ ] `export/session.json` — the native export: session totals, messages,
      tokens, reasoning, tool calls and results.
- [ ] `output/` — every deliverable the agent wrote.
- [ ] Three covers: A no seed, B `maqam_kurd_seed_v2.abc`, C new `seed.abc`.

---

## 4. Measure exactly (no character estimates)

From `session.json` (`info.tokens`, `messages[].tokens`):

| Field | Session 06 (estimated) | Session 07 (measured) |
|---|---:|---:|
| Requests | 15 | |
| Prompt traffic (`input + cache_read`) | 291 k | |
| Cache read | not in export | |
| Cache share of traffic | unknown | |
| Output tokens | ~5.6 k visible | |
| Reasoning tokens | not in export | |
| Reasoning share of output | unknown | |
| Cost | not in export | |
| Wall clock | 14 m 21 s | |
| Time to first ABC | call 11 | |
| Checker runs | 0 | |
| score.abc rewrites | 1 | |

- [ ] `cache_share = cache_read / (input + cache_read)` computed.
- [ ] Largest reasoning block: time, chars, what it was doing.
- [ ] `tools[*]`: which tools consumed the most calls / I/O.
- [ ] `finish` reasons: any `length` or `error`.

**Attribution rule:** if cache share > 90%, documentation is cheap in dollars and
the cost driver is output/reasoning. In that case, do not repeat the session-06
claim that the 43.5 KB skill is the failure cause; it is a *context* cost, not
necessarily a *quota* cost.

---

## 5. Blind listen

| Label | What it is |
|---|---|
| **A** | no seed: lyrics + style only |
| **B** | old v2 seed (`maqam_kurd_seed_v2.abc`, D/80) |
| **C** | new `seed.abc` |

Shuffle; listen once through; rate 0–4:

| Dimension | A | B | C |
|---|---:|---:|---:|
| Hook (can you hum the 2-bar cell?) | | | |
| Text setting (long syllables, rhyme, caesura) | | | |
| Rhythm (not a grid; breathes) | | | |
| Maqam (Kurd, b2 as event) | | | |
| Form/arrangement (riff, chorus payoff, arc) | | | |
| **Rhythm section (do the drums answer the voice?)** | | | |
| Singability | | | |
| Seed usefulness | | | |
| **Mean** | | | |

- [ ] One sentence per cover: what you remember after it ends.
- [ ] Unblind and record the mapping.

Decision: **Fail** if C ≤ A, C mean < 2.5, any dimension 0, or two gaming flags.
**Usable** if C > A and C > B, mean ≥ 2.5. **Good** if mean ≥ 3.0, hook ≥ 3,
rhythm section ≥ 3, seed usefulness ≥ 3.

---

## 6. Gaming audit

- [ ] **Process theater:** a beautiful sheet/plan but no score, or a score after
      the notes.
- [ ] **Task-list ceremony.**
- [ ] **Decorative drums:** generic 4/4 loop, no fill in a hole, no drop.
- [ ] **Metric-shaped music:** bars differ on paper, every line feels the same.
- [ ] **Token melisma:** a 3–5 note tag to hit a band.
- [ ] **Loop or through-composition:** one 2-bar cell 10×, or 26 unrelated lines.
- [ ] **Cadence carpet:** every phrase on the tonic or every phrase long.
- [ ] **Guitar as floor:** whole-bar arpeggios, no riff, no texture change.
- [ ] **Claim without check:** a named baḥr it did not scan; "0 warnings" as
      quality.
- [ ] **Plan edited to fit the score.**

Any **two** = process fail, even if the ear likes the cover.

---

## 7. What to change after the run

| If the finding is… | Change… |
|---|---|
| Cache share > 90%, reasoning dominates | Checkpointed deliverables, not the skill split |
| Cache share < 70%, docs dominate | Split the skill (0.5.3) |
| Reasoning composes the piece before the sheet | A hard intermediate artifact, not more prose |
| 26-row table typed again | `syllabify.py` emits absolute bars |
| Complete deliverables, drums rejected | The seed contract |
| No ABC by call 10 | Process still front-loaded; stop and rethink |

Rules: one change per run; never add a hard gate for taste; never fix a bad
score by editing the checker or lowering a target.
