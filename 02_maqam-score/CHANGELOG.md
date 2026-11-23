# Changelog

## 0.2.0 — 2026-11-23

Calibrated against the 177-track `five_stars` ABC corpus.

### Checker
- Parses inline `M:`/`K:` changes and per-bar meter (177/177 corpus files).
- Three gate classes: `contract`, `sanity`, `style`.
- Six hard sanity guards (pass 175/177 = 98.9%): simultaneity ≤4, register mean
  74±5, top duration share ≤85%, distinct durations ≥4, notes/syllable 1.0–1.55,
  Ins active ≥5%.
- Style targets warn by default; `--strict-style` makes them fail.
- Final rest warns by default; `--require-final-rest` makes it a render contract.
- `report.json` carries `class`, `calibration_version`, and `percentiles`.
- `--calibration` points at a different calibration file.

### Syllabifier
- Pace 2.8 sixteenths per syllable (corpus median 2.84), not 2.29.
- Cap ratio 0.884 (corpus median), not one-case 0.87.
- Tempo default 80 with a warning, not a silent 73.
- `seconds_per_bar` is meter-aware; the old 4/4-only formula is gone.
- Per-line P25/P75 flags instead of a fixed ±1 median rule.
- JSON carries `calibration_version`, `pace`, `case_ratio`, `seconds_per_bar`.

### Docs / examples
- `SKILL.md` and `references/reference.md` now report corpus distributions with
  `n`, not five takes as the norm.
- `example/plan.json` uses broad style values and `cadence: "any"`.
- `selftest.sh` proves the default WARN and the opt-in FAIL.
- `tests/test_checker.py` covers the example, multi-meter, strict style, and the
  final-rest flag.

### Calibration
- `scripts/calibration.json` records the 177-track corpus hashes, percentiles,
  the six sanity guards, the two optional guards, and the style defaults.

### Deliberately not in this release
- Priors for the 482-track OSTRIS instrumental set (needs the GCS manifests).
- A/B quality evaluation on a held-out set.
