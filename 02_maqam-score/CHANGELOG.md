# Changelog

## 0.5.3 — economic contract (source; contract still 0.4.0)

**Evidence:** `analysis/eval/reports/2026-11-24-deepseek-session-07.md` and the
causal audit that followed it. The run delivered all artifacts and passed the
checker, but generated 241,400 tokens for a ~2.1 k-token score (115×). 57,425
reasoning tokens went to 19 hand-written parser/stats scripts, 39,930 to
gate-tuning, and 33,890 to repairing a full score rewrite. The skill and the
task made the correct path unclear: the checker was described as a final step,
the default plan made shape targets hard, and `syllabify` left absolute bars to
hand arithmetic.

**Why:** the tools were present but the contract made them look like decoration.
A competent agent wrote a worse checker because it could not use the real one
as a measuring instrument until the end.

### Instructions
- `SKILL.md` §3.5: the checker is a **measurement instrument**, not a final
  exam. Run it with `--json report.json` after the first score and after a
  named fix; read `report.json.measured`; do not write a parser or statistics
  script; stop after a pass.
- `SKILL.md` §3.2 and `example/plan.json`: `strict_shape` defaults to **false**.
  Shape targets are warnings by default; only a strict release sets it true.
- `SKILL.md` §3.1/§3.3: `syllabify.py --sections` writes absolute
  `bar_start`/`bar_end`; do not hand-type offsets. The task uses it.
- `SKILL.md` §3.3/§7: `core_draft.abc` is the **first 8–16 bars of
  `score.abc`**; write it before planning the full form. No full-score rewrite
  after the first complete file; repair named bars with `edit`.
- `SKILL.md` §3.3/§5/§7: exactly **10 numbered lines** for `seed_sheet.md` and
  `notes.md`; no title or blank line.
- `SKILL.md` §3.3: offline, read the cell in notation; do not claim a mental
  audition. "Hum" only when audio exists.
- `SKILL.md` §7: write the score early; in an instrumented run the analyst may
  end the session at about **10×** the score's token size. It is a stop rule,
  not a quality target.

### Tools
- `scripts/syllabify.py`: add `--sections`/`--layout` (`"intro=7,verse 1=13,
  chorus=37,verse 2=46,chorus=65,outro=77"`). It groups the lyric sections in
  order and writes absolute `bar_start`/`bar_end`; repeated names are consumed
  in order. Tests: `tests/test_syllabify.py`.
- No change to `checker.py`, `calibration.json`, `abc_tools.py`, the corpus
  numbers, or the contract.

### Evaluation
- Session 08 task/checklist: `analysis/eval/inbox/deepseek_session_08/task.md`,
  `analysis/eval/checklists/2026-11-24-session-08-economic.md`.
- One experiment: checker-first measurement + no custom parser + targeted edits
  + a manual 10× analyst stop. Do not change the model in the same run.

---

## 0.5.2 — lean sheet (source; contract still 0.4.0)

**Evidence:** `analysis/eval/reports/2026-11-24-claude-session-05.md`. The 0.5.1
run never wrote a note. It spent 19 m 42 s in hidden design, produced a 5.5 KB
`seed_sheet.md` with a 26-row line table, and stopped before `core_draft.abc`.
The prompt had asked for the sheet and the core "before any ABC"; the agent
obeyed, and the session ended at the sheet.

**Why:** the sheet asked for **results** — every line's start beat, bar count,
slots and breath — before the music existed. The model had to compose the whole
piece in its head to fill the table. That is the 19 minutes. The line table is
already `phrases.json`; retyping it is duplicate arithmetic, not a plan.

### Instructions
- `SKILL.md` §3.3 step 9: write the phrase/groove **rules**, not the per-line
  table; `phrases.json` owns the table.
- `SKILL.md` §3.3 sheet paragraph: a **10-line scratchpad** (frame, cell,
  period rule, cadence rule, melisma rule, riff, subtraction, groove, three
  events, weakest bar). Rules, not results; a plan, not a deliverable.
- `craft.md` §1 step 8: the same rules-level wording.
- `SKILL.md` §5 and §7: the sheet is 10 lines of rules.

### Not changed
- The checker, `calibration.json`, the 177 corpus numbers, the rhythm layer
  (`rhythm.md`), the seed drum voice, and the §3.3 numeric craft table.
- This is a process change, not a musical one. The rhythm hypothesis is still
  untested because session 05 produced no score.

