# OSTRIS plan — implementation checklist

**Snapshot:** 2026-11-23 · **Repo:** `skill_abc_writer` · **Skill:** v0.2.0
**Tools:** 0.3.0 · **Overall:** M0–M5 implemented; M6 objective half implemented;
M7 documented and in CI. Named-maqam work stays deferred.
Implementation commit `ecde347`, pushed to `origin/main`; earlier `7ffae22`,
`3115daa`.
**Last verified:** 38 tests pass, `make selftest` and `make offline-check` pass,
contract pins match, `dist/02_maqam-score.zip` rebuilt with the bundled data.

Legend: ✅ done · 🟡 partial · ⏳ not started · ⏸️ deferred/blocked.
The source plan is `docs/ostris-score-tools-plan.md`; decisions are in
`docs/ostris-decisions.md`.

## At a glance

| Phase | Plan scope | Status | Gate |
|---|---|---|---|
| **M0** Audit & contracts | Links, audit, schemas, inventory re-check | ✅ done | PASS |
| **M1** Ingest & canonicalize | Canonical ABC, FADL links, records + provenance | ✅ done with deviations (no tar sidecars) | PASS |
| **M2** Features & labels | Features, maqam, mood, prosody | 🟡 label-free subset | PASS (amended) |
| **M3** Priors & plan | Quantiles, backoff, `brief.json` + `skill_plan.json` | ✅ done, objective-only | PASS |
| **M4** Idioms, similarity, check | Idiom bank, k-gram index, combined `check` | ✅ done; maqam-fit unavailable | PASS for objective subset |
| **M5** Integration | `ostris check`, TOOLS section, wrapper | ✅ CLI-level | PASS (CLI roundtrip) |
| **M6** Evaluation | Held-out A/B, quality + token metrics | 🟡 split + objective metrics; mechanics smoke-tested | PASS (objective half, no generated runs) |
| **M7** Hardening & handoff | Licensing, CI, release | 🟡 docs, CI, notes; no clearance/tag | not a gate |

## M0 — Audit & contracts ✅

- [x] `manifest_links.csv`: 482 rows (460 YT500 + 22 FADL), missing list included
- [x] `audit.json`: parse status, bars, chords, duration mismatch, duplicates, quality flags
- [x] `track_record` schema v1 and `audit` schema v1
- [x] Fixtures + tests (`OstrisFixture`, parse/link/duplicate/schema tests)
- [x] Inventory re-verified: 482 library, 495 YT500, 35 held-out, 438 v3, 3,162,110,202 bytes / 36.6 h
- [x] Duplicate inventory: 5 groups / 10 tracks
- [x] Missing list with a decision: 4 YT500 tracks without ABC, all held out
- [x] Gate: 482/482 matched, 482/482 parsed (100%)
- [x] Extra evidence: `held_out.jsonl`, duplicate groups, quality flags

**Result:** `docs/ostris-m0-audit.md`.

## M1 — Ingest & canonicalize ✅

- [x] Manifests and YT500 ABC shards copied to the local cache
- [x] FADL shortlist + selected-score transcripts + reference conditioner ABCs copied
- [ ] Sample `tar.gz` download — **not done, intentionally**. The shard JSON carries the ABC; the 2.95 GiB bundle was not downloaded.
- [x] `score.abc` content extracted from the shard JSON
- [ ] Tar sidecars / `structure.lab` — **not extracted**. M2 uses the manifest `sections` count and ABC comment labels.
- [x] Canonical ABC, structural normalization only
- [x] Per-bar `M:` and inline `[K:...]` preserved (D9)
- [x] `L`/`Q` preserved as written
- [x] FADL linking: 22/22, selected transcript preferred, reference as fallback
- [x] `records.jsonl` with per-field provenance and a `canonical` object
- [x] Gate: 482/482 canonical and re-parsed; 1.84 MB; unique hashes
- [x] D7/D14 contract pins checked by `ostris contract`

**Result:** `docs/ostris-m1-ingest.md`.

