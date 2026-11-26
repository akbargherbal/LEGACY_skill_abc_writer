# cli.md — the composer's commands

One entry point. The CLI owns `score.abc`; the model owns the notes.

```bash
python3 <skill>/scripts/score_cli.py <command> [args]
```

Run it from the session directory. Paths default to `score.abc`, `plan.json`,
`phrases.json`, `score_state.json`; `init` also reads `input/lyrics.txt` and
`input/style.md`.

## init

```bash
score_cli.py init --tempo 80 --sections "intro=7,verse 1=13,chorus=37,verse 2=46,chorus=65,outro=77"
score_cli.py init --bars 86 --key Dm
```

Runs `syllabify.py`, writes `prosody.json`, `phrases.json`, a complete
`plan.json`, an 86-bar `score.abc` scaffold (both voices `Z`) and
`score_state.json`. `--sections` is the absolute bar where each sung section
starts, in lyric order; repeat a name for a repeat. Without it, bars are
allocated by syllable weight. `--force` rebuilds existing files.

`init` prints a **FORM BUDGET** line when the chosen form is more than ±5% away
from the syllabify budget. The form is baked into `plan.json`/`phrases.json`;
keep the compact form and accept the warning, or rerun with `--force --bars N`
**and** `--sections` to place the extra bars. It is an advisor, not a gate.

## core

```bash
score_cli.py core --snapshot            # copy the first 16 bars to core_draft.abc
# write core_review.md: 5 numbered lines, one issue per line, tied to a bar
score_cli.py core --check               # exact prefix + 5 lines; unlocks expansion
```

`line` writes the first 16 bars without a review. Beyond 16, it refuses until
`core --check` passes. If you edit the core after the snapshot, run
`--snapshot` again before `--check`.

## line

```bash
score_cli.py line 1 \
  --vocal "z:2 D:4 F:2 G:2 | A:4 G:2 F:2 z:2 | _E:8 D:4 z:4" \
  --ins   "Z|Z|Z"
```

- The number of `|`-separated bars must equal the line's `bar_start..bar_end`
  in `phrases.json`.
- `pitch:dur` and plain ABC (`D4`) both work. Durations are
  `1,2,3,4,6,8,12,16,24,32,48`. No dots, tuplets, `[...]` chords or `^/2`.
- The CLI pads the bar tail with rests. You do not need the sum to be 16; write
  the notes you want. A tie at the bar end cannot be padded.
- The whole file is linted before writing; a bad bar changes nothing.
- `--ins` defaults to rests. The guitar answers in the vocal gaps; a whole bar
  of `Z` is a floor, not a part.
- After the write, a meter block prints the line's note deficit, the projected
  score ratio, repeated share, duration inventory, register mean, ties, gap and
  overlaps. Read it before the next line.
- `--dry-run` prints the padded bars and the meter and writes nothing.
- `--guard` refuses the write if the current line has a deficit over 1, its gap
  is below the target, or an overlap is over the cap, or, on the last line, a
  whole-score sanity band is outside. Off by default.

## patch

```bash
score_cli.py patch 26 --vocal "D4 F2 G2 A4 G2 z2" --ins "z4 A,2 c2 A,2"
```

Replaces one bar in both voices atomically and lints the file. Use this for a
named fix from `check`/`repair`, not a rewrite. `--dry-run` and `--guard` work
the same as on `line`; the meter covers that bar.

## asset_bank / verify_loans

```bash
python3 <skill>/scripts/asset_bank.py query --role chorus --bars 2 --syllables 14 --contour up --limit 3
python3 <skill>/scripts/asset_bank.py apply --id <asset> --to-key Dm --maqam kurd
python3 <skill>/scripts/verify_loans.py --loans loans.json --plan plan.json
```

`query` returns 3–5 compact references with `fit` and `why`; it never dumps the
library. `apply` returns a standalone ABC fragment, not a score write. If you
use an asset, record it in `loans.json` with `asset`, `source`, `bars`,
`borrowed`, `fit`, `transform` and `why`. A loan without a reason or a
transformation is rejected. `verify_loans.py` is separate; it does not touch
`checker.py`.

## lint

```bash
score_cli.py lint
```

Reports **every** header/group/bar error in one pass: voice, bar, token,
expected/actual. Exit 1 if any. This replaces the fail-fast parser and the
home-made `barsum.py`. It also reports the existing simultaneity guard per bar:

```text
lint: bar 30 Ins overlaps Vocal 14 units (max 4)
```

Exit 1 when any bar is over the cap; the full checker still owns the verdict.

## check

```bash
score_cli.py check --bars 9-16     # section report: sums, per-line table, register, rests, cadence
score_cli.py check                 # full checker.py, non-strict, writes report.json
score_cli.py check --release       # strict-style + final rest
score_cli.py release               # same as check --release
score_cli.py release --dry-run     # strict verdicts; score_state.json unchanged
```

On a hard failure, `check` prints the `repair.py` bar/phrase map and writes
`repair.json`. Fix only the named bars with `patch`, then check once. Stop
after a pass. `--bars` does not run the full gate; it is for early feedback.

## seed

```bash
score_cli.py seed                  # score.abc -> seed.abc (chords + V: Drums)
score_cli.py seed-check            # Vocal/Ins/Drums align bar-for-bar
```

`seed` copies the melody, adds one chord per Vocal bar, a 2-bar groove per
section, a fill at a 4/8-bar group end, and silence for the close. Edit the
seed's orchestration; do not change the melody. The seed is not contract-checked.

## plan

```bash
score_cli.py plan show
score_cli.py plan lint              # required keys, 3-4 deviations, tiling
score_cli.py plan set register.mean=72
score_cli.py plan refresh           # re-derive arrangement + ins_entries from the score
```

`plan set` takes a dotted path to an existing key (`arrangement.ins_entries=[15]`);
an unknown top-level key is rejected.

`plan lint` fails while a deviation is a placeholder. `plan refresh` never
invents a deviation, a copy or a section; it only re-derives the structural
ranges.

## status / explain

```bash
score_cli.py status                 # bars written, next line, core, last check
score_cli.py explain                # abc_doctor.py: plain-language parse diagnosis
score_cli.py explain-metric --list  # names of the measured values
score_cli.py explain-metric end     # definition, formula and known pitfall
```

## align / view (read only)

```bash
score_cli.py align --lines 3-6      # positional syllable -> note projection
score_cli.py view --roll --bars 3-5 # ASCII piano roll, 1 column per L-unit
score_cli.py view --contour         # one line per lyric phrase
```

`align` assigns one note per syllable in order and prints any surplus notes as
a cadence tail. It is a heuristic, not a text alignment. `view --roll` caps at
32 bars; `view --contour` covers every line.

## Error recovery

| Error | Meaning | Fix |
|---|---|---|
| `expected N bars separated by '|'` | the line spec has the wrong bar count | read `phrases.json`; split with `|` |
| `bar has X units; the meter holds Y` | you wrote more than the bar | shorten a note or move it to the next bar |
| `a tie at the bar end cannot be padded` | the tie needs a target | close the tie inside the line |
| `unsupported duration` | not in the duration set | split into tied supported values |
| `core not reviewed` | you tried to expand past 16 | write the core, snapshot, review, check |
| `unsupported token at ...` | a typo or an ABC feature outside the dialect | `explain`, then write the token the parser accepts |

Do not read the scripts to diagnose an error; `lint` and `explain` carry the
bar, the voice and the expected value.
