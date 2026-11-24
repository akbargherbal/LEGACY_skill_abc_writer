# Proposal: turning `abc_score_writer` into a library-aware Remixer

Audience: an implementing/testing AI agent. Personal, educational use only.
Status: design proposal. Nothing here has been implemented.
Baseline inspected: `abc_score_writer` v0.3.0 (zip, 13 MB).

---

## 1. Goal

Today the skill composes a score from **lyrics + style prompt**, with the model
working from priors only. The new goal is a **remix mode**: the model is given
open creative freedom and a library of ~480 transcribed songs, and must

1. think of a concept for a new piece,
2. *go to specific songs* in the library, pick material that suits the concept,
3. quote / transform / embed that material into a new two-voice score,
4. declare every borrowing, and be checked on it,

**without ever loading the library (or a large part of it) into context.**

The point is to measure the model's ability to remix intelligently, so the
tooling must make retrieval cheap and make "how much it borrowed and how it
transformed it" measurable.

### Non-goals

- Do not change `scripts/calibration.json`, the sanity thresholds, or
  `checker.py` behaviour. Existing `tests/` and `scripts/selftest.sh` must
  keep passing unchanged.
- Do not generate the score with a script. Tools **retrieve, transform and
  verify**; the model **writes the ABC by hand** (the existing skill rule).
- No audio, no rendering, no network (offline mode, as in the current skill).

---

## 2. Verified facts about the current bundle

(Measured by inspecting the zip; re-verify before relying on them.)

| Fact | Value |
|---|---|
| `data/ostris/records.jsonl` | 482 records: 460 `yt500`, 22 `fadhl_shaker_shortlist`; 2.1 MB |
| Records with `exclude_from_priors: true` | 10 |
| Records' `maqam` | `null` / `maqam_source: "unlabelled"` for **all 482** |
| Record fields useful for search | `title, artist, key, keys, meter, meters, tempo, bars, section_count, density, silence, range{vocal,ins}, notes{vocal,ins}, chords, quality_score, flags, duplicate_of, duplicate_group, mode_hypothesis, features` |
| Full ABC text | inside shard JSONs: `data/ostris/source/TRANSCRIPTS/YT500/YT500/abc/shard-NN.json` (25 shards, `tracks[]`), `.../FADL_SHAKER/abc/*.json` (15 albums, `tracks[]`), plus loose `.abc` in `source/DATASET/fadhl_shaker_instrumental_18/abc/` and `source/TRANSCRIPTS/fadhl_shaker_selected_scores/*/score.abc` |
| Tracks found in transcript JSONs | 635 entries, 623 carry ABC text (check exact key names: `abc`, `abc_melody` seen on Fadl entries) |
| Total ABC size | ~2.49 M chars (~0.8-1.0 M tokens). Mean song ~4.0 k chars (~1.3-1.6 k tokens), max ~9 k chars |
| `idioms.jsonl` | 1304 rows (481 opening / 476 cadence / 347 phrase), 2-4 bars, **Vocal only**, interval + duration sequences, `degree_start/end`, contour; no absolute pitches, no ABC, `reviewed: false` |
| `similarity/index.json` | 3- and 4-gram interval inverted index over those 1304 idioms (1.6 MB); `QUOTATION_RUN = 8` |
| `ostris_cli.py` subcommands | `sync audit build features priors plan idioms exemplar similarity check eval contract` |
| `canonical.json` | 2.9 KB only; the canonical ABC files that `build` would write are **not** bundled |
| Source ABC dialect | not uniform: e.g. `L:1/32`, `M:2/4`, mid-score `M:1/4`, chord symbols in the Vocal voice, `Z` whole-bar rests, `d'` octave marks. The composing dialect in `SKILL.md` §3.4 uses `L:1/16` in the examples and only durations `1,2,3,4,6,8,12,16,24,32,48` |
| Identity join | YT500 records use `yt500-NNNN-<video_id>`; transcript entries have `video_id`, `source_rank`, `track_id`. Fadl records need joining via shortlist / `stem` / title. **This join is not trivial and must be tested.** |

