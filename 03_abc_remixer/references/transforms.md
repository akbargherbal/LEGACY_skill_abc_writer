# Remix transforms

Transforms are applied **left to right** as written in `remix.sources[].transform`.
The verifier works from parsed notes `(pitch, duration_quarters)`, never from
source text.

| Transform | Syntax | Effect | Quote is literal? |
|---|---|---|---|
| transpose | `transpose:+2`, `transpose:-3` | add semitones | yes |
| invert | `invert` | reflect around the first pitch | no |
| retrograde | `retrograde` | reverse note order and durations | no |
| augment | `augment:2x` | multiply durations by 2 | no |
| diminish | `diminish:0.5x` | multiply durations by 0.5 | no |
| fragment | `fragment:first-5-notes` | keep the first N notes | no |
| fragment | `fragment:last-3-notes` | keep the last N notes | no |
| fragment | `fragment:2-6` | keep 1-based note slice 2..6 | no |
| rhythm-only | `rhythm-only` | keep durations, ignore pitch | no |
| contour-only | `contour-only` | match the up/down/repeat contour | no |

## Matching

- Exact mode (default) compares interval sequences exactly and note durations
  exactly. `--tolerance N` allows up to N mismatched positions and labels the
  result `partial`.
- `transpose` does not change intervals; a transposed quote is still literal
  pitch content and is counted in `literal_share`.
- `invert` reflects `p -> 2*p0 - p`; intervals are negated.
- `retrograde` reverses the note list, so the interval sequence is reversed and
  negated.
- `augment`/`diminish` scale absolute durations; the verifier compares the
  scaled durations, not only their ratios.
- `fragment` shortens the expected sequence; a fragment of a longer quote is a
  valid declared transform.
- `rhythm-only` ignores pitch and compares duration sequences.
- `contour-only` ignores exact intervals and compares contour tokens:
  `R` repeated, `u1/u2/u3` up by 1–2 / 3–4 / ≥5 semitones, `d1/d2/d3` down.

## Undeclared matches

`remix check` also searches the whole library for a run of at least 8 intervals
that matches an undeclared source run. It requires the same duration sequence
and a minimum-information filter (at least 2 distinct intervals) to avoid
flagging repeated-note wallpaper. Undeclared matches are warnings by default;
`--fail-on-undeclared` makes them failures.

## Limits

- A declared quote that is not found is a warning by default;
  `--strict-quotes` makes it a failure.
- `literal_cap_bars` is a hard cap on an untransformed run.
- `quote_coverage`, `literal_share`, `novelty`, `source_diversity`, and
  `transform_mix` are numbers, not aesthetic judgements.
