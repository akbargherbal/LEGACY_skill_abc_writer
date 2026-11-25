---
name: abc-score-writer
description: >-
  Compose a NEW ABC score from Arabic lyrics and an arabmaqamrock style prompt:
  a small, declared set of deviations from the LoRA's own default arrangement.
  Ships its own syllabifier and checker; the full package also bundles a corpus
  snapshot, so it runs offline in two commands.
  Use when asked to write, compose, generate or design a score, melody, or ABC
  file from lyrics and a style. Do NOT use for editing an existing SheetSage2
  transcription.
---

# abc-score-writer — composing a score from scratch

You are writing a **complete two-voice score** for a LoRA that already knows this
genre and performs competently on its own. The score is not a sketch and not a
list of gestures: it is the full vocal line plus the guitar part, bar by bar.
**Then** you declare three or four deliberate deviations from what the LoRA would
do without it. The deviations are the only intentional changes; the arrangement
around them is still a real arrangement.

The checked file is two voices. The arrangement it feeds also has drums: the
**seed** carries them (§3.7), and the vocal's rhythm must give them something to
answer (`references/rhythm.md`). A score that passes the gate and leaves the
drummer to the model is the failure the listener hears first.

**Write the tune before you write to the gate.** The checker proves the score is
readable and inside the corpus; it cannot tell you whether the melody is worth
hearing. §3.3 and `references/craft.md` are the composition method. A score that
satisfies every number and has no cell, no period and one phrase rhythm is the
failure mode this skill exists to prevent.

The tools are bundled. You do not write a parser, a builder, a renderer, or a
syllabifier, and you do not install anything. **Run the scripts; do not read
them.** This file, `references/craft.md` and `references/reference.md` are the
interface.

```
<skill>/scripts/syllabify.py       lyrics -> numbers (letters, syllables, bars)
<skill>/scripts/checker.py         score verifier: PASS/WARN/FAIL + measured block
<skill>/scripts/verify_package.py  package verifier: score<->seed, Drums, core, docs, state
<skill>/scripts/craft.py           report-only tune mirror; --phrases for the per-line table
<skill>/scripts/quality.py         objective quality gate (unbroken/pause/distinct/top/tessitura)
<skill>/scripts/repair.py          global failure -> bars/phrases repair map
<skill>/scripts/abc_doctor.py      explains a parser error in plain language
<skill>/scripts/abc_tools.py       score parser CLI: inspect / strip-chords / compare
<skill>/scripts/calibration.json   the 177-track thresholds (do not edit)
<skill>/scripts/selftest.sh        proves the tools work on example/
<skill>/example/                   a 16-bar syntax fixture; derive your own shape
<skill>/example/groove.abc         the seed.abc drum voice, 8 bars
<skill>/references/craft.md        the composition method: cell, period, cadence, riff
<skill>/references/rhythm.md       phrase rules, groove, drum interaction, seed drums
<skill>/references/critic.md       the 8-point core review (5 numbered lines)
<skill>/references/style-tags.md   style tag -> score decision
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

### 3.0 The order — one order only

```text
syllabify → core_draft.abc (8–16) → core_review.md → plan.json
          → score.abc → seed.abc → seed_sheet.md / notes.md
```

- `core_draft.abc` is the **first composition file**. Do not write `plan.json`
  or `score.abc` before it. Do not design the full 82 bars before it.
- The core uses the targets in `example/plan.json` and the absolute bars in
  `prosody.json`/`phrases.json`. The full `plan.json` is written **after** the
  core and its review.
- `core_review.md` is the critic's 5-line review (`references/critic.md`).
- `seed_sheet.md` is written **after** `score.abc`. The full frame is not a
  precondition for the core.

### 3.1 Numbers

```bash
python3 <skill>/scripts/syllabify.py <lyrics> --tempo <Q> --json prosody.json
```

When you already know the section layout, write the phrase sidecar in the same
run and let the tool do the absolute-bar arithmetic:

```bash
python3 <skill>/scripts/syllabify.py <lyrics> --tempo <Q> --json prosody.json \
  --phrases phrases.json \
  --sections "intro=7,verse 1=13,chorus=37,verse 2=46,chorus=65,outro=77"
