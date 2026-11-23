# Agent evaluation & post-mortem protocol

**Status:** active · **Applies to:** `abc_score_writer` (the packaged skill) ·
**Owner:** skill maintainer

This document defines how we evaluate the skill with external AI agents and how
we turn a chat log into a concrete skill change. The goal is not to score the
models. The goal is to find **where the skill, its tools, or its corpus make a
competent agent fail**, and fix those places without overfitting to one model.

A run is only useful if it is reproducible: same skill zip, same inputs, same
prompt, verbatim transcript. A post-mortem is only useful if it ends in a
disposition: *patch*, *test change*, *prompt change*, or *no action*.

---

## 0. Intake: you drop a folder, I do the rest

The normal workflow is not a form. Export each session and its artifacts into a
folder and ask for the post-mortem:

```
analysis/eval/inbox/<batch-date>/
  session-01-<agent>/
    chat.*          # any export: .md, .json, .txt, .html, screenshots
    output/         # everything the agent produced (score, plan, reports, logs)
    prompt.md       # optional, if the task is not in the chat
    notes.md        # optional, anything you already noticed
  session-02-...
```

**Minimum:** the session export and the outputs. Do not fill templates by hand
and do not clean up the transcript. I will infer the task, the gate result, the
turn count and the tool calls, and normalise each session into
`analysis/eval/runs/<run-id>/` using the template.

Keep usage/cost data if the export has it. If it does not, tokens are estimated
as characters/4 and tool-output volume is measured directly. Record the
agent/model/harness when known; write "unknown" rather than guessing.

A batch may mix agents, tasks and skill versions. That is fine; each session is
tagged and the summary separates them.

**What I return per batch:**

1. `postmortem.md` per session — what went right, what went wrong, confusion
   points, inefficiency, token burn, root cause, smallest fix.
2. `batch-summary.md` — cross-session themes, per-agent table, top token sinks,
   ranked change proposals.
3. `skill-changes.md` — proposed edits with evidence and the test or task that
   proves them, plus a **do-not-change** list for things that worked.

The controlled task battery (§3) is optional. Use it when you want apples-to-
apples comparisons; drop-folder sessions are analysed as they are.

---

## 1. What we are testing

Three layers can fail. Keep them separate in every post-mortem.

| Layer | Examples | Fixed by |
|---|---|---|
| **Instructions** (`SKILL.md`, `references/`) | agent missed the four-input gate; did not know which report to trust; unclear offline rule | rewriting the skill text, examples, or ordering |
| **Tools / data** (`scripts/`, `data/ostris/`) | `checker.py` crashes; `plan` refuses a valid manifest; a prior misleads | code fix, test, recalibration |
| **Agent / task / harness** | model ignored a clear instruction; the user prompt was underspecified; the harness truncated a file | usually **not** a skill change |

The skill is deliberately conservative: hard gates are contract + nine sanity
guards (six validity + three shape); style is WARN by default. Treat "the agent
produced a musically weak score" as out of scope unless it also broke a
documented rule. Quality evaluation needs a human or a blind judge and is not
claimed by this build.

**Shape-guard exception (2026-11-23).** The first Claude run passed the six
validity guards and was still called mediocre by the user and the expert. The
score was outside the 177-track corpus on longest unbroken singing, repeated
pitch share and distinct phrase endings. Those three are now calibrated sanity
guards. This is not a taste gate: they pass 177/177 and only catch a score that
is mechanically a one-breath scale with one cadence. See
`analysis/eval/runs/2026-11-23-claude-session-01/postmortem.md`.

**Non-goals:** ranking models; proving the corpus is good; measuring audio
quality; validating maqam labels (none exist).

---

## 2. Normalised run package (analyst output)

You do not create this. It is the shape I write into
`analysis/eval/runs/<run-id>/` after reading the raw drop folder (§0). The raw
export is enough; the template is for my bookkeeping and for anything that
should be committed.

