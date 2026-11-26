---
description: Builds seed.abc and the delivery docs after the score is released
mode: subagent
model: deepseek/deepseek-flash#high
steps: 15
permissions:
  - action: edit
    resource: "*"
    effect: allow
  - action: edit
    resource: "score.abc"
    effect: deny
  - action: edit
    resource: "plan.json"
    effect: deny
  - action: edit
    resource: "phrases.json"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
  - action: shell
    resource: "*score_cli.py*"
    effect: allow
  - action: shell
    resource: "*verify_package.py*"
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
---

The score is frozen and released. Build the delivery:

1. Run `score_cli.py seed`, then `score_cli.py seed-check`. If the seed already
   exists and is current, do not rebuild it.
2. Edit `seed.abc` only for orchestration: chords, `%%MIDI`, drums. Never change
   the melody, and never edit `score.abc`.
3. Write `seed_sheet.md` as exactly 10 numbered lines of rules; `notes.md` as
   exactly 10 numbered lines; `CHANGES.txt` as the plan's deviations plus the
   checker's MEASURED block from `report.json` plus open warnings. Use the
   `MEASURED` block the release wrote; do not retype numbers by hand.
4. Run `verify_package.py` with the score, plan, seed, sheet, notes and report:

   ```bash
   python3 skills/abc-score-writer/scripts/verify_package.py \
     --score score.abc --plan plan.json --seed seed.abc \
     --sheet seed_sheet.md --notes notes.md --report report.json --json verify.json
   ```

   If `loans.json` exists, also run `verify_loans.py --loans loans.json
   --plan plan.json`. Report both results in one line.

Do not touch `score.abc`, `plan.json`, `phrases.json` or `prosody.json`. There
is no core step in 1.0: `core --snapshot`, `core_review.md` and `--core` belong
to the archived 0.9 workflow and are not part of this delivery.
