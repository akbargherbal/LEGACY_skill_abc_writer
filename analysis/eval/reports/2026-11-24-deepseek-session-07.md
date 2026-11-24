# Session 07 post-mortem — measured cost, gate-driven composition

**Run:** `2026-11-24-deepseek-session-07`
**Session:** `ses_df2fe0a84ffeqC73F3pspJjbVx` (OpenCode, agent `build`)
**Model:** `opencode/deepseek-v4.1-flash-free`, variant `high` — not `v4-pro`
**Skill:** `abc-score-writer` 0.5.2, frozen. `SKILL.md` SHA-256
`8c469bec…734a7d`; package zip SHA-256 `e7fca141…7d0f9` (same as session 06).
**Task:** same brief as session 06 — D Kurd, 80 BPM, 4/4, 26 lines, 361 syllables.
**Delivered:** all nine artifacts plus `lyrics.txt`; no audio.
**Status:** `succeeded`; 47 m 49.9 s wall; 75 assistant requests; 86 tool calls;
2 auto-compactions; cost **$0.00**.
**One-line verdict:** a complete, checker-passing deliverable set produced by a
**front-loaded, gate-driven** process — 8 minutes of composition before the first
file, two full score versions, **five** checker runs, and **98.2%** of 6.66 M
prompt tokens served from cache. The music is not judged here: there is no audio.

---

## 1. TL;DR

1. **The run finished.** `score.abc` is 82 bars in each of two voices;
   `seed.abc` is 82 bars of Vocal + 82 of Drums and its vocal is textually
   identical to `score.abc`; `core_draft.abc` is 12 bars in each voice. The
   checker's final pass is `PASS 0 hard check(s) failed, 2 warning(s)`.
2. **H1 is partly confirmed: the piece is front-loaded, but not composed once
   and not entirely before the first file.** 8 m 00 s of reasoning (112 k
   characters) preceded the first file; the first block was cut by the output
   limit, then the model wrote the sheet, plan, phrases and core, and composed
   and rewrote the score in further 3–3.5-minute blocks. The sheet is still a
   transcript, not a plan.
3. **H2 is confirmed without qualification.** The self-check is driven by the
   plan's numbers. The model says it in plain language: *“I must meet it or …
   the checker fails hard”* (req 58), *“Need sum ≥ 28,566 for mean 69.0 →
   +161”* (req 60), *“Mean 69.133 ✓ (≥69), 2-share 0.64 ✓ (≤0.65)”* (req 61).
   The final metrics sit on six different limits. No audio was auditioned.
4. **H3: cache read dominates traffic; reasoning dominates generation;
   documentation is a cached baseline.** Cache read is **98.2%** of traffic
   (6.54 M of 6.66 M); fresh input is 1.8%. Reasoning is 202 k tokens — 83.8%
   of generated tokens and 5.16× the visible output. A rough carry estimate puts
   the whole doc set at ~12% of traffic and the 43.5 KB `SKILL.md` at ~4.4%.
   The session-06 report's 82.6% documentation share described *re-sent text*,
   not billed cost. As a cost claim, its emphasis on the 43.5 KB skill is
   **incomplete and, in its framing, wrong**; as a description of what is
   re-read, it is still right.
5. **H4 is confirmed.** The 26-row table returned as a hand-typed 26-entry
   offset dict: `off={1:6, 2:6, …, 26:22}` followed by
   `bar_start = body_bar_start + o` (tool 22). The table did not disappear; it
   became a different hand-typed table.
6. **The harness contaminated the run.** The working directory contained the
   analyst `notes.md`, `checklist.md`, `README.md` and the exporter. The agent
   read the checklist, the README and the first 40 lines of the analyst notes;
   it even says *“notes.md is the analyst notes (not to be pasted)”* (req 8) and
   preserved it as `notes.analyst.md` before overwriting. The token/cost data is
   still exact; the **process** evidence is not clean-room and is provisional
   until a clean re-run.
7. **The one proposed change is not the skill split.** It is to set
   `strict_shape: false` in the plan template/example so the declared shape
   targets stay warnings. That is the switch that made the model rewrite the
   score for `max_top_duration_share`, chorus lift and the duration/ties
   tightness (the register mean was a separate sanity fix). The checker and
   calibration stay frozen; the ear stays the verdict.

---

## 2. Run facts

| Field | Value |
|---|---|
| Run id | `2026-11-24-deepseek-session-07` |
| Harness / agent | OpenCode / `build` |
| Model | `opencode/deepseek-v4.1-flash-free`, variant `high` |
| Provider | `opencode` |
| Skill | `abc-score-writer` 0.5.2, frozen |
| `SKILL.md` | 43,660 bytes, SHA-256 `8c469bec…734a7d` |
| Package zip | `dist/abc-score-writer.zip`, SHA-256 `e7fca141…7d0f9` |
| Task | D Kurd, 80 BPM, 4/4, 26 lines, 361 syllables |
| Start / end (UTC) | 10:02:41.966 → 10:50:31.901 |
| Wall clock | 2,869.9 s = **47 m 49.9 s** |
| Assistant requests | **75** (+ 2 compaction calls = 77 model calls) |
| Tool calls | **86** (85 completed, 1 error) |
| Aborted requests | **2** (`ECONNRESET`, retry attempts 2 and 3) |
| Compactions | **2**, both `auto` |
| Outcome | `succeeded` (`idle`) |
| Cost | **$0.00** |
| Audio | none (no mp3/wav/ogg/flac in the package) |

