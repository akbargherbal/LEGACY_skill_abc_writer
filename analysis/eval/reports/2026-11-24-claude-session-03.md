# Eval report — 2026-11-24 / Claude session 03

Redacted, committed copy. The raw transcript, lyrics and artifacts stay in the
gitignored `analysis/eval/inbox/claude_session_03/`.

**Run id:** `2026-11-24-claude-session-03`
**Skill:** `abc_score_writer` 0.4.0 (mounted copy; zip hash unknown — the export
does not show the package)
**Agent:** Claude (Claude.ai-style harness; model id not exported)
**Task:** ad-hoc, T01-shaped with a twist: compose an ABC score from vocalised
Arabic lyrics and an arabmaqamrock style block (Maqam Kurd), **to be used as a
seed for AI-generated music (Suno)**. No key, tempo or render length given.
**Artifacts:** `score.abc`, `plan.json`, `phrases.json`, `CHANGES.txt`,
`report.json` (v1); `score_v1.abc`, `score.abc` (v2 revision);
`maqam_kurd_seed.abc` (free-ABC rewrite), `maqam_kurd_seed_v2.abc` (basīṭ
revision).

This run is unusual: the user rejected the first score on listening, and the
agent then left the skill's dialect. The post-mortem therefore measures both
the in-contract score and the free-ABC scores.

---

## 1. Outcome, measured not trusted

I re-ran the pinned 0.4.0 `checker.py` on the in-contract artifacts, and
`analysis/measure_craft.py` on every score that can be parsed. The free-ABC
scores are not in the dialect (`T:` is not blank, `[V:n]` inline, `!p!`,
`%%MIDI`), so the checker cannot read them; their numbers are from a
chord-stripped, inline-voice parse and are marked †.

| Version | Contract | Hard | WARN | notes/syll | repeated | stepwise | rhythm variety | peak-late | end-long | unique bars |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 (`score.abc`) | PASS | 0 | 0 | 1.11 | 32.7% | 92.3% | **0.62** | **0.08** | **1.00** | 0.98 |
| v2 (`maqam_kurd_seed_v2.abc`) † | **FAIL** (4 voices, `T:`, `!p!`) | — | — | 1.04 | **15.4%** | 85.6% | **0.23** | **0.00** | **1.00** | **0.31** |
| 177 corpus, P10 | — | — | — | 1.17 | 28.7% | 82.1% | 0.914 | 0.242 | 0.061 | 0.769 |
| 177 corpus, median | — | — | — | 1.28 | 32.9% | 85.6% | 0.970 | 0.361 | 0.241 | 0.862 |
| 177 corpus, max | — | — | — | 1.52 | 42.3% | 91.1% | 1.000 | 0.680 | 0.821 | 1.000 |

The 0.4.0 gate is **correct on its own terms**: v1 passes strict style and
`strict_shape` with 0 warnings. It is also the score the user called "very
mediocre". The gap is the finding.

Three craft metrics are outside the entire 177-track corpus:

- **phrase-rhythm variety 0.62** (corpus min 0.818): 16 distinct phrase rhythms
  in 26 phrases. Most verse lines reuse the same handful of 2/1 patterns.
- **peak-late 0.08** (corpus min 0.108): 2 of 26 phrases reach their highest
  note in the second half. Almost every phrase starts high and falls.
- **end-long 1.00** (corpus max 0.821): every phrase ends on a quarter note or
  longer. There is no short, suspended ending.

v2 is outside the corpus in the other direction: **rhythm variety 0.23**,
**peak-late 0.00**, **unique vocal bars 0.31**, **repeated pitch 15.4%**. It is
a fixed 4-bar period repeated five times — the 9-note verse bar appears eleven
times — with one rhythm for every line. The added breath, backing echo, strings
and lower outro are arrangement around it.

### 1.1 Cadence ladder

| Version | distinct endings | most common ending | tonic share |
|---|---:|---|---:|
| v1 | 5 | 5th 27%, 3rd 23%, ♭6 19%, ♭7 19%, tonic 12% | 12% |
| v2 † | 3 | tonic 50%, 5th 35%, ♭7 15% | 50% |
| 177 corpus | 7 (median) | 5th 31%, tonic 16%, ♭6 17%, 2nd 11%, ♭7 11%, 4th 10%, 3rd 5% | 16% |

v1 ends on the minor third more often than the corpus does (23% vs 5%); v2 ends
on the tonic in half its phrases and has only three endings, below the corpus
minimum of four. Both are the mechanical cadence the skill's own §3.3 warns
about, reached by different routes.

---

## 2. What went right

