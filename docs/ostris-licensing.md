# OSTRIS licensing inventory

**Date:** 2026-11-23 · **Status:** inventory only. This is not a legal review and
it does not grant reuse rights.

The tools in `02_maqam-score/scripts/ostris/` are original code in this
repository. The **data** they consume comes from the project data root. Only the
**derived** statistics and short idiom rows are copied into
`02_maqam-score/data/ostris/`, so the skill runs without the bucket. Those
artifacts carry no ABC text. The raw inputs under `source/` are fetched on
demand with `sync` and are part of neither the repository nor the package (see
`02_maqam-score/data/README.md`, "Regenerating `source/`"). The bundled snapshot
is for **internal use on project machines only**; it is not cleared for public
redistribution.

## Sources

| Source | What the tools read | Bundled in the skill? | Licence status |
|---|---|---|---|
| `OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json` | 482-track inventory, titles, durations, URIs | No — `sync` fetches it into a rebuild cache only | **Unknown** — check the upstream dataset card before any redistribution |
| `DATASET/yt500_instrumental` + `TRANSCRIPTS/YT500` | ABC transcripts and YT500 metadata | No — `sync` only; derived intervals/rhythms ship, not the ABC shards | **Unknown** — YouTube-derived audio/transcripts; treat as project-internal |
| `TRANSCRIPTS/fadhl_shaker_selected_scores` and reference conditioner ABCs | 22 canonical scores | No — `sync` only; `idioms.jsonl` carries derived interval/rhythm rows, not ABC | **Unknown** — project-internal transcriptions |
| `v3_arabmaqamrock_dataset_manifest.json` | 438 maqam labels, used only as a future cross-check | No — `sync` only; labels are not written into records | **Unknown** — separate corpus; D4 forbids using it for priors/eval |
| 177-track `five_stars` calibration | Thresholds in `scripts/calibration.json` | Yes — numeric thresholds | Same status as the existing skill release |
| `arabmaqamrock` repository | Vendored `abc_tools.py` (`e99e5c…`) | Yes — code only | Follow the upstream repository's licence |

## What this means

1. **No licence claim is made.** The table records what is used and marks each
   data source unknown until its upstream terms are confirmed.
2. **Internal package.** `02_maqam-score/data/ostris/` ships inside the skill zip
   for use on project machines. It contains titles, track ids, derived features,
   and short interval/rhythm sequences; it carries no ABC text.
3. **Audio stays out.** The 2.95 GiB audio bundle is never copied into the
   skill, the repository, or any package; the tools only read manifest metadata
   for it.
4. **`work/canonical/` and `source/` stay out.** The first is a second copy of
   the ABC text; the second is the raw input. Both are reproducible
   (`make ostris-sync`, `make ostris-build`) and the bundle script omits them.
5. **Before a public release**, confirm the terms for the YT500, FADL Shaker,
   OSTRIS, v3, and five_stars sources and record the result here. A public
   release without that confirmation should ship only the skill code, the
   reference registry, and the example fixture — remove `data/ostris/` from the
   zip and rely on the reader commands' explicit `--out`/`--priors` flags.