### Evaluation
- Session 06 is the lean rerun: rules-level sheet, score before report, no task
  list, one checker run. If the score exists and the ear improves, the next
  one-change run is the skill split (a later 0.5.x) to cut the 43.5 KB fixed
  context.

---

## 0.5.1 — rhythm section (source; contract still 0.4.0)

**Evidence:** `analysis/eval/reports/2026-11-24-claude-session-04.md`. A 0.5.0
score passed `--strict-style` with 0 hard checks and 0 warnings, then the user
heard "the drums are not supporting the vocal phrasing; the drummer is playing
his own idea." Measured on the final artifact: all 26 phrases started on beat 1,
25/26 used only two phrase lengths (a 3-bar frame), line-end gaps were only 1,
1.5 or 2 beats, 4/436 notes sustained through beat 3, and neither `score.abc`
nor `seed.abc` had a drum voice.

**Why:** the craft layer taught the cell, the period, the guitar and
subtraction, but the rhythm section was left to the model. The two-voice corpus
has no drum staff, so no gate could see the part the listener hears first. This
is the third run with the same rhythmic-uniformity finding; the fix is a method
and a seed part, not another gate.

### Instructions
- Add `references/rhythm.md`: the three clocks, five phrase-rhythm rules, a
  2-bar groove per section, three interaction events, the seed drum voice, the
  three tests and the 3-bar-grid anti-pattern.
- `SKILL.md` §3.3: add step 9 (rhythm section), the phrase-start/length/drum-hole
  craft rows, and `seed_sheet.md` as a required pre-ABC artifact.
- `SKILL.md` §3.7: `seed.abc` must carry a `V: Drums` voice when the style has
  drums or the target is a cover model; point to `example/groove.abc`.
- `SKILL.md` §3.4/§6/§7: state that the checked file is two voices, add the
  three-bar-grid, drums-left-to-the-model and fill-every-gap traps, and put the
  rhythm sheet in the core draft.
- `craft.md`: add §7.5 (the drummer is a partner), §11.7 (the three-bar grid),
  and audition items 11–13 (clap the backbeat, count starts/lengths, find the
  fill).
- Add `example/groove.abc`: a working 8-bar percussion voice.

### Measurement
- Add `analysis/measure_rhythm.py`: report-only phrase starts, lengths, gaps,
  onset syncopation, sustain-through-beat-3, and (with `--seed`) drum hits in
  vocal rests, fill bars and drop bars. It prints flags for the session-04
  pattern. **No checker or calibration change.**
- Session-04 baseline: `distinct_phrase_starts 1`, `25/26` phrases in two
  lengths, `weak16_share 0.071`, `sustain_beat3 4/436`, no drum voice.

### Evaluation
- Add T31 (rhythm section) to `docs/agent-eval-protocol.md`; report-only.
- The next run must use the controlled brief (D Kurd, 80 BPM), write
  `seed_sheet.md` before ABC, and deliver a drum voice in `seed.abc`.

---

## 0.5.0 — craft (source; not released, contract still 0.4.0)

**Evidence:** `analysis/eval/reports/2026-11-24-claude-session-03.md` (a 0.4.0
score that passed `--strict-style` with 0 warnings and was rejected on
listening) and the 177-track craft measurements in
`analysis/out/craft.json`.

**Why:** 0.4.0 measures validity and shape, but a score can satisfy every number
and still be a phrase grid. The session-03 v1 had phrase-rhythm variety 0.62,
peak-late 0.08 and end-long 1.00, all outside the 177; v2, after the evaluator's
prosody fix, had rhythm variety 0.23 and peak-late 0.00. The missing layer was
composition technique, not another gate.

### Instructions
- Add `references/craft.md`: cell → 2+2 period → transformation vocabulary →
  elastic text slots → cadence ladder and sayr → melisma as an event → guitar as
  a part → intensity by subtraction → the audition-by-reduction checklist →
  anti-pattern gallery (bad/fixed ABC pairs).
- Rewrite `SKILL.md` §3.3 as the nine-step method, with a compact target table
  and the draft→critique→expand process. The gate moves to "last step, not
  first".
- Add `SKILL.md` §3.7 seed delivery: `score.abc` (contract, checked) plus
  `seed.abc` (free ABC, chords/voices/instruments, not contract-checked), same
  melody.
- Add craft traps: phrase grid, bar loop, transposed verse, melisma average,
  early peaks, every-phrase-long, unscanned baḥr, silent contract exit,
  whole-bar arpeggio guitar.
- `references/style-tags.md`: rewrite the table into score decisions
  (belting = a peak, tarab = a cadence, metal = a riff, somber = gaps/colour).
