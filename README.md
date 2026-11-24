# skill_abc_writer

Source of the **`maqam-score`** skill and the 177-track calibration that
justifies its numbers.

**Version:** 0.4.0 (skill contract) · tools 0.4.0 · offline corpus bundle · **remixer 0.1.0** ·
**Date:** 2026-11-23

## Layout

| Path | What it is | Status |
|---|---|---|
| `02_maqam-score/` | Skill source: `SKILL.md`, scripts, references, example, tests | **active source** |
| `03_abc_remixer/` | Sibling skill source: library-aware remixer CLI, prebuilt 472-song store, tests | **active source** |
| `02_maqam-score/scripts/ostris/` | OSTRIS corpus tools (M0–M6: sync, audit, build, features, priors, plan, idioms, similarity, check, eval) | **active** |
| `02_maqam-score/data/ostris/` | Packaged corpus artifacts: source cache, records, priors, idiom bank, similarity index, eval split | **bundled, ships in the zip** |
| `02_maqam-score/schemas/` | JSON contracts for records, priors, plans, phrases, reports, eval | **active** |
| `dist/abc-score-writer.zip` | Current built skill package (post-0.4.0 craft build) | **build artifact** |
| `dist/releases/` | Versioned archives: 0.2.0, 0.3.0, 0.4.0 (full + public) and checksums | **release history** |
| `dist/RELEASE-0.4.0.md` | Release notes, compatibility, hashes | **release notes** |
| `analysis/` | Calibration scripts (`calibrate_177.py`, `test_checker_corpus.py`, `measure_phrasing.py`, `measure_craft.py`) | **active** |
| `analysis/out/` | Regeneration workspace: `summary.json`, `tracks.jsonl`, `ostris/` | **generated, reproducible** |
| `docs/` | Reports, plans, baseline inventory | **active docs** |
| `docs/archive/` | Inputs that served their purpose | **frozen** |

The skill source is the truth; `dist/abc-score-writer.zip` is rebuilt with
`make zip`. Every released archive is kept in `dist/releases/`; the previous
0.2.0 package (the one used in the first eval session) is
`dist/releases/abc_score_writer-0.2.0.zip`.

## Quick start

```bash
make selftest        # the example passes strict shape/style + phrases
make test            # unit tests
make acceptance      # 0.4.0 regression: example, old score, template, corpus
make offline-check   # the corpus tools run on the bundled data, no flags
make check-corpus    # 177/177 parse, 175/177 hard (98.9%)
make craft           # craft distributions over the 177 (report-only, not a gate)
make zip             # build dist/abc-score-writer.zip
make release         # test + selftest + acceptance + offline + zip + dist/releases/<version>
make remix-build     # build the 472-song remixer store
make remix-test      # remixer unit tests
make remix-release   # remixer tests + verify + full/public zips + checksums
```

## Remixer

`03_abc_remixer/` is a sibling skill built on the 0.3.0 baseline; its 53 tests
also pass with the 0.4.0 runtime. It exposes
`catalog`, `songmap`, `slice`, `motif-find`, `budget`, and `remix check`, with a
hard session ledger and declared-quote verification. See
`03_abc_remixer/SKILL.md` and `docs/remixer-implementation-plan.md`. The prebuilt
store under `03_abc_remixer/data/remix/` contains 472 included songs.

```bash
make remix-build
python3 03_abc_remixer/scripts/remix_cli.py catalog --key Dm --limit 5
python3 03_abc_remixer/scripts/remix_cli.py slice yt500-0001-fbK2ySlxAW4 --bars 17-20
```

## OSTRIS corpus tools

The 482-track instrumental corpus is processed once from the project data root.
**The results ship inside the skill** under `02_maqam-score/data/ostris/`, so the
skill needs no bucket, no network and no flags at use time:

| Command | Reads from the bundle |
|---|---|
| `plan` | `priors/priors.json` |
| `exemplar` | `idioms.jsonl` |
| `similarity --score` | `similarity/index.json` |
| `check` | `priors/` and `similarity/` (optional enrichment) |
| `audit`, `build`, `features`, `priors`, `idioms`, `eval --build-split` | `source/`, `records.jsonl` |

The bundle is ~13 MB raw / ~1.9 MB compressed. It holds the lightweight inputs
(manifests, YT500 ABC shards, FADL album JSONs and reference ABCs) and the
generated statistics; the **2.95 GiB audio bundle is never included**.

Refreshing the corpus is the only step that touches the bucket:

```bash
DATA_ROOT=gs://<bucket> make ostris-sync   # refresh analysis/out/ostris/source
make ostris-audit          # M0: inventory, links, parse, records
make ostris-build          # M1: canonical ABC, contract pin check
make ostris-features       # M2: objective features + unreviewed mode hypothesis
make ostris-online         # M3-M6: priors, idioms, similarity index, eval split
make ostris-bundle         # snapshot analysis/out/ostris into the skill
make zip                   # rebuild the package with the new snapshot
```

`ostris-bundle` copies only the artifacts the tools read; `work/canonical/` is
reproducible with `make ostris-build` and is left out.

