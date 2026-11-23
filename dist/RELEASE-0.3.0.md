# Release 0.3.0 — shape gate after the first agent eval

**Date:** 2026-11-23
**Skill:** `abc_score_writer` 0.3.0
**Contract:** checker / calibration / abc_tools re-pinned (`skills v0.3.0: pinned`)
**Base:** 0.2.0 (`dist/releases/abc_score_writer-0.2.0.zip`)
**Evidence:** `analysis/eval/runs/2026-11-23-claude-session-01/postmortem.md`
(redacted copy: `analysis/eval/reports/2026-11-23-claude-session-01.md`)

---

## Why 0.3.0

The first Claude run passed the 0.2.0 gate with **0 hard failures and 1 style
warning**. The user and the expert both called the score mediocre. Re-measured
against the 177-track corpus, the score was outside it on three shape metrics:

| Metric | Claude 0.2.0 | 177 corpus (min · median · max) | 0.3.0 gate |
|---|---:|---|---:|
| longest unbroken singing | **34.05 s** | 5.49 · 10.42 · 22.89 | ≤ 23 s |
| repeated-pitch share | **6.1%** | 25.2 · 32.4 · 42.6 | ≥ 20% |
| distinct phrase endings | **2** | 4 · 7 · 8 | ≥ 3 (≥6 phrases) |

The score also had 11 phrases over 78 bars, a 14.59 s median phrase, and 10 of
13 endings on D. The root cause was an instruction, not the model: `SKILL.md`
§3.3 said "The tonic at each phrase end." It also had no breath target and a
plan template that copied sanity ceilings as style targets.

## Artifacts

| File | What | SHA-256 |
|---|---|---|
| `dist/releases/abc_score_writer-0.3.0.zip` | full skill, bundled corpus | `e792743eecda594a38b1eeb73d24c86cfc4c69185a224d0011e443c49978ac34` |
| `dist/releases/abc_score_writer-0.3.0-public.zip` | code only, no corpus data | `e2e9a89523d922684e41a0fd915fc7230d6d91af893d8c5b0f3695fd36b06e0f` |
| `dist/abc_score_writer.zip` | current alias of the full 0.3.0 zip | same as above |
| `dist/abc_score_writer-public.zip` | current alias of the public 0.3.0 zip | same as above |
| `dist/releases/abc_score_writer-0.2.0.zip` | previous release (as provided) | `1db1938e59ef7e8cb3b4ca24e66df6f45e5a8c23c3c90cb6912e36f59d5c6499` |
| `dist/releases/abc_score_writer-0.2.0-public.zip` | previous public release | `f691609c8e5465b36a7a90ea76ff48bd32a51ff14f01d26347bac6d9bd22f819` |

`SHA256SUMS-0.2.0.txt` and `SHA256SUMS-0.3.0.txt` are in `dist/releases/`.

