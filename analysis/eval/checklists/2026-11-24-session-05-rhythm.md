# Session 05 — rhythm-section test checklist

**Phase 1 of 2 (excellence).** This run tests whether the new rhythm layer makes
the drummer answer the voice. It does **not** test whether the skill is cheap.
Do not optimise tokens, do not add retrieval, do not add gates.

**Artifact under test:** `dist/abc-score-writer.zip`
**SHA-256:** `d224199ea32a772c755f69c55d1b827b224f0539580be12ff64d35b9fb76f9df`
**Build:** 0.5.1 rhythm section (contract version still 0.4.0)
**Date:** 2026-11-24
**Input package:** `analysis/eval/inbox/claude_session_05/`

**Hypothesis (one change):** a required `seed_sheet.md` with a phrase map and a
2-bar groove, plus a `V: Drums` voice in `seed.abc`, makes the drummer answer the
vocal phrasing instead of playing his own idea.

**Do not also change** the §3.3 numeric craft table in this run. Session 04's
`rhythm_variety` was exactly 0.85, the table's target, while the ear still heard
a grid. That is the next candidate change if this one fails, not a second change
now.

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
      the new score. Same key (D) and tempo (80) or the listen is not an A/B.

---

## 1. Freeze the run

- [ ] Zip hash matches `d224199e…76f9df`; if not, stop and record the real one.
- [ ] Harness + model recorded (Claude Code / Claude.ai / other, model id).
- [ ] Working directory and whether the skill is unpacked or mounted.
- [ ] Offline/online recorded. No renderer, no listening claim by the agent.
- [ ] The exact prompt saved verbatim (`task.md`); it was copied to `input/`.
- [ ] The agent received **D Kurd / 80 BPM**, not an open key/tempo choice.
- [ ] No retrieval: no `ostris exemplar`, no phrase bank, no corpus idiom call.

---

## 2. The task

Use `analysis/eval/inbox/claude_session_05/task.md` **verbatim**. Do not add
"make it strict", "0 warnings", "use the craft metrics", or a token limit. The
prompt already contains the one new requirement: `seed_sheet.md` and
`core_draft.abc` before the full score, and a `V: Drums` voice in `seed.abc`.

The lyrics and style are in `input/lyrics.txt` and `input/style.md`; the prompt
includes them inline as well.

---

## 3. Required process artifacts

- [ ] **`seed_sheet.md` before ABC.** One page: cell, period, cadence ladder,
      melisma, 2-bar riff, subtraction arc, lyric map, groove, three interaction
      events. If it is written after the score, it is not a plan.
- [ ] **Lyric map** has a **start beat** and a **bar count** per line, not only
      `bar_start`/`bar_end`. At least two starts and two lengths must appear.
- [ ] **Draft core (8–16 bars).** A real excerpt: the cell, the period, the
      groove. Not the first 8 bars of the final score pasted after the fact.
- [ ] **Four-line self-critique.** Must name a real weakness and say what it
      changed. "The cell is strong" is not a critique.
- [ ] **Named cell and transformations.** e.g. "cell A A C B; bars 3–4
      compressed, bars 9–10 start on the b6".
- [ ] **Named cadence plan.** Which phrase ends on 5, b6, b7, tonic.
- [ ] **Named melisma.** Which bar, which syllable (the rhyme), how many notes.
- [ ] **Named riff.** The 2-bar motif and where it returns; not "arpeggios".
- [ ] **Named subtraction.** What is removed before the chorus / solo / last
      line, including the drums.
- [ ] **2-bar groove per section** (verse, chorus, interlude/solo, last line).
- [ ] **Three interaction events** by bar and beat: unison, stop, fill, drop.
- [ ] **`seed.abc` uses the same melody.** If it is a second composition, fail.
- [ ] **`seed.abc` has a `V: Drums` voice.** A 2-bar groove, a fill at the end
      of a 4- or 8-bar group, and drums out for the last line.

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
    seed_sheet.md
    core_draft.abc
    rhythm.json        measure_rhythm output
  audio/
    no-seed.mp3
    v2-seed.mp3
    new-seed.mp3
```

- [ ] Transcript saved, including the sheet and the draft, not only the final.
- [ ] `seed.abc` saved separately from `score.abc`.
- [ ] Three covers, same lyrics/key/tempo/settings, labelled A/B/C.
- [ ] The A/B/C mapping written down but not looked at while rating.

---

## 5. Measure, don't trust

Run from the repo:

```bash
python3 02_maqam-score/scripts/checker.py output/score.abc \
  --plan output/plan.json --phrases output/phrases.json \
  --require-final-rest --strict-style --json output/recheck.json
python3 analysis/measure_craft.py output/score.abc
python3 analysis/measure_rhythm.py output/score.abc \
  --seed output/seed.abc --json output/rhythm.json