## M2 — Features & labels 🟡

### Done

- [x] Bars, duration, key, tempo, tempo band
- [x] Meter timeline: declared meters, change count, family
- [x] Section count (manifest) + section comment labels
- [x] Melody/rhythm: density, range, median pitch, intervals, durations, phrases
- [x] Harmony: chord count, vocabulary, per-bar rate, roots, qualities
- [x] Ties per track (M3 uses them as a prior)
- [x] Objective feature rows: **482/482**
- [x] Unreviewed `mode_hypothesis`: **482/482**, `reviewed: false`, key-anchored
- [x] Zero named-maqam claims: `maqam: null` on **482/482**
- [x] Replacement gate: **PASS**

### Not done

- [ ] Full form/structure spans from `structure.lab` (no sidecars downloaded)
- [ ] Prosody features (no lyric text in the ABC; the syllabifier owns this)
- [ ] Maqam classifier + manual review — **deferred** with D3
- [ ] Maqam coverage/accuracy reporting — **not applicable** until D3
- [ ] Mood tags + 50-track lexicon review — **not done**

**Result:** `docs/ostris-m2-features.md`.

## M3 — Priors & plan ✅

- [x] Priors by objective stratum: meter, tempo, bars, density, sections, mode
- [x] Two interactions (meter×tempo, meter×mode) when n ≥ 12
- [x] Quantiles (p10/p25/median/p75/p90), `n`, and confidence per stratum
- [x] Backoff: meter×tempo → meter×mode → meter → tempo → bars → mode → global
- [x] `ostris plan`: `brief.json` + `skill_plan.json` (15 checker keys)
- [x] Assumptions recorded when key/tempo/meter/bars come from the prior
- [x] Sections scale to `bars`; `section_bars` sums exactly
- [x] Duration target within ±10%
- [x] Plan fixtures and a `plan → score → check` roundtrip covered by tests
- [x] Gate: **PASS** — 29 strata, 472 eligible, every plan valid
- [x] Every prior records `maqam_conditioned: false`
- [ ] Named-maqam priors — **blocked by D3/D12**

**Result:** `docs/ostris-m3-priors-plan.md`.

## M4 — Idioms, similarity, check ✅

- [x] Structural idiom bank, 2–4 bars: opening / phrase / cadence
- [x] 1,304 idioms across 481 tracks; every row `reviewed: false`
- [x] Interval k-gram index (k=3,4): 1,304 idioms, 3,714 grams
- [x] `similarity --score` returns matches, longest shared run, quotation flag
- [x] `ostris check` combines checker + priors + similarity
- [x] Report nests the checker under `skill_report` (D10)
- [x] Gate policy D8: contract/sanity/structure hard; style WARN
- [x] Maqam-fit component: **marked unavailable** (no labels)
- [x] Gate: a matching score passes and a bars mismatch fails
- [ ] Three labelled good/medium/bad scores — **partial**: good and bad are covered, “medium” needs a quality label
- [ ] Maqam-conditioned idioms — **blocked by D3**

**Result:** `docs/ostris-m4-idioms-check.md`.

## M5 — Integration ✅

- [x] Skill v0.2.0 pinned (checker `bd3645…`, calibration `c5cd51…`)
- [x] Vendored parser pinned (`abc_tools.py` `e99e5c…`)
- [x] `ostris check` passes `--require-final-rest` to the checker
- [x] `TOOLS`/corpus section in `SKILL.md` (three online commands)
- [x] Wrapper `scripts/ostris` that runs on CPU from any directory
- [x] D6 enforced: plans emit `vocal+ins`; `check` consumes only that plan
- [x] Gate: CLI roundtrip `plan → score → check` covered by tests, including the final-rest failure
- [ ] A live composition session outside CI — **not run**

**Result:** `docs/ostris-m5-m6-integration-eval.md`.

## M6 — Evaluation 🟡

