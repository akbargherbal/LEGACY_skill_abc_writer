# reference — numbers and the dialect

Every number is one of three things:

- **derived** — re-run the formula;
- **corpus-measured** — a distribution over the 177 `five_stars` ABC scores
  (2026-11-23), with its `n` and percentiles;
- **a design rule** — a renderer or craft requirement, labelled as such.

A number measured on one case is not a rule. The five `p01`–`p05` takes below
are a case study from an older pipeline; the 177-track corpus is the shape
reference.

The full provenance registry — every number, its class, sample size, pass rate,
and where it is used — is **`references/numbers.md`**. The machine-readable copy
is `scripts/calibration.json`.

## 1. Duration cap (derived)

Source: `arabmaqamrock/duration_cap.py`.

```text
N        = Arabic letters (Unicode Lo, U+0600–U+06FF); harakat are Mn, not counted
duration = 111.1 + 0.3126 × N        q = 0.95   (94.8% coverage)
duration = 122.9 + 0.3081 × N        q = 0.975
duration = 105.1 + 0.3059 × N        q = 0.90
round to the nearest 10 s, then tokens = duration × 25
```

This is an **upper bound**, not a target. The Imru' al-Qais set: N = 608 →
301.2 s → 300 s → 7500 tokens. The render that shipped was 262.15 s.

Do not use the old centre fit `92.0 + 0.280 × N`; it under-provisions.

## 2. Bars from tempo (derived + corpus median)

One bar of `M:n/d` is `4n/d` quarter notes, so:

```text
seconds_per_bar = (4n/d) × 60 / Q
bars            = round(duration_s / seconds_per_bar)
```

At M:4/4 this is `240/Q`; at M:2/4 it is `120/Q`; at M:3/8 it is `90/Q`.

The cap over-states sung time. Over the 177 scores, `audio / cap` has
**median 0.884** (P5 0.785, P95 1.003); `syllabify.py` uses 0.884 when no
`--duration` is given. This is a **corpus median**, not the old one-case 0.87 —
the difference is small, but the provenance is now 177 tracks.

On the pure-4/4 subset (n = 20), `bars = round(duration × Q / 240)` predicted the
transcribed bar count within **±5% for every track** (median error −1 bar). With
a render length, pass `--duration`; with a fixed plan, pass `--bars`.

**Tempo:** the corpus is bimodal (`P25 68 · median 80 · P75 109`; the prompts say
110 BPM). The old 73 BPM was the slow cluster. `syllabify.py` now uses **80 BPM**
with a warning when `--tempo` is omitted; pass the real tempo when known.

## 3. Prosody (derived per lyric, verified)

One syllable = one **vowel mark** (fatha, damma, kasra, tanwin, dagger alif).
A long vowel extends the nucleus; shadda is gemination, not a syllable. That is
the same convention as `check_abc.py:lyric_stats`, and it is why the count comes
from the tashkeel and not the letters.

Pace is a **corpus measurement**, not one line's arithmetic. Over the 177
scores, sung bars give **P5 2.24 · P25 2.40 · median 2.84 · P95 4.89**
sixteenths per syllable. `syllabify.py` uses **2.8** (the median, rounded), so a
14-syllable line gets about `14 × 2.8 / 16 = 2.45` bars — two or three, not a
fixed two. The old `2.29` (two bars per line, from one case) sat at P10–P15 and
compressed the vocal by about 24%.

A line off by one is a variant. **Do not scan the poem, look up a bahr, or
transliterate.** The job is a bar budget, not a recitation.

## 4. The ABC dialect (the parser contract)

The runtime parser is `plumbing/yue2_instrumental/abc_tools.py`. It fails closed,
and so does `checker.py`. `example/score.abc` is a 16-bar syntax fixture; use it
for the dialect, not as a song shape. Derive bars, syllables, tempo, key, and
register from `syllabify.py` and the prompt.

Header — exactly eight lines, no extras:

```abc
X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Am
```

Tempo and key come from the plan; the header above is a dialect example, not a
default. Body: `% section`, then `V: Vocal` + 1–4 bars, then `V: Ins` + the
same number of bars. Repeat.

**A blank line ends the tune** for the runtime parser. Never put a blank line in
the body; `checker.py` runs the vendored `abc_tools.parse` first and rejects it
with `runtime parse`. Section comments are `% ` (percent + a space); `%%` is an
ABC directive, not a section marker. `Z`/`Z2`–`Z4` must be the whole bar.

**End with a full-bar rest in both voices** after the final cadence (`Z|`).
Every music line still ends with a plain `|`; **`]` is not part of this
dialect** and fails the runtime parser. The checker **warns** on a missing final
rest by default (92.1% of the 177 have one); pass `--require-final-rest` before
rendering to make it a contract. The renderer/cap then has a clean place to stop.

**Meter changes** are allowed: `M:` may appear after `V:` and before the music
line, and `[K:...]` may appear inside a bar. The corpus uses nine meters
(1/4, 1/8, 2/4, 3/4, 3/8, 4/4, 5/8, 7/8, 9/8) and 121/177 scores change meter;
the checker parses per-bar meter instead of rejecting it.

### 4.1 Keys and maqam spelling

`K:` accepts a standard major or minor key only. `K:Dphr`, `K:Dkurd`,
`K:Dhijaz` and every other mode name are **contract failures**: the runtime
parser rejects them before the checker measures anything. Write the tonic as
`K:<tonic>m` (minor) or `K:<tonic>` (major), and spell every degree the key
signature does not supply with `_`/`^` at each occurrence. An accidental lasts
to the bar end, so restate it after a barline. D Kurd is `K:Dm` with `_E` for
E♭; B♭ is already in Dm. D Hijaz is `K:Dm` with `_E` and `^F`. D Ajam is `K:D`.

**No quarter tones.** The dialect has no `^/2`, `_/2` or microtonal accidental.
Rast, Bayati, Saba and Huzam cannot be encoded; write the nearest diatonic
skeleton and put the intonation in the prompt. Do not claim the maqam is
encoded in ABC.

Declare the pitch set in the plan so the checker can measure the maqam instead
of the key:

```json
"maqam": {"name": "kurd", "tonic": "D",
          "degrees": ["D", "Eb", "F", "G", "A", "Bb", "C"],
          "resting": ["D", "F", "A", "Bb", "C"]}
```

Without this block, `chromatic_per_100` is measured against `K:Dm` and a
correct Kurd score reports about 19 chromatic notes per 100 (the defining E♭).
That number is not a defect; it is the wrong denominator. With the block, the
same score reports 0 chromatic and `maqam_fit_share 1.0`.

| token | meaning | note |
|---|---|---|
| `D4`, `d2`, `C,6` | pitch + L-units | case and `,`/`'` set the octave |
| `^F`, `_B`, `=C` | accidental | overrides the key for that letter to the bar end |
| `z16`, `z8z2` | rest | a rest of 10 is `z8z2` |
| `Z`, `Z2`–`Z4` | whole-bar rest(s) | `Z3` = three bars |
| `"Dm"` | chord symbol | Vocal only; declared in the plan or omitted |
| `d8-d8` | tie | same pitch; merges into one written note |

Legal durations: `1,2,3,4,6,8,12,16,24,32,48` L-units. No dots, no tuplets, no
`[chords]`, no grace notes, no `w:` (lyrics live outside the score). A 5-unit
note is `3-2` tied.

Bar arithmetic matters more than anything else: at L:1/16, 4/4, **every bar is
16** including its rests. A bar that sums to 15 is a failed parse, not a nuance.

## 5. Melodic material (measured corpus)

Source: the `arabmaqamrock` 177-track `five_stars` corpus.

- Diatonic: **0.72** chromatic notes per 100 (pitch class outside the key at
  that note); median track **0**; **91 of 177** tracks have none. An earlier
  count gave 0.83 / 0.38 / 74; the definition differed slightly. The direction
  is the same: the corpus is overwhelmingly diatonic.
- **0 of 177** are Hijaz-shaped even where the prompt said Hijaz (M1 report).
  The maqam tags are provenance, not measured content.
- Consequence: spend colour at cadences, not decoratively. The checker reports
  chromatic notes per 100; the reference case is 0.0.

### 5.1 Maqam spelling table (design rule, not a corpus measurement)

The corpus has no maqam labels: the four tags are prompts, and 0/177 are
Hijaz-shaped (M1 report). This table is a **composition convention** for the
score, not a claim about the audio. Use it to choose a tonic, spell the
degrees, and vary the phrase endings.

| Maqam | Default tonic | Degrees (relative) | ABC spelling | Typical phrase endings |
|---|---|---|---|---|
| **Kurd** | D | 1 ♭2 ♭3 4 5 ♭6 ♭7 | `K:Dm` + `_E` | D, F, A, B♭, C; final D |
| **Nahawand** | D | 1 2 ♭3 4 5 ♭6 ♭7 | `K:Dm` | D, F, A, C; final D |
| **Hijaz** | D | 1 ♭2 3 4 5 ♭6 ♭7 | `K:Dm` + `_E` + `^F` | D, F♯, A, B♭; final D |
| **Ajam** | D | 1 2 3 4 5 6 7 | `K:D` | D, F♯, A, B; final D |

**Why D is the default:** 72/177 corpus scores are in `Dm`, and `Dm` is the
most common key in every maqam subset (Kurd 23/43, Hijaz 13/49, Ajam 21/43,
Nahawand 15/42). If the prompt names a tonic, use it. If the maqam is not in
this table, ask for the tonic; do not invent a scale.

**Phrase endings:** the first column after the scale is the set intermediate
phrases may end on. The final phrase ends on the tonic. A score that ends every
phrase on the tonic has one ending, which the checker now counts as a
degeneracy (corpus min 4, gate min 3).

**Quarter-tone maqams** (Rast, Bayati, Saba, Huzam) are not representable in
this dialect. Write the nearest diatonic skeleton, label the intonation as a
prompt/LoRA responsibility, and do not present the ABC as the maqam.

## 6. Bandwidth — which deviations are audible

| Channel | Bandwidth | Example |
|---|---|---|
| Silence / gap placement | highest | a line left unanswered |
| Density | high | answers pulled for two lines |
| Section register | high | chorus lifted, outro dropped |
| Repetition rate | high | the hook returns a fourth time, or not |
| Phrase shape mutation | medium | one note of the answer changes |
| Single note inside a phrase | lowest | 21 of 490 — inaudible |

Put every declared deviation in the top four rows.

## 7. Shape references: five takes and the 177 corpus

### 7.1 Five takes (case study, older pipeline)

Five SheetSage2 transcripts of the same lyric set. p02 is a YuE2 render; the
group is a case study, not the corpus norm. A declared deviation may leave one
row, not all of them.

| Take | bars | s | vocal mean | top | notes/syll | top dur share | distinct dur | ties | Ins active | Ins notes | chords |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p01 | 71 | 224.6 | 73.5 | 85 | 1.28 | 51% | 7 | 13 | 35% | 123 | 85 |
| p02 | 80 | 263.0 | 75.1 | 88 | 1.26 | 56% | 9 | 8 | 39% | 215 | 99 |
| p03 | 88 | 249.5 | 74.5 | 86 | 1.17 | 54% | 6 | 10 | 41% | 276 | 116 |
| p04 | 101 | 256.0 | 75.4 | 88 | 1.26 | 57% | 7 | 6 | 36% | 250 | 138 |
| p05 | 193 | 312.3 | 74.6 | 86 | 1.37 | 55% | 8 | 12 | 17% | 301 | 198 |

What the rows say **about this case**: the mean is 73.5–75.4, the top 85–88,
ties 6–13, Ins 17–41%, chords 85–198. `p05` at 1.37 is not an outlier in the
177: corpus P90 is 1.40 and P95 is 1.44. Do not copy `melisma_max = 1.30` from
p02/p04; the corpus median is 1.28 and the band is 1.10–1.45.

### 7.2 The 177 corpus (n = 177)

Distributions, not targets. The P5–P95 span is the natural range; a score far
outside it is a different animal.

| Property | P5 | median | P95 | What it means |
|---|---:|---:|---:|---|
| vocal mean MIDI | 71.7 | 73.5 | 75.1 | the voice sits around D5 |
| vocal top | 81 | 84 | 86 | 85 is a stretch, not a default |
| notes per syllable | 1.12 | 1.28 | 1.44 | 1.37 is inside the corpus |
| top duration share | 50.5% | 61.4% | 75.6% | the corpus is more even than p01–p05 |
| distinct durations | 5 | 7 | 9 | 4 is the floor |
| ties per 10 bars | 0.23 | 1.07 | 2.31 | 0.4 is a reasonable plan target |
| Ins active share | 14.1% | 25.3% | 41.2% | the guitar is a part, not the floor |
| chords per bar | 0 | 0 | 0 | the 177 ABCs carry no chord symbols |
| final rest | — | 92.1% have one | — | warn; contract with `--require-final-rest` |
| longest unbroken (s) | 6.1 | 10.4 | 14.9 | max 22.9; one breath, not one bayt |
| phrase median (s) | 2.7 | 3.6 | 5.3 | max 5.8 |
| repeated-pitch share | 27.2% | 32.4% | 38.9% | min 25.2%; a line below 20% is a scale |
| distinct phrase endings | 5 | 7 | 8 | min 4; gate ≥3 |
| tessitura ≥ C5 | 55.3% | 71.2% | 84.5% | max 91%; style/structure target ≤ 0.80, not a sanity gate |
| verse→chorus median | −4 | +2 | +7 | semitones; release target +5, not a sanity gate |
| breaths per bar | 0.18 | 0.24 | 0.41 | min 0.14 |

Source: `analysis/measure_phrasing.py` over the same 177 transcripts
(2026-11-23). A *phrase* is a contiguous sung run; a *breath* is a gap ≥ 0.3 s.
These are the shape numbers the original calibration did not measure. The
median phrase is ~3.6 s, not the 14.6 s of the 2026-11-23 Claude run; the
longest unbroken is 10.4 s median and 22.9 s max, not 34 s.

### 7.3 The nine hard sanity guards

