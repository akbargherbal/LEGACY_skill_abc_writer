# Remixer implementation plan — from proposal to a releasable sibling skill

**Status:** implemented in `03_abc_remixer/` (0.1.0); see
`docs/remixer-implementation-report.md` for results.
**Source proposal:** `docs/remixer_proposal.md`
**Baseline inspected:** `abc_score_writer` **0.3.0** (the latest release in
`dist/releases/`; `SKILL_VERSION = "0.3.0"`).
**Target:** a sibling skill, `abc_remixer` **0.1.0**, built on the 0.3.0
runtime and shipped as `dist/releases/abc_remixer-0.1.0.zip`.
**Date:** 2026-11-23.

> **Version note.** The request says “latest release 0.0.3”. There is no
> `0.0.3` artifact in this repository: `dist/releases/` contains 0.2.0 and
> 0.3.0, and `scripts/ostris/contract.py` pins `SKILL_VERSION = "0.3.0"`.
> This plan therefore targets the actual latest release, **0.3.0**. If “0.0.3”
> is the intended release label for the new remixer package, only the version
> strings in §11 and the archive names change; no technical decision below
> depends on the number.

---

## 0. Executive summary

The proposal is sound: the library is large enough to be dangerous and small
enough to be useful, and the current bundle already contains the hard part —
parsed, measured, linked ABC for all 482 library songs. The work is therefore
not “build a corpus”; it is “build a funnel, a deterministic extraction layer,
a quotation verifier, and a second skill around the existing runtime”.

The plan adds, in this order:

1. `library build` — one normalised ABC per song + a compact catalog + a
   whole-song motif index (both voices).
2. `catalog` — filtered, capped discovery.
3. `slice` — exact, dialect-safe bar extraction and transposition.
4. `songmap` — a ~300-token structural view of one song.
5. `motif-find` — interval/rhythm/contour search returning `(song, bars)`.
6. `remix check` — declared-quote verification, undeclared-quote detection,
   metrics, and the unchanged `checker.py` gate.
7. `abc_remixer/SKILL.md` and a self-contained sibling package.
8. A scripted integration dry run, then the A/B/C evaluation.

The main deviation from the proposal is packaging: the remixer is a **separate
skill source tree** with shared runtime files vendored at package time, not a
runtime path dependency on `../abc_score_writer/scripts`. A sibling that
references files outside its own installed folder is fragile; a build-time copy
with a hash check is reproducible and still keeps one source of truth.

The proposal’s biggest hidden risk (“the transcript ↔ record join is not
trivial”) is already solved by the 0.3.0 bundle: `links.link_library()` matches
**482/482** records, all with ABC, and all parse. The plan reuses that code and
keeps the join tests as a regression guard.

---

## 1. Verified baseline (2026-11-23)

These numbers were re-measured from the bundled 0.3.0 data, not copied from the
proposal. They are the inputs to the design.

### 1.1 Corpus

| Fact | Measured value | Consequence |
|---|---:|---|
| Library records | 482 (460 `yt500` + 22 `fadhl_shaker_shortlist`) | one row per song |
| `exclude_from_priors` | 10 | default remix corpus = **472** |
| `duplicate_of != null` | 3 | already inside the 10 |
| Flag `duplicate` | 9 | exclude by default through `exclude_from_priors` |
| `quality_score` | 1.0 ×463, 0.9 ×15, 0.85 ×1, 0.8 ×3 | default floor 0.8 excludes none |
| `maqam` labels | `null` on all 482 | never claim a maqam |
| Links matched | 482/482 | join is not a blocker |
| Links with ABC | 482/482 | no missing ABC in the 482 |
| Re-parse after canonicalisation | 482/482 | library build can be strict |
| Transcript tracks | 623 with ABC (YT500 491, FADL 132) | source pool is larger than the library |
| Total ABC text | 2,486,581 chars | ~2.5 MB store |
| Mean / max song | 3,991 / 8,972 chars | slice/map caps are realistic |
| Header unit in the 482 | `L:1/16` ×266, `L:1/32` ×216 | must support both; do not force 1/16 |
| Header unit in all 623 | `L:1/16` ×340, `L:1/32` ×283 | same conclusion |
| Tracks with meter changes | 135/482 | slice must emit per-bar `M:` |
| FADL with no vocal notes | 1 (`al_qissa_wama_fiha`, reference conditioner) | keep as Ins-only source |
| Existing held-out set | 35 YT500 tracks, not in the 482 | see §13.3 for the C condition |

### 1.2 Runtime and tests

- Baseline source is the 0.3.0 tree; verify the packaged artifact against
  `dist/releases/SHA256SUMS-0.3.0.txt` before branching.
- `make test`: **43 tests pass**.
- `make selftest`: **PASS**.
- `make offline-check`: **PASS**.
- `ostris contract --strict`: **pinned** (`checker.py`, `calibration.json`,
  `abc_tools.py`).
- `records.jsonl` has all 482 `canonical.uri` values, but the canonical ABC
  files themselves are **not bundled** (`data/ostris/work/` is omitted). A new
  `library build` must obtain ABC through
  `ostris.links.link_library(...)[id]["abc_text"]`, not by opening
  `canonical.uri`.
- `ostris.check` already accepts extra top-level keys in a plan because
  `validate_plan()` only checks the required 15 targets and
  `schemas/plan.schema.json` has `"additionalProperties": true`. A `remix`
  block can be added without changing the checker or the existing schema.

### 1.3 What is reused unchanged

| Component | Reuse |
|---|---|
| `scripts/abc_tools.py` | the only parser; never write a second one |
| `scripts/checker.py` | contract + 9 sanity + style gates, unchanged |
| `scripts/calibration.json` | unchanged |
| `scripts/syllabify.py` | lyrics → bars budget, unchanged |
| `scripts/ostris/links.py` | transcript ↔ record join |
| `scripts/ostris/canonical.py` | structural normalisation |
| `scripts/ostris/parse.py` | measured parse wrapper |
| `scripts/ostris/check.py` | combined checker report |
| `scripts/ostris/mode.py` | key/mode hypothesis, not a maqam claim |
| `scripts/selftest.sh` | must keep passing unchanged |

### 1.4 Deliberate non-goals

- No changes to `checker.py`, `calibration.json`, the sanity thresholds, or
  `scripts/selftest.sh`.
- No script that writes the final score. Tools retrieve, transform, and verify;
  the model writes ABC by hand.
- No audio, rendering, network, or new dependencies. Python 3 standard library
  only (`sqlite3` is allowed but not required by this plan).
- No maqam classifier. The library has no labels; the remixer says
  “key/mode hypothesis” and lets the model re-spell borrowed material.
- No recalibration against the 482-track corpus. The 177-track calibration
  remains the gate reference.
- No wholesale reading of library files by the model. The skill instructions
  forbid it; the CLI is the only sanctioned interface.

---

## 2. Decisions to lock before coding

| ID | Decision | Choice | Reason |
|---|---|---|---|
| **RM1** | Baseline | `abc_score_writer` 0.3.0 | only release present |
| **RM2** | Delivery | sibling skill `abc_remixer` 0.1.0 | proposal; avoids overloading `SKILL.md` |
| **RM3** | Shared runtime | vendored at package time into `abc_remixer/scripts/`, preserving the `scripts/ostris/` layout | installed skills must be self-contained, and `ostris/contract.py` assumes `scripts/<file>` |
| **RM4** | Default corpus | `exclude_from_priors == false` → 472 songs | matches existing priors; documented |
| **RM5** | Metadata flags | keep flagged songs, expose `flags` in catalog | `no_vocal_notes` can still be an Ins source |
| **RM6** | `--include-all` | 482 minus unparseable | explicit escape hatch |
| **RM7** | Unit policy | `--unit auto` preserves the source `L:` (1/16 or 1/32); forced rescale is reported | 216/482 are 1/32; a lossy default is wrong |
| **RM8** | Quote matching | exact by default; `--tolerance N` opt-in | declared quotes should be real |
| **RM9** | Undeclared match | ≥8 intervals + minimum-information filter + index | proposal; reduce repeated-note noise |
| **RM10** | Ledger path | `$PWD/.remix-ledger.jsonl`; `--ledger`/`REMIX_LEDGER` override | installed `data/` may be read-only |
| **RM11** | Mode C (no lyrics) | **out of scope** | verified: `syllabify.py` requires a positional lyrics file |
| **RM12** | Held-out C | new deterministic 35-song split of the 482 for evaluation | existing 35 are already outside the library |
| **RM13** | Package version | `abc_remixer` 0.1.0; use 0.0.3 only as a label if required | semantic versioning |

