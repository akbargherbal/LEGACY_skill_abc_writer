# assets.md — the stock pass (optional, declared)

The library is a quarry, not a template. You still write every line through
`score_cli.py`; an asset is a reference.

## When

Before the first line of a section, if you want a rhythm/contour starting point.
Skip it when you already have a clear cell. Do not query for every bar.

## Query

```bash
python3 <skill>/scripts/asset_bank.py query \
  --role chorus --bars 2 --syllables 14 --contour up \
  --register 67-74 --maqam kurd --limit 3
```

Read the compact rows. Choose at most two. A row is a candidate, not a command.
If the default is too narrow, add `--allow-monotone` or `--allow-repetitive`.

## Apply

Preview one transformation:

```bash
python3 <skill>/scripts/asset_bank.py apply --id <asset> --to-key Dm --maqam kurd
```

The fragment is a draft. Write your line with `score_cli.py line`; do not paste
the preview as the final score.

## Declare

If you use an asset, append to `loans.json`:

```json
{"loans": [{
  "asset": "<id>", "source": "<source>", "bars": "33-34",
  "borrowed": ["rhythm", "contour"], "role": "chorus",
  "fit": {"bars": 2, "cadence": 3, "register": "69-76", "syllables": 13},
  "transform": ["remap to Kurd", "end on tonic"],
  "why": "two-bar rising phrase; cadence on 3; 14-syllable capacity; chorus lift"
}]}
```

Then:

```bash
python3 <skill>/scripts/verify_loans.py --loans loans.json --plan plan.json
```

No reason, no loan. No transform, no loan. If nothing fits, compose.

## Rules

- Never read the library files directly; use `asset_bank.py`.
- Never write `score.abc` directly; use `score_cli.py`.
- No `w:` lines; lyrics stay outside the score.
- A loan is WARN-checked, not a taste gate; the ear decides.
- Keep the query small: 3–5 assets per section, not the whole index.
