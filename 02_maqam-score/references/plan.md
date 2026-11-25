# plan.md — the one-page brief

`plan.json` is written by `score_cli.py init`; you edit values, not the shape.
The checker requires the keys below. `plan lint` names what is missing;
`plan refresh` re-derives `arrangement` from the score.

## Required targets

| Key | Meaning | Default |
|---|---|---|
| `plan_version` | schema generation | `"0.8.1"` |
| `key` | standard major/minor key; `K:Dm`, not `K:Dkurd` | from the maqam |
| `tempo`, `meter`, `unit` | `80`, `4/4`, `1/16` | from `init` |
| `bars`, `syllables` | form length and lyric count | from `syllabify` |
| `sections` | lyric sections in order, repeats kept | from `phrases.json` |
| `melisma_min/max` | notes per syllable band | `1.10` / `1.45` |
| `register` | `{mean, top, max_top, tolerance}` | `70 / 82 / 84 / 3` |
| `tessitura_share_ge_c5_max` | share at/above C5 | `0.80` |
| `chorus_lift_min` | median chorus minus verse, semitones | `5` |
| `max_top_duration_share` | most common duration share | `0.65` |
| `min_distinct_durations` | duration values | `5` |
| `ties_min` | tied vocal notes | `1` |
| `min_fill_notes` | shortest guitar answer | `3` |
| `ins_active_share_min` | share of bars with Ins | `0.20` |
| `chords_min` | chord symbols in `score.abc` | `0` |
| `max_unbroken_seconds` | longest unbroken singing | `10` |
| `min_phrase_endings` | distinct phrase endings | `3` |
| `strict_shape` | make shape targets hard | `false` |
| `cadence` | `"tonic"` is a self-imposed hard final | `"tonic"` |
| `maqam`, `maqam_fit_min` | required when the prompt names a maqam | `null` / `0.95` |

## Maqam (design convention, not a corpus measurement)

| Maqam | Tonic | `K:` | Degrees | Resting |
|---|---|---|---|---|
| Kurd | D | `K:Dm` + `_E` | D, Eb, F, G, A, Bb, C | D, F, A, C |
| Nahawand | D | `K:Dm` | D, E, F, G, A, Bb, C | D, F, A, C |
| Hijaz | D | `K:Dm` + `_E` + `^F` | D, Eb, F#, G, A, Bb, C | D, F#, A, Bb |
| Ajam | D | `K:D` | D, E, F#, G, A, B, C# | D, F#, A, B |

If the prompt names a maqam but no tonic, use D and say so. If the maqam is not
in this table, ask for the tonic.

## Arrangement

`arrangement.section_plan` tiles `1..bars` contiguously. Each row:

```json
{"bars": "13-36", "role": "verse", "vocal_notes_per_bar": [0, 3],
 "ins_notes_per_bar": [0, 8], "ins_active_share": [0, 1],
 "answer_rate": [0, 1]}
```

Every sung range carries `answer_rate`. An instrumental range (intro,
interlude, solo, outro) has `vocal_notes_per_bar: [0, 0]`. `ins_entries` lists
the bars where Ins enters after at least two silent bars; `plan refresh`
detects them. Do not hand-type the ranges; init writes them and refresh repairs
them after a form edit.

## Copies

`"copies": []` means every repeated section is newly composed. If a section is
a by-ear copy of an earlier one, declare it:

```json
{"mode": "independent", "bars": "46-66"}
```

The checker compares declared copies bar-for-bar and fails on drift or on a
declared change that did not happen. When in doubt, write new music and leave
the list empty.

## Deviations

`deviations` is **3-4** entries, positioned by bar, on a high-bandwidth channel
(register, density, gap rate, answer shape, texture). Qualitative
`before`/`after` is enough; add an `assert` when the number is already measured:

```json
{"bars": "35-39", "channel": "gap rate",
 "before": "the guitar answers every line",
 "after": "the guitar drops out for both choruses",
 "assert": {"metric": "ins_active_share", "range": "35-39", "op": "==", "value": 0}}
```

Allowed assert metrics: `answer_rate`, `ins_notes_per_bar`,
`vocal_notes_per_bar`, `vocal_median_pitch`, `ins_active_share`,
`silence_share`. If a deviation cannot be measured, use `"unverifiable": true`
with a real `reason`. `plan lint` fails while `placeholder` remains.

## Checks

`plan lint` is structural: required keys, 3-4 deviations, no placeholders, and
a section plan that tiles `1..bars`. `plan refresh` rewrites the section plan
and `ins_entries` from the current score. Neither command judges the music.
