# Eval report — 2026-11-23 / Claude session 01

This is the redacted, committed copy of the post-mortem. The raw transcript,
lyrics and artifacts stay in the gitignored run folder:
`analysis/eval/runs/2026-11-23-claude-session-01/`.


**Run id:** `2026-11-23-claude-session-01`
**Skill:** `abc_score_writer` v0.2.0 (contract `2026-11-23`)
**Agent:** Claude (Claude.ai-style harness; model id not exported — "unknown")
**Task:** ad-hoc, T01-shaped: compose a two-voice ABC score from vocalised
Arabic lyrics + an arabmaqamrock style block (Maqam Kurd), with key/tempo
omitted and no attachments.
**Artifacts:** `output/score_v1.abc`, `output/score_v1_fixed.abc`,
`output/score_v2_pre.abc`, `output/score_final.abc`, `plan_v1.json`,
`plan_final.json`, `report.json`, `CHANGES.txt`, plus the expert pair
(`mediocre.abc` = final, `excellent.abc`) and `expert_opinion.md`.

The raw export is `analysis/eval/inbox/claude_session_01/`; the verbatim
transcript is `chat.md` in this folder. Thinking text was hidden by the export
(empty blocks with one-line summaries), so the reconstruction uses the visible
messages, tool inputs and tool outputs only.

---

## 1. Freeze the run

| Field | Value |
|---|---|
| Skill source | plugin mount `/mnt/skills/plugins/abc-score-writer/` |
| Zip sha256 | **unknown** for the mounted copy. The repo `dist/abc_score_writer.zip` is `b797b4e76ade8f5c04219b50ba582367aeca772d27b90dd50df96c46ee79a34e`; its `SKILL.md` body is identical to the mounted file, but the mounted frontmatter name is `abc-score-writer` (hyphen) and the repo name is `abc_score_writer`. Treat the run as the same skill content, not the same packaging. |
| Skill version | 0.2.0 (`scripts/ostris/contract.py`) |
| Agent model | unknown (export has no model field) |
| Harness | Claude chat with `view`, `bash_tool`, `present_files`; Python 3; working dir `/home/claude/w` |
| Network | not stated; no network tool was used |
| Mode | offline (agent said so; no render, no listening) |
| Inputs visible | lyrics inline in the prompt; style block inline; **no attachment files** (`/mnt/user-data/uploads` empty) |
| Task prompt | `task.md` (turn 1), clarification (turn 2), revision request (turn 3) |

---

## 2. Outcome, measured not trusted

I re-ran my own copy of the pinned `checker.py` (repo v0.2.0, the same contract
the agent used) on every score version.

| Version | Bars | Hard gate | Style warnings | notes/syll | top duration | chromatic/100 |
|---|---:|---|---|---:|---:|---:|
| v1 draft (`K:Dphr`) | — | **FAIL contract** — `Unsupported key 'Dphr'; use a standard major or minor K: field` | — | — | — | — |
| v1 fixed (`K:Dm` + `_E`) | 78 | **FAIL sanity** — duration spread 89% (max 85%) | duration target 89%; silence 17% | 1.18 | 0.89 | 19.95 |
| v2 pre (less melisma, new melody) | 78 | PASS | melisma 1.06 (plan 1.10–1.20); silence 17% | 1.06 | 0.81 | 18.86 |
| v2 final (cadential turns added) | 78 | **PASS 0 hard, 1 warning** | silence 17% (floor 22%) | 1.12 | 0.72 | 18.86 |

The agent's final claim — "0 hard failures and 1 style warning" — is **true**.
The gate passed. The expert and the user both say the score is mediocre. That
gap is the finding.

### 2.1 Expert metrics, re-measured on all three versions

`analysis/measure_phrasing.py` implements the expert's definitions (phrase = a
contiguous sung run; unbroken = first onset to last note end; a breath is a gap
≥ 0.3 s). Numbers match the expert's brief on the final score.

