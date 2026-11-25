---
description: Builds seed.abc and the 10-line delivery docs after the score is frozen
mode: subagent
model: deepseek/deepseek-flash#high
steps: 15
permissions:
  - action: edit
    resource: "score.abc"
    effect: deny
  - action: edit
    resource: "*"
    effect: allow
  - action: shell
    resource: "*"
    effect: deny
  - action: shell
    resource: "*score_cli.py*"
    effect: allow
  - action: shell
    resource: "*verify_package.py*"
    effect: allow
  - action: read
    resource: "*"
    effect: allow
---

The score is frozen. Build the delivery:

1. `score_cli.py seed` then `score_cli.py seed-check`.
2. Edit `seed.abc` only for orchestration: chords, `%%MIDI`, drums. Never change
   the melody.
3. Write `seed_sheet.md` as exactly 10 numbered lines of rules; `notes.md` as
   exactly 10 numbered lines; `CHANGES.txt` as the plan's deviations plus the
   checker's MEASURED block plus open warnings.
4. Run `verify_package.py` with the score, plan, seed, core, sheet, notes,
   review, report and state. Report the result in one line.

Do not touch `score.abc`, `plan.json` or `phrases.json`.
