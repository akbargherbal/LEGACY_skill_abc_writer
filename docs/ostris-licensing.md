# OSTRIS licensing inventory

**Date:** 2026-11-23 · **Status:** inventory only. This is not a legal review and
it does not grant reuse rights.

The tools in `02_maqam-score/scripts/ostris/` are original code in this
repository. The **data** they consume comes from the project data root. As of
the offline-bundle change, the lightweight inputs and the derived statistics are
copied into `02_maqam-score/data/ostris/` so the skill runs without the bucket.
That bundle is for **internal use on project machines only**; it is not cleared
for public redistribution.

## Sources

| Source | What the tools read | Bundled in the skill? | Licence status |
|---|---|---|---|
| `OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json` | 482-track inventory, titles, durations, URIs | Yes — the manifest is needed to rebuild inventory | **Unknown** — check the upstream dataset card before any redistribution |
| `DATASET/yt500_instrumental` + `TRANSCRIPTS/YT500` | ABC transcripts and YT500 metadata | ABC shards and metadata, not audio | **Unknown** — YouTube-derived audio/transcripts; treat as project-internal |
| `TRANSCRIPTS/fadhl_shaker_selected_scores` and reference conditioner ABCs | 22 canonical scores | Yes — reference ABCs | **Unknown** — project-internal transcriptions |
| `v3_arabmaqamrock_dataset_manifest.json` | 438 maqam labels, used only as a future cross-check | Manifest only; labels are not written into records | **Unknown** — separate corpus; D4 forbids using it for priors/eval |
| 177-track `five_stars` calibration | Thresholds in `scripts/calibration.json` | Yes — numeric thresholds | Same status as the existing skill release |
| `arabmaqamrock` repository | Vendored `abc_tools.py` (`e99e5c…`) | Yes — code only | Follow the upstream repository's licence |

## What this means

1. **No licence claim is made.** The table records what is used and marks each
   data source unknown until its upstream terms are confirmed.
2. **Internal package.** `02_maqam-score/data/ostris/` ships inside the skill zip
   for use on project machines. It contains titles, track ids, short
   interval/rhythm sequences, and the ABC text the tools parse.
3. **Audio stays out.** The 2.95 GiB audio bundle is never copied into the
   skill, the repository, or any package; the tools only read manifest metadata
   for it.
4. **`work/canonical/` stays out.** It is a second copy of the ABC text and is
   reproducible with `make ostris-build`; the bundle script omits it.
5. **Before a public release**, confirm the terms for the YT500, FADL Shaker,
   OSTRIS, v3, and five_stars sources and record the result here. A public
   release without that confirmation should ship only the skill code, the
   reference registry, and the example fixture — remove `data/ostris/` from the
   zip and rely on the reader commands' explicit `--out`/`--priors` flags.
