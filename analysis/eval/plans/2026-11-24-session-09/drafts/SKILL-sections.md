# Phase 1 — `SKILL.md` / `craft.md` replacement sheet

**Apply on the VM.** Not applied to this checkout. This is a section-level
rewrite, not a line patch: each block below replaces the whole quoted block.

---

## 1. Tool map (`SKILL.md`, the scripts block)

**Replace:**

```
<skill>/scripts/syllabify.py       lyrics -> numbers (letters, syllables, bars)
<skill>/scripts/checker.py         score + plan -> PASS/WARN/FAIL + the measured block
<skill>/scripts/calibration.json   the 177-track thresholds (do not edit)
<skill>/scripts/abc_tools.py       vendored runtime parser (the renderer's contract)
<skill>/scripts/selftest.sh        proves both work on example/ (run once if in doubt)
```

**With:**

```
<skill>/scripts/syllabify.py       lyrics -> numbers (letters, syllables, bars)
<skill>/scripts/checker.py         score verifier: PASS/WARN/FAIL + measured block
<skill>/scripts/verify_package.py  package verifier: score<->seed, Drums, core, docs
<skill>/scripts/craft.py           report-only tune mirror (rhythm, cadence, register)
<skill>/scripts/abc_tools.py       score parser CLI: inspect / strip-chords / compare
<skill>/scripts/calibration.json   the 177-track thresholds (do not edit)
<skill>/scripts/selftest.sh        proves the tools work on example/
```

The next sentence stays: «Run the scripts; do not read them.» The parser CLI is
now documented; it is for the two-voice score, not the seed.

---

## 2. `SKILL.md` §3.3, item 9 — the seed_sheet order

**Replace:**

```
   **2-beat hole** per 4 bars. Put the rules in `seed_sheet.md` (exactly 10
   numbered lines, no title). `phrases.json` owns the per-line table; do not
   retype it. A drummer cannot answer a grid; see `references/rhythm.md`.
```

**With:**

```
   **2-beat hole** per 4 bars. Record the rules; write `seed_sheet.md`
   **after** `score.abc` as exactly 10 numbered lines (no title).
   `phrases.json` owns the per-line table; do not retype it. Do not write the
   full frame before the core. A drummer cannot answer a grid; see
   `references/rhythm.md`.
```

---

## 3. `SKILL.md` — the line that says "before the first bar"

**Replace:**

```
**Write `seed_sheet.md` before the first bar, as exactly 10 numbered lines
(no title, no blank line).** Rules, not per-line results: frame, cell, period
```

**With:**

```
**Write `seed_sheet.md` after `score.abc`, as exactly 10 numbered lines
(no title, no blank line).** Rules, not per-line results: frame, cell, period
```

---

## 4. Register table — one number

**Replace:**

```
| register | mean 74, top 84, `max_top` 86 for a full song; one peak per section; `tessitura_share_ge_c5_max` 0.80 | corpus median/P95 |
```

**With:**

```
| register | mean 70, top 80, `max_top` 84; one peak per section; `tessitura_share_ge_c5_max` 0.80 | example/plan.json |
```

Any other `74` **as the plan default** is removed. The sanity gate `74 ± 5`
and the corpus tables stay: they are the validity band, not the composing
target. If a high-tenor/female release needs 74, the task says so explicitly;
it is not a default.

---

## 5. §3.5 Check — one policy

**Replace the paragraph:**

```
**The checker is your measurement instrument, not a final exam.** Run it with
`--json report.json` after the first `score.abc`, and again after a named fix.
Read `report.json.measured`; it is the authoritative block for bar counts, note
counts, register, duration spread, ties, silence, phrase endings and the rest.
Do not write your own ABC parser or statistics script. The vendored
`abc_tools.py` is the renderer's parser; the checker is the way to use it. If a
number you need is missing, add it to the checker, not to a throwaway script.
```

**With:**

```
**The checker is the score verifier, not a final exam.** Run it with
`--json report.json` after the first `score.abc`, and again only after a named
fix. Read `report.json.measured`; it is the authoritative block for bar counts,
notes, register, duration spread, ties, silence and phrase endings. Stop after
a pass. A global sanity failure (e.g. `repeated_share`) allows one full rewrite
and one verification; any contract error after that is a named fix. Maximum
four runs. Do not write a parser or a statistics script: the seed/drums/docs
checks are in `verify_package.py`; if a number is missing, extend that file,
not a throwaway script.
```

---

## 6. `checker.py --help` — one line

**Replace:**

```
This is the skill's only verifier. It runs the vendored runtime parser
```

**With:**

```
This is the score verifier. For seed/drums/docs use verify_package.py. It runs
the vendored runtime parser
```

No logic change; `calibration.json` untouched.

---

## 7. `SKILL.md` §3.3 — the craft fallback

**Replace:**

```
In the source repo,
`analysis/measure_craft.py score.abc` prints the melodic ones and
`analysis/measure_rhythm.py score.abc --seed seed.abc` prints the rhythm and
drum-interaction ones; if you only have the shipped zip, count them on 4–8
phrases by eye.
```

**With:**

```
Run `craft.py score.abc --seed seed.abc --json craft.json`; it prints the
melodic, rhythm and drum-interaction numbers. It is a mirror, not a gate.
```

---

## 8. `references/craft.md` §10 — the same fallback

**Replace:**

```
Run `analysis/measure_craft.py score.abc` for 3–8 if you have the source repo
(and `analysis/measure_rhythm.py score.abc --seed seed.abc` for 11–13). It is a
mirror, not a gate.
```

**With:**

```
Run `craft.py score.abc --seed seed.abc --json craft.json` for 3–8 and 11–13.
It is a mirror, not a gate.
```

---

## 9. Removal check (must be empty)

Run from `02_maqam-score/`:

```bash
grep -R "74" SKILL.md references/ example/ scripts/checker.py
grep -R "only verifier\|the checker is the way\|count them on 4–8 phrases by eye" .
grep -R "analysis/measure_craft\|analysis/measure_rhythm" .
```

Expected: no `74` **as the plan default**; the sanity `74 ± 5` in
`checker.py`/`numbers.md`/`reference.md` and the corpus data stay. No old
verifier fallback; no source-repo path. `verify_package.py` and `craft.py` are
the only package verifiers.

---

## 10. `task.md` — one page

Copy `drafts/task.md` into the session package. It contains inputs, session
choices, acceptance and stop rules; it points to `SKILL.md §3` and does not
repeat the 10-line rules, the checker policy or the tool commands.
