# rhythm — the drummer is the second listener

The checker measures note lengths; it cannot hear a groove. This file is the
layer between the voice and the drums. Read it after `craft.md` §7 and before
you encode the full score.

It is **design**, not a gate. The numbers in §12 of `craft.md` come from
two-voice transcripts; the 177 corpus contains no drum staff and cannot measure
interaction.

---

## 0. The failure this prevents

Session 04 (2026-11-24) passed `--strict-style` with 0 warnings and was heard
as a drummer playing his own idea. The score had:

- 26 phrases, **every one started on beat 1**;
- **every phrase the same length** (10 or 11 beats, a 3-bar frame);
- **every gap 1 or 2 beats** (4 or 8 sixteenths);
- 55% eighth notes, 4 of 436 notes sustaining through the bar's midpoint;
- **no drum voice** in `seed.abc` — the drummer was left entirely to the model.

A drummer cannot answer a grid. The melody is the drummer's score: its onsets,
rests, holds and cadence landings are the cues. If the voice is an unbroken
eighth-note stream in identical 3-bar blocks, the only possible drum part is a
generic one.

---

## 1. Three clocks

| Clock | Unit | What it decides |
|---|---|---|
| **lyric** | hemistich / bayt | where the breath is |
| **phrase** | 2–4 bars | where the fill goes |
| **groove** | 2 bars | what the drummer repeats |

If all three are the same length, there is no interaction. The 3-bar phrase is
not forbidden; 26 of them in a row is.

---

## 2. Phrase rhythm — five rules

1. **Vary the phrase length.** Use two or three of these per section: 2+2 bars,
   3+2, 2+3, 3+3, 4+4. A bayt does not have to be three bars per hemistich; a
   14-syllable line can be 2 bars and a 17-syllable line 3.
2. **Vary the start.** Not every phrase begins on beat 1. Write a pickup on the
   `&` of 4 (or 3) into the next phrase, or start a consequent on beat 2. At
   least one pickup per section.
3. **Vary the breath.** The caesura is shorter than the bayt end, and the
   section end is longer than both: roughly 0.5–0.75 s / 1.0–1.5 s / one bar.
   A one-beat gap at every line end is a metronome.
4. **Leave a hole inside the phrase.** Once per 4 bars, leave a **2-beat rest**
   where the voice stops and the drums fill. This is not the line-end breath;
   it is an internal hole. The singer breathes, the drummer speaks.
5. **Vary the cadence beat.** Land on beat 1, beat 3, and the `&` of 4 across a
   section. If every cadence lands on beat 3 or 4 of bar 3, the drummer knows
   exactly when to hit and stops listening.

One more: let a note **cross beat 3 or the barline** in each section. A stream
of eighth notes has no weight; a held note makes the backbeat audible.

---

## 3. Groove — a 2-bar cell, not a metronome

Write one 2-bar groove per section, derived from the vocal cell's rhythm:

| Section | Groove | What it leaves |
|---|---|---|
| verse | sparse: kick 1 and 3`&`, snare 2 and 4, hat eighths | the last beat of bar 2 for the voice or a fill |
| chorus | half-time (snare 3) or four-on-the-floor; crash on the downbeat | no fill every bar; the lift is the space |
| interlude / solo | the riff is the lead; drums support, then drop | one bar of drums alone before the return |
| last line | drums out | the voice and guitar close |

Rules:

- **A fill belongs at the end of a 4- or 8-bar group**, and only into a vocal
  rest. Do not fill every 2-bar loop.
- **The kick follows the vocal's stressed syllable**, not a fixed grid. If the
  voice lands on 1 and 3`&`, the kick can land with it; the snare answers.
- **The snare is the argument.** Put it where the voice is *not*, so the two
  parts converse. If the voice and snare always hit together, there is no
  counterpoint.
- **Silence is an arrangement.** A bar of drums alone, or a bar with no drums,
  is worth more than another crash.

---

## 4. Three interaction events per section

Name them in `seed_sheet.md` by bar and beat. Pick three, not all four:

| Event | What happens | Where it works |
|---|---|---|
| **unison** | voice and kick land on the same beat | the first line of a verse, the hook |
| **stop** | voice alone for one bar; drums out | before the chorus, before the last line |
| **fill** | voice rests 2 beats; drums fill | the end of a 4- or 8-bar group |
| **push** | voice enters on 4`&`; drums answer on 1 | between two phrases, into the chorus |

The chorus lift is not "drums louder". It is usually **half-time** (the snare
moves from 2/4 to 3) or **four-on-the-floor** with the voice free to float.

---

## 5. The seed drum voice

`score.abc` stays two voices — the contract. `seed.abc` is free ABC and may
carry a `V: Drums` voice. When the style block names drums, rhythm guitar or
metal, or the target is a cover model, **write it**. Leaving the drummer to the
model is how the session-04 cover got a generic beat.

```abc
V: Drums clef=perc name="Drums" snm="Drums"
%%MIDI channel 10
%%MIDI drummap B, 36
%%MIDI drummap C 38
%%MIDI drummap D 42
%%MIDI drummap E 49
K:C
% verse: kick 1/3&, snare 2/4, hat eighths; last beat open for the voice
B,2 D2 C2 D2 B,2 D2 C2 D2|B,2 D2 C2 D2 B,2 D2 z4|
% fill into the chorus: the voice's 2-beat hole
B,2 D2 C2 D2 B,2 D2 C2 D2|C2 C2 C2 C2 E4 z4|
% chorus: half-time, crash on the downbeat
E4 B,4 C4 B,4|B,4 C4 B,4 E4|
% last line: drums out
Z2|
```

The file `example/groove.abc` is this groove. Check bar sums like any voice.
Say in the report whether the renderer reads percussion; if it does not, the
phrase rules and the vocal rhythm still carry the interaction.

---

## 6. The three tests — before encoding

1. **Clap 2 and 4 and sing the phrase.** Does the line sit on the backbeat, or
   fight it? If it fights everywhere, you wrote a grid, not a phrase.
2. **Count the phrase starts.** If all are beat 1, rewrite two as pickups or
   start one on beat 2.
3. **Find the fill.** If you cannot point to a 2-beat hole once per 4 bars, the
   drummer has nowhere to answer. Add the hole before you add the drum part.

---

## 7. Anti-pattern

```abc
% bad: 26 x (3 bars, start on 1, end on 3/4, 1-beat gap, even eighths)
A2 A2 d4 c2 B2 A2 A2|c2 c2 _e4 d2 d2 c4|B4 B2 A2 B2 A2 z4|
% fixed: a varied start (beat 2), a 2-bar phrase, a 2-beat hole, a cadence on beat 4
z4 A2 A2 d4 c2 B2|A4 z8 G4|z8 A2 A2 d4|c4 B4 z4 D4|
```

Both are legal D Kurd, `L:1/16`, 4/4. The first is the session-04 frame. The
second leaves the drummer two places to speak: the 2-beat hole in bar 2 and the
varied starts in bars 1 and 3.
