# Eval report — 2026-11-24 / Claude session 04

**Run id:** `2026-11-24-claude-session-04`
**Skill:** `abc-score-writer` 0.5.0 source (contract `0.4.0`), zip
`a71dd3c6f1e6bc0ba102ebe50ad60a61b99517a2b75f40a3b2ba1126a4687c63`
**Agent:** Claude (Claude.ai-style harness; model id not exported)
**Task:** the session-04 excellence brief: compose an ABC score from the
session-03 lyric and style as a seed for an AI cover. No key or tempo was given.
**Artifacts:** `score.abc`, `seed.abc`, `plan.json`, `phrases.json`,
`report.json`, `CHANGES.txt`; no audio, no seed sheet, no core draft.
**One-line verdict:** the gate passed again; the ear failed again on the rhythm
section. This run is a **process fail** under the session-04 checklist (no seed
sheet, no draft core, no four-line critique), and the recurring defect is now
measured: a 3-bar vocal grid with no drum part for the drummer to answer.

---

## 0. The verdict under test

The user's listening verdict, which is the aesthetic evidence for this run:

> Poor Rhythmic Phrasing / Poor Musical Interaction. The drums are not
> supporting the vocal phrasing. The drummer seems to be playing his own idea
> instead of interacting with the singer.

The agent itself agreed with the reviewer on the mechanism:

> the 3-bar phrases and the identical breath lengths leave a drum loop nothing
> to hang a fill on.

It then revised only the breath lengths. That is the finding: the revision
treated a rhythm-section problem as a rest-length problem.

---

## 1. Freeze the run

| Field | Value |
|---|---|
| Zip hash | **matches** `a71dd3c6…687c63` |
| Skill version | 0.5.0 source (craft build); contract still 0.4.0 |
| Delivery | not shown in the export; the first five tool blocks are consistent with reads of the skill and craft references |
| Harness / model | Claude.ai-style chat; model id unknown |
| Mode | **offline**; no renderer, no listening claim |
| Working directory | unknown (likely `/home/claude/w`) |
| Prompt | `task.md` (verbatim) |
| Turns / wall clock | 6 messages; 62 min 11 s wall, **13 min 05 s active** |
| Checker runs | 3 (initial, silence repair, breath revision) |
| Score versions | 2 (full score, scoped breath revision) |

**Export caveat (corrected).** `try_01` and `try_02` are different zip archives
but contain **byte-identical** `score.abc` and `seed.abc`; both are timestamped
07:41, after the last turn at 07:33. They are both **post-revision** snapshots,
not a before/after pair. The pre-revision file is not in the inbox, so the size
of the revision delta cannot be verified. The final file does contain the
claimed revision: 12 line ends use `z4` (short) and 14 use `z8` (long), and
`CHANGES.txt` carries `REVISION 1`. The final file is consistent with the
agent's claim that the revision changed **rests inside the same phrase frames**,
not the frames themselves; the pre-revision file is not available to confirm the
delta independently.

**Protocol deviation.** The session-04 checklist asked for the session-03 brief
**plus** “Use D Kurd (`K:Dm` with `_E`) and 80 BPM”. The prompt actually sent
had no key or tempo; the agent chose D and **88 BPM**. The A/B against the v2
seed (80 BPM) is therefore not controlled. The listen cannot be compared with
the previous take on equal terms.

---

## 2. Outcome, measured not trusted

I re-ran the pinned checker and both craft diagnostics on the final artifacts.

```bash
python3 02_maqam-score/scripts/checker.py score.abc --plan plan.json \
  --phrases phrases.json --require-final-rest --strict-style --json recheck.json
python3 analysis/measure_craft.py score.abc
python3 analysis/measure_rhythm.py score.abc --seed seed.abc
```

### 2.1 Gate

| Check | Result |
|---|---|
| Contract + strict style + strict shape + phrases + final rest | **PASS, 0 hard, 0 warnings** |
| Notes per syllable | 1.21 |
| Register mean / top / range | 71.3 / 84 / 57–84 |
| Tessitura ≥ C5 | 0.50 |
| Verse → chorus median | +9.0 semitones |
| Silence | 0.23 |
| Ins active | 0.25 |
| Distinct durations / top duration share | 6 / 0.56 |
| Longest unbroken singing | 7.5 s |
| Phrase violations | none |
| Maqam fit (Kurd) | 1.00; 0 chromatic notes per 100 |
| Final rest | yes |

The gate is **not** the problem. It passed the same way the rejected session-03
score passed.

### 2.2 Craft vs session 03 and the corpus

