# OSTRIS plan — implementation checklist

**Snapshot:** 2026-11-23 · **Repo:** `skill_abc_writer` · **Skill:** v0.2.0
**Overall:** M0–M2 are implemented (M2 label-free); M3–M7 are not started.
No commit has been made.

Legend: ✅ done · 🟡 partial · ⏳ not started · ⏸️ deferred/blocked.
The source plan is `docs/ostris-score-tools-plan.md`; decisions are in
`docs/ostris-decisions.md`.

## At a glance

| Phase | Plan scope | Status | Gate |
|---|---|---|---|
| **M0** Audit & contracts | Links, audit, schemas, inventory re-check | ✅ done | PASS |
| **M1** Ingest & canonicalize | Canonical ABC, FADL links, records + provenance | ✅ done with deviations (no tar sidecars) | PASS |
| **M2** Features & labels | Features, maqam, mood, prosody | 🟡 label-free subset (no maqam/mood/prosody) | PASS (amended) |
| **M3** Priors & plan | Quantiles, backoff, `brief.json` + `skill_plan.json` | ⏳ not started | not run |
| **M4** Idioms, similarity, check | Idiom bank, k-gram index, combined `check` | ⏳ not started | not run |
| **M5** Integration | `ostris check`, TOOLS section, wrapper | 🟡 pin only | not run |
| **M6** Evaluation | Held-out A/B, quality + token metrics | ⏳ not started | not run |
| **M7** Hardening & handoff | Licensing, CI, release | 🟡 docs/provenance/build only | not run |

## M0 — Audit & contracts ✅

- [x] `manifest_links.csv`: 482 rows (460 YT500 + 22 FADL), missing list included
- [x] `audit.json`: parse status, bars, chords, duration mismatch, duplicates, quality flags
- [x] `track_record` schema v1 and `audit` schema v1
- [x] Fixtures + tests (`OstrisFixture`, parse/link/duplicate/schema tests)
- [x] Inventory re-verified from manifests: 482 library, 495 YT500, 35 held-out, 438 v3, 3,162,110,202 bytes / 36.6 h
- [x] Duplicate inventory: 5 groups / 10 tracks
- [x] Missing list with a decision: 4 YT500 tracks without ABC, all in the held-out set
- [x] Gate: ≥95% linked and parsed → **482/482 matched, 482/482 parsed (100%)**
- [x] Extra evidence: `held_out.jsonl`, duplicate groups, quality flags

**Result:** `docs/ostris-m0-audit.md`.

## M1 — Ingest & canonicalize ✅

- [x] Manifests and YT500 ABC shards copied to the local cache
- [x] FADL shortlist + selected-score transcripts + reference conditioner ABCs copied
- [ ] Sample `tar.gz` download — **not done, intentionally**. The YT500 shard JSON already carries the ABC text; the 2.95 GiB audio bundle and 495 tar shards were not downloaded.
- [x] `score.abc` content extracted from the shard JSON
- [ ] Tar sidecars / `structure.lab` — **not extracted**. M2 uses the manifest `sections` count and ABC comment labels instead.
- [x] Canonical ABC, structural normalization only
- [x] Per-bar `M:` and inline `[K:...]` preserved (D9)
- [x] `L`/`Q` preserved as written (no risky duration rescale)
- [x] FADL linking: 22/22, selected transcript preferred, reference conditioner as fallback
- [x] `records.jsonl` with per-field provenance and a `canonical` object
- [x] Gate: 482/482 canonical and re-parsed; 1.84 MB; unique hashes
- [x] D7/D14 contract pins checked by `ostris contract`

**Deviations:** no tar extraction, no sidecars. The shard JSON is the extracted
score source; this is documented in `docs/ostris-m1-ingest.md`.

## M2 — Features & labels 🟡

### Done