---

## 3. What happened

| Time (UTC) | Event | Evidence |
|---|---|---|
| 10:02:42 | User message: `@skills/abc-score-writer/ Follow the instructions of @task.md` | `msg_20d01f5890012ibf6xvLs4dmst` |
| 10:02:49 | **`skill` tool fails**: “Unable to load skill abc-score-writer” | tool 1, `msg_20d01f870001pLJ2Ig3O0Ncq3v` |
| 10:02:55 | Agent reads `SKILL.md` directly (47,306-char result) | tool 2, `msg_20d0213ff001Cb20Wqt6M9LXZv` |
| 10:03:25 | Reads `README.md` **and** `checklist.md` | tools 9–10, `msg_20d028853001hVBfNw7qXWNgBz` |
| 10:03:32 | `ls` plus `head -40 notes.md` — **reads the analyst notes** | tool 11, `msg_20d029e4e001OjA0xGjnwOX6Dx` |
| 10:03:50 | Syllabify once: 26 lines, 361 syllables, 82 bars (58 body + 24 free) | tool 14, `msg_20d02dd0b001OKnTxwAv8vche6` |
| 10:04:50–10:13:00 | **Composition blocks**: 154.7 s + 325.4 s, 112 k chars of reasoning, no file yet | req 13–14, `msg_20d065ebc001JWzXufwehBhiYJ` |
| 10:13:00 | Req 14 ends `finish: length` (31,937 reasoning tokens); synthetic message: “hit the output token limit … break the remaining work into smaller pieces” | `msg_20d0b64c2001y5XUls5dd5qKKt` |
| 10:13:17 | `seed_sheet.md` written (first file) | tool 20, `msg_20d0b64c5001vjrCa8JcyWUq8v` |
| 10:13:27 | `plan.json` written | tool 21, `msg_20d0ba6cb001vOnceef1pjxTC8` |
| 10:13:43 | 26-entry `off` dict patches `phrases.json` | tool 22, `msg_20d0bd15c001lCpQ2DL2WrpT8B` |
| 10:14:55 | `core_draft.abc` written (12 bars/voice) | tool 23, `msg_20d0c0ed9001ShR8Ms0YOY0GQJ` |
| 10:18:20 | `score.abc` v1 written | tool 24, `msg_20d0d290c001ciRbEyjpXzqrXh` |
| 10:19:07–10:23:02 | Home-made stats, 192.5 s thinking, **score v2 full rewrite** | req 25, tool 30, `msg_20d11a6ad001FXBUgpTz8ylTfu` |
| 10:23:25 | **Compaction 1** (auto): context 167,940 → 19,719 tokens | `msg_20d14ee93001No2dGEVSOkmK9U` |
| 10:33:04 | `seed.abc` written | tool 47, `msg_20d1c26f1001EVLK2juVjphPv5` |
| 10:36:24 | Checker #1: `FAIL [contract] runtime parse` | tool 61, `msg_20d20ad1000140MgY6YCKBeY5j` |
| 10:37:53 | Checker #2: `FAIL 2 hard check(s) failed` (mean, duration spread) | tool 67, `msg_20d22084e001DFNlGBlXItKPhx` |
| 10:41:09–10:45:13 | 233.9 s tuning block: +161 register sum, 30 mordents, cadence octaves | req 60, `msg_20d252bf0001CL3YAgIyv25OKl` |
| 10:46:58 | Final `score.abc` / `seed.abc` emitted | tool 72 (req 62), `msg_20d296272001itk0hy1dRYftYy` |
| 10:47:49 | Checker #3: `PASS 0 hard check(s) failed, 2 warning(s)` | tool 76, `msg_20d2af5ec001RgECfzQtbQSGqR` |
| 10:48:22 | `notes.md` written | tool 77, `msg_20d2b4975001Yeri0EwiA8UZme` |
| 10:49:28 | **Compaction 2** (auto): context 168,812 → 22,153 tokens | `msg_20d2cc9dd001XH1TSrOth7k2vY` |
| 10:50:04 | `seed_sheet.md` trimmed to exactly 10 lines | tool 84 |
| 10:50:13 / 10:50:20 | Checker #4 and #5 (verification) | tools 85–86 |
| 10:50:31 | Idle; `finish: stop` at req 75 | `msg_20d2d94cd001gzVb3vxTDbQveX` |

---

## 4. Deliverable audit

All paths are under
`analysis/eval/runs/2026-11-24-deepseek-session-07/session-07/`.

| File | Bytes | Lines | Independent check |
|---|---:|---:|---|
| `lyrics.txt` | 2,868 | — | copied from `input/lyrics.txt` once |
| `prosody.json` | 10,101 | — | syllabify output, 361 syllables |
| `phrases.json` | 5,885 | 293 | 26 rows, 58 body bars, 361 syllables; absolute bars 7–80 |
| `seed_sheet.md` | 2,014 | 10 | exactly 10 numbered rules; no 26-row table |
| `plan.json` | 1,536 | 38 | 82 bars; key/tempo/meter/register/maqam; 4 deviations; `strict_shape: true` |
| `core_draft.abc` | 817 | 33 | **12 bars Vocal / 12 bars Ins**, all 16 units |
| `score.abc` | 3,296 | 134 | **82 bars Vocal / 82 bars Ins**, all 16 units |
| `seed.abc` | 4,516 | 61 | **82 bars Vocal / 82 bars Drums**, all 16 units; vocal == score vocal |
| `report.json` | 10,738 | 429 | `ok: true`; 0 FAIL; 2 WARN (`sections`, `answer mutation`) |
| `notes.md` | 1,740 | 10 | exactly 10 numbered lines |
| `notes.analyst.md` | 4,060 | 90 | extra: the analyst notes, preserved by the agent |

