---
name: abc_score_writer
description: >-
  Compose a NEW ABC score from Arabic lyrics and an arabmaqamrock style prompt:
  a small, declared set of deviations from the LoRA's own default arrangement.
  Ships its own syllabifier and checker plus a corpus snapshot, so it runs
  offline in two commands.
  Use when asked to write, compose, generate or design a score, melody, or ABC
  file from lyrics and a style. Do NOT use for editing an existing SheetSage2
  transcription.
---

# abc_score_writer — composing a score from scratch

You are writing a **complete two-voice score** for a LoRA that already knows this
genre and performs competently on its own. The score is not a sketch and not a
list of gestures: it is the full vocal line plus the guitar part, bar by bar.
**Then** you declare three or four deliberate deviations from what the LoRA would
do without it. The deviations are the only intentional changes; the arrangement
around them is still a real arrangement.

The tools are bundled. You do not write a parser, a builder, a renderer, or a
syllabifier, and you do not install anything. **Run the scripts; do not read
them.** This file and `references/reference.md` are the interface.

```
<skill>/scripts/syllabify.py       lyrics -> numbers (letters, syllables, bars)
<skill>/scripts/checker.py         score + plan -> PASS/WARN/FAIL + the measured block
<skill>/scripts/calibration.json   the 177-track thresholds (do not edit)
<skill>/scripts/abc_tools.py       vendored runtime parser (the renderer's contract)
<skill>/scripts/selftest.sh        proves both work on example/ (run once if in doubt)
<skill>/example/                   a 16-bar syntax fixture; derive your own shape
```

`<skill>` is the directory holding this file. Run the scripts by absolute path;
write `plan.json`, `score.abc` and the reports in your working directory.

**Gate classes.** The checker has four:

- **contract** — the renderer's rules: dialect, header, complete bars, voices,
  and plan/score agreement. Always hard.
- **sanity** — nine broad degeneracy guards calibrated on the 177-track corpus:
  simultaneity, register mean, duration spread, duration variety,
  notes per syllable, Ins presence, and three **shape** guards: longest
  unbroken singing, repeated-pitch share, and distinct phrase endings. Always
  hard. They pass **175/177 (98.9%)**, because they are wide enough to describe
  the corpus, not a taste.
- **structure** — declared shape targets: breath, duration mix, tessitura,
  register ceiling, chorus median lift, silence, maqam fit, phrase plan. Hard
  when the plan has `strict_shape: true`; otherwise `style`. A declared
  `cadence: "tonic"` is always hard.
- **style** — melisma band, high register, Ins density, tie count, chords,
  sections, answer mutation, chorus max lift. **Warn by default.**
  `--strict-style` turns them into failures if you want that.

The final rest warns by default; pass `--require-final-rest` before rendering.
A style number that fails more than 5% of good scores is a **warning or a
prior**, never a hard gate. The calibration lives in
`scripts/calibration.json`; do not invent thresholds.

Every threshold is registered with its `class`, `basis`, `n`, and pass rate in
**`references/numbers.md`**. If you change a number, change that registry and
`scripts/calibration.json` together.

## 1. The gate

You need four things:

1. **Lyrics, vocalised** — the harakat carry the count. Stripped lyrics cannot be
   counted; stop and say so.
2. **The style block** for this run.
3. **The maqam.** The key is the maqam's tonic. If the prompt names a maqam but
   no tonic, use the default in `references/reference.md` §5.1 (Kurd → D,
   Nahawand → D, Hijaz → D, Ajam → D) and say so. If the maqam is not in that
   table, ask for the tonic.
4. **The lyrics file path**, for the duration cap. Pasting counts: save the
   pasted lyrics verbatim to `lyrics.txt`. An empty uploads folder alone is not
   a missing lyric.

Stop only when the lyric is missing or unvocalised, the style block is missing,
or the maqam is missing. Do not guess a maqam. **Tempo is not a gate:** if it is
omitted, use 80 BPM (the corpus median; `syllabify.py` does this with a warning)
and record the assumption. If the prompt gives a range, take a value inside it.

