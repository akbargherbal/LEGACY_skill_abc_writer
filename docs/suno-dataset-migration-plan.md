# SUNO remixer library migration plan (rev 2)

**Status:** implemented (rev 2) · **Date:** 2026-11-24
**Goal:** replace the **verbatim material library** used by `abc_remixer` with
`data/SUNO_ABC_SCORE_DATASET.pkl`, while leaving the aggregate corpus artifacts
used by `abc-score-writer` (`priors/`, `idioms.jsonl`, `similarity/index.json`)
untouched.
**Scope:** `03_abc_remixer/` first. `02_maqam-score/` runtime and data are
**not** rebuilt or changed.

> **Revision note.** The first draft also proposed regenerating the OSTRIS
> priors/idioms/similarity and recalibrating the 177-track gates. That is not
> needed for the copyright concern. The actual exposure is the remixer's
> `slice` command and literal quotes, which return source ABC bars. The
> aggregate statistics are not the verbatim path. This revision keeps the
> aggregate data frozen and swaps only the material library.

## Implementation result

Implemented on 2026-11-24:

| Item | Result |
|---|---|
| Raw input | `data/SUNO_ABC_SCORE_DATASET.pkl`, sha256 `4217a4f1…78ac`, now trackable in git |
| Canonical builder | `tools/build_suno_library.py` → `data/suno/` (670 rows, 670 parse) |
| Canonical bundle | `data/suno/dataset.json`, `catalog_source.jsonl`, `manifest.json`, `songs/` (4.2 MB) |
| Remixer store | `03_abc_remixer/data/remix/` rebuilt: **670** included, 0 excluded, 644 vocal, 26 `Ins`-only, store `remix-build-v2` (4.7 MB) |
| Version | `abc_remixer` 0.2.0 |
| Priors | fixed snapshot vendored at `data/remix/priors/` |
| Guards | only `suno-*` ids; legacy ids resolve as `source_not_found` |
| Tests | 57 remixer tests (54 previous + 2 SUNO builder tests + 1 legacy-id guard); skill tests unchanged |
| Packaging | `dist/abc_remixer.zip` full (with data); `abc_remixer-public.zip` code-only |
| Score writer | unchanged: `make test`, `make selftest`, `make offline-check` pass |

The phase list below remains as the implementation record.

---

## 1. The distinction that matters

| Artifact | What it is | Is it verbatim expression? | Action |
|---|---|---|---|
| `02_maqam-score/data/ostris/priors/` | distributions (bars, tempo, density, register, …) | no — statistics | **keep as-is** |
| `02_maqam-score/data/ostris/idioms.jsonl` | 2–4 bar interval/rhythm sequences | no ABC text; derived structural descriptors | **keep as-is** |
| `02_maqam-score/data/ostris/similarity/index.json` | k-gram postings over idioms | no — retrieval metadata | **keep as-is** |
| `02_maqam-score/data/ostris/records.jsonl` | per-track metadata + features | no ABC text | **keep as-is** |
| `03_abc_remixer/data/remix/songs/*.abc` | source ABC bars returned by `slice` | **yes** | **replace with SUNO** |
| `03_abc_remixer/data/remix/catalog.tsv` | titles, artists, ids, measurements of the above | metadata, but tied to the source list | **rebuild from SUNO** |
| `03_abc_remixer/data/remix/index/` | 4-gram postings into the above songs | pointers to the source list | **rebuild from SUNO** |

`abc-score-writer` never pastes a corpus song into its output. It reads
statistics and structural exemplars. The remixer does paste material: `slice`
emits exact source bars, and `remix check` verifies literal quotes. That is the
part that should draw from a corpus you control.

**Therefore:** the migration is a **remixer-only data swap**, not a rebuild of
the whole corpus stack.

---

## 2. Current usage, for context

### 2.1 `abc-score-writer` — unchanged

| Path | Read by | Role |
|---|---|---|
| `data/ostris/priors/priors.json` + strata | `plan`, `check` | numeric targets and prior percentiles |
| `data/ostris/idioms.jsonl` | `exemplar`, `similarity --build` | structural phrases |
| `data/ostris/similarity/index.json` | `similarity --score`, `check` | k-gram quotation checks |
| `data/ostris/source/` | `audit`, `build`, `features`, `eval` | regeneration only |

No runtime change is proposed. The 482-record bundle, the 29 prior strata, the
idiom bank and the similarity index stay where they are. The 177-track
calibration in `scripts/calibration.json` stays frozen too.

