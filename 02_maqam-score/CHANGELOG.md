# Changelog

## 0.3.0-dev — 2026-11-23

### OSTRIS corpus tools (M0)
- New `scripts/ostris_cli.py` + `scripts/ostris/` package. Commands:
  `sync` (lightweight GCS/local cache) and `audit` (M0 inventory/link/parse).
- `sync` copies manifests, 25 YT500 ABC shards, 15 FADL album JSONs, the
  22-track FADL shortlist, and reference ABCs; never the 2.95 GiB audio bundle.
- `audit` links all 482 library tracks (460 YT500 + 22 FADL), parses them with
  the vendored `abc_tools.py`, writes `records.jsonl`, `manifest_links.csv`,
  `audit.json`, `audit.md`, and `held_out.jsonl`.
- New schemas: `schemas/track_record.schema.json`, `schemas/audit.schema.json`.
- New tests: `tests/test_ostris.py` (parse, links, duplicate exclusion, schema).
- M0 result: 482/482 matched and parsed; 35 YT500 held-out (4 without ABC);
  5 duplicate groups / 10 tracks; 10 excluded from priors; 472 prior candidates.
- The separate-repository proposal is dropped. Offline code lives in the skill;
  generated evidence lives in `analysis/out/ostris/`.

### OSTRIS M1 ingest & canonicalization
- M1 decisions resolved and pinned in `docs/ostris-decisions.md`:
  D5 (`brief.json` + `skill_plan.json`), D6 (`Vocal+Ins` only),
  D7 (skill v0.2.0 + hashes + `--require-final-rest`), D9 (preserve `M:`/`[K:]`),
  D14 (vendored `abc_tools.py` + hash).
- New `scripts/ostris/canonical.py`: structural canonicalization. It normalizes
  line endings/trailing whitespace, validates headers and both voices, and
  preserves music lines, per-bar `M:`, and inline `[K:...]`.
- New `scripts/ostris/build.py` + `ostris build`: writes
  `analysis/out/ostris/work/canonical/abc/` (gitignored), re-parses every
  canonical file, adds a `canonical` object to `records.jsonl`, and writes
  `canonical.json` / `canonical.md`.
- New `scripts/ostris/contract.py` + `ostris contract`: verifies pinned hashes
  for `checker.py`, `calibration.json`, and `abc_tools.py`.
- M1 result: 482/482 canonical and re-parsed; 1.84 MB; 482 unique hashes;
  135 tracks with declared meter changes; 3 with inline `[K:...]`; 0 failures.
- `make ostris-build` runs with `--require-contract`.
- No priors, plan, exemplar, or check command yet: M3+ remains gated on
  the decisions in `docs/ostris-score-tools-plan.md` §13.

### OSTRIS M2 features (label-free)
- No expert maqam review is available, so D3 and D12 are **deferred** and
  `maqam` stays `null`; no maqam coverage or accuracy is claimed.
- D4 (v3 cross-check only), D11 (177 calibration only), and D16 (sanity on
  generated scores only) are recorded in `docs/ostris-decisions.md`.
- New `scripts/ostris/features.py` + `ostris features`: extracts bars, key,
  tempo band, meter timeline, section comments, per-voice density/range/
  intervals/durations/phrases, and harmony statistics.
- New `scripts/ostris/mode.py`: coarse, **unreviewed** 12-TET mode hypothesis
  (`major_like`, `minor_like`, `phrygian_like`, `hijaz_like`, `unknown`)
  anchored to the key tonic. Every row carries `reviewed: false` and is
  excluded from gates and priors.
- New `make ostris-features`; new `schemas/features.schema.json`; the track
  schema documents `features` and `mode_hypothesis`.
- M2 result: 482/482 feature rows, 482/482 mode rows, 0 named-maqam claims,
  0 failures. Key-relative families: minor_like 401, phrygian_like 55,
  major_like 25, hijaz_like 1.
- M3 may build priors by objective strata, but every prior must record
  `maqam_conditioned: false`.
- Added `docs/ostris-implementation-checklist.md`: phase-by-phase status,
  decisions, CLI/artifact coverage, deviations, and next work.

## 0.2.0 — 2026-11-23

Calibrated against the 177-track `five_stars` ABC corpus.

### Checker
- Parses inline `M:`/`K:` changes and per-bar meter (177/177 corpus files).
- Three gate classes: `contract`, `sanity`, `style`.
- Six hard sanity guards (pass 175/177 = 98.9%): simultaneity ≤4, register mean
  74±5, top duration share ≤85%, distinct durations ≥4, notes/syllable 1.0–1.55,
  Ins active ≥5%.
- Style targets warn by default; `--strict-style` makes them fail.
- Final rest warns by default; `--require-final-rest` makes it a render contract.
- `report.json` carries `class`, `calibration_version`, and `percentiles`.
- `--calibration` points at a different calibration file.

### Syllabifier
- Pace 2.8 sixteenths per syllable (corpus median 2.84), not 2.29.
- Cap ratio 0.884 (corpus median), not one-case 0.87.
- Tempo default 80 with a warning, not a silent 73.
- `seconds_per_bar` is meter-aware; the old 4/4-only formula is gone.
- Per-line P25/P75 flags instead of a fixed ±1 median rule.
- JSON carries `calibration_version`, `pace`, `case_ratio`, `seconds_per_bar`.

### Docs / examples
- `SKILL.md` and `references/reference.md` now report corpus distributions with
  `n`, not five takes as the norm.
- `example/plan.json` uses broad style values and `cadence: "any"`.
- `selftest.sh` proves the default WARN and the opt-in FAIL.
- `tests/test_checker.py` covers the example, multi-meter, strict style, and the
  final-rest flag.

### Calibration
- `scripts/calibration.json` records the 177-track corpus hashes, percentiles,
  the six sanity guards, the two optional guards, and the style defaults.

### Deliberately not in this release
- Priors for the 482-track OSTRIS instrumental set (needs the GCS manifests).
- A/B quality evaluation on a held-out set.