**The key is not a maqam key.** `K:` accepts a standard major or minor key
only; `K:Dphr`, `K:Dkurd`, `K:Dhijaz` are contract failures. Write the tonic as
`K:<tonic>m` (minor) or `K:<tonic>` (major), spell the maqam's other degrees
with `_`/`^`, and declare `maqam` in the plan (`references/reference.md` §5.1).

**Mode.** You are in **offline mode** unless you can actually run the renderer
(`generate.py` with the LoRA on a GPU) and listen to the result. Offline means:
priors from `references/reference.md`, no baseline render, no listening claim, no installing
`abcmidi`/`abcm2ps`, no rendering PNGs, no web search. Say "offline" in the
report. Never claim an audition that did not happen.

## 2. The baseline you deviate from

| Default behaviour | Why |
|---|---|
| answers every sung line | fixed answer rate |
| reuses one answer shape | no mutation |
| keeps density flat | no curve |
| keeps the second voice present throughout | no priority |
| builds by adding layers | conventional build |

This table is a **hypothesis** until a bare render is measured. Offline, it is
still the prior you design against — but write "prior, unmeasured" in the report.
`references/reference.md` §7 holds the measured cases; they show what good takes did, not
what the default is.

### 2.1 What a complete score contains

The **177-track corpus** is the shape reference. The numbers below are
distributions, not targets. Only the nine `sanity` guards are hard; everything
else is a warning or a prior.

| Property | Corpus (n=177) | Gate |
|---|---|---|
| vocal mean MIDI | 71.7–75.1 (median 73.5) | **sanity 74 ± 5** |
| vocal top | 81–86 (median 84) | style floor 80; target 82–85 |
| notes per syllable | 1.12–1.44 (median 1.28) | **sanity 1.0–1.55** |
| most common duration | 50.5–75.6% (median 61.4%) | **sanity ≤ 85%** |
| distinct durations | 5–9 (median 7) | **sanity ≥ 4** |
| ties per 10 bars | 0.23–2.31 (median 1.07) | style; plan target |
| Ins active bars | 14.1–41.2% (median 25.3%) | **sanity ≥ 5%** |
| longest unbroken singing | 5.5–22.9 s (median 10.4) | **sanity ≤ 23 s**; target 10 |
| repeated-pitch share | 25.2–42.6% (median 32.4) | **sanity ≥ 20%** |
| distinct phrase endings | 4–8 (median 7) | **sanity ≥ 3** (when ≥ 6 phrases) |
| tessitura ≥ C5 | 55.3–84.5% (median 71.2) | style/structure target ≤ 0.80 |
| verse→chorus median | −4 to +7 semitones (median +2) | style/structure target +5 in release mode |
| answer length | floor 3; answers can run long | style |
| chord symbols | no chords in the 177 ABCs | style / optional |
| final rest | 92.1% | warn; `--require-final-rest` before render |

The nine sanity guards pass **175/177 (98.9%)**. A number that fails more than
5% of good scores is a warning or a prior, not a gate. A declared deviation may
leave a style range; it may not fail a sanity guard.

The 177 are SheetSage2 transcripts of Suno renders, not human compositions.
They describe **what the model rendered**, not what a score must be. The five
`p01`–`p05` takes in `references/reference.md` came from an older pipeline
(p02 is a YuE2 render); they are a case study, not the corpus norm.

Who owns what — do not fight another row:

| Layer | Owns |
|---|---|
| Prompt | idiom, genre, mood, production words |
| LoRA | mix, timbre, arrangement, harmonies, choir, performance |
| Score | structure, prosody, gaps, density, register, repetition |
| Listener | whether it is beautiful |

Density is yours; balance is not. Never write a busy part to "fix" the mix — the
score can only avoid causing the problem. Translate style tags with
`references/style-tags.md`; a tag never overrides a quality target.

## 3. The pipeline — one pass

### 3.1 Numbers

```bash
python3 <skill>/scripts/syllabify.py <lyrics> --tempo <Q> --json prosody.json
```

It prints letters, syllables (marks), the duration cap and token cap, the bar
budget, the section table, and syllables per line. Copy those numbers; do not
recount by hand. If it exits 1, the lyrics need more bars than the duration
allows — raise the tempo or cut lines, do not compress the syllables. Pass
`--duration` when a render length is known, or `--bars` when the length is
already decided.