The zip also contains the harness package (`README.md`, `checklist.md`,
`opencode_export.py`, `task.md`, `input/`, `skills/`); these are not
deliverables. `notes.analyst.md` is the agent's preservation of the analyst
`notes.md`, not a deliverable.

**Independent bar counts** (own parser, not `report.json`; `Z<n>` expanded to
`n` bars):

- `score.abc`: Vocal 82, Ins 82; every bar 16 units. 444 note tokens in the
  vocal, 443 sounding after the single tie (`d2-d2`); Ins 138.
- `seed.abc`: Vocal 82, Drums 82; every bar 16 units; 502 drum note tokens.
  The vocal is textually identical to `score.abc`'s vocal after removing chord
  symbols.
- `core_draft.abc`: Vocal 12, Ins 12; every bar 16 units.
- `phrases.json`: 26 rows, 361 syllables, 58 body bars; every row has
  `bar_start`/`bar_end`; the 26 offsets are exactly the hand-typed dict.

**Skill integrity.** The skill copy in the zip is pristine: `SKILL.md` and all
scripts (`checker.py`, `abc_tools.py`, `syllabify.py`, `calibration.json`, …)
hash-match `02_maqam-score/`. Only `CHANGELOG.md` and `data/README.md` are
absent (packaging), and `scripts/__pycache__/abc_tools.cpython-313.pyc` was
added by running the checker. No `write`/`edit` tool call targets `skills/`
during the run. This is a genuine 0.5.2 run.

**Deliverable order:** sheet (10:13:17) → plan (10:13:27) → phrases (10:13:43)
→ core (10:14:55) → score (10:18:20) → seed (10:33:04) → notes (10:48:22).
Every deliverable existed before the session ended.

---

## 5. Exact cost

### 5.1 Totals and cache

The header totals reconcile with `messages[]` plus the two compaction
messages. The residual is consistent with the two aborted transport retries,
which logged reasoning text but no token row; it is ≤0.1% of every column.

| Quantity | Header (`info.tokens`) | Sum of messages + compactions | Residual |
|---|---:|---:|---:|
| Fresh input | 119,731 | 119,634 | +97 |
| Cache read | 6,536,576 | 6,536,192 | +384 |
| Cache write | 0 | 0 | 0 |
| Output | 39,165 | 39,157 | +8 |
| Reasoning | 202,235 | 202,196 | +39 |
| Prompt traffic (`input + cache_read`) | **6,656,307** | 6,655,826 | +481 |
| Cost | **$0.00** | $0.00 | 0 |

- **Cache share = 6,536,576 / 6,656,307 = 0.9820 → 98.2%.**
- Fresh input share = **1.8%**.
- Reasoning = 202,235 tokens; **83.8%** of generated tokens
  (`reasoning / (output + reasoning)`), **5.16×** the visible output.
- Visible output = 39,165 tokens (16.2% of generated).
- 75 assistant requests; average context **88,751 tokens**; maximum **168,812**
  (req 69, just before compaction 2).
- Cost is $0.00 because the model is free. The token volumes are the comparable
  quantity, not the dollar figure.

### 5.2 Phase table

| Phase | Reqs | Tools | Fresh input | Cache read | Output | Reasoning | Wall |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0. Docs / setup (req 1–12) | 12 | 18 | 53,242 | 435,072 | 1,070 | 5,608 | 126.6 s |
| 1. Composition (req 13–19) | 7 | 6 | 1,629 | 694,656 | 3,473 | 74,136 | 810.6 s |
| 2. Score v1→v2 (req 20–26) | 7 | 7 | 3,748 | 1,029,120 | 5,438 | 22,931 | 303.9 s |
| 3. Seed + checker loop (req 27–69) | **43** | **49** | 42,464 | **4,030,336** | 22,599 | **98,797** | **1,555.5 s** |
| 4. Close / verify (req 70–75) | 6 | 6 | 17,189 | 128,256 | 1,041 | 724 | 62.8 s |
| Compaction calls | 2 | — | 1,362 | 218,752 | 5,536 | 0 | — |
| **Total** | **75** | **86** | **119,634** | **6,536,192** | **39,157** | **202,196** | **2,859.4 s** |

Phase 3 is the cost centre: 43 requests, 49 tool calls, 62% of all cache read,
49% of all reasoning, 26 minutes. It contains the seed build, two failing
checker runs, the +161-sum tuning block, the 30-mordent rewrite, the final
checker pass, and the notes. The 8-minute composition (phase 1) is the
second-largest reasoning block, but phase 3 is larger. The phases sum to
2,859.4 s of model time; the remaining ~10.5 s is inter-call gap.

### 5.3 Context growth and compactions

