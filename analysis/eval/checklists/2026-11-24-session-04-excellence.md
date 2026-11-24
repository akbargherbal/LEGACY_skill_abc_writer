# Session 04 — excellence test checklist

**Phase 1 of 2.** This session tests whether the agent can write an **excellent**
score. It does **not** test whether the skill is cheap. Do not optimise tokens,
do not add retrieval, do not add gates. Those are phase 2.

**Artifact under test:** `dist/abc-score-writer.zip`
**SHA-256:** `a71dd3c6f1e6bc0ba102ebe50ad60a61b99517a2b75f40a3b2ba1126a4687c63`
**Build:** post-0.4.0 craft build (contract version still 0.4.0)
**Date:** 2026-11-24

---

## 0. Non-negotiables

- [ ] **The ear is the verdict.** The checker and the craft metrics are
      diagnostics, not the goal. A score that passes everything and sounds like
      slop has failed.
- [ ] **No gate-chasing.** Do not tell the agent to hit a metric. Do not reward
      "0 warnings". Do not accept a score because the numbers are in range.
- [ ] **No YT500 retrieval in this run.** No `ostris exemplar`, no phrase bank,
      no "find me a cadence". We are testing composition, not retrieval.
- [ ] **No new code.** If something is missing, record it; do not patch the
      checker mid-session.
- [ ] **Log the cost, do not cap it.** Tokens, turns, tool calls, wall clock.
      Phase 2 needs the baseline.
- [ ] **One lyric, one style, three seeds.** Same input for the baseline, v2 and
      the new score. Otherwise the listen is not an A/B.

---

## 1. Freeze the run

- [ ] Zip hash matches `a71dd3c6…687c63`; if not, stop and record the real one.
- [ ] Harness + model recorded (Claude Code / Claude.ai / other, model id).
- [ ] Working directory and whether the skill is unpacked or mounted.
- [ ] Offline/online recorded. No renderer, no listening claim by the agent.
- [ ] The exact prompt saved verbatim in the run folder.

---

## 2. The task

Use the **session-03 brief verbatim**: same lyrics, same style block, same
missing key/tempo (the agent must choose and declare). Copy it from
`analysis/eval/inbox/claude_session_03/` or paste it.

**For a controlled A/B, add:** "Use D Kurd (`K:Dm` with `_E`) and 80 BPM, the
same assumptions as the previous take." The Suno covers must share key and
tempo or the listen is not comparable. If you also want to test the key/tempo
choice, run a second take, but keep the blind A/B on the D/80 set.

Prompt to give the agent:

```text
/abc-score-writer

Write an ABC score for these lyrics and style, as a seed for an AI cover.
The goal is a score that makes the cover better than a no-seed cover — not a
score that passes a checker.

Before writing any ABC, give me:
1. a one-page seed sheet: tempo/key/meter/bars, sections, one 3–6 note cell
   (degrees + rhythm), the 2+2 period (which phrase opens, which closes), the
   cadence ladder, where the melisma goes, the 2-bar guitar riff, the
   subtraction arc, and the lyric map (line -> bars -> syllables -> slots);
2. a draft 8–16 bar core (the hook + the period), with a four-line critique:
   can I hum the cell? how many ideas are in the verse? where is the peak?
   which bar is the weakest?

Then expand to the full score. Deliver score.abc, seed.abc (free ABC with
chords and any backing voices for the cover), plan.json, phrases.json, and a
short report that names the cell, the transformations, and the three moments a
listener should notice. Do not use the checker as the goal; run it once at the
end and report what it measured.
```

Do **not** add "make it strict", "0 warnings", "use the craft metrics", or a
token limit. We want to see what the method produces on its own.

---

## 3. Required process artifacts

These are process evidence, not optional prose.

- [ ] **Seed sheet before ABC.** If the agent jumps straight to bars, that is a
      process fail; note it and let it finish.
- [ ] **Draft core (8–16 bars).** A real excerpt: the cell, the period, one
      cadence. Not the first 8 bars of the final score pasted after the fact.
- [ ] **Four-line self-critique.** Must name a real weakness and say what it
      changed. "The cell is strong" is not a critique.
- [ ] **Named cell and transformations.** e.g. "cell A A C B; bars 3–4
      compressed, bars 9–10 start on the b6".
- [ ] **Named cadence plan.** Which phrase ends on 5, b6, b7, tonic.
- [ ] **Named melisma.** Which bar, which syllable (the rhyme), how many notes.
- [ ] **Named riff.** The 2-bar motif and where it returns; not "arpeggios".
- [ ] **Named subtraction.** What is removed before the chorus / solo / last line.
- [ ] **`seed.abc` uses the same melody.** If it is a second composition, fail.

---

## 4. Save everything

```
analysis/eval/runs/<run-id>/
  task.md              exact prompt
  chat.md              verbatim export
  output/
    score.abc
    seed.abc
    plan.json
    phrases.json
    report.json
    CHANGES.txt
    seed_sheet.md      (or wherever the sheet is in the transcript)
    core_draft.abc     (if written as a file)
  audio/
    no-seed.mp3
    v2-seed.mp3
    new-seed.mp3
```

- [ ] Transcript saved, including the sheet and the draft, not only the final.
- [ ] `seed.abc` saved separately from `score.abc`.
- [ ] Three Suno covers, same settings, same lyrics, labelled A/B/C.
- [ ] The A/B/C mapping written down but not looked at while rating.

---

## 5. Measure, don't trust

Run from the repo:

```bash
python3 02_maqam-score/scripts/checker.py output/score.abc \
  --plan output/plan.json --phrases output/phrases.json \
  --require-final-rest --strict-style --json output/recheck.json
python3 analysis/measure_craft.py output/score.abc
```

