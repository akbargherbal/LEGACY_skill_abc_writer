# Release 0.4.0 — acceptance, anti-anchoring, and the remaining expert findings

**Date:** 2026-11-23
**Skill:** `abc_score_writer` 0.4.0
**Contract:** checker / calibration re-pinned; `abc_tools.py` unchanged
**Base:** 0.3.0 (`dist/releases/abc_score_writer-0.3.0.zip`)
**Evidence:** `analysis/eval/inbox/claude_session_02/expert_opinion.md` (same
pair as `analysis/eval/reports/2026-11-23-claude-session-01.md`) and the 0.3.0
source review. Plan: `docs/0.4.0-remaining-fixes-plan.md`.

---

## Why 0.4.0

0.3.0 made the three metrics that were outside the 177-track corpus hard:
34.05 s unbroken, 6.1% repeated pitch, 2 phrase endings. The old score now
fails 3 hard. The expert's **inside-the-corpus** findings were still only
warnings, and the skill still taught the mediocre run's plan as the template:

- the §3.2 plan was 78 bars / 74 BPM / 361 syllables with the four session-01
  deviations;
- the example was 100% ≥ C5, register mean 78.2, Ins active 69%, and still
  passed;
- `max_unbroken_seconds 10` and `max_top_duration_share 0.65` were WARN only;
- there was no per-hemistich phrase artifact;
- there was no style-tag translation for belting/tarab.

0.4.0 closes those gaps **as declared brief targets**, not as new corpus sanity
guards. The 177 hard-gate set is unchanged: 175/177 = 98.9%.

## Artifacts

| File | What | SHA-256 |
|---|---|---|
| `dist/releases/abc_score_writer-0.4.0.zip` | full skill, bundled corpus | `7190dfd0c17ab35f61c1fef8aa2f14f7a5da95a1b63b589470e634a771ed4e99` |
| `dist/releases/abc_score_writer-0.4.0-public.zip` | code only, no corpus data | `1321de03c8a57069d548473b19b83d53b72c9e18b867ff41a75376c6f6274d52` |
| `dist/abc_score_writer.zip` | current alias of the full 0.4.0 zip | same as above |
| `dist/abc_score_writer-public.zip` | current alias of the public 0.4.0 zip | same as above |
| `dist/releases/abc_score_writer-0.3.0.zip` | previous full release | `e792743eecda594a38b1eeb73d24c86cfc4c69185a224d0011e443c49978ac34` |
| `dist/releases/abc_score_writer-0.2.0.zip` | previous full release | `1db1938e59ef7e8cb3b4ca24e66df6f45e5a8c23c3c90cb6912e36f59d5c6499` |

`SHA256SUMS-0.4.0.txt` is in `dist/releases/`.

**Install:** unzip the archive; the top-level folder is `abc_score_writer/`.
No network, no install, Python 3 only.
**Selftest:** `cd abc_score_writer && bash scripts/selftest.sh`.

## What changed

### Gate / plan

- **`strict_shape`** (optional, default false). When true, the shape targets the
  plan declares are hard: `max_unbroken_seconds`, `max_top_duration_share`,
  `tessitura_share_ge_c5_max`, `register` mean/top/max_top, `chorus_lift_min`,
  `silence`, `maqam_fit`, `min_phrase_endings`, and the optional phrase sidecar.
  Old plans without the flag keep 0.3.0 behaviour.
- **Tessitura/register:** `tessitura_share_ge_c5_max` (0.80), `register.max_top`
  (86), `register.tolerance` 3 style (sanity stays ±5),
  `verse_chorus_semitones` measured, `chorus_lift_min` 4 default / 5 release.
- **Phrase sidecar:** `syllabify.py --phrases phrases.json` writes per-line
  bar suggestions and a 0.5 s hemistich / 1.0 s bayt pause minimum.
  `checker.py --phrases` verifies absolute bar ranges, line-end pauses, and the
  plan's unbroken span.