| Metric | S03 v1 | S03 v2 † | **S04** | Corpus P10 | Median |
|---|---:|---:|---:|---:|---:|
| notes / syllable | 1.11 | 1.04 | **1.21** | 1.17 | 1.28 |
| repeated-pitch share | 32.7% | 15.4% | **31.0%** | 28.7% | 32.9% |
| phrase-rhythm variety | 0.62 | 0.23 | **0.85** | 0.914 | 0.970 |
| peak-late share | 0.08 | 0.00 | **0.62** | 0.242 | 0.361 |
| end-long share | 1.00 | 1.00 | **0.42** | 0.061 | 0.241 |
| unique vocal bars | 0.98 | 0.31 | **0.97** | 0.769 | 0.862 |
| shape variety | — | — | **0.23** | 0.233 | 0.333 |
| distinct ending degrees | 5 | 3 | **6** | 6 | 7 |

† v2 is free ABC, not contract-checked; its numbers are indicative.

This is a **real improvement** on the three craft outliers that made session 03
mediocre: rhythm variety 0.62 → 0.85, peak-late 0.08 → 0.62, end-long
1.00 → 0.42. The cadence ladder is also in range: six endings, the 5th degree is
the most common (A, 7/26), the tonic D is 5/26 (19%), and the final note is D.
The melody is no longer the one-breath descending sigh of v1.

But rhythm variety 0.85 is still **below the corpus P10 (0.914)**, and shape
variety 0.23 sits at P10. The improvement is real and insufficient: the score
moved from “outside the corpus on three metrics” to “inside the corpus on paper,
outside it in the ear”.

### 2.3 The rhythm section — the new measurement

| Metric | S04 | What it means |
|---|---:|---|
| Phrases | 26 | one per lyric line |
| Phrases starting on beat 1 | **26 / 26** | no pickup, no cue for the drummer |
| Distinct phrase starts | **1** | every fill lands in the same place |
| Phrase lengths (16ths) | 40 × 13, 42 × 1, 44 × 12 | **25/26 in two lengths**; the 3-bar frame |
| Line-end gaps (16ths) | 4 × 12, 6 × 1, 8 × 8 | 1–2 beats; the breath is a metronome |
| Cadence positions (16ths) | 8 × 13, 10 × 1, 12 × 12 | every cadence on beat 3 or 4 |
| Quarter-beat onsets | 0.60 | 40% on eighth offbeats, **7% on weak 16ths** |
| Notes sustaining through beat 3 | **4 / 436** | no weight on the backbeat |
| Notes crossing the barline | 3 | only the written ties |
| Drum voice in `seed.abc` | **absent** | the drummer is left to the model |

This is the mechanical signature of the listener's verdict. A drummer has:

- no phrase start to answer (all 26 on beat 1);
- no varied phrase length to phrase across (two lengths);
- no internal 2-beat hole (the gaps are the line ends, 1–2 beats);
- no sustained note to place a backbeat against (4/436);
- no written part at all (no drum voice).

The only possible drum part is a generic 4/4 with a fill every three bars. That
is what “the drummer is playing his own idea” describes.

---

## 3. The recurring defect, across three runs

| Run | The same finding, measured | The fix applied then |
|---|---|---|
| 01 | 72% equal eighths; one breath per bayt; 34 s unbroken; one cadence | shape sanity guards, register/ending targets |
| 03 | phrase-rhythm variety 0.62; peak-late 0.08; end-long 1.00 | `craft.md`, cell/period, elastic slots |
| 04 | 26/26 phrases start on beat 1; 25/26 in two lengths; 4/436 sustain beat 3; no drum voice | **this report: the rhythm section** |

Each previous fix added a **measurement** or a **melodic** rule. None added the
part the listener names: the drums. The corpus is two-voice SheetSage2
transcripts; it has **no drum staff**. The gate therefore cannot see the layer
the ear hears first, and the agent had no instruction to write it.

---

## 4. Process audit — the checklist's required evidence

| Required artifact | Result | Evidence |
|---|---|---|
| Seed sheet **before** ABC | **FAIL** | no `seed_sheet.md`; the agent says “I've … drafted the whole score” |
| Draft core 8–16 bars | **FAIL** | no `core_draft.abc`; the full 92 bars were written first |
| Four-line self-critique | **FAIL** | absent |
| Named cell | PASS | `A A d c B` (repeated note, 4th leap, sigh) |
| Named transformations | PARTIAL | “varied per section”; no named operation with bars |
| Named cadence plan | PASS | six endings A/D/B♭/F/C/G; final D |
| Named melisma | **FAIL** | no bar, syllable or note count |
| Named riff | PARTIAL | guitar answers, swell and solo; no named 2-bar riff |
| Named subtraction | PASS | bar 75 silence; guitar leaves the outro; voice drops for the solo |
| `seed.abc` same melody | PASS | seed = score + chords + MIDI programs |
| Drums in the seed | **FAIL** | neither file has a drum voice |