### 2.2 `abc_remixer` — the only thing that changes

| Path | Read by | Role |
|---|---|---|
| `data/remix/catalog.tsv` | `catalog`, `songmap`, `slice`, `motif-find`, `remix check` | 472-song discovery |
| `data/remix/songs/*.abc` | `songmap`, `slice`, `motif-find`, `remix check` | the verbatim material |
| `data/remix/index/` | `motif-find`, `remix check` | 4-gram postings |
| `data/remix/catalog_meta.json`, `build_report.json` | `library verify`, humans | counts and hashes |
| `02_maqam-score/data/ostris/records.jsonl` + `source/` | `library build` | **the coupling to remove** |
| `data/ostris/priors` (optional) | `remix check` | advisory percentiles |

Today the library is a filtered view of the OSTRIS corpus. The build reads the
other skill's `records.jsonl` and `source/`; every song id is `yt500-…` or
`fs18-…`; tests and examples hard-code those ids and counts 472/482.

---

## 3. Target

```
data/SUNO_ABC_SCORE_DATASET.pkl          frozen raw input
        │
        ▼  tools/build_suno_library.py   (new, deterministic)
data/suno/                               canonical intermediate (optional but useful)
  dataset.json                           id, n, hash, provenance, counts
  songs/suno-0000.abc … suno-0669.abc
  catalog_source.jsonl                   id, key, meter, tempo, bars, sections, flags
        │
        ▼  remix library build --dataset suno
03_abc_remixer/data/remix/
  dataset.json                           dataset id + source hash + counts
  catalog.tsv                            only suno-* ids
  songs/suno-*.abc
  index/motif.json.gz
  catalog_meta.json
  build_report.json
  priors/                                fixed vendored snapshot (not rebuilt)
```

The intermediate `data/suno/` is recommended for one reason: it gives both the
remixer and a future aggregate refresh the same canonical source, and it lets
`--check` validate the dataset without rebuilding a store. If a direct
pickle→store path is preferred, the same code can do it in one step; the
contract is what matters, not the extra directory.

---

## 4. What the SUNO pickle gives the remixer

Verified on 2026-11-24 with the existing `abc_tools.parse`:

| Fact | Value |
|---|---:|
| Rows / unique ids / unique ABC texts | 670 / 670 / 670 |
| Parse | **670/670** |
| With vocal notes | **644** |
| Without vocal notes | **26** (usable as `Ins`-only sources) |
| Without instrumental notes | 1 |
| Voices per score | `Vocal` + `Ins` |
| Keys | 635 minor / 35 major |
| Meters | `4/4` 411, `2/4` 236, `6/8` 10, `3/4` 7, others 6 |
| Tempo | 57–172 BPM, median 93 |
| Bars | 57–461, median 148.5 |
| Chords | present in all 670 |
| Section labels | `% verse` 1,786, `% chorus` 1,740, `% interlude` 1,185, `% intro` 667, `% outro` 267, `% bridge` 43, `% pre-chorus` 27, `% silence` 34 |
| Titles / artists | empty (`T:` is blank, no metadata columns) |
| Lyrics | none |
| Maqam labels | none |
| Audio | none |
| Pickle size / ABC text | 2.6 MB / 2.69 M chars |

This is a good **material** library for the remixer: enough songs, both voices,
chords, sections and meter variety. The missing title/artist/quality metadata
only affects catalog presentation, not extraction.

---

## 5. Fields for the rebuilt remixer store

Keep the existing 30-column `catalog.tsv` schema; only the values change.

| Field | Value |
|---|---|
| `song_id` | `suno-0000` … `suno-0669` |
| `title` | `""` or the id; do not invent titles |
| `artist` | `""` |
| `key`, `mode`, `meter`, `meters`, `tempo`, `bars` | parsed from the ABC |
| `section_count` | count of `%` section labels |
| `density`, `silence`, `vocal_*`, `ins_*`, `notes_*`, `unit`, `repeated_pitch_share`, `duration_variety`, `ins_active_share` | existing `_catalog_row` logic |
| `quality` | `null` (no reviewer) |
| `source` | `"suno_abc_score_dataset"` |
| `flags` | `no_vocal_notes` for the 26, else empty |
| `ins_only` | `1` for the 26 |
| `excluded_reason` | `""` |
| `abc_sha256` | sha256 of the stored ABC |

Recommendations:

- **Include all 670.** The 26 vocal-empty scores still have `Ins` material and
  the quote checker already falls back to `Ins` when `Vocal` is empty.
