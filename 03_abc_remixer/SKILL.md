---
name: abc_remixer
description: >-
  Compose a NEW two-voice ABC score by retrieving bounded material from a
  472-song Arabic transcription library, transforming it, and declaring every
  borrowing for verification. Use when asked to remix, borrow from, quote,
  interpolate, or build on existing Arabic songs. Do NOT use for reading or
  editing an existing transcription.
---

# abc_remixer — library-aware remixing

You are writing a **complete two-voice score** with an explicit relationship to
the library. The library is a set of objective transcriptions, not a style
prompt. You must go to specific songs, choose material that serves your concept,
transform it, and declare every borrowing. The tools retrieve and verify; **you
write the ABC by hand**.

The shared runtime is `abc_score_writer` 0.3.0: the same `checker.py`,
`calibration.json`, and `abc_tools.py`. The gate is unchanged.

## 1. The rule of the game

- Open creative brief: you choose the concept, form, key/maqam, tempo, and
  texture.
- The library is required. A run that never retrieves is not a remix.
- Every borrowed phrase is declared in `plan.json` under `remix.sources`.
- The declaration must match what is in the score; `remix check` verifies it.
- You may transform: transpose, invert, retrograde, augment/diminish, fragment,
  rhythm-only, contour-only.
- The final score must pass the **unchanged** checker contract and sanity gates.
  Style warnings are reported, not hidden.

## 2. Hard prohibition

**Never read the library files directly.** Do not run `cat`, `head`, `tail`,
`less`, `grep`, `awk`, `python -c`, or any other reader over:

```
data/remix/records.jsonl
data/remix/catalog.tsv
data/remix/index/
data/remix/songs/
```

and never read the OSTRIS shard JSONs or `records.jsonl`. Library access is
only through `scripts/remix_cli.py`. The ledger counts characters returned to
you and will stop a session that tries to dump the corpus.

## 3. Inputs gate

Stop only when the lyric is missing/unvocalised, the style or maqam is missing,
or the user refuses a needed choice. Tempo is not a gate.

### Mode A — user lyrics

The user supplies fully vocalised Arabic lyrics. Save them verbatim to
`lyrics.txt` and run:

```bash
python3 scripts/syllabify.py lyrics.txt --tempo <Q> --meter <M> --bars <N>
```

### Mode B — model-written lyrics

Write your own **fully vocalised** Arabic lyrics (harakat required), save to
`lyrics.txt`, and run the same command. The library carries no lyrics, so
borrowing is musical only.

### Mode C — no lyrics

**Out of scope.** `syllabify.py` requires a lyrics file; a no-lyrics mode is not
implemented. Do not pretend it exists.

### Maqam and tonic

The library has **no maqam labels**. Choose the maqam for the new piece. Use the
library for interval, rhythm, contour, register, and form; re-spell borrowed
material into your chosen maqam. Write `K:<tonic>m` or `K:<tonic>` and spell
non-key degrees with `_`/`^`. Never write `K:Dhijaz`, `K:Dkurd`, etc.

## 4. The funnel (one pass)

Use the call budgets; the ledger enforces the character budget.

1. **Concept (no tool).** Mood, form, and the *roles* that need borrowed
   material: hook, answer shape, riff, rhythm skeleton, section form, register
   curve. Write one sentence.
2. **Catalog (≤3–5 calls).** Shortlist candidates by key, meter, tempo, bars,
   density, title, or a random seed.
3. **Songmap (≤3–4 songs).** Inspect sections, hooks, riffs, and cadences.
4. **Choose 2–4 source songs.** Assign one role to each. Do not use one song
   for everything.
5. **Slice (≤8 bars per call).** Pull the exact bars. The output is a reference,
   not an auto-insert.
6. **Plan + score.** Write `plan.json` with the 15 checker targets and a
   `remix` block, then write `score.abc` by hand.
7. **Check once.** Run `remix check`; at most one scoped repair.

### Commands

