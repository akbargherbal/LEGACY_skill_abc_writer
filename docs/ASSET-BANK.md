# Asset bank — phrase-level stock for declared borrowing

**Purpose:** make the 670-score library usable as **stock**, not as a template.
The unit is a phrase, cadence or cell. The composer queries a few candidates,
writes the line, and declares what it borrowed and why.

This is the implementation of `docs/DECISIONS.md` D5–D7. It reuses the existing
`remixer`/`idioms` data; it does not add a RAG or touch `checker.py`.

## What is indexed

| Field | Meaning |
|---|---|
| `id` | stable asset id: source, bars, kind, hash |
| `source` / `start_bar` / `end_bar` | provenance |
| `section` / `role` / `function` / `kind` | where it sits: verse/chorus, opening/phrase/cadence, phrase/cadence/cell |
| `meter` / `tempo` / `key` / `tonic_pc` | compatibility |
| `notes` | `[bar, beat, midi, duration_quarters]` |
| `intervals` / `durations` / `contour` | what can be borrowed |
| `degree_start` / `degree_end` / `cadence_degree` | tonic-relative colour |
| `low` / `high` / `range` / `mean_pitch` / `density` | register and weight |
| `syllables_min` / `syllables_max` | lyric capacity, from the 1.0–1.55 notes/syllable band |
| `quality` | top duration, distinct durations, longest run, leap, register, vocal/Ins activity, monotone/repetitive, `clean` |
| `dedupe_group` | exact duplicate group |

`clean` means "no hard degeneracy", not "radio-ready". A phrase with two
durations can be a real cell; the full-score `distinct_durations ≥ 4` rule does
not apply to a 2-bar asset.

## Build

```bash
python3 02_maqam-score/scripts/asset_bank.py build \
  --songs 03_abc_remixer/data/remix/songs \
  --out 02_maqam-score/data/assets/assets.jsonl.gz \
  --meta 02_maqam-score/data/assets/assets.meta.json \
  --cells
```

- 644 vocal songs, 26 instrumentals skipped (670 total).
- **38,601 assets** (32,487 phrases, 970 cadences, 5,144 cells); **30,725
  clean**, 7,876 raw; index **2.5 MiB** gzipped.
- 1–4 bar phrases, cadences, up to 8 one-bar cells per song.
- Exact duplicate ids removed; `dedupe_group` keeps cross-song duplicates
  visible.
- Build is offline: **zero agent tokens**.

## Query

```bash
python3 02_maqam-score/scripts/asset_bank.py query \
  --role chorus --bars 2 --syllables 14 --contour up \
  --register 67-74 --maqam kurd --limit 5
```

Returns 3–5 compact rows, e.g.:

```text
a-suno-0025-0033-0034-phrase-571851 | suno-0025 33-34 | chorus/phrase | 2b | up | cad 3 | reg 69-76 | syll 13-19 | clean | 7.5
  why: chorus/phrase; 2 bars; contour up; cadence 3; reg 69-76; syll 13-19; clean; kurd fit 100%
```

The output never dumps the library. `--quality clean` is the default; use
`--allow-monotone`/`--allow-repetitive` to widen it. Diversity is capped at two
assets per source by default.

## Apply

```bash
python3 02_maqam-score/scripts/asset_bank.py apply \
  --id a-suno-0025-0033-0034-phrase-571851 \
  --to-key Dm --maqam kurd --cadence-degree 0
```

Returns a standalone ABC fragment with a `% transforms:` header. Operations:
transpose/to-key, maqam remap, rhythm-only, contour-only, retrograde, augment,
fragment, syllable fit, cadence degree. The tool previews; the composer writes
the line with `score_cli.py line`.

## Loan declaration

`loans.json`:

```json
{"loans": [{
  "asset": "a-suno-0025-0033-0034-phrase-571851",
  "source": "suno-0025",
  "bars": "33-34",
  "borrowed": ["rhythm", "contour"],
  "role": "chorus",
  "fit": {"bars": 2, "cadence": 3, "register": "69-76", "syllables": 13},
  "transform": ["remap to Kurd", "end on tonic"],
  "why": "two-bar rising phrase to the fifth; cadence on 3; 14-syllable capacity; fits the chorus lift"
}]}
```

```bash
python3 02_maqam-score/scripts/verify_loans.py --loans loans.json --plan plan.json
```

`PASS` requires: real asset, matching source/bars, known borrowed fields, a
real transform, at least two fit fields, and a reason of at least 20
characters. Similarity/coherence are WARN; the ear decides.

## Budget

- Build: 0 agent tokens.
- Query: ~50 tokens per asset; 3–5 assets per section; typically <1,500 tokens
  per score.
- Apply: one fragment per chosen asset.
- The 10k thinking goes to **choice, transformation and the reason**, not to
  writing a parser or a full baseline.

## Limits

- The 670 are general-style SUNO transcriptions, not the LoRA's style. Use their
  **rhythm, arrangement, chords and groove** as stock; take the melodic contour
  from the 482 OSTRIS / 24 Fadl references when the target is arabmaqamrock.
- The library has no lyrics. `syllables_min/max` is estimated from the
  1.0–1.55 notes/syllable band; the composer fits the actual line.
- `clean` is broad. `--allow-monotone`/`--allow-repetitive` widen the query;
  these flags are warnings, not a quality verdict.
- Section labels are replayed from `%` comments; this build has zero
  mismatches. 26 instrumental songs are skipped.
- The query is a shortlist, not a decision. The ear decides.

## Integration

- `score_cli.py` still owns `score.abc`; `asset_bank` is read-only.
- The composer queries before a section, chooses 0–2 assets, writes `loans.json`,
  then writes each line through `score_cli.py`.
- If no asset fits, compose. Never force a loan.
- `verify_loans.py` is separate; `checker.py`/`calibration.json` are untouched.

## Pilot

Use the same lyrics and model as the control. One variable: asset assistance.
The pilot package is `dist/session-13-ready.zip`; session 12 is not used.
Measure `output+reasoning` against 10× the final score, then listen. 7–8 is the
stock stage; 9+ needs the taste pass. If the ear does not improve, fix the bank
or abandon it; do not scale.
