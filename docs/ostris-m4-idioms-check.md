# OSTRIS M4 — idioms, similarity, and combined check

**Date:** 2026-11-23 · **Stage:** M4 · **Gate:** PASS for the objective subset;
maqam-fit is explicitly unavailable.

## Idiom bank

`ostris idioms` extracts 2–4 bar vocal phrases from the canonical ABC. Phrase
boundaries are bar gaps, not semantics. Functions are structural:

| Function | Rule | Idioms |
|---|---|---|
| `opening` | first phrase of the track | part of 1,304 |
| `cadence` | last phrase of the track | part of 1,304 |
| `phrase` | one middle phrase | part of 1,304 |

Result: **1,304 idioms across 481 tracks**; one track has no vocal notes.
Every row has `reviewed: false` and says it is not a maqam label. Each row
stores intervals, durations, contour, start/end scale degree, bar range, key,
and tonic. `ostris exemplar --function cadence --bars 2` returns a few.

## Similarity

`ostris similarity --build` creates an interval k-gram index (k=3,4) over the
idiom bank, then `--score score.abc` returns the top matches, the longest shared
contiguous run, and a quotation flag when the run is at least 8 intervals.

| Item | Result |
|---|---|
| Indexed idioms | 1,304 |
| Distinct grams | 3,714 |
| Index size | 1.6 MB JSON |

The index is JSON rather than the plan's `.npz` because the tools stay
standard-library only. This is a documented deviation, not a numerical claim.

## Combined check

`ostris check score.abc --plan skill_plan.json --report report.json`:

1. validates the 15 key plan shape;
2. runs the pinned `checker.py` as a subprocess (no reimplementation);
3. nests its report under `skill_report` (D10);
4. adds prior percentiles for six measured metrics;
5. adds similarity and quotation;
6. always reports `maqam_fit.available: false`.

Gate policy (D8): `contract`, `sanity`, and `structure` are hard; `style` stays a
warning unless `--strict-style`. `pass` means no hard failure, not zero warnings.

Real run on `yt500-0001` with a generated plan:

| Result | Value |
|---|---|
| Hard failures | 0 |
| Style warnings | 5 (duration spread, ties floor/target, chords, sections) |
| Prior | `meter-2_4_tempo-slow` (n=86), chords/bar percentile 36.5 |
| Similarity | max shared run 11 |
| maqam fit | unavailable |

## Limits

- Functions are positional, not semantic; a cadence phrase is the last phrase.
- Shared intervals are not evidence of quotation by themselves.
- Idioms are unreviewed and must not be called maqam examples.
- The maqam-fit component stays unavailable until reviewed labels exist.