Implication: nothing in the bundle may be read wholesale. Even the metadata
file is ~0.7 M tokens.

---

## 3. Gap analysis

What exists and is reusable as-is:

- `checker.py` contract + sanity + style gates (apply to the remix output unchanged).
- `syllabify.py` (lyrics -> syllables/bars budget; supports `--bars`).
- `ostris plan`, `ostris check`, priors, `abc_tools.parse` (the parser to reuse for all new tools).
- `similarity` as a **post-hoc** accidental-quotation detector.

What is missing for remixing:

| Needed capability | Present? |
|---|---|
| Find songs by key / meter / tempo / density / title / artist / quality | No (only `plan` priors by stratum) |
| Cheap structural overview of ONE song | No |
| Pull a specific bar range from a specific song, as dialect-valid ABC, in the target key | No |
| Search by melodic/rhythmic pattern and get back *(song, bars)* | Index exists but is Vocal-idiom-only and returns anonymous idiom ids; no Ins voice |
| Declare borrowings in the plan and verify them | No |
| Measure transformation/novelty vs sources | Only a binary "run >= 8" flag |
| Hard cap on how much context a session can pull from the library | No |
| Remix workflow instructions for the model | No |

The existing `exemplar` returns structural phrases without provenance, so it
cannot support "think of a song, then borrow from it".

---

## 4. Design principles

1. **Funnel, not dump.** catalog (cheap, wide) -> songmap (cheap, narrow) ->
   slice (bounded, deep). Each step costs more per item and touches fewer items.
2. **Every tool has a hard output cap** enforced in code, not in prose.
3. **A session ledger** counts characters returned by library tools and refuses
   past a configurable budget.
4. **Tools never compose.** They return ABC fragments and numbers.
5. **Borrowing is declared and verified**, so a result can be judged as
   "what was quoted, how it was transformed, what is new".
6. Pure Python 3 standard library (`sqlite3` allowed), as the rest of the skill.
7. Reuse `abc_tools.parse` for parsing; do not write a second parser.

---

## 5. Components to add

Place under `scripts/remix/` and expose through `scripts/remix_cli.py`
(same pattern as `ostris_cli.py`; run with `python3 -I`). Data goes in
`data/remix/`.

### 5.1 `library build` — one normalised store

Input: the transcript JSONs, loose `.abc` files, `records.jsonl`.

Output (suggested):

```
data/remix/songs/<song_id>.abc         one normalised ABC per song (parseable by abc_tools)
data/remix/catalog.tsv  (or catalog.sqlite)   one row per song
data/remix/build_report.json           counts, join failures, dropped songs + reasons
```

Requirements:

- Stable `song_id` (reuse record `id` where present).
- Join transcripts <-> records; **report every unmatched record/track**.
  Target: >= 95% of the 482 records have ABC text; list the rest.
- Parse every song with `abc_tools.parse`; unparseable songs are excluded and
  listed in `build_report.json`.
- Exclude by default: `duplicate_of != null`, `exclude_from_priors`, low
  `quality_score` (threshold configurable), flagged records. Keep an
  `--include-all` switch.
- Idempotent and deterministic (byte-identical output on re-run).
- Catalog columns: `song_id, title, artist, key, meter, tempo, bars,
  section_count, density, silence, vocal_range, ins_range, quality, source`.
  Add derived columns computed from the parsed score: vocal top / mean pitch,
  share of bars with Ins active, repeated-pitch share.

### 5.2 `catalog` — filtered, capped search

```
remix_cli.py catalog [--key Dm] [--mode minor|major] [--meter 4/4]
                     [--tempo 70-90] [--bars 60-120] [--density light|medium|busy]
                     [--title STR] [--artist STR] [--sort quality|density|...]
                     [--limit 15]
```

- One line per song, <= ~30 tokens, e.g.
  `yt500-0001 | Maktooba Leek | Elissa | Fm 2/4 70bpm | 186 bars | 7 sec | dens 4.6 | q1.0`
