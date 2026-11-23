# analysis/out — generated evidence

Do not edit these files by hand. Regenerate with:

```bash
python3 analysis/calibrate_177.py \
  --corpus ~/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars \
  --out analysis/out
```

| File | Contents |
|---|---|
| `summary.json` | Distributions, pass rates, A6 comparison, sanity gate set |
| `tracks.jsonl` | One row per track: raw metrics, gate verdicts, section match |

The human registry is `02_maqam-score/references/numbers.md`; the
machine-readable thresholds are `02_maqam-score/scripts/calibration.json`.