1. **Offline honesty.** The agent said it had not heard anything, made no
   audition claim, and said the arrangement choices rest on corpus priors.
2. **Bundled tooling.** `syllabify.py`, the plan, the phrase sidecar and
   `checker.py` were used as documented; no parser or threshold was built.
3. **The first score really is contract-clean.** 82 bars, both voices, complete
   plan, 0 hard / 0 WARN under `--strict-style`. The failure is not sloppiness.
4. **Responsive revisions.** Turn 3 addressed the user's "flat" complaint with
   concrete changes (leaps, held cadences, a guitar theme, gallop riffs), and
   turn 5 addressed the evaluator's breath, backing-vocal, strings, outro and
   dynamics points. It did not ignore feedback.
5. **No gate loosening.** No calibration or checker edit.

---

## 3. Findings

### G1 — the gate is blind to phrase-level rhythm (S1, `data_prior`)

`top_duration_share 0.50` and `distinct_durations 7` pass comfortably, while
62% of phrases share one rhythm. The gate measures the distribution of note
lengths across the whole score; it cannot see that the *same* 2-2-1-2 phrase is
repeated 26 times. The corpus's own P10 is 0.914 phrase-rhythm variety, so this
is not a taste threshold; it is a distribution the skill already owns and does
not measure.

**Smallest fix:** ship `analysis/measure_craft.py` as a report-only diagnostic
and name phrase-rhythm variety, peak placement and end-long share as craft
targets in the composition method. Do not make them gates.

### G2 — the evaluator's prosody fix made the tune worse (S1, `instruction_gap`)

The external evaluator's P1 was "rhythm is not text-driven; lengthen the long
syllables". The agent responded by imposing a fixed *al-basīṭ* template:
long=2 units, short=1, 14 slots per hemistich, the same in every line. Result:
**rhythm variety 0.23, peak-late 0.00**. The fix replaced a loose grid with a
tighter one. The skill offers no alternative: it has "mix durations" and a
`syllabify.py` that explicitly refuses to scan. An agent told to derive rhythm
from the text will either invent a meter or impose a template.

**Smallest fix:** an *elastic slot* method: a fixed anchor rhythm with 2–4
fill positions that absorb 13–17 syllables, plus a cadence melisma. The phrase
rhythm varies by line; the anchors keep it singable. State that a named *baḥr*
is a hypothesis, not a measurement, and never claim scansion.

### G3 — melisma is an average, not an event (S1, `instruction_gap`)

The brief says "melismatic, tarab". v1 is at 1.11 notes/syllable, the floor of
the band; v2 is at 1.00 in the body with one 5-note tag per chorus. The band
1.10–1.45 lets a fully syllabic setting pass a melismatic brief. Tarab ornament
is a *cadential event*: a held rhyme syllable with 4–8 notes, approached and
left by step. A global ratio cannot express that.

**Smallest fix:** split the target: body 1.00–1.10, cadence melisma 3–8 notes on
chosen line ends, overall 1.15–1.35. Say where the ornament is; do not raise the
average by sprinkling turns.

### G4 — the example teaches the skeleton the agent wrote (S1, `data_prior`)

`example/score.abc` is a 16-bar syntax fixture: the Ins voice is whole-bar
chord arpeggios (`A,4 C4 E4 A4`), the vocal is 3-bar cells separated by `Z3`,
and there is no rhythmic motif. The agent's v1 guitar is the same writing, and
in turn 3 it names the problem itself: "the guitar just played low arpeggios".
Models copy the only score they see. The fixture is corpus-valid and teaches
the wrong craft.

**Smallest fix:** keep the 16-bar fixture, but replace the whole-bar
arpeggio Ins with a riff motif that has rhythm and answers the vocal cell. The
vocal fixture can stay (it already has a cell, a leap and a 25% repeated-note
share); the Ins is what the agent copied. Done in this iteration: the example's
Ins voice is now a pedal riff with a 19-note interlude, and it still passes
`--strict-style` with 0 WARN.

### G5 — there is no seed mode, so the best output left the contract (S1, `packaging`)

The user's target is a Suno seed, not the LoRA renderer. v2 is closer to that
target (chords, backing vocals, strings, dynamics) and is unreadable to the
checker; the agent fell back to "every bar adds up". The skill's contract and
the user's deliverable diverge, and the skill has no rule for the divergence.

**Smallest fix:** two named deliverables from one composition:
`score.abc` (the strict two-voice contract, checker-validated) and `seed.abc`
(free ABC: chords, optional backing/strings voices, instruments). The seed is a
rendering of the same material, not a second composition; say it is not
contract-checked.

