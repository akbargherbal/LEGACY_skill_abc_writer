# Remixer 0.1.0 — implementation report

**Status:** implemented on top of `abc_score_writer` 0.3.0.
**Plan:** `docs/remixer-implementation-plan.md`
**Source:** `03_abc_remixer/`
**Package:** `dist/releases/abc_remixer-0.1.0.zip`
**Date:** 2026-11-23.

## 1. What shipped

| Component | Result |
|---|---|
| `library build` | 482 records, 482 linked, 482 with ABC, 482 canonical + parsed; **472 included**, 10 `exclude_from_priors` |
| Store | 472 one-song ABC files, `catalog.tsv` (103 KB), `catalog_meta.json`, `build_report.json` |
| Motif index | 16,490 interval 4-gram keys, 155,354 unique song/voice postings; 1,573 rhythm grams, 42,030 postings; 780 KB gzip |
| Units | included store: 263 × `L:1/16`, 209 × `L:1/32`; all 482 source records: 266 / 216 |
| `catalog` | filters + 40-row hard cap + deterministic random seed |
| `songmap` | 3,000-character cap; sections, hooks/riffs, cadence degrees |
| `slice` | 8-bar default / 16-bar ceiling; exact re-emission; transposition; meter changes; `Z`; ties; optional chords; quantisation report |
| `motif-find` | interval, duration-ratio, and contour queries; both voices; whole songs |
| Ledger | 30,000-character default; exits 3 before crossing; `budget` summary/reset |
| `remix check` | declared quote verification for 8 transform families, undeclared 8+ run detection, literal cap, unchanged checker |
| Skill | `SKILL.md`, dialect/transform references, schemas, workflow example |
| Package | full and public archives, vendored 0.3.0 runtime with hash manifest |

Measured store shape:

```text
records   482
linked    482
with ABC  482
included  472
excluded   10 (exclude_from_priors)
ins_only    1 (fs18-al_qissa_wama_fiha_2510759693)
```

## 2. Tests

- Remixer: **53 tests** (`cd 03_abc_remixer && python3 -m unittest discover -s tests -t . -v`).
- Existing skill: **43 tests** pass unchanged.
- `make selftest`: PASS.
- `make offline-check`: PASS.
- `ostris contract --strict`: pinned.
- `make remix-offline`: PASS.
- `make remix-verify`: PASS (472/472 re-parse; catalog hash matches).

Coverage includes idempotent build, catalog filters/caps, one-32nd slice
round-trips, forced-unit quantisation, meter changes, key-change refusal,
hook verification by slicing, interval/rhythm/contour search, all eight
transform families, literal cap, undeclared detection, ledger cap/reset, and
package layout.

### False-positive probe

50 random song pairs (200 same/different-voice comparisons, seed 1) produced
**2** duration-matched 8+ interval runs (1.0% of voice pairs), both in the Ins
voice. That is the residual base rate of the undeclared-quote detector; it is
reported as a warning by default and is not treated as a hard failure. The
declared-quote path is exact, so it has no comparable false positive by
construction.

## 3. Package

```bash
make remix-build      # regenerate the store
make remix-test       # 53 tests
make remix-verify     # re-parse 472 songs
make remix-zip        # dist/abc_remixer.zip
make remix-zip-public # dist/abc_remixer-public.zip (no data)
make remix-release    # versioned archives + checksums
```

The full archive vendors the 0.3.0 runtime into `abc_remixer/scripts/`; it does
not depend on a sibling `abc_score_writer/` at runtime. The public archive has
no `data/` and needs `--library` for retrieval.

## 4. Deviations from the proposal

1. **`L:1/32` is a first-class output.** The store has 209/472 songs at 1/32.
   `slice --unit auto` preserves the source unit; forcing 1/16 reports
   quantisation and refuses above a threshold unless `--allow-lossy`.
2. **Sibling packaging is self-contained.** The proposal suggested reusing
   `abc_score_writer/scripts` by path. The installed package copies the runtime
   into its own `scripts/` because `ostris/check.py` and `ostris/contract.py`
   resolve paths relative to `scripts/`.
3. **Declared quote matching is exact by default.** `--tolerance N` opts into
   partial matches. A not-found quote is a warning unless `--strict-quotes`.
4. **Undeclared detection also checks durations.** The interval-only 8-run rule
   produced many false positives on common repeated-note cells; requiring the
   same duration sequence removed them in the synthetic quote test. The
   minimum-information filter remains (≥2 distinct intervals).
5. **Ledger lives in the working directory.** Installed `data/` may be
   read-only; the default is `$PWD/.remix-ledger.jsonl`, not `data/remix/.ledger`.
6. **Mode C is out of scope.** `syllabify.py` requires a lyrics file; no
   no-lyrics mode was invented.
7. **Condition C in the evaluation needs a new split.** The existing 35
   held-out YT500 tracks are already outside the 472-song store. A true
   retrieval-held-out condition requires a deterministic 35-song split of the
   482, as described in the plan.

## 5. Not done

- The A/B/C evaluation runs have not been produced. The tooling is ready; the
  five fixed briefs and the evaluation report are next.
- Human listening/reading review is outside the tooling.
- No maqam labels were added; the library has none.
- The 177-track calibration was not recalibrated against the 482-track library.

## 6. Quick verification

```bash
python3 03_abc_remixer/scripts/remix_cli.py library verify
python3 03_abc_remixer/scripts/remix_cli.py catalog --key Dm --limit 3
python3 03_abc_remixer/scripts/remix_cli.py songmap yt500-0001-fbK2ySlxAW4
python3 03_abc_remixer/scripts/remix_cli.py slice yt500-0001-fbK2ySlxAW4 --bars 34-37 --to-key Dm
python3 03_abc_remixer/scripts/remix_cli.py motif-find --intervals "0,-2,0,-2" --limit 3
python3 03_abc_remixer/scripts/remix_cli.py budget
```