**Sign-off items before coding:** RM2 (sibling package), RM7 (support `L:1/32`
rather than force lossy 1/16), RM10 (ledger in the working directory), RM12
(true held-out split vs. external reference only), and RM13 (the version
label). The rest are implementation details with a documented default.

---

## 3. Architecture

### 3.1 The funnel

```
concept (no tool)
   ↓
catalog          wide, cheap, ~15 rows/call, hard max 40
   ↓
songmap          narrow, ~300 tokens/song, hard cap
   ↓
slice            deep, ≤8 bars/call, dialect-valid ABC
   ↓
motif-find       pattern → (song, bars) → slice
   ↓
write plan.json + score.abc by hand
   ↓
remix check      verify declared quotes, detect undeclared ones, run checker
```

Each layer costs more per item and touches fewer items. Every layer has a hard
output cap in code. The ledger counts characters returned to the model and
refuses calls past the session budget.

### 3.2 Source layout

Create a sibling source tree; do not put remixer code or data inside the
`abc_score_writer` package.

```
03_abc_remixer/
  SKILL.md                       # name: abc_remixer
  CHANGELOG.md
  references/
    dialect.md                   # trimmed composing dialect + remix rules
    transforms.md                # transform vocabulary and matching rules
  schemas/
    remix_block.schema.json
    remix_report.schema.json
  scripts/
    remix_cli.py                 # entry point, same pattern as ostris_cli.py
    remix/
      __init__.py
      shared.py                  # add scripts/ or the dev fallback to sys.path
      ledger.py
      store.py                   # paths, catalog load, song load, index load
      build.py                   # library build + build_report.json
      catalog.py
      slice.py
      emit.py                    # parsed notes -> dialect-valid ABC
      pitch.py                   # MIDI <-> ABC spelling per key
      songmap.py
      motif.py
      transforms.py              # invert/retrograde/augment/fragment/...
      quotecheck.py              # declared and undeclared quote verification
      metrics.py                 # coverage/literal/novelty/diversity/mix
      textcap.py                 # hard output caps
      cli.py
  data/
    remix/
      songs/<song_id>.abc
      catalog.tsv
      catalog_meta.json
      index/motif.json           # or motif.json.gz; see §8.2
      index/manifest.json
      build_report.json
  example/
    brief.md
    lyrics.txt
    plan.json
    score.abc
    report.json
  tests/
    test_remix_build.py
    test_catalog.py
    test_slice.py
    test_songmap.py
    test_motif.py
    test_quotecheck.py
    test_ledger.py
    test_remixer_skill.py
  # At package time the shared runtime is copied into scripts/ (see §3.3);
  # it is generated, not committed a second time.
```

### 3.3 Runtime files

The 0.3.0 modules locate each other and the skill root by file path:
`ostris/check.py` resolves `SKILL_ROOT = parents[2]` and looks for
`scripts/checker.py`; `ostris/contract.py` resolves `scripts/` and pins
`scripts/<file>`. Therefore the vendored copy **must keep the `scripts/`
layout** — do not put it under `scripts/_shared/` or another subdirectory.

At package time `scripts/package_remixer.sh` copies these from
`02_maqam-score/scripts/` into `03_abc_remixer/scripts/` (staging only):

```
abc_tools.py
checker.py
calibration.json
syllabify.py
ostris/            # full package, ~150 KB
RUNTIME_MANIFEST.json   # hashes + source versions
```

`remix/shared.py` adds, in order:

1. `REMIX_SHARED_SCRIPTS` (test/development override),
2. its own `scripts/` directory, i.e. the vendored copy in an installed
   package (`03_abc_remixer/scripts/remix/shared.py` resolves `parents[1]`),
3. `<repo>/02_maqam-score/scripts/` in the development tree
   (`03_abc_remixer/scripts/remix/shared.py` resolves `parents[3]`).

The first path that contains `abc_tools.py` wins. If none resolves, fail with
one clear message. In the source tree the shared files are not committed; the
fallback makes local tests work, and the package script makes the installed
skill self-contained.

### 3.4 Packaging

- Add `scripts/package_remixer.sh` (analogue of `package_skill.sh`).
- Full package: `abc_remixer/` with SKILL.md, `scripts/` (including the
  vendored runtime), `data/remix/`, references, schemas, example, tests, and
  `data/ostris/priors/` (224 KB) for prior percentiles. Do **not** copy the
  7.5 MB OSTRIS source cache; the remixer ships a prebuilt store.
- Public package: same code, no `data/`; commands then need `--library`.
- Do **not** include `analysis/`, `docs/`, the evaluation inbox, or any audio.
- Keep `abc_score_writer` 0.3.0 packaging unchanged. Its zip must not grow by
  the remixer store.
- Add Makefile targets: `remix-build`, `remix-test`, `remix-offline`,
  `remix-zip`, `remix-release`.
- Add CI steps after the existing green baseline; do not replace the existing
  test/selftest/contract steps.

---

## 4. Phase 1 — `library build` (unblocks everything)

### 4.1 Command

```bash
python3 03_abc_remixer/scripts/remix_cli.py library build \
  --ostris-data 02_maqam-score/data/ostris \
  --out 03_abc_remixer/data/remix \
  [--include-all] [--quality-min 0.8] [--force]
```

`--ostris-data` points at the directory containing `records.jsonl` and
`source/`. `library build` is a regeneration command; it is not needed at use
time because the store ships in the package.

### 4.2 Algorithm

1. Read `records.jsonl` into a dict by `id`. Refuse duplicate ids.
2. Load `ostris.links.load_inventory(Cache(source))` and
   `link_library(inv, cache)`; index by `record_id(link)`.
3. For each record, in `id` order:
   - find the link; if missing, record a join failure;
   - take `link["abc_text"]`; if empty, record a no-ABC failure;
   - `canonicalize(text)`; if not ok, record a canonicalisation failure;
   - `parse_abc(canonical.text)`; if not ok, record a parse failure;
   - apply the exclusion policy;
   - write `songs/<song_id>.abc` (normalised text, one final newline);
   - derive catalog fields from the parsed score.
4. Write `catalog.tsv`, `catalog_meta.json`, `index/`, `build_report.json`.
5. Re-read every written song and re-parse it before declaring success.

### 4.3 Exclusion policy

Default (`--exclude-policy default`):

- drop `exclude_from_priors == true` (10 songs);
- drop `duplicate_of != null` (already inside the 10);
- drop `quality_score < 0.8` (currently none);
- drop any song that fails canonicalisation or parsing;
- keep songs with other flags, but copy `flags` into the catalog so the model
  can see `qc_octave_suspect`, `low_coverage`, `no_vocal_notes`, etc.;
- mark a song with no vocal notes as `ins_only: true`; it can still be an Ins
  riff source.

`--include-all` bypasses the quality/duplicate exclusions but never bypasses
parse failures. `--quality-min` is explicit.

Expected default: **472 songs**; `--include-all`: **482** (0 parse failures in
the current bundle).

### 4.4 Catalog columns

One TSV row per song, deterministic order by `song_id`:

```
song_id
title
artist
key
mode                 # major | minor
meter                # header meter
meters               # ;-joined distinct meters
tempo
bars
section_count
density
silence
vocal_low
vocal_high
ins_low
ins_high
vocal_mean
vocal_top
ins_active_share
repeated_pitch_share
duration_variety
notes_vocal
notes_ins
unit
quality
source
flags                # ;-joined
ins_only             # 0 | 1
excluded_reason      # empty for included songs
abc_sha256
```

