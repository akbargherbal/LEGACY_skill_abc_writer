# Eval report — 2026-11-24 / Claude session 05

**Run id:** `2026-11-24-claude-session-05`
**Skill:** `abc-score-writer` 0.5.1 source (contract `0.4.0`), zip
`d224199ea32a772c755f69c55d1b827b224f0539580be12ff64d35b9fb76f9df`
**Agent:** Claude (Claude.ai-style harness; model id not exported; skill mounted at
`/mnt/skills/plugins/abc-score-writer`)
**Task:** the session-05 rhythm brief: D Kurd, 80 BPM, `seed_sheet.md` and
`core_draft.abc` before any ABC, `V: Drums` in `seed.abc`.
**Delivered:** `lyrics.txt`, `seed_sheet.md`, `plan.json` (plus a patched
`phrases.json` in the workspace).
**Not delivered:** `core_draft.abc`, `score.abc`, `seed.abc`, `report.json`,
`CHANGES.txt`, the short report. No checker run. No audio.
**One-line verdict:** the run did not test the rhythm hypothesis. It spent
**19 m 42 s in hidden design**, produced a **5.5 KB seed sheet and a plan**, and
was stopped **before the first ABC note**. The scaffolding consumed the session.

> **Correction (session-06 recount).** The 26-row sheet was not the cause of the
> 19 m 42 s; it was written *after* the thinking, in 21 seconds. The thinking is
> the composition itself, and the dominant cost is the 43.5 KB skill re-sent on
> every request (52.6% of this run's input traffic) plus 29.1% of reference
> lookups. See `2026-11-24-claude-session-06.md` §4–§6. The absolute token
> figures below use a different request count/char ratio; the shares agree.

---

## 0. What actually happened

The human message is only `/abc-score-writer` plus an attachment. The attachment
is the task prompt (5,118 bytes; 4,075 extracted characters). The empty file name
is an export artifact, not a missing prompt: the agent read the attachment and
wrote `lyrics.txt` from it. **The user delivered the brief.**

The assistant produced one long turn:

| Field | Value |
|---|---:|
| Messages in export | 2 (1 human, 1 assistant) |
| Assistant turns with tools | **14** |
| Tool calls | **21** |
| Tool-result characters | **91,252** |
| Output files | 3 (+ `phrases.json`) |
| ABC characters written | **0** |
| Checker runs | **0** |
| Wall clock | **20 m 43 s** |
| Hidden thinking | **19 m 42 s (95% of wall)** |
| Visible tool execution | ~61 s |
| Thinking summaries exported | **202** |

Timeline:

| Time | What |
|---|---|
| 08:22:32 | Prompt received; skill loaded (44,200-char result) |
| 08:22:36–08:22:50 | 5 `TaskCreate`; lyrics written; syllabify attempted |
| 08:22:50–08:23:06 | 2 failed syllabify calls, then one success; 5 reference reads |
| **08:23:10–08:42:43** | **19 m 33 s of continuous hidden design** |
| 08:43:04–08:43:15 | `seed_sheet.md`, `plan.json`, `phrases.json` patched; session stops |

The last assistant text before the final writes:

> Picking up at the design stage. I'm writing `seed_sheet.md` first, before any
> ABC, as you asked.

That sentence is the whole failure. The agent obeyed the prompt. The prompt
forbade ABC until the sheet and the core were delivered; the sheet took the rest
of the budget, and the core never started.

---

## 1. Cost model

The earlier 21-call count is the number of tool calls. The API bill is the number
of **assistant requests**: parallel tool calls in one assistant message are one
request. Grouping the export by request gives **14 requests**, not 21.

Method: for each request, sum the characters of everything before it (human
message, prior assistant text/tool inputs, prior tool results); divide by 4. This
is a **lower bound**: it excludes the system prompt, tool schemas, and the
redacted thinking blocks.

| Metric | Value |
|---|---:|
| Requests | 14 |
| Tool calls | 21 |
| Sum of request inputs | **266,314 tokens** (lower bound) |
| Final context | 28,012 tokens |
| Visible output (text + tool inputs) | 3,288 tokens |
| Input : visible output | **81 : 1** |
| Thinking | 19 m 42 s, 202 summaries |

With a typical 8–12 k-token system prompt and tool schema on every request, add
~110–170 k input tokens. With the hidden thinking, a total in the
**450–550 k** range is plausible. The exact thinking count is not in the export;
the time and the 202 summaries are.

Session 04 was estimated at ~30 k tokens and delivered a score and a seed.
Session 05's **visible** input alone is ~9× that, and it delivered no score. The
comparison is not exact (session 04's tool payloads were hidden), but the
direction is unambiguous.

---

## 2. Where the requests went

| Phase | Requests | Tool calls | Input tokens | Share |
|---|---:|---:|---:|---:|
| Skill load | 1 | 1 | 1,912 | 0.7% |
| Task list (+ one lyrics write) | 4 | 9 | 78,018 | **29.3%** |
| Syllabify (3 attempts) | 3 | 3 | 41,835 | 15.7% |
| Reference reading | 3 | 5 | 63,593 | 23.9% |
| Seed sheet + plan + phrases | 3 | 3 | 80,956 | **30.4%** |
| **Total** | **14** | **21** | **266,314** | 100% |

The two planning phases — task list and sheet/plan — are **59.7% of the visible
input**. Neither produced a note. The score is 0% of the budget.

The task phase includes one `Write` of `lyrics.txt` in the same request as a
`TaskUpdate`; pure task requests (5 creates + 3 updates) are ~64.7 k (24.3%).
The task tools returned **396 characters** in total.

---

## 3. The context tax — the real line item

Each request re-sends everything read so far. A 44 KB skill is not "11 k tokens
once"; it is 11 k tokens on every request.

| Artifact | Size | Requests present | Carry cost | Share of total |
|---|---:|---:|---:|---:|
| `SKILL.md` (Skill result) | 44,200 chars | 13 | **143,650** | **53.9%** |
| `craft.md` | 25,659 chars | 7 | 44,903 | 16.9% |
| `rhythm.md` + `groove.abc` | 8,295 chars | 7 | 14,516 | 5.5% |
| `numbers.md` + `checker.py` grep | 4,165 chars | 5 | 5,206 | 2.0% |
| `reference.md` §5.1 | 2,844 chars | 7 | 4,977 | 1.9% |
| `example/score.abc` + plan | 2,029 chars | 6 | 3,044 | 1.1% |
| **Documentation carry total** | | | **216,296** | **81.2%** |
| syllabify output | 2,429 chars | 8 | 4,858 | 1.8% |

**81% of the input bill is re-sending documentation the agent already read**;
another 1.8% is the syllabify table. The actual work — the human brief, the
writes, the small tool results — is the remaining 17%.

The single biggest lever is not a bad tool call. It is the 43.5 KB `SKILL.md`
re-sent 13 times. At 15 KB, the same 13 requests would carry ~48.8 k instead of
143.7 k: a **95 k-token saving with no change to the music**.

---

## 4. The 19 m 42 s

The export redacts thinking, so its token count is not measurable. The summaries
are:

| Keyword in the 202 summaries | Count |
|---|---:|
| bar | **84** |
| line | 47 |
| check | 37 |
| verse | 31 |
| melisma | 29 |
| cadence | 26 |
| chorus | 16 |
| syllable | 15 |
| tally | 9 |

The agent re-derived the same bar allocation at least three times:

- summaries 24–27: “Allocating bars… Tallying the bar budget… Tallying the full
  bar count”;
- summaries 86–109: “Mapping out the song's bar layout… Tallying the bars for
  each section… Assigning bars to each sung line”;
- summaries 168–194: “Planning the bar allocation for each section… Allocating
  bars for each section… Mapping each lyric line to its start beat and bars.”

That is not composing. It is solving a 26-row arithmetic table in the head. The
table was not written until 08:43; the thinking happened first. The sheet is a
**transcript of the design**, not a working plan that guided it.

This is the opposite of what the sheet was for. Session 04 failed because there
was no sheet and the full score came first. Session 05 added the sheet and got
19 minutes of hidden design, a polished sheet, and no score. The sheet became a
**graded deliverable**, so the model perfected it before writing music.

---

## 5. Culprits, ranked

Costs are visible-input lower bounds; they overlap with the context tax and must
not be added.

| # | Culprit | Evidence | Cost | Serves the ear? |
|---|---|---|---|---|
| 1 | **Sheet-first 10-bullet prompt** | Agent's last text; 0 ABC; 19 m 42 s thinking; 5.5 KB sheet | 19 m 42 s + 81 k (30.4%) | Partly: cell, cadence, groove, events. **No** for the 26-row table. |
| 2 | **43.5 KB `SKILL.md` loaded whole** | 44,200-char Skill result, present in 13 requests | **143.7 k (53.9%)** | The method, at ~3× the needed size. |
| 3 | **Full `craft.md` read** | 25,659-char `cat`; 7 requests | 44.9 k (16.9%) | Partly; ~8 KB of it was needed for the first pass. |
| 4 | **26-row lyric map / slots** | 1,370 chars of sheet; 84 “bar” summaries; duplicates `phrases.json` | Most of the thinking | **No.** The script owns the line table. |
| 5 | **8 task-tool calls** | 5 creates + 3 updates; 396 chars returned | 4 requests, ~65–78 k (24–29%) | **No.** Harness UI, not music. |
| 6 | **15-field plan form** | 1,949 chars; mostly copied defaults | 1 write, ~27 k request | **No.** Checker plumbing. |
| 7 | **2 failed syllabify calls** | `--phrases` with no path; then argparse error | 27.7 k (10.4%) | **No.** |
| 8 | **`checker.py` / `numbers.md` grep** | 4,165-char result; skill says “do not read scripts” | 24.7 k request | **No.** Maqam block is already in SKILL §3.2. |
| 9 | **Duplicate lyrics write** | Wrote 1,601 chars, then copied the upload over it | 13.4 k request | **No.** Empty attachment name caused it. |
| 10 | **Nine deliverables for one score** | Only 3 of 9 reached | Future overhead | **No.** Report ×3, plan, phrases, critique, core, score, seed. |

The ranking has two axes. By **causality**, #1 is first: it is why there is no
score. By **tokens**, #2 is first: the skill is more than half the bill. Both are
ours, not the model's.

---

## 6. Requirements that serve no purpose

These are the concrete pieces to cut. Each is a requirement the agent obeyed; none
of them improves the ear.

1. **The per-line `slots` column and the 26-row bar table.** `phrases.json`
   already carries `bar_start`, `bar_end`, syllables and pauses. The sheet's
   extra columns (start beat, anchor/short/fill/cad) are hand arithmetic. They
   are results of composing, demanded before composing. This is the direct cause
   of the 19 minutes.

2. **The 15-field `plan.json`.** `simultaneity_exception`, `ties_min`,
   `min_fill_notes`, `ins_active_share_min`, `chords_min`,
   `max_top_duration_share`, `tessitura_share_ge_c5_max` are gate defaults, not
   musical decisions. The agent copied the template values. The checker can
   default them; a 6-field plan is enough for the brief.

3. **Three reporting artifacts.** `report.json` is the checker's `--json`
   output; `CHANGES.txt` is the deviation list; the short report is prose. One
   10-line `notes.md` plus the checker JSON would do.

4. **The separate `core_draft.abc` and four-line critique as a stage.** The core
   is useful; as a separate deliverable it is another gate before the score. It
   can be the first 8 bars of `score.abc` or a comment block.

5. **The task list.** Eight calls, four requests, 396 characters. It exists
   because the prompt reads like a five-phase project. A single-artifact
   composition does not need a task board.

6. **Reading `reference.md` §5.1 and grepping `checker.py`.** The maqam block is
   documented in SKILL §3.2. The agent did not trust the doc and reverse-engineered
   the checker, against the skill's own “run the scripts; do not read them.”

7. **The polished sheet.** A one-page sheet should be 10 lines of **rules**:
   “sadr opens on 5, ajuz closes on 3/1; melisma 4–6 on ajuz, 8 at L24; verse
   groove kick 1/3&, snare 2/4; events at bars 8, 22, 34.” The agent wrote the
   **instances** of those rules for all 26 lines. The rules are the plan; the
   instances are the score.

The principle: **the sheet should hold rules, not results.** Results are what the
score and `phrases.json` are for. Asking for results before the music forces the
model to compose in its head, which is exactly what happened.

---

## 7. What is not the culprit

- **The rhythm method.** The sheet's groove, 2-beat hole, varied starts and three
  interaction events are good. The agent understood `rhythm.md` and applied it.
  The defect was never reached in audio because there was no score.
- **The checker or the gate.** It was never run. No threshold moved.
- **The model's effort.** It did substantive design for 20 minutes. It was not
  lazy; it was over-managed.
- **The user's delivery.** The task was attached and read. The empty file name
  cost one duplicate write, not the run.

---

## 8. The causal story across runs

| Run | Process | Result |
|---|---|---|
| 04 | No sheet, no core; full 92-bar score first; 3 checker runs | Score + seed delivered; ear rejected the drums |
| 05 | Sheet first, 10 bullets, core next; no score yet | Sheet + plan delivered; budget ended before ABC |

The 0.5.1 fix was right in content and wrong in packaging. It converted a
10-line planning aid into a 5.5 KB document with 156 table cells, and the
session-05 prompt added more columns on top. The agent complied completely: all
ten bullets are present in `seed_sheet.md`. Full compliance, zero music.

---

## 9. Recommended next change (one)

**Plan at the level of rules, not per-line results.**

Replace the 10-bullet sheet with a 10-line sheet:

```
Frame: D Kurd, 80 BPM, 81 bars; sections + bar ranges.
Cell: degrees + rhythm (one line).
Period: sadr opens on 5; ajuz closes on 3 or 1; final tonic.
Cadence rule: 5 most common; b7, b6; tonic only at closes.
Melisma rule: 4-6 on ajuz cadences; 8 at the peak line.
Riff: 2 bars; returns at 40, 71, 79.
Subtraction: bar 34 stop; chorus half-time; outro drums out.
Groove: verse kick 1/3&, snare 2/4; chorus half-time; last line out.
Events: bar 8 push/unison; bar 22 fill; bar 34 stop.
Open question: the weakest bar, to fix in the core.
```

- `phrases.json` owns the 26 rows; the sheet does not repeat them.
- Write the 8-bar core first; the sheet's rules are checked against it.
- Write `score.abc` and `seed.abc` before the report.
- `notes.md` is 10 lines, after the score exists.
- No task list; no `checker.py` reading; one checker run at the end.

Expected effect with the current skill: 14 requests → ~7–8; visible input
266 k → ~110–130 k; thinking 20 min → a few minutes; a score exists before the
report. Do **not** add a gate or a metric.

If this works, the next one-change run is the **skill split** (0.5.3): a 12–15 KB
compose card, with the plan field reference, report format and corpus provenance
moved to `references/`. That is the 95 k-token lever. Do not do both in the same
run; then we cannot tell whether the score improved because of the lean prompt
or the smaller context.

---

## 10. If we do nothing

The next run will repeat the pattern. The skill is 43.5 KB; the prompt asks for
nine artifacts; the sheet asks for 26 rows of results before the first note. A
capable model will again try to solve the whole composition in hidden thinking,
write a beautiful sheet, and stop. The ear will again have nothing to judge.