The defaults come from `calibration.json`, not from one case: **tempo 80 BPM**
(with a warning — pass `--tempo` when the render is known), **pace 2.8
sixteenths per sung syllable** (corpus median 2.84), and **cap ratio 0.884**
(corpus median `audio/cap`). The old 73 BPM / 2.29 / 0.87 were a single-case
prior; they compressed the vocal.

### 3.2 Plan — one JSON file

Write `plan.json`. This is the brief; every value is a number or a name. The
checker fails a plan that omits a required target, so write the complete object
before the first bar. The block below is the 16-bar fixture: use it for the
field names, not for its bars, tempo, key, sections, or deviations.

```json
{
  "key": "Am", "tempo": 80, "meter": "4/4", "unit": "1/16",
  "bars": 16,
  "syllables": 16,
  "sections": ["intro", "verse", "chorus", "outro"],
  "simultaneity_exception": null,
  "cadence": "tonic",
  "melisma_min": 1.10,
  "melisma_max": 1.45,
  "register": {"mean": 70, "top": 80, "max_top": 84, "tolerance": 3},
  "tessitura_share_ge_c5_max": 0.80,
  "chorus_lift_min": 5,
  "max_top_duration_share": 0.65,
  "min_distinct_durations": 5,
  "ties_min": 1,
  "min_fill_notes": 3,
  "ins_active_share_min": 0.20,
  "chords_min": 0,
  "max_unbroken_seconds": 10,
  "min_phrase_endings": 3,
  "strict_shape": true,
  "maqam": null,
  "maqam_fit_min": 0.95,
  "deviations": [
    {"bars": "1-2, 15-16", "channel": "section register", "before": "guitar under the voice", "after": "guitar owns the intro and outro"},
    {"bars": "3-14", "channel": "gap rate", "before": "an answer after every line", "after": "answers thin to the first and third lines"},
    {"bars": "9-14", "channel": "section register", "before": "one verse-level register", "after": "the chorus lifts the median without sitting above C5 throughout"}
  ]
}
```

- `sections` in order, with repeats. Names are **normalized** (`Verse 1` →
  `verse`); the score may have extra instrumental sections (`interlude`,
  `intro`, `outro`) that the lyrics do not. Sections warn by default; keep the
  plan honest, but do not invent a section to satisfy a string match.
- `deviations`: **3–4**, from the high-bandwidth channels only (`references/reference.md`
  §6). Position by bar. "At the chorus" is not a position. Keep `before`/`after`
  qualitative unless the number is already in `MEASURED`; a plan that claims
  "3/10" while the checker measures "4/4" is a false brief.
- `simultaneity_exception`: `null`, or one bar number you spend deliberately
  (≤ 4 sixteenths, one short note). The sanity guard allows at most 4
  overlapping sixteenths in total.
- `melisma_min` / `melisma_max`: notes per syllable band. The corpus runs
  **1.12–1.44** (median 1.28); use **1.10–1.45** as a broad band. 1.26 is a
  center, not a target. Ties do not count as extra notes. This is a **style**
  target: it warns by default. **If the brief asks for less ornament, set
  `melisma_min` to 1.00 and keep `melisma_max` around 1.15; a style WARN is
  acceptable. Never add notes the user asked you to remove.**
- `register`: `mean` is the verse centre; `top` is the note the take must
  reach; `max_top` is the ceiling. `tolerance` is the style band around the
  mean (use 3; the sanity guard stays ±5). For a full song the corpus mean is
  73.5, top median 84, top P95 86; the 16-bar fixture uses 70/80 only because
  it is a miniature, not a register target. A high note alone is not a style:
  the chorus lifts the median, not the whole line.
- `tessitura_share_ge_c5_max`: the share of vocal notes at or above C5. Corpus
  median 71%, P95 84.5%, max 91%. The style target is **0.80**: a score can
  reach high notes without sitting there. `strict_shape` makes a miss hard.
- `chorus_lift_min`: the median chorus pitch minus the median verse pitch, in
  semitones. Corpus median 2, P95 7; the release target is **5**. It is a
  brief target, not a corpus sanity guard.