**Verdict: process fail.** The checklist says jumping straight to bars is a
process fail; the missing sheet and core are the same failure. The score cannot
be treated as evidence that the method was used, because the method was not
used. The report's own “cell varied” is a description after the fact, not a plan
before it.

---

## 5. Gaming audit

| Tell | Yes/No | Evidence |
|---|---|---|
| Metric-shaped music | **partial** | rhythm variety 0.85 is below P10, so it was not bought; but 25/26 phrases share two lengths and all start on beat 1 — uniform in feel |
| Token melisma | no | 1.21 notes/syllable; cadence ornaments are real notes, not a last-syllable tag |
| Loop or through-composition | no at bar level; **yes at phrase level** | 0.97 unique bars, but the 3-bar frame repeats 26 times |
| Transposed verse | no | verse 2 stays in D; no key move |
| Cadence carpet | no | 6 endings, 5th most common, tonic 19% |
| Guitar as floor | partial | answers and a solo, not whole-bar arpeggios; no named 2-bar riff |
| Template copy | **partial** | the 3-bar phrase frame reappears; the section layout and deviations are new |
| Claim without check | no | offline honesty; no maqam claim; no “0 warnings = quality” |
| Plan edited to fit score | no | targets not lowered; 88 BPM declared as a cap decision |
| No sheet / no core | **yes** | the required process artifacts are absent |

The process fail is independent of the ear: the checklist requires the sheet and
the core, and neither exists.

---

## 6. Cost baseline (phase 2 input, not optimised)

The export hides tool payloads, so these are a lower bound plus an inferred
range. The visible transcript is 10,083 characters; the five skill files the
agent read total 100,965 characters.