- **Set `quality=null`** and change the catalog default sort to `bars` or
  `random`. A synthetic `1.0` would imply a ranking that does not exist.
- **Use `suno-XXXX` as the display title** in catalog lines. No fake artist or
  title metadata.
- **Keep title/artist filters in the code**, but document that they are empty
  for this dataset; discovery should use key, mode, meter, tempo, bars, density
  and random seed.

---

## 6. Implementation phases

### Phase 0 — freeze and provenance (0.5 day)

1. Tag the current state (`abc_remixer` 0.1.0) so the old store is recoverable.
2. Add `data/SOURCE.md` (or `data/suno/PROVENANCE.md`) covering:
   - which Suno plan/terms produced the scores;
   - model/version and generation dates;
   - whether prompts referenced existing songs, artists or melodies;
   - who or what produced the ABC text;
   - who owns the lyrics, if any;
   - `source_sha256` of the pickle.
3. Decide how the pickle is versioned. It is currently in `.gitignore`; either
   commit it, use Git LFS, or record its hash and keep a mirrored copy.
4. Do **not** delete the old remixer store. Keep it as the rollback path.

**Exit:** the dataset has a written provenance record and a stable hash.

### Phase 1 — canonical library builder (1 day)

Add `tools/build_suno_library.py`:

```bash
python3 tools/build_suno_library.py \
  --pkl data/SUNO_ABC_SCORE_DATASET.pkl \
  --out data/suno \
  --check
```

Work:

- load the pickle; validate `SUNO_ID`, `abc`, `abc_lines`, `abc_encoding`;
- assert 670 unique padded ids and 670 unique ABC texts;
- canonicalise each score with `ostris.canonical.canonicalize`; preserve
  `Vocal`/`Ins`, inline `M:`/`K:` changes and `%` sections;
- parse with `abc_tools.parse`; abort on any failure;
- write `songs/<id>.abc`, `catalog_source.jsonl`, `dataset.json` and
  `manifest.json`;
- compute `section_count` from `%` labels;
- make output deterministic (sorted JSON, `SOURCE_DATE_EPOCH=0`, no timestamps
  unless `--timestamp`);
- `--check` validates an existing bundle against the pickle and reports:
  670 rows, 670 parse, 644 vocal, 26 ins-only, matching hashes.

This builder does not read `02_maqam-score/data/`. It depends only on the
pickle and the shared parser.

**Exit:** two consecutive builds are byte-identical; `--check` passes.

### Phase 2 — rebuild the remixer store from SUNO (1 day)

1. Refactor `03_abc_remixer/scripts/remix/build.py`:
   - extract the existing catalog-row computation into a function that takes a
     parsed score + optional metadata;
   - add `build_suno(dataset_dir, out)`;
   - keep `build_from_ostris(...)` as a developer-only adapter (or delete it
     after the new path is proven);
   - write `dataset.json` into the store.
2. Change the CLI:
   ```bash
   python3 03_abc_remixer/scripts/remix_cli.py library build \
     --dataset suno --data data/suno --out 03_abc_remixer/data/remix
   ```
   Remove `--ostris-data` as the default build path. If kept for one release,
   make it explicit and deprecated.
3. Rebuild the store and verify:
   ```bash
   python3 03_abc_remixer/scripts/remix_cli.py library verify
   python3 03_abc_remixer/scripts/remix_cli.py catalog --key Dm --limit 5
   python3 03_abc_remixer/scripts/remix_cli.py slice suno-0000 --bars 1-4
   python3 03_abc_remixer/scripts/remix_cli.py songmap suno-0000
   ```
4. Remove the runtime cross-read:
   - `shared.ostris_data_dir()` must not be a default for the remixer;
   - `remix check` reads `03_abc_remixer/data/remix/priors/priors.json` if it
     exists, else skips prior percentiles;
   - vendor **one fixed copy** of the existing
     `02_maqam-score/data/ostris/priors/` tree into the remixer store and check
     it in. Do not copy it during the build: the build must not depend on
     `02_maqam-score/data/`.
5. Update `catalog_meta.json` and `build_report.json`:
   - `records=670`, `included=670`, `excluded=0`;
   - `dataset="suno_abc_score_dataset"`;
   - source hash, catalog hash, index hash;
   - flags: 26 `no_vocal_notes`.
6. Add a store-level guard: every catalog row's `source` must be
   `suno_abc_score_dataset`, and every `song_id` must start with `suno-`.
   `library verify` fails if a legacy id is present.