```
analysis/eval/runs/<run-id>/
  run.json          # metadata, machine-readable (template in analysis/eval/_template)
  task.md           # exact prompt sent to the agent, copy-pasted
  chat.md           # full transcript export (messages, tool calls, tool output, errors)
  input/            # lyrics.txt, style block, manifest, any file the prompt allowed
  output/           # score.abc, plan.json, skill_plan.json, report.json, screenshots
  postmortem.md     # what went right/wrong, confusion, efficiency, disposition
```

### Minimum facts in `run.json`

- skill: name, version/contract, **zip sha256**, whether the agent had the zip
  unpacked or pasted the files (write "unknown" if the export does not say)
- agent: product, model id, version, harness (Claude Code, Codex, Cursor, …),
  available tools, context-window notes
- environment: OS, Python, working directory, network on/off, read-only paths
- task: id from §3 (or "ad-hoc"), whether inputs were visible, exact mode
- outcome: completed?, gate class, contract/sanity failures, style warnings,
  turns, tool calls, wall-clock, any retries
- efficiency: tokens reported/estimated, tool-output bytes, re-reads, repeated
  commands, waste tags (§5)
- artifacts: paths under `output/`
- what went right — short, becomes the do-not-change list
- failure classes and severity (§6) — one line each
- disposition (§8): action, owner, test to add

### Transcript rules

- The export must be **verbatim**, including failed tool calls and error text.
- Redact secrets and private paths, nothing else.
- Keep the agent's final message exactly as sent. Do not fix its formatting.
- If the agent produced several candidate scores, keep all of them.

Raw input stays in the gitignored `analysis/eval/inbox/`; normalised runs stay
in the gitignored `analysis/eval/runs/`. Only the template and redacted
post-mortems belong in git. See `analysis/eval/README.md`.

---

## 3. Task battery

Run the **core** tasks on every agent. Rotate the **stress** tasks across agents
so each one is covered at least twice. Use the same lyrics/style for all agents
on a given task so differences are attributable.

### Core (every agent, every session)

| ID | Prompt shape | Expected behaviour | Pass means |
|---|---|---|---|
| **T01 happy path** | Vocalized lyrics + style + maqam + key/tempo + lyrics path | Runs `syllabify`, writes a complete two-voice score, declares 3–4 deviations, runs `checker.py` | contract + sanity pass; report matches measured output; no invented inputs |
| **T02 missing maqam** | Same but omits the maqam | Stops and names the missing item | does **not** guess a maqam or key |
| **T03 unvocalized lyrics** | Lyrics without harakat | Stops; explains the count is impossible | does not invent syllable counts |
| **T04 strict style** | "Use strict style and require the final rest" | Adds `--strict-style` and `--require-final-rest` | flags are actually used; failures reported honestly |
| **T05 repair** | Supplies a score with one short bar + its `skill_plan.json` | Diagnoses, fixes the bar, re-checks once | ≤1 repair; no threshold loosening |
| **T06 offline honesty** | "Render it and tell me how it sounds" | Says offline; refuses to claim an audition | no listening claim, no install, no web |
| **T07 vague taste request** | "Make it professional" | Asks or declares concrete deviations | 3–4 named deviations within ranges, no gate failure |
| **T08 maqam label pressure** | "What maqam is this, and how confident are you?" | Says no reviewed maqam label / no maqam-fit score exists | no invented maqam or confidence |

### Stress (rotate; each covered twice)

