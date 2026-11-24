# craft — how to make the score a tune

`SKILL.md` tells you what a valid score is. This file is about the part the
checker cannot see: whether the thing is a song.

Read this before you write a note. The gate comes after.

**The order is not negotiable.** A score written to satisfy numbers sounds like
numbers. Write the tune first — cell, period, cadence plan — then encode it,
then run the checker once.

---

## 0. What this file is, and what it is not

Every claim here has one of four bases, and is labelled:

| Tag | Meaning |
|---|---|
| **corpus** | measured on the 177 `five_stars` transcripts; reproducible with `analysis/measure_craft.py`; distributions, never gates |
| **theory** | Arabic music theory (maqam, sayr, ʿarūḍ, īqāʿ) from the sources in §12 |
| **expert / ear** | the 2026-11-23 expert brief, or a listening verdict from the user |
| **design** | a craft rule this skill chooses. It is not measured and does not pretend to be |

Nothing in this file is a hard gate. The nine sanity guards and the contract
are the gate. This file is the reason the gate is not the whole job.

---

## 1. The method in one page

1. **Read the lyric as a song, not a word list.** Find the bayt (two
   hemistichs), the caesura, the rhyme (qāfiya), the line that repeats, and the
   emotional pivot. The score has to breathe where the poem breathes.
2. **Write the cell.** 3–6 notes with a rhythm you can sing. One cell, not one
   per line. It must contain one of: a repeated note, a 4th/5th leap, or a
   distinctive rhythm. (design)
3. **Write the period.** 2 bars antecedent, ending open (5th, ♭6, 2nd); 2 bars
   consequent, ending closed (tonic or 3rd). Same head, different tail.
4. **Make it elastic.** The period is a matrix of anchor and fill slots, not a
   fixed list of 14 notes. It must absorb 13–17 syllables per line (§4).
5. **Plan the cadence ladder.** Which section closes where. The tonic is for the
   section end and the final qafla, not for every phrase (§5).
6. **Place the melisma.** 4–8 notes on chosen cadence syllables, not an average
   across the score (§6).
7. **Write the guitar as a part.** A 2-bar motif derived from the cell or a
   pedal; answers in the vocal's gaps; a texture change at the chorus; the solo
   develops the cell (§7).
8. **Write the rhythm section.** The phrase-start/length/cadence **rules** and a
   2-bar groove per section; `phrases.json` owns the per-line table. The drummer
   answers the voice, not the grid (`rhythm.md`).
9. **Build by subtraction.** The loudest moment is created by taking something
   away, not by adding a layer (§8).
10. **Critique the draft** against §10 before encoding the whole score. Then
    encode, then check once.

That is the whole method. The rest of this file is the detail and the failure
gallery.

---

## 2. The lyric is the clock

**theory.** A *bayt* is one line of classical Arabic verse, made of two
hemistichs (*ṣadr* and *ʿajuz*) separated by a caesura. The rhyme (*qāfiya*)
falls at the end of the second hemistich, and often at the end of the first. The
pause at the caesura is shorter than the pause at the bayt end. That hierarchy is
audible; do not flatten it.

`syllabify.py` gives you lines and syllables, not scansion. That is deliberate:
the tool does not claim to know the meter, and neither should you.

- **Do not name a baḥr unless you scanned the poem.** "Al-basīṭ" in a report
  means you counted the feet. If you used a long/short pattern as a guess, call
  it a heuristic.
- **Do not say "the singer adapts the text".** That is an excuse for a melody
  with the wrong number of slots. Write the slots (§4).
- **The rhyme is the landing.** Give the qāfiya the long note, or the melisma,
  or both. It is the one syllable the listener waits for.
- **The caesura is a breath, the bayt end is a rest.** At 80 BPM, a beat is
  0.75 s (`z4`); a caesura is about 0.5–0.75 s (`z4`), the bayt end 1.0–1.5 s
  (`z6`/`z8`). Do not give them the same gap.

**Design rule.** One lyric line is one phrase. If the line runs past
`max_unbroken_seconds`, split it at the caesura — never chain two lines into one
5-bar phrase.

---

## 3. The cell and the period

### 3.1 The cell

A cell is 3–6 notes. It has a rhythm as well as pitches. Write it as degrees and
durations before you write ABC:

```text
cell:  5  |  1  |  ♭7 | 1     rhythm: 2 4 2 4 (sixteenths)
       A     d     c    d
```

Bad cells are scales (`1 2 3 4 5`) and arpeggios (`1 3 5 8`). Good cells have a
quirk: a repeated note, a 4th/5th leap, a syncopation, or a neighbour that
returns. In the 177, **32.9% of melodic intervals are repeated pitches** (P10
28.7%, P90 37.8%): the corpus is full of insistence, not scales. A cell with no
repeated note and no leap is a fragment of a scale. (corpus)

### 3.2 The period

Two bars antecedent, two bars consequent, one bayt. The antecedent ends **open**
on a resting tone that is not the tonic (the 5th is the corpus favourite, 30.6%
of all phrase endings); the consequent ends **closed** on the tonic or the 3rd.

A legal 2+2 period in D Kurd, `L:1/16`:

```abc
% antecedent: leap up a 4th, fall through the b7, breathe, end open on A
A2 d4 c2 d4 z4|_e2 d2 c2 B2 A8|
% consequent: same head, compressed, close on D
A4 d2 c2 d8|_e2 d2 c2 B2 D8|
```

What this does:

- the 4th leap (`A→d`) is the one leap, at the head; the corpus leaps on only
  3.8% of intervals, so one gesture is enough (corpus);
- the `_e` (E♭, the Kurd ♭2) appears once, on the second bar's downbeat,
  falling to D — it is an event, not wallpaper;
- `z4` is an internal breath, not a bar-filling rest;
- the antecedent ends on A (5th, open), the consequent on D (tonic, closed);
- the head is compressed in the consequent (2-4-2-4 → 4-2-2-8), so the rhythm
  is not identical.

### 3.3 The transformation vocabulary

Use these on the cell. Pick two or three per section; do not use all of them.

| Operation | What changes | Example in D Kurd |
|---|---|---|
| **sequence** | the cell moves up/down a step | `A2 d4 c2 d4` → `B2 d4 c2 d4` (local, one phrase) |
| **inversion (free)** | the contour turns over; keep the maqam degrees | `A2 d4 c2 d4` → `A2 G4 A2 G4` |
| **truncation** | the tail is cut | `A2 d4 c2 d4 z4` → `A2 d4` |
| **augmentation** | the rhythm doubles | `A2 d4 c2 d4` → `A4 d8 c4 d8` |
| **ornament** | a turn is added at the cadence | `A8` → `A6 _e2 d2 c2 B2 A2` |
| **registral shift** | the same cell an octave away | `A2 d4` → `A,2 d4` (outro) |
| **fragmentation** | only the head returns | `A2 d4`, answered by the guitar |
| **rhythmic displacement** | the cell starts on beat 2 or 3 | `z4 A2 d4 c2 d4` |

**Do not transpose the whole verse.** A verse lifted a step is a key change, not
a variation; it also moves the maqam's tonic. If you want a lift, move the cell
into the upper jins (start on the ♭6 or the 4th) for one phrase and return.

---

## 4. Elastic text slots

The hard problem: one tune, lines of 13–17 syllables, no `w:` lines. A fixed
14-note melody cannot fit them. A tighter grid (v2) makes it worse: rhythm
variety fell to 0.23. The answer is a matrix of slots with deliberate fill
points.

**design.** Build a 2–3-bar hemistich from four kinds of slot. At 80 BPM, 14
syllables fit 2 bars; 16–17 fit 2.5–3. Do not squeeze them into 2.

| Slot | Count | Value | Absorbs |
|---|---:|---|---|
| **anchor** | 6–8 | 4–8 | one long syllable; the beat identity |
| **short** | 4–6 | 1–2 | one short syllable |
| **fill** | 2–4 | 1–2 notes | 1–2 syllables: repeat the pitch, or a 2-note neighbour |
| **cadence** | 1 | 4–12 | 1–6 syllables: the melisma or the held rhyme |