| Metric | Value |
|---|---:|
| Visible transcript chars / tokens (÷4) | 10,083 / **2,521** |
| Hidden tool-result blocks | **20** |
| Files read (inferred) | 6 (SKILL.md, craft.md, reference.md, style-tags.md, numbers.md, lyrics) |
| Inferred input from those files | ~25,200 tokens |
| Estimated total tokens | **~30k (range 25–40k)** |
| Turns | 6 (3 human, 3 assistant) |
| Tool calls | ≥20 visible blocks; exact count hidden |
| Checker runs | **3** |
| Score versions | 2 |
| Wall clock | 62 min 11 s |
| Active agent time | **13 min 05 s** (48 min was the user's listening pause) |
| Output size | 5,828 bytes (`score.abc` 2,741 + `seed.abc` 3,087), ~1,460 tokens |

**Where the tokens went:** reading the five reference files (~25k), writing the
92-bar score (~4k output and context), the checker/report loop (~3k), and the
final prose. **Nothing went to a seed sheet or a core draft**, because neither
was written. The bottleneck at this stage is not the 100k-token blow-up the
brief worried about; it is that the full-length score was written before the
8–16 bar core, so the repair happened at the wrong scale. The phase-2 target is
therefore: keep the core, cut the five-file read and the full-score-first loop.

---

## 7. Blind listen

**Not run.** The inbox contains no `audio/` covers, so the A/B/C scorecard
cannot be filled. The only aesthetic evidence is the user's verdict in §0. I
will not invent ratings for A, B or C.

The checklist's decision rule therefore cannot be applied as written. The
process fail and the measured rhythm signature are enough to reject this run as
evidence of “Good”: the score may pass every gate, but it does not contain the
layer the listener judged.

---

## 8. Decision

| Criterion | Result |
|---|---|
| Gate | PASS (necessary, not sufficient) |
| Process artifacts | **FAIL** (no sheet, no core, no critique) |
| Craft vs session 03 | improved on all three former outliers; rhythm variety still below P10 |
| Cadence ladder | good (6 endings, 5th most common, tonic 19%) |
| Rhythm section | **FAIL**: one phrase start, two lengths, no drum voice |
| Blind A/B/C | **not run** (no audio) |
| “Good” on the session-04 bar | **not achieved** |

The honest summary: the skill fixed the **melodic** failure of session 03 and
left the **rhythmic** failure untouched. The user heard the part the method
never wrote.

---

## 9. Disposition — one change, the rhythm section

This is the change for run 04→05. It is a method and a deliverable, not a gate.
The checker, calibration, corpus thresholds and the nine sanity guards are
**unchanged**.

| File | Change |
|---|---|
| `02_maqam-score/references/rhythm.md` | **new**: three clocks; five phrase-rhythm rules; 2-bar groove per section; three interaction events; seed drum voice; three tests; 3-bar-grid anti-pattern |
| `02_maqam-score/SKILL.md` §3.3 | step 9 “Rhythm section”; phrase-start/length/drum-hole craft rows; `seed_sheet.md` required before ABC |
| `02_maqam-score/SKILL.md` §3.7 | `seed.abc` must carry `V: Drums` when the style has drums or the target is a cover; points to `example/groove.abc` |
| `02_maqam-score/SKILL.md` §3.4/§6/§7 | two-voice checked file; three-bar-grid, drums-left-to-model and fill-every-gap traps; rhythm sheet in the core draft |
| `02_maqam-score/references/craft.md` | §7.5 “The drummer is a partner”; §11.7 “The three-bar grid”; audition items 11–13 |
| `02_maqam-score/example/groove.abc` | **new**: a legal 8-bar `V: Drums` model (verse groove, fill, half-time chorus, drop) |
| `analysis/measure_rhythm.py` | **new**: report-only phrase starts/lengths/gaps, weak-16th share, sustain-through-beat-3, drum hits in vocal rests, fill/drop bars, and flags |
| `docs/agent-eval-protocol.md` | T31 (rhythm section), report-only |
| `02_maqam-score/CHANGELOG.md`, `README.md` | 0.5.1 entry and the session-04 pointer |

**Do not change:** the checker, `calibration.json`, the nine sanity guards, the
177 corpus numbers, the example `score.abc` (it is a syntax fixture; its
one-bar phrases are now explicitly labelled “not a rhythm model”), and the
`seed.abc` rule that the melody is the same as `score.abc`.

**One change, deliberately.** The session-04 `rhythm_variety` is **exactly
0.85**, the number in the §3.3 craft table, while the corpus P10 is 0.914. That
is the metric-shaped risk the checklist names. Removing the numeric craft rows
from §3.3 in the same run would confound the next result: we would not know
whether the drums improved because of the rhythm method or because the finish
line disappeared. Keep the table for session 05. **If** the next ear still says
“grid” while the craft numbers sit at target, the next change is the checklist's
first disposition row: remove the numeric craft rows from §3.3 and keep them in
the analyst reference (`craft.md` §12 / `numbers.md`), not add another metric.

**Next build:** `dist/abc-score-writer.zip`, sha256
`d224199ea32a772c755f69c55d1b827b224f0539580be12ff64d35b9fb76f9df`
(0.5.1 source; contract still 0.4.0). Public variant:
`dist/abc-score-writer-public.zip`, sha256
`8dd7b5212696cc4d5420c98e2e058198c40118190b55465c35e14a53124badaa`.
The session-04 hash above is the artifact that was under test and is kept for
provenance.

**Proof obligation for session 05:**

1. Use the checklist prompt **verbatim** (D Kurd, 80 BPM) so the A/B is
   controlled.
2. Deliver `seed_sheet.md` **before** `score.abc`, with the phrase map, groove
   and three interaction events.
3. `seed.abc` carries a `V: Drums` voice.
4. The score has ≥2 phrase starts, ≥2 phrase lengths, one pickup and one 2-beat
   hole per 4 bars.
5. Run `analysis/measure_rhythm.py` once at the end and report its flags.
6. Blind A/B/C covers on the same lyrics, key, tempo; the ear decides.

The change is a hypothesis. It is not proven until a cover built from the new
seed makes the drummer answer the voice. If the next ear still says “the
drummer is playing his own idea”, the failure is no longer the missing method;
it is the renderer's use of the seed, and the next change is the seed contract
(what the model actually reads), not another paragraph.

---

## 10. If the next run fails, change this — not the gate

| If the ear says… | Change… |
|---|---|
| still no interaction, but the sheet is good | the seed contract: what the renderer reads (drum voice? MIDI? section tags?), not more prose |
| interaction starts in the verse but dies in the chorus | the chorus groove: half-time vs four-on-the-floor; fewer fills |
| the drummer answers, but the voice is still square | the phrase map: pickups, 2-beat holes, cadence beats |
| the score is better but the cover is worse | the seed is over-specified; cut the drum voice to a 2-bar guide and keep the phrase map |
| the agent ignores the sheet again | make `seed_sheet.md` a hard deliverable in the task prompt and the run package, not advice |

**Never** fix this by adding a hard gate for groove, by lowering a corpus
threshold, or by editing the checker. The rhythm layer is report-only until the
ear says it works.
