# Proposal: a retrieve-and-adapt baseline for abc-score-writer

**Target:** abc-score-writer 0.8.0
**Status:** draft for maintainer review
**One-line summary:** Stop asking the agent to write a ~3,000-token score from a blank page. Have a tool build a checker-passing baseline score from our own Suno ABC library, and have the agent edit that baseline.

---

## 1. Problem

A single score of about 3,000 tokens currently costs **100,000–200,000 tokens** end to end. That is not sustainable. This is far beyond the skill's own stated budget of about 10x the score size.

**We have not measured where the tokens go.** The causes below are hypotheses, ranked by my best guess, and have to be confirmed with a per-turn log (section 7).

1. **Thinking tokens spent counting.** The agent re-derives syllables, sixteenths and bar sums by hand. LLMs are weakest at exactly this, and the skill already tells the agent not to do it.
2. **Context re-sent every turn.** `SKILL.md` is about 8,600 words, and the references add about 12,000 more. Each checker run adds about 45 lines of output plus a JSON report. Over 30 or more tool calls this multiplies.
3. **Process ceremony.** A run produces about 13 artifacts, with several checks, repairs and state updates.
4. **Blank-page exploration.** With no baseline, the agent deliberates about options before the first bar exists.

## 2. What the review of 0.8.0 found

The skill's strength is verification: a parser plus a four-class checker, exact repeat checking, a maqam-fit measure, and plan-then-measure. Its weaknesses, ranked by how silently they damage the output:

| Rank | Issue |
|---|---|
| 1 | Pace ignores the style: a fixed 2.8 sixteenths per syllable regardless of "melismatic" or "somber" |
| 2 | Section tags are read silently (an intro tagged "single clean guitar" that contains lyrics is counted as sung) |
| 3 | No syllable-to-note binding: the score has no `w:` lines, so the rhyme melisma and ties cannot be verified |
| 4 | Process load and contradictory instructions |
| 5 | Syllable counter is wrong on 4 of 26 lines of the test lyrics (line-initial hamzat waṣl undercounted; fatha plus dagger alif double-counted) |
| 6 | Taste review is the same model reviewing itself |
| 7 | Poem long/short rhythm is out of scope |
| 8 | Gates pull toward the corpus average |

This proposal addresses the cost problem directly and reduces exposure to items 3, 5 and 6. Items 1, 2 and 5 should be fixed first or alongside it, because a baseline built on wrong counts bakes in the errors.

## 3. The asset

We hold about 600 Suno-generated songs transcribed to ABC. They are our own material and can be used in any form. Case study of 5 random files:

- All five parse with the vendored runtime parser. The checker accepts `L:1/32` and 6/8, 2/4 and 3/8 meters once the plan declares them.
- 3 of 5 fail at least one hard sanity guard: one is an instrumental with zero vocal notes, one has 96% of notes at the same length (a quantisation artifact), one has a register mean of 79.9.
- The chorus does not lift: the verse-to-chorus median lift is 0 in all four vocal songs.
- The second voice is silent under the singer in all four vocal songs (0.00–0.19 notes per bar).
- Section labels are noisy: one `% verse` is 44 bars of silence.
- All five carry about one chord symbol per bar and four of five are `L:1/32`; the skill's own corpus is `L:1/16` with no chords. The 600 therefore come from a different export than the skill's 177 tracks.
- The 600 are general styles, not the LoRA's style.

Conclusion: the 600 are **not safe for calibrating gates** for the LoRA style. They are a good source of **phrase rhythms, contours and section skeletons**, once filtered.

## 4. Proposal

Add a deterministic **baseline builder** that sits before the agent's composition step.

```
lyrics + style
   -> syllabify (+ fixed counter)            existing, patched
   -> phrase sidecar + section layout        existing
   -> donor retrieval (per section)          NEW
   -> adapters (remap / fit / lift)          NEW
   -> baseline score.abc + plan.json         NEW, passes the checker
   -> agent edits the baseline (small diffs) existing method, narrower scope
   -> checker once per change                existing
```

### 4.1 Donor library (offline, built once)

- Ingest the 600 files. Normalise units; trim silent tails; drop instrumentals, monotone-rhythm files and files that fail the contract.
- Segment vocal lines at gaps. For each phrase store note durations, rests, ties, bar span, contour as scale degrees and intervals, and section label. Store whole-song section skeletons (bar counts, silence layout, intro and interlude Ins riffs).
- Tag with mode family, tempo, meter and pace. Cluster; hand-listen only to cluster representatives.