- Default `--limit 15`, hard maximum 40. Output states how many matched in total.
- Deterministic ordering. Offer `--random --seed N` for serendipity (the model
  should be able to ask for "a few unexpected songs").

### 5.3 `songmap <song_id>` — structure at ~300 tokens

Compact report derived from the parsed ABC:

- header (key, meter(s), tempo, bars);
- sections table: name, bar range, vocal active share, Ins active share, density;
- ranges (vocal/Ins);
- **hook candidates**: the top 3-5 most repeated 4-6 note interval cells in the
  Vocal voice (and separately Ins), each with count and bar locations;
- **Ins riff candidates** likewise;
- cadence points (phrase-ending pitches as scale degrees relative to the tonic).

Hard cap on output length. Nothing here claims a maqam (labels do not exist;
see §2). Use "key/mode hypothesis" wording only.

### 5.4 `slice <song_id>` — bounded, dialect-safe extraction

```
remix_cli.py slice <song_id> --bars 17-24 --voice Vocal|Ins|both
                    [--to-key Dm] [--transpose N] [--strip-chords]
                    [--unit 1/16] [--emit abc|json]
```

- **Hard cap: 8 bars per call** (configurable up to a ceiling; refuse above it).
- Output is dialect-valid ABC bars in the composing dialect of `SKILL.md`
  §3.4, ready to paste as a reference (not auto-inserted into any score).
- Must handle source/target dialect differences found in §2:
  - unit rescale `L:1/32 -> L:1/16`: durations that become non-integral or
    outside the allowed set `{1,2,3,4,6,8,12,16,24,32,48}` need a documented
    quantisation policy (report how many notes were altered, and fail loudly
    above a threshold rather than silently mangling);
  - meter changes inside the range;
  - strip chord symbols by default (the 177-track calibration corpus has none);
  - convert `Z` whole-bar rests, octave marks, ties correctly;
  - transposition re-spells accidentals via `_`/`^` for the target key. Work
    from parsed MIDI events and re-emit; do not regex the text.
- Always prints a provenance header line: `# src=<song_id> bars=17-24 voice=Vocal transpose=+2`.
- Transposition is chromatic (12-TET). Sources contain no quarter tones, so
  there is nothing to preserve; but say so in the docs.

### 5.5 `motif-find` — pattern search returning (song, bars)

```
remix_cli.py motif-find --intervals "0,0,2,-2" [--durations "1,1,2,1"]
                        [--voice Vocal|Ins] [--min-run 4] [--limit 10]
remix_cli.py motif-find --contour wave --degree-start 7 --degree-end 0 --bars 2
```

- Extend the existing interval k-gram index in two ways: (a) cover **both
  voices**, (b) index **whole songs**, not only the 1304 idioms.
- Results: `song_id, voice, bars, match_length`, ranked; capped.
- Supports rhythm-only matching (duration-ratio sequence) because rhythmic
  skeletons are a primary remix material.
- Query output feeds straight into `slice`.

### 5.6 Remix plan block + `remix check`

Extend the plan (do **not** change the existing 15 required targets) with an
optional `remix` block, validated by a new `remix_check` that wraps the
existing `ostris check`:

```json
"remix": {
  "concept": "one sentence",
  "sources": [
    {"id": "yt500-0001-...", "role": "vocal hook",
     "from_bars": "17-20", "to_bars": "9-12",
     "transform": ["transpose:+2", "augment:2x", "fragment:first-5-notes"],
     "voice": "Vocal"},
    {"id": "...", "role": "guitar riff", "from_bars": "33-34",
     "to_bars": "5-6, 21-22", "transform": ["invert"], "voice": "Ins"}
  ],
  "literal_cap_bars": 4
}
```

Transforms to support and detect: `transpose`, `invert`, `retrograde`,
`augment/diminish` (duration scale), `fragment`, `rhythm-only` (keep durations,
replace pitches), `contour-only`.

`remix check` must:

1. **Verify each declared quote** exists in the score at `to_bars` with the
   declared transform (match on interval/duration sequences; tolerate declared
   transpositions; report `verified / not found` per item).