- `example/score.abc`: replace the whole-bar arpeggio Ins with a pedal riff and
  a 3-bar development; the vocal fixture and plan are unchanged. Still 0 WARN
  under `--strict-style`.

### Measurement
- Add `analysis/measure_craft.py`: report-only phrase rhythm variety, contour,
  peak placement, cadence ladder, literal bar repetition and n-gram recurrence.
  It writes `analysis/out/craft.json` and registers the distributions in
  `references/numbers.md` §7.1. **No checker or calibration change.**
- The nine sanity guards, the 175/177 joint pass, and the 0.4.0 plan contract
  are unchanged. The old mediocre score still fails the same three guards.

### Evaluation
- Add T25–T30 to `docs/agent-eval-protocol.md`: hook/period, elastic text, seed
  delivery, no false prosody, cadence ladder, self-critique. They are
  report-only, not gates.
- Add the session-03 post-mortem with the measured before/after.

---

## 0.4.0 — acceptance, anti-anchoring, and the remaining expert findings

**Evidence:** `analysis/eval/inbox/claude_session_02/expert_opinion.md` (the
same pair as `analysis/eval/reports/2026-11-23-claude-session-01.md`) and the
0.3.0 source review. 0.3.0 closed the three metrics that were outside the 177
corpus; 0.4.0 closes the inside-the-corpus findings and removes the template
that taught the mediocre run's frame.

### Gate / plan
- Add optional `strict_shape` (default false). When true, the plan's declared
  shape targets are hard: `max_unbroken_seconds`, `max_top_duration_share`,
  `tessitura_share_ge_c5_max`, `register` mean/top/max_top,
  `chorus_lift_min`, `silence`, `maqam_fit`, `min_phrase_endings`, and the
  optional phrase sidecar. Old plans without the flag keep 0.3.0 behaviour.
- Add `tessitura_share_ge_c5_max` (0.80), `register.max_top` (86),
  `register.tolerance` 3 style, `chorus_lift_min` (4 default / 5 release),
  `verse_chorus_semitones` measured.
- Add `syllabify.py --phrases` and `checker.py --phrases`: a per-line
  `phrases.json` with absolute bar ranges and a 0.5 s hemistich / 1.0 s bayt
  pause minimum.
- Add `checker.py --strict-shape` override; report `strict_shape`,
  `phrases_checked`, `phrase_violations`, `verse_chorus_semitones`.

### Instructions / example
- De-anchor §3.2: replace the 78-bar/74-BPM/361-syllable run plan with a
  16-bar generic plan; remove the four session-01 deviations.
- `example/` is now Am / 80 BPM, mixed register (tessitura 50%), Ins 31%,
  silence 56%; it passes `--strict-style`, `strict_shape`, and `--phrases`
  with 0 WARN.
- Add `references/style-tags.md`: belting → planned peaks, tarab → cadence
  melisma, call-and-response → separate voices, symphonic metal → Ins.
- Revise `SKILL.md` §3.2/§3.3/§3.5/§3.6/§4/§5/§6/§7 for strict shape, phrase
  sidecar, WARN accountability, and the anti-anchoring traps.
- `ostris plan` emits the new targets with `strict_shape: false`; the composer
  template sets it true.

### Tests / docs
- Add tests for strict_shape backward compatibility, tessitura/register
  ceilings, chorus median, phrase plan, and the strict example.
- Add `schemas/phrases.schema.json`; align `schemas/plan.schema.json` with the
  checker's required fields; extend the schema test.
- Add `analysis/verify_0_4_0.py` and `make acceptance`.
- Update `references/numbers.md`, `references/reference.md`,
  `docs/agent-eval-protocol.md` (T17, T21–T24), `README.md`,
  `dist/RELEASE-0.4.0.md`, and this changelog.
- Contract pins re-pinned; `SKILL_VERSION 0.4.0`.

## 0.3.0 — shape gate after eval run `2026-11-23-claude-session-01`

**Evidence:** `analysis/eval/runs/2026-11-23-claude-session-01/postmortem.md`.
A Claude session passed the 0.2.0 gate (0 hard, 1 warning) with a score the
expert and the user called mediocre. Re-measured against the 177-track corpus,
the score was outside it on three shape metrics: 34.05 s unbroken singing
(corpus max 22.89), 6.1% repeated-pitch share (corpus min 25.2), and 2 distinct
phrase endings (corpus min 4). The skill had no target for any of them.