- [x] Bars, duration, key, tempo, tempo band
- [x] Meter timeline: declared meters, change count, family
- [x] Section count (manifest) + section comment labels (`intro`, `verse`, `chorus`, …)
- [x] Melody/rhythm features: density, range, median pitch, intervals, durations, phrases
- [x] Harmony features: chord count, vocabulary, per-bar rate, roots, qualities
- [x] Objective feature rows: **482/482**
- [x] Unreviewed `mode_hypothesis`: **482/482**, `reviewed: false`, key-anchored
- [x] Zero named-maqam claims: `maqam: null` on **482/482**
- [x] Replacement gate: **PASS**

### Not done

- [ ] Full form/structure spans from `structure.lab` (no sidecars downloaded)
- [ ] Prosody features (the ABC has no lyric text; the syllabifier owns this)
- [ ] Maqam classifier + manual review — **deferred** with D3
- [ ] Maqam coverage/accuracy reporting — **not applicable** until D3
- [ ] Mood tags + 50-track lexicon review — **not done**

**Result:** `docs/ostris-m2-features.md`. Keys: `maqam_conditioned: false`,
`maqam_reviewed: false`.

## M3 — Priors & plan ⏳

- [ ] Quantiles per stratum, with `n` and confidence
- [ ] Backoff for small strata
- [ ] `ostris plan` generator
- [ ] `brief.json` output
- [ ] `skill_plan.json` output (the 15 keys `checker.py` requires)
- [ ] Fixtures for 10 manifests
- [ ] Gate: 100% valid `skill_plan.json`, bars within ±10% of target

**Prerequisite:** D5 is resolved. Priors must be stratified by objective
features (meter, tempo, bars, density, section count, range, chords) and must
record `maqam_conditioned: false`. Named-maqam priors remain blocked by D3/D12.

## M4 — Idioms, similarity, check ⏳

- [ ] Idiom bank, 2–4 bars per function (maqam-conditioned idioms blocked by D3)
- [ ] k-gram similarity index
- [ ] `ostris check` combining skill checker + priors + similarity
- [ ] Maqam-fit component (blocked by D3; can be omitted or marked unavailable)
- [ ] Gate policy D8: `contract` + `sanity` hard, `style` WARN
- [ ] Gate: three known scores distinguish good/medium/bad with `class` and `percentiles`

**Blocked by:** D8, D10, D15.

## M5 — Integration 🟡

- [x] Skill v0.2.0 pinned (checker `bd3645…`, calibration `c5cd51…`)
- [x] Vendored parser pinned (`abc_tools.py` `e99e5c…`)
- [ ] `ostris check` passes `--require-final-rest` on the render path
- [ ] `TOOLS` section in `SKILL.md` (3 online commands)
- [ ] Wrapper that runs in `/content/chat` on CPU
- [ ] D6 two-voice contract enforced end to end (`Vocal+Ins`; decision recorded)
- [ ] Gate: full session `plan → write → check → patch` without corpus in context

**Blocked by:** M3 and M4; D8, D10, D15.

## M6 — Evaluation ⏳

- [x] Natural held-out set identified: 35 YT500 tracks not in the library
- [x] Usable subset measured: 4 of the 35 have no ABC, leaving **31**
- [ ] Reserve 12–16 manifests from the 35 for generation (D13)
- [ ] Use the remaining held-out tracks for retrieval
- [ ] A/B: prompt-only vs tool-assisted
- [ ] Quality, token, and time metrics
- [ ] Gate: non-inferiority + ≥30% token reduction

**Blocked by:** D1, D2, D13.

## M7 — Hardening & handoff 🟡

- [x] Docs for M0–M2
- [x] Provenance: source URIs, hashes, contract pins, limitations
- [x] Reproducible build: `make ostris-sync / audit / build / features`
- [x] Unit tests: **19 passing**; `make selftest` passes
- [ ] Licensing review
- [ ] CI on fixtures
- [ ] Release v0.1
- [ ] Final handoff notes for a future reviewer/labelled dataset

## Decisions