### 4.2 Retrieval

For each section of the lyrics, match donor sections on the sequence of phrase lengths and note counts. Allow different donors for different sections. Enforce a diversity limit so outputs do not converge on a few donors.

### 4.3 Adapters (deterministic code, not free writing)

- **Degree remap** onto the declared maqam set (for Kurd: D, E♭, F, G, A, B♭, C), restating accidentals per bar.
- **Syllable fit:** stretch or trim a phrase to the syllable count using ties, rests and passing notes; rebuild bar sums.
- **Chorus lift:** apply the plan's lift to the chosen chorus donor.
- **Section tiling:** emit the `arrangement.section_plan` and `copies` entries automatically.

### 4.4 What the agent still decides

- Which donors and which operations.
- Placement of the maqam's defining colour (for Kurd, the E♭ events) and the cadence ladder.
- The melisma on the rhyme syllable.
- The three or four declared deviations.
- Taste edits to the baseline, one scoped change and one check each.

### 4.5 Guardrails

- **Similarity ceiling:** the output may not exceed a set interval n-gram overlap with any single donor (build on the skill's existing similarity check). The score is an adaptation, not a copy.
- **Donor quality filter:** donors must pass the checker's sanity guards before entering the library.
- **No gate calibration from the 600.** Their statistics are not used to set thresholds for the LoRA style.
- **Honest labelling:** the report states which donors were used and which checks ran offline.

## 5. Expected effect

The agent's output shrinks from a full score to a spec of choices plus a handful of local edits, and most of the repair loop disappears because the baseline passes the contract. **I expect a large cut in output and repair tokens, but I have not measured it.** The 10x figure is a target, not a result. Reading overhead does not shrink unless the skill is also split into a short core with references loaded on demand (section 6).

## 6. Companion changes (cheap, independent)

- Patch the syllabifier (line-initial hamzat waṣl; fatha plus dagger alif) and emit a per-word table for audit.
- Add a `--brief` mode to the checker that prints only failing lines.
- Make the pace a style-aware input and warn when it conflicts with the style tags.
- Report instrumental-tag-with-lyrics conflicts instead of resolving them silently.
- Split `SKILL.md` into a short core plus on-demand references; remove the stale internal references ("session 10", "T21") and the contradiction between `--strict-style` and "do not rewrite for a warning".
- Enforce a turn and token budget in the runner, not in prose.

## 7. Plan

1. **Measure (1 day).** Export per-turn input, output and thinking tokens for one 100k+ run. Sort turns by cost and confirm which of the four hypotheses dominates.
2. **Prerequisites.** Syllabifier patch, `--brief` checker, dialect decision (below).
3. **Pilot.** Extract phrases from a sample of the library; build the retrieval and adapters; run on the Kurd test lyrics; run the checker; record tokens and the score. Pilot input: the five files already in hand plus the Kurd lyrics.
4. **Scale** to the full library only if the pilot draft is already decent.

## 8. Success criteria

- Median tokens per run down by at least 5x on N representative lyrics, measured against the current process on the same lyrics.
- Baseline passes the contract and sanity checks with no repair pass in most runs.
- The final score, rendered through the LoRA and **listened to by us**, is judged no worse than a from-scratch score. The checker cannot decide this; listening is the quality gate.

## 9. Risks

- **Style mismatch:** general-style donors may import the wrong feel. Mitigation: borrow rhythm and contour only; filter by mode and meter.
- **No lyrics in the library:** matching is by note count, so the syllable fit is approximate. The LoRA does final alignment.
- **Formulaic output:** template stitching can produce the "phrase grid" sound. Mitigation: mutation operations and the existing critic points.
- **Homogeneity:** a diversity limit on donors.
- **Inherited transcription artifacts:** quality filter before ingest.
- **Over-trusting the checker:** it cannot judge whether a tune is good.

## 10. Open questions

1. **Which format does the LoRA expect:** `L:1/16` without chords (the skill's corpus) or `L:1/32` with a chord per bar (these files and the earlier sample)? The builder must target one.
2. Why are the five sampled files all within 1% of each other in size (5,329–5,373 bytes) though the songs run 288–352 s? An exporter cap or coincidence?
3. What share of the 600 are instrumentals?
4. Can the real per-turn token log be shared?