- `max_top_duration_share`: the corpus median is 61%, P75 is 69%, and the
  sanity ceiling is **0.85**. Use **0.65** as the style target. Never copy
  0.85 as a target: it is the last value before the gate fails.
- `min_distinct_durations`: the sanity floor is **4**; 5 is a style target.
  Values come from `1,2,3,4,6,8,12,16,24,32,48`.
- `ties_min`: the sanity floor is **1**; 0 is valid for a syllabic style. A
  floor of **3** is safe for a long score; the corpus median is about 8 ties at
  78 bars (1.07 per 10). Do not force ties.
- `min_fill_notes`: the shortest guitar answer. Use 3; answers can run much
  longer than 8 (the 3–8 upper bound is not measured). A two-note tag is still
  a tag, not an answer.
- `ins_active_share_min`: the sanity floor is **5%**; 20% is P25 and 25% is the
  corpus median. Use **0.20**; 0.15 is below P25. Do not force the guitar
  through the whole score.
- `chords_min`: **0 by default**. The 177 ABCs carry no chord symbols. If you
  want a harmony line, declare about 1.0 per bar and write it; otherwise leave
  harmony to the LoRA.
- `cadence`: `"tonic"` puts the **final** vocal note on the tonic and makes it
  a hard check you chose. It does not mean every phrase ends on the tonic; see
  §3.3.
- `max_unbroken_seconds`: the longest a singer goes without a breath. Corpus
  median 10.4 s, max 22.9 s; the sanity ceiling is 23 s and the style target is
  **10**. Use 10. A 14-syllable line at 80 BPM is about 7.5 s; 10 s is one
  line, not two.
- `min_phrase_endings`: at least **3** distinct phrase-ending pitches, with the
  final one on the tonic. Corpus min 4, median 7. The checker counts them from
  the phrase boundaries; a score with fewer than 3 (and at least 6 phrases)
  fails the sanity guard.
- `strict_shape`: `true` in the template. It makes the shape targets the plan
  declares (`max_unbroken_seconds`, `max_top_duration_share`, `tessitura`,
  `register`, `chorus_lift_min`, `silence`, `maqam_fit`, phrase plan) **hard**.
  Without the flag they stay warnings, as in 0.3.0. This is how the brief
  becomes an acceptance test without changing the corpus sanity gate.
- `maqam`: **required when the prompt names a maqam**; `null` only when no
  maqam was given. `degrees` is the pitch set the vocal may use; `resting` is
  the set intermediate phrases may end on; `tonic` must match `K:`. When
  present, `chromatic_per_100` is measured against the maqam, not the key.
  Without it the report says `chromatic_basis: key:...`, and a Kurd score
  written as `K:Dm` looks 19% chromatic.

Two or three answer shapes, each mutating; a rate that rises, falls, and partly
returns; the guitar owns the intro/interlude/outro outright. That plan lives in
the bars, not in prose.

### 3.3 Material — seven decisions, before a pitch

- **Maqam and cadence figure.** Use the table in `references/reference.md` §5.1
  for the pitch set, the default tonic and the resting tones. The phrase that
  says "this maqam", used once or twice, entered and left by step.
- **Two or three motifs.** The vocal's cells, 3–6 notes each; every phrase
  derives from one. Write each with the transformation you will use.
- **Register.** From a bare render; offline, the `references/reference.md` §7 prior,
  labelled unmeasured. The corpus verse mean is **71.7–75.1 MIDI** (median 73.5)
  and the top is **81–86** (median 84). For a full song use 74 mean, 84 top, and
  a `max_top` of 86; 82 is P25 and 88 is a stretch. The 16-bar fixture uses
  70/80 because it is a miniature, not a register target. Put the chorus inside
  the same ceiling and do not write the verse an octave below it. One planned
  peak per section, not a high tessitura throughout:
  `tessitura_share_ge_c5_max 0.80` is the target.
- **Phrase and breath.** **One lyric line is one phrase.** `syllabify.py` prints
  the bars per line and can write a `phrases.json` sidecar (`--phrases`). Copy
  the line table, set the absolute `bar_start`/`bar_end` after the section
  layout, and pass it to the checker. At 80 BPM one beat is 0.75 s (`z4`), two
  beats 1.5 s (`z8`); a breath is at least 0.5 s. Do not chain a bayt (two
  hemistichs) into one 5-bar phrase: a 14-syllable line at 80 BPM is about
  7.5 s, and the ceiling is 10 s unbroken. If a line runs longer, split it at
  the caesura. The silence floor is 22% of the sung span (corpus median 30%);
  rests are added by allocating bars, not by removing syllables.