| Req | Time | Context | Input | Cache read | Output | Reasoning | Duration | What |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 13 | 10:04:50 | 62,210 | 258 | 61,952 | 157 | 13,294 | 160.9 s | composition begins |
| 14 | 10:07:31 | 76,225 | 577 | 75,648 | 63 | 31,937 | 329.2 s | **`finish: length`** |
| 15 | 10:13:00 | 108,262 | 102 | 108,160 | 728 | 434 | 16.8 s | sheet/plan |
| 19 | 10:14:56 | 118,976 | 64 | 118,912 | 1,126 | 20,707 | 205.0 s | score v1 |
| 25 | 10:19:50 | 147,134 | 190 | 146,944 | 1,154 | 19,633 | 192.5 s | score v2 |
| 26 | 10:23:02 | **167,940** | 1,156 | 166,784 | 1,069 | 1,340 | 22.4 s | before compaction 1 |
| 27 | 10:23:25 | **19,719** | 12,423 | 7,296 | 105 | 44 | 8.3 s | after compaction 1 |
| 60 | 10:41:09 | 128,845 | 717 | 128,128 | 1,177 | 19,762 | 243.9 s | tuning block |
| 69 | 10:49:11 | **168,812** | 620 | 168,192 | 535 | 905 | 17.7 s | before compaction 2 |
| 70 | 10:49:28 | **22,153** | 14,729 | 7,424 | 130 | 229 | 15.7 s | after compaction 2 |

The context grows to ~168 k and is cut back twice. The two compactions are not
free: they generate 8,050 + 8,085 characters of summary with 5,536 output
tokens — **14.1% of all output** — plus 218,752 cache read and 1,362 fresh input.
They are 2 of 77 model calls.

### 5.4 Largest reasoning blocks

| Req | Msg id | Chars | Seconds | Reasoning tokens | Finish | What it spends the block on |
|---:|---|---:|---:|---:|---|---|
| 14 | `msg_20d065ebc001JWzXufwehBhiYJ` | 75,568 | 325.4 | 31,937 | **length** | Whole-piece design, bar arithmetic, melisma counting; cut by the output limit |
| 60 | `msg_20d252bf0001CL3YAgIyv25OKl` | 58,438 | 233.9 | 19,762 | tool-calls | +161 register sum, pitch distribution, 30 mordents, cadence octaves |
| 19 | `msg_20d0d290c001ciRbEyjpXzqrXh` | 44,546 | 200.4 | 20,707 | tool-calls | Core/score: 82-bar vocal list, durations, pauses |
| 25 | `msg_20d11a6ad001FXBUgpTz8ylTfu` | 40,283 | 186.5 | 19,633 | tool-calls | Self-check misses → full score v2 |
| 13 | `msg_20d03e9cf0015SssgFlmi5Fg7Y` | 36,253 | 154.7 | 13,294 | tool-calls | Cell, period, cadence, form; first 112 k chars of the cluster |

These five blocks are 105,333 reasoning tokens — **52%** of all reasoning — in
about 18 minutes. The two composition blocks (13+14) are 480.1 s = **8 m 00 s**,
before the first file at 10:13:17.

### 5.5 Finish reasons

| Finish | Count | Where |
|---|---:|---|
| `tool-calls` | 71 | normal tool turns |
| `length` | 1 | req 14, the composition block (31,937 reasoning tokens) |
| `error` | 2 | req 45–46, `ECONNRESET` retry attempts 2 and 3; no token rows |
| `stop` | 1 | req 75, final answer |

The two `error` messages are a transport retry of one request; the run
recovered at req 47. The header residual in §5.1 is consistent with these
unrecorded attempts.

---

## 6. Reasoning forensics

The full trace is `parsed/reasoning.md` (71 reasoning parts, 202,196 tokens,
531 KB). All quotes below are from that file; `req` numbers refer to the
assistant requests in `cost.csv`.

### H1 — Was the whole piece composed in one block before any file existed?

**Verdict: partly confirmed. Front-loaded, but not one block and not the whole
piece before the first file.**

- Req 13 opens: *“OK. Let me now think about the composition itself. This is the
  main work. Let me design carefully.”* It then goes bar by bar: *“bar 7: 5
  syllables … A2 c2 B2 A2 z2 A6”*, *“bar 8 … G2 F2 _E2 D4 z2 F4”*, and so on.
- Req 14 continues for 325 s and says: *“Let me write out the whole thing now,
  carefully.”* and *“Let me define the vocal bars in order (82)”* and *“Final
  vocal (I’ll write it as a list of 82 entries, Z for rests).”* This is before
  any deliverable exists.
- Req 14 ends with `finish: length` at 31,937 reasoning tokens. The synthetic
  message at 10:13:00 tells it to break the work into smaller pieces. Req 15
  writes `seed_sheet.md` (10:13:17); req 16 writes `plan.json` (10:13:27); req 17
  patches the phrase dict (10:13:43).
- Req 19 (200 s) still says: *“Let me write the score.abc now with all 82 bars,
  then count/patch”* and *“Let me write it now — the whole score.”* Req 25
  (186 s) says: *“I’ll replace the whole score.abc with the final version.”*

So the piece was **front-loaded**: 8 m 00 s of reasoning before the first file,
then two full re-compositions after the sheet/plan existed. The 06 report's
“one hidden block” is the right shape but the wrong singularity: the first
block was cut by the harness, and the model kept composing/rewriting after it
had written files.

