# OSTRIS M3 — objective priors and plan generation

**Date:** 2026-11-23 · **Stage:** M3 · **Gate:** PASS

M3 turns the M2 feature layer into sample-sized priors and uses the best
matching stratum to generate a score plan. It is **objective-only**: no maqam
label exists, so no prior is maqam-conditioned.

## Priors

Built from `records.jsonl`; duplicates and rows without features are excluded
(10 tracks).

| Item | Result |
|---|---|
| Records | 482 |
| Eligible | 472 |
| Excluded | 10 |
| Strata | 29 |
| Global strata | meter, tempo band, bars band, density band, section band, key mode |
| Interactions | meter×tempo and meter×mode when n ≥ 12 |
| Minimum stratum | 10 tracks; smaller cells are omitted |

Each stratum carries `n`, `excluded`, `confidence` (high ≥60, medium ≥25,
low ≥10), and a five-number summary plus mean for: bars, tempo, chords,
chords/bar, vocal/Ins notes, density, silence, span, median MIDI, distinct
durations, top-duration share, phrase median, section count, ties, and Ins
active share.

`select_prior` backs off in this order:

```
meter×tempo → meter×mode → meter → tempo → bars → mode → global
```

Every prior file records `maqam_conditioned: false`.

## Plan generation

`ostris plan --manifest song.json --out plans/song` writes:

| File | Contents |
|---|---|
| `brief.json` | request, assumptions, selected prior, section bars, targets, limits |
| `skill_plan.json` | the 15 targets `checker.py` requires, plus provenance |
| `plan.md` | human summary |

Derivation rules:

- `key`, `tempo`, `meter`, `bars` from the manifest when present;
  otherwise the prior median/top value, recorded as an assumption.
- With no `bars`, derive from `target_duration_s` and the meter/tempo, rounded
  to four bars.
- `syllables` = prior vocal-note median scaled to the requested bars ÷ 1.30,
  keeping notes/syllable inside the checker's sanity band.
- `melisma` 1.20–1.45; register mean/top from the prior; distinct durations,
  ties, and chords from the stratum's lower quartile, clamped to sane minima.
- Sections scale to `bars`; `section_bars` sums exactly.
- `maqam` is `null`; `maqam_conditioned` is `false`.

Gate: valid plan shape, sections sum, no maqam claim, and duration within ±10%
when a target duration was supplied.

## Verified

- 29 strata built; every stratum `maqam_conditioned: false`.
- Plan for a 180 s, 4/4, 100 BPM brief: 76 bars, 6 sections, 182.4 s planned
  (1.3% off), `meter-4_4_tempo-medium` (n=72, high confidence).
- Plan for the real 186-bar 2/4 track: valid shape, no hard failures when
  checked against its canonical score.

## Limits

- Priors describe this corpus, not a target style or a correctness bound.
- No maqam-conditioned priors until D3 has reviewed labels.
- Small strata are absent by design; callers must accept backoff.
