# docs — index

## Active

| File | Role |
|---|---|
| `constraints-calibration.md` | Full evidence report: 177 tracks, every number, verdicts, what is unverified |
| `numbers-provenance.md` | Short entry point to the in-skill registry |
| `implementation-plan-constraints.md` | Execution plan M0–M7 + implementation status |
| `ostris-score-tools-plan.md` | OSTRIS score-tools plan (482 instrumental corpus); M0–M5 implemented, M6 objective half |
| `ostris-decisions.md` | Resolved decisions D1–D16, M2 amendment, M3–M6 resolutions, pinned hashes |
| `ostris-m0-audit.md` | M0 result: verified inventory, link/parse coverage, FADL finding, corpus shape |
| `ostris-m1-ingest.md` | M1 result: canonical ABC build, preservation of `M:`/`[K:...]`, contract checks |
| `ostris-m2-features.md` | M2 result: deterministic features and an unreviewed mode hypothesis; no maqam labels |
| `ostris-m3-priors-plan.md` | M3 result: objective priors, backoff, `brief.json` + `skill_plan.json` |
| `ostris-m4-idioms-check.md` | M4 result: structural idiom bank, k-gram similarity, combined `check` |
| `ostris-m5-m6-integration-eval.md` | M5/M6 result: CLI, wrapper, held-out split, objective metrics and what was not measured |
| `ostris-implementation-checklist.md` | Phase-by-phase progress: what is done, partial, deferred, and next |
| `ostris-licensing.md` | Data/source inventory; licence status unknown, no clearance claimed |
| `suno-dataset-migration-plan.md` | Plan (rev 2): swap only the remixer's verbatim material library to `data/SUNO_ABC_SCORE_DATASET.pkl`; keep the OSTRIS aggregate priors/idioms/similarity and the 177 calibration unchanged; public archive now carries the open-source SUNO store |
| `ostris-handoff.md` | Handoff: frozen contracts, how to add reviewed labels, reproduce commands |
| `ostris-release-notes.md` | Tools v0.4.0: included commands, verified numbers, upgrade notes |
| `remixer_proposal.md` | Proposal: turn the skill into a library-aware remixer with capped retrieval, declared quotes, and verification |
| `remixer-implementation-plan.md` | Execution plan for `abc_remixer`: store, catalog, slice, songmap, motif-find, remix check, packaging, tests |
| `remixer-implementation-report.md` | 0.1.0 implementation result: counts, tests, package, limitations |
| `agent-eval-protocol.md` | Drop-folder agent evaluation: intake, task battery, rubric, confusion & token-waste audit, post-mortem → skill change |
| `0.4.0-remaining-fixes-plan.md` | 0.4.0 implementation plan (applied): anti-anchoring, strict shape, tessitura, style tags, phrase sidecar |

## Baseline / input

| File | Role |
|---|---|
| `constraints_inventory.md` | Claude Code's inventory of the v1 constraints; the problem statement this work answers |

## Separate evaluation

| File | Role |
|---|---|
| `rag-abc-model-evaluation.md` | ABC/RAG model evaluation; not part of the constraint calibration |

## Archive

| File | Role |
|---|---|
| `archive/scripts.zip` | Claude Code's scripts that reproduced the v1 inventory; superseded by `analysis/calibrate_177.py` for the 177-track calibration |

The canonical number registry is **`02_maqam-score/references/numbers.md`**;
the machine-readable copy is **`02_maqam-score/scripts/calibration.json`**.

## Offline bundle

The corpus artifacts ship inside the skill under
`02_maqam-score/data/ostris/`, so `plan`, `exemplar`, `similarity --score` and
`check` run with no bucket and no flags (`make offline-check`). Phase reports
below keep their original `DATA_ROOT=gs://…` commands as a record of how the
evidence was produced; refreshing the bundle is the only remaining bucket step
(`make ostris-sync … && make ostris-bundle`).
