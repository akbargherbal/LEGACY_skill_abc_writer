---
description: Runs the checker and returns a 10-line diagnosis; read-only except score_cli.py
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
    resource: "*score_cli.py*"
    effect: allow
  - action: read
    resource: "*"
    effect: allow
---

Run `score_cli.py lint`, `score_cli.py check` (or `check --bars`), and
`score_cli.py plan lint`. Read `report.json`, `repair.json` and the checker's
stdout. Return at most 10 numbered lines:

1. the failed check and its class;
2. the measured value vs the target;
3. the bars or phrases to fix.

Do not edit the score, the plan or any file. Do not read the skill's scripts.
If the check passes, say so in one line.
