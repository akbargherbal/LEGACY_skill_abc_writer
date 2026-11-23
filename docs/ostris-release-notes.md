# OSTRIS release notes — tools v0.3.0

**Date:** 2026-11-23 · **Skill:** `maqam-score` v0.2.0 · **Python:** 3.11+
standard library only (tests optionally use `jsonschema`)

## Included

| Stage | Command | Output |
|---|---|---|
| M0 | `audit` | `audit.json`, `manifest_links.csv`, `records.jsonl`, `held_out.jsonl` |
| M1 | `build` | `canonical.json`, canonical ABC work set |
| M2 | `features` | `features.json`, per-track `features` + unreviewed `mode_hypothesis` |
| M3 | `priors` | `priors/priors.json`, 29 objective strata, per-stratum files |
| M3 | `plan` | `brief.json`, `skill_plan.json` (the 15 checker targets) |
| M4 | `idioms` | `idioms.jsonl` (1,304 structural phrases) |
| M4 | `similarity` | `similarity/index.json`, query on a score |
| M4 | `check` | `report.json` with nested `skill_report`, prior percentile, similarity |
| M5 | wrapper | `scripts/ostris_cli.py`, `SKILL.md` §8 |
| M6 | `eval` | `eval/split.json` (14 generation + 17 retrieval); `eval/report.json` when runs are supplied |

## Offline bundle (this build)

- The corpus artifacts ship inside the skill at `02_maqam-score/data/ostris/`
  (~13 MB raw, ~1.9 MB compressed) and are included in the zip.
- `plan`, `exemplar`, `similarity --score`, and `check` default to that directory:
  no flags, no bucket, no network.
- The regeneration commands (`audit`, `build`, `features`, `priors`, `idioms`,
  `eval --build-split`) also default to the bundled `source/`, so the corpus can
  be rebuilt offline.
- `sync` is refresh-only; `make ostris-bundle` snapshots `analysis/out/ostris/`
  back into the skill after a refresh.
- Not bundled: the 2.95 GiB audio (never read) and `work/canonical/`
  (reproducible with `make ostris-build`).

## Verified

- 482/482 linked, canonical, parsed, and featured.
- 472/482 eligible for priors; 10 duplicates excluded.
- 29 strata; every one records `maqam_conditioned: false`.
- 1,304 idioms across 481 tracks; one track has no vocal notes.
- 1,304 indexed idioms, 3,714 interval grams.
- Held-out split: 31 usable, 4 without ABC, 14 generation + 17 retrieval.
- **38 unit tests pass**; `make selftest` passes; `make offline-check` passes;
  contract pins match.
- End-to-end on a real canonical track: contract+sanity pass, 5 style warnings,
  similarity run 11.

## Not included, on purpose

- No maqam labels, coverage, accuracy, or maqam-conditioned priors (D3/D12).
- No maqam-fit score in `check`; the field says `available: false`.
- No blind quality evaluation and no measured token reduction (D1/D2 need a
  judge and model instrumentation).
- No audio download and no tar sidecars.

## Upgrade notes

- `mode_hypothesis` and `ties` were added to M2. Re-run `features` before
  `priors`; older records without `ties` fall back to zero.
- `check` expects `skill_plan.json`, not `brief.json`.
- `similarity` writes JSON, not `.npz`, because the tools stay dependency-free.
- Pinned hashes are unchanged: checker `bd3645…`, calibration `c5cd51…`,
  parser `e99e5c…`.
