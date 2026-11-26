# DECISIONS — the implementation constitution

**Status:** active · **Date:** 2026-11-25 · **Owner:** project owner

`analysis/MY_MAIN_GOALS.md` is the constitution. This file is the single
implementation interpretation. If they disagree, `MY_MAIN_GOALS.md` wins.

The two proposals (`proposal-retrieve-and-adapt.md`, `RAG_SUNO.zip`) are
rationale, not instructions. This file supersedes them where they conflict.
Do not ship the proposals or analyst briefs in an agent session folder.

## D1 — Quality

- The ear is the judge. Target **9/10+**. 6/10 is the floor of no regression,
  not success. 7–8 is the stock-assembly stage; 9+ needs a taste pass.
- No musical quality claim without a rendered, listened-to file. If there is no
  audio, goal 1 stays suspended.
- The checker and the numbers are diagnostic tools, never the goal.

## D2 — Budget

- The budget is **10× the final `score.abc` tokens**, `output + reasoning`.
- `seed.abc`, docs, plans and reports are diagnostics, not part of the ratio.
- There is no fixed token ceiling: a 2,400-token score has a 24,000 budget.
- The owner watches the session and ends it. No automatic total-budget monitor.
- Per-call guard (8,000 output tokens) and step limit are harness guards, not a
  quality gate.

## D3 — Acceptance ladder

| Layer | Class | Decision |
|---|---|---|
| contract | hard | renderer/parser contract |
| sanity | hard | degeneracy guards |
| structure / style | WARN | reported, not a taste gate |
| `quality.py` | diagnostic | hard only in a declared quality run |
| loans / similarity | WARN | reported; the ear decides |
| ear | final | owner's listening verdict |

Never edit `checker.py` or lower `calibration.json` to make a weak score pass.

## D4 — One workflow

`init → plan → asset query (optional) → core → expand line by line → check →
taste pass → release → seed/docs`.

There is no second "baseline then edit" workflow. An asset is a **reference**;
the composer still writes each line through `score_cli.py`. `remixer` remains a
separate skill for explicit remix tasks, not the composer default.

## D5 — Library roles

| Library | Role | Not for |
|---|---|---|
| 177 five-star | calibration, gates, priors | melody donor |
| 482 OSTRIS / 24 Fadl | in-style phrase/contour reference | whole-song template |
| 670 SUNO | arrangement, chords, groove, rhythm, owner's taste | primary melodic baseline for the LoRA style |
| `remixer` | explicit remix/borrow tasks | default composition |

If the owner wants the 670's style, change the style prompt/LoRA first; then the
670 become in-style.

## D6 — The asset unit

The unit is an **asset**: phrase, cadence, cell, chord loop, section skeleton,
groove. Never a whole-song template. The score is assembled from references,
not copied.

## D7 — Declared borrowing

Every loan names `asset`, `source`, `bars`, `borrowed`, `fit`, `transform`,
`why`. A loan without a reason is rejected. A copy without transformation is
rejected. `verify_loans.py` checks the structure; the ear judges the result.

## D8 — Lyrics stay outside the score

No `w:` lines. Binding is line-level via `phrases.json`/`alignment.py`; loans
live in `loans.json`. The ABC contract is unchanged.

## D9 — Harness

Paid model pinned; no free fallback; 8,000-token per-call cap; 40-step composer;
clean session folder (`input/`, `skills/`, `opencode.json`, prompt only). The
owner may end the session at any time.

## D10 — Change discipline

One change at a time. Measure the before/after on the same lyrics and model.
No claim without a log, a report, or a listening verdict. No patches: replace
the conflicting section, do not append a parallel instruction.

Session 12 is not used. The next pilot is **session-13** (the stock-pass
package): same lyrics, same model, one change — the optional asset bank.

## Conflict resolutions

| Conflict | Resolution |
|---|---|
| 10× score vs 10× score+seed vs 13× | D2: 10× score only |
| 9/10 vs "not worse" vs checker pass | D1 + D3: ear final; 6 floor; 9 target |
| checker WARN vs quality.py hard vs taste | D3: one ladder |
| line workflow vs auto baseline vs remixer | D4: one workflow; asset is reference |
| four libraries | D5: role matrix |
| whole song vs phrase | D6: asset only |
| `w:` vs contract | D8: no `w:` |
| patch vs no patch | D10: replace, do not append |
| new RAG vs existing tools | D5 + D4: reuse `remixer`/`idioms`/`exemplar` |
| checker edit vs loan check | separate `verify_loans.py`; checker untouched |
| 40 steps vs 26 lines | monitor; raise only if truncation, as one measured change |

## Non-goals

- No new RAG, parser, checker, or calibration from the 670.
- No automatic total-budget enforcement.
- No taste gate.
- No `w:` lines.
- No second composition workflow.
- No analyst briefs in the agent folder.
