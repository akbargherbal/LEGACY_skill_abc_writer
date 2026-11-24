# Session 06 post-mortem — where the tokens went

**Run:** `2026-11-24-claude-session-06`
**Artifact:** `dist/abc-score-writer.zip`, SHA-256 `e7fca141…7d0f9` (0.5.2 lean sheet)
**Source:** `analysis/eval/inbox/claude_session_06/conversations-000.zip`
→ `analysis/eval/runs/2026-11-24-claude-session-06/chat.json`
**Date:** 2026-11-24
**Status:** the turn ended mid-run, after 14 tool calls and a complete `score.abc`,
before `seed.abc`, the checker and the notes.

This report measures both failing runs (05 and 06) from their exported
transcripts. It changes nothing in the skill.

---

## 1. TL;DR

1. **The run did write a score.** 84 bars, 413 notes, two voices, written at call
   12 and rewritten at call 13. It died while preparing `seed.abc`, not at the
   sheet.
2. **The 0.5.2 diagnosis was wrong about the cause.** The sheet was never the
   expensive step. In both sessions the model composed the whole piece in one
   hidden-thinking block (10–20 minutes), and *then* wrote the sheet and plan in
   11–21 seconds. A shorter sheet cannot shorten thinking that already happened.
3. **82.6% of session 06's visible input traffic is documentation** re-sent on
   every request: 61.6% the 43.5 KB `SKILL.md`, 21.0% five reference/schema
   lookups. The score, sheet, plan and core draft together are 5.7%.
4. **The 26-row table came back**, as a hand-typed Python dict in the last call,
   because `syllabify.py --phrases` emits only relative `body_bar_start/end` and
   tells the agent to add absolute `bar_start/bar_end` by hand. The sheet no
   longer holds the table; the tool still demands it.
5. **The turn has no intermediate finish line.** Compose → encode → self-check →
   repair → seed → checker → notes all live in one turn, so exhausting the
   budget anywhere loses the ending. Session 05 lost it after the sheet; session
   06 lost it after the score.
6. **It was not a context overflow.** The final visible context was 29 k tokens
   of a ~200 k window. The transcript simply stops after a tool result, which is
   consistent with the session's usage allowance ending mid-turn.

---

## 2. What actually happened

| Time (UTC) | Call | Event |
|---|---|---|
| 09:09:47 | — | prompt + 3 attachments (task, lyrics, style) |
| 09:09:48–54 | 1–3 | reads all of `SKILL.md` in three chunks (48,936 chars) |
| 09:09:55 | 4 | syllabify: 361 syllables, 82 bars, 26 lines |
| 09:09:58–10:07 | 5–7 | `phrases.json`, `groove.abc`, maqam format, example plan, rhythm, schema |
| 09:10:09–11:11 | — | **62 s thinking (12 segments)** |
| 09:11:11–14 | 8–9 | grep degrees, craft: cell, cadence, melisma |
| 09:11:15–21:15 | — | **600 s thinking (10 min), 106 thought segments** |
| 09:21:15–26 | 10 | writes `seed_sheet.md` (10 rules) + `plan.json` in **11 s** |
| 09:21:32–38 | 11 | writes `core_draft.abc` (15 bars) |
| 09:21:43–22:07 | 12 | writes full `score.abc` + a home-made stats script |
| 09:22:09–23:41 | — | **93 s thinking**, then rewrites the whole `score.abc` |
| 09:24:05–08 | 14 | hand-types 26 bar ranges into `phrases.json` |
| 09:24:08 | — | tool result returned; **no further assistant message** |

Wall clock 14 m 21 s. Thinking 12 m 46 s (89%). Visible output 5.6 k tokens.

The 10-line sheet exists and is exactly 10 rules — the 0.5.2 process change
worked as written. It was simply written *after* the composition, not before it.

---

## 3. Method

The export contains every message, tool call and tool result, but **no usage
field**. Token figures are estimated from visible characters at **3.6 chars per
token (±15%)**. "Input traffic" = the sum of the context present at each model
request, i.e. what the model actually re-read, not the final context size. Five
parallel calls count as one request. Hidden thinking text is absent; only its
duration and the number of UI thought-summaries are measurable.

Because of these conventions the absolute numbers differ from the earlier
session-05 report (266 k, 14 requests); the **shares** are stable (skill 53.9%
→ 52.6%, docs 81.2% → 81.7%). Use the shares, not the absolute tokens.

---

## 4. Where the tokens went

### 4.1 Session 06 — 291 k visible input tokens, 15 requests

| Phase | Re-sent chars | Share | ≈ tokens |
|---|---:|---:|---:|
| **`SKILL.md`** (read in 3 chunks) | 645,635 | **61.6%** | **179 k** |
| Reference / craft / schema / example lookups (calls 5–9) | 219,876 | **21.0%** | **61 k** |
| `score.abc` + home-made self-check | 35,713 | 3.4% | 10 k |
| syllabify run | 30,151 | 2.9% | 8 k |
| sheet + plan + core draft | 24,142 | 2.3% | 7 k |
| human message + status lines | 2,620 | 0.3% | 1 k |
| `phrases.json` patch | 865 | 0.1% | 0 k |
| **Documentation total** | **865,511** | **82.6%** | **240 k** |

