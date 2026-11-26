# metrics.md — what the numbers mean

One entry per measured value. Definitions are for diagnosis, not for tuning a
score into a gate. `score_cli.py explain-metric <name>` prints one entry.

## notes_per_syllable

Vocal notes divided by `plan.json` `syllables`. It counts notes, not duration.
Sanity band 1.00–1.55; the plan's melisma band is 1.10–1.45. A partial score
naturally reads low because the denominator is the whole lyric; the live meter
therefore prints a **projection** for the lines already written.

## register_mean

Arithmetic mean of the MIDI pitch numbers of all vocal notes. It is
**note-weighted, not duration-weighted**: a held D and a passing D count once
each. Sanity 74 ± 5; the plan target is 70 ± 3 by default.

## register_top

The highest vocal MIDI pitch in the score. It is a ceiling, not a centre. The
corpus floor is 80; the plan's default top target is 82 and max top 84.

## repeated_share

Share of consecutive vocal intervals that are 0 (the same pitch repeated). The
interval list is built inside breath-runs. Sanity floor 20%; corpus min 25%. A
low value describes a scale, not a tune; it says nothing about which pitch
should repeat.

## top_duration_share

Share of vocal notes that use the score's most common written duration. It
catches a score padded with one note value. Sanity max 85%; plan max 65%.

## distinct_durations

Number of distinct written durations among vocal notes, in `L:` units. Sanity
min 4; plan min 5. Splitting a note into tied pieces does not create a new
duration at the metric level in the way a longer or shorter written value does.

## simultaneities

Total overlapping sounding L-units between `Vocal` and `Ins`, summed over the
score and reported per bar. The hard cap is 4 units unless the plan declares a
`simultaneity_exception` bar. This is the "voice and guitar occupy the same
sixteenth" guard.

## silence_share

`1 - (sum of vocal note durations) / (last vocal note end - first vocal note
onset)`. It measures the breath inside the sung span, not the instrumental
bars. Style floor 22%; the corpus is around 30%.

## answer_rate

Per section, the share of vocal beat-phrases whose following gap (at least four
L-units) contains at least one Ins onset. It is printed as `answered/total`, not
as a percentage, because the sample is small. `insufficient sample` means the
section has too few phrases to judge.

## vocal_median_pitch

Median MIDI pitch of the vocal notes in the bar range named by a plan deviation
or a section. It is a range metric: the same note contributes to the whole-score
`register_mean` but only to its own range here.

## unbroken_seconds_max

The longest contiguous run of vocal notes with no rest at all, measured from the
first onset to the last note end in seconds. Sanity max 23 s; the plan default
target is 10 s. It is not the same as a phrase: a phrase may contain a short
rest.

## end

The `end°` column of `check --bars` is a **pitch class relative to the tonic**:
`(last_midi - tonic_midi) % 12`, printed with flat spelling. In Dm a written C
is `10` and prints `Bb`; it is not the written pitch. The `pitch` column is the
absolute written note (`C5`). `cadence_pc` is the raw pitch class of the final
vocal note (C = 0).

## cadence_pc

Raw pitch class (0–11, C = 0) of the last vocal note. The `cadence: "tonic"`
check compares it with the tonic pitch class of the key. It does not say the
cadence is good; only that the final note is the declared tonic.

## chorus_lift

`median(chorus MIDI) - median(verse MIDI)`, in semitones. The plan default
minimum is 5. The separate `chorus lift` check compares the **max** pitch of the
two sections; `chorus_lift` is the median comparison.

## cap_ratio

`score seconds / raw duration cap` from `prosody.json`. Below the corpus minimum
0.708 it warns about padding; above the cap it warns about exceeding the
declared duration. It is a band warning unless a strict shape run is active.