```bash
# discovery
python3 scripts/remix_cli.py catalog --key Dm --mode minor --limit 12
python3 scripts/remix_cli.py catalog --tempo 70-90 --bars 60-120 --density light
python3 scripts/remix_cli.py catalog --random --seed 7 --limit 8

# one song
python3 scripts/remix_cli.py songmap yt500-0001-fbK2ySlxAW4

# extraction (≤8 bars, dialect-valid ABC)
python3 scripts/remix_cli.py slice yt500-0001-fbK2ySlxAW4 --bars 17-20 --voice Vocal
python3 scripts/remix_cli.py slice yt500-0001-fbK2ySlxAW4 --bars 17-20 --to-key Dm

# pattern → source bars
python3 scripts/remix_cli.py motif-find --intervals "0,0,2,-2" --limit 8
python3 scripts/remix_cli.py motif-find --durations "1,1,2,1" --limit 8
python3 scripts/remix_cli.py motif-find --contour wave --degree-start 7 --degree-end 0 --bars 2

# budget and verification
python3 scripts/remix_cli.py budget
python3 scripts/remix_cli.py remix check score.abc --plan plan.json --require-final-rest
```

`slice` defaults to the source `L:` (1/16 or 1/32). Forcing `--unit 1/16` can
quantise; it reports the count and refuses above a threshold unless
`--allow-lossy` is passed.

## 5. Plan block

Keep the 15 checker targets exactly as in `abc_score_writer`. Add:

```json
"remix": {
  "concept": "one sentence",
  "sources": [
    {
      "id": "yt500-0001-fbK2ySlxAW4",
      "role": "vocal hook",
      "from_bars": "17-20",
      "to_bars": "9-12",
      "transform": ["transpose:+2", "augment:2x"],
      "voice": "Vocal"
    }
  ],
  "literal_cap_bars": 4
}
```

Rules:

- `id` must exist in the catalog.
- `from_bars` is one-based, in the source song.
- `to_bars` is one-based, in your score; comma-separate multiple ranges.
- `voice` is `Vocal`, `Ins`, or `both`.
- `transform` is applied left to right; empty means a literal quote.
- `literal_cap_bars` is the maximum untransformed run allowed (default 4).

## 6. Writing the score

- Copy the header and dialect from the slice output or `references/dialect.md`.
  **Delete the `% src=...` provenance line when you paste material into your
  score**; it is metadata for you, not a section name.
- **One lyric line = one phrase.** Do not split notes to fill a bar.
- Use the slice as material, not as the whole section. A four-bar literal quote
  is the cap; transform it or answer it.
- The two voices must both be present by the end; the checker will warn on a
  missing Ins.
- End with a full-bar rest in both voices (`Z|`) before rendering.
- Do not add chord symbols unless the plan asks for them; the calibration
  corpus has none.

## 7. Report

Replace the deviation list with the quote/transform ledger:

| source | source bars | role | transform | target bars | voice |
|---|---|---|---|---|---|
| `yt500-...` | 17-20 | vocal hook | transpose:+2, augment:2x | 9-12 | Vocal |

Then copy the checker's `MEASURED` block and the `remix check` metrics verbatim.
Never retype a number. State “offline, not auditioned” unless the renderer was
actually run and heard.

## 8. Traps

- Pasting a whole section instead of a hook or riff.
- Quoting without transforming; the literal cap and `literal_share` expose it.
- Using one source for everything; `source_diversity` exposes it.
- Borrowing only on a low-bandwidth channel (e.g. only the bass line).
- Declaring a quote that the check cannot find.
- Claiming an audition that did not happen.
- Reading library files directly; the ledger and the transcript expose it.
- Treating a transcription artifact as a rule.
- Writing `K:Dhijaz`/`K:Dkurd`; only standard major/minor keys are accepted.
- Adding a maqam label to a library song; the library has none.

The checker remains the only gate. `remix check` adds quotation metrics; it does
not judge quality.
