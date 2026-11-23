# skill_abc_writer

Source of the **`maqam-score`** skill and the 177-track calibration that
justifies its numbers.

**Version:** 0.2.0 (skill contract) · tools 0.3.0 · offline corpus bundle ·
**Date:** 2026-11-23

## Layout

| Path | What it is | Status |
|---|---|---|
| `02_maqam-score/` | Skill source: `SKILL.md`, scripts, references, example, tests | **active source** |
| `02_maqam-score/scripts/ostris/` | OSTRIS corpus tools (M0–M6: sync, audit, build, features, priors, plan, idioms, similarity, check, eval) | **active** |
| `02_maqam-score/data/ostris/` | Packaged corpus artifacts: source cache, records, priors, idiom bank, similarity index, eval split | **bundled, ships in the zip** |
| `02_maqam-score/schemas/` | JSON contracts for records, priors, plans, reports, eval | **active** |
| `dist/abc_score_writer.zip` | Built skill package | **build artifact** |
| `analysis/` | Calibration scripts (`calibrate_177.py`, `test_checker_corpus.py`) | **active** |
| `analysis/out/` | Regeneration workspace: `summary.json`, `tracks.jsonl`, `ostris/` | **generated, reproducible** |
| `docs/` | Reports, plans, baseline inventory | **active docs** |
| `docs/archive/` | Inputs that served their purpose | **frozen** |

The skill source is the truth; `dist/abc_score_writer.zip` is rebuilt with
`make zip`. The old v1 zip lives in git history.

## Quick start

```bash
make selftest        # the example passes; the dialect is enforced
make test            # unit tests
make offline-check   # the corpus tools run on the bundled data, no flags
make check-corpus    # 177/177 parse, 175/177 hard (98.9%)
make zip             # build dist/abc_score_writer.zip
```

## OSTRIS corpus tools

The 482-track instrumental corpus is processed once from the project data root.
**The results ship inside the skill** under `02_maqam-score/data/ostris/`, so the
skill needs no bucket, no network and no flags at use time:

| Command | Reads from the bundle |
|---|---|
| `plan` | `priors/priors.json` |
| `exemplar` | `idioms.jsonl` |
| `similarity --score` | `similarity/index.json` |
| `check` | `priors/` and `similarity/` (optional enrichment) |
| `audit`, `build`, `features`, `priors`, `idioms`, `eval --build-split` | `source/`, `records.jsonl` |

The bundle is ~13 MB raw / ~1.9 MB compressed. It holds the lightweight inputs
(manifests, YT500 ABC shards, FADL album JSONs and reference ABCs) and the
generated statistics; the **2.95 GiB audio bundle is never included**.

Refreshing the corpus is the only step that touches the bucket:

```bash
DATA_ROOT=gs://<bucket> make ostris-sync   # refresh analysis/out/ostris/source
make ostris-audit          # M0: inventory, links, parse, records
make ostris-build          # M1: canonical ABC, contract pin check
make ostris-features       # M2: objective features + unreviewed mode hypothesis
make ostris-online         # M3-M6: priors, idioms, similarity index, eval split
make ostris-bundle         # snapshot analysis/out/ostris into the skill
make zip                   # rebuild the package with the new snapshot
```

`ostris-bundle` copies only the artifacts the tools read; `work/canonical/` is
reproducible with `make ostris-build` and is left out.

Per song:

```bash
scripts/ostris_cli.py plan  --manifest song.json --out plans/song
scripts/ostris_cli.py exemplar --function cadence --bars 2
scripts/ostris_cli.py check score.abc --plan plans/song/skill_plan.json --report report.json
```

Outputs under `analysis/out/ostris/`: `audit.json`, `audit.md`,
`manifest_links.csv`, `records.jsonl`, `held_out.jsonl`, `canonical.json`,
`canonical.md`, `features.json`, `features.md`, `priors/`, `idioms.jsonl`,
`similarity/`, `eval/`, plus the gitignored `work/canonical/abc/` set. The
source cache (`analysis/out/ostris/source/`) and `work/` are regeneration
scratch. `make ostris-bundle` snapshots the shippable subset into
`02_maqam-score/data/ostris/`. Only lightweight manifests, YT500 ABC shards,
FADL album JSONs, and reference ABCs are pulled; the 2.95 GiB audio bundle is
never downloaded.

M1 decisions D5/D6/D7/D9/D14 are recorded in `docs/ostris-decisions.md`; the
result is `docs/ostris-m1-ingest.md`. No expert maqam review is available, so
M2 is label-free: `maqam` stays `null` and the coarse `mode_hypothesis` is
unreviewed. M3–M6 are objective-only: priors record `maqam_conditioned: false`,
`check` has no maqam-fit score, and `eval` does not claim quality. See
`docs/ostris-m2-features.md`, `docs/ostris-m3-priors-plan.md`,
`docs/ostris-m4-idioms-check.md`, and
`docs/ostris-m5-m6-integration-eval.md`.

The phase-by-phase status, including what is partial or deferred, is
`docs/ostris-implementation-checklist.md`. Licensing is inventoried, not
cleared: `docs/ostris-licensing.md`.

## Where the numbers come from

- Human registry: `02_maqam-score/references/numbers.md`
- Machine-readable: `02_maqam-score/scripts/calibration.json`
- Full analysis: `docs/constraints-calibration.md`
- Raw distributions: `analysis/out/summary.json`

**Rule:** every hard gate passes ≥95% of the 177 good scores. The six sanity
guards pass **175/177 = 98.9%**; everything else is a warning or a prior.

## Docs map

See `docs/README.md`.