(The v2 file is free ABC, so `measure_craft.py` cannot parse it; use the
session-03 post-mortem numbers for the v2 comparison.)

- [ ] Contract + strict style: __ FAIL, __ WARN. (Necessary, not sufficient.)
- [ ] `notes_per_syllable`, `rhythm_variety`, `peak_late_share`,
      `end_long_share`, `distinct_bar_share`, `repeat_share`,
      `distinct_end_degrees`.
- [ ] Compare with the 177 P10/median/P90 and with v1/v2.
- [ ] Token estimate: chars of transcript ÷ 4; turns; tool calls; checker runs;
      score rewrites; wall clock.
- [ ] Did it run the checker more than once? That is tuning, not composing.

---

## 6. Blind listen

Three covers, same lyrics and settings:

| Label | What it is |
|---|---|
| **A** | no seed: the lyrics + style only |
| **B** | the old v2 seed (`maqam_kurd_seed_v2.abc`) |
| **C** | the new `seed.abc` |

- [ ] Shuffle A/B/C; listen once through without skipping.
- [ ] Rate each 0–4 on: **hook**, **text setting**, **rhythm**, **maqam**,
      **form/arrangement**, **singability**, **seed usefulness**.
- [ ] Write one sentence per cover: what you remember after it ends.
- [ ] Unblind and record the mapping.
- [ ] If the new cover is not better than A and B, the iteration failed,
      regardless of the score's metrics.

**Hook test:** after one listen, hum the 2-bar cell. If you cannot, hook = 0–1.

---

## 7. Gaming audit

These are the tells from sessions 01–03. Mark each yes/no.

- [ ] **Metric-shaped music.** Phrase rhythms differ on paper but every line
      feels the same; `rhythm_variety` is bought with tiny duration changes.
- [ ] **Token melisma.** One 3–5 note tag at the last syllable to satisfy the
      notes/syllable band, while the body is fully syllabic.
- [ ] **Loop or through-composition.** One 2-bar cell repeated 10×, or 26
      unrelated lines. Neither is a tune.
- [ ] **Transposed verse.** Verse 2 is verse 1 up a step; the tonic moved.
- [ ] **Cadence carpet.** Every phrase ends on the tonic, or every phrase ends
      on a long note, to satisfy the ending/length checks.
- [ ] **Guitar as floor.** Whole-bar arpeggios, chord pads, two-note tags; no
      2-bar riff, no texture change.
- [ ] **Template copy.** The example's Am/80 shape, the plan's 3 deviations, or
      the session-03 bar frame reappears.
- [ ] **Claim without check.** A named baḥr it did not scan; "the singer adapts";
      "0 warnings" presented as quality; "every bar adds up" presented as
      validation.
- [ ] **Plan edited to fit the score.** Targets lowered after the fact instead of
      the music fixed.
- [ ] **No sheet / no core.** The process artifacts were produced after the
      score, not before.

Any **two** of these = process fail, even if the ear likes the cover.

---

## 8. Scorecard and success bar

Per cover (0–4):

| Dimension | A no seed | B v2 | C new |
|---|---:|---:|---:|
| Hook (can you hum it?) | | | |
| Text setting (long syllables, rhyme, caesura) | | | |
| Rhythm (not a grid; breathes) | | | |
| Maqam (Kurd, b2 as event) | | | |
| Form/arrangement (riff, chorus payoff, arc) | | | |
| Singability | | | |
| Seed usefulness (would you use it?) | | | |
| **Mean** | | | |

Decision:

- **Fail:** C ≤ A, or C mean < 2.5, or any dimension 0, or two gaming flags.
- **Usable:** C > A and C > B, C mean ≥ 2.5, no gaming flags.
- **Good:** C mean ≥ 3.0, hook ≥ 3, seed usefulness ≥ 3, no gaming flags.
- **Excellent:** C mean ≥ 3.5, hook ≥ 4, and you would release the cover.

The goal of session 04 is **Good on the same brief**. Excellent is the phase-1
endpoint; it may need more than one run.

---

## 9. What to change after the run

Do not change the skill during the session. After the post-mortem:

| If the failure is… | Change… |
|---|---|
| Ear says slop, metrics pass | Remove the numeric craft table from the agent-facing §3.3; keep the numbers in the analyst reference. The model is writing to the numbers. |
| No hook, but the sheet looks right | The cell/period step is too abstract; add one worked 8-bar core and a "hum it" gate before expansion. |
| Hook good, arrangement weak | Guitar/riff and subtraction sections; add a riff-development example. |
| Text setting off | Elastic slots: add a worked 13/16/17-syllable line map. |
| The agent ignores the method | The seed sheet must be a required deliverable, not advice; make it a file the run is judged on. |
| Seed is worse than no seed | The seed contract is wrong (too much information, wrong register, wrong repetition). Fix the contract before the score. |

Rules:

- One change per run. If a failure repeats across two runs, change the skill;
  otherwise it is variance.
- Never add a hard gate for taste. The craft metrics stay report-only.
- Never fix a bad score by editing the checker or lowering a target.
- Log every change against the run id.

---

## 10. Phase-2 log (fill in, do not optimise yet)

| Metric | Value |
|---|---|
| total transcript tokens (chars ÷ 4) | |
| turns | |
| tool calls | |
| checker runs | |
| score rewrites | |
| wall clock | |
| output size (score.abc + seed.abc) | |
| where the tokens went (sheet, draft, expansion, repair, report) | |

This is the baseline for "excellent, then cheap". Do not compress before the
ear says the music is good.