```

`--sections` lists the absolute bar of each **sung** section, in lyric order;
repeat a section name for a repeat (the first `chorus` is the first chorus).
The tool writes `bar_start`/`bar_end` for every line. Do not add those offsets
by hand.

The command prints letters, syllables (marks), the duration cap and token cap,
the bar budget, the section table, and syllables per line. Copy those numbers;
do not recount by hand. If it exits 1, the lyrics need more bars than the duration
allows — raise the tempo or cut lines, do not compress the syllables. Pass
`--duration` when a render length is known, or `--bars` when the length is
already decided.

The defaults come from `calibration.json`, not from one case: **tempo 80 BPM**
(with a warning — pass `--tempo` when the render is known), **pace 2.8
sixteenths per sung syllable** (corpus median 2.84), and **cap ratio 0.884**
(corpus median `audio/cap`). The old 73 BPM / 2.29 / 0.87 were a single-case
prior; they compressed the vocal.

### 3.2 Plan — one JSON file (after the core)

After the core and its review, write `plan.json`. This is the brief; every
value is a number or a name. The checker fails a plan that omits a required
target, so write the complete object before the first bar of the **full**
score. The block below is the 16-bar fixture: use it for the field names, not
for its bars, tempo, key, sections, or deviations.

The core itself uses the targets in `example/plan.json` and the bars in
`prosody.json`/`phrases.json`; do not write this file to start the core.

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
  "strict_shape": false,
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
  reach high notes without sitting there. `strict_shape: true` makes a miss
  hard; the default `false` keeps it a warning.
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
- `strict_shape`: `false` in the template. It makes the shape targets the plan
  declares (`max_unbroken_seconds`, `max_top_duration_share`, `tessitura`,
  `register`, `chorus_lift_min`, `silence`, `maqam_fit`, phrase plan) **hard**
  when set to `true`. With the default `false` they stay warnings, as in 0.3.0:
  the brief is a target, not a gate. Set it `true` only when the user asks for a
  strict release (T21); then fix every shape WARN or report it with approval.
  Never set it true just to make the checker look strict.
- `maqam`: **required when the prompt names a maqam**; `null` only when no
  maqam was given. `degrees` is the pitch set the vocal may use; `resting` is
  the set intermediate phrases may end on; `tonic` must match `K:`. When
  present, `chromatic_per_100` is measured against the maqam, not the key.
  Without it the report says `chromatic_basis: key:...`, and a Kurd score
  written as `K:Dm` looks 19% chromatic.

Two or three answer shapes, each mutating; a rate that rises, falls, and partly
returns; the guitar owns the intro/interlude/outro outright. That plan lives in
the bars, not in prose.

### 3.3 Compose — the method, before a pitch

Read `references/craft.md` here. The gate comes later; this is the part the gate
cannot see. Work in this order, and keep a **draft core** of 8–16 bars before
expanding:

The core is the **first 8–16 bars of `score.abc`**, and it is the **first
composition artifact**. Write `core_draft.abc` before `plan.json` and before
`score.abc`; do not design the full 82 bars in your head before the first file
exists. The core is not extracted from a finished score: it is written first,
reviewed, fixed, then expanded. If the core changes after a check, edit the
opening bars; do not rewrite the whole score. The core is the one place extra
thinking buys quality — the rest is expansion and local repair.

1. **Lyric as song.** Find the bayt (two hemistichs), the caesura, the qāfiya,
   the repeated line and the emotional pivot. The score breathes where the poem
   breathes. Do not name a baḥr unless you scanned it.
2. **Cell.** 3–6 notes with a rhythm you can sing; one cell per section. It must
   contain a repeated note, a 4th/5th leap, or a distinctive rhythm.
3. **Period.** 2 bars antecedent ending open (5th, ♭6, 2nd); 2 bars consequent
   ending closed (tonic or 3rd). Same head, different tail.
4. **Transform.** Pick two or three: sequence, inversion, truncation,
   augmentation, ornament, registral shift, fragmentation, displacement. Never
   transpose the whole verse; that is a key change, not a variation.
5. **Elastic text slots.** The period is anchors + shorts + 2–4 fills + one
   cadence slot, so it absorbs 13–17 syllables without squeezing every note.
   Write the alignment intent in the report (bar, syllables, slots, where the
   fill and the melisma are).
6. **Cadence ladder and sayr.** Open on the 5th; use ♭6/♭7 for colour; the ♭3
   rarely (4.7% of corpus endings); the tonic for the section close and the final
   qafla. In Kurd, Jins Kurd (D–E♭–F–G) sits under Jins Nahawand on the 4th
   (G–A–B♭–C): touch G (the ghammāz), rise to the jawāb once, return.
7. **Melisma as an event.** Body 1.00–1.10 notes/syllable; 3–8 notes on chosen
   cadence syllables; overall 1.15–1.35. Write the place; the renderer performs
   the quarter-tone ornament.
8. **Guitar as a part.** Two or three answer shapes, 3–8 notes each and each a
   mutation of the last; a 2-bar riff motif derived from the cell or a pedal;
   answers in the vocal's gaps; owns the intro/interlude/solo/outro; changes
   texture at the chorus; the solo develops the cell. A whole-bar arpeggio is a
   floor, not a part.
9. **Rhythm section.** Write the phrase and groove **rules** before you encode:
   how phrases start and end, the 2–4 bar length range, one 2-bar groove per
   section, and three interaction events (unison, stop, fill, drop). Vary the
   start (a pickup on the `&` of 4), the length and the cadence beat; leave one
   **2-beat hole** per 4 bars. Record the rules; write `seed_sheet.md`
   **after** `score.abc` as exactly 10 numbered lines (no title).
   `phrases.json` owns the per-line table; do not retype it. Do not write the
   full frame before the core. A drummer cannot answer a grid; see
   `references/rhythm.md`.
10. **Subtract for intensity.** Remove a layer before the chorus; let the voice
    drop out for the solo; let the guitar drop out for the last line. The chorus
    lifts the median about five semitones; it does not add notes.

Then the **audition by reduction** on the draft core (`craft.md` §10): read the
cell in notation and check its contour, count the ideas, find the peak, count
the phrase rhythms, check the cadence ladder, check the literal loops. If audio
is available, hum it; offline, say you did not audition. Fix the core *before*
encoding the whole score. The numbers are below; the method is what makes them
music.

| Decision | Target | Basis |
|---|---|---|
| register | mean 70, top 80, `max_top` 84; one peak per section; `tessitura_share_ge_c5_max` 0.80 | example/plan.json |
| breath | one lyric line = one phrase; ≥0.5 s at the line end; ≤10 s unbroken; silence ≥22% | corpus |
| cadence | final tonic; intermediate on resting tones; ≥3 distinct endings (aim 5–7); 5th most common, tonic ≤25% | corpus |
| repeated pitch | 25–43% of intervals | corpus min/max |
| literal loops | ≥75% unique vocal bars | corpus P10 |
| phrase rhythm | ≥0.85 distinct phrase rhythms | corpus P10 0.914 |
| late peak | ≥25% of phrases peak in their second half | corpus P10 |
| phrase end | not every phrase ends on a long note; ≤0.80 | corpus max 0.821 |
| melisma | body 1.00–1.10; cadence 3–8; overall 1.15–1.35 | corpus band + design |
| phrase start | ≥2 distinct beat positions per section; one pickup | design |
| phrase length | ≥2 distinct lengths; not every line the same 3-bar frame | design |
| drum hole | one 2-beat internal rest per 4 bars; a fill at the group end | design |

**Phrase plan.** `syllabify.py --phrases` writes the line table. Pass
`--sections` in the same run to write the absolute `bar_start`/`bar_end` after
the section layout; do not add the offsets by hand. Then pass
`--phrases phrases.json` to the checker. At 80 BPM `z4` is 0.75 s; a breath is
≥0.5 s at the line end and ≥1.0 s at the bayt end. Rests come from allocating
bars, not from removing syllables. **The sidecar is a map, not a 3-bar
template:** if every line has the same bar count, the drummer has nothing to
phrase against.

The register, breath, ending and maqam numbers are still plan targets and the
checker enforces them. The last eight rows are craft diagnostics: count them on
the draft, not after the full score. Run `craft.py score.abc --json craft.json`; it prints the melodic numbers
(rhythm variety, unique bars, end-long, cadence, tessitura). The seed is
structural in `verify_package.py`. It is a mirror, not a gate.

**Write `seed_sheet.md` after `score.abc`, as exactly 10 numbered lines
(no title, no blank line).** Rules, not per-line results: frame, cell, period
rule, cadence rule, melisma rule, riff, subtraction, one 2-bar groove per
section, three interaction events, and the weakest bar to fix. `phrases.json`
owns the line table (bar ranges, syllables, pauses); do not retype it. The sheet
is a plan, not a deliverable: if a line is uncertain, write the rule and move
on. A sheet written after the score is not a plan.

The checker cannot see motifs or grooves, so do not claim it did. If a motif
carries an answer shape, name that shape in the deviation list.

**Before the full score:** run `craft.py core_draft.abc --phrases phrases.json`
to see the per-line table, then run the critic in `references/critic.md` and
write `core_review.md` (exactly 5 numbered lines, one issue per line, tied to a
bar). Fix the core. Only then write `plan.json` and expand to `score.abc`.

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

The tempo and key come from your plan, not from this example. The example is a
dialect fixture; do not copy its register, proportions, section lengths or
one-bar phrase lengths. It is a syntax model, not a rhythm model; `rhythm.md`
and `example/groove.abc` are the rhythm models.

Rules that save a repair pass:

- **No blank lines anywhere in the body.** The runtime parser treats a blank
  line as the end of the tune. The checker runs the vendored parser before it
  measures anything; a blank line is a hard FAIL, not a warning.
- `% section` goes **before** the `V: Vocal` block, with a space after the
  percent (`% intro`). A `%` inside a block is an annotation and is ignored.
- Blocks alternate `V: Vocal`, `V: Ins`, each 1–4 bars, music line ending in `|`.
  Both blocks in a pair have the same bar count. Do not insert blank lines
  between pairs. **`score.abc` is two voices:** do not add a Drums voice to the
  checked file; the contract parser rejects it. Drums go in `seed.abc` (§3.7).
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
do not fail unless `strict_shape: true` or you pass `--strict-style`.
The default check is a validity check. **Release quality is
`--strict-style` with zero WARNs.** The checker runs the vendored runtime parser
first; if it prints `FAIL runtime parse`, the renderer cannot read the file at
all — fix the dialect (usually a blank line, a header line, or a tie), not the
checker.

**The checker is the score verifier, not a final exam.** Run it with
`--json report.json` after the first `score.abc`, and again only after a named
fix. Read `report.json.measured`; it is the authoritative block for bar counts,
notes, register, duration spread, ties, silence and phrase endings. Stop after a
pass. A global sanity failure (e.g. `repeated_share`) allows one full rewrite
and one verification; any contract error after that is a named fix. Maximum four
runs. Do not write a parser or a statistics script: the seed/drums/docs checks
are in `verify_package.py`; if a number is missing, extend that file, not a
throwaway script.

**Tool map — one question, one tool.**

| Question | Tool |
|---|---|
| Is the score valid? | `checker.py` → `report.json` |
| Where is the global failure? | `repair.py` → `repair.json` (bars/phrases) |
| What is each lyric line doing? | `craft.py --phrases` → `phrase_table.json` |
| Are the objective quality targets met? | `quality.py` → `quality.json` |
| Why did the parser reject? | `abc_doctor.py` |
| Is the package/order/state consistent? | `verify_package.py` → `verify.json` |
| What is the state? | `state.json` + `STATE.md` |

If a tool cannot answer a number, add it to that tool; do not write a heredoc.

**State.** Copy `templates/STATE.md` and `templates/state.json` to the working
directory **before the first artifact**. Update both after each artifact and each
check (phase, last artifact, last check, pass, report hash, next action).
After a compaction, read `state.json` before anything else; if it says the
package is done, stop. Do not re-run a check the state records as passed.
`verify_package.py --state state.json` checks the hash and the pass flag.

The checker is not the aesthetic gate. It does not measure the cell, the
period, the phrase-rhythm variety or the peak placement; §3.3 and `craft.md` §10
do. A PASS is not a verdict on the tune; the listener decides.

On a **contract or sanity FAIL**, read `report.json.measured` and run
`repair.py score.abc --report report.json --plan plan.json --phrases phrases.json`
to get the bars/phrases responsible. Fix **only** those bars or headers, then
run the checker again. Do not rewrite the whole score for a global metric unless
the repair map covers most of it and you declare why.

On a **style or shape WARN**:
- In a **validity run** (no `quality_targets.json`), a WARN is diagnostic;
  report it. Do not rewrite the score for a WARN.
- In a **quality run** (`quality_targets.json` present, as in session 10), the
  objective Layer-2 targets are acceptance: `unbroken`, `pause hierarchy`,
  `distinct_bar_share`, `top_duration`, `tessitura`. Fix them with the repair
  map, then run `quality.py`. Taste (cell, sayr, melisma, dialogue, ostinato,
  arc) stays with the critic; it is not a gate.

The old sentence "do not rewrite the score for a WARN" applies only to the
validity run. A quality run that leaves a declared objective target failing is
not done. If a check can only be satisfied by changing the plan, change the
plan and say so; never fake a number. A declared arrangement deviation is not a
waiver for breath, tessitura, duration mix, endings, silence, or pause
hierarchy.

Stop after the check passes. Do not re-run to "confirm"; do not run a fifth
check after a clean pass. In a quality run, run `quality.py` once after the
checker passes; if it fails, use `repair.json` for one scoped fix and one
verification.

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

### 3.5.2 Quality run — the objective layer

If the task includes `quality_targets.json` (session 10 does), run:

```bash
python3 <skill>/scripts/quality.py score.abc --plan plan.json \
  --phrases phrases.json --targets quality_targets.json --json quality.json