**Exit:** `make remix-build`, `make remix-verify`, `make remix-offline` and
`make remix-test` pass. The build works from a checkout with no
`02_maqam-score/data/` at all; the priors snapshot is vendored inside the
remixer store.

### Phase 3 — verbatim-borrowing guardrails (0.5 day)

This is the safety layer that makes “borrow verbatim” defensible.

1. **Dataset allow-list in the plan check.** `remix.sources[].id` must resolve
   to a row whose `source` is the cleared dataset. Reject `yt500-…`, `fs18-…`
   and any id not in the current catalog with `source_not_found`.
2. **Store provenance.** Add `dataset` to `catalog_meta.json` and
   `dataset.json`; `remix check` echoes it in the report:
   `library: suno_abc_score_dataset v1`.
3. **No silent legacy fallback.** `Store.require()` must not search a sibling
   data directory. One store, one dataset.
4. **Keep the existing quote rules.** The 4-bar literal cap, transformation
   vocabulary, and `literal_share`/`source_diversity` metrics stay. They are
   quality guardrails, not a licence.
5. **Report attribution.** Add one line to the remix report template:
   “Library: SUNO ABC Score Dataset v1 (project-compiled).”
6. **Optional hardening:** persist the prompt/provenance id per source row in
   `catalog_source.jsonl` (e.g. a batch id), so a future audit can trace a
   borrowed phrase back to its generation batch. Do not expose the full prompt
   in the catalog.

**Exit:** a plan quoting a legacy id fails; a plan quoting `suno-XXXX` passes;
the report names the dataset.

### Phase 4 — docs, tests, packaging (1 day)

- `03_abc_remixer/SKILL.md`:
  - “472-song Arabic transcription library” → “670-score SUNO ABC library”;
  - “transcriptions” → “project-compiled symbolic scores”;
  - update the example ids from `yt500-…` to `suno-…`;
  - keep “no lyrics”, “no maqam labels” and the literal-cap rules;
  - state that the library is the cleared material source and that legacy ids
    are not accepted.
- `03_abc_remixer/tests/`:
  - read counts from `catalog_meta.json`/`dataset.json` instead of hard-coding
    472/482;
  - replace `SAMPLE_SONG` and all example ids;
  - assert `verify()` returns 670;
  - assert no catalog row has a legacy source;
  - assert a legacy id is rejected by `remix check`;
  - keep the no-audio test.
- `Makefile`: `remix-build` uses `--dataset suno --data data/suno`;
  `remix-offline` uses `suno-0000`.
- `scripts/package_remixer.sh`:
  - include `dataset.json`;
  - stop copying `02_maqam-score/data/ostris/priors` at package time; ship the
    remixer's own `data/remix/priors` snapshot instead;
  - add a packaging grep test for `yt500-`, `fs18-`, `fadl`, `OSTRIS` in the
    shipped `data/`.
- `03_abc_remixer/example/README.md` and `example/plan.template.json`: replace
  both `yt500-…` source ids and the slice example with `suno-…` ids.
- `README.md`, `03_abc_remixer/CHANGELOG.md`.

**Exit:** both remixer zips build; the default store has no legacy ids; the
public variant is code-only as before.

### Phase 5 (deferred) — optional aggregate refresh

This is **not** required for the copyright goal and should be a separate
decision later.

If you later want `abc-score-writer`'s priors/idioms/similarity to come from the
same SUNO corpus for consistency:

- add a SUNO adapter to `ostris/features.py` and `ostris/eval.py`;
- rebuild `priors/`, `idioms.jsonl` and `similarity/index.json`;
- compare distributions before replacing anything;
- keep the 177-track calibration frozen unless a separate recalibration plan is
  signed off.

Until then, the OSTRIS aggregate bundle stays exactly as it is.

---

## 7. Why this is safer, and what it does not solve

**Safer because:**

- the remixer's verbatim path (`slice`, literal quotes, `songmap`, `motif-find`)
  now points at a corpus you compiled;
- the legacy YT500/FADL-derived ABC text is no longer in the shipped remixer
  store;
- the catalog no longer carries third-party titles and artists for the material
  it quotes;
- the output report can name a single, auditable dataset.

**Still needs care:**

- “compiled myself” is not a licence conclusion. Suno’s terms, the prompts
  used, and the ABC-generation method determine whether the scores are safe to
  redistribute.
- If a prompt referenced an existing song or artist, the generated score may
  still be derivative.
- If the ABC was produced by transcribing audio, there is a second layer of
  uncertainty.