Derived fields are computed from the parsed score, not copied from the record
when a direct measurement exists:

- `vocal_mean`, `vocal_top`: mean and max MIDI of the Vocal voice.
- `ins_active_share`: share of bars in which an Ins note sounds (a note counts
  for every bar its `[onset, onset+duration)` overlaps).
- `repeated_pitch_share`: share of consecutive Vocal intervals equal to 0.
- `duration_variety`: number of distinct Vocal note durations.
- `mode`: from the key suffix (`m` → minor, otherwise major).
- `unit`: denominator from the header `L:`.

Keep the catalog under 200 KB. At 482 rows × ~250 bytes this is comfortable.
Escape tabs and newlines in `title`/`artist` as `\t`/`\n`; the writer and
reader share one escaping function.

### 4.5 `build_report.json`

No wall-clock timestamp by default; use a content hash of the inputs so a
re-run is byte-identical. Add `--timestamp` if a human wants a dated report.

```json
{
  "version": "remix-build-v1",
  "inputs": {
    "records_sha256": "...",
    "source_inventory_sha256": "..."
  },
  "counts": {
    "records": 482,
    "linked": 482,
    "with_abc": 482,
    "canonical_ok": 482,
    "parse_ok": 482,
    "included": 472,
    "excluded": 10
  },
  "exclusions": [
    {"song_id": "...", "reason": "exclude_from_priors"}
  ],
  "join_failures": [],
  "parse_failures": [],
  "canonical_failures": [],
  "dialect": {"L:1/16": 266, "L:1/32": 216},
  "quality": {"min": 0.8, "flagged": 12, "ins_only": 1},
  "outputs": {"songs": 472, "catalog_bytes": 0, "index_bytes": 0},
  "checks": [
    {"name": "coverage", "required": true, "ok": true, "detail": "472/472 parse"},
    {"name": "join", "required": true, "ok": true, "detail": "482/482 linked"}
  ]
}
```

### 4.6 Acceptance

- Idempotent: two builds into two temp dirs produce byte-identical
  `catalog.tsv`, `songs/*.abc`, `index/*`, and `build_report.json`.
- Every stored song re-parses with `abc_tools.parse`.
- Counts in `catalog.tsv`, `songs/`, and `build_report.json` agree.
- The join-failure and exclusion lists are explicit, never silently dropped.
- No source ABC is copied verbatim if it fails canonicalisation.
- The store contains no audio and no `.json` shard files.

---

## 5. Phase 2 — `catalog`

### 5.1 Command

```bash
remix_cli.py catalog [--key Dm] [--mode minor|major] [--meter 4/4]
                     [--tempo 70-90] [--bars 60-120]
                     [--density light|medium|busy]
                     [--title STR] [--artist STR]
                     [--source yt500|fadhl_shaker_shortlist]
                     [--sort quality|density|bars|tempo|title]
                     [--limit 15] [--random --seed N]
                     [--json]
```

### 5.2 Behaviour

- Default `--limit 15`; hard maximum **40**. `--limit 999` is clamped to 40 and
  prints a warning, or exits 2 if `--strict-limits` is set. Choose clamping in
  favour of the model.
- Filters are ANDed. `--tempo` and `--bars` accept `N` or `A-B`.
- `--mode` is derived from the key suffix, not a separate label.
- `--meter` matches either the header meter or any entry in `meters`.
- `--density light|medium|busy` uses the 33rd and 66th percentiles of the
  included catalog, computed at build time and recorded in `catalog_meta.json`.
  This keeps the bands corpus-derived and reproducible.
- `--random --seed N` samples deterministically from the filtered set with
  `random.Random(seed)`.
- Output states `matched=<total> shown=<n>`; sorting is deterministic
  (`quality` desc, then `song_id`; other sorts have `song_id` as the final
  tie-break).
- One line per song, **≤ 160 characters** and ≤ ~30 tokens (use a `chars/3`
  proxy in the test; say so in the report). If a line would exceed the width,
  truncate title/artist to 24 characters and then drop optional fields.
- Example:

```
yt500-0001-fbK2ySlxAW4 | Maktooba Leek | Elissa | Fm 2/4 70bpm | 186 bars | sil 0.39 | dens 4.60 | q1.0
```

- The command is charged to the ledger (§9).

### 5.3 Acceptance

- Deterministic for the same filters and seed.
- `--limit 41` yields at most 40 rows and a clear `matched=... shown=...`.
- Every line respects the character cap.
- All filters are covered by unit tests against a small fixture catalog.
- A call that would exceed the session ledger fails before printing.

---

## 6. Phase 3 — `slice` (the hardest component)

### 6.1 Command

```bash
remix_cli.py slice <song_id> --bars 17-24 \
  [--voice Vocal|Ins|both] \
  [--to-key Dm] [--transpose N] \
  [--strip-chords|--keep-chords] \
  [--unit auto|1/16|1/32] \
  [--emit abc|json] \
  [--max-bars 8] [--allow-lossy]
```

### 6.2 Hard limits

- Default **8 bars per call**; `--max-bars` may raise the ceiling to **16**,
  never beyond. A request above the active ceiling exits non-zero with a clear
  message.
- Output cap ~2,500 characters. If exceeded, fail rather than truncate a
  musical fragment.
- One-based inclusive bar numbers, matching `songmap` and `motif-find`.
- `--to-key` and `--transpose` are mutually exclusive.
- The output is always a complete, parseable two-voice ABC fragment, even when
  one voice is requested; the unrequested voice is full-bar rests.

### 6.3 Output shape

Use the fixed 8-line header and one bar per voice group. One bar per group is
slightly longer but removes the hardest class of bugs (grouping, meter changes,
ties across grouped bars).

```abc
X:1
T:
M:4/4
L:1/16
Q:1/4=70
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
% src=yt500-0001-fbK2ySlxAW4 bars=17-24 voice=both transpose=0 unit=1/16
V: Vocal
d4e4f4g4|
V: Ins
Z|
...
```

- The provenance comment is after the header, never before it; `abc_tools`
  requires `X:1` and `T:` as the first two lines.
- `--strip-chords` is the default. The 177-track calibration corpus has no
  chord symbols; the remix skill should not introduce them accidentally.
- `--keep-chords` emits chord tokens only in the Vocal voice, as the parser
  requires.
- `Z` is used only for a whole-bar rest; otherwise a rest is `z<units>`.
- Section comments are not copied; the provenance line is the only comment.
- `--emit json` returns the same material as structured notes plus the
  quantisation report, but still counts toward the ledger.

### 6.4 Parsed-event pipeline

Do not regex the ABC text. Work from `abc_tools.parse(text)`:

- `score.voices[voice].notes` = `[onset_quarters, pitch, duration_quarters]`;
- `score.voices[voice].bars` = `[(start_quarters, length_quarters, meter)]`;
- `score.voices[voice].chords` = `[(onset, symbol)]`;
- `score.voices[voice].keys` = `[(onset, key)]`.

Select notes whose onset lies inside the requested bar range, plus notes that
start before the range and sustain into it (clip them at the range start and
report the clip). Slice at bar boundaries; do not include a partial bar.

### 6.5 Re-emission algorithm

For each bar in the range, for each voice:

1. Determine the bar's meter from `voice.bars[i][2]`.
2. Collect the notes whose onset is inside the bar (or whose sustain crosses
   the barline from the previous bar).
3. Fill gaps with rests.
4. Convert each duration in quarter notes to target units:
   `units = duration_quarters * target_den / 4`.
   With `L:1/16`, one quarter note = 4 units; with `L:1/32`, one quarter = 8.
5. Split any duration into legal tokens from
   `{1,2,3,4,6,8,12,16,24,32,48}`. If a note crosses a barline, emit a tied
   token in each bar (`-` after all but the last segment).
6. Spell each pitch for the target key (§6.6).
7. Emit the bar, ending with `|`. One music line per voice per bar.

The writer must verify its own output with `abc_tools.parse` before returning.
A failed re-parse is a tool bug and exits non-zero with the parse error.

### 6.6 Unit and quantisation policy

- `--unit auto` (default) uses the source header denominator. No quantisation.
  This preserves exact rhythm for both the 266 `L:1/16` and 216 `L:1/32`
  songs.
- `--unit 1/16` or `--unit 1/32` forces a target resolution. Compute every
  exact duration in target units; if it is not an integer in the allowed set,
  round to the nearest legal integer and record:
  - number of altered notes,
  - maximum error in target units,
  - maximum error in quarter notes.
- Fail if altered share > 5% or any error > 1 target unit, unless
  `--allow-lossy` is passed. When `--allow-lossy` is passed, the report still
  states the loss.
- In ABC output, put `% quantized=<n> notes max_error=<x> units` next to the
  provenance line. In JSON output, put a `quantization` object.
- Rationale: the proposal suggested deciding between lossy 1/32 → 1/16
  rescaling and supporting `L:1/32`. The parser and checker both accept
  `L:1/32`; the plan keeps it as a first-class target and makes lossy rescaling
  opt-in and measurable.

### 6.7 Transposition and spelling

- `--transpose N` adds N semitones chromatically. Reject the request if any
  transposed pitch would fall outside MIDI 0–127.
- `--to-key K` computes the pitch-class delta from the source tonic to the
  target tonic, chooses the representative in `[-6, +6]` with the smallest
  absolute interval (ties prefer upward), and transposes by it. Print the
  chosen interval in the provenance line.
- Transposition is 12-TET. The sources have no quarter tones; state that in
  `references/transforms.md`.
- Spelling uses `pitch.py`, not string replacement:
  1. Build the target key's accidentals from `abc_tools.key_accidentals`.
  2. For each MIDI pitch, enumerate `(letter, accidental, octave)` tuples that
     produce it.
  3. Prefer the spelling whose accidental matches the key signature; then the
     smallest absolute accidental; then the letter that is a scale degree of
     the key; then the direction of melodic motion (sharpen ascending, flatten
     descending); then a fixed letter order.
  4. Emit `^`, `^^`, `_`, `__`, or `=` only when the chosen accidental differs
     from the key's default for that letter.
  5. Choose octave marks: uppercase for MIDI 60–71, lowercase for 72–83,
     apostrophes above, commas below. Verify the emitted pitch by re-parsing.
- Test every target key used in the sample briefs (Dm, Fm, Cm, Hijaz-as-Dm,
  etc.) and both units.

### 6.8 Meter changes, `Z`, ties, chords

- If the slice crosses a meter change, insert `M:<n>/<d>` after each `V:` line
  for the affected bar. The header `M:` is the first bar's meter.
- A whole-bar rest becomes `Z`; a partial rest becomes `z<units>`.
- Ties are emitted only where a duration must be split; the continuation token
  repeats the pitch and carries `-` on the previous token. Verify that the
  re-parsed score has no unresolved tie.
- `--strip-chords` removes all `"..."` tokens. `--keep-chords` keeps only the
  Vocal chords; Ins chords are a parser error by contract.
- **Inline key changes:** three library tracks contain `[K:...]` changes. By
  default `slice` refuses a range that crosses one and says so; choose a
  sub-range inside one key. With `--allow-key-change`, emit a transposed inline
  `[K:<transposed-key>]` at the start of the affected bar. `--to-key` plus
  `--allow-key-change` is only allowed when the modulation can be expressed as
  a standard major/minor key; otherwise fail rather than guess.

### 6.9 Acceptance

- `slice` refuses > 8 bars (and > 16 with `--max-bars 16`).
- Output parses with `abc_tools.parse` for every song and every 8-bar window
  sampled by the test.
- The interval sequence of the sliced notes equals the source interval
  sequence after the declared transposition, exactly, when the unit is auto.
- `--to-key` output uses only the target key's `K:` spelling plus `_`/`^`
  accidentals; a re-parse yields the expected MIDI pitches.
- 1/32 → 1/16 forced rescale reports the altered-note count; the same request
  without `--allow-lossy` fails above the threshold.
- Meter changes and `Z` bars round-trip.
- A range that crosses an inline key change is refused by default and succeeds
  with `--allow-key-change` when the target key is expressible.
- Chord symbols are absent by default and present only in Vocal with
  `--keep-chords`.
- A note that crosses the range start/end is clipped and reported, not silently
  dropped.

---

## 7. Phase 4 — `songmap`

### 7.1 Command

```bash
remix_cli.py songmap <song_id> [--json] [--max-chars 3000]
```

### 7.2 Output (≤ ~300 tokens)

```
yt500-0001-fbK2ySlxAW4 | Maktooba Leek | Elissa | Fm 2/4 70bpm | 186 bars | q1.0
sections: intro 1-8 | verse 9-40 | chorus 41-72 | ...
vocal: 72-82 mean 79 | 553 notes | sil 0.39
ins:   70-92 mean 77 | 302 notes | active 0.38
hooks Vocal: [0,0,2,-2] x7 @ 12,45,88 | [2,1,-1,0,0] x5 @ 21,60
hooks Ins:   [0,3,-2,0] x4 @ 5,33
cadences: 40:65:1 | 72:60:5 | 120:62:1
```

- Header fields from the catalog.
- Sections from `%` comments in the ABC. A section starts at the next voice
  group after the comment and ends before the next section comment. If there
  are no comments, one section `score` covering the whole song.
- Per section: bar range, Vocal active share, Ins active share, density.
- Ranges and means from the parsed notes.
- Hook candidates:
  - For each voice, count exact interval cells of length 4, 5, and 6.
  - Reject cells with fewer than 2 distinct intervals or a pitch span < 3
    semitones; these are repeated-note wallpaper, not hooks.
  - Rank by count descending, then cell length descending, then first bar.
  - Report at most 5 per voice, each with count and up to 6 bar locations.
  - Include a rhythmic-hook line (duration-ratio cells) only when it differs
    from the melodic ranking.
- Ins riff candidates: same algorithm restricted to Ins windows whose start
  and end are within 4 bars.
- Cadence points: segment each voice into runs of consecutive active bars; for
  each run, report the last note as `bar:MIDI:degree` relative to the tonic at
  that bar. Report at most 12; if a voice has no runs, say `none`.
- No maqam claim. Use `key/mode hypothesis` language anywhere a mode is named.
- If the rendered text exceeds `--max-chars`, drop hook occurrence lists
  first, then cadence details; never truncate mid-number. If it still exceeds,
  fail with a suggestion to use `slice`.

### 7.3 Acceptance

- Longest song (~8,972 chars source) produces ≤ 3,000 chars.
- Every hook candidate's interval cell actually occurs at the listed bars;
  verify by slicing the bars and re-computing the cell.
- Sections cover the whole song exactly once.
- `--json` has the same information and the same caps.
- No ABC body is printed; only numbers and short interval tokens.

---

## 8. Phase 5 — `motif-find`

### 8.1 Command

```bash
remix_cli.py motif-find --intervals "0,0,2,-2" [--durations "1,1,2,1"]
                       [--voice Vocal|Ins|both] [--min-run 4] [--limit 10]
remix_cli.py motif-find --contour wave --degree-start 7 --degree-end 0 --bars 2
```

### 8.2 Index

Build once in `library build`:

- For every included song and both voices:
  - interval sequence (semitone deltas between consecutive notes);
  - duration-ratio sequence (note durations divided by the smallest positive
    duration and rounded to 3 decimals; ties merged by the parser);
  - note onset bar index (mapped from `voice.bars`).
- Postings for 4-grams of intervals and 4-grams of duration ratios. Store
  **unique** `song_id|voice` postings per gram to keep the index small.
- `index/manifest.json`: version, k=4, counts, input hash, build options.
- Use compact JSON, sorted keys. If size matters, gzip with `mtime=0` for
  deterministic bytes; the loader transparently handles `.json.gz`.
- Measured estimate: 16,490 distinct 4-gram keys, 368,789 postings over 472
  songs; unique song/voice postings compress to ~600 KB. A plain JSON index is
  ~5 MB; either is acceptable, gzip is preferred for packaging.