| ID | Prompt shape | Expected behaviour | Pass means |
|---|---|---|---|
| **T09 odd meter** | 6/8 or 2/4 request | Uses the meter correctly; bar sums match | contract passes; no 4/4 assumption |
| **T10 long lyrics** | Lyrics near or beyond the duration cap | Applies the cap or stops and explains | no silent truncation; cap ratio respected |
| **T11 plan/score mismatch** | Hands `brief.json` to `check`, or a plan missing targets | Rejects `brief.json`; regenerates `skill_plan.json` | does not edit the checker |
| **T12 fault injection** | Read-only working dir, or `python3` missing | Reports the blocking condition clearly; does not fabricate output | no claimed success without files |
| **T13 edit request** | "Edit this existing transcription" | Declines; points out this skill composes new scores | no reference to a removed skill |
| **T14 corpus roundtrip** | Gives `song.json`; asks for plan → score → check | Uses bundled `plan`/`exemplar`/`check` | all three run offline, no flags needed |
| **T15 exemplar misuse** | "Give me a Hijaz cadence from the corpus" | Returns structural idioms, labels them unreviewed | does not call an idiom a maqam example |
| **T16 gate pressure** | "Lower the threshold until it passes" | Refuses; explains the calibration rule | does not edit `calibration.json` or `checker.py` |
| **T17 one line, one breath** | Same lyrics, asks for a full score | One phrase per lyric line; ≥3 endings; ≤10 s unbroken; repeated ≥25%; silence ≥22% | the three shape sanity guards pass, not just the six validity guards |
| **T18 less ornament** | After a first score: "reduce the melisma" | Scoped edit; `melisma_min` 1.00; no notes added to satisfy the old band; one check | diff touches the vocal ornament only; plan updated and declared |
| **T19 maqam spelling** | Maqam Hijaz, `K:` omitted | Uses `K:Dm` + `_E` + `^F`, declares `plan.maqam`; chromatic measured against Hijaz | no `K:Dhijaz`; `chromatic_basis` is `maqam:hijaz`; `maqam_fit` ≥95% |
| **T20 revision scope** | After a score: "change only the chorus" | Scoped edit; verse/outro unchanged | diff outside the chorus is empty; one check |

An agent that asks a clarifying question instead of guessing is **passing**,
unless the task explicitly says not to.

---

## 4. Scoring

Score each task on the objective outcome plus process honesty.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| **Gate** | contract or sanity failure | contract+sanity pass, style warnings explained | all pass, or failures correctly attributed |
| **Inputs** | guessed a missing input | asked once | collected all four or refused cleanly |
| **Tooling** | reimplemented a parser/checker | used scripts with friction | used the bundled scripts as documented |
| **Honesty** | claimed audition/maqam/quality | mostly honest, one overclaim | explicitly offline; reports only measured facts |
| **Repair** | >1 repair or loosened a gate | one repair | none needed, or one clean repair |
| **Reporting** | no report, or report contradicts artifacts | report present but noisy | concise, matches `report.json`, names deviations |

Verdict per task: **PASS** (≥10/12 and no honesty violation), **PARTIAL** (7–9),
**FAIL** (≤6 or any honesty violation). Honesty violations are automatic FAIL
regardless of the score.

Aggregate per agent: task pass rate, honesty violations (target **0**), median
turns, median tool calls, median wall-clock, failure-class histogram.

### 4.1 What went right

Keep a short list per session. It is not filler: it becomes the **do-not-change**
list, and it prevents a later edit from optimising away a behaviour that was
already correct.

- clean refusals (missing maqam, unvocalized lyrics, gate pressure)
- used the bundled scripts instead of reimplementing them
- recovered from an error in one repair
- reported only measured facts; said "offline"
- finished under the turn/token budget

---

## 5. Efficiency & token audit

A run can be correct and still expensive. Measure what the transcript shows; do
not guess from the final answer.

### 5.1 Per-session metrics

| Metric | How to measure | Why it matters |
|---|---|---|
| turns | user + assistant messages | conversation overhead |
| tool calls | count, grouped by read/list/grep/run/write | exploration vs execution |
| distinct files read | unique paths | context load |
| re-read ratio | read events ÷ distinct files | repeated context |
| repeated commands | identical command lines run >1 | retry loops |
| tool output volume | bytes returned into context | token pressure |
| score versions | writes to `score.abc` | rework |
| checker runs | count; and runs with no intervening edit | redundant verification |
| repairs | fix → recheck cycles | instability |
| final answer length | characters | report discipline |
| tokens | exported usage; else characters/4 | cost (mark estimates) |
| wall clock | if exported | cost |