The three skill chunks alone cost 70 k + 59 k + 49 k tokens of traffic. The
first chunk is re-sent on all 14 subsequent requests.

Per-request context (k tokens), with the thinking that preceded each call:

| Req | Call | Context | Thinking before | What |
|---:|---:|---:|---:|---|
| 1 | view | 1.6 | 0 s | skill 1/3 |
| 2 | view | 6.7 | 0 s | skill 2/3 |
| 3 | view | 11.2 | 0 s | skill 3/3 |
| 4 | syllabify | 15.4 | 0 s | 82 bars, 26 lines |
| 5 | bash | 16.1 | 2 s | phrases + groove + maqam |
| 6 | bash | 17.9 | 2 s | example plan/score + rhythm |
| 7 | bash | 20.1 | 2 s | schema + rhythm rest |
| 8 | bash | 21.2 | **64 s** | grep degrees |
| 9 | bash | 21.6 | 64 s | craft: cell, cadence, melisma |
| 10 | bash | 23.7 | **664 s** | sheet + plan |
| 11 | bash | 24.7 | 664 s | core draft |
| 12 | bash | 25.1 | 668 s | score v1 + stats |
| 13 | bash | 27.4 | **761 s** | score v2 (full rewrite) |
| 14 | bash | 29.0 | 766 s | 26-row phrases patch |
| 15 | — | 29.2 | — | **no response** |

### 4.2 Session 05 — 327 k visible input tokens, 15 requests, 21 calls

| Phase | Share | ≈ tokens |
|---|---:|---:|
| **`SKILL.md`** (Skill tool) | **52.6%** | **172 k** |
| Reference / craft / schema lookups (calls 12–17) | **29.1%** | **95 k** |
| syllabify runs (3 attempts) | 3.0% | 10 k |
| sheet + plan | 1.8% | 6 k |
| lyrics write | 1.8% | 6 k |
| task list ceremony | 1.7% | 5 k |
| human + status | 0.2% | 1 k |
| **Documentation total** | **81.7%** | **267 k** |

Thinking: 489 s + 471 s + 211 s = **19.7 min (95% of the wall clock)**, 202
thought segments. The three big blocks sit immediately before the 5.5 KB sheet
and plan, which were then written in 21 seconds. No ABC followed.

### 4.3 The output side is invisible

| | Session 05 | Session 06 |
|---|---:|---:|
| Visible output (files, commands, text) | ~3.4 k tok | 5.6 k tok |
| Hidden thinking | 19.7 min, 202 segments | 12.8 min, 144 segments |
| Thinking as share of wall clock | 95% | 89% |

The export cannot price the thinking, but it is 89–95% of the run's time and its
thought segments outnumber every artifact the run produced. At a conservative
20–40 tokens/s, session 06's thinking is 15–31 k output tokens — three to six
times everything it visibly wrote.

---

## 5. The four sinks

Taken together, the four findings below produce the loop that consumed both
sessions: **read the manual → think the whole piece → write it → measure it with
a home-made proxy → rewrite it → measure again.** No step has a final output, so
the loop has no exit short of finishing everything; when the allowance ends, the
budget is gone and the deliverable set is incomplete. Each extra call also
re-pays the 43.5 KB manual.

### S1 — the 43.5 KB manual, re-sent on every request (60% of input)

In 05 it is one `Skill` result of 44,200 chars; in 06 it is three `view` results
totalling 48,936 chars. Either way the whole document enters context at the
start and is paid for again on every turn. It is the single largest block in
both sessions and the only one the 0.5.2 change did not touch.

### S2 — the composition happens in hidden thinking, before any file exists

Session 05: 19.7 min thinking → a 5.5 KB sheet, no music.
Session 06: 600 s thinking → sheet + plan + core + score in 90 seconds.

The sheet is a **transcript** of a decision already made, not the plan that
produces it. Making the sheet 10 lines changed the artifact; it did not change
the 10 minutes. Any future prompt that only reshapes the sheet will reproduce
this.

### S3 — the run checks itself with a home-made checker, then rewrites

The prompt says "run the checker once at the end" and "do not read
`checker.py`". So at call 12 the agent wrote its own ABC parser + statistics
script (~3.4 KB) into the same shell command as the score, measured bar sums,
duration spread, repeat share and chorus lift, found three misses, thought for
93 s, and **rewrote all 2.8 KB of `score.abc`**. Then it patched `plan.json`'s
register mean to match what it had written.

That is a self-imposed gate with the same numbers as the real checker. The ban
on reading the checker did not remove the checking; it forced a worse
reimplementation. In session 05 the single `checker.py` grep cost 24.7 k; here
the substitute cost ~3.4 k of output plus 93 s of thinking plus a full rewrite.

### S4 — the table returns through the tool