### G6 — no motif development method (S1, `instruction_gap`)

v1 has 98% unique vocal bars: nothing repeats literally, so there is no hook.
v2 has 31% unique bars: one 9-note cell repeated 11 times, so there is a loop.
The corpus sits between (median 86% unique bars, 40% 4-note pitch recurrence,
85% rhythmic recurrence). The skill says "two or three motifs" and "mutate the
cell", but never says *how*, so the agent either through-composes or loops.

**Smallest fix:** a transformation vocabulary and a period model: antecedent
open / consequent closed, then sequence, inversion, truncation, augmentation,
ornament, registral shift. One cell per section, not one per line.

### G7 — a prosody claim and a reduced validation (S2, `agent_capability` + `instruction_gap`)

The agent wrote "al-basīṭ ... 14 slots per half-line" without scanning the poem,
and "the singer adapts the text to the tune" as a substitute for alignment. That
is an agent overclaim: the skill says not to scan and does not license a meter
label. The count itself (14 notes per hemistich) is right; the defect is that
the rhythm is fixed and the claim is unearned.

The agent was honest that `abc2midi` was unavailable, but the skill gave it no
named reduced check for a free-ABC deliverable, so "every bar adds up" became the
only validation of the version the user was judging.

**Smallest fix:** add the unscanned-baḥr and "singer adapts" traps; name the
seed's reduced check in §3.7 (bar sums and voice alignment, not the contract).

### G8 — cadence ladder off-distribution (S2, `data_prior`)

v1 ends 23% of phrases on the minor third (corpus 5%) and only 12% on the tonic;
v2 ends 50% on the tonic with three endings (corpus min 4). The skill says "at
least three endings" but gives no distribution or hierarchy.

**Smallest fix:** publish the corpus ending ladder and a per-section cadence
plan: open on the 5th, colour on the ♭6/♭7, the b3 rarely, the tonic only at
the section close and the final qafla.

---

## 4. Root cause

The skill is a **validity and shape gate with a materials list**. It can say
what a score must not be (no >23 s breath, no <20% repeated pitch, no <3
endings) and it can list the ingredients (maqam table, motif count, register,
breath). It cannot say how to make a phrase, how to develop a cell, where the
peak goes, or how to set a line of Arabic. So a competent agent satisfies every number and
writes a grid, then — when the user says it is flat — either adds ornaments
around the grid (v1 → turn 3) or imposes a tighter grid (v2).

The second cause is that the only worked artifact the agent sees is a skeleton.
Prose loses to example.

The third is the missing seed mode: the best-liked output was outside the
contract, so the agent's own validation stopped.

---

## 5. Disposition

| Action | Target | Proof |
|---|---|---|
| `patch` | new `references/craft.md`: cell → period → elastic slots → cadence ladder → melisma event → riff part → subtraction → self-critique → anti-pattern gallery | T25–T30 |
| `patch` | `SKILL.md` §3: craft-first method, draft → critique → expand, `seed.abc` mode, craft traps | docs review + T25 |
| `patch` | `example/score.abc`: replace the arpeggio Ins with a riff motif; keep the 16-bar fixture | `make selftest`, `make acceptance` |
| `patch` | `references/style-tags.md`: tarab/melisma as an event; belting as peaks; metal as a riff part | T24 |
| `test` | `analysis/measure_craft.py` (report-only) + `references/numbers.md` craft-reference block | reproducible `analysis/out/craft.json` |
| `test` | `docs/agent-eval-protocol.md` T25–T30: hook, period, elastic text, seed mode, self-critique, no false prosody | eval battery |
| `no action` | the nine sanity guards and the 0.4.0 checker | v1 still passes; the gate was not the defect |
| `no action` | leaps as a craft target | corpus is 85.6% stepwise; leaps are 3.8% of intervals. Do not teach leaps as the fix. |

**Severity note.** The protocol's S1 means "output fails a hard gate". These
findings pass the gate and fail the user. I am using S1 for "the deliverable is
not usable as a seed" and recording the deviation, because a post-mortem that
calls a rejected score an S2 is measuring the wrong thing.

---

## 6. Confounders

- One run, one model, one lyric. The corpus distributions are the guard against
  overfitting a single taste.
- v2 is a free-ABC file; † numbers come from a chord-stripped inline parse, not
  from `checker.py`. The comparison is indicative, not a contract measurement.
- The evaluator's brief supplied the basīṭ pattern in its P1 example. The agent
  followed it. That is a task-prompt contribution, but the skill had no better
  option to offer.
- No audio was heard by the analyst. The user's listening verdict is the
  aesthetic evidence; the metrics explain the mechanism.