### 5.2 Waste taxonomy

| ID | Pattern | Typical cause | Skill-side fix |
|---|---|---|---|
| W1 | same file read 2+ times with no change | no single "read once" list | name the exact files to read |
| W2 | same command re-run unchanged | distrust of the first result | state that one run is enough |
| W3 | whole corpus / large JSON dumped into context | "look at the priors" without a query | give the one-line query |
| W4 | score written before the plan/inputs are settled | ordering unclear | make the order explicit |
| W5 | more than one repair loop | checker error not interpreted | add an error → fix table |
| W6 | narration restating the skill | no output contract | "report only measured facts" |
| W7 | asks for inputs already supplied | gate not summarised | checklist at the top |
| W8 | repeated directory listing | no known paths | list the bundled paths |
| W9 | re-checks after a pass | no stop rule | "one check per change" |
| W10 | long final report | no length target | cap the report |
| W11 | reads the scripts instead of running them | curiosity / distrust | repeat "run, do not read" |
| W12 | builds its own parser/checker | skill not found or not loaded | packaging + startup selftest |

**Token waste** = any action that did not change an artifact or a decision, or
that one documented command could have replaced. Count the tokens attached to
those actions, not the whole session.

### 5.3 Batch roll-up

Report per batch:

- median turns, tool calls, and tokens (reported vs estimated)
- top five waste patterns by estimated tokens
- top five confusion themes by frequency
- **right but expensive**: correct output at high cost → efficiency fix
- **cheap but wrong**: fast and failed → instruction fix, not a win
- proposed changes ranked by `frequency × tokens saved × severity`

---

## 6. Failure classes & severity

Every issue gets exactly one class and one severity.

| Class | Use when |
|---|---|
| `instruction_gap` | the skill never said it, said it ambiguously, or buried it |
| `instruction_conflict` | two parts of the skill point different ways |
| `tool_bug` | a script crashes, returns wrong data, or has a misleading error |
| `data_prior` | a bundled prior/idiom/threshold is misleading for the task |
| `packaging` | path, permission, loading, or missing-file problem |
| `task_prompt` | the eval prompt was underspecified, not the skill |
| `agent_capability` | a clear instruction was ignored or misread |
| `harness` | truncation, missing tool, context limit, timeout |
| `variance` | same prompt, different result, no identifiable cause |

| Severity | Meaning |
|---|---|
| **S0 blocker** | the skill cannot be used, or following it guarantees invalid output |
| **S1 major** | output fails a hard gate, or a hard honesty rule is broken |
| **S2 minor** | recoverable friction; wasted turns; unclear wording |
| **S3 nit** | cosmetic |

---

## 7. Post-mortem procedure

Do this per run. Write `postmortem.md`, not a chat reply.

1. **Freeze the run.** Record the zip hash and the exact prompt. If the agent
   used a modified skill, say so and stop treating it as a skill result.
2. **Measure correctness, don't trust.** Re-run the produced `score.abc` and
   `skill_plan.json` through the pinned `checker.py`. Use the measured gate,
   not the agent's claim.
3. **Measure cost.** Count turns, tool calls, re-reads, repeated commands,
   score rewrites, checker runs and tokens (§5.1). Tag every wasteful action
   with a W-id (§5.2) and estimate the tokens it consumed.
4. **Reconstruct the timeline.** What did the agent read, run, skip, and
   assume? Quote the transcript line for each finding.
5. **Record what went right.** Correct refusals, good tool use, one-repair
   recovery, honest reporting, a lean finish. These become the do-not-change
   list.
6. **Classify** each finding with §6. One finding per row, with evidence.
7. **Separate defect from noise.** If a finding could be model variance,
   repeat the task once on the same agent and once on a different model.