`syllabify.py --phrases` writes `body_bar_start` / `body_bar_end` (relative to
the sung body) and prints *"add absolute bar_start/bar_end before …"*. The
checker and `phrases.schema.json` require `bar_start` / `bar_end`. So every
session must translate 26 rows by hand after choosing the section layout. Both
05 and 06 did exactly that, at the very end, in Python:

```python
rng={1:(4,6),2:(7,9),3:(11,13), ... 26:(80,83)}
```

The 0.5.2 line "`phrases.json` owns the table" is true of the artifact and false
of the work. The work is still there; it just moved from Markdown to a dict.

---

## 6. What this falsifies

The session-05 report concluded that the 26-row sheet consumed the session and
that a rules-level 10-line sheet would fix it. The data does not support that:

- The sheet was 5.5 KB (~1.5 k tokens) and 1.8% of session-05 traffic. The
  thinking in front of it was 19.7 minutes.
- In session 06 the sheet is 10 lines and the thinking in front of it is still
  600 seconds.
- The 26-row table did not disappear; it reappeared as a dict in the final call.

The correct statement is narrower: the sheet was a **symptom** of composing in
one hidden block, and the 0.5.2 change removed the symptom, not the block.

---

## 7. Why the run stopped

- Final visible context: **29.2 k tokens** — not a context-window overflow.
- The last event is a tool result at 09:24:08 with no assistant reply.
- 12.8 minutes of the 14.4 were hidden thinking; visible output was 5.6 k.
- Artifacts at stop: `seed_sheet.md`, `plan.json`, `core_draft.abc`,
  `score.abc` (84 bars, 413 notes). Missing: `seed.abc`, `notes.md`,
  `report.json`, checker run.

This is consistent with the session's token/usage allowance being consumed
mid-turn. The transcript cannot distinguish "output/thinking allowance" from
"total-token allowance"; if the Claude usage screen shows the request-level
breakdown for 09:09–09:24, that would settle it. What it rules out is the
context window and the sheet.

---

## 8. Comparison

| | Session 04 | Session 05 | Session 06 |
|---|---:|---:|---:|
| Skill build | 0.5.0 | 0.5.1 | 0.5.2 |
| Requests / calls | — / — | 15 / 21 | 15 / 14 |
| Visible input traffic | — | 327 k | 291 k |
| Skill share of traffic | — | 52.6% | 61.6% |
| Docs share of traffic | — | 81.7% | 82.6% |
| Hidden thinking | — | 19.7 min | 12.8 min |
| Time to first ABC | — | never | call 11 (core), call 12 (score) |
| Sheet | none | 5.5 KB, 26 rows | 1.8 KB, 10 rules |
| `score.abc` | yes | **no** | yes, 84 bars |
| `seed.abc` | yes (no drums) | **no** | **no** |
| Checker runs | 1 | 0 | 0 |

Session 04 delivered; 05 and 06 both died with the work unfinished, at different
stages of the same one-turn contract.

---

## 9. What I am not changing

No skill, checker, calibration, prompt or gate has been modified for this
report. The session-06 artifacts are preserved under
`analysis/eval/runs/2026-11-24-claude-session-06/` (`chat.json`, `cost.json`,
`task.md`, `output/`).

The next change should be chosen from the evidence, and only one should be run:

| Candidate | What it removes | Evidence |
|---|---|---|
| **A. Split the skill** (≤15 KB compose card + references on demand) | ~60% of input traffic and 6 of the 8 lookup calls | S1, §4.1 |
| **B. Emit absolute `bar_start/bar_end` from syllabify** | the hand-typed 26-row table in every run | S4 |
| **C. Checkpointed deliverables** (score → seed → notes, each a finish line; checker on the first artifact) | losing the ending to a budget stop; the home-made checker | S3, §7 |
| **D. Shorter prompt / another sheet rewrite** | nothing measurable | §6 |

D is what the last two runs did. A is the token lever, B is the mechanical
correctness lever, C is the failure-mode lever. They are separable; running two
at once would repeat the attribution mistake this report corrects.

---

## Appendix — artifacts recovered from the transcript

`analysis/eval/runs/2026-11-24-claude-session-06/output/`

| File | Size | Note |
|---|---:|---|
| `seed_sheet.md` | 1,800 chars | exactly 10 numbered rules; no 26-row table |
| `plan.json` | 1,581 chars | plan template + maqam block; register mean edited to 71 after the score |
| `core_draft.abc` | 1,494 chars | 15 bars, weakest bar already fixed |
| `score.abc` | 2,778 chars | v1, 84 bars, 413 notes, n/syl 1.144 |
| `score.v2.abc` | 2,778 chars | full rewrite after the self-check; same length, different durations |

Bar count verified independently on `score.v2.abc`: **84 bars in each voice**
after expanding `Z`/`Z2`/`Z3`. The score was structurally complete when the
session stopped; only the seed, the checker and the notes were missing.

The agent's own final measurements: bars 84/84, overlap 0, 413 notes,
n/syl 1.144, mean 70.59, top 86, top-duration share 0.564, repeat share 0.233,
verse median 70, chorus median 77, lift 7, ins active 0.369, ties 2, vocal
silence 0.277.
