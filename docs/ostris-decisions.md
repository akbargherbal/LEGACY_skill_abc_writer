# OSTRIS pre-execution decisions — M1 gate

**Resolved:** 2026-11-23 · **Scope:** the five M1 decisions, plus the M2
amendment forced by the absence of an expert maqam reviewer. M3–M6 decisions
remain open.

The skill stays at **v0.2.0**. The pins below are recorded so a later change to
the checker, calibration, or parser is visible instead of silent. The runtime
`ostris` code verifies them and reports drift; it does not edit the skill.

## D5 — plan schema

**Chosen:** two files, not one ambiguous `plan.json`.

| File | Role |
|---|---|
| `brief.json` | Creative brief: maqam intent, mood, bars **or** `target_duration_s`, tempo/meter constraints, must-quote references |
| `skill_plan.json` | The 15 keys `checker.py` requires: `key, tempo, meter, unit, bars, syllables, sections, melisma_min, melisma_max, register{mean,top,tolerance}, max_top_duration_share, min_distinct_durations, ties_min, min_fill_notes, chords_min` |

`ostris check` consumes `skill_plan.json`. `brief.json` is never passed to
`checker.py` directly; the plan generator turns the brief into the 15-key
contract. This keeps artistic intent and renderer contract separate.

## D6 — instrumental voices

**Chosen:** `Vocal+Ins` only in v1.

`checker.py` already requires both voices, so `--voices ins` is deferred. No
separate instrumental checker. Instrumental-only generation, if added later,
needs a skill-contract change first. The 482-track corpus still supplies `Ins`
priors and ranges under the two-voice contract.

## D7 — skill contract pin

**Chosen:** pin v0.2.0 by hash; the M5 render path will use
`--require-final-rest`; `style` stays WARN by default.

| Artifact | SHA-256 |
|---|---|
| `scripts/checker.py` | `bd364578417a8b407fa0b5953bbfb2b358a44eaf1bc9dccf332a5501e4bf30b4` |
| `scripts/calibration.json` | `c5cd513c83936d1f847eb93f9f8aed1f0a5c23f0249a0217498ce0ddd21333a1` |

`--strict-style` remains opt-in. A hash mismatch is reported as contract drift;
`ostris build --require-contract` turns it into a failure.

## D9 — variable meter

**Chosen:** preserve per-bar `M:` changes and inline `[K:...]`; never force 4/4.

Canonicalization must not transpose, re-beam, or rewrite meter. Meter/key
changes stay where the transcript put them. M0 confirms this is necessary: the
corpus uses 11 meter labels and 57 tracks contain 1/4 bars.

## D14 — parser

**Chosen:** vendor, do not fork.

| Artifact | SHA-256 |
|---|---|
| `scripts/abc_tools.py` | `e99e5cf9dff4647f48322e3319065ba793e7dbc808222e1848bab7aa8c4bd11c` |

`ostris` imports the vendored module. No second parser, no lenient fallback.
A parse failure is a failure. The configured hash is checked by
`ostris contract` and recorded in every build summary.

## Consequence for M1 canonicalization

The plan says "unify `L/M/Q`, preserve `M:` and `[K:...]`", which is
self-contradictory if "unify `M`" means rewriting meter. Following D9 and D14,
the canonical form here is **structural**, not a re-notation:

- LF line endings and no trailing whitespace;
- `X/T/M/L/Q/K` headers present, both named voices present;
- all music lines, comments, per-bar `M:`, and inline `[K:...]` preserved
  byte-for-byte apart from trailing whitespace;
- `L` and `Q` values preserved as written (rescaling durations would be a
  musical rewrite and is not justified by the parser contract);
- SHA-256 recorded for every canonical file.

If a later stage needs a single `L`, that is a separate, reviewable transform,
not part of M1.

## M2 amendment — no expert reviewer available (2026-11-23)

The 482-track corpus has no maqam labels, and no expert review is available.
The original M2 gate (maqam coverage ≥90% plus accuracy on a reviewed sample)
cannot be met honestly. The plan is amended as follows:

| Decision | Resolution under the constraint |
|---|---|
| **D3** maqam review | **Deferred.** No maqam labels are produced. `maqam` stays `null`, `maqam_source="unlabelled"`. |
| **D4** 438 v3 labels | **Cross-check only**, and only on the separate v3 corpus. Never training, priors, or eval for the 482. |
| **D11** 177 role | **Calibration only.** The 177 labels are prompts/calibration, not ground truth. |
| **D12** coverage metric | **Not applicable until D3 exists.** M2 reports feature coverage, not maqam coverage or accuracy. |
| **D16** sanity on 482 | **Generated scores only.** The sanity guards are not applied to corpus priors. |

**Replacement M2 gate:** 482/482 deterministic feature rows, 482/482
`mode_hypothesis` rows, zero named-maqam claims, and a recorded explanation of
the limitation.

`mode_hypothesis` is a coarse 12-TET template fit anchored to the ABC key
tonic. It is marked `reviewed: false`, is excluded from every gate, and must
not be described as a maqam label or used to condition priors. Ajam/Rast and
Nahawand/Bayati are not separable in this dialect; the output families are
`major_like`, `minor_like`, `phrygian_like`, `hijaz_like`, `unknown`.

If a reviewer or a licensed labelled dataset becomes available later, it can
upgrade D3 and add named-maqam priors without changing the M2 feature layer.

## M3–M6 resolutions (2026-11-23)

No new expertise was required for these; the plan's recommended defaults were
applied and are recorded in code and outputs.

| Decision | Resolution | Where |
|---|---|---|
| **D5** plan schema | `brief.json` + `skill_plan.json`; `check` refuses a brief | `plan.py`, `check.py` |
| **D8** gate policy | `contract`/`sanity`/`structure` hard; `style` WARN unless `--strict-style` | `check.py` |
| **D10** report merge | checker report nested under `skill_report`; top-level `class` | `check.py`, `schemas/report.schema.json` |
| **D13** held-out source | the 35 unused YT500 tracks; 14 generation + 17 retrieval | `eval.py` |
| **D15** final rest | WARN by default; `--require-final-rest` promotes it to contract | `check.py` |
| **D1** quality target | **ABC only.** Contract+sanity and objective metrics; no audio judge | `eval.py` |
| **D2** held-out function | both: generation reserve and retrieval reserve are disjoint | `eval.py` |
| **D3/D12** maqam | still deferred; `maqam_fit.available: false` in every report | `mode.py`, `check.py` |

Priors stay objective-only (`maqam_conditioned: false` on all 29 strata). The
online surface is `plan`, `exemplar`, `similarity`, and `check`; the offline
surface adds `priors`, `idioms`, `eval`, and the existing M0–M2 commands.