- **Cadence note.** The **final** vocal note is the tonic. Intermediate phrases
  end on the maqam's resting tones, and the score uses **at least three
  different phrase-ending pitches**. Do not end every phrase on the tonic: that
  is the mechanical cadence the listener hears first. For Kurd the resting set
  is D, F, A, B♭, C; for Nahawand D, F, A, C; for Hijaz D, F♯, A, B♭; for Ajam
  D, F♯, A, B.
- **Rhythm profile.** A sung phrase is not a row of eighth notes. Mix sixteenths
  and eighths, repeat a note, hold a long note at the phrase end, and tie it
  when it crosses a beat. Every phrase needs one gesture from the rhythm list:
  a repeated cell, a long note, a tie, or a short rest inside the phrase.
  The corpus repeats a pitch on **25–43%** of its melodic intervals (median
  32%); a line with almost no repeated notes is a scale, not a melody. If you
  can sing it as "one, two, three, four" in every bar, it is a scale.
- **Answer shapes.** Two or three, 3–8 notes each, each a transformation of the
  last. The guitar owns the intro/interlude/outro outright; in the chorus it may
  become a low bed instead of an answer. A two-note tag at the barline is not
  an answer.

The checker cannot see motifs, so do not claim it did. If a motif carries an
answer shape, name that shape in the deviation list.

### 3.4 Write `score.abc`

Write the ABC directly. Do not generate it with a script and do not build one.

The dialect is fixed by the runtime parser (`abc_tools.py`). Header, exactly:

```abc
X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Am
% intro
V: Vocal
Z|
V: Ins
A,4 C4 E4 A4|
```

The tempo and key come from your plan, not from this example. The example is
a dialect fixture; do not copy its register, proportions, or section lengths.

Rules that save a repair pass:

- **No blank lines anywhere in the body.** The runtime parser treats a blank
  line as the end of the tune. The checker runs the vendored parser before it
  measures anything; a blank line is a hard FAIL, not a warning.
- `% section` goes **before** the `V: Vocal` block, with a space after the
  percent (`% intro`). A `%` inside a block is an annotation and is ignored.
- Blocks alternate `V: Vocal`, `V: Ins`, each 1–4 bars, music line ending in `|`.
  Both blocks in a pair have the same bar count. Do not insert blank lines
  between pairs.
- **Meter changes are allowed.** `M:2/4` may appear after `V:` and before the
  music line; `[K:...]` may appear inside a bar. The corpus uses nine meters and
  121/177 scores change meter; the checker parses per-bar meter instead of
  rejecting it.
- **End with silence.** The final bar should be a full-bar rest in both voices
  (`Z|`), after the final cadence. The last music line still ends with a plain
  `|`. Do **not** use `]`: the runtime parser rejects it. The checker **warns**
  on a missing final rest by default; pass `--require-final-rest` before
  rendering to make it a render contract. The final rest is the only clean
  place for the renderer/cap to stop.
- Durations are only `1,2,3,4,6,8,12,16,24,32,48` L-units. A 10-sixteenth rest
  is `z8z2`, not `z10`; a 5-sixteenth note is `3-2` tied, not `5`. No dots.
- Every bar sums to its meter: 16 L-units at L:1/16 in 4/4, 8 in 2/4, 6 in
  3/8. Count rests, not just notes.
- `Z` / `Z2`–`Z4` are whole-bar rests and must be the **whole** bar; `z16` is a
  rest inside one bar. Do not mix `Z` with notes in the same bar.
- Chord symbols (`"Dm"`) only in Vocal. They are optional: the 177 ABCs carry
  none, so `chords_min` defaults to 0. Declare about 1.0 per bar only if you
  deliberately want a harmony line.
- **No `w:` lines.** The score carries no lyrics; the renderer takes them
  separately. No tuplets, no `[...]` chords, no microtonal `^/2`.