**Install:** unzip the archive; the top-level folder is `abc_score_writer/`
(matching `SKILL.md`'s `name`). No network, no install, Python 3 only.
**Selftest:** `cd abc_score_writer && bash scripts/selftest.sh`.

## What changed

### Gate (three new hard sanity guards, all 177/177)

- `unbroken_seconds_max <= 23` (corpus max 22.89).
- `repeated_share >= 0.20` (corpus min 0.252).
- `distinct_phrase_endings >= 3` when the score has ≥6 phrases (corpus min 4).

The gate is now **contract + 9 sanity guards** (6 validity + 3 shape), joint
pass **175/177 = 98.9%**. Style stays WARN by default; `--strict-style` opts in.

### Plan / style targets

- `max_unbroken_seconds: 10` (corpus median 10.42; the hard ceiling is 23).
- `min_phrase_endings: 3` (corpus min 4, median 7).
- `max_top_duration_share: 0.65` in the template (0.85 is the hard ceiling).
- `register.top: 84` (corpus median; 82 is P25).
- `ins_active_share_min: 0.20` (P25; 0.15 was below it).
- `maqam: {name, tonic, degrees, resting}`; when present,
  `chromatic_per_100` is measured against the maqam, not `K:`. D Kurd written
  as `K:Dm` now reports 0 chromatic / `maqam_fit 100%` instead of 18.86
  (100th percentile).
- New `MEASURED`: `unbroken_seconds_max`, `phrase_seconds_median`,
  `breaths_per_bar`, `repeated_share`, `stepwise_share`,
  `distinct_phrase_endings`, `phrase_endings`, `tessitura_share_ge_c5`,
  `chromatic_basis`, `maqam_fit_share`.

### Instructions

- **Cadence:** only the final note is tonic; intermediate phrases end on the
  maqam's resting tones; at least three different endings.
- **Breath:** one lyric line = one phrase; use the `syllabify.py` bars-per-line
  table; rest at every line end; do not chain a bayt into a 5-bar phrase.
- **Melisma:** when the brief asks for less ornament, set `melisma_min` to 1.00
  and keep `melisma_max` around 1.15; never add notes the user asked to remove.
- **Revision (§3.6):** one channel, one plan change, one edit, one check; a full
  rewrite is not the default.
- **Error → fix table (§3.5.1):** especially "do not split notes to fix
  `duration spread`" — that repair added the melisma the user then complained
  about.
- **Gate defaults (§1):** tempo is not a gate (80 BPM prior); a named maqam with
  no tonic uses the table's default (D) and declares it; the gate stops only for
  a missing/unvocalised lyric, style, or maqam.
- **`K:` rule:** major/minor only; `K:Dphr` is a contract failure. D Kurd is
  `K:Dm` + `_E`; D Hijaz is `K:Dm` + `_E` + `^F`; D Ajam is `K:D`. No quarter
  tones (`^/2`) in this dialect.

### Corpus tools / example

- `ostris plan` no longer asks for chords (`chords_min 0`) or a 2-note fill
  (`min_fill_notes 3`); it emits the shape targets.
- `example/plan.json` uses the style targets; `example/score.abc` no longer
  carries chord symbols (the corpus has 0; the plan says 0).
- `plan.schema.json` allows the maqam object and object-form deviations.

## Compatibility

- **Existing 0.2.0 plans still parse.** The 15 required targets are unchanged;
  the new fields (`max_unbroken_seconds`, `min_phrase_endings`, `maqam`,
  `maqam_fit_min`) are optional.
- **The new sanity guards apply to every score**, even an old plan. A score like
  the Claude one (34 s / 6.1% / 2 endings) now fails with 3 hard errors.
- **`K:Dphr` was never valid**; 0.2.0 rejected it too. The release makes the
  workaround explicit.
- **Chromatic numbers change only when `plan.maqam` is present.** Without it,
  `chromatic_basis` is `key:<K>` and the old number is unchanged.
- **The example score changed** (no chords); if you diff against 0.2.0, expect
  that.

## Validation

- `make test`: **43 tests pass** (was 41; new shape and maqam tests).
- `make selftest`: PASS.
- `make offline-check`: PASS.
- `analysis/test_checker_corpus.py`: **177/177 parse, 175/177 hard**.
- Clean-room extraction of both release zips:
  - 0.3.0: selftest PASS, 43 tests OK, `contract: pinned`.
  - 0.2.0: selftest PASS, `contract: pinned`.
- The exact Claude score: 0.2.0 PASS (0 hard, 1 warning) → 0.3.0 **FAIL 3 hard**
  (`unbroken`, `repeated`, `phrase endings`), while the bundled example still
  passes.

## Known limits

- **No `w:` lines / syllable-to-note alignment.** The renderer dialect has no
  `w:`; the checker counts total syllables only. A per-line phrase plan is P2.
- **No quarter tones.** Rast/Bayati/Saba/Huzam are not encodable; write the
  nearest diatonic skeleton and put intonation in the prompt.
- **No listening.** The gate measures structure, not beauty; the listener owns
  "impressive".
- **Stepwise share, tessitura share, chorus-median +5** are measured/reported
  but not gated: they do not separate these takes or would fail much of the
  corpus. See the post-mortem.

## Rollback

Use `dist/releases/abc_score_writer-0.2.0.zip` (full) or
`abc_score_writer-0.2.0-public.zip` (code only). The 0.2.0 package is validated
and usable; it will pass the old six-guard gate and the old example.

## Next

Run the 0.3.0 regression battery on two agents: T01 (twice), T17 (one line, one
breath), T18 (less melisma), T19 (Hijaz spelling), T20 (chorus-only revision),
plus the cheap refusals T02/T03/T06/T08. If it passes, this is the release to
ship; if an instruction fails, patch the instruction, not the gate.
