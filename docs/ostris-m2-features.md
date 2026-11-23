# OSTRIS M2 — deterministic features, no maqam labels

**Date:** 2026-11-23 · **Stage:** M2 (label-free) · **Gate:** PASS

M2 originally required a reviewed maqam label set. No expert review or labelled
source is available for the 482 tracks, so the plan was amended: M2 extracts
objective, reproducible features and adds a coarse **unreviewed** mode
hypothesis. It does **not** label maqam.

## What is extracted

Per track, from the canonical ABC:

- **Global:** bars, duration, key (tonic + mode), tempo and tempo band, meter
  timeline (`declared`, `changes`, `family`), section comment labels.
- **Vocal and Ins voices:** note count, density per bar, range, median pitch,
  rest bars / silence, interval histogram (steps, medium, leaps, repeats),
  duration distinct/median/top-share, phrase count and lengths.
- **Harmony:** chord count, unique symbols, chords per bar, root and quality
  histograms, top symbols.
- **Mode hypothesis:** coarse family anchored to the key tonic, pitch-class
  degree shares, third quality, augmented-second flag, template score, and
  alternatives.

The ABC has no lyric text, so prosody/syllable features are not extracted here;
they stay with the existing syllabifier.

## Mode hypothesis is not a label

`mode_hypothesis` is a 12-TET pitch-class template fit over four coarse families:

| Family | Interpretation |
|---|---|
| `major_like` | Ajam / Rast are indistinguishable in this dialect |
| `minor_like` | Nahawand / Bayati are indistinguishable in this dialect |
| `phrygian_like` | Kurd-like lowered second |
| `hijaz_like` | Augmented second between the second and third degrees |
| `unknown` | No usable notes |

It is anchored to the ABC `K:` tonic. The key is not the maqam tonic, so this
is a **key-relative** description, not a corpus maqam distribution. Every row
carries `reviewed: false` and `warning: "unreviewed heuristic; not a maqam
label"`. It is excluded from all gates and must not condition priors.

## Result

| Check | Result |
|---|---|
| Records with features | **482/482** |
| Records with a mode hypothesis | **482/482** |
| Named maqam labels | **0** |
| Feature failures | **0** |
| Key-relative families | minor_like 401 · phrygian_like 55 · major_like 25 · hijaz_like 1 |
| Third quality | minor 454 · major 26 · neutral 2 |
| Tempo bands | medium 220 · slow 139 · fast 123 |
| Bars | median 150, range 57–296 |
| Vocal notes | median 525, range 0–1064 |
| Chords | median 170, range 73–360 |

The family counts describe the key-relative pitch content of this corpus, not
maqam. A future reviewer can replace the hypothesis with labels without
changing the feature layer.

## Decisions

| Decision | Status |
|---|---|
| D3 maqam review | **Deferred** — no reviewer; `maqam` stays `null` |
| D4 438 v3 labels | **Cross-check only** on the separate v3 corpus; never training/priors/eval for the 482 |
| D11 177 labels | **Calibration only** |
| D12 maqam coverage | **Not applicable** until D3 exists |
| D16 sanity on 482 | **Generated scores only** |

The replacement gate is feature coverage, not maqam accuracy. This is recorded
in `docs/ostris-decisions.md` and in the plan's M2 section.

## Reproduce

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit
make ostris-build
make ostris-features
```

Outputs:

| File | Contents |
|---|---|
| `analysis/out/ostris/features.json` | Gate checks, feature coverage, families, shape, limitations |
| `analysis/out/ostris/features.md` | Human summary |
| `analysis/out/ostris/records.jsonl` | Per-track `features` and `mode_hypothesis`; `maqam` remains `null` |

## What M3 can do

M3 can build priors stratified by objective features: meter family, tempo band,
bars band, density band, section count, vocal range, and chord vocabulary. It
must record `maqam_conditioned: false` in every prior. Named-maqam priors remain
blocked until D3 has real reviewed labels.