- **CLI:** `checker.py --strict-shape`; report fields `strict_shape`,
  `phrases_checked`, `phrase_violations`, `verse_chorus_semitones`.
- **Maqam fit / silence** are hard only when `strict_shape` is true; the corpus
  sanity gate is unchanged.

### Instructions / example

- §3.2 no longer carries the 78-bar/74-BPM/361-syllable run plan. The template
  is the 16-bar generic fixture; the four session-01 deviations are gone.
- `example/` is now Am / 80 BPM, mixed register (tessitura 50%), Ins 31%,
  silence 56%; it passes `--strict-style`, `strict_shape`, and `--phrases`
  with 0 WARN.
- Add `references/style-tags.md`: belting → planned peaks, tarab → cadence
  melisma, call-and-response → separate voices, symphonic metal → Ins.
- `SKILL.md` §3.2/§3.3/§3.5/§3.6/§4/§5/§6/§7 update the gate classes, the
  strict final check, the phrase sidecar, WARN accountability, and the
  anti-anchoring traps.
- `ostris plan` emits the new targets with `strict_shape: false` (objective
  generated plan); the composer template sets it true.

### Tests / docs

- 51 tests pass, including strict_shape backward compatibility, tessitura and
  register ceilings, chorus median, phrase plan, and the strict example.
- Add `schemas/phrases.schema.json`; align `schemas/plan.schema.json` with the
  checker's required fields; schema tests for the example.
- Add `analysis/verify_0_4_0.py` and `make acceptance`.
- Update `references/numbers.md`, `references/reference.md`,
  `docs/agent-eval-protocol.md` (T17, T21–T24), `README.md`, and
  `docs/0.4.0-remaining-fixes-plan.md`.

## Compatibility

- **Old plans parse unchanged.** `strict_shape` absent = 0.3.0 behaviour.
- **The nine sanity guards are unchanged**; the joint hard pass stays
  175/177 = 98.9%.
- **The example changed** from Dm/73 to Am/80 and from a high register to a
  mixed one. Diff against 0.3.0 is expected.
- **The old mediocre score still fails** the three shape sanity guards with or
  without `strict_shape`.
- **A minimally repaired score** (20 s / 72% / 82% tessitura) now fails the
  declared shape targets when the plan has `strict_shape`.

## Validation

- `make test`: **51 tests pass**.
- `make selftest`: PASS (strict shape/style + phrases, short bar, final rest,
  blank line, two-note answer).
- `make acceptance`: PASS (example strict, phrase failure, old score, template,
  177 corpus).
- `make offline-check`: PASS.
- `analysis/test_checker_corpus.py`: **177/177 parse, 175/177 hard**.
- `python3 scripts/ostris_cli.py contract --strict`: pinned.
- Full archive extracts to `abc_score_writer/`; selftest and tests run offline.

## Known limits

- **W5.2 not in this release.** The long/short rhythm heuristic is deferred to
  0.5.0; F2 remains a duration-mix target plus the model's own rhythm choice.
- **No `w:` lines / syllable-to-note alignment.** The phrase sidecar verifies
  line bar ranges and pauses, not one syllable per note. The renderer dialect
  has no `w:`.
- **No quarter tones.** Rast/Bayati/Saba/Huzam are not encodable; the nearest
  diatonic skeleton and the prompt carry the intonation.
- **No listening.** These are score-shape targets, not a beauty verdict.
- **No new agent run on 0.4.0 yet.** The T21–T24 battery is the next step; the
  current evidence is the old score and the bundled fixtures.

## Rollback

Use `dist/releases/abc_score_writer-0.3.0.zip` (full) or
`abc_score_writer-0.3.0-public.zip` (code only). 0.3.0 remains validated and
passes the old gate.

## Next

Run T01 (twice), T17, T18, T19, T20, T21–T24 on two agents with the 0.4.0 zip.
Record before/after for unbroken, top duration, tessitura, chorus median,
per-line pauses, WARN count, turns, and repairs. Ship 0.5.0 only if the
long/short heuristic beats the current duration-mix instruction on 10–20 lines.
