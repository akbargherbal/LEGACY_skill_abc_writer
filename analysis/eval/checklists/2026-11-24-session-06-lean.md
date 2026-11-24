# Session 06 — lean process checklist

**Artifact:** `dist/abc-score-writer.zip`
**SHA-256:** `e7fca1418951e09f258bdad4f42b8a030bdc7b1c42def520dfac14f4d6b7d0f9`
**Build:** 0.5.2 lean sheet (contract 0.4.0)
**Date:** 2026-11-24
**Input package:** `analysis/eval/inbox/claude_session_06/`

**Hypothesis (one change):** a 10-line rules sheet and a score-first order make
the agent write the score, where the session-05 26-row table consumed the
session. The rhythm layer is unchanged and still untested in audio.

**Do not also change** the §3.3 numeric craft table, the checker, the
calibration, or the rhythm rules. Those are later runs.

---

## 0. Non-negotiables

- [ ] **The ear is the verdict.** The checker and craft metrics are diagnostics.
- [ ] **No gate-chasing.** Do not ask for "0 warnings" or a metric target.
- [ ] **No retrieval.** No exemplar, phrase bank or corpus idiom call.
- [ ] **No new code during the session.** Record gaps; do not patch the checker.
- [ ] **Log the cost, do not cap it.** Tokens, requests, calls, wall clock.
- [ ] **Same input for A/B/C:** D Kurd, 80 BPM, same lyrics and settings.

---

## 1. Freeze the run

- [ ] Zip hash matches `e7fca141…7d0f9`.
- [ ] Harness + model recorded; skill mounted or unpacked.
- [ ] Offline/online recorded; no renderer, no listening claim by the agent.
- [ ] Prompt saved verbatim (`task.md`); the agent received **D Kurd / 80 BPM**.
- [ ] The agent was not given a previous `score.abc`, `seed.abc` or sheet.

---

## 2. Process checks

The prompt orders the work. Check the order, not just the output.

- [ ] `lyrics.txt` used once; no retyped copy after an attachment.
- [ ] `syllabify.py --phrases phrases.json` run **once**; the line table is not
      retyped by hand.
- [ ] `seed_sheet.md` is **10 lines of rules**, not a 26-row table.
- [ ] `phrases.json` owns the bar ranges/syllables/pauses; the sheet does not
      duplicate them.
- [ ] `plan.json` exists and uses the skill template; defaults are acceptable.
- [ ] `core_draft.abc` exists and **predates** the full score; it is 8–16 bars,
      not the first 16 bars pasted after the fact.
- [ ] **No task list** was created.
- [ ] `score.abc` is two voices: `Vocal` + `Ins`, no third voice.
- [ ] `seed.abc` is the **same melody** plus chords and `V: Drums`.
- [ ] The drum voice has a 2-bar groove per section, a fill in a vocal hole, and
      a drop for the last line.
- [ ] The checker ran **once**, at the end.
- [ ] `notes.md` is 10 lines and was written **after** the score.

**Stop rule:** if there is no ABC by the 10th tool call, stop and record
"process still front-loaded"; do not let it run to another 20-minute sheet.

---

## 3. Save everything

```
analysis/eval/runs/<run-id>/
  task.md
  chat.md / chat.json
  output/
    score.abc
    seed.abc
    plan.json
    phrases.json
    seed_sheet.md
    core_draft.abc
    notes.md
    report.json          (checker --json)
    rhythm.json          (measure_rhythm)
  audio/
    A-no-seed.mp3
    B-v2-seed.mp3
    C-new-seed.mp3
```

- [ ] Transcript saved, including the sheet and the core.
- [ ] Three covers, same lyrics/key/tempo/settings, labelled A/B/C.
- [ ] Mapping written down but not looked at while rating.

---

## 4. Measure, don't trust

```bash
python3 02_maqam-score/scripts/checker.py output/score.abc \
  --plan output/plan.json --phrases output/phrases.json \
  --require-final-rest --strict-style --json output/report.json
python3 analysis/measure_craft.py output/score.abc
python3 analysis/measure_rhythm.py output/score.abc \
  --seed output/seed.abc --json output/rhythm.json
```