- Aggregate priors and idiom sequences are lower-risk than verbatim ABC, but
  they are not automatically copyright-free either.

**Mitigation:** the provenance record in Phase 0, the dataset allow-list in
Phase 3, and the existing public/code-only packaging split.

---

## 8. Decisions to confirm

| ID | Decision | Recommendation |
|---|---|---|
| **R1** | Scope | Remixer-only data swap; leave `02_maqam-score/data/ostris/` untouched |
| **R2** | Intermediate bundle | Build `data/suno/` once, then build the store from it; keep `--check` |
| **R3** | Inclusion | All 670; 26 are `Ins`-only |
| **R4** | Quality | `null`; default sort by bars/random |
| **R5** | Titles/artists | Empty; use `suno-XXXX` as the display id |
| **R6** | Legacy ids | Reject in `remix check`; no fallback |
| **R7** | `remix check` priors | Vendor one fixed priors snapshot in the remixer store; optional at runtime |
| **R8** | Public packaging | Code-only until the provenance record is complete |
| **R9** | Aggregate refresh | Deferred; separate plan |
| **R10** | Pickle tracking | Commit/LFS it or pin its hash and mirror it |

---

## 9. Acceptance criteria

| Check | Command | Expected |
|---|---|---|
| Dataset shape | `python3 tools/build_suno_library.py --pkl … --out data/suno --check` | 670 rows, 670 parse, 644 vocal, 26 ins-only |
| Reproducibility | build twice to temp dirs | identical hashes |
| Remixer build | `make remix-build` | 670 included, 0 excluded |
| Store verify | `make remix-verify` | 670 songs, hashes match, no legacy ids |
| Remixer tests | `make remix-test` | pass |
| Offline tools | `make remix-offline` | catalog/songmap/slice/motif/budget pass |
| Quote guard | `remix check` with `suno-0000` | passes |
| Legacy guard | `remix check` with `yt500-0001-…` | fails `source_not_found` |
| Packaging | `make remix-zip` | no legacy ids or `source/` in the shipped data |
| Unchanged skill | `make test`, `make selftest`, `make offline-check` | still pass; no `02_maqam-score/data/` edits |

---

## 10. Rollback

1. Tag `pre-suno-remixer`; confirm
   `dist/releases/abc_remixer-0.1.0.zip` is present.
2. Keep both stores during the transition:
   - `03_abc_remixer/data/remix-ostris/` (old, dev-only)
   - `03_abc_remixer/data/remix/` (new SUNO)
3. Add a temporary `--library` override so a failed run can point back at the
   old store.
4. Do not delete the old store until one successful release on the new data.

---

## 11. File-by-file touch list

**New**

- `tools/build_suno_library.py` — pickle → `data/suno/` canonical bundle
- `data/SOURCE.md` or `data/suno/PROVENANCE.md` — licence/provenance record
- `data/suno/dataset.json`, `data/suno/catalog_source.jsonl`
- `03_abc_remixer/data/remix/dataset.json`
- tests for the builder, the SUNO store, the legacy-id guard and packaging

**Changed**

- `03_abc_remixer/scripts/remix/build.py` — `build_suno`, generic row builder
- `03_abc_remixer/scripts/remix/cli.py` — `library build --dataset suno --data`
- `03_abc_remixer/scripts/remix/shared.py` — remove the OSTRIS data default
- `03_abc_remixer/scripts/remix/quotecheck.py` — local priors or none
- `03_abc_remixer/scripts/remix/catalog.py` — default sort if `quality` is null
- `03_abc_remixer/SKILL.md`, `CHANGELOG.md`
- `03_abc_remixer/example/README.md`, `example/plan.template.json`
- `03_abc_remixer/tests/*`
- `scripts/package_remixer.sh`
- `Makefile`
- `README.md`, `docs/README.md`

**Unchanged**

- `02_maqam-score/data/ostris/` (all priors, idioms, similarity, records, source)
- `02_maqam-score/scripts/` runtime
- `calibration.json` and the 177-track calibration
- `checker.py`, `abc_tools.py`, `syllabify.py`

---

## 12. Definition of done

- The remixer store is built only from the SUNO pickle.
- No remixer runtime or build path reads `02_maqam-score/data/`.
- Every catalog row is `suno-*` with `source="suno_abc_score_dataset"`.
- The old aggregate artifacts are untouched and still pass
  `make offline-check`.
- A legacy id in a remix plan is rejected, and the report names the dataset.
- The provenance record exists, so “we can use this corpus” has a written basis.