- [x] Natural held-out set identified: 35 YT500 tracks not in the library
- [x] Usable subset measured: 4 without ABC, leaving **31**
- [x] Reserve 14 for generation / 17 for retrieval (D13)
- [x] `eval --build-split` writes a deterministic disjoint split
- [x] `eval --runs` scores supplied runs: class, contract+sanity, bars delta, size
- [x] Mechanics smoke-tested on one canonical track: contract+sanity 1/1, bars delta 0
- [ ] Generated held-out runs — **not produced**; the smoke run is not a model output
- [ ] A/B prompt-only vs tool-assisted — **not run**
- [ ] Blind quality / non-inferiority — **not measured** (no judge)
- [ ] Token reduction — **not measured** (`tokens_proxy` only)

**Result:** `docs/ostris-m5-m6-integration-eval.md`.

## M7 — Hardening & handoff 🟡

- [x] Docs for M0–M6
- [x] Provenance: source URIs, hashes, contract pins, limitations
- [x] Reproducible build: `make ostris-sync / audit / build / features / online`
- [x] Unit tests: **30 passing**; `make selftest` passes
- [x] CI on Python 3.11/3.12: tests, selftest, contract pins
- [x] Licensing **inventory** (`docs/ostris-licensing.md`)
- [x] Release notes for tools v0.3.0
- [x] Handoff notes for a future reviewer (`docs/ostris-handoff.md`)
- [x] Eight JSON schemas: record, audit, canonical, features, priors, plan, report, eval
- [ ] Licence clearance for the data sources — **unknown, needs the owner**
- [ ] Public release / git tag — **not created**

## Decisions

| # | Topic | Status |
|---|---|---|
| D1 | Final quality target | 🔶 ABC only; no audio judge |
| D2 | Held-out function | ✅ 14 generation + 17 retrieval |
| D3 | Maqam review | ⏸️ deferred — no reviewer |
| D4 | 438 v3 labels | ✅ cross-check only |
| D5 | Plan schema | ✅ `brief.json` + `skill_plan.json` |
| D6 | Instrumental voices | ✅ `Vocal+Ins` only in v1 |
| D7 | Skill contract | ✅ v0.2.0 + hashes + `--require-final-rest` |
| D8 | Gate policy | ✅ contract+sanity hard; style WARN |
| D9 | Variable meter | ✅ preserve `M:`/`[K:...]` |
| D10 | `report.json` merge | ✅ nested `skill_report` + `class` |
| D11 | 177 role | ✅ calibration only |
| D12 | Maqam coverage | ⏸️ N/A until D3 |
| D13 | Held-out source | ✅ 35 YT500, 14/17 split |
| D14 | Parser | ✅ vendored + pinned |
| D15 | Final rest | ✅ WARN + `--require-final-rest` |
| D16 | Sanity on 482 | ✅ generated scores only |

## CLI surface

| Command | Status |
|---|---|
| `sync` | ✅ lightweight cache |
| `audit` | ✅ M0 |
| `build` | ✅ M1 |
| `features` | ✅ M2 |
| `priors` | ✅ M3 |
| `plan` | ✅ M3 |
| `idioms` | ✅ M4 |
| `exemplar` | ✅ M4 |
| `similarity` | ✅ M4 (build + query) |
| `check` | ✅ M4/M5 |
| `eval` | ✅ M6 (split + runs) |
| `contract` | ✅ hash verification |
| `state` | ⏳ not implemented |
| `search` | ⏳ optional, not implemented |

Entry point: `python3 02_maqam-score/scripts/ostris_cli.py <command>`.

## Artifacts

The shippable artifacts are bundled under `02_maqam-score/data/ostris/` and
included in `dist/02_maqam-score.zip`; `analysis/out/ostris/` is the
regeneration workspace. The reader commands default to the bundle.