```

`quality.py` fails only on the objective targets the task declared:

- `unbroken_seconds_max`;
- `pause hierarchy` (actual gaps vs the sidecar, plus variation);
- `top_duration_share_max`;
- `distinct_bar_share_min`;
- `tessitura_share_ge_c5_max`.

The sidecar's `pause_after_s` is the **intended** rest. Edit that value to the
hierarchy (caesura 0.5–0.75 s, line end 1.0–1.5 s, section end longer), never
the `bar_start`/`bar_end` ranges. `quality.py` compares the actual gap to it.

It does not judge the cell, sayr, melisma, dialogue, ostinato or the arc; those
are `references/critic.md`. If `quality.py` fails, read `repair.json` (or run
`repair.py`), fix the named bars/lines, and verify once. A quality run is not
done while an objective target is open.

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
4. **Run the checker after the fix.** If a style target now contradicts the
   brief, change the target and record it; do not "fix" the music back to the old
   target. One check per change; stop after it passes.
5. **Stop after one pass.** If the user is still unhappy, ask which section
   (chorus, verse, outro) and work there.
6. **A quality WARN is not an arrangement deviation.** If the final check has a
   shape WARN (breath, tessitura, duration, endings, silence), fix it or report
   it with the user's explicit approval. Do not file it under `deviations` to
   make the report look clean.

A revision is not a second composition. One scoped edit and one check are the
whole budget.

### 3.7 Seed delivery — one tune, two renderings

When the target is a cover model (Suno, Udio) or the user asks for chords,
instruments or backing voices, deliver two files:

| File | What it is | Validated by |
|---|---|---|
| `score.abc` | the strict two-voice dialect, the source of truth | `checker.py`, `--strict-style`, `--phrases` |
| `seed.abc` | free ABC: `"Dm"` chords, `%%MIDI program`, optional backing/strings voices, and a `Drums` voice when the style has drums, `!p!`/`!f!` | bar sums and voice alignment only |

Rules:

- The melody is **the same** in both. Do not compose a second tune for the seed.
- Write and check the full `score.abc` **before** `seed.abc`. It is the proof
  that the melody is complete and inside the corpus; `seed.abc` is the
  orchestration of that melody.
- `seed.abc` is **not** contract-checked. Say so in the report, and say which
  checks were not run. Do not present "every bar adds up" as a validation.
- If the user asked only for a seed, still write `score.abc`. The strict file
  costs one pass and prevents the free file from hiding an incomplete melody.
- Chords are optional in `score.abc` (`chords_min` 0) and expected in the seed.
  The contract still allows `"Dm"` in the Vocal voice if you want the harmony
  written in the checked file.
- **Drums are a voice in the seed, not a hope.** When the style block names
  drums, rhythm guitar or metal, or the target is a cover model, `seed.abc` must
  carry a `V: Drums` voice: a 2-bar groove per section, a fill at the end of a
  4- or 8-bar group, and a drop at the last line. Use `%%MIDI channel 10` and
  `%%MIDI drummap`; `example/groove.abc` is a working 8-bar model, and
  `references/rhythm.md` §5 gives the dialect. If the renderer ignores
  percussion, say so; the phrase rules and the vocal rhythm still carry the
  interaction.
- **The melody must imply the groove even without the drum staff.** A drummer
  reads the vocal's onsets, rests, holds and cadence landings. If the voice is
  an unbroken eighth-note stream in identical 3-bar phrases, the drum part is
  decoration. Write the pickup, the 2-beat hole and the varied cadence beat
  before you write the drums.

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

These are the brief, not a corpus gate. With `strict_shape: false` (the template
default) they stay warnings; `strict_shape: true` makes the declared values
FAIL. Set it true only for a strict release.

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
output. Never retype a number. The run also delivers `seed_sheet.md` (exactly 10
numbered lines of rules: cell, period, cadence, groove, events), `notes.md`,
`core_review.md` (5 numbered critic lines), `verify.json`, `craft.json`,
`repair.json` (when a global metric failed), `quality.json` (quality run),
`craft.json`/`core_table.json` includes the per-line table when `--phrases` is
used, `state.json`, `STATE.md`, and, for a cover target, `seed.abc` with the
drum voice. The sheet is written **after**
`score.abc`; it is a plan, not a checker input. The measured block includes `register_mean`,
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
- **Writing a phrase grid.** The same 2-2-1-2 rhythm in 26 phrases passes
  `top_duration_share` and sounds like a metronome. Count the distinct phrase
  rhythms on the draft (`craft.md` §10); the corpus P10 is 0.914.
- **The three-bar grid.** Every lyric line set to the same 3-bar frame, starting
  on beat 1, ending on beat 3 or 4, with a 1-beat gap. The drummer has no cue
  and will play his own idea. Vary the start, the length and the cadence beat
  (`references/rhythm.md`).
- **Drums left to the model.** The style says metal; the score has no drum voice
  and the seed has none. The listener hears the model's default drummer, not
  your arrangement. Write the 2-bar groove and the fills in `seed.abc`.
- **A fill in every gap.** If the voice rests one beat at every line end, there
  is no room for a fill and no reason for one. Leave a 2-beat hole once per 4
  bars, at the end of a group, and let the drums answer there.
- **Looping a bar, or transposing the verse.** One 9-note bar eleven times is a
  loop; a verse lifted a step is a key change. Reuse the *cell*, not the bar;
  vary the consequent and the cadence.
- **Making melisma an average.** 1.11 notes/syllable with one 5-note tag is not a
  melismatic setting. Put 3–8 notes on chosen cadence syllables and keep the
  body syllabic (`craft.md` §6).
- **Every phrase peaking on its first note.** 26 descending sighs is a tic. Let
  a third of the phrases build to a late peak (corpus P10 0.242).
- **Ending every phrase long.** A quarter note at every line end kills the
  forward motion; the corpus max for "end long" is 0.821, and the median is
  0.241.
- **Naming a baḥr without scanning.** "Al-basīṭ" is a claim about the poem's
  feet. If you used a long/short pattern as a guess, call it a heuristic, and do
  not say the singer "adapts" a line to a tune with the wrong slots.
- **Leaving the contract silently for a seed.** If the user wants chords,
  backing voices or Suno, deliver `score.abc` *and* `seed.abc` (§3.7), and say
  which file passed which check.
- **The whole-bar arpeggio guitar.** `A,4 C4 E4 A4` is a floor, not a riff.
  Write a 2-bar motif with rhythm, answer in the vocal's gaps, and change
  texture at the chorus.
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

Composition has two drafts, then one check per change:

1. **Core draft** — 8–16 bars: cell, period, one cadence, the guitar motif, the
   phrase/groove rules (the 10 numbered lines of `seed_sheet.md`). Write the
   core **before** you plan the rest of the form. Run the §10 checklist on it
   (read the cell in notation, count the phrase rhythms, find the peak, check
   the cadence ladder). Do not encode the full score yet.
2. **Expand** — set the bayts on the elastic slots, write the guitar part, the
   rhythm section and the subtraction arc, encode `score.abc` (and `seed.abc`
   with the drum voice if the target is a cover model).
3. **Check and repair.** Run `checker.py --json report.json`; fix only the bars
   or headers the checker names, with `edit`. Do not rewrite the whole score.
   One repair per check; stop after the check passes.

**Economic contract.** The final score is small; the process is not allowed to
be arbitrarily larger. Treat the score's token size as the unit: write the first
`score.abc` early, use the checker for measurement, and do not re-derive the
piece in prose. In an instrumented run the analyst may end the session if it
spends more than about **10×** the score's token size. A budget is a stop rule,
not a target and not a reason to lower the music.

Before delivering a release-quality score, run `--strict-style`; a shape WARN
is a miss only for a strict release, not a command to rewrite a default run.
Revision: one scoped edit and one check per feedback. If a revision needs a
second repair, the plan and the request disagree; change the plan, not the
music.

The core draft is the one place extra tokens buy quality. It is 8–16 bars, not a
second score. Do not skip it to save a pass; a gate-shaped first draft costs
more, because every later fix is arrangement around a weak tune. The rhythm
sheet is one page of names and beats, not a second score; it is what keeps the
drummer from inventing his own arrangement.

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
