---
description: Runs the scorecard and release dry-run; read-only diagnosis
mode: subagent
model: deepseek/deepseek-flash#high
steps: 8
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
  - action: shell
    resource: "*scorecard.py*"
    effect: allow
  - action: shell
    resource: "*score_cli.py*"
    effect: allow
  - action: shell
    resource: "*verify_loans.py*"
    effect: allow
  - action: shell
    resource: "ls *"
    effect: allow
  - action: shell
    resource: "pwd"
    effect: allow
  - action: read
    resource: "*"
    effect: allow
  - action: read
    resource: "skills/abc-score-writer/scripts/**"
    effect: deny
---

Run the 1.0 checks, read-only:

```bash
python3 skills/abc-score-writer/scripts/scorecard.py score.abc \
  --plan plan.json --phrases phrases.json
python3 skills/abc-score-writer/scripts/score_cli.py release --dry-run
```

If `loans.json` exists, also run `verify_loans.py --loans loans.json --plan
plan.json`. Read the card, `report.json` and `verify.json` if they exist. Return
at most 10 numbered lines:

1. each `BLOCKING` check and its measured value vs the band;
2. each `RELEASE-BLOCKING` check (what `release --dry-run` fails);
3. the seams or bars to rewrite;
4. the next action: rewrite whole, polish seams, release, or package.

Do not edit the score, the plan or any file. There is no `core`, `line` or
`patch` step in 1.0; do not run the legacy 0.9 commands. If both blocks are
empty and release passes, say so in one line.