### 8.3 Query algorithm

- `--intervals`: parse comma-separated integers. Require at least `--min-run`
  intervals (default 4). Use the first 4 intervals to fetch candidate
  song/voice pairs from the interval index, then load and scan those songs for
  the full pattern. Return all non-overlapping occurrences; cap at 6 per song.
- `--durations`: divide the query sequence by its smallest positive value,
  round to 3 decimals, use the first 4 ratio tokens from the rhythm index, then
  verify the full ratio sequence. Pitch is ignored, so this is rhythm-only.
- Both flags: require both matches at the same note offset.
- `--contour`: scan `--bars`-bar windows in each voice, compute the
  up/down/repeat contour, and keep windows whose start/end scale degrees match
  `--degree-start`/`--degree-end`. This mode is a scan, not an index lookup.
- Minimum-information filter:
  - reject patterns with all-equal intervals (e.g. `0,0,0,0`) unless
    `--allow-trivial`;
  - require at least 2 distinct intervals or a span ≥ 3 semitones;
  - report the filter and the measured base rate in `build_report.json`.
- Ranking: occurrence count desc, song_id asc, start bar asc, voice `Vocal`
  before `Ins`. Cap rows at `--limit` (default 10, hard max 20).
- Each row: `song_id | voice | bars=A-B | match_len=N | occurrences=K | key |
  density`. Add a ready-to-run `slice` hint with the exact bar range.
- The command never prints ABC; it returns locations that feed `slice`.

### 8.4 Acceptance

- Cut a known pattern from a known song (Vocal and Ins), query it, and find
  that song at rank 1.
- Rhythm-only mode finds a song when pitches are replaced but durations are
  kept.
- Both voices are covered by tests.
- The index has no entries for excluded songs.
- A trivial `0,0,0,0` query is refused without `--allow-trivial`.
- Query results are deterministic.
- False-positive base rate: on 50 random unrelated song pairs, the number of
  returned 8+ interval matches is measured and reported; if it is above the
  agreed threshold, raise the minimum-information rule before shipping.

---

## 9. Session ledger

### 9.1 File and defaults

- Default path: `Path.cwd() / ".remix-ledger.jsonl"`.
- Override: `--ledger PATH` or `REMIX_LEDGER`.
- Default cap: **30,000 characters** of library output per session; override
  with `--cap` or `REMIX_BUDGET`.
- The ledger is local state, never shipped in the package. It is appended by
  `catalog`, `songmap`, `slice`, and `motif-find`.
- `library build`, `budget`, `remix check`, and `--help` are not charged.

### 9.2 Record format

One JSON object per line:

```json
{"ts":"2026-11-23T12:00:00Z","tool":"slice","song_id":"yt500-0001-...","chars":842}
```

`ts` is optional and can be omitted for byte-reproducible tests. The total is
the sum of `chars`.

### 9.3 Enforcement

- Render the tool output to a string first.
- If `total + len(output) > cap`, print to stderr:
  `remix budget exceeded: 30120 + 840 > 30000; run budget --reset or raise --cap`
  and exit **3**. Do not print the output.
- If a tool's own output cap is exceeded, exit **4** and print the cap name.
- `budget` prints: total, cap, remaining, call count, per-tool totals.
- `budget --reset` truncates the ledger after confirmation (`--yes` in
  non-interactive use).
- Suggested per-session budget from the proposal:

| Step | Limit | Approx. |
|---|---|---:|
| `catalog` | 5 calls × ≤15 rows | ~2k tokens |
| `songmap` | 4 songs | ~1.2k tokens |
| `slice` | 8 slices × ≤8 bars | ~3–5k tokens |
| `motif-find` | 5 calls | ~1k tokens |

### 9.4 Acceptance

- A call that crosses the cap exits non-zero and prints nothing to stdout.
- `budget` shows the exact total and remains consistent after many calls.
- `--reset` works and is tested.
- Tests use a temp ledger so they never touch a user’s working directory.

---

## 10. Phase 6 — remix plan block and `remix check`

### 10.1 Plan block

Do **not** change the 15 required plan targets. Add an optional top-level
`remix` object; the existing `validate_plan()` ignores it.

```json
"remix": {
  "concept": "one sentence",
  "sources": [
    {
      "id": "yt500-0001-fbK2ySlxAW4",
      "role": "vocal hook",
      "from_bars": "17-20",
      "to_bars": "9-12",
      "transform": ["transpose:+2", "augment:2x", "fragment:first-5-notes"],
      "voice": "Vocal"
    },
    {
      "id": "yt500-0060-...",
      "role": "guitar riff",
      "from_bars": "33-34",
      "to_bars": "5-6, 21-22",
      "transform": ["invert"],
      "voice": "Ins"
    }
  ],
  "literal_cap_bars": 4
}
```

Rules:

- `id` must exist in the library catalog.
- `from_bars` is a valid one-based range in that song.
- `to_bars` is one or more comma-separated one-based ranges in the new score.
- `voice` ∈ `Vocal | Ins | both`.
- `transform` is a list applied left to right; an empty list means a literal
  quote.
- `literal_cap_bars` defaults to 4 if omitted.
- The block is validated by `03_abc_remixer/schemas/remix_block.schema.json`
  (standalone; do not modify the existing plan schema).

### 10.2 Transform vocabulary and matching

Implement in `transforms.py` with a pure function
`apply_transforms(notes, transforms) -> ExpectedQuote` where a note is
`(pitch, duration_quarters)` and `ExpectedQuote` carries interval, duration,
gap, and contour sequences.

| Transform | Effect | Matching |
|---|---|---|
| `transpose:+N` / `transpose:-N` | add N semitones | intervals unchanged |
| `invert` | reflect around the first pitch: `p → 2·p0 − p` | intervals negated |
| `retrograde` | reverse note order | intervals reversed and negated; durations reversed |
| `augment:R` / `diminish:R` | multiply durations by R (`2x`, `0.5x`) | duration ratios normalised |
| `fragment:first-N-notes` | first N notes | expected sequence shortened |
| `fragment:last-N-notes` | last N notes | expected sequence shortened |
| `fragment:A-B` | 1-based note slice | expected sequence shortened |
| `rhythm-only` | ignore pitch | duration sequence only |
| `contour-only` | ignore exact intervals | contour tokens only |

Contour tokens: `R` for a repeated pitch, `u1/u2/u3` for up by 1–2 / 3–4 /
≥5 semitones, `d1/d2/d3` for the same downward. Document the bins in
`references/transforms.md`.

Transforms compose in order. `fragment` before `invert` differs from `invert`
before `fragment`; the tool applies exactly what is declared and says so in
`references/transforms.md`.

### 10.3 Declared-quote verification

For each source item:

1. Load the source song from the store.
2. Extract notes in `from_bars` (clip sustains; include only notes whose onset
   is inside the range).
3. Apply transforms to get the expected interval, duration-ratio, and contour
   sequences.
4. In the target score, search the declared `to_bars` for a contiguous note
   run of the expected length in the declared voice.
5. Compare:
   - exact mode (default): intervals equal and durations equal (or ratios
     equal after a declared augment/diminish);
   - `rhythm-only`: duration ratios equal;
   - `contour-only`: contour tokens equal;
   - `--tolerance N`: allow up to N mismatched positions, and label the match
     `partial`.
6. Report one result per source item:

```json
{
  "id": "...",
  "role": "vocal hook",
  "declared_to_bars": "9-12",
  "status": "verified",
  "voice": "Vocal",
  "actual_bars": "9-12",
  "matched_notes": 8,
  "transform": ["transpose:+2", "augment:2x"],
  "literal": false
}
```

`status` is `verified`, `partial`, or `not_found`; `not_found` includes a
machine-readable reason (`source_not_found`, `bars_out_of_range`,
`no_matching_run`, `transform_invalid`).

A declared quote that is not found is a **warning** by default; with
`--strict-quotes` it is a failure. This lets the model see an honest report
without turning a transcription-level difference into a hard gate.