### Gate
- Add three calibrated **sanity** guards, all 177/177:
  `unbroken_seconds_max <= 23`, `repeated_share >= 0.20`,
  `distinct_phrase_endings >= 3` (when the score has ≥6 phrases).
  Hard gate set is now 6 validity + 3 shape = 9; joint pass stays 175/177.
- Add plan **style** targets `max_unbroken_seconds` (default 10) and
  `min_phrase_endings` (default 3), and report `unbroken_seconds_max`,
  `phrase_seconds_median`, `breaths_per_bar`, `repeated_share`,
  `stepwise_share`, `distinct_phrase_endings`, `phrase_endings`,
  `tessitura_share_ge_c5`.
- Add optional `plan.maqam` (`name`, `tonic`, `degrees`, `resting`);
  `chromatic_per_100` is measured against the maqam when declared, and the
  report says `chromatic_basis`. D Kurd as `K:Dm` now reports 0 chromatic /
  `maqam_fit_share 1.0` instead of 18.86 (100th percentile).
- Add `maqam_fit` and `maqam tonic` style checks.

### Instructions
- §1: tempo and tonic are not gate items; use the corpus/prompt defaults and
  declare them. The gate still stops for a missing lyric, style or maqam.
- §3.2: plan template now uses style targets (0.65 top duration, top 84, Ins
  0.20, endings 3, unbroken 10) instead of sanity ceilings; adds the maqam
  block and the "less ornament → melisma_min 1.00" rule.
- §3.3: **one lyric line = one phrase**; breath and phrase budget; the final
  note is the tonic but intermediate phrases end on the maqam's resting tones;
  at least three endings; repeated-note share is named.
- §3.5.1: error→fix table, including "do not split notes for duration spread"
  (the 0.2.0 repair added melisma, and the user then asked to remove it).
- §3.6: revision is one channel, one plan change, one edit, one check; a full
  rewrite is not the default.
- §6 traps: one breath per bayt, all-tonic cadences, copying 0.85/top 82.
- `references/reference.md`: §4.1 `K:`/maqam spelling (no `K:Dphr`, no
  quarter tones), §5.1 maqam table, §7.2 shape distributions, §7.3 nine guards.
- `references/numbers.md`: register the new numbers with class, n, pass rate.
- `example/plan.json` uses the style targets; `example/score.abc` no longer
  carries chord symbols (the plan says 0, the corpus has 0).
- `ostris plan` no longer asks for chords (`chords_min 0`) or a 2-note fill
  (`min_fill_notes 3`); it emits the two shape targets.

### Tests
- `test_shape_guards_reject_a_one_breath_scale` (a synthetic scale fails all
  three shape guards).
- `test_maqam_measures_against_declared_degrees` (Kurd as `K:Dm` reports 0
  chromatic when the maqam is declared).
- `test_sanity_set_passes_the_example` counts ≥6 sanity results; the example
  passes all nine guards that apply.
- Contract pins re-pinned; `SKILL_VERSION 0.3.0`.
- Release archives: `dist/releases/abc_score_writer-0.3.0.zip` (sha256
  `e792743e…78ac34`) and `-public.zip` (`e2e9a895…b06e0f`); 0.2.0 kept at
  `dist/releases/abc_score_writer-0.2.0.zip`. See `dist/RELEASE-0.3.0.md`.

## Claude-compatible package — 2026-11-23

### Portable bundle and skill name
- Rename the skill to **`abc_score_writer`** (`SKILL.md` name and title); the
  archive now extracts to `abc_score_writer/`.
- Store bundled selected-score folders under their ASCII transliterated slug and
  normalise FADL album filenames (`space` → `_`, `&` → `and`, apostrophes and
  parentheses removed). `sync.py`/`links.py` accept both the slug and the
  legacy Arabic-stem layout; `sync.py` normalises album names on refresh.
- Add `scripts/package_skill.sh`; `make zip` now builds
  `dist/abc_score_writer.zip` with `abc_score_writer/` at the root and excludes
  `CHANGELOG.md`, `data/README.md` and generated reports. `make zip-public`
  builds the code-only variant.
- Remove every `maqam-edit` reference (`SKILL.md`, `references/reference.md`,
  `docs/constraints_inventory.md`); the skill is being phased out.
- New tests assert the bundle is ASCII, space-free, and that every record path
  resolves or carries a "not in cache" note. 41 tests pass.
- Verified on a clean extraction: selftest, tests, plan/exemplar/similarity/
  check, and a full offline regeneration (audit/build/features/priors/idioms/
  similarity/eval) reproduces the shipped records, idioms, priors, similarity
  index and split exactly.

