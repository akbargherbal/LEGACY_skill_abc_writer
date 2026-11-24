# Release 0.1.0 — abc_remixer

**Date:** 2026-11-23
**Skill:** `abc_remixer` 0.1.0
**Baseline:** `abc_score_writer` 0.3.0 (runtime, checker, calibration, parser)
**Evidence:** `docs/remixer-implementation-report.md`
**Plan:** `docs/remixer-implementation-plan.md`

---

## What this release is

A sibling skill that turns a 472-song transcription library into bounded remix
material. The model can discover songs, inspect structure, slice exact bars,
search patterns, write a score by hand, and declare every borrowing for
mechanical verification — without ever loading the corpus into context.

The checker is unchanged. `remix check` runs the 0.3.0 contract and sanity
gates, then adds quotation metrics.

## Included

- `library build` / `library verify`
- `catalog`, `songmap`, `slice`, `motif-find`
- session ledger and `budget`
- `remix check` with declared-quote verification and undeclared-run detection
- `SKILL.md`, references, schemas, workflow example
- prebuilt store: 472 songs, catalog, both-voice motif index

## Measured store

| Item | Value |
|---|---:|
| Records | 482 |
| Linked / with ABC | 482 / 482 |
| Included | 472 |
| Excluded | 10 (`exclude_from_priors`) |
| `L:1/16` / `L:1/32` included | 263 / 209 |
| Catalog | 103 KB |
| Motif index | 780 KB gzip |
| Songs | 2.5 MB on disk |
| Ins-only song | 1 (`al_qissa_wama_fiha`) |

## Tests

- 53 remixer tests
- 43 unchanged `abc_score_writer` tests
- `make selftest`, `make offline-check`, `make remix-offline`, `make remix-verify`
- `ostris contract --strict` pinned

## Install

```bash
unzip -q abc_remixer-0.1.0.zip
cd abc_remixer
python3 scripts/remix_cli.py contract
python3 scripts/remix_cli.py catalog --limit 5
python3 scripts/remix_cli.py songmap yt500-0001-fbK2ySlxAW4
```

No network, no audio, Python 3 only.

## Public variant

`abc_remixer-0.1.0-public.zip` contains code only, no corpus data. Retrieval
commands then need `--library DIR`. The full data package remains internal-use
only, consistent with the OSTRIS bundle.

## Not claimed

- No maqam labels. The library has none; the skill says “key/mode hypothesis”.
- No aesthetic judgement. `remix check` reports numbers.
- No A/B/C evaluation runs yet. The tooling is ready; the evaluation protocol is
  in `docs/remixer-implementation-plan.md` §13.
- No change to `checker.py`, `calibration.json`, or `selftest.sh`.

## Archives

| File | What |
|---|---|
| `dist/releases/abc_remixer-0.1.0.zip` | full skill + 472-song store |
| `dist/releases/abc_remixer-0.1.0-public.zip` | code only, no data |
| `dist/abc_remixer.zip` | current alias |
| `dist/abc_remixer-public.zip` | current public alias |

Checksums: `dist/releases/SHA256SUMS-remixer-0.1.0.txt`.

| File | SHA-256 |
|---|---|
| `abc_remixer-0.1.0.zip` | `4e4733c66db25af66559a542c7158e1eaf6d89caaafaff79216861134da45f0e` |
| `abc_remixer-0.1.0-public.zip` | `1934894e334ae9973242432d92dd4718feaa68eb12a97a8e9b0f8d2550f28c99` |