| Metric | v1 fixed | v2 pre | v2 final | Corpus n=177 (min · median · max) | Expert "excellent" |
|---|---:|---:|---:|---|---:|
| phrases (any rest) | 10 | 11 | 11 | 18 · 32 · 49 (beat rule) | 41 |
| median phrase (s) | 14.59 | 14.59 | 14.59 | 2.08 · 3.61 · 5.79 | 4.09 |
| **longest unbroken (s)** | **34.05** | **34.05** | **34.05** | 5.49 · 10.42 · 22.89 | 8.86 |
| breaths / bar | 0.115 | 0.128 | 0.128 | 0.136 · 0.240 · 0.490 | 0.246 |
| **repeated-pitch share** | **0.017** | **0.032** | **0.061** | 0.252 · 0.324 · 0.426 | 0.272 |
| **distinct phrase endings** | **1** | **2** | **2** | 4 · 7 · 8 | 7 |
| phrase endings | D×13 | D×10, C×3 | D×10, C×3 | — | A,E,C,D,Bb,G,F |
| tessitura ≥ C5 | 0.791 | 0.820 | 0.821 | 0.495 · 0.712 · 0.910 | 0.676 |
| top duration share | 0.887 | 0.807 | 0.717 | 0.428 · 0.614 · 0.860 | 0.567 |
| eighths / quarters | 0.887 / 0.068 | 0.807 / 0.146 | 0.717 / 0.139 | 0.255–0.86 / 0.002–0.343 | 0.567 / 0.299 |

Three numbers are **outside the entire 177-track corpus**:

- longest unbroken singing **34.05 s** vs corpus max **22.89 s**;
- repeated-pitch share **6.1%** vs corpus min **25.2%**;
- distinct phrase endings **2** vs corpus min **4**.

Those are not taste judgements. They are the mechanical signature of "scale
walking with one breath per bayt, every phrase landing on D". The agent fixed
the checker's *duration-spread* letter three times (0.887 → 0.807 → 0.717) and
never touched the three numbers the listener hears. The skill gave it no
target for any of them.

### 2.2 Process score (protocol §4)

| Dimension | Score | Why |
|---|---:|---|
| Gate | 2 | Final 0 hard, 1 warning; failures on the way were correctly attributed |
| Inputs | 1 | Asked once for key/tempo, then proceeded after the user authorised a guess |
| Tooling | 2 | Bundled `syllabify`/`checker`; no parser, no install |
| Honesty | 2 | Offline, no audition, no maqam claim, measured facts only |
| Repair | **0** | Two repair cycles (duration split; melisma turns) plus a full rewrite |
| Reporting | 2 | Matches `report.json`; names the warning and the deviations |
| **Total** | **9/12** | **PARTIAL**, no honesty violation |

The process is a PARTIAL, not a clean PASS. The artifact is a gate PASS under
0.2.0 and a gate FAIL under the proposed 0.3.0 shape guards. Both statements
are true and they are the point.

---

## 3. What went right (do-not-change list)

1. **Clean refusal at the gate.** It stopped and named the missing items
   (attachments, tonic, tempo) instead of inventing them:
   > "I've stopped before writing because the skill's gate says to stop when an
   > input is missing rather than guess it."
2. **Used the bundled tools as documented.** `syllabify.py` once, `checker.py`
   five times, `reference.md` and `example/plan.json` read; it did **not**
   reimplement a parser/checker or install an ABC toolchain.
3. **Offline honesty.** It said "offline", "nothing has been rendered or
   listened to", called the baseline "an unmeasured prior", and made no
   audition claim. In the revision it said the final judgement is the user's ear.
4. **No maqam overclaim.** It used "D Kurd" as the requested mode, did not
   present a prior or an exemplar as a maqam judgement, and explained the
   `_E` spelling instead of hiding it.
5. **One clean recovery from the `K:Dphr` contract failure.** It read the error,
   switched to `K:Dm` with explicit flats, and re-ran. It did not edit the
   checker.
6. **Correct report mechanics.** `CHANGES.txt` is the deviation list plus the
   `MEASURED` block; `report.json` is the `--json` output; the final message
   quotes measured numbers and says which warning remains.
7. **No gate loosening.** On the silence warning it declared the warning and
   explained it; it did not lower `calibration.json` or edit `checker.py`.
8. **It recognised the user's aesthetic complaint.** It rewrote the hook with a
   fifth leap and a held top note, and it named the trade-off at 1.06
   notes/syllable. The *process* was responsive; the *plan* pulled it back.

---

## 4. Timeline and findings

### 4.1 Turn 1 — gate stop

- Read `SKILL.md` (full, 433 lines, 19,006 chars), then re-read lines 160–273
  (6,983 chars) because the first view appeared truncated in the UI. **W1**
  (same file, no change) plus a harness display limit.