## Offline bundle — 2026-11-23

### Packaged corpus artifacts
- The OSTRIS artifacts now ship **inside the skill** at
  `02_maqam-score/data/ostris/` and are included in
  `dist/abc_score_writer.zip`, so the bucket is no longer a runtime dependency.
- Bundle contents: `source/` (manifests, YT500 ABC shards, FADL album JSONs and
  reference ABCs), `records.jsonl`, `held_out.jsonl`, `audit.*`,
  `canonical.*`, `features.*`, `manifest_links.csv`, `priors/` (30 files),
  `idioms.*`, `similarity/`, `eval/split.json`. ~13 MB raw / ~1.9 MB compressed.
- The 2.95 GiB audio bundle and the derived `work/canonical/` copy are **not**
  bundled; audio is never read, and `work/` is reproducible with
  `make ostris-build`.
- `cli.py` defaults now resolve from `__file__`:
  `plan` reads the bundled `priors/priors.json`, `exemplar` the bundled
  `idioms.jsonl`, `check` the bundled `priors/` + `similarity/`, and the
  regeneration commands the bundled `source/`. No flags and no network needed.
- New `scripts/bundle_data.sh` + `make ostris-bundle` snapshot
  `analysis/out/ostris/` into the skill after a corpus refresh.
- New `make offline-check`: exercises `exemplar`, `plan`, `similarity --score`
  and `check` against the bundle from a temporary directory.
- `sync` is unchanged but is now documented as refresh-only.
- Skill contract stays **v0.2.0**: `checker.py`, `calibration.json` and
  `abc_tools.py` are untouched, so the pinned hashes still match.
- Licensing: `docs/ostris-licensing.md` now records that the bundle is
  **internal-use only** and must be dropped from any public release until the
  upstream terms are cleared.

## 0.3.0-dev — 2026-11-23

### OSTRIS corpus tools (M0)
- New `scripts/ostris_cli.py` + `scripts/ostris/` package. Commands:
  `sync` (lightweight GCS/local cache) and `audit` (M0 inventory/link/parse).
- `sync` copies manifests, 25 YT500 ABC shards, 15 FADL album JSONs, the
  22-track FADL shortlist, and reference ABCs; never the 2.95 GiB audio bundle.
- `audit` links all 482 library tracks (460 YT500 + 22 FADL), parses them with
  the vendored `abc_tools.py`, writes `records.jsonl`, `manifest_links.csv`,
  `audit.json`, `audit.md`, and `held_out.jsonl`.
- New schemas: `schemas/track_record.schema.json`, `schemas/audit.schema.json`.
- New tests: `tests/test_ostris.py` (parse, links, duplicate exclusion, schema).
- M0 result: 482/482 matched and parsed; 35 YT500 held-out (4 without ABC);
  5 duplicate groups / 10 tracks; 10 excluded from priors; 472 prior candidates.
- The separate-repository proposal is dropped. Offline code lives in the skill;
  generated evidence lives in `analysis/out/ostris/`.

### OSTRIS M1 ingest & canonicalization
- M1 decisions resolved and pinned in `docs/ostris-decisions.md`:
  D5 (`brief.json` + `skill_plan.json`), D6 (`Vocal+Ins` only),
  D7 (skill v0.2.0 + hashes + `--require-final-rest`), D9 (preserve `M:`/`[K:]`),
  D14 (vendored `abc_tools.py` + hash).
- New `scripts/ostris/canonical.py`: structural canonicalization. It normalizes
  line endings/trailing whitespace, validates headers and both voices, and
  preserves music lines, per-bar `M:`, and inline `[K:...]`.
- New `scripts/ostris/build.py` + `ostris build`: writes
  `analysis/out/ostris/work/canonical/abc/` (gitignored), re-parses every
  canonical file, adds a `canonical` object to `records.jsonl`, and writes
  `canonical.json` / `canonical.md`.
- New `scripts/ostris/contract.py` + `ostris contract`: verifies pinned hashes
  for `checker.py`, `calibration.json`, and `abc_tools.py`.
- M1 result: 482/482 canonical and re-parsed; 1.84 MB; 482 unique hashes;
  135 tracks with declared meter changes; 3 with inline `[K:...]`; 0 failures.
- `make ostris-build` runs with `--require-contract`.
- At M1 no priors, plan, exemplar, or check command existed; the M3–M6
  sections below add them.