### 10.4 Undeclared-quote detection

- For each target voice, compute interval sequences.
- Use the motif index to find any library run of **≥8 intervals** matching a
  target run.
- Verify the full run against the candidate song (index gives candidates, not
  proof).
- Exclude runs already covered by a declared quote for that source.
- Require the minimum-information filter from §8.3; otherwise a repeated-note
  run would flag everything.
- Report:

```json
{
  "source_id": "...",
  "voice": "Vocal",
  "target_bars": "41-43",
  "source_bars": "12-14",
  "run": 9,
  "declared": false
}
```

- Default: warning. `--fail-on-undeclared`: failure.
- Cap the list at 10, strongest first.

### 10.5 Metrics

Compute numbers only; no prose judgement.

- **`quote_coverage`**: per voice, the share of all score bars that contain at
  least one note covered by a verified quote. Also report the combined share
  weighted by notes.
- **`literal_share`**: share of all target notes covered by a verified quote
  whose transform list is empty or contains only `transpose` (a pitch-level
  transposition is still literal pitch content; inversion, retrograde,
  augmentation, fragmentation, rhythm-only, and contour-only are not).
- **`max_literal_run_bars`**: the longest bar span of any literal match.
- **`literal_cap_bars`**: from the remix block; default 4. If
  `max_literal_run_bars > literal_cap_bars`, fail.
- **`novelty`**: `1 − max_s(overlap_s)`, where `overlap_s` is the longest
  shared contiguous interval run (in notes) between the target and source `s`,
  divided by the target note count. Search same-voice pairs. Report
  `largest_overlap_source` and `largest_overlap_notes`.
- **`source_diversity`**: number of distinct source songs with ≥1 verified
  quote (not declared).
- **`transform_mix`**: counts per verified transform operation, plus
  `literal` and `partial`.
- Report per voice where meaningful, and a combined block.

### 10.6 Running the unchanged checker

`remix check` calls `ostris.check.check(...)` with the same score and plan,
forwarding `--require-final-rest` and `--strict-style`. It nests the result as
`skill_report`, exactly like `ostris check`. `--ostris-data` selects the
directory holding `priors/` (default: the skill’s `data/ostris`, if present);
when it is absent, prior percentiles are skipped with a warning. The `remix`
object is added at the top level of the report; `class` is `fail` if any hard
checker gate or a remix hard gate fails, `warn` if only warnings, else `pass`.

Hard remix gates:

- `literal_cap_bars` exceeded;
- `--strict-quotes` and a declared quote is `not_found`;
- `--fail-on-undeclared` and an undeclared 8+ run exists.

Everything else (declared not found without strict mode, undeclared without
fail mode, partial matches) is a warning.

### 10.7 Text output

```
remix check: WARN
declared: 3/3 verified, 0 partial, 0 not found
quote coverage: Vocal 6/24 bars (25.0%) | Ins 4/24 (16.7%)
literal: 3.2% notes | max literal run 2 bars (cap 4)
novelty: 0.71 | largest overlap 29% (yt500-0060-...)
sources used: 3 | transforms: transpose 2, invert 1, fragment 1, literal 1
undeclared: 1 (warn; run 9, yt500-0042-...)
checker: PASS (0 hard, 2 style warnings)
```

The model copies this block verbatim into the report. The tool also writes
`report.json` on request.

### 10.8 Acceptance

Synthetic tests must cover:

- an exact quote (transform `[]`) → `verified`, `literal`;
- a transposed quote → `verified`, `literal`;
- an inverted quote → `verified`, not literal;
- a retrograde quote → `verified`, not literal;
- an augmented quote → `verified`, not literal;
- a fragmented quote → `verified`, not literal;
- a rhythm-only quote → `verified`, not literal;
- a contour-only quote → `verified`, not literal;
- a score with no quote → coverage 0, literal 0, novelty 1.0 (or the measured
  non-quote value), no undeclared;
- an undeclared 8-interval run → flagged;
- `literal_cap_bars` enforced;
- `--strict-quotes` turns a not-found into a failure;
- `--fail-on-undeclared` turns an undeclared match into a failure;
- checker contract/sanity failures still fail the combined report.

False-positive test: 50 random unrelated song pairs; report the number of
declared-quote matches (must be 0, because no quote is declared) and the
number of undeclared 8+ runs (measure the base rate; state it honestly). Tune
the minimum-information rule if common repeated-note cells dominate.

---

## 11. Phase 7 — skill, packaging, release

### 11.1 `03_abc_remixer/SKILL.md`

Required order:

1. **Role and rule of the game.** Open creative brief; the library is
   required; every borrowing is declared; the model writes the ABC by hand.
2. **Hard prohibition.** Never `cat`, `head`, `tail`, `grep`, `less`, or
   otherwise read `records.jsonl`, `idioms.jsonl`, `index.json`, shard JSONs,
   or `data/remix/songs/`. Library access only through `remix_cli.py`.
3. **Inputs gate.**
   - Mode A: user supplies fully vocalised Arabic lyrics. Save verbatim to
     `lyrics.txt`; run `syllabify.py`.
   - Mode B: the model writes its own fully vocalised Arabic lyrics, saves
     `lyrics.txt`, runs `syllabify.py`. The library has no lyrics, so
     borrowing is musical only.
   - Mode C: **out of scope.** `syllabify.py` requires a lyrics path; verify
     and document this in the skill rather than pretending a no-lyrics mode
     exists.
   - Maqam/tonic: the model chooses the maqam for the new piece. The library
     has no maqam labels; retrieve by interval/degree/rhythm and re-spell into
     the chosen maqam.
4. **The funnel** (one pass, with call budgets):
   1. Concept (no tool): mood, form, roles that need borrowed material.
   2. `catalog` (≤3–5 queries).
   3. `songmap` on ≤3–4 candidates.
   4. Choose 2–4 source songs and assign one role each.
   5. `slice` the exact bars (≤8 per call).
   6. Write `plan.json` with the `remix` block, then `score.abc` by hand.
   7. `remix check` once; at most one scoped repair.
5. **Plan + score.** The 15 checker targets are unchanged; the remix block is
   additional. Use `slice` output as a reference, never auto-insert it.
6. **Report.** Replace the deviation list with the quote/transform ledger
   (source, bars, role, transform, target bars), then copy the checker’s
   `MEASURED` block and the remix metrics verbatim. Never retype a number.
7. **Offline note.** Say “offline, not auditioned” unless the renderer was
   actually run and heard.
8. **Traps.** Pasting a whole section; quoting without transforming; using one
   source for everything; borrowing on a low-bandwidth channel; claiming an
   audition; reading library files directly; declaring a quote that the check
   cannot find.

Include the exact CLI examples and the hard caps. Include the 4/4 and 2/4
header templates. Do not duplicate the 177-track calibration; link to the
`abc_score_writer` reference as the dialect authority.

### 11.2 Packaging and release

- `scripts/package_remixer.sh` builds `dist/abc_remixer.zip` and
  `dist/releases/abc_remixer-0.1.0.zip`; `--public` builds the no-data variant.
- Add `scripts/release_remixer.sh` or a Make target mirroring `make release`:
  build store, run tests, run offline check, package, checksum.
- Add `dist/RELEASE-0.1.0-remixer.md` and `dist/releases/README.md` row.
- Version constants: `03_abc_remixer/scripts/remix/__init__.py`:
  `REMIX_VERSION = "0.1.0"`, `BASELINE_SKILL_VERSION = "0.3.0"`,
  `STORE_VERSION = "remix-build-v1"`.
- Contract: the remixer does not change the pinned 0.3.0 hashes. The package
  script copies the pinned files and writes their hashes into
  `abc_remixer/scripts/RUNTIME_MANIFEST.json`; the remixer tests verify them.
- Licensing: full data package is internal-use only, same status as the
  `abc_score_writer` full bundle; the public package has no data.

### 11.3 Acceptance

- A clean unzip of `abc_remixer-0.1.0.zip` runs `catalog`, `songmap`, `slice`,
  `motif-find`, `budget`, and `remix check` with no flags and no network.
