# skill_abc_writer

Source of the **`maqam-score`** skill and the 177-track calibration that
justifies its numbers.

**Version:** 0.2.0 · **Date:** 2026-11-23

## Layout

| Path | What it is | Status |
|---|---|---|
| `02_maqam-score/` | Skill source: `SKILL.md`, scripts, references, example, tests | **active source** |
| `dist/02_maqam-score.zip` | Built skill package | **build artifact** |
| `analysis/` | Calibration scripts (`calibrate_177.py`, `test_checker_corpus.py`) | **active** |
| `analysis/out/` | Generated evidence: `summary.json`, `tracks.jsonl` | **generated, reproducible** |
| `docs/` | Reports, plans, baseline inventory | **active docs** |
| `docs/archive/` | Inputs that served their purpose | **frozen** |

The skill source is the truth; `dist/02_maqam-score.zip` is rebuilt with
`make zip`. The old v1 zip lives in git history.

## Quick start

```bash
make selftest        # the example passes; the dialect is enforced
make test            # 6 unit tests
make check-corpus    # 177/177 parse, 175/177 hard (98.9%)
make zip             # build dist/02_maqam-score.zip
```

## Where the numbers come from

- Human registry: `02_maqam-score/references/numbers.md`
- Machine-readable: `02_maqam-score/scripts/calibration.json`
- Full analysis: `docs/constraints-calibration.md`
- Raw distributions: `analysis/out/summary.json`

**Rule:** every hard gate passes ≥95% of the 177 good scores. The six sanity
guards pass **175/177 = 98.9%**; everything else is a warning or a prior.

## Docs map

See `docs/README.md`.