### OSTRIS M2 features (label-free)
- No expert maqam review is available, so D3 and D12 are **deferred** and
  `maqam` stays `null`; no maqam coverage or accuracy is claimed.
- D4 (v3 cross-check only), D11 (177 calibration only), and D16 (sanity on
  generated scores only) are recorded in `docs/ostris-decisions.md`.
- New `scripts/ostris/features.py` + `ostris features`: extracts bars, key,
  tempo band, meter timeline, section comments, per-voice density/range/
  intervals/durations/phrases, and harmony statistics.
- New `scripts/ostris/mode.py`: coarse, **unreviewed** 12-TET mode hypothesis
  (`major_like`, `minor_like`, `phrygian_like`, `hijaz_like`, `unknown`)
  anchored to the key tonic. Every row carries `reviewed: false` and is
  excluded from gates and priors.
- New `make ostris-features`; new `schemas/features.schema.json`; the track
  schema documents `features` and `mode_hypothesis`.
- M2 result: 482/482 feature rows, 482/482 mode rows, 0 named-maqam claims,
  0 failures. Key-relative families: minor_like 401, phrygian_like 55,
  major_like 25, hijaz_like 1.
- M3 may build priors by objective strata, but every prior must record
  `maqam_conditioned: false`.
- Added `docs/ostris-implementation-checklist.md`: phase-by-phase status,
  decisions, CLI/artifact coverage, deviations, and next work.

### OSTRIS M3 priors & plan
- New `scripts/ostris/stats.py`: quantiles, five-number summaries, percentile
  lookup, bands, and confidence.
- New `scripts/ostris/priors.py` + `ostris priors`: 29 objective strata
  (meter, tempo, bars, density, sections, mode, plus meter×tempo and meter×mode),
  472/482 eligible, 10 duplicates excluded, minimum stratum 10.
- New `scripts/ostris/plan.py` + `ostris plan`: writes `brief.json`,
  `skill_plan.json` (the 15 checker targets), and `plan.md`; records assumptions
  and the selected prior; sections sum to `bars`; duration within ±10%.
- New `make ostris-priors` / `ostris-plan`; new `schemas/priors.schema.json` and
  `schemas/plan.schema.json`.
- M3 result: every plan valid, no maqam claim, every prior
  `maqam_conditioned: false`.

### OSTRIS M4 idioms, similarity, check
- New `scripts/ostris/idioms.py` + `ostris idioms`: 1,304 structural 2–4 bar
  phrases (opening/phrase/cadence) across 481 tracks; `reviewed: false`.
- New `scripts/ostris/similarity.py` + `ostris similarity`: JSON interval
  k-gram index (1,304 idioms, 3,714 grams) and score queries with a longest
  shared run and quotation flag. JSON replaces `.npz` to stay stdlib-only.
- New `scripts/ostris/check.py` + `ostris check`: runs the pinned checker as a
  subprocess, nests its report under `skill_report`, adds prior percentiles and
  similarity, and reports `maqam_fit.available: false`.
- D8 applied: contract/sanity/structure hard, style WARN. D10 applied: nested
  report with a top-level `class`. D15 applied: `--require-final-rest` passthrough.
- New `make ostris-idioms` / `ostris-similarity` / `ostris-check`; new
  `schemas/report.schema.json`.
- M4 result on a real canonical track: 0 hard failures, 5 style warnings,
  similarity run 11, prior percentile reported.

### OSTRIS M5 integration
- New `scripts/ostris` wrapper that runs on CPU from any directory.
- `SKILL.md` §8 documents `plan`, `exemplar`, and `check`, and repeats that no
  maqam label or maqam-fit score exists.
- CLI roundtrip `plan → score → check` and the final-rest failure are covered
  by tests.

### OSTRIS M6 objective evaluation
- New `scripts/ostris/eval.py` + `ostris eval`: deterministic held-out split
  (31 usable, 4 without ABC, 14 generation + 17 retrieval) and run scoring with
  contract+sanity, bars delta, characters, and `tokens_proxy`.
- `quality_evaluated` and `token_reduction_measured` are always false; the
  report states what was not measured.
- New `make ostris-online` / `ostris-eval`; new `schemas/eval.schema.json`.

### OSTRIS M7 hardening
- New CI workflow (Python 3.11/3.12): tests, selftest, contract pins.
- New `docs/ostris-licensing.md` (inventory, not clearance),
  `docs/ostris-handoff.md`, `docs/ostris-release-notes.md`, and stage reports
  for M3, M4, and M5–M6.
- Tools version `0.3.0`; **30 tests pass**.

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