- `ls` uploads, `grep` reference for Kurd/key/tempo.
- Stopped for attachments, tonic and tempo.

**Finding G1 — gate over-asks for tempo and tonic.**
Class `instruction_conflict`, severity **S2**.
`SKILL.md` §1 says "do not guess a key, a tempo or a maqam" (line 69), while
§3.1 documents a default tempo of 80 BPM with a warning (line 148) and the
corpus writes Dm for 72/177 tracks (the top key in every maqam subset). The
agent followed the stricter sentence and paid a turn. The tempo was not one of
the four gate items, yet the prose forbade guessing it. Evidence:
> "I've stopped ... Three things are missing: ... The key ... The tempo or
> render length."
Disposition: patch — state the defaults and when to declare instead of ask.

### 4.2 Turn 2 — the user authorises guessing

> "1 - take the pasted text as your input. 2 - make educational guess about the
> best option and follow with it. 3 - ... (70–80) would be fine."

The agent chose D Kurd, 74 BPM, 78 bars. The choice is defensible. It wrote
`K:Dphr` — the obvious musical spelling — and the checker rejected it.

**Finding G2 — no maqam/key encoding rule; `K:Dphr` is a guaranteed contract
failure.** Class `instruction_gap`, severity **S2** (latent **S1**: the
workaround corrupts the chromatic diagnostic).
Evidence:
> "The parser only accepts major or minor keys, so I'll write `K:Dm` and spell
> every E as `_E` or `_e`."
The skill never says the `K:` field is major/minor only, never gives a
maqam→key spelling, and never explains that the corpus's `K:Dm` files are
maqam-agnostic. The agent discovered it by failing a contract check. The
workaround then produced `chromatic_per_100 18.86` (100th percentile) because
every defining E♭ is "outside the key". A less careful agent would remove the
E♭ to satisfy the diatonic prior, destroying the maqam. This is the most
dangerous latent defect in the run.
Disposition: patch — maqam table + explicit `K:` rule + maqam-relative
chromatic measurement.

### 4.3 Turn 3 — composition and the duration-spread repair

The first score had 89% eighth notes. The sanity guard failed:

> "FAIL [sanity] duration spread  most common duration 89% of notes (sanity
> max 85%)"

The repair:

> "the first check failed the duration-spread guard, with 89% of vocal notes the
> same length. I split some eighth notes into sixteenth-note turns, which also
> adds the melismatic ornament your style block asks for. Nothing else changed."

**Finding G3 — the duration-spread failure has no prescribed musical fix, so
the agent split notes and added melisma.** Class `instruction_gap`, severity
**S2**. The skill says "on a sanity FAIL, fix only the bars named" — the
duration check names no bars. The only instruction nearby is "write the missing
music", and the agent's regex split turns into a global mutation. It raised
notes/syllable 1.18 → 1.27. The user's next message is a complaint about too
much melisma. The repair caused the complaint.

**Finding G4 — the canonical plan template uses the sanity ceiling as the
target.** Class `data_prior`, severity **S2**. `SKILL.md` §3.2 and
`example/plan.json` both show `"max_top_duration_share": 0.85`, which is the
*hard ceiling* (corpus max 0.86), not a style target (corpus median 0.614,
P75 0.691). The agent copied 0.85 and wrote 89%. Even after the repair, 72%
passed silently. The same pattern appears in `register.top 82` (corpus median
84), `ins_active_share_min 0.15` (corpus P25 0.20), and `ties_min 3` (corpus
median 1.07 per 10 bars; 78 bars → 8 ties at the median). A template should
show the target, not the last value before failing.

### 4.4 Turn 3 — the final report

The final score passed with one warning. The warning is the expert's F1 in
disguise:

> "One warning left in place: rests are 17% of the sung span against a 22%
> floor. The lyric is dense and the guitar only answers in vocal rests, so I
> left it."