2. **Detect undeclared matches** against the whole library (run >= 8 intervals,
   as `similarity` already defines) and report them as `undeclared_quote`
   (fail or warn: configurable, default warn).
3. **Report metrics** (numbers only, no prose judgement):
   - `quote_coverage`: share of Vocal bars / Ins bars containing a declared quote;
   - `literal_share`: share of notes inside exact (untransformed) matches;
   - `max_literal_run_bars` vs the declared `literal_cap_bars` (fail above it);
   - `novelty`: 1 - the largest overlap fraction with any single source song;
   - `source_diversity`: number of distinct source songs actually used;
   - `transform_mix`: counts per transform type.
4. Run the **unchanged** `checker.py` gates on the same score (contract and
   sanity stay hard; style stays warn).

### 5.7 Session ledger (token budget)

`data/remix/.ledger` (or a path given by `--ledger`): every library call
appends `{tool, song_id, chars_returned}`. A configurable cap (default
**~30 k chars, about 8-10 k tokens**) makes further calls exit non-zero with a
clear message. `remix_cli.py budget` prints the running total. This is what
prevents the model from "burning" context.

Suggested default call limits per remix session (enforced via the ledger):

| Step | Limit | Approx. cost |
|---|---|---|
| `catalog` | 5 calls x <= 15 rows | ~2 k tokens |
| `songmap` | 4 songs | ~1.2 k tokens |
| `slice` | 8 slices x <= 8 bars | ~3-5 k tokens |
| `motif-find` | 5 calls | ~1 k tokens |

---

## 6. Skill-side changes

Create a sibling skill `abc_remixer` (reuses `abc_score_writer/scripts` by
path) rather than overloading the existing `SKILL.md`. The new `SKILL.md`
should contain, in this order:

1. **Role and rule of the game**: open-ended creative brief; the model must
   use the library; quotes are declared.
2. **Hard prohibition**: never `cat`, `head`, `grep`, or otherwise read
   `records.jsonl`, `idioms.jsonl`, `index.json`, the shard JSONs, or
   `songs/`. Library access only through `remix_cli.py`.
3. **Inputs gate**:
   - *Lyrics mode A*: user supplies vocalised lyrics (existing gate).
   - *Lyrics mode B (free)*: the model writes its own **fully vocalised**
     Arabic lyrics (harakat required), saves them to `lyrics.txt`, runs
     `syllabify.py`. The transcripts carry no lyrics, so borrowing is
     musical only.
   - *Mode C (no lyrics)*: only if `syllabify.py --bars N` works without a
     lyric file; the agent must verify this and document the result. If it
     does not, mode C is out of scope.
   - Maqam/tonic: same rule as now, but note that the library has **no maqam
     labels**; the model chooses the maqam for the new piece and may borrow
     material by interval/degree pattern and re-spell it.
4. **The funnel workflow** (one pass):
   1. Concept (no tool): mood, form, which *roles* need borrowed material
      (hook, answer shape, riff, rhythm skeleton, section form, register curve).
   2. `catalog` (<= 3-5 queries) to shortlist candidates.
   3. `songmap` on <= 3-4 candidates.
   4. Choose 2-4 **source songs** and assign a role to each.
   5. `slice` the exact bars needed (<= 8 per call).
   6. Write `plan.json` including the `remix` block, then `score.abc` by hand.
   7. `remix check` once; one scoped repair at most (existing cost rule).
5. **Report**: deviation list is replaced by the **quote/transform ledger**
   (source, bars, role, transform, target bars) + the checker's MEASURED block
   + the remix metrics, copied verbatim, never retyped.
6. **Traps** specific to remixing: pasting a whole section, quoting without
   transforming, using one source for everything, borrowing on a low-bandwidth
   channel, claiming an audition that did not happen, reading library files directly.

---

## 7. Acceptance tests (the implementing agent must run these)

Unit-level

- `library build`: idempotent; row count and exclusions match `build_report.json`;
  every stored song re-parses with `abc_tools.parse`; join-failure list is
  explicit.
- `catalog`: deterministic; honours `--limit` and the hard maximum; each line
  <= 40 tokens (use a chars/3 proxy and say so).