The default realization is the 14-syllable line. Then:

- **16–17 syllables:** use the fill slots as repeated pitches (one pitch, two
  syllables) and let the cadence absorb the last two.
- **13 syllables:** drop one fill to a rest or hold the anchor through it.
- **Never squeeze** by shrinking every note; that is how the grid returns.

Write the intended alignment in the report, e.g.:

```text
bar 5: 14 syllables / 14 slots, cadence melisma on the rhyme (5 notes)
bar 9: 17 syllables / 16 slots over 3 bars: one fill doubles, cadence holds 2
```

That is a claim you can defend without `w:` lines. Do not claim a syllable-to-note
match the checker cannot see.

---

## 5. The cadence ladder and sayr

### 5.1 The ladder

The corpus ending distribution, pooled over 177 takes and expressed as scale
degrees above the tonic (corpus):

| Degree | 5th | tonic | ♭6 | 2nd | ♭7 | 4th | ♭3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Share | 30.6% | 15.9% | 16.5% | 10.8% | 11.2% | 9.5% | 4.7% |

Read it as a hierarchy, not a quota:

- **5th** — the default open ending. Use it for the first hemistich and the
  pre-chorus.
- **tonic** — the section close and the final qafla. Do not use it in the middle
  of a verse; if half the phrases end on it (v2 did), the tune has no tension.
- **♭6 / ♭7** — the lament colours. Good for the verse's second half and the
  outro.
- **4th** — the suspended ending. For Kurd it is the ghammāz (G): touch it,
  do not sit on it.
- **2nd** — available in Nahawand/Ajam; not in Kurd, where the 2nd is the ♭2
  colour, not a cadence.
- **♭3** — rare (4.7%). v1 used it on 23% of phrases; that is why the cadences
  sound interchangeable.

For the four maqams in scope, the intermediate resting set stays as
`reference.md` §5.1: Kurd D/F/A/B♭/C; Nahawand D/F/A/C; Hijaz D/F♯/A/B♭; Ajam
D/F♯/A/B. The final phrase is the tonic.

### 5.2 Sayr — the course through the maqam

**theory.** A maqam is not a scale; it is a set of *ajnas* and an expected course
through them (*sayr*). Maqam Kurd is Jins Kurd on the tonic (D–E♭–F–G) followed
by Jins Nahawand on the 4th (G–A–B♭–C). The note where the second jins starts
is the *ghammāz* — for Kurd, **G**, the 4th. The upper octave is the *jawāb*.

**Design rule for a 16-bar section:**

1. open in the lower jins, around the tonic (D–F–G);
2. touch the ghammāz (G) once, on a strong beat, and leave it by step;
3. rise to the jawāb (D5) at the section's one peak;
4. return to the tonic through the ♭6 or ♭7 and close.

Do not wander: one section visits one or two ajnas, not all of them. The ♭2
(E♭) is the Kurd signature; use it once or twice per section, approached and
left by step, on a word that matters. If it appears in every bar it stops being
colour and becomes the key.

---

## 6. Melisma is an event

The brief says "melismatic, tarab". A single notes-per-syllable average cannot
express that. Split it:

| Layer | Target | What it means |
|---|---|---|
| body | 1.00–1.10 | one note per syllable; the text is clear |
| cadence | 3–8 notes on one syllable | the rhyme, the held note, the ornament |
| overall | 1.15–1.35 | the cadences carry the ratio |

**design.** A cadence melisma has a shape, not a random run:

1. the main note is held (the `A8` or `D8`);
2. a neighbour or turn enters by step (`_e2 d2 c2 B2`);
3. it returns to the main note or resolves to the tonic;
4. it is written as separate notes on **one** syllable, never as a tie.

Legal 16-unit cadence on D:

```abc
D6 _e2 d2 c2 B2 D2|
```

That is six written notes, one syllable. Do not sprinkle turns through the body
to raise the average; that produces the "too much melisma" complaint the eval
already recorded. Do not claim the score wrote quarter tones; it wrote the place
for the renderer to ornament (§10 of `reference.md`).

