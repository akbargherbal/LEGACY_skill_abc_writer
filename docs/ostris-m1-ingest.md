# OSTRIS M1 — ingest & canonicalize

**Date:** 2026-11-23 · **Stage:** M1 · **Gate:** PASS

M1 turns the 482 linked transcripts from M0 into a stable, hash-addressed
canonical set. The five gate decisions are recorded in
`docs/ostris-decisions.md`.

## Decisions applied

| Decision | Resolution |
|---|---|
| D5 | `ostris plan` will emit `brief.json` + `skill_plan.json`; check consumes only the 15-key skill plan |
| D6 | v1 is `Vocal+Ins` only; no instrumental-only checker |
| D7 | Skill v0.2.0 pinned by hash; render uses `--require-final-rest`, style stays WARN |
| D9 | Per-bar `M:` and inline `[K:...]` are preserved; never forced to 4/4 |
| D14 | Vendored `abc_tools.py` only, pinned by hash |

## Method

The M0 cache already contains the full ABC text in the YT500 shard JSON and the
FADL reference/selected-score files. M1 therefore does **not** download the 495
tar shards or the 2.95 GiB audio bundle; there is no second extraction step.

Canonicalization is deliberately structural:

- LF line endings; trailing whitespace removed; one final newline;
- `X/T/M/L/Q/K` headers present; `Vocal` and `Ins` voices present;
- every music line, comment, per-bar `M:`, and inline `[K:...]` preserved;
- `L` and `Q` values kept as written (no duration rescale);
- SHA-256 recorded for each canonical file;
- the canonical text is parsed again with `abc_tools.py`; a parse failure is a
  build failure, not a warning.

This resolves the plan's contradictory "unify `M` / preserve `M:`" wording in
favour of D9: there is no musical rewriting in M1.

## Result

| Check | Result |
|---|---|
| Library records | **482** |
| Canonical + re-parsed | **482/482** (100%) |
| Canonical bytes | **1.84 MB** |
| Voice shape | **482** tracks with `Vocal+Ins` |
| Unique canonical hashes | **482/482** |
| Tracks with declared meter changes | **135** |
| Tracks with inline `[K:...]` | **3** |
| Canonical failures / warnings | **0 / 0** |
| Excluded from priors | **10** (unchanged from M0) |
| Skill contract | v0.2.0, all three hashes **pinned** |

Meter changes are common, which confirms D9: 135 tracks declare more than one
meter, with shapes such as `4/4;2/4`, `2/4;1/4`, and `4/4;3/4;1/4`. Any
pipeline that forces 4/4 would corrupt these scores.

## Reproduce

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit
make ostris-build
```

Outputs:

| File | Contents |
|---|---|
| `analysis/out/ostris/records.jsonl` | M0 records plus a `canonical` object per track |
| `analysis/out/ostris/canonical.json` | Gate checks, counts, contract pins, failures, meter/voice shapes |
| `analysis/out/ostris/canonical.md` | Human summary |
| `analysis/out/ostris/work/canonical/abc/*.abc` | Canonical ABC files (gitignored, reproducible) |

`make ostris-build` passes `--require-contract`, so a changed `checker.py`,
`calibration.json`, or `abc_tools.py` fails the build instead of silently
changing the corpus contract.

## Still not done

M1 does not label maqam, build priors, emit a plan, or implement check. M2 was
subsequently implemented as a **label-free** feature layer because no expert
maqam review is available; see `docs/ostris-m2-features.md`. Named-maqam priors
remain deferred with D3/D12, while D4 (cross-check only), D11 (calibration
only), and D16 (generated scores only) are recorded. The 35 held-out tracks
remain untouched.