- A tie must join the same pitch and stay inside one syllable — in practice, the
  long note at a line end. Every tie is one written note.

### 3.5 Check

```bash
python3 <skill>/scripts/checker.py score.abc --plan plan.json \
  --phrases phrases.json --json report.json --require-final-rest
```

Exit 0 means no **hard** check failed; `WARN` lines are style diagnostics and
do not fail unless `strict_shape` is in the plan or you pass `--strict-style`.
The default check is a validity check. **Release quality is
`--strict-style` with zero WARNs.** The checker runs the vendored runtime parser
first; if it prints `FAIL runtime parse`, the renderer cannot read the file at
all — fix the dialect (usually a blank line, a header line, or a tie), not the
checker.

On a sanity `FAIL`, fix **only** the bars named, then run it once more. No other
edits. If a shape target misses, write the missing music; do not lower a
threshold. If a check can only be satisfied by changing the plan, change the
plan and say so; never fake a number. A declared arrangement deviation is not a
waiver for breath, tessitura, duration mix, endings, or silence.

### 3.5.1 Error → fix

| Check | Fix |
|---|---|
| `duration spread` FAIL (one duration >85%) | Write longer notes at phrase ends and rests between phrases. **Do not split notes into sixteenths**: that raises notes/syllable and adds melisma. |
| `notes per syllable` FAIL high | Remove turns/passing notes; keep one note per syllable; use a tie for a long note. |
| `notes per syllable` FAIL low | Add a melisma only at a planned cadence; do not add notes everywhere. |
| `unbroken singing` FAIL | Add a rest at the next line end; split the phrase at the caesura. |
| `repeated notes` FAIL | Repeat a pitch or a 3-note cell; do not transpose the scale. |
| `phrase endings` FAIL | End intermediate phrases on different resting tones; only the final phrase is tonic. |
| `silence` WARN | Add rests at line ends. The vocal needs 22% rest; the guitar is not the cause. |
| `tessitura share` WARN/FAIL | Remove sustained notes at/above C5; keep one planned peak per section. Do not raise the target. |
| `chorus lift median` WARN/FAIL | Move the verse down or the chorus median up; the chorus lifts the median, not only the top note. |
| `phrase plan` WARN/FAIL | Add the missing line-end rest or fix the bar range; use the `syllabify.py --phrases` table. |
| melisma target WARN after a "less melisma" request | Lower `melisma_min` to 1.00, keep `melisma_max`, say so; do not add notes. |

One check per change. If a check passes, stop checking; do not re-run after a
pass to "confirm".

### 3.6 Revision — one channel, one pass

When the user gives feedback on a finished score:

1. **Name the channel** they asked to change: melisma, register, phrase, hook,
   accompaniment, ending. Change that channel only; keep the bars, key, tempo,
   sections and the parts they said they liked.
2. **If the feedback changes a plan target, edit `plan.json` and say which
   value changed.** "Less ornament" means `melisma_min` 1.00, not more notes.
   A style target is the brief; when the brief changes, the target changes.
3. **Edit the score in place.** Do not regenerate the whole score unless the
   user asks for a rewrite or the structure is wrong.
4. **Run the checker once.** If a style target now contradicts the brief,
   change the target and record it; do not "fix" the music back to the old
   target.
5. **Stop after one pass.** If the user is still unhappy, ask which section
   (chorus, verse, outro) and work there.
6. **A quality WARN is not an arrangement deviation.** If the final check has a
   shape WARN (breath, tessitura, duration, endings, silence), fix it or report
   it with the user's explicit approval. Do not file it under `deviations` to
   make the report look clean.

A revision is not a second composition. One scoped edit and one check are the
whole budget.

## 4. What the checks mean

**Contract — the file is unusable or the brief is empty (always FAIL):**

- `runtime parse`: the vendored `abc_tools.parse` accepts the file. A blank
  line, a wrong header, a mixed `Z` bar, or a bad tie fails here.
- exact dialect and headers, complete bars, both voices with equal length;
- key, tempo, meter, unit, and bars agree with the plan;
- a complete plan: every target key present;
- **final rest**: only with `--require-final-rest` (before rendering). Without
  the flag it is a style warning.

