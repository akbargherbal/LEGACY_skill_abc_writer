# Post-mortem — `<run-id>`

**Task:** T01 · **Agent:** `<model>` · **Harness:** `<harness>` ·
**Skill zip:** `<sha256>` · **Verdict:** PASS / PARTIAL / FAIL

## 1. What the agent produced

One paragraph. Cite artifacts. State the **measured** gate from a fresh
`checker.py` run, not the agent's claim.

| Check | Measured | Agent claimed |
|---|---|---|
| contract | | |
| sanity | | |
| style | | |
| final rest | | |

## 2. What went right

- correct refusal / clean gate handling:
- tool use:
- recovery:
- honesty:
- lean finish:

These become the **do-not-change** list for this batch.

## 3. Confusion points

Where the agent had to guess, re-read, ask, or contradict itself. Quote the
moment.

| # | Moment | What was unclear | Cost |
|---|---|---|---|
| C1 | | | turns / tokens |

## 4. Efficiency & token accounting

| Metric | Value | Source |
|---|---|---|
| turns | | transcript |
| tool calls | | transcript |
| tokens | | reported / estimated (chars÷4) |
| tool output bytes | | transcript |
| distinct files read | | transcript |
| re-read ratio | | computed |
| repeated commands | | transcript |
| score versions | | output/ |
| checker runs | | transcript |
| repairs | | transcript |
| final answer chars | | transcript |

Waste found:

| W-id | Where | Estimated tokens | Fix |
|---|---|---|---|
| | | | |

## 5. Timeline

Quote the transcript. What did it read, run, skip, assume?

1. …
2. …

## 6. Findings

| # | Class | Sev. | Where | Evidence (quote) | Smallest fix |
|---|---|---|---|---|---|
| F1 | | | | | |

## 7. Defect or noise?

- repeated on same agent? yes/no — result:
- repeated on second model? yes/no — result:
- conclusion: skill defect / agent capability / prompt / harness / variance

## 8. Disposition

- action: patch / test / prompt / docs / no action
- files to touch:
- regression to add (test id or eval task):
- owner / target release:

## 9. Re-run

- patched zip sha256:
- this task after patch:
- turns/tokens before → after:
- core battery result:
