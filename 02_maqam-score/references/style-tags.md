# Style-tag translation

A style tag is a prompt/LoRA instruction. The score can only choose the part it
owns: structure, prosody, gaps, density, register, repetition, rhythm. Translate
each tag into a **score decision** and, where possible, a measured target. Keep
the target `style`/`strict_shape`; never turn it into a corpus sanity guard.

Read `references/craft.md` for the method behind the decisions.

| Tag | Score decision | Measured by |
|---|---|---|
| **belting, operatic, powerful** | 2–3 planned peaks, each a *held* note; chorus median +5 in release mode; `tessitura_share_ge_c5_max 0.80`; `max_top 86`; do not belt every line | register, tessitura, chorus lift median |
| **tarab, melismatic, ornaments** | body 1.00–1.10 notes/syllable; 3–8 notes on chosen cadence syllables; the return of a phrase with more intensity (*tarjīʿ*), not a new phrase; write the place for the ornament | melisma band, phrase plan, craft §6 |
| **call and response** | the Ins answers in a vocal rest, never under a sung syllable; two or three answer shapes, each a mutation; in the seed, a backing voice echoes the cadence | simultaneity, answer fill, craft §7 |
| **symphonic metal, heavy, epic** | a 2-bar riff motif (pedal or cell-derived), palm-mute in the verse, open texture in the chorus; strings as pad/counterline, not block chords; the solo develops the cell; the score does not add a third voice in the contract | Ins active share, rhythm variety, craft §7 |
| **rhythm guitar, distorted guitars** | a riff with rhythm and a motif, not a whole-bar arpeggio; the low register belongs to the riff, the vocal stays above it | Ins notes/bar, answer shapes |
| **backing vocals, choir, layered harmonies** | the LoRA performs them; the contract stays two voices. In the seed, add a backing voice that echoes the line end, not a doubled lead | contract, craft §9 |
| **microtonal, quarter-tone, maqam ornament** | not encodable in this dialect; keep the intonation in the prompt and write the place (a long note, a rest, a cadential turn). Never claim ABC encoded the quarter tone | reference §9/§10 |
| **somber, night dread, lament** | low verse register, slow tempo, longer gaps, ♭6/♭7 endings, the ♭2 as an event; the outro drops an octave | plan, register, cadence ladder |
| **clear enunciation, vocal-forward, crisp consonants** | body syllabic (one note per syllable), no busy Ins under the voice, no tie across a word boundary; the rest is the mix's job | notes/syllable, simultaneity |
| **audiophile, close-mic, plate reverb** | not in the score; do not claim it. Timbre and space belong to the prompt and the render | — |
| **Maqam Kurd** | Jins Kurd on the tonic + Jins Nahawand on the 4th; touch G (ghammāz), one peak at the jawāb, return to D; the ♭2 once or twice per section; do not write natural minor | `maqam_fit_share`, cadence ladder, craft §5 |

Rules:

1. A tag never overrides a user request ("less melisma" wins).
2. A tag never justifies a missed breath, tessitura, duration, or ending
   target. Those are quality targets, not arrangement deviations.
3. Do not claim the score encoded timbre, mix, microtones, or ornament quality.
   It encoded a place for the renderer to perform them.
4. If a tag conflicts with the corpus shape, prefer the user's brief and record
   the deviation; do not edit `calibration.json`.
5. A tag is not a licence to add notes. "Epic" is an arc, "belting" is a peak,
   "tarab" is a cadence, "heavy" is a riff. None of them means "busier".