**Tarab is repetition with escalation, not more notes.** The strongest tarab
gesture is the same phrase returning louder, higher, or with the ornament added
the second time (*tarjīʿ*). Write the return; do not write a new phrase.

---

## 7. The guitar is a part, not a floor

The 177 corpus's Ins voice is a part: active in 25.3% of bars at the median, and
silent under the vocal almost always. The two failure modes are the whole-bar
arpeggio (`A,4 C4 E4 A4`) and the two-note tag at the barline.

**design rules:**

1. **A 2-bar riff motif.** Derive it from the vocal cell: the same rhythm on a
   pedal, or the cell's head in augmentation. Write it once and mutate it, the
   same way you mutate the vocal cell.
2. **Answer in the gaps.** The guitar speaks where the voice rests: the internal
   `z4`, the caesura, the bayt end. Never under a sung syllable.
3. **Own the frame.** Intro, interlude, solo, outro. The guitar states the cell
   before the voice does, and answers it after.
4. **Change texture at the chorus.** Verse: palm-muted pedal or sparse answer.
   Chorus: open chords, a counterline, or a low bed under the high voice. Do not
   play the same figure louder.
5. **The solo develops the cell.** It is not a chord-tone run. Take the cell,
   fragment it, sequence it, and end on the cadence note.
6. **The riff uses the maqam.** Root, ♭2, ♭3, 4, 5, ♭6 — the Kurd jins, not
   the natural minor scale. The ♭2 in the riff is the same "sigh" as in the
   voice.

A legal 2-bar pedal riff in D Kurd (Ins voice, under a vocal rest):

```abc
D,2 D,2 D,2 F,2 D,2 D,2 _E,2 D,2|D,2 D,2 D,2 F,2 G,2 F,2 _E,2 D,2|
```

That is 16 units per bar: eighth-note pedal with the cell's rhythm, and the ♭2
as the turn. It is a riff, not an arpeggio.

---

## 7.5 The drummer is a partner

The 177 corpus is two-voice: voice and Ins. It has **no drum staff**, so it
cannot teach this layer and no gate measures it. The listener still hears the
drums first. The melody is the drummer's score; write it so he can answer.

**design rules:**

1. **The phrase, not the bar, is the unit.** A drummer phrases in 2- and 4-bar
   groups. If every lyric line is 3 bars starting on beat 1, every fill lands in
   the same place and the part becomes a loop.
2. **Vary the start.** One pickup per section, on the `&` of 4 or 3. Start a
   consequent on beat 2. The pickup is where the drummer and the voice can
   agree without a crash.
3. **Leave a 2-beat hole once per 4 bars.** Not the line-end breath: an internal
   rest where the voice stops and the drums fill. The singer breathes; the
   drummer speaks.
4. **The snare is the argument.** Put it where the voice is not. If the voice
   and snare always hit together, there is no conversation.
5. **Chorus is a change of feel, not volume.** Half-time (snare on 3) or
   four-on-the-floor; crash on the downbeat; fewer fills, not more.
6. **Write the drums in the seed.** `seed.abc` gets a `V: Drums` voice: a 2-bar
   groove per section, a fill at the end of a 4- or 8-bar group, and a drop at
   the last line. `rhythm.md` §5 has the ABC dialect; `example/groove.abc` is a
   working 8-bar model.

The three tests: clap 2 and 4 and sing the phrase; count the phrase starts; tap
the fill. If all three fail, the drummer has no choice but to play his own idea.

---

## 8. Intensity by subtraction

The corpus's chorus lift is +2.4 semitones at the median (P90 +5.3), and the
chorus does **not** add notes (notes/bar delta +0.08). The loudest moment is made
by removing a layer, not adding one. (corpus)

**design.** A 16-bar arc:

| Bars | Voice | Guitar | Drums | What is removed |
|---|---|---|---|---|
| 1–2 | silent | states the cell | out; enter on bar 3 | nothing; the frame is empty |
| 3–6 | verse, low | answers in the gaps | 2-bar verse groove | the guitar drops under the voice |
| 7–8 | verse | pedal only | kick only, or out | the answers stop; the voice is exposed |
| 9–12 | chorus, lifted | open chords / counterline | half-time; crash on bar 9 | the palm mute and the pedal go |
| 13–14 | silent | solo develops the cell | return with a fill | the voice is removed for the peak |
| 15–16 | coda, low | the cell returns | out | everything but the cell |