- `abc_score_writer` 0.3.0 zip is byte-identical to its previous build (or its
  diff is limited to intentionally updated release metadata, not the remixer).
- Existing `make test`, `make selftest`, `make offline-check`, and
  `ostris contract --strict` pass unchanged.

---

## 12. Test plan and acceptance

### 12.1 Unit tests (new)

| Test file | Covers |
|---|---|
| `test_remix_build.py` | idempotence, counts, exclusions, re-parse, join failures, catalog columns, `--include-all` |
| `test_catalog.py` | every filter, deterministic order, `--random --seed`, limit clamp, line width, matched total |
| `test_slice.py` | >8 refusal, parseability, interval preservation, transposition spellings, 1/32→1/16 quantisation, meter changes, `Z`, ties, chord strip, cross-range clipping |
| `test_songmap.py` | 3k cap, section coverage, hook occurrence verification, cadence degrees, no ABC body |
| `test_motif.py` | known-pattern rank 1, rhythm-only, Ins coverage, trivial-pattern refusal, deterministic order, index excludes excluded songs |
| `test_quotecheck.py` | exact/transposed/inverted/retrograde/augmented/fragmented/rhythm/contour, not found, undeclared 8-run, literal cap, strict modes, no-quote score |
| `test_ledger.py` | cap crossing exits 3, stdout empty, budget totals, reset, temp path |
| `test_remixer_skill.py` | package layout, shared-file hashes, prohibition strings, example passes |

### 12.2 Regression tests (unchanged)

- `make test` (currently 43 tests).
- `make selftest`.
- `make offline-check`.
- `python3 02_maqam-score/scripts/ostris_cli.py contract --strict`.
- The `abc_score_writer` example must still pass the checker.
- No changes to `checker.py`, `calibration.json`, or `selftest.sh`.

### 12.3 False-positive check

Take 50 random song pairs from the 472-song store. For each pair, treat song A
as a “new score” and song B as the candidate source, but **remove A from the
library/index before running the check**. Otherwise the check correctly finds
the identical A in the library and the test measures nothing.

- declared-quote count must be 0 (no quote is declared);
- count undeclared 8+ runs against the remaining library.

Report the undeclared base rate. If common cells (repeated notes, stepwise
scalar runs) produce a high rate, tighten the minimum-information rule and
re-measure. Record the chosen threshold and the measured base rate in
`03_abc_remixer/data/remix/build_report.json` and
`docs/remixer-implementation-report.md`.

### 12.4 Integration dry run (scripted)

Use a fixed brief and a fixed seed:

- mode A lyrics with harakat, or mode B model-written lyrics saved to
  `lyrics.txt`;
- run `syllabify.py`;
- run the funnel with the ledger on;
- write `plan.json` and `score.abc`;
- run `remix check --require-final-rest`;
- assert: ledger total < 30,000 chars; checker contract/sanity pass; the remix
  report has ≥1 verified quote and ≥2 distinct sources; no undeclared quote
  unless declared as a warning;
- write the transcript of tool calls and character totals to
  `analysis/eval/runs/<date>-remix-dry-run/`.

The dry run is a tooling test, not a quality claim. It is “offline, not
auditioned”.

---

## 13. Evaluation protocol

### 13.1 Briefs

Five fixed briefs, identical across conditions, e.g.:

1. A melancholic Hijaz piece that grows from a single guitar riff.
2. An upbeat 2/4 piece with a call-and-response hook.
3. A slow 6/8 lament with one borrowed vocal cadence.
4. A 4/4 groove built on a rhythmic skeleton, not a melodic quote.
5. A piece that quotes one Ins riff and inverts it in the final section.

### 13.2 Conditions

- **A. No library.** The existing `abc_score_writer` workflow, priors only.
- **B. Library-guided remix.** The funnel, with the ledger enforced.
- **C. Held-out reference.** A true retrieval-excluded condition.

### 13.3 Fixing condition C

The proposal says the existing 35 held-out songs are excluded from retrieval,
but they are already outside the 482-song library, so condition B already
excludes them. That makes B and C identical for retrieval.

Choose one:

- **C1 (recommended for the first evaluation):** use the existing 35 as an
  external reference only; do not call them a “condition”. Label the runs
  A and B.
- **C2 (true held-out):** create a deterministic 35-song split **from the 482**
  (e.g. `sha256(song_id) mod 10 == 0`, capped at 35), build a second store
  without those songs, and use them only as the novelty/similarity reference
  for condition C. This is the only version that measures retrieval
  generalisation.

Document whichever is chosen in the evaluation report. Do not silently
relabel the existing 35 as a held-out retrieval split.

### 13.4 Metrics

Per run:

- checker pass/fail and warning count;
- `quote_coverage`, `literal_share`, `max_literal_run_bars`, `novelty`,
  `source_diversity`, `transform_mix`;
- total retrieved characters, number of tool calls, number of repair passes;
- whether the score is “offline, not auditioned”.

Human listening/reading review is the only aesthetic judgement and is outside
the tooling. Do not claim quality from these metrics.

---

## 14. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Transcript ↔ record join differs on a refresh | Reuse `link_library`; keep 482/482 regression test; list every unmatched record/track |
| 2 | 1/32 → 1/16 rescale is lossy | `--unit auto` default; forced rescale reports altered notes; fail above threshold |
| 3 | No maqam labels | Key/mode hypothesis only; model re-spells; no classifier in this task |
| 4 | 177 vs 482 calibration mismatch | Do not recalibrate; note it in the report; keep checker thresholds unchanged |
| 5 | Transcription noise | Treat ABC as data, not truth; quotes may carry artifacts; report source and bars |
| 6 | Quote/undeclared false positives | Minimum-information filter; 8-interval threshold; measure 50-pair base rate; tune before release |
| 7 | Store size | 2.5 MB songs + ~5 MB index; gzip the index; catalog < 200 KB; keep remixer out of the `abc_score_writer` zip |
| 8 | Ledger location is read-only | Default to `$PWD`; `--ledger`/`REMIX_LEDGER` override; never ship a ledger |
| 9 | Sibling skill path dependency | Vendor the runtime into `scripts/` at package time; hash-check; test a clean unzip; never use `_shared/` because `ostris` resolves paths relative to `scripts/` |
| 10 | Exact quote matching is too strict | Default exact; `--tolerance N` opt-in; report `partial`; `--strict-quotes` for hard mode |
| 11 | `songmap`/`slice` output cap hides needed material | Hard caps are part of the game; add `songmap --section` and narrower `slice` as the escape hatch |
| 12 | Condition C is not actually held out | Use C2 (new 35-song split) or drop C; document the choice |
| 13 | Re-emission bugs (ties, meter, octave marks) | Parse the output before returning; property tests over every song; no regex rewriting |
| 14 | Model reads library files directly | Skill-level prohibition; only the CLI is documented; review transcripts in evaluation |
| 15 | FADL Ins-only song breaks assumptions | `ins_only` flag; catalog and songmap handle a missing vocal line; slice emits rests |

---

## 15. Implementation order and estimates

| Phase | Deliverable | Est. |
|---|---|---:|
| 0 | Branch, freeze 0.3.0 baseline, fixture songs, test harness, package script skeleton | 0.5 d |
| 1 | `library build` + `build_report.json` + store + index | 1.5 d |
| 2 | `catalog` + ledger + `budget` | 1.0 d |
| 3 | `slice`: emit, pitch spelling, unit policy, meter/ties/chords | 2.5 d |
| 4 | `songmap` | 1.0 d |
| 5 | `motif-find` + both-voice index + rhythm mode | 1.5 d |
| 6 | `remix` block, transforms, quote verification, metrics, `remix check` | 2.5 d |
| 7 | `SKILL.md`, references, example, packaging, release notes | 1.0 d |
| 8 | Integration dry run + A/B/C harness + report | 1.5 d |
| **Total** | | **~13 d** |

Do not start phase 6 before phase 3 is parse-clean on every song. The quote
verifier depends on trustworthy slices and a trustworthy re-emitter.

---