These are the only corpus thresholds that fail a score. They pass **175/177
(98.9%)**; each guard passes ≥99% alone. A gate that fails more than 5% is a
warning/prior, not a guard.

| Guard | Threshold | Corpus basis |
|---|---|---|
| simultaneity | ≤ 4 sixteenths | corpus max 8; 99.4% pass |
| register mean | 74 ± 5 | corpus 69.6–75.9 |
| top duration share | ≤ 0.85 | corpus max 0.86 |
| distinct durations | ≥ 4 | corpus min 4 |
| notes per syllable | 1.0–1.55 | corpus 1.03–1.52 |
| Ins active share | ≥ 0.05 | corpus min 0.08 |
| unbroken singing | ≤ 23 s | corpus max 22.89; 177/177 |
| repeated-pitch share | ≥ 0.20 | corpus min 0.252; 177/177 |
| distinct phrase endings | ≥ 3 | corpus min 4; 177/177, when ≥6 phrases |

The last three are **shape** guards, added after the 2026-11-23 Claude run: that
score passed the six validity guards while singing 34 s without a breath,
repeating a pitch on 6% of intervals, and ending 10 of 13 phrases on D. They
are calibrated on the same 177 and pass all of them; they are not taste. The
*style targets* are stricter (10 s, 3 endings, 0.65 top duration).

### 7.4 The p02 take in detail

`p02_nahawand_a015_c15_ar075_7949497`, SheetSage2 transcript of a
YuE2/arabmaqamrock render, Q = 73, 80 bars (263 s nominal; the audio was
262.15 s), two voices.

| Property | Measured |
|---|---|
| bars with guitar | 31 |
| of those, singer silent (intro / interlude / outro) | 15 |
| of those, singer singing — guitar in the gaps | 16 |
| moments with both voices sounding | **0** |
| answer rate, verse 1 | 5 of 6 lines |
| answer rate, verse 2 | 2 of 8 lines |
| answer rate, verse 3 | 3 of 4 lines |
| answer rate, chorus 1 / 2 | 2 of 2 / 1 of 2 |
| distinct answer shapes in the verse | 3 |
| repeats per shape | 2 each |

Shape mutation, as transcribed:

```text
cdABAAG  →  cdABzAG  →  cdABAAz2  →  cdcBzAz2
DEFAdef  →  FADefed
```

Answer register per fill, ABC spelling: F4–B4, then G4–D5, then D4–F5 — it
widens and rises before it is pulled. In the chorus the guitar changes texture
instead: long low notes (`AGFE`) under the high voice — a bed, not an answer.

Gap arithmetic: the vocal's largest contiguous rest in an answered bar is 6–8
sixteenths; the answer fits inside it and leaves the bar at 16.

**These are that case's numbers, not targets.** Re-measure on your own render.

## 8. Register (procedure, not numbers)

1. Render the same lyrics bare at the same settings.
2. Transcribe the vocal, or read the MIDI range.
3. Use that range for the verse; put the chorus inside the same ceiling.

The reference case's chorus top equalled the highest note the singer reached
anywhere else: a lift *within* the voice, not beyond it. Offline, use §7.2 as a
prior and say the range is unmeasured: mean **71.7–75.1** (median 73.5), top
**81–86** (median 84). The corpus median is `mean 74, top 84, max_top 86`;
the example plan uses `mean 70, top 80, max_top 84` for a lower male lead.
Use 74 only when the style names a high tenor or a female lead.

`top` is the note the take must reach; `max_top` is the ceiling. A high note is
not a style. The chorus lifts the median by about five semitones; it does not
move the whole line above C5. Keep `tessitura_share_ge_c5` at or below 0.80
(corpus P95 0.845) and write one planned peak per section.

## 9. What the ABC cannot measure

| Thing | Why | Where it lives |
|---|---|---|
| chord symbols | **0 of 177** ABC scores carry them | the `chord.lab` sidecar / render |
| motifs | no annotation in ABC | manual or corpus analysis |
| per-line bar allocation | `phrases.json` carries the line bar range/pause; syllable-to-note still needs `w:` | phrase sidecar + forced alignment |
| timbre, mix, balance | not in ABC | prompt + LoRA + render |
| microtonal ornament | not in the dialect | renderer |
| audio quality | not in ABC | listening |

Do not infer these from the score and do not claim the checker measured them.
The checker measures notes, bars, registers, durations, ties, and text-derived
syllables. That is the whole scope.

## 10. What the score cannot express

Do not attempt these in ABC; they belong to the prompt and the LoRA:

- microtonal / quarter-tone ornament
- timbre, EQ, compression, reverb, stereo image
- consonant crispness, vocal-forward balance
- choir, backing harmonies, layered guitars, drums
- breath, belting onset, tarab inflection

Write the *place* for the ornament; the renderer performs it.