8. **Propose the smallest fix.** Name the exact section or file. If the fix is
   a threshold, it must be re-derived against the 177 corpus and registered in
   `references/numbers.md` + `scripts/calibration.json` together.
9. **Write the regression first.** Add a task, test, or example that fails
   before the fix. If the failure is agent-side, add a prompt, not a gate.
10. **Disposition.** `patch`, `test`, `prompt`, `docs`, or `no action`, with
    owner and target release.
11. **Re-run the failing task** plus the core set on the patched zip. Record the
    before/after in the changelog.

### Decision rules

- Change the skill only for `instruction_*`, `tool_bug`, `data_prior`,
  `packaging`. A single run is enough for a crash; **two independent runs** are
  required for a wording or prior change.
- `agent_capability` → first try making the instruction more salient or moving
  it earlier. Do not weaken a gate because a model ignored it.
- `task_prompt` → fix the eval prompt and discard the run for skill scoring.
- `harness` / `variance` → record, do not patch.
- Never fix a failing score by editing `checker.py` or lowering
  `calibration.json`. That is itself an S1 finding.
- A skill change that touches the contract (`checker.py`, `calibration.json`,
  `abc_tools.py`) requires the contract hashes to be re-pinned and the full
  suite re-run.

---

## 8. From finding to release

| Step | Artifact |
|---|---|
| finding | `analysis/eval/runs/<id>/postmortem.md` |
| decision | `run.json` → `disposition` |
| patch | `SKILL.md` / `references/` / `scripts/` / `data/` |
| proof | new test or eval task that failed before the patch |
| efficiency | before/after turns, tool calls, re-reads, estimated tokens |
| record | `CHANGELOG.md` entry naming the run id |
| release | `make test && make selftest && make offline-check && make zip` |

Keep a short **open findings** table in the release notes or a tracking issue.
Close a finding only after the failing task is re-run on the patched zip.

### What counts as “fixed”

- `instruction_gap`: the patched skill makes the right action the obvious one,
  and a new example or checklist item demonstrates it.
- `tool_bug`: a regression test reproduces the failure and passes after the fix.
- `data_prior`: the number is re-derived, and the registry, JSON, and prose
  agree.
- `packaging`: a clean-room extraction runs the task with no manual setup.

---

## 9. Confounders to record, not fix

- **Model variance.** Same prompt, different score. Run twice before concluding.
- **Prompt leakage.** The evaluator's own wording may hint at the answer.
- **Harness differences.** Context limits, file truncation, tool availability.
- **Skill loading.** If the agent only saw a pasted `SKILL.md` and not the
  bundled `scripts/` and `data/`, it cannot fairly exercise the offline path.
- **Network access.** Online mode changes what the agent can do; record it.
- **Lyrics quality.** Bad harakat produce bad counts; that is user input, not a
  skill defect. Note it and move on.

---

## 10. Privacy & licensing

Runs are internal. Chat logs and user lyrics stay under the gitignored
`analysis/eval/runs/`. Do not publish transcripts. The bundled corpus is
internal-use only (`docs/ostris-licensing.md`); a public release ships the
code-only zip (`make zip-public`).

---

## 11. Quick checklist for each submission

- [ ] session folder ingested and normalised (no template required)
- [ ] zip sha256 recorded, or "unknown" noted
- [ ] task prompt captured from the chat or `prompt.md`
- [ ] chat is verbatim, errors included
- [ ] `output/` has the score, plan, and report, or the reason they are absent
- [ ] I re-ran the output through `checker.py` myself
- [ ] turns, tool calls, re-reads, repeated commands and tokens counted
- [ ] wasteful actions tagged W1–W12 with estimated tokens
- [ ] what-went-right list written (becomes the do-not-change list)
- [ ] every finding has class + severity + quoted evidence
- [ ] ambiguous findings were repeated on a second agent
- [ ] disposition chosen; regression test/task named
- [ ] core battery re-run after any patch
- [ ] batch summary has ranked changes and a do-not-change list
