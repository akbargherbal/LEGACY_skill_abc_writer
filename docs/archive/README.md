# archive — files kept for provenance, no longer active

Do not add new work here.

## `scripts.zip`

Claude Code's scripts used to reproduce the **v1** inventory
(`../constraints_inventory.md`):

- `budget.py` — the A-series (syllabify constants, cap ratio, pace)
- `corpus_table.py` — the five-take table and implicit tempos
- `measure.py` — location-aware stretch metrics for the single example
- `plan_example_check.py` — the example plan vs the lyrics
- `verify_refs.py` — line-reference checks
- `run_all.sh` — runs the above

They are kept because the inventory is still the baseline document. For the
177-track calibration that replaced the one-case numbers, use
`analysis/calibrate_177.py` and `analysis/out/summary.json`. The single-example
`measure.py` may still be useful for a composed score; the corpus-wide
measurement is in `analysis/`.