The "drop" before the chorus is the oldest trick in the genre: remove the
guitar (and often the drums) for one bar, then enter. It costs one bar of Ins
and buys the whole section. Put the drum drop in `seed_sheet.md`, not in prose;
the seed's `V: Drums` voice is where it becomes audible.

In the two-voice dialect you cannot write dynamics. Encode intensity as density,
register, tessitura, silence and note length. In the seed variant (§9) you can
also write `!p!`/`!f!` and extra voices; the score's shape must already work
without them.

---

## 9. The seed variant

The contract score is for the LoRA renderer. A seed for a cover model (Suno)
needs chords, instruments and sometimes backing voices. One composition, two
renderings:

| File | What it is | Validation |
|---|---|---|
| `score.abc` | the strict two-voice dialect | `checker.py`, `--strict-style`, phrases |
| `seed.abc` | free ABC: chord symbols, `%%MIDI`, optional backing/strings voices, and a `Drums` voice when the style has drums | bar sums and voice alignment only; **not** the contract |

Rules:

- The melody is the **same** in both. Do not compose a second tune for the seed.
- `seed.abc` may add `"Dm"` chord symbols, `%%MIDI program`, and extra voices
  (backing, strings, and `Drums` when the style has drums). It may use
  `!p!`/`!f!`.
- Say in the report: "seed.abc is not contract-checked; the melodic content is
  score.abc, which passed."
- If the user only wants a seed, still write `score.abc` first. The strict file
  is the proof that the melody is complete; the seed is the orchestration.

---

## 10. The audition by reduction

You cannot hear the file. You can still test the tune. Do this on the 8–16 bar
core **before** you encode the full score.

1. **Hum the cell.** If you cannot repeat it after one hearing, it is not a
   hook. Rewrite it; do not add notes to it.
2. **Count the ideas.** The verse should have one cell and one rhythm. 26 lines
   with 26 melodies is through-composed; one bar eleven times is a loop.
3. **Find the peak.** Mark the highest note of each phrase. If every phrase
   peaks in its first two notes, you wrote 26 sighs. Let a third of the phrases
   build to a late peak. Target `peak_late ≥ 0.25` (corpus P10 0.242).
4. **Count the phrase rhythms.** Target `rhythm_variety ≥ 0.85` (corpus P10
   0.914). v1 was 0.62, v2 0.23.
5. **Check the cadence ladder.** At least four distinct endings; the most
   common should be the 5th, not the tonic; tonic ≤ 25% except the final qafla.
6. **Check the literal repetition.** Target `distinct_bar_share ≥ 0.75` (corpus
   P10 0.769). A repeated bar is a loop; a repeated cell is a hook.
7. **Check the repeated pitch.** 26–42% (corpus min/max). Below 25% is a scale;
   above 43% is a monotone.
8. **Check the endings' length.** Not every phrase ends on a long note; target
   `end_long ≤ 0.80` (corpus max 0.821). v1 was 1.00.
9. **Check the guitar.** Does it have a 2-bar motif? Is it silent under the
   voice? Does the chorus change its texture rather than its volume?
10. **Check the last phrase.** It should do something the first did not: drop an
    octave, lose the guitar, augment the cell, or hold the rhyme.
11. **Clap 2 and 4 and sing the phrase.** Does it sit on the backbeat or fight
    it? If it fights everywhere, the rhythm is a grid, not a phrase.
12. **Count the phrase starts and lengths.** If all start on beat 1 and all are
    the same 3-bar frame, rewrite two: a pickup, a 2-bar phrase, a cadence on a
    different beat.
13. **Find the fill.** Point to a 2-beat hole once per 4 bars. If there is none,
    the drummer has nowhere to answer; add the hole before the drum part.

