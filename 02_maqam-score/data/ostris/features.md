# OSTRIS M2 features

- Generated: `2026-11-23T09:19:03+00:00`
- Gate: **PASS**
- Features: 482/482
- Named maqam labels: **0** (not claimed)

## Mode hypothesis (unreviewed, key-anchored)

| Coarse family | Tracks |
|---|---:|
| minor_like | 401 |
| phrygian_like | 55 |
| major_like | 25 |
| hijaz_like | 1 |

| Third | Tracks |
|---|---:|
| minor | 454 |
| major | 26 |
| neutral | 2 |

## Shape

| Measure | n | min | median | max |
|---|---:|---:|---:|---:|
| bars | 482 | 57.0 | 150.0 | 296.0 |
| vocal_notes | 482 | 0.0 | 525.0 | 1064.0 |
| chords | 482 | 73.0 | 170.0 | 360.0 |

## Checks

| Check | Required | OK | Detail |
|---|---|---|---|
| feature_coverage | yes | yes | 482/482 feature rows |
| mode_hypothesis_coverage | yes | yes | 482/482 mode rows |
| no_maqam_claim | yes | yes | 0 records carry a maqam label (must be 0) |
| contract_pin | yes | yes | skill 0.2.0 pins match: scripts/checker.py=ok, scripts/calibration.json=ok, scripts/abc_tools.py=ok |

## Limits

- No expert maqam review is available for the 482-track corpus.
- mode_hypothesis is a coarse, unreviewed 12-TET template fit; it is not a maqam label.
- Mode families are anchored to the ABC key tonic; this is not a corpus maqam distribution.
- Ajam/Rast and Nahawand/Bayati are not separable in this ABC dialect.
- The 438 v3 labels are a separate corpus and are only a weak cross-check, never priors or eval.
- The 177 five_stars labels are prompts/calibration, not ground truth.