| Artifact | Status |
|---|---|
| `records.jsonl` | ✅ 482 rows; canonical + features + ties |
| `manifest_links.csv` | ✅ 482 rows |
| `audit.json` / `audit.md` | ✅ M0 |
| `canonical.json` / `canonical.md` | ✅ M1 |
| `features.json` / `features.md` | ✅ M2 |
| `held_out.jsonl` | ✅ 35 rows |
| `priors/priors.json` + 29 strata | ✅ M3 |
| `brief.json` / `skill_plan.json` | ✅ M3, generated per manifest |
| `idioms.jsonl` / `idioms.json` | ✅ M4 (1,304 rows) |
| `similarity/index.json` | ✅ M4 (1.6 MB) |
| `report.json` from `check` | ✅ M4 |
| `eval/split.json` | ✅ M6 (31 usable, 14/17) |
| `eval/report.json` | ✅ on demand from `eval --runs` (objective metrics only) |
| `schemas/*.json` | ✅ 8 contracts: record, audit, canonical, features, priors, plan, report, eval |

## Verified numbers

- [x] 482 library tracks = 460 YT500 + 22 FADL
- [x] 495 YT500 transcripts; 460 used; 35 held out
- [x] 35 held out; 4 without ABC; **31 usable**; 14 generation + 17 retrieval
- [x] 438 v3 labels, excluded from priors/eval (D4)
- [x] 2.95 GiB / 36.6 h audio inventory
- [x] 5 duplicate groups / 10 tracks; 10 excluded from priors
- [x] 22 FADL shortlist; 24 selected-score tracks, 23 with ABC
- [x] 482/482 parse, canonical, and feature coverage
- [x] 472/482 eligible for priors; 29 strata
- [x] 1,304 idioms; 3,714 interval grams
- [x] 0 named-maqam claims; 0 maqam-conditioned priors
- [x] 8 schemas parse; generated artifacts validate against them
- [x] 38 tests pass; `make selftest` and `make offline-check` pass; contract pins
  match; zip rebuilt with `data/ostris/`

## Deviations from the plan

1. **No separate repository.** The tools live in the skill.
2. **No audio bundle.** Only lightweight manifests/ABCs are cached.
3. **No M1 tar/sidecar extraction.** The shard JSON already contains the ABC.
4. **Canonicalization is structural.** `L`/`Q`/`M:`/`[K:...]` are preserved.
5. **M2 is label-free.** No maqam labels, mood tags, or prosody; the gate was amended.
6. **FADL source corrected.** Selected scores + reference conditioner, not the 15-album set.
7. **Similarity index is JSON, not `.npz`.** The tools stay standard-library only.
8. **Priors use objective strata, not `<maqam>_<form>`.**
9. **`check` has no maqam-fit score.** It reports `available: false`.
10. **M6 measures only the objective half.** Quality and token reduction are not claimed.

## Reproduce and verify

With the bundled package (no bucket, no flags):

```bash
make offline-check          # plan + exemplar + similarity + check on the bundle
make test                   # unit tests
make selftest               # dialect + checker sanity
python3 02_maqam-score/scripts/ostris_cli.py contract --strict
```

Refreshing the corpus from the project data root:

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit
make ostris-build
make ostris-features
make ostris-online          # priors + idioms + similarity + eval split
make ostris-bundle          # snapshot analysis/out into 02_maqam-score/data
```

Per song:

```bash
python3 02_maqam-score/scripts/ostris_cli.py plan  --manifest song.json --out plans/song
python3 02_maqam-score/scripts/ostris_cli.py check score.abc --plan plans/song/skill_plan.json --report report.json
```

## Next

Nothing in the tooling or objective split remains unstarted. The remaining work
needs a model run, a judge, or data this build does not have:

1. **M6 generated runs** — compose on the 14 held-out generation briefs, then
   score them with `eval --runs`; the current smoke run is not model output.
2. **D3/D12** — reviewed maqam labels. Then add maqam strata and a maqam-fit
   component; keep `mode_hypothesis` separate.
3. **D1** — an audio/blind judge. Then evaluate quality and non-inferiority.
4. **M6 token reduction** — instrument prompt-only vs tool-assisted runs with
   real token counts.
5. **M7 release** — confirm data licences, then tag and publish.
6. **M5 live session** — compose one real score end to end and record it.
