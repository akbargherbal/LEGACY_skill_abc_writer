# Critic — the core review before expansion

This is the taste layer. It is **not** a gate and it does not write a score.
It reviews the 8–16 bar `core_draft.abc` before the full form exists.

The composer runs this review after the core and before `plan.json`/`score.abc`.
The output is `core_review.md`: exactly **5 numbered lines**, each one issue or
"no change", tied to a bar.

## The eight points

1. **Rhythm is not a grid.** Does every line start with the same cell? Count the
   first three durations of each line. If more than 40% share one cell, rewrite
   the starts. The dominant duration must not exceed 60%; at least three
   duration values must carry real weight; some starts and ends should be off
   the beat.
2. **Anacrusis.** Do some lines enter after a rest, on the last beat of the
   previous bar? A pickup after a breath is the poet's breath, not a late note.
3. **Rest hierarchy.** The caesura is short (about 0.5–0.75 s); the bayt end is
   longer (1.0–1.5 s); the section end is longer still. If every gap is the same,
   the poem has no commas.
4. **Melisma is an event.** The body is syllabic (about 1.0–1.1 notes per
   syllable); one chosen cadence syllable carries a 3–8 note turn or a held
   rhyme. Not an average across the score.
5. **Voice and instrument converse.** The instrument answers in the vocal's
   rests, not only in the intro/interlude. At least one answer is a mutation of
   the vocal cell, not a generic scale.
6. **The intro has a texture.** An ostinato/arpeggio derived from the cell, not
   a single melodic line that stops when the voice enters.
7. **The verse–chorus arc is audible.** The verse starts lower (D4–F4 in D
   Kurd) and climbs; the chorus is a new motif or a transposed answer, not the
   verse head with a louder arrangement.
8. **The line moves.** There are deliberate 4th/5th leaps followed by a
   contrary step, and some repeated pitches used as insistence, not a scale.
   End verses on D via E♭ where the maqam allows it.

## The output

```text
1. Bar 3: the line starts with the same 4-3-1 cell as bars 1 and 2. Start on the & of 4 with a pickup.
2. Bar 6: 0.19 s gap after the line; the caesura needs ~0.5–0.75 s. Add z2.
3. Bar 9: 14.25 s unbroken; split at the caesura after «بيدٍ».
4. Bar 12: no melisma on the rhyme. Hold the last syllable or write E♭–D–C–D.
5. Bar 15: the chorus is the verse head transposed. Give it a new f–a–b opening.
```

Rules:
- exactly 5 lines, numbered `1.`–`5.`;
- one bar reference per line where possible;
- no aggregate numbers, no new score, no gate;
- the composer edits the core and records what changed in `core_review.md`
  (append a short "fixed" note only if needed; the 5 numbered lines stay).
