# OSTRIS M3 priors (objective features only)

- Generated: `2026-11-23T09:25:31+00:00`
- Gate: **PASS**
- Eligible tracks: 472 / 482
- Excluded: 10 (duplicates, unparsed, no features)
- Strata: 29
- Maqam-conditioned: **no** (no reviewed labels exist)

## Global shape

| Metric | n | min | p10 | median | p90 | max |
|---|---:|---:|---:|---:|---:|---:|
| bars | 472 | 57.0 | 91.1 | 150.0 | 210.9 | 296.0 |
| tempo | 472 | 57.0 | 70.0 | 90.0 | 133.0 | 158.0 |
| chords | 472 | 73.0 | 112.0 | 170.0 | 234.0 | 360.0 |
| chords_per_bar | 472 | 0.8359 | 0.9929 | 1.0964 | 1.4918 | 1.9467 |
| vocal_notes | 472 | 0.0 | 352.1 | 526.0 | 721.9 | 1064.0 |
| ins_notes | 472 | 10.0 | 132.1 | 232.5 | 405.9 | 1269.0 |
| density | 472 | 0.0 | 2.328 | 3.6123 | 5.5258 | 8.1831 |
| silence | 472 | 0.0455 | 0.2273 | 0.3311 | 0.4409 | 1.0 |
| span_semitones | 471 | 7.0 | 10.0 | 14.0 | 19.0 | 28.0 |
| median_midi | 471 | 66.0 | 69.0 | 72.0 | 78.0 | 81.0 |
| distinct_durations | 472 | 0.0 | 3.0 | 4.0 | 6.0 | 9.0 |
| top_duration_share | 471 | 0.4244 | 0.5057 | 0.6711 | 0.8598 | 0.9646 |
| phrase_median_bars | 471 | 1.0 | 13.0 | 32.0 | 59.0 | 105.0 |
| sections | 450 | 3.0 | 6.0 | 9.0 | 11.0 | 18.0 |
| ties | 472 | 0.0 | 0.0 | 2.0 | 15.0 | 108.0 |
| ins_active_share | 472 | 0.0215 | 0.2055 | 0.3063 | 0.4347 | 0.9752 |

## Strata

| Stratum | n | Confidence |
|---|---:|---|
| `bars-long` | 130 | high |
| `bars-medium` | 211 | high |
| `bars-short` | 131 | high |
| `density-busy` | 179 | high |
| `density-light` | 20 | low |
| `density-medium` | 273 | high |
| `global` | 472 | high |
| `meter-2_4` | 164 | high |
| `meter-2_4_mode-minor` | 156 | high |
| `meter-2_4_tempo-medium` | 77 | high |
| `meter-2_4_tempo-slow` | 86 | high |
| `meter-4_4` | 169 | high |
| `meter-4_4_mode-minor` | 158 | high |
| `meter-4_4_tempo-fast` | 78 | high |
| `meter-4_4_tempo-medium` | 72 | high |
| `meter-4_4_tempo-slow` | 19 | low |
| `meter-mixed` | 131 | high |
| `meter-mixed_mode-minor` | 125 | high |
| `meter-mixed_tempo-fast` | 37 | medium |
| `meter-mixed_tempo-medium` | 62 | high |
| `meter-mixed_tempo-slow` | 32 | medium |
| `mode-major` | 25 | medium |
| `mode-minor` | 447 | high |
| `sections-many` | 291 | high |
| `sections-mid` | 155 | high |
| `sections-unknown` | 22 | low |
| `tempo-fast` | 122 | high |
| `tempo-medium` | 213 | high |
| `tempo-slow` | 137 | high |

## Limits

- Priors are conditioned on objective features only; no maqam labels exist.
- Strata below ten tracks are omitted; callers must use the backoff chain.
- Quantiles describe this corpus, not a target style or a correctness bound.
