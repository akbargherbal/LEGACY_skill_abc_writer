# OSTRIS licensing inventory

**Date:** 2026-11-23 · **Status:** inventory only. This is not a legal review and
it does not grant reuse rights.

The tools in `02_maqam-score/scripts/ostris/` are original code in this
repository. The **data** they consume comes from the project data root and is
not redistributed here: the cache under `analysis/out/ostris/source/` is
gitignored. Generated artifacts are derived statistics and short structural
fragments (intervals and rhythms), not copies of the source audio.

## Sources

| Source | What the tools read | Redistributed in git? | Licence status |
|---|---|---|---|
| `OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json` | 482-track inventory, titles, durations, URIs | Manifest is copied into the cache, not into git | **Unknown** — check the upstream dataset card before any redistribution |
| `DATASET/yt500_instrumental` + `TRANSCRIPTS/YT500` | ABC transcripts and YT500 metadata | Only derived records and a 1.8 MB canonical set; the audio is never downloaded | **Unknown** — YouTube-derived audio/transcripts; treat as project-internal |
| `TRANSCRIPTS/fadhl_shaker_selected_scores` and reference conditioner ABCs | 22 canonical scores | Derived records only | **Unknown** — project-internal transcriptions |
| `v3_arabmaqamrock_dataset_manifest.json` | 438 maqam labels, used only as a future cross-check | Counts only; labels are not written into records | **Unknown** — separate corpus; D4 forbids using it for priors/eval |
| 177-track `five_stars` calibration | Thresholds in `scripts/calibration.json` | Yes — numeric thresholds, already in the skill | Same status as the existing skill release |
| `arabmaqamrock` repository | Vendored `abc_tools.py` (`e99e5c…`) | Yes — code only | Follow the upstream repository's licence |

## What this means

1. **No licence claim is made.** The table records what is used and marks each
   data source unknown until its upstream terms are confirmed.
2. **Do not publish the cache or audio.** `analysis/out/ostris/source/`,
   `work/`, and the 2.95 GiB audio bundle stay out of git and out of any
   distribution.
3. **Generated statistics are low-risk but not cleared.** `records.jsonl`,
   priors, idioms, and the similarity index contain titles, track ids, and short
   interval/rhythm sequences. Treat them as project-internal until a reviewer
   signs off.
4. **Before a public release**, confirm the terms for the YT500, FADL Shaker,
   OSTRIS, v3, and five_stars sources, and record the result here. A release
   without that confirmation should ship only the skill code and the example
   fixture.