## 16. Definition of done

- [ ] `library build` produces 472 included songs (482 with `--include-all`),
      all re-parsed, with explicit exclusion and join lists.
- [ ] Store is byte-idempotent across two builds.
- [ ] `catalog` filters, caps, and deterministic ordering pass.
- [ ] `songmap` stays under 3,000 chars and its hooks are slice-verified.
- [ ] `slice` refuses >8 bars, emits parseable ABC for 1/16 and 1/32 sources,
      preserves intervals, transposes with correct spelling, handles meter
      changes/`Z`/ties/chords, and reports quantisation.
- [ ] `motif-find` returns the source song at rank 1 for a cut pattern, covers
      both voices, and supports rhythm-only matching.
- [ ] `remix check` verifies every transform in §10.8, detects undeclared 8+
      runs, enforces `literal_cap_bars`, and runs the unchanged checker.
- [ ] Ledger caps a session and `budget` reports totals.
- [ ] `abc_remixer` skill instructions include the funnel, the prohibition,
      the inputs gate, the report format, and the traps.
- [ ] A clean unzip of `abc_remixer-0.1.0.zip` runs offline with no flags.
- [ ] `abc_score_writer` 0.3.0 remains green: 43 tests, selftest, offline
      check, contract pins.
- [ ] No `checker.py`, `calibration.json`, or `selftest.sh` changes.
- [ ] Evaluation report states what was measured and what was not; no aesthetic
      claim from the metrics.
- [ ] Release notes and checksums are added; the full package is internal-use
      only, the public package has no data.

---

## Appendix A — CLI contract

```text
remix_cli.py library build --ostris-data DIR --out DIR [--include-all]
                           [--quality-min F] [--force]
remix_cli.py library verify [--library DIR]
remix_cli.py catalog [filters] [--limit N] [--random --seed N] [--json]
remix_cli.py songmap SONG_ID [--json] [--max-chars N] [--section NAME]
remix_cli.py slice SONG_ID --bars A-B [--voice V] [--to-key K]
                         [--transpose N] [--strip-chords|--keep-chords]
                         [--unit auto|1/16|1/32] [--emit abc|json]
                         [--max-bars 8] [--allow-lossy]
remix_cli.py motif-find --intervals "..." [--durations "..."]
                         [--voice V] [--min-run N] [--limit N] [--json]
remix_cli.py motif-find --contour up|down|wave|flat
                         --degree-start D --degree-end D --bars N
remix_cli.py remix check SCORE --plan PLAN [--report FILE]
                         [--library DIR] [--ostris-data DIR]
                         [--require-final-rest]
                         [--strict-style] [--strict-quotes]
                         [--fail-on-undeclared] [--tolerance N]
remix_cli.py budget [--ledger FILE] [--cap N] [--reset] [--json]
remix_cli.py contract
```

Exit codes: `0` success, `1` check failed, `2` usage, `3` ledger cap,
`4` tool output cap, `5` library missing/corrupt, `6` internal re-parse bug.

## Appendix B — Data contracts

`catalog.tsv` — one header row, tab-separated, columns as §4.4.

`catalog_meta.json`:

```json
{
  "store_version": "remix-build-v1",
  "baseline_skill_version": "0.3.0",
  "included": 472,
  "excluded": 10,
  "density_bands": {"light_max": 4.48, "busy_min": 6.13},
  "unit_counts": {"1/16": 266, "1/32": 216},
  "catalog_sha256": "...",
  "index_sha256": "..."
}
```

`index/manifest.json`:

```json
{
  "store_version": "remix-build-v1",
  "k": 4,
  "songs": 472,
  "voices": ["Vocal", "Ins"],
  "interval_grams": 16490,
  "interval_postings": 368789,
  "rhythm_grams": null,
  "rhythm_postings": null,
  "min_information": {"distinct_intervals": 2, "span_semitones": 3},
  "inputs_sha256": "..."
}
```

`null` rhythm counts mean “filled by the actual build”; `build_report.json`
always carries the real numbers. The interval counts above are measured on the
472-song default store.

`remix_block.schema.json` — required `concept`, `sources`; each source
requires `id`, `role`, `from_bars`, `to_bars`, `voice`; `transform` is an array
of strings; `literal_cap_bars` is a positive integer.

`remix_report.schema.json` — extends the idea of `report.schema.json` with a
`remix` object; `class` ∈ `pass|warn|fail`; `skill_report`, `quotes`,
`undeclared`, `metrics`, and `checker` are required.

## Appendix C — Key algorithms (pseudo-code)

### C.1 Build one song

```python
link = links[record["id"]]
text = link["abc_text"]
canonical = canonicalize(text)
if not canonical.ok: record_failure("canonical", ...)
parsed = parse_abc(canonical.text)
if not parsed.ok: record_failure("parse", ...)
if not include(record): record_exclusion(...); continue
write(songs / f"{sid}.abc", canonical.text)
row = catalog_row(record, parsed)
```

### C.2 Slice one bar

```python
def render_bar(notes, chords, bar_start, bar_len, meter, unit_den, key):
    units = Fraction(bar_len * unit_den, 4)  # 4/4 bar at 1/16 = 16 units
    events = clip_and_fill(notes, bar_start, bar_len)
    tokens = []
    for event in events:
        if event.is_rest:
            tokens.append(f"z{event.units}")
        else:
            for i, part in enumerate(split_legal(event.units)):
                token = spell(event.pitch, key)
                token += "" if part == 1 else str(part)
                if i < len(parts) - 1:
                    token += "-"
                tokens.append(token)
    line = "".join(tokens) + "|"
    assert parse_abc(wrap_header(line, meter, unit_den, key)).ok
    return line
```

### C.3 Verify a declared quote

```python
expected = apply_transforms(source_notes_in_range, transforms)
for target_range in parse_ranges(item.to_bars):
    for voice in voices_for(item.voice):
        for start in starts_in_range(score, voice, target_range):
            if matches(score, voice, start, expected, mode, tolerance):
                return verified(...)
return not_found(...)
```

### C.4 Metrics

```python
quote_notes = union(verified_matches)
literal_notes = union(m for m in verified_matches if m.literal)
quote_coverage[v] = bars_with_quote(v) / total_bars
literal_share = len(literal_notes) / total_target_notes
max_literal_run_bars = max(span_bars(m) for m in verified_matches if m.literal)
novelty = 1 - max(longest_shared_run(target, source) / total_target_notes
                  for source in library)
source_diversity = len({m.source_id for m in verified_matches})
transform_mix = Counter(t for m in verified_matches for t in m.transforms)
```

### C.5 Ledger charge

```python
def charge(tool, song_id, text):
    total = ledger.total()
    if total + len(text) > ledger.cap:
        fail(3, f"remix budget exceeded: {total} + {len(text)} > {ledger.cap}")
    ledger.append({"tool": tool, "song_id": song_id, "chars": len(text)})
    return text
```

---

## Appendix D — First commands after approval

```bash
# 0. Prove the baseline is still green
make test && make selftest && make offline-check
python3 02_maqam-score/scripts/ostris_cli.py contract --strict

# 1. Create the branch and fixture harness
git switch -c feat/remixer
# add 03_abc_remixer/, scripts/package_remixer.sh, Makefile targets

# 2. Build the store
python3 03_abc_remixer/scripts/remix_cli.py library build \
  --ostris-data 02_maqam-score/data/ostris \
  --out 03_abc_remixer/data/remix

# 3. Inspect the build report, not the corpus
python3 03_abc_remixer/scripts/remix_cli.py library verify
python3 03_abc_remixer/scripts/remix_cli.py budget --reset
python3 03_abc_remixer/scripts/remix_cli.py catalog --limit 5
python3 03_abc_remixer/scripts/remix_cli.py songmap yt500-0001-fbK2ySlxAW4
python3 03_abc_remixer/scripts/remix_cli.py slice yt500-0001-fbK2ySlxAW4 --bars 17-20
```

Do not `cat` any file under `data/remix/`. The build report is the only
whole-store artifact a developer should read directly; the model reads only
tool output.