**Finding G5 — the silence warning is explained away, not fixed.** Class
`instruction_gap`, severity **S1** (the expert's largest practical difference).
`silence_share` is 17% because the vocal sings five bars without a breath; the
"dense lyric" is not a reason — rests are added by allocating bars, not by
removing syllables. The skill has no phrase-length target, no breath rule, and
no statement that one lyric line is one phrase. The agent chained a bayt (two
hemistichs) into one 5-bar phrase: 34 s unbroken, 10–11 phrases over 78 bars.
Corpus max is 22.9 s; the expert's ceiling is 10 s.

### 4.5 Turn 4 — the user rejects the melody

> "أحس المليزما طالعة أكثر من اللزوم، هل تقدر تقللها، اللحن اللي سويته بعد عادي،
> ما أحس فيه شيء مبهر."
> ("The melisma feels like too much; can you reduce it? The melody you made is
> ordinary; I don't feel anything impressive.")

The agent rewrote the whole vocal line (not a scoped edit), got 1.06
notes/syllable, then **added notes back** to reach the plan floor of 1.10:

> "Add light cadential turns outside the choruses and recheck" → 1.12.

**Finding G6 — the plan's melisma floor overrides an explicit user request.**
Class `instruction_conflict`, severity **S1**. The user asked for *less*
ornament; the plan said `melisma_min 1.10`; the agent added turns to satisfy
the plan, then told the user "if you want less, I can go to 1.06, but then it
is closer to recitation." That is backwards: the user had already asked for
less. The skill says "1.0 is only for a deliberately syllabic line" but does
not say "a user request is a legitimate reason to set `melisma_min` to 1.00;
a style WARN is acceptable". It also conflates "melisma" (notes per syllable)
with ornament; repeated notes count toward the ratio, so a syllabic setting
with repeated notes can be at 1.0.

**Finding G7 — no revision protocol; a full rewrite and a second repair loop.**
Class `instruction_gap`, severity **S2**. The revision replaced all 78 bars,
then needed a repair to reach the plan floor. The skill's cost rule ("one
syllabify, one plan, one score, one check, at most one repair") applies to the
initial composition, not to feedback. There is no instruction to keep the
structure the user liked, change only the named channel, update the plan when
the brief changes, or cap the revision at one pass.

### 4.6 What the score never did

- No `w:` lines (correct: the renderer takes lyrics separately), so syllable
  alignment was not measured. The checker only checks the total 361.
- No listening claim, no render, no install, no web search. Honest.
- No maqam-fit claim. Honest.
- No `--strict-style`; style stays WARN. Correct per the skill.

---

## 5. Efficiency audit

### 5.1 Metrics (estimated: the export has no usage block)

| Metric | Value |
|---|---:|
| turns | 6 messages (3 user, 3 assistant) |
| tool calls | 14 (2 `view`, 10 `bash_tool`, 2 `present_files`) |
| distinct files read | `SKILL.md`, `reference.md`, `example/plan.json`, `example/score.abc` (4) |
| re-reads | `SKILL.md` twice (same content) → re-read ratio 1.25 |
| repeated commands | `checker.py` 5 runs; no identical command line repeated |
| score writes | 5 (v1, sed, split script, v2 rewrite, turn script) |
| checker runs | 5 (3 on v1, 2 on v2) |
| repairs | 2 (v1 duration split; v2 melisma turns) |
| tool-output volume | 57,499 chars ≈ 14.4k tokens |
| estimated tokens | ~20.9k (inputs 17.5k + outputs 57.5k + text 8.5k chars) / 4 |
| assistant wall clock | ~7m46s (turn 1 16s; turn 3 5m23s; turn 5 2m07s) |
| final answer length | ~1.66k chars (Arabic) |

### 5.2 Waste tags

| ID | Action | Evidence | Estimated tokens |
|---|---|---|---:|
| W1 | `SKILL.md` read twice with no change | first view 19,006 chars, second 6,983 chars | ~1.7k |
| W5 | two repair loops | duration split; melisma turns | ~2.5k |
| W6 | narration restating the checker | final message repeats the measured block in prose | ~0.4k |
| W7 | asked for inputs that the skill can derive | attachment/tempo/tonic stop | ~0.4k |
| — | full rewrite on a feedback turn | 78 bars replaced, not a scoped edit | ~1.6k |

No W3 (no corpus dump), no W11 (did not read the scripts), no W12 (did not
build a parser). The session is **correct but expensive in the two places that
matter**: a full rewrite where a scoped edit would do, and two repair loops
caused by thresholds the agent did not understand.

---

## 6. Failure classes

| # | Finding | Class | Severity | Smallest fix |
|---|---|---|---|---|
| G1 | Gate stops for tonic/tempo that the skill can default | `instruction_conflict` | S2 | State the defaults in §1; stop only for lyrics/style/maqam |
| G2 | `K:Dphr` rejected; maqam encoded as `K:Dm` + flats, chromatic misreads 18.86 | `instruction_gap` | S2 (latent S1) | Maqam table + `K:` rule + maqam-aware chromatic |
| G3 | Duration-spread FAIL repaired by splitting notes → more melisma | `instruction_gap` | S2 | Error→fix table for duration spread |
| G4 | Plan template uses sanity ceilings as targets (0.85, top 82, Ins 0.15) | `data_prior` | S2 | Template uses style targets (0.65, top 84, Ins 0.20) |
| G5 | 34 s unbroken, 17% silence warning left in place; no breath target | `instruction_gap` | **S1** | One line = one phrase; `max_unbroken_seconds`; sanity guard |
| G6 | Melisma floor (1.10) overrides "less melisma"; notes added back | `instruction_conflict` | **S1** | Allow 1.00 on request; style WARN is not a reason to add notes |
| G7 | Full rewrite + second repair; no revision protocol | `instruction_gap` | S2 | §3.6 revision: one channel, one pass, update plan |
| G8 | All phrases end on the tonic (D×10, 2 distinct) | `instruction_conflict` | **S1** | "Tonic at each phrase end" is the cause; change to resting tones + final tonic |
| G9 | The gate passes a score outside the corpus on 3 shape metrics | `data_prior` / gate design | **S1** | Add 3 calibrated sanity guards + plan targets |

`agent_capability`: none. The agent followed the skill's instructions; the
instructions were the defect. `task_prompt`: the prompt omitted key/tempo, but
the user explicitly allowed guesses in turn 2; not the root cause.
`harness`: the `view` display truncation caused one re-read; recorded, not
patched.

---

## 7. Root cause

The skill is a **validity gate**, not a **shape gate**. It measures bars,
register mean/top, duration spread, ties, sections, cadence and syllable count.
It does not measure:

- how long the voice sings without a breath;
- whether every phrase ends on the same pitch;
- whether the line repeats notes (the corpus repeats 25–43% of intervals; this
  score repeats 6%);
- whether the melody is a scale (stepwise share is not discriminating on this
  corpus — the expert's 58% vs 81% did not reproduce with a simple definition;
  repeated-note share did).

The one instruction that does address cadence points the wrong way:
`SKILL.md` §3.3, "**Cadence note.** The tonic at each phrase end". That is why
the score has 10 D endings and 2 distinct endings. The expert's F3 is not a
model habit; it is the skill's rule.

The second root cause is **template anchoring to ceilings**. The plan snippet
shows `0.85` (the sanity maximum), `top 82` (below the corpus median), and
`Ins 0.15` (below P25). A model copying the template writes a score at the edge
of the gate, then repairs toward the edge again. The example's own
`plan.json`/`score.abc` are inconsistent (plan `chords_min 0`, score has
`"Dm"`/`"Gm"` chords), which weakens the template further.

The third is **no revision semantics**. The user's "reduce melisma, make it
less ordinary" is a scoped edit plus a plan change. The skill has no rule for
it, so the agent rewrites everything and then fights its own plan.

**What this patch does not claim.** The user's "nothing impressive" is not a
gate. The new guards remove the three mechanical causes the expert identified;
they cannot make a melody inspired. The skill's own layer table says the
listener owns beauty, the LoRA owns timbre/arrangement, and the score owns
structure/prosody/gaps/register/repetition. The patch improves the third layer;
it does not turn the skill into a taste model.

---

## 8. Disposition

| Action | Target | Proof |
|---|---|---|
| `patch` | `SKILL.md` §1 (gate defaults), §3.2 (plan targets), §3.3 (cadence, breath, maqam), §3.5 (error→fix), new §3.6 (revision), §6 traps | new eval task T17 "one line, one breath" + T18 "less melisma" |
| `patch` | `references/reference.md` §4 (`K:` rule), new §5.1 maqam table, §7.5 phrasing distributions | numbers registry |
| `patch` | `scripts/checker.py` + `scripts/calibration.json`: 3 sanity guards (unbroken, repeated, endings), 3 style targets (unbroken, endings, maqam fit), maqam-relative chromatic, phrasing in MEASURED | regression tests in `tests/test_checker.py` |
| `patch` | `example/plan.json` + `example/score.abc`: style targets, no chords, new fields | `make selftest` |
| `patch` | `scripts/ostris/plan.py`/`priors.py`: generated plan must not require chords or a fill of 2 | `make offline-check` + a plan/check roundtrip |
| `test` | `tests/test_checker.py`: the mediocre score must fail the new guards; the example must pass | test fixture `tests/data/mediocre_2026-11-23.abc` (redacted, internal) |
| `docs` | `references/numbers.md`: register the new numbers, classes, n, pass rates | registry |
| `no action` | `w:` lines / syllable alignment | rejected: the renderer dialect has no `w:`; the total-count check stays. Alternative (per-line phrase plan) is P2. |
| `no action` | microtonal quarter tones | rejected: not in the dialect (`reference.md` §9). The prompt carries intonation. |
| `no action` | two-voice scope / sparse Ins line | not a defect: Ins notes/bar 1.17 is inside the corpus (P25 0.95, median 1.29); B's 193 notes are a full-mix transcription, not a lead sheet. |
| `no action` | stepwise-share gate | the expert's 81% vs 58% did not reproduce with a simple ≤2-semitone definition (both files 88.8%); do not gate a metric that does not separate. |
| `no action` | tessitura-share gate | A is 82.1% ≥ C5, inside the corpus (P95 84.5) and below the max 91%; a target would punish a legitimate high-register take. Report it; the plan's `register.mean/top` is the handle. |
| `no action` | rhythm-uniformity gate | A's 71.7% eighths is P90 but inside the corpus (P95 75.6); the plan target `max_top_duration_share 0.65` warns it without a new gate. |
| `no action` | chorus median ≥5 semitones | A is 5, B is 2 on our measure; corpus median 2, P95 7; a gate would fail ~half the corpus. Keep the existing top-note `chorus lift`. |

---

## 9. Confounders

- **One pair, one run.** The expert compared one mediocre to one excellent
  take. The corpus calibration is the guard against overfitting; the three new
  guards pass 177/177.
- **Different tempos.** A is 74 BPM, B 110 BPM. Seconds-based phrase metrics
  favour the faster take. The corpus distribution spans both; the new target
  is 10 s for a singer, not a bar count.
- **B is a transcription.** Its pitches and mode are not ground truth; only its
  phrasing/repetition/endings are used as evidence.
- **Skill packaging.** The mounted skill's frontmatter differs from the repo
  zip. Content is the same; the zip hash is unknown.
- **No usage block.** Tokens are estimated at chars/4; treat them as ±20%.
- **Lyrics quality.** The harakat are complete; 361 syllables is plausible.
  Not a defect.

---

## 10. Post-patch verification

The patch is `0.3.0` (see `skill-changes.md`). Re-running the shipped checker
on the same artifacts:

| Artifact | 0.2.0 gate | 0.3.0 gate |
|---|---|---|
| `score_final.abc` + `plan_final.json` | PASS 0 hard, 1 warning | **FAIL 3 hard** — unbroken 34.05 s (max 23), repeated 6.1% (min 20), endings 2 (min 3); 1 warning (silence 17%) |
| same + `plan.maqam = kurd` | — | FAIL same 3; `chromatic_per_100 0.0` (basis `maqam:kurd`), `maqam_fit 100%`; 3 warnings (unbroken target 10, endings target 3, silence) |
| `example/score.abc` + `example/plan.json` | PASS 0 hard, 1 warning | PASS 0 hard, 1 warning (silence 19%) |
| `make test` | 41 tests | **43 tests pass** (new shape and maqam tests) |
| `make selftest` | PASS | PASS |
| `make offline-check` | PASS | PASS |

The before/after is the proof the run was not only a report: the same score
that passed 0.2.0 now fails the three guards that describe what the listener
heard, while the bundled example still passes. The maqam block changes the
chromatic number from 18.86 (100th percentile) to 0.0 (maqam basis) without
changing a note.

## 11. Quick checklist

- [x] session ingested and normalised
- [x] zip sha recorded as unknown; repo zip hash recorded
- [x] task prompt captured verbatim
- [x] chat verbatim, errors included
- [x] output has v1, v2 pre, final, plan, report
- [x] re-ran every version through `checker.py`
- [x] turns, tool calls, re-reads, repeated commands, tokens counted
- [x] waste tagged W1/W5/W6/W7
- [x] what-went-right list written
- [x] every finding has class + severity + quoted evidence
- [x] no honesty violation
- [x] disposition chosen; regression tests named
- [x] core battery to be re-run after the patch