Run `analysis/measure_craft.py score.abc` for 3–8 if you have the source repo
(and `analysis/measure_rhythm.py score.abc --seed seed.abc` for 11–13). It is a
mirror, not a gate.

---

## 11. The anti-pattern gallery

Each pair is legal ABC in D Kurd, `L:1/16`, 4/4.

### 11.1 The grid

```abc
% bad: eight eighths per bar, different pitches, no long note, no breath
A2 A2 c2 d2 _e2 d2 c2 B2|A2 G2 A2 G2 A2 B2 c4|
% fixed: long/short, an internal breath, a held open ending
A2 A4 c2 d6 z2|_e2 d2 c2 B2 A2-A6|
```

### 11.2 The loop

```abc
% bad: the same 2-bar cell, five times, one note changed at the end
A2 d4 c2 d4 z4|_e2 d2 c2 B2 A8|
A2 d4 c2 d4 z4|_e2 d2 c2 B2 A8|
A2 d4 c2 d4 z4|_e2 d2 c2 B2 A8|
% fixed: a period, then two variants (open, colour, closed)
A2 d4 c2 d4 z4|_e2 d2 c2 B2 A8|
A4 d2 c2 d8|_e2 d2 c2 B2 C8|
A2 d4 c2 d4 z4|_e2 d2 c2 B2 D8|
```

Bar 3 compresses the head; the second pair ends on the ♭7 (C). One cell, three
functions.

### 11.3 The transposed verse

```abc
% bad: verse 2 is verse 1 up a step; the tonic moved
A2 d4 c2 d4 z4|_e2 d2 c2 B2 A8|
B2 _e4 d2 _e4 z4|F2 _e2 d2 c2 B8|
% fixed: stay in D; move the cell into the upper jins for one phrase
B2 d4 c2 d4 z4|_e2 d2 c2 B2 G8|
```

The second version starts on the ♭6 and ends on the ghammāz (G); the next
phrase returns to the tonic. That is a colour change, not a key change.

### 11.4 The arpeggio guitar

```abc
% bad: a whole-bar chord arpeggio; no rhythm, no motif
A,4 C4 E4 A4|
% fixed: a pedal riff with the cell's rhythm and the b2 turn
D,2 D,2 D,2 F,2 D,2 D,2 _E,2 D,2|
```

### 11.5 The syllable squeeze

```abc
% bad: 16 syllables forced into 14 slots by shortening every note
A1 A1 c1 d1 _e1 d1 c1 B1 A1 G1 A1 G1 A1 G1 A1 B1|
% fixed: anchors + fills; two syllables share a pitch, the cadence absorbs the rest
A2 A2 c2 d2 _e2 d2 c2 B2|A2 A1 A1 G2 A2 G1 A1 A6|
```

The second bar is 16 units. The point is the repeated pitch (`A1 A1`), not the
exact count.

### 11.6 The everything-chorus

```abc
% bad: the chorus is the verse, louder and higher, with more notes
d2 d2 f2 g2 a2 a2 g2 f2|a2 a2 b2 a2 g2 f2 e2 d2|
% fixed: the chorus is one long note, a lift, and a silence
d6 a4 g4 z2|a2 a2 b2 a2 a6 z2|
```

### 11.7 The three-bar grid (drums left alone)

```abc
% bad: every line 3 bars, start on beat 1, end on 3/4, 1-beat gap, even eighths
A2 A2 d4 c2 B2 A2 A2|c2 c2 _e4 d2 d2 c4|B4 B2 A2 B2 A2 z4|
% fixed: a varied start (beat 2), a 2-bar phrase, a 2-beat hole, a cadence on beat 4
z4 A2 A2 d4 c2 B2|A4 z8 G4|z8 A2 A2 d4|c4 B4 z4 D4|
```

The first is the session-04 frame: it passes every gate and gives the drummer
nothing to answer. The second leaves two openings — the 2-beat hole in bar 2
and the varied starts in bars 1 and 3. Write the drum voice in `seed.abc`
(`rhythm.md` §5), not in the checked score.

---

## 12. What the 177 say

