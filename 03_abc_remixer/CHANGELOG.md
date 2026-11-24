# Changelog — abc_remixer

## 0.2.0 — SUNO material library

Replaces the OSTRIS-derived verbatim material store with the project-compiled
SUNO ABC dataset.  The `abc-score-writer` aggregate priors/idioms/similarity
bundle is unchanged.

### Data

- New canonical builder: `tools/build_suno_library.py` reads
  `data/SUNO_ABC_SCORE_DATASET.pkl` and writes `data/suno/` (670 canonical
  songs, `catalog_source.jsonl`, `dataset.json`, `manifest.json`).
- `library build --dataset suno` builds the store from that bundle.  The build
  no longer reads `02_maqam-score/data/ostris/records.jsonl` or `source/`.
- Store: **670** songs, **0** excluded, **644** with vocal notes, **26**
  `Ins`-only; ids are `suno-0000` … `suno-0669`.
- Every catalog row carries `source="suno_abc_score_dataset"`; legacy
  `yt500-*` / `fs18-*` ids are not present and are rejected by `remix check`.
- The optional prior snapshot is vendored at
  `03_abc_remixer/data/remix/priors/`; `remix check` no longer defaults to the
  sibling skill's data path.
- `quality` is `null` (no reviewer); catalog default sort is now `bars`.

### Tests and packaging

- Remixer tests read the 670-song store, use `suno-*` sample ids, and cover the
  SUNO builder, idempotence, and the dataset allow-list.
- `make suno-build`, `make suno-check`, and updated `make remix-build` /
  `make remix-offline`.
- Full package includes the new store and its priors snapshot; public package
  remains code-only until the provenance record is cleared.

## 0.1.0 — library-aware remixer on abc_score_writer 0.3.0

First implementation of `docs/remixer_proposal.md`.

### Tools

- `library build` normalises the 482-record library into **472** included songs
  by default (10 `exclude_from_priors` exclusions), writes one ABC per song,
  `catalog.tsv`, a compressed whole-song motif index (both voices), and a
  deterministic `build_report.json`.
- `library verify` re-parses every stored song and checks the catalog hash.
- `catalog` filters by key, mode, meter, tempo, bars, density, title, artist,
  and source; caps at 40 rows; supports deterministic random sampling.
- `songmap` reports sections, ranges, hook/riff cells, and scale-degree
  cadences under a 3,000-character cap.
- `slice` extracts at most 8 bars (16 by explicit ceiling), re-emits valid
  two-voice ABC from parsed events, supports `L:1/16` and `L:1/32`, transposes
  by semitones or to a key, strips chord symbols, handles meter changes and
  `Z` rests, and reports quantisation.
- `motif-find` searches interval sequences, duration-ratio sequences, and
  contour windows across both voices and returns `(song, bars)`.
- Session ledger caps retrieval at 30,000 characters by default and exits
  non-zero before crossing it.
- `remix check` verifies declared quotes for exact/transposed/inverted/
  retrograde/augmented/fragmented/rhythm-only/contour-only transforms, detects
  undeclared 8+ interval runs, enforces `literal_cap_bars`, and runs the
  unchanged 0.3.0 checker.

### Skill and package

- New sibling skill source `03_abc_remixer/`; the package vendor-copies the
  0.3.0 runtime into `scripts/` so the installed skill is self-contained.
- `scripts/package_remixer.sh` builds full and public archives; the full archive
  contains the prebuilt store, the public archive contains code only.
- `SKILL.md`, `references/dialect.md`, `references/transforms.md`, schemas, and
  a workflow example.
- Tests: 53 remixer tests plus the unchanged 43 skill tests, selftest, offline
  check, and contract pins.

### Deliberate limitations

- No maqam labels are invented. The library has none; the skill says so.
- Mode C (no lyrics) is out of scope because `syllabify.py` requires a lyrics
  file.
- The 177-track calibration is unchanged; the 482-track library is not used to
  recalibrate the gate.
- The existing 35 held-out YT500 tracks are already outside the 472-song store;
  a true held-out retrieval condition needs a new split, as documented in the
  implementation plan.