Per song:

```bash
scripts/ostris_cli.py plan  --manifest song.json --out plans/song
scripts/ostris_cli.py exemplar --function cadence --bars 2
scripts/ostris_cli.py check score.abc --plan plans/song/skill_plan.json --report report.json
```

Outputs under `analysis/out/ostris/`: `audit.json`, `audit.md`,
`manifest_links.csv`, `records.jsonl`, `held_out.jsonl`, `canonical.json`,
`canonical.md`, `features.json`, `features.md`, `priors/`, `idioms.jsonl`,
`similarity/`, `eval/`, plus the gitignored `work/canonical/abc/` set. The
source cache (`analysis/out/ostris/source/`) and `work/` are regeneration
scratch. `make ostris-bundle` snapshots the shippable subset into
`02_maqam-score/data/ostris/`. Only lightweight manifests, YT500 ABC shards,
FADL album JSONs, and reference ABCs are pulled; the 2.95 GiB audio bundle is
never downloaded.

M1 decisions D5/D6/D7/D9/D14 are recorded in `docs/ostris-decisions.md`; the
result is `docs/ostris-m1-ingest.md`. No expert maqam review is available, so
M2 is label-free: `maqam` stays `null` and the coarse `mode_hypothesis` is
unreviewed. M3–M6 are objective-only: priors record `maqam_conditioned: false`,
`check` has no maqam-fit score, and `eval` does not claim quality. See
`docs/ostris-m2-features.md`, `docs/ostris-m3-priors-plan.md`,
`docs/ostris-m4-idioms-check.md`, and
`docs/ostris-m5-m6-integration-eval.md`.

The phase-by-phase status, including what is partial or deferred, is
`docs/ostris-implementation-checklist.md`. Licensing is inventoried, not
cleared: `docs/ostris-licensing.md`.

## Where the numbers come from

- Human registry: `02_maqam-score/references/numbers.md`
- Machine-readable: `02_maqam-score/scripts/calibration.json`
- Full analysis: `docs/constraints-calibration.md`
- Raw distributions: `analysis/out/summary.json`

**Rule:** every hard gate passes ≥95% of the 177 good scores. The nine sanity
guards (six validity + three shape) pass **175/177 = 98.9%**; everything else is
a warning or a prior. The shape guards (unbroken singing, repeated-pitch share,
distinct phrase endings) were added after the 2026-11-23 eval run.

**0.4.0:** `strict_shape` makes the plan's declared breath, duration, tessitura,
register-ceiling, chorus-lift, silence, and phrase targets hard. The corpus
sanity gate is unchanged; `ostris plan` emits the targets with
`strict_shape: false`, while the composer template sets it true.

## Craft (source, post-0.4.0)

The checker answers "is this a valid score of the declared shape?". It cannot
answer "is this a tune?". Session 03 produced a score that passed `--strict-style`
with 0 warnings and was rejected on listening; its phrase-rhythm variety was
0.62 (corpus P10 0.914), its phrases peaked late 8% of the time (P10 24%), and
every phrase ended on a long note (corpus max 82%).

`02_maqam-score/references/craft.md` is the missing layer: cell → 2+2 period →
transformation vocabulary → elastic text slots → cadence ladder and sayr →
melisma as an event → riff part → intensity by subtraction → the audition by
reduction → anti-pattern gallery. The numbers behind it are in
`references/numbers.md` §7.1 and `analysis/out/craft.json`; they are
**report-only**, not gates. See
`analysis/eval/reports/2026-11-24-claude-session-03.md`.

Session 04 passed the same gate and was rejected on the drums: the vocal was a
3-bar grid and `seed.abc` had no drum voice. `references/rhythm.md` is the next
layer: phrase starts, phrase lengths, gaps, a 2-bar groove per section, three
interaction events, and the `V: Drums` voice in the seed. The baseline and the
diagnostic are in `analysis/eval/reports/2026-11-24-claude-session-04.md` and
`analysis/measure_rhythm.py`; also report-only. See `02_maqam-score/CHANGELOG.md`
0.5.1.

Session 05 never wrote a note: a 5.5 KB sheet with a 26-row line table, 19 m 42 s
of hidden design, and no ABC. 0.5.2 makes `seed_sheet.md` a **10-line rules
scratchpad**, gives the line table to `phrases.json`, and puts the score before
the notes. The cost analysis is in
`analysis/eval/reports/2026-11-24-claude-session-05.md`; the lean rerun is
session 06.

Session 07 delivered the full set but spent 241 k generated tokens for a ~2.1 k
score (115×): 19 hand-written parser/stats scripts, a full score rewrite, and a
gate-tuning loop. 0.5.3 makes the checker a **measurement instrument** (run it
after the first score; use `report.json.measured`), defaults `strict_shape` to
false, has `syllabify.py --sections` write absolute bars, defines the core as
the first 8–16 bars of the score, and adds a **10× generated-token budget**.
The evidence and the revised session-08 experiment are in
`analysis/eval/reports/2026-11-24-deepseek-session-07.md`.

## Docs map

See `docs/README.md`.