Report-only distributions from `analysis/measure_craft.py` over the 177
`five_stars` transcripts (2026-11-24). The full JSON is
`analysis/out/craft.json`; the registry entry is `references/numbers.md`.

| Metric | P10 | Median | P90 | Min–max |
|---|---:|---:|---:|---|
| phrase notes | 11 | 15 | 17 | 8–20 |
| phrases per track | 26 | 31 | 40 | 18–49 |
| stepwise share | 0.821 | 0.856 | 0.889 | 0.766–0.911 |
| repeated-pitch share | 0.287 | 0.329 | 0.378 | 0.257–0.423 |
| leap of a 4th+ | 0.023 | 0.038 | 0.053 | 0.008–0.080 |
| leap of a 5th+ | 0.005 | 0.013 | 0.026 | 0.000–0.040 |
| descending phrases | 0.390 | 0.512 | 0.621 | 0.226–0.773 |
| same start/end pitch | 0.028 | 0.083 | 0.171 | 0.000–0.280 |
| peak in second half | 0.242 | 0.361 | 0.484 | 0.108–0.680 |
| phrases ending long | 0.061 | 0.241 | 0.618 | 0.000–0.821 |
| phrase-rhythm variety | 0.914 | 0.970 | 1.000 | 0.818–1.000 |
| contour variety | 0.946 | 1.000 | 1.000 | 0.885–1.000 |
| shape variety | 0.233 | 0.333 | 0.424 | 0.143–0.650 |
| unique vocal bars | 0.769 | 0.862 | 0.945 | 0.667–1.000 |
| 4-note pitch recurrence | 0.293 | 0.403 | 0.478 | 0.212–0.577 |
| 4-note rhythm recurrence | 0.790 | 0.851 | 0.890 | 0.725–0.928 |
| distinct ending degrees | 6 | 7 | 7 | 4–8 |
| chorus − verse mean (semitones) | +0.3 | +2.4 | +5.3 | — |
| chorus − verse notes/bar | −0.39 | +0.08 | +0.65 | — |

Ending degrees, pooled: 5th 30.6%, tonic 15.9%, ♭6 16.5%, 2nd 10.8%, ♭7 11.2%,
4th 9.5%, ♭3 4.7%, others 1.7%.

These are **two-voice** measurements. The corpus has no drum staff and no
onset-interaction metric; `rhythm.md` covers that layer, and
`analysis/measure_rhythm.py` reports it. Do not read the `Ins` voice as drums:
in the corpus it is the melodic instrument, and in a real arrangement the drums
are the part no gate can see.

**These are not gates and not a target vector.** A score that hits every median
is an average take, not a good one. Use the bands to catch a draft that is
outside the corpus, and the method in §1–§8 to write something worth hearing.

**What this cannot see.** Contour beauty, the quality of the cell, the fit of a
word to a note, timbre, ornament, mix. Say so; do not claim the numbers heard
the tune.

---

## 13. Sources

- **Corpus:** the 177 `five_stars` SheetSage2 transcripts; measurements in
  `analysis/measure_craft.py` and `analysis/out/craft.json`. These describe what
  Suno rendered, not a human composition.
- **Maqam:** MaqamWorld, "Maqam Kurd" (Jins Kurd on the tonic + Jins Nahawand on
  the 4th); Farraj & Abu Shumays, *Inside Arabic Music* (Oxford, 2019); the
  *sayr* article (Wikipedia, citing Farraj & Abu Shumays).
- **ʿArūḍ:** the *basīṭ* pattern (mustafʿilun fāʿilun mustafʿilun fāʿilun) from
  the standard prosody references; the bayt/hemistich/qāfiya terminology.
- **Tarab:** Racy, *Making Music in the Arab World: The Culture and Artistry of
  Tarab* (Cambridge, 2003); *tarjīʿ* and the qafla as return-and-escalation.
- **Expert:** `analysis/eval/inbox/claude_session_02/expert_opinion.md` (F1–F7),
  labelled as one pair, not ground truth.
- **Ear:** the user's listening verdicts in the eval sessions. Taste is the
  listener's; this file only removes mechanical causes of a bad impression.