- [ ] Contract + strict style: __ FAIL, __ WARN. Necessary, not sufficient.
- [ ] Craft: `notes_per_syllable`, `rhythm_variety`, `peak_late_share`,
      `end_long_share`, `distinct_bar_share`, `repeat_share`,
      `distinct_end_degrees`.
- [ ] Rhythm: `distinct_phrase_starts`, `distinct_phrase_lengths`,
      `line_gaps_16ths`, `weak16_share`, `sustain_beat3`,
      `drums.share_in_vocal_rest`, `drums.fill_bars`, `drums.drop_bars`.
- [ ] Compare with session 05 (no score) and session 04 (starts 1, lengths 3,
      weak16 0.071, sustain 4/436, no drums).

---

## 5. Blind listen

| Label | What it is |
|---|---|
| **A** | no seed: lyrics + style only |
| **B** | old v2 seed (`maqam_kurd_seed_v2.abc`, D/80) |
| **C** | new `seed.abc` (D/80, with drums) |

Shuffle; listen once through; rate 0–4 on:

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

**Hook test:** if you cannot hum the cell after one listen, hook = 0–1.
**Drum test:** can you hear one moment where the drums enter a hole the voice
left? If not, rhythm section = 0–1.

Decision:

- **Fail:** C ≤ A, or C mean < 2.5, or any dimension 0, or two gaming flags.
- **Usable:** C > A and C > B, C mean ≥ 2.5, no gaming flags.
- **Good:** C mean ≥ 3.0, hook ≥ 3, rhythm section ≥ 3, seed usefulness ≥ 3.
- **Excellent:** C mean ≥ 3.5, hook ≥ 4, rhythm section ≥ 4, release-ready.

---

## 6. Gaming audit

- [ ] **Process theater.** A beautiful sheet/plan but no score, or a score
      written after the notes. The session-05 tell.
- [ ] **Task-list ceremony.** Calls spent on task creation instead of music.
- [ ] **Decorative drums.** A `V: Drums` voice that is a generic 4/4 loop, with
      no fill in a vocal hole and no drop.
- [ ] **Metric-shaped music.** Phrase rhythms differ on paper but every line
      feels the same.
- [ ] **Token melisma.** A 3–5 note tag at the last syllable to hit a band.
- [ ] **Loop or through-composition.** One 2-bar cell 10×, or 26 unrelated lines.
- [ ] **Cadence carpet.** Every phrase on the tonic or every phrase long.
- [ ] **Guitar as floor.** Whole-bar arpeggios, no 2-bar riff, no texture change.
- [ ] **Claim without check.** A named baḥr it did not scan; "0 warnings" as
      quality; "every bar adds up" as validation.
- [ ] **Plan edited to fit the score.** Targets lowered after the fact.

Any **two** = process fail, even if the ear likes the cover.

---

## 7. Cost log (fill in; do not cap)

| Metric | Session 05 | Session 06 |
|---|---:|---:|
| API requests | 14 | |
| Tool calls | 21 | |
| Visible input (lower bound) | 266,314 | |
| Visible output | 3,288 | |
| Thinking time | 19 m 42 s | |
| Time to first ABC | never | |
| Checker runs | 0 | |
| Score versions | 0 | |
| ABC chars | 0 | |
| Where the tokens went | sheet + task list + references | |

---

## 8. What to change after the run

| If the failure is… | Change… |
|---|---|
| No ABC again, sheet still large | The prompt/skill still front-loads; cut the sheet further or put a hard "ABC by call 5" stop. |
| ABC exists, but 14 requests again | The skill size: split 0.5.3. |
| Ear rejects the drums | The seed contract (what the renderer reads), not more prose. |
| Ear likes it, cost high | Split the skill; do not touch the music. |
| Score good but no hook | The cell/period step; add one worked 8-bar core. |
| Text setting off | Elastic slots; add a worked 13/16/17-syllable line map. |

Rules:

- One change per run. If a failure repeats across two runs, change the skill;
  otherwise it is variance.
- Never add a hard gate for taste. Craft and rhythm metrics stay report-only.
- Never fix a bad score by editing the checker or lowering a target.
