# OSTRIS handoff

**Date:** 2026-11-23 · **Tools version:** 0.3.0 · **Skill:** v0.2.0

This note is for whoever picks up the corpus tools next, especially a reviewer
who can supply the maqam labels this build deliberately does not invent.

## What is frozen

| Contract | Value | Meaning |
|---|---|---|
| `scripts/checker.py` | `bd3645…` | The only verifier; do not edit it to make a plan pass |
| `scripts/calibration.json` | `c5cd51…` | 177-track thresholds |
| `scripts/abc_tools.py` | `e99e5c…` | Vendored runtime parser |
| `skill_plan.json` | 15 keys | `checker.py` fails a plan that omits any |
| `maqam` | `null` | No label is claimed anywhere |

`python3 02_maqam-score/scripts/ostris_cli.py contract --strict` checks the first
three. If one drifts, M1–M6 should be rebuilt, not patched.

## Where the stages stop

| Stage | State | What it needs to go further |
|---|---|---|
| M0 audit | complete | nothing |
| M1 canonical | complete | nothing |
| M2 features | complete, label-free | a reviewer for D3 (maqam) and D12 (coverage) |
| M3 priors/plan | complete, objective-only | maqam-conditioned priors once D3 exists |
| M4 idioms/similarity/check | complete; maqam-fit omitted | reviewed idioms and a maqam-fit metric |
| M5 integration | complete to the CLI and `SKILL.md` | a real composition session outside CI |
| M6 evaluation | split + objective metrics | human or blind quality evaluation, token instrumentation |

## Adding maqam labels later

1. Get a reviewed label set for a sample. A label needs `maqam`,
   `maqam_confidence`, `maqam_source`, and a reviewer id.
2. Add the fields to `records.jsonl`; do not overwrite `features` or
   `mode_hypothesis`.
3. Add a `maqam` stratum to `priors.py` **only** after coverage and accuracy are
   measured on a reviewed sample (D12). Until then every prior stays
   `maqam_conditioned: false`.
4. Keep `mode_hypothesis` separate. It is key-relative, unreviewed, and must not
   be relabelled as maqam.
5. Re-run: `features → priors → idioms → similarity → eval --build-split`.

The schemas under `02_maqam-score/schemas/` are additive; new fields are allowed,
removing or renaming the current ones is a breaking change.

## Reproduce

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit
make ostris-build
make ostris-features
make ostris-online      # priors, idioms, similarity index, eval split
make test               # 30 tests
make selftest
```

Generated evidence lives in `analysis/out/ostris/`. The cache and canonical work
directory are gitignored; `records.jsonl` is reproducible from the data root.

## Known limits

- Ajam/Rast and Nahawand/Bayati are not separable in this 12-TET ABC dialect.
- Prior strata below ten tracks are omitted and served by backoff.
- `tokens_proxy` is characters/4 for the score only, not a model token count.
- Quality and blind non-inferiority are **not measured**; the reports say so.
- The 35 held-out tracks were never used for priors or idioms.