**The sheet is still a transcript, not a plan.** It was written after the
8-minute block, and it was later revised to match the score: tools 73–74
(10:47) change the cadence rule from *“tonic only at 34, 41, 62, 69, 80”* to
*“internal qaflas take the upper tonic at 11, 34, 41, 49, 58, 62, 69”*, and
change the melisma rule to the 16th upper-neighbour shake. Compaction 2's own
summary says: *“`seed_sheet.md` rules 6, 7, 9, 10 were revised to match the
built score/seed.”* The sheet records decisions; it did not drive them.

### H2 — Was the self-check driven by plan targets before any listening language?

**Verdict: confirmed, explicitly and repeatedly.**

- The gate numbers are present before any music. Req 4: *“I must then write music
  that satisfies them: vocal mean 70±3 (sanity ±5 so 65-79… wait sanity is
  74±5 = 69-79; structure register mean 70±3 = 67-73).”* Req 10 lists the plan
  targets and designs the 82-bar form around them.
- Req 58, after checker #2: *“Two hard fails: 1. `register mean 68.6 vs sanity
  74 +/- 5` → sanity floor 69. Need mean ≥69.0. … 2. `duration spread target
  76% (plan max 65%)` … This is a ‘structure’ hard fail because the plan sets
  `max_top_duration_share` 0.65. The task said ‘leave the gate targets at the
  template defaults’ … So I must meet it or … the checker fails hard.”*
- Req 60 computes the exact number of semitones: *“N=414, sum=28,405, mean
  68.611. Need sum ≥ 28,566 for mean 69.0 → +161.”* It then chooses 30 mordents
  and raises cadence notes to D5.
- Req 61 reports: *“Mean 69.133 ✓ (≥69), 2-share 0.64 ✓ (≤0.65), notes/syllable
  1.23 ✓ (1.10-1.45). Durations 5 distinct ✓. Margin on 2-share: 0.640 vs 0.65
  — tight but passes.”*
- The deliverable `notes.md` admits the tuning: *“the internal qaflas went up to
  D5 to bring the mean to 69.1.”*
- The only listening language in the self-check is verbal: *“let me
  sanity-listen (mentally)”* (req 61), after the numeric changes. `notes.md`
  says: *“offline pass, no renderer or audio, so nothing was auditioned.”*

The final metrics sit on the limits:

| Metric | Target | Final | Margin |
|---|---:|---:|---:|
| Register mean | sanity floor 69 | **69.1** | +0.1 |
| Top-duration share | structure max 0.65 | **0.64** | −0.01 |
| Chorus lift | min 5 | **5.0** | 0 |
| Distinct durations | min 5 | **5** | 0 |
| Ties | floor 1 | **1** | 0 |
| Repeated-pitch share | sanity floor 20% | **20.8%** | +0.8 pts |
| Notes / syllable | 1.10–1.45 | 1.23 | inside |
| Maqam fit | ≥0.95 | 1.00 | inside |
| Silence | floor 22% | 34% | inside |

This is the signature of writing to the gate, not to the ear. The agent read
the checklist's *“No gate-chasing: no ‘0 warnings’, no metric target”* and did
it anyway, because the checker's `strict_shape: true` makes the plan's shape
targets hard failures. The instruction “the ear is the verdict” cannot override
a hard FAIL.

### H3 — What dominates: documentation, reasoning, or output?

**Verdict: cache read dominates the bill; reasoning dominates generation;
documentation is a small cached baseline. The 06 report's emphasis on the
43.5 KB skill was incomplete and, as a cost claim, wrong.**

- **98.2%** of the 6.66 M prompt traffic is cache read (6,536,576 tokens).
  Fresh input is 1.8% (119,731). Visible output is 0.59% of traffic
  (39,165); reasoning is 3.0% (202,235).
- On the generated side, reasoning is **83.8%** of output+reasoning and **5.16×**
  visible output. Output is 39,165 tokens, 7× session 06's ~5.6 k visible
  output.
- The 06 report estimated **291 k** visible input traffic for 15 requests. This
  run measured **6.656 M** for 75 requests: **22.9× the 06 estimate**. Average
  context per request is 88.8 k here vs ~19.4 k in 06; the maximum is 168.8 k.
  The two figures are not the same quantity (06 had no cache/usage field and
  counted visible characters only), so compare shares, not absolute tokens.
- A rough carry estimate at 3.6 chars/token, assuming a document stays in the
  prefix until compaction 1: the 43.5 KB `SKILL.md` is ~12.1 k tokens × 24
  requests ≈ **291 k**, or **4.4%** of traffic. The whole doc set (skill, craft,
  reference, rhythm, schemas, README, checklist) is ~34 k tokens × 24 ≈ **817 k**,
  or **12.3%**. That is an upper bound and is not itemized by the export; the
  exact figure is the 98.2% cache share.
- The remaining ~87% is the growing conversation: prior reasoning, tool results,
  score text, stats scripts, and the system/tool schemas — not a fixed manual.
  The 43.5 KB manual is a fixed context/attention cost, not the quota driver.
  Splitting it (candidate A) would save little money because 98.2% of its
  re-sends are cached; it might reduce attention dilution and the 168 k context
  pressure, but it is not the lever the 06 report thought it was.
- The 06 report's *qualitative* claim — “documentation is re-sent, not re-read” —
  is still true. Its *quantitative* 82.6% share described re-sent characters, not
  billed tokens. The right statement is: **traffic is documentation-shaped;
  cost is reasoning-shaped.**

### H4 — Did the 26-row absolute bar table return as a hand-typed dict?

**Verdict: confirmed.** Tool 22 (`msg_20d0bd15c001lCpQ2DL2WrpT8B`) runs:

```python
off={1:6,2:6,3:7,4:7,5:7,6:7,7:7,8:7,9:7,10:7,11:7,12:7,
     13:9,14:9,15:13,16:13,17:13,18:13,19:13,20:13,21:13,22:13,
     23:15,24:15,25:22,26:22}