- `songmap`: output <= cap for the longest song (~9 k chars); hook candidates
  actually occur at the listed bars (verify by slicing them).
- `slice`: refuses > 8 bars; output parses; transposition preserves interval
  sequence exactly; `--to-key` yields only notes spellable in the target key
  plus declared accidentals; 1/32 -> 1/16 rescale reports altered-note count;
  meter changes and `Z` bars round-trip; chord symbols stripped.
- `motif-find`: finds a pattern cut from a known song with that song at rank 1;
  rhythm-only mode works; both voices covered.
- `remix check`: build synthetic scores that contain a quote that is
  exact / transposed / inverted / augmented / fragmented and confirm each is
  detected with the right transform label; a score with no quote reports 0;
  an undeclared 8+ interval run is flagged; `literal_cap_bars` is enforced.
- Ledger: the call that crosses the cap exits non-zero; `budget` shows the total.
- Regression: all existing `tests/` and `scripts/selftest.sh` pass unchanged.

False-positive check

- Take 50 random song pairs; confirm `remix check` reports no declared-quote
  match and no undeclared 8-run for unrelated pairs (or report the base rate
  honestly; common short cells such as repeated notes may match by chance, so
  consider a minimum-information threshold for the match).

Integration (dry run, scripted)

- Execute the full funnel on a fixed brief with a fixed seed; log total
  characters returned by library tools; confirm the session stays under the
  ledger cap and the final `score.abc` passes `checker.py --require-final-rest`.

---

## 8. Evaluation protocol: does the library actually help?

To measure "remix ability" rather than just tool function:

- Use a fixed set of ~5 open briefs (e.g. "a melancholic Hijaz piece that
  grows from a single guitar riff", "an upbeat 2/4 piece with a call-and-response
  hook", ...), identical across conditions.
- Conditions:
  - **A. No library**: the existing skill, priors only.
  - **B. Library-guided remix**: the funnel above, with the ledger enforced.
  - **C. Library-guided + held-out exclusion**: `held_out.jsonl` songs (35)
    excluded from retrieval, then used only as an evaluation reference for
    novelty / similarity.
- Metrics: checker pass/fail and warning count; `quote_coverage`,
  `literal_share`, `novelty`, `source_diversity`, `transform_mix`;
  total retrieved characters; number of tool calls; number of repair passes.
- **Human listening/reading review is the only aesthetic judgement** and is
  outside the tooling; offline runs must say "offline, not auditioned".

---

## 9. Risks and open questions for the implementer

1. **Transcript <-> record join** for the Fadl entries is the most likely
   point of failure; budget time for it and report the unmatched.
2. **Dialect rescale** (1/32 -> 1/16) may force lossy quantisation for many
   songs. Decide whether the target dialect can also use `L:1/32`
   (check `checker.py` / plan `unit` handling) or whether quantisation is
   acceptable; document the decision and the measured loss.
3. **No maqam labels.** Do not add a maqam classifier as part of this work;
   keep "key/mode hypothesis" language, and let the model re-spell borrowed
   material into its chosen maqam.
4. **Calibration mismatch.** Sanity guards were calibrated on 177 tracks; the
   library has ~480. Do not recalibrate in this task; just note it.
5. **Transcription noise.** The ABCs are model transcriptions, not authoritative
   scores; quotes can carry transcription artifacts. The metrics treat them as
   data, not ground truth.
6. **Match thresholds** for "quote" detection need tuning to avoid trivial
   matches (runs of repeated notes). Report the chosen threshold and why.
7. **Size.** Per-song store adds ~2.5 MB; acceptable. Keep the catalog under
   ~200 KB.

## 10. Suggested implementation order

1. `library build` + `build_report.json` (unblocks everything).
2. `catalog`, `slice` (+ dialect normalisation tests).
3. `songmap`, ledger.
4. `motif-find` (both voices, whole songs).
5. `remix` plan block + `remix check`.
6. `abc_remixer/SKILL.md`.
7. Integration dry run, then the A/B/C evaluation.