**Sanity — nine broad degeneracy guards (always FAIL; pass 175/177):**

- at most 4 overlapping sixteenths between the two voices;
- vocal mean within 74 ± 5 MIDI;
- no single duration is more than 85% of the vocal notes;
- at least 4 distinct vocal durations;
- notes per syllable between 1.0 and 1.55;
- the Ins sounds in at least 5% of the bars;
- **longest unbroken singing ≤ 23 s** (corpus max 22.9; target 10);
- **repeated-pitch share ≥ 20%** (corpus min 25.2);
- **at least 3 distinct phrase endings** when the score has ≥ 6 phrases
  (corpus min 4).

These catch an octave error, a monotone rhythm, a missing second voice, a
one-breath scale, or a score that is not in the corpus universe. They do **not**
prescribe a style.

**Structure — declared shape targets (hard under `strict_shape`):**

- `max_unbroken_seconds`, `max_top_duration_share`, `tessitura_share_ge_c5_max`,
  `register` (mean/top/max_top), `chorus_lift_min`, `silence`, `maqam_fit`,
  `min_phrase_endings`, and the optional `phrases.json` line plan;
- `cadence: "tonic"` is always a self-imposed hard target.

These are the brief, not a corpus gate. A plan without `strict_shape` falls back
to the 0.3.0 warnings; a plan with it makes the declared values FAIL.

**Style — WARN by default; `--strict-style` makes them FAIL:**

- the plan's melisma band, duration variety, ties, answer fill, Ins activity,
  chords, sections;
- answer mutation, chorus max lift, deviations, final rest.

**Listening is the only aesthetic gate, and it needs audio.** The sanity guards
ask "is this a score in the same universe?"; the style warnings ask "is it the
brief you declared?" Neither is a verdict on beauty. Offline, say so.

## 5. Report

`CHANGES.txt` = the plan's deviation list plus the checker's `MEASURED` block,
copied verbatim, plus a `WARNINGS` section. `report.json` is the `--json`
output. Never retype a number. The measured block includes `register_mean`,
`register_top`, `register_range`, `top_duration_share`,
`distinct_durations`, `ties`, `fill_lengths`, `ins_active_share`, `chords`,
`unbroken_seconds_max`, `phrase_seconds_median`, `repeated_share`,
`distinct_phrase_endings`, `phrase_endings`, `tessitura_share_ge_c5`,
`verse_chorus_semitones`, `phrases_checked`, `phrase_violations`,
`chromatic_basis`, `maqam_fit_share`, and a `percentiles` line that places each
value in the 177-track distribution. Quote them; do not restate them from
memory. Every check also carries its `class` (`contract`, `sanity`, `structure`,
`style`).

```
WARNINGS
- <check>: <measured vs target> -> FIXED <bars/change>
- <check>: <measured vs target> -> DECLARED <reason + user approval>
```

A release-quality score has no open `WARNINGS` rows. A shape WARN is a miss,
not a style preference; a declared arrangement deviation is not a waiver.

`chromatic_per_100` is measured against `plan.maqam.degrees` when a maqam block
is present, and against `K:` when it is not. A Kurd score written as `K:Dm`
therefore reports about 19 chromatic notes per 100 unless you declare the
maqam; that number is the flat second, not an error. Declare the maqam.

If a measured value leaves the reference range, write the reason in the file.
A silent overrun is a defect; a declared one is a decision.

The checker cannot see motifs, orchestration, timbre, or harmony that is not
written as chord symbols. Do not claim it measured them; the 177 ABCs carry no
chords at all. See `references/reference.md` §9 for the boundary.

## 6. Traps

- Building a parser, a syllabifier, or a renderer. They are in `scripts/`.
- Installing an ABC toolchain or rendering sheet images to "look" at the score.
- Writing before the plan, then rationalising the bars against it.
- **Writing a skeleton that passes the counts.** One note per syllable, the
  guitar on whole-bar rests, two-note answers, no ties, no chords: every bar can
  add up and the result is not a score. The sanity guards and style warnings
  exist for this.
- **Copying the example or the §3.2 plan as a template.** Both are 16-bar
  dialect fixtures, not a melody or a song frame. Derive bars, syllables,
  tempo, key, sections, and register from `syllabify.py` and the prompt; never
  copy 16/80/Am or the example's three deviations onto another lyric.