for l in p['lines']:
    o=off[l['line']]
    l['bar_start']=l['body_bar_start']+o
    l['bar_end']=l['body_bar_end']+o
```

It is not the 26-row lyric table, but it is 26 hand-typed offsets followed by
26 additions. `phrases.json` ends with 26 rows and correct absolute bars
(7–9 … 79–80), but the arithmetic is still manual. The model worked the offset
mapping by hand in req 10 and req 12 before typing the dict. `syllabify.py`
emits only `body_bar_start/body_bar_end`; the absolute offset depends on the
section layout, which the tool does not know. This is a tool defect, not a
prompt defect.

---

## 7. Harness findings

These are not skill findings. They matter for how much of the run can be used.

1. **The skill tool is broken for this mount.** Tool 1 `skill({"id":
   "abc-score-writer"})` returns *“Unable to load skill abc-score-writer”*. The
   agent falls back to reading `skills/abc-score-writer/SKILL.md` directly
   (tool 2). The skill content is intact (hash matches), so the run still tests
   0.5.2; but the harness's skill loader did not see the attached directory. The
   failed call is negligible in cost (78 result chars).
2. **The working directory was not clean.** It contained `checklist.md`,
   `notes.md` (the analyst notes), `README.md`, `opencode_export.py`,
   `task.md`, `input/`, and `skills/`. The agent read the README (tool 9), the
   checklist (tool 10), and `head -40 notes.md` (tool 11). The checklist
   contains the stop rule (“no ABC by the 10th tool call”), the evaluation
   criteria, the blind-listen form and the decision tree; the head of the
   analyst notes includes the “do not paste this file into the agent” warning
   and the H1 heading (the full file also contains H2–H4). Req 8 says:
   *“notes.md is the analyst notes (not to be pasted).”* The agent preserved it
   as `notes.analyst.md` before overwriting (tool 61). This is a **setup
   contamination**, not a skill defect. Token/cost measurements are unaffected;
   process observations are contaminated and should be repeated clean before
   being treated as final. The agent did not visibly use H1–H4, and it still
   front-loaded and gate-chased, but the clean-room requirement was violated.
3. **One output-limit stop.** Req 14 (`finish: length`, 31,937 reasoning tokens,
   5 m 25 s) is cut by the output token limit. The synthetic message at
   10:13:00 tells the model to break the work into smaller pieces. This is a
   harness/model limit event, not a skill event. It explains why the “one
   block” is split into req 13 + 14.
4. **Two transport errors.** Req 45–46 (`finish: error`, `ECONNRESET`, retry
   attempts 2 and 3) log reasoning text but no token row. The run recovers at
   req 47. This is the residual in §5.1.
5. **Two auto-compactions, both effective.** Compaction 1 at 10:23:25 keeps from
   the `plan.json` write (`msg_20d0ba6cb001vOnceef1pjxTC8`, idx 17) and drops the
   skill reads, syllabify, and the 8-minute composition trace; context
   167,940 → 19,719. Compaction 2 at 10:49:28 keeps from the second checker run
   (`msg_20d22084e001DFNlGBlXItKPhx`, idx 59, the one with 2 hard fails) through
   the tuning loop and the final checker; it drops the score/seed build and the
   first checker parse fail; context 168,812 → 22,153. Both summaries preserve
   the 82-bar form, the plan values (including `strict_shape true`), the maqam
   block, the phrase mapping, and the work state. The agent also re-reads the
   files (`ls`, `score.abc`, `seed_sheet.md`, `report.json`) after the cuts. The
   sheet, plan and score state survived. The compactions cost 5,536 output
   tokens (14.1% of output) and 218,752 cache read.
6. **The checker's hard shape gate drove the composition.** `strict_shape: true`
   in the plan makes `max_top_duration_share`, register, chorus lift, silence,
   maqam fit and the phrase plan hard failures (SKILL.md §3.2). The model says
   so explicitly (req 58) and rewrites to clear them. This is the loop the 06
   report called S3, now visible and quantified: 5 checker runs (2 failing),
   2 full score writes, 43 requests, 98.8 k reasoning.

---

## 8. What this changes in the session-06 conclusion

| | Session 06 (Claude) | Session 07 (DeepSeek) |
|---|---:|---:|
| Skill | 0.5.2 | 0.5.2 |
| Requests / calls | 15 / 14 | **75 / 86** |
| Prompt traffic | 291 k (estimated) | **6.656 M (measured)** |
| Cache read | not in export | **6.537 M (98.2%)** |
| Skill share of traffic | 61.6% | ~4.4% carry (estimate) |
| Docs share of traffic | 82.6% | ~12.3% carry (estimate) |
| Output | ~5.6 k visible | **39.2 k** |
| Reasoning | 12.8 min, not priced | **202.2 k tokens, 83.8% of generated** |
| Cost | not in export | **$0.00** |
| Time to first ABC | call 11 (core), 12 (score) | call 23 (core), 24 (score); 12 m 13 s / 15 m 38 s |
| Score rewrites | 1 full rewrite | **2 full writes (1 rewrite), 5 edits** |
| Checker runs | 0 | **5** |
| Deliverables | sheet, plan, core, score | **all nine** |
| Seed / notes | no / no | **yes / yes** |

What survives from 06:

- **S2 (composition before files) is confirmed for the design, not as “one
  block.”** 8 m 00 s before the first file, and the sheet is a transcript; but the
  first block was cut by the output limit and the score was recomposed twice
  after files existed.
- **S3 (self-check then rewrite) is confirmed and larger.** The real checker,
  not a home-made proxy, now drives the rewrite. Five runs (two failing), two
  full score versions.
- **S4 (the table returns) is confirmed.** 26 hand-typed offsets.

What changes:

- **S1/§4.1 was a traffic claim, not a cost claim.** 98.2% of this run's traffic
  is cache; the 43.5 KB skill is not the dollar/quota driver. The measured
  traffic is 22.9× the 06 estimate and is not comparable to a cache-inclusive
  total. Its recommendation A (“split the skill”) is not supported as a
  token/cost lever.
- **Candidate C (checkpointed deliverables) is not supported by a failure in
  this run.** All deliverables existed; the problem is not a lost ending but a
  43-request gate-chasing loop. Checkpointing would ensure a seed earlier; it
  would not stop the score from being rewritten for a hard shape target.
- **Candidate B (absolute bars) is confirmed but small.** It is a mechanical
  correctness fix; it does not account for the 202 k reasoning tokens. Fix it
  later, not as this run's one change.
- **The new finding is H2.** The biggest avoidable loop is the hard shape gate.
  That is where the one change should go.

---

## 9. The one proposed next change

> **Superseded by §12.** The causal audit after this report changed the
> priority: the custom parser/measurement loop (57 k reasoning) is larger than
> the shape gate (40 k). The text below is the original recommendation; §12
> records the executed Stage 0 fixes and the revised one-change experiment.

**Set `strict_shape: false` in the plan template (§3.2) and
`example/plan.json`, so the declared shape targets stay warnings.**

This is one default in two copies (the §3.2 template and the example fixture),
not a checker rewrite and not a new gate. The plan keeps every target
(`max_top_duration_share`, `chorus_lift_min`, `register`, `tessitura`, `silence`,
`maqam_fit`, phrase plan); the checker still prints them as `WARN`; only their
class changes from `structure` to `style`. The contract and the nine corpus
sanity guards stay hard. The task's “leave the gate targets at the template
defaults” then yields a plan whose shape targets are diagnostic. The ear remains
the verdict.

One precision: the 68.6 register mean that failed checker #2 was a **sanity**
fail, not a `strict_shape` fail; the 74 ± 5 guard stays hard. The
`strict_shape` flag governs the declared shape targets, including the
`max_top_duration_share` 0.65 check that demanded converting 46 notes. So expect
the loop to shrink, not to reach zero rewrites; the remaining mean fix is a
small musical correction to stay inside the corpus, not gate-chasing.

**Why this one:**

- H2 is the clearest, most expensive finding: 43 requests, 49 tool calls,
  4.03 M cache read, 98.8 k reasoning, 26 minutes in phase 3; 5 checker runs;
  2 full score writes. The model's own words: *“I must meet it or … the checker
  fails hard”* (req 58), and the deliverable admits the mean was tuned to 69.1.
- It is not a taste gate and not a metric goal. It *removes* a hard metric gate
  from a diagnostic. The 0.5.2 skill already says “the checker proves the score
  is readable and inside the corpus; it cannot tell you whether the melody is
  worth hearing.” The shape targets are the brief, not the contract.
- It is a one-field experiment: same task, same model, same checker, same
  calibration, one default flipped. If the next score collapses, the ear will
  hear it; if it holds, the loop should shrink. Either result is informative.
- It is separable from B (absolute bars) and from the harness clean-room fix.
  Do not bundle them.

**Candidates considered and not chosen:**

| Candidate | Why not this run |
|---|---|
| A. Split the skill (a later 0.5.x) | H3: 98.2% cache; the skill is ~4.4% of traffic and not the cost driver. It is a context/attention cost, not the quota lever. |
| B. Emit absolute bars from `syllabify.py` | Confirmed (H4), but small: ~12 k chars of reasoning, not the 43-request loop. Fix later; it is a mechanical tool fix. |
| C. Checkpointed deliverables | No failure to fix: all nine artifacts existed. The loop is gate-driven, not budget-driven. |
| D. Shorter prompt / another sheet rewrite | The prompt already says “the ear is the verdict”; the hard checker overrode it. More prose is not the lever. |
| E. **`strict_shape: false`** | **Chosen.** Removes the hard shape gate that caused the rewrites, without touching the music or the corpus guards. |

**How to check it (not a metric goal):**

1. Next run: same task, same model, same 0.5.2 plus only this default; confirm
   `plan.json` has `"strict_shape": false` and the checker still lists the shape
   checks as `WARN`.
2. Count full score writes, checker runs and phase-3 reasoning; compare with
   2 writes / 5 runs / 98.8 k. This is a diagnostic, not a target.
3. The ear judges the score. If the result is worse, the next change is the
   seed/drums or the gate policy, not a threshold.

**Precondition, not the one change:** the next run must use a clean working
directory containing only `task.md`, `input/` and `skills/`. The 07 checklist,
analyst notes and README must not be inside the agent's cwd. Without that, the
process evidence remains contaminated.

---

## 10. Goal 1 — pending, not judged

Goal 1 is **pending**. The package contains no mp3/wav/ogg/flac; the agent's own
notes say “offline pass, no renderer or audio, so nothing was auditioned.” The
model changed from Claude to DeepSeek, so even a good or bad score here would
not be evidence about 0.5.2's ear. The score is structurally complete,
checker-passing, and the seed matches its vocal line; whether it is worth
hearing is for the blind listen, after a clean re-run and an audio render.

No listening verdict is claimed.

---

## 11. What was not changed

No skill, checker, calibration, schema, prompt or gate was modified for this
report. The frozen skill copy and the run artifacts are preserved under
`analysis/eval/runs/2026-11-24-deepseek-session-07/`.

---

## 12. Addendum — causal audit and Stage 0 repair (2026-11-24)

The causal audit after the report separates our errors from the agent's. The
primary causes were in the task/skill contract, not the model:

- the checker was described as a final step, so the agent wrote 19 parser/stats
  scripts (57,425 reasoning, 14,772 output) instead of using
  `report.json.measured`;
- `strict_shape: true` in the manual template (while `ostris plan` already used
  `false`) made shape targets hard, so the agent tuned 39,930 reasoning to
  numbers;
- `syllabify.py` emitted body bars only, so the agent hand-typed 26 offsets;
- the core draft was not defined as the opening of `score.abc`, so the agent
  designed the full piece before writing;
- "hum it" was impossible for a text-only, offline agent;
- the run directory contained the checklist and analyst notes, and the skill
  loader failed.

Stage 0 (executed, not the experiment) removed these contradictions:

| Fix | File |
|---|---|
| Checker is a measurement instrument; run after the first score, no custom parser, fix named bars, stop after pass | `02_maqam-score/SKILL.md` §3.5 |
| `strict_shape: false` default; shape targets warn; true only for a strict release | `SKILL.md` §3.2, `example/plan.json` |
| `syllabify.py --sections` writes absolute `bar_start`/`bar_end`; tests added | `scripts/syllabify.py`, `tests/test_syllabify.py` |
| Core is the first 8–16 bars of `score.abc`; write before planning the full form | `SKILL.md` §3.3/§7 |
| Exactly 10 numbered lines; no mental audition | `SKILL.md` §3.3/§5/§7 |
| 10× generated-token stop rule (manual analyst stop; no automatic monitor) | `SKILL.md` §7, session-08 checklist |
| Clean-room task package and checklist | `analysis/eval/inbox/deepseek_session_08/`, `analysis/eval/checklists/2026-11-24-session-08-economic.md` |
| Acceptance check uses `--strict-shape` for the phrase-failure fixture; W13 economic gate added | `analysis/verify_0_4_0.py`, `docs/agent-eval-protocol.md` |

Verification: `make test` (54 tests, OK), `make selftest` (PASS),
`make acceptance` (PASS after the phrase-failure check passes
`--strict-shape`), `make offline-check` (PASS). New package:
`dist/abc-score-writer.zip`, SHA-256
`14956cec853d7b6231ea58c79f29308d40cfce252f01dba47b19c8e1fbd0242b`
(source build 0.5.3; contract 0.4.0 unchanged).

The 10× budget is a **manual analyst stop rule**: the analyst watches the
session and ends it if generated tokens exceed 10× the score. The task tells the
agent to write early, but the enforcement is human judgment; there is no
automatic monitor. This is deliberately simple: the user can see when a session
is dragging and stop it.

**Revised one-change experiment (session 08):** checker-first measurement + no
custom parser + targeted edits + 10× generated-token budget. Success is quality
≥6/10 **and** generated / score ≤10×, with 0 custom scripts, 1 full score write
and ≤3 checker runs. Do not change the model in the same run; if the contract is
clean and the agent still writes a parser, that is an agent-capability finding.

---

## Appendix — artifacts and method

| File | What |
|---|---|
| `session-07/` | unpacked deliverables and the frozen skill copy |
| `parsed/summary.json` | per-message facts, totals, compactions |
| `parsed/tools.json` | all 86 tool calls: name, input, status, result size |
| `parsed/reasoning.md` | full reasoning trace in order (71 parts, 531 KB) |
| `parsed/reasoning_req{13,14,18,19,25,60,61}.md` | selected large blocks (the full trace is in `reasoning.md`) |
| `cost.csv` | all 75 assistant requests with tokens, finish, duration, context |
| `tools.csv` | all 86 tool calls with inputs and result sizes |
| `deliverable_audit.json` | independent bar/unit/note counts |
| `parse_log.py` | parser for the OpenCode JSON (not SQLite) |
| `audit_deliverables.py` | independent ABC bar counter (no checker import) |

**Method.** `OpenCode_Session_Log.json` is the native session export, not the
SQLite DB; it was parsed directly. Token totals come from `messages[].tokens`
and the two `compaction` messages; the header is `info.tokens`. Bar counts come
from an independent ABC parser (expanding `Z<n>` to `n` whole-bar rests), not
from `report.json`. Character/token carry estimates use 3.6 chars/token and are
labelled as estimates; the measured token table is exact. The checker's own
`report.json` is used only for the pass/warn status and the measured block, and
is identified as such.