```

- [ ] Contract + strict style: __ FAIL, __ WARN. (Necessary, not sufficient.)
- [ ] `notes_per_syllable`, `rhythm_variety`, `peak_late_share`,
      `end_long_share`, `distinct_bar_share`, `repeat_share`,
      `distinct_end_degrees`.
- [ ] **Rhythm section:** `distinct_phrase_starts`, `distinct_phrase_lengths`,
      `line_gaps_16ths`, `weak16_share`, `sustain_beat3`,
      `drums.hits_in_vocal_rest`, `drums.fill_bars`, `drums.drop_bars`.
- [ ] `measure_rhythm.py` flags: all phrases start on beat 1? only two phrase
      lengths? line gaps only 1–2 beats? no 2-beat gap? no drum voice?
- [ ] Compare with session 04 (starts 1, lengths 3, weak16 0.071, sustain 4/436,
      no drum voice) and with the 177 corpus where comparable.
- [ ] Token estimate: chars of transcript ÷ 4; turns; tool calls; checker runs;
      score rewrites; wall clock.
- [ ] Did it run the checker more than once? That is tuning, not composing.

---

## 6. Blind listen

Three covers, same lyrics, key, tempo and settings:

| Label | What it is |
|---|---|
| **A** | no seed: the lyrics + style only |
| **B** | the old v2 seed (`maqam_kurd_seed_v2.abc`, D/80) |
| **C** | the new `seed.abc` (D/80, with drums) |

- [ ] Shuffle A/B/C; listen once through without skipping.
- [ ] Rate each 0–4 on: **hook**, **text setting**, **rhythm**, **maqam**,
      **form/arrangement**, **rhythm section (do the drums answer the voice?)**,
      **singability**, **seed usefulness**.
- [ ] Write one sentence per cover: what you remember after it ends.
- [ ] Unblind and record the mapping.
- [ ] If the new cover is not better than A and B, the iteration failed,
      regardless of the score's metrics.

**Hook test:** after one listen, hum the 2-bar cell. If you cannot, hook = 0–1.

**Drum test:** can you hear one moment where the drums enter a hole the voice
left? If not, rhythm section = 0–1.

---

## 7. Gaming audit

These are the tells from sessions 01–04. Mark each yes/no.

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
- [ ] **Rhythm grid.** Every phrase starts on beat 1, the same 3-bar frame, a
      1-beat gap at every line end. The session-04 tell.
- [ ] **Decorative drums.** A `V: Drums` voice exists but is a generic 4/4 loop
      under the voice, with no fill in a vocal hole and no drop. The new tell.
- [ ] **Template copy.** The example's Am/80 shape, the plan's 3 deviations, or
      the session-04 bar frame reappears.
- [ ] **Claim without check.** A named baḥr it did not scan; "the singer
      adapts"; "0 warnings" presented as quality; "every bar adds up" presented
      as validation.
- [ ] **Plan edited to fit the score.** Targets lowered after the fact instead
      of the music fixed.
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
| **Rhythm section (drums answer the voice)** | | | |
| Singability | | | |
| Seed usefulness (would you use it?) | | | |
| **Mean** | | | |

Decision:

- **Fail:** C ≤ A, or C mean < 2.5, or any dimension 0, or two gaming flags.
- **Usable:** C > A and C > B, C mean ≥ 2.5, no gaming flags.
- **Good:** C mean ≥ 3.0, hook ≥ 3, rhythm section ≥ 3, seed usefulness ≥ 3, no
  gaming flags.
- **Excellent:** C mean ≥ 3.5, hook ≥ 4, rhythm section ≥ 4, and you would
  release the cover.

The goal of session 05 is **Good on the same brief**. Excellent is the phase-1
endpoint; it may need more than one run.

---

## 9. What to change after the run

Do not change the skill during the session. After the post-mortem:

| If the failure is… | Change… |
|---|---|
| Ear says slop, metrics pass | Remove the numeric craft table from the agent-facing §3.3; keep the numbers in the analyst reference. |
| No hook, but the sheet looks right | The cell/period step is too abstract; add one worked 8-bar core and a "hum it" gate before expansion. |
| Hook good, arrangement weak | Guitar/riff and subtraction sections; add a riff-development example. |
| Text setting off | Elastic slots: add a worked 13/16/17-syllable line map. |
| Still no drum interaction, sheet good | The seed contract: what the renderer reads (drum voice? MIDI? section tags?), not more prose. |
| Drums answer in the verse, die in the chorus | The chorus groove: half-time vs four-on-the-floor; fewer fills. |
| The agent ignores the sheet | Make `seed_sheet.md` a hard deliverable in the task prompt and the run package. |
| Seed is worse than no seed | The seed contract is wrong (too much information, wrong register, wrong repetition). Fix the contract before the score. |

Rules:

- One change per run. If a failure repeats across two runs, change the skill;
  otherwise it is variance.
- Never add a hard gate for taste. The craft and rhythm metrics stay report-only.
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