- **Writing a scale.** `D2 F2 G2 A2 B2 A2 G2 F2` in every bar is a finger
  exercise. Start from a 3–6 note motif, repeat notes, hold a long note, and
  mutate the cell. The corpus repeats a pitch on 25–43% of intervals; a line
  with almost none is a scale.
- **One breath per bayt.** A 5-bar phrase at 80 BPM is about 15 s without a
  breath. One lyric line is one phrase; put a rest at each line end, use the
  `syllabify.py --phrases` sidecar, and pass it to `checker.py --phrases`.
- **Sitting above C5 throughout.** The chorus lifts the median; it does not
  move the whole line into the top register. Keep `tessitura_share_ge_c5` at
  or below 0.80 and plan one peak per section.
- **Ending every phrase on the tonic.** Only the final phrase ends on the tonic.
  Intermediate phrases end on the maqam's resting tones; use at least three
  different endings.
- **Splitting notes to fix `duration spread`.** That adds notes per syllable and
  melisma. Write longer notes and rests instead.
- **Copying `0.85` or `top 82` from an old plan.** 0.85 is the sanity ceiling and
  82 is P25; both are below the corpus shape. Use 0.65 and 84.
- **A blank line in the body.** The runtime parser ends the tune there; the
  renderer never sees the rest.
- **Ending on a note with no final rest.** The cap then has no clean place to
  cut, and the model keeps filling. Close the score with `Z|` in both voices,
  and pass `--require-final-rest` before rendering.
- **Lowering a sanity threshold to pass.** The sanity guards are corpus-wide
  floors. If the score misses one, write the missing music. Style targets are
  the brief: fix them or declare the deviation; do not edit the calibration.
- Deviating everywhere, or on a low-bandwidth channel (one note in a phrase) and
  waiting to hear a difference.
- A busy second voice under the vocal, then blaming the mix.
- Tying across a word boundary — the consonant lives in the transition.
- Counting bars or notes by hand and reporting the hand count.
- Claiming a listening result that was never heard.

## 7. Cost

Composition: one `syllabify` run (with `--phrases`), one plan, one score, one
check, at most one repair. The first pass must meet the declared shape targets;
if you are past that, the plan was wrong — go back to 3.2, not to the parser.
Before delivering a release-quality score, run `--strict-style`; a shape WARN
is a miss, not a free pass. Revision: one scoped edit and one check per
feedback. If a revision needs a second repair, the plan and the request
disagree; change the plan, not the music.

## 8. Corpus tools (bundled)

The corpus artifacts — source cache, records, priors, idiom bank, similarity
index and evaluation split — ship with the skill under `<skill>/data/ostris/`.
The three commands below work offline with no flags and no bucket access:

```bash
scripts/ostris_cli.py plan     --manifest song.json --out plans/song
scripts/ostris_cli.py exemplar --function cadence --bars 2
scripts/ostris_cli.py check    score.abc --plan plans/song/skill_plan.json --report report.json
```

`plan` defaults to the bundled `priors/priors.json`; `exemplar` to the bundled
`idioms.jsonl`; `check` to the bundled `priors/` and `similarity/`. Pass
`--out`/`--priors` only to point at a different snapshot.

- `plan` writes `brief.json` and `skill_plan.json`. `skill_plan.json` carries the
  15 targets `checker.py` requires plus the shape targets
  (`max_unbroken_seconds`, `min_phrase_endings`, `tessitura_share_ge_c5_max`,
  `chorus_lift_min`, `register.max_top`); `strict_shape` is false in the
  objective generated plan. Set it true for a composer release brief. Pass
  `skill_plan.json` to `check`, never `brief.json`.
- `exemplar` returns 2–4 bar structural phrases. They are unreviewed. Do not
  call them maqam examples.
- `check` runs `checker.py`, adds a prior percentile and an interval-similarity
  run, and nests the checker report under `skill_report`. `pass` means no
  contract or sanity failure; style warnings stay warnings.

There is no maqam label and no maqam-fit score in this build. Do not present a
prior, `mode_hypothesis`, or an exemplar as a maqam judgement.