| # | Topic | Status |
|---|---|---|
| D1 | Final quality target | ⏳ open |
| D2 | Held-out function | ⏳ open |
| D3 | Maqam review | ⏸️ deferred — no reviewer |
| D4 | 438 v3 labels | ✅ cross-check only |
| D5 | Plan schema | ✅ `brief.json` + `skill_plan.json` |
| D6 | Instrumental voices | ✅ `Vocal+Ins` only in v1 |
| D7 | Skill contract | ✅ v0.2.0 + hashes + `--require-final-rest` |
| D8 | Gate policy | ⏳ open |
| D9 | Variable meter | ✅ preserve `M:`/`[K:...]` |
| D10 | `report.json` merge | ⏳ open |
| D11 | 177 role | ✅ calibration only |
| D12 | Maqam coverage | ⏸️ N/A until D3 |
| D13 | Held-out source | ⏳ open (recommendation: 35 YT500) |
| D14 | Parser | ✅ vendored + pinned |
| D15 | Final rest | ⏳ open |
| D16 | Sanity on 482 | ✅ generated scores only |

## CLI surface

| Command | Status |
|---|---|
| `sync` | ✅ added for the lightweight cache |
| `audit` | ✅ M0 |
| `build` | ✅ M1 |
| `features` | ✅ M2 |
| `contract` | ✅ hash verification |
| `plan` | ⏳ M3 |
| `exemplar` | ⏳ M4 |
| `check` | ⏳ M4 |
| `similarity` / `originality` | ⏳ M4 |
| `state` | ⏳ later |
| `search` | ⏳ optional |
| `eval` | ⏳ M6 |

Entry point: `python3 02_maqam-score/scripts/ostris_cli.py <command>`.

## Artifacts

| Artifact | Status |
|---|---|
| `records.jsonl` | ✅ 482 rows; M1 canonical + M2 features |
| `manifest_links.csv` | ✅ 482 rows |
| `audit.json` / `audit.md` | ✅ M0 |
| `canonical.json` / `canonical.md` | ✅ M1 |
| `features.json` / `features.md` | ✅ M2 |
| `held_out.jsonl` | ✅ 35 rows |
| `priors/<stratum>.json` | ⏳ M3 |
| `idioms.jsonl` | ⏳ M4 |
| `similarity/index.*` | ⏳ M4 |
| `eval/queries.jsonl` | ⏳ M6 |
| `report.json` from `check` | ⏳ M4 |

## Verified numbers

- [x] 482 library tracks = 460 YT500 + 22 FADL shortlist
- [x] 495 YT500 transcripts; 460 used; 35 held out
- [x] 35 held out; 4 without ABC; **31 usable** for M6
- [x] 438 v3 labels, excluded from priors/eval (D4)
- [x] 2.95 GiB / 36.6 h audio inventory
- [x] 5 duplicate groups / 10 tracks; 10 tracks excluded from priors
- [x] 22 FADL shortlist; 24 selected-score tracks, 23 with ABC
- [x] 482/482 parse, canonical, and feature coverage
- [x] 0 named-maqam claims

## Deviations from the plan

1. **No separate repository.** The user rejected it; the tools live in the skill.
2. **No audio bundle.** Only lightweight manifests/ABCs are cached.
3. **No M1 tar/sidecar extraction.** The shard JSON already contains the ABC;
   `structure.lab` was not downloaded. M2 uses manifest section counts and
   comment labels instead.
4. **Canonicalization is structural.** `L`/`Q` values are preserved; `M:` and
   `[K:...]` are preserved. There is no duration rescale.
5. **M2 is label-free.** No maqam labels, no mood tags, no prosody; the gate was
   amended. The `mode_hypothesis` is unreviewed and key-anchored.
6. **FADL source corrected.** The 22 tracks link through
   `fadhl_shaker_selected_scores` + reference conditioner ABCs, not the broader
   15-album `TRANSCRIPTS/FADL_SHAKER` set.

## Reproduce and verify

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit
make ostris-build
make ostris-features
python3 02_maqam-score/scripts/ostris_cli.py contract --strict
make test          # 19 tests
make selftest      # dialect + checker sanity
```

## Next

M3 is the next unblocked stage. It can build priors by objective features and
emit `brief.json` + `skill_plan.json`, with `maqam_conditioned: false` recorded
everywhere. Named-maqam work stays deferred until a reviewer or a licensed
labelled dataset exists.
