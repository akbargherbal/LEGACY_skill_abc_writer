# Session 16 — token economy, hypothesis check, and visible limitations

**Status:** analysis (no score changes) · **Date:** 2026-11-26
**Model:** `deepseek/deepseek-flash#low` · **Agent:** `composer` · **Skill:** `abc-score-writer` 1.0.0
**Evidence:** `analysis/eval/inbox/deepseek_session_16/opencode_session_16.json`
(69 messages, one session) and `FINAL_session-16.zip`
**Score:** 82 bars, 400 vocal + 104 Ins notes, 1,719 cl100k tokens (2,512 bytes)
**Verdict:** valid low-thinking run, structurally valid score, **economy failure at
53.1×**; the 10× target is not reachable by draft-count alone at the observed
per-draft cost.

Turn numbers in this document are **0-based message indices** (`m0`–`m68`) in
the exported JSON.

---

## 0. الخلاصة التنفيذية

- **الجلسة صالحة كاختبار `low`**: `init` طبع `FORM BUDGET: 64 vs 82`، والوكيل
  أعاد بـ`--force --bars 82 --sections`، والسجل يثبت `after.variant = "low"` في
  كل نداء. الملف سليم: 82 بار، 400 نوتة، وتقرير `release` يطابق بصمة `state.json`.
- **الاقتصاد فشل**: ‎91,243‎ مولّد ÷ ‎1,719‎ = **53.1×** (الجلسة 15: 54.2×).
  `low` خفّض التفكير 12.9% لكنه رفع الكتابة 36.7%، فالمحصلة ‎−3.5%‎ فقط.
- **84% من التوكنز في حلقة الكتابة نفسها**: ‎24,000‎ احتراق سقف بلا مخرجات،
  و‎49,303‎ في عشر مسودات كاملة. الأدوات والتغليف أقل من 10%.
- **أخطر عيب صحة**: البطاقة قالت `0 blocking` مرتين، و`release` رفض الملف نفسه
  بـ3 ثم 1 hard failures؛ فأنتج الوكيل 4 مسودات زائدة (~20k).
- **الفرضية صحيحة في الاتجاه، خاطئة في السببية**: الكتابة الكاملة أفضل من
  السطرية، لكن الكلفة يحكمها **عدد المسودات × كلفة التفكير لكل مسودة**، لا
  حجم الوحدة. متوسط المسودة 4,930 توكن، وأربع مسودات وحدها تتجاوز ميزانية 10×.
- **23 finding**: Tooling 6، Self-assessment 5، Instruction 3، Musical quality 3،
  Tokenization/ABC 2، Cross-voice 1، Long-range 1، Arithmetic 1، Other 1.
  منها 1 inherent (غياب الأذن) و22 قابلة للمعالجة.
- **التوصيات الخمس**: preflight حسابي، prose من `report.json`، توحيد
  `scorecard` مع `release`، حدود صلبة للمسودات/الخطوات، وإصلاح `packager`
  وفحص الانسجام/المقام في `seed`.

---

## 1. Run validity and artifact integrity

| Check | Result | Evidence |
|---|---|---|
| `init` printed FORM BUDGET | pass | m5: `FORM BUDGET: 64 bars vs syllabify 82 (-22%)` |
| Form decision | 82 with `--force --bars 82 --sections` | m7; one failed attempt with `chorus2` at m6 |
| Variant | `low` on every primary call | `abc-session.log`, all 77 lines |
| One session / complete export | pass | `ses_de9b64…`; ends at m68 `idle` |
| Score integrity | 82 bars / 400 vocal notes | `abc_tools.parse`; `report.json` |
| Report ↔ state | sha256 match | `a9b7dbf8…` in both |
| Archive ↔ last write | identical | m53 write == `score.abc` |
| Audio | none | no `.wav/.mp3/.mid`; quality verdict suspended |

The run is a real low-thinking test, not a dirty-room artifact. The economy
result is therefore interpretable.

---

## 2. Token economy

### 2.1 Headline

| | Session 15 (`high`) | Session 16 (`low`) | Δ |
|---|---:|---:|---:|
| output | 17,783 | **24,314** | +36.7% |
| reasoning | 76,801 | **66,929** | −12.9% |
| generated | 94,584 | **91,243** | −3.5% |
| score tokens | 1,744 | **1,719** | — |
| ratio | 54.2× | **53.1×** | −1.1 |
| whole drafts | 5 | **10** | ×2 |
| scorecard runs | 18 | **12** | −6 |
| pure 8k burns | 5 = 40,000 | **3 = 24,000** | −16k |
| duration / cost | 16.6 min / $0.0885 | **8.9 min / $0.074** | faster |

> `measure_session.py` prints `checker runs 0` because it counts `checker.py`,
> not `scorecard.py`. The audit counts 12 `scorecard.py` runs directly.
> It also does not count `edit` patches on `score.abc` (4 here).

### 2.2 Where the tokens went

| Bucket | Tokens | Share |
|---|---:|---:|
| Score-writing loop: 10 writes + 4 edits | **52,431** | 57.5% |
| 8k cap burns with zero output (m10, m27, m34) | **24,000** | 26.3% |
| Packaging | 3,868 | 4.2% |
| Discovery / help / explain-metric | 2,662 | 2.9% |
| `init` (incl. failed `chorus2` attempt) | 2,472 | 2.7% |
| `scorecard` | 2,367 | 2.6% |
| Section-check + release | 1,938 | 2.1% |
| Plan-puzzle + other | 1,500 | 1.6% |
| **Total** | **91,238** | 100% |

**84% of all generated tokens are the writing loop** (draft turns + cap burns).
Tooling and the card together are under 10%.

### 2.3 Waste, ranked

1. **24,000 tokens with zero output (26.3%).** m10, m27, m34 each ended
   `finish: "length"`, `output: 0`, `reasoning: 8000`. The synthetic reply said
   “Break the remaining work into smaller pieces” (m11, m28, m35). This is the
   only bucket with no artifact at all; part of the plan survives in context,
   but the call is cut before it can write.
2. **Ten whole drafts instead of 1–4 (49,303 tokens, 54%).** Average 4,930 per
   draft: ≈1,750 write + ≈3,200 reasoning. The draft count alone is 2.5× the
   declared bound.
3. **Card/release severity split (~20k, 4 extra drafts).** m39 card:
   `0 blocking`; m40 release: `3 hard`. m44 card: `0 blocking`; m45 release:
   `1 hard`. Every failing item was printed as `POLISH` on the preceding card.
4. **Invalid first draft + patch loop (~7k).** m12 wrote `T:Ka's al-Furaq` and
   `Z2|Z2|…` with an 80-segment Ins group against 82 Vocal bars. m13/m15/m17
   were three patches;
   m14/m16/m18 were three parse failures; m19 rewrote.
5. **Tool puzzles (~4k).** `plan set ins_entries` vs `arrangement.ins_entries`
   (m21–m26), `check --bars` usage error (m46), wrong metric name (m50).
6. **Packager failure (~3.9k).** m58: “Maximum steps… Permission denied: shell.”
   The composer redid the packaging itself.

### 2.4 The arithmetic that matters

- 10× budget = **17,190**.
- 4 drafts at the observed cost = 4 × 4,930 = **19,720** — already over budget
  before any card, release, or packaging.
- Remove the 24k burn and cut to 4 drafts: 91.2 − 24 − 29.6 = **37.6k ≈ 21.9×**.
  Still outside 10×.
- To reach 17.2k with 4 drafts, per-draft cost must fall to **≈3,000 (−39%)**,
  leaving ~5k for everything else.

**The binding constraint is reasoning per draft, not draft granularity.**

---

## 3. Hypothesis vs. agent behavior

### 3.1 Claim-by-claim

| Thesis claim | What the log shows | Verdict |
|---|---|---|
| Write whole, not line-by-line | 10 whole `write`s; no `line`/`patch`/`core` | **Partial** — plus 4 `edit` patches (m13, m15, m17, m30) |
| 1–4 decisive drafts | 10 drafts, 12 cards, 3 releases | **Violated** |
| Code guards, never composes | 0 hand scripts; 0 note selection by code; checker caught every hard/parse error | **Held** |
| The ear is the final judge | no audio; no /10 claim | **Untested**; the agent respected the no-verdict rule |
| Economics follow granularity | whole-draft move gave 54.2× → 53.1× | **Not supported** |
| Think art, not arithmetic | 468 `=16`, 307 `✓`, 597 arithmetic lines (22.5%) vs motif=2, arc=0 | **Violated** |
| Descend fast, see the whole terrain | coherent 6-section form produced | **Held in outcome, took 10 descents** |

### 3.2 Root causes

**A. The premise is half true.** Writing 3,000 characters is easy (~1,750
tokens). *Thinking about the whole 82-bar score inside an 8k completion cap* is
not: three calls hit 8k with zero output. The thesis attacked the wrong
bottleneck.

**B. The causal claim fails.** Granularity changed (line → whole) and cost did
not (54.2 → 53.1). The cost driver is drafts × reasoning per draft.

**C. The card is not neutral.** `scorecard` labels style targets `POLISH`;
`release` makes them hard. The model followed the card, then paid for the
release. This is a tool defect, not disobedience.

**D. The instructions conflict.** “Write the whole file” vs the synthetic
“break it into smaller pieces”; “no `edit`” vs `edit score.abc: allow`; “do not
read scripts” vs a shell `cat` that bypasses the read deny.

**E. The experiment is not one-variable.** Session 16 changed `low` **and** the
clean room, `A4` docs, and the whole-file rule. The bug fixes should have
helped; the total stayed flat, which makes the “variant is the lever” idea
weaker.

---

## 4. Limitations audit

### 4.1 Summary

- **23 findings**: Tooling 6, Self-assessment 5, Instruction 3, Musical quality 3,
  Tokenization/ABC 2, Cross-voice 1, Long-range 1, Arithmetic 1, Other 1.
- **1 inherent** (no ear: the model can only optimize printed numbers),
  **22 mitigable**.
- **Most damaging:** three zero-output 8k burns = 24,000 tokens (26.3%).
- **Most damaging correctness defect:** the card/release split (m39→m40,
  m44→m45), 4 extra drafts.
- Every parse/bar/voice error in the first four drafts was caught by the
  checker, not by the agent (near-misses).

### 4.2 Findings table

| # | Turn/Step | Category | Evidence (≤25 words) | Inherent / Mitigable | Severity |
|---|---|---|---|---|---|
| 1 | m12, m16, m18 | Cross-voice | Vocal 82; Ins 80 segments + 22 invalid `Z2`; `Z2\|Z2\|…` | Mitigable — voice bar-count preflight | Critical |
| 2 | m12, m14 | Tokenization/ABC | `T:Ka's al-Furaq` → “blank T: header” | Mitigable — state the blank-T rule | Major |
| 3 | m13, m15, m17, m30 | Instruction | 4 `edit` patches on `score.abc` against “no piecemeal edit” | Mitigable — remove edit permission | Major |
| 4 | m19, m20 | Tokenization | “line 11: 12 notes < 14 syllables (deficit 2)” | Mitigable — per-line note check | Major |
| 5 | m19, m20 | Long-range | “longest unbroken 81s (sanity max 23s)” | Mitigable — rest/breath preflight | Major |
| 6 | m19, m20 | Musical quality | register 67.7; repeats 11%; durations 3 | Mitigable — card thresholds | Major |
| 7 | m29, m31 | Arithmetic | “duration 7/2 … != meter duration 4”; “unsupported duration 5” | Mitigable — bar-sum preflight | Major |
| 8 | m34, m36, m54 | Musical quality | “add repeated notes by splitting exactly where easy, and add one tie” | **Inherent** — no ear | Major |
| 9 | m39→m40 | Tooling | card “0 blocking”; release “3 hard check(s) failed” | Mitigable — card = release | Critical |
| 10 | m44→m45 | Tooling | card “0 blocking”; release “1 hard”; chorus +4 < 5 | Mitigable — card = release | Critical |
| 11 | m43, m48, m49, m53 | Arithmetic/Tooling | chorus +2→+4→+4→+5; m48 no change | Mitigable — print the median | Major |
| 12 | m10, m27, m34 | Tooling | `finish: length`; output 0; reasoning 8000; 24k total | Mitigable — split the call | Critical |
| 13 | m21–m26, m46, m50 | Tooling | `plan set ins_entries` vs `arrangement…`; `--bars` usage error | Mitigable — CLI schema/help | Minor |
| 14 | m55, m58 | Tooling | “Maximum steps…”; “Permission denied: shell” | Mitigable — permissions/steps | Major |
| 15 | m59, m60, m65 | Musical quality | seed `"Em"_e4…` over Kurd `_e`; seed-check PASS | Mitigable — maqam chord check | Major |
| 16 | m56, m63, m64 | Self-assessment | “Verse: call-and-response” vs report `verse 0/18` | Mitigable — prose from report | Major |
| 17 | m56, m60, m63 | Self-assessment | verse “A4–C5”/“A3–C5” vs report `65-77` | Mitigable — prose from report | Minor |
| 18 | m63, m64 | Self-assessment | “3 declared deviations” vs “placeholder…” | Mitigable — clear flags | Minor |
| 19 | m41 | Self-assessment | “one final full rewrite” then 3 more | Mitigable — reject “final” claims | Minor |
| 20 | m3 | Instruction | `cat … score_cli.py` despite “Do not read the skill's scripts” | Mitigable — deny shell `cat` | Minor |
| 21 | m19–m53 | Instruction | 10 drafts, 61 tool calls vs 4 drafts / 24 steps; 1.0 has no card cap | Mitigable — hard stop | Major |
| 22 | m62 | Self-assessment | core_review “intro 1-12, verse 1 opening 13-16” vs intro 1-9 | Mitigable — derive from plan | Minor |
| 23 | m20, m23, m26 | Other (workaround) | plan `ins_entries` changed to match score; no musical reason | Mitigable — plan audit | Minor |

### 4.3 Detail — Critical and Major

**#1 — First draft: Ins group misaligned with the 82-bar Vocal (Critical, m12/m16/m18).**
m12 wrote `V: Ins\nZ2|Z2|…` (22 `Z2` tokens). The Ins group had 80 segments
against Vocal 82, and `Z2` is not a valid whole-bar rest in this dialect.
m16 and m18 returned `group 1, Ins: expected V: Ins`. The draft was invalid
before any musical judgment. m13 changed `Z2`→`Z`; m17 inserted one `Z`; the
count still failed; only m19 rewrote. *Mitigation:* count bars per voice and
refuse a write when Vocal ≠ Ins.

**#2/#3 — First-draft dialect and patch loop (Major, m12–m18, m30).**
`T:Ka's al-Furaq` was rejected (`blank T: header`). The model had read
`example/score.abc` at m2 but did not follow its blank `T:` or single-`Z`
convention. It then used three `edit` calls (m13/m15/m17) and a fourth at m30,
each followed by a parse failure. *Mitigation:* remove `edit` on `score.abc`;
state “`T:` blank, `Z` one bar, never `Z2`” in the dialect page.

**#4/#5/#6 — Draft 2 failed four independent checks (Major, m19/m20).**
m20: 7 blocking — `notes / syllable 351/361 = 0.97`, line deficits 11/20/25,
`register mean 67.7`, `repeated notes 11%`, `durations 3`, `unbroken 81s`. The
melody was under-written, below the register floor, and had no rests across a
22-bar verse; 81 seconds is vocally impossible. It rewrote at m32 and m36 and
moved all metrics at once. *Mitigation:* preflight notes-per-line vs syllables,
rests per phrase, and register/repeat deltas.

**#7 — Draft 3 bar-length and duration errors (Major, m29/m31).**
`duration 7/2 quarter notes != meter duration 4` on many bars and `unsupported
duration 5`. The model was summing sixteenths by hand (`A1 A1 G4` did not total
16). m30 patched one bar; m31 still failed; m32 rewrote. *Mitigation:* print
`bar N: 14/16` before the write; reject unsupported durations.

**#9/#10 — Card/release severity split (Critical, m39→m40 and m44→m45).**
m39 card: `0 blocking | 4 polish`; m40 release: `3 hard`. m44 card:
`0 blocking | 3 polish` with `chorus +4.0`; m45 release: `1 hard`. Every
failing item was printed as POLISH on the preceding card. The agent trusted the
card and rewrote at m41, m43, m48, m53; it never diagnosed the split.
*Mitigation:* make `scorecard` run the same strict checks as `release`, or
print a `RELEASE-BLOCKING` block. This is the largest correctness defect.

**#11 — Chorus median guessed, one draft no-op (Major, m43–m53).**
Chorus lift: +2 (m42) → +4 (m44) → +4 (m49) → +5 (m54). m48 was a full draft
with no change. At m53: “Need actual medians… compute from the ABC? That would
be writing a metric script — forbidden.” It eventually used `explain-metric`
and the section report. *Mitigation:* print verse/chorus medians and the exact
delta to the floor.

**#12 — Three zero-output turns at the 8k cap (Critical, m10/m27/m34).**
Each: `finish: "length"`, `output: 0`, `reasoning: 8000`; the synthetic reply
said “Break the remaining work into smaller pieces.” The model tried to plan
the whole 82-bar score in one reasoning block. It continued in the next call
and wrote the whole file anyway, so the burn repeated. *Mitigation:* split the
turn (short plan artifact, then write), or cap reasoning and force a write.
This is the largest token bucket.

**#14 — Packager subagent returned nothing (Major, m55/m58).**
m58: “Maximum steps for this agent have been reached” and “Permission denied:
shell.” `packager.md` allows only `*score_cli.py*` and `*verify_package.py*`
shell patterns and `steps: 15`; `ls`/`pwd` are denied. The composer did the
packaging itself (m59–m66) and disclosed it at m67. *Mitigation:* allow
`ls`/`pwd`/`cat` or `shell: *` with a workdir; raise `steps` to 25.

**#15 — Seed harmony clashes with the maqam, yet PASS (Major, m59/m60/m65).**
`score_cli.py seed` generated `"Am"`, `"C"`, `"Em"` chords. The verse bar
`"Em"_e4 c2 _e2 f4 z4` puts E minor over an Eb melody. `seed-check` printed
`PASS seed: 82 bars, V: Drums present, Vocal/Ins/Drums align`; m67 declared
“seed.abc + seed-check: PASS.” `_chord_for_bar` maps the first note letter and
ignores the accidental; `seed-check` checks only bar counts. The model printed
the seed head at m60, saw `"Am"`/`"C"`, and did not inspect the `"Em"` bar.
*Mitigation:* accidental-aware chord generation (Eb → Eb chord) and a
chord/maqam consistency check in `seed-check`.

**#16 — False call-and-response claim (Major, m56/m63/m64).**
m56: “Verse: call-and-response between voice and guitar”; `notes.md` l.7:
“it answers in bar tails”; `CHANGES.txt` repeats it. `report.json`:
`answer_rate = {"intro":"1/1","verse":"0/18","chorus":"1/2","outro":"1/2"}`;
the Ins voice is `Z` in every verse bar. The claim came from the plan's intent,
not the measured score. *Mitigation:* derive prose from `report.json`, or lint
“call-and-response” against `answer_rate`.

**#8 — Threshold-chasing / floor profile (Major, m36/m54).**
m36: “add repeated notes by splitting exactly where easy, and add one tie.”
Final values sit at the floors: repeats 21% (min 20%), ties 1 (floor 1),
chorus +5.0 (min 5), durations 6 (min 5). Report percentiles:
`notes_per_syllable 4.1`, `register_mean 2.9`, `repeated_share 0.0`,
`distinct_phrase_endings 0.0`. The style asks for “melismatic, belting,
powerful operatic”; the score is at the 4th percentile for melisma and the 3rd
for register. The notes admit the target: “land the register mean at 70.8
(band 69-79)”, “above the 20% floor.” *Mitigation:* part inherent; target the
corpus median (1.28, 73.5, repeats ≥25%) and add audio listening. Only the
second removes the cause.

**#21 — Draft and step inflation (Major, m19–m53).**
10 whole `write`s, 12 `scorecard` runs, 3 `release`s, 61 tool calls. The
composer prompt says “At most four drafts”; the user's goal says ≤24 steps.
No hard stop enforced either. The 4-card rule existed only in 0.9 and was
removed in 1.0, so 12 cards is a cost, not a violated 1.0 limit. *Mitigation:*
hard stop at 4 drafts / 24 steps, with a report instead of another rewrite.

### 4.4 Near-misses

- **m14/m16/m18:** the card caught the first draft's `T:` and voice-count
  errors; the agent's three patches did not.
- **m20:** the card caught 7 blocking, including the vocally impossible 81 s
  unbroken run.
- **m31:** the card caught the `7/2` and unsupported-duration errors.
- **m40/m45:** `release` caught what the card had labelled POLISH; without it
  the score would have shipped with hard failures.
- **m65:** `verify_package` passed, but it does not inspect chords; the seed's
  `"Em"` over `_e` is an **uncaught** near-miss in the opposite direction.

### 4.5 Patterns

| Pattern | Occurrences | Turns |
|---|---:|---|
| Patch-then-rewrite | 4 | m13/15/17/30 → m14/16/18/31 |
| Card/release split | 2 | m39→m40, m44→m45 |
| 8k zero-output burn | 3 | m10, m27, m34 |
| Threshold-chasing | 6 | m20, m33, m36, m38, m43–m53 |
| Tool-schema detour | 3 | m21–m26, m46, m50–m52 |
| Prose not from report | 5 | m56, m60, m62, m63, m64 |
| No-op draft | 1 | m48 (chorus +4 before and after) |

### 4.6 Skill gaps

1. **Card vs release severity.** The skill says “BLOCKING — hard failures” and
   “when no blocking, release once”; it never says POLISH can be hard in
   release. Contradicted by m39/m40 and m44/m45.
2. **No arithmetic preflight.** “Parse error → fix bar sums first” has no
   bar-sum, voice-count, or line-note tool. The agent patched and rewrote.
3. **No dialect rule.** The example shows blank `T:` and single `Z`; the skill
   does not state it. m12/m14 and m12/m16.
4. **No hard stop.** “At most four drafts” is unenforced; 10 happened.
5. **No deviation-clearing step.** Release passes with
   “placeholder…unverifiable”; the agent claimed 3 declared deviations.
6. **Packager contradiction.** The skill says the subagent builds the files;
   its permissions deny `ls`/`pwd` and `steps: 15`.
7. **No maqam/chord check.** `seed-check` checks bar counts only;
   `_chord_for_bar` ignores accidentals.
8. **Style targets below the corpus.** The plan's melisma/register targets let
   a “melismatic/belting” score pass at the 4th/3rd percentile.
9. **`--sections` convention.** Repeated labels are undocumented; m6 guessed
   `chorus2` and failed.
10. **`plan set` nested path.** Top-level writes are accepted silently; m23
    wrote `ins_entries`, m26 needed `arrangement.ins_entries`.

### 4.7 Ranked recommendations

1. **Preflight all deterministic facts before the write** — per-bar sum,
   per-voice bar count, notes-per-line vs syllables, rests/unbroken,
   unsupported durations, verse/chorus medians. Eliminates or prevents
   #1, #2, #4, #5, #7, #11, part of #12. (~6 findings)
2. **Derive all prose from `report.json` and lint claims** — tessitura, answer
   rate, deviations, core bar ranges. Eliminates #16, #17, #18, #22, part of
   #15. (~4)
3. **Make `scorecard` run the same strict checks as `release`** — or print a
   `RELEASE-BLOCKING` block. Eliminates #9, #10 and the extra drafts.
   (~2 critical, ~20k tokens)
4. **Enforce the declared bounds** — hard stop at 4 drafts / 24 steps; if a
   card cap is wanted, add it to 1.0 (it exists only in 0.9); remove `edit`
   on `score.abc`; deny shell `cat` on scripts.
   Eliminates #3, #20, #21. (~3)
5. **Fix the packager and the seed harmony** — allow `ls`/`pwd`, raise steps,
   make `_chord_for_bar` accidental-aware, add a chord/maqam check.
   Eliminates #14 and #15. (~2)

---

## 5. Measurement caveats

- **Ratio basis.** `analysis/measure_session.py` uses `cl100k_base` on
  `score.abc`. ABC tokenizes poorly (1,719 tokens for 2,512 bytes), so the
  denominator is generous; a char-based comparison would look worse, not better.
- **Subagent tokens excluded.** The export's `info.tokens` covers the composer
  session only. The failed `packager` subagent (`ses_de9af531…`) is outside the
  91,243, so the real ratio is a lower bound.
- **`checker runs 0` is a false pass.** The script counts `checker.py`, not
  `scorecard.py`; the session ran 12 cards. It also misses the 4 `edit` patches.
- **No audio.** Per `MY_MAIN_GOALS` §1.1 and the session brief, quality is
  suspended; the 0-blocking result is structural, not a 9/10 verdict.

---

## 6. Evidence index

| Claim | Source |
|---|---|
| Totals: 91,243 = 24,314 + 66,929 | `opencode_session_16.json` `info.tokens` |
| 53.1× / 1,719 tokens | `measure_session.py` |
| 3 × `finish:"length"`, output 0 | m10, m27, m34 |
| 10 writes, 4 edits | m12, m13, m15, m17, m19, m29, m30, m32, m36, m38, m41, m43, m48, m53 |
| 12 cards, 3 releases | m14…m54 |
| Card 0 blocking → release 3 hard | m39, m40 |
| Card 0 blocking → release 1 hard | m44, m45 |
| First draft: Ins 80 segments + 22 `Z2` vs Vocal 82 | m12; segments from `write` input |
| 81 s unbroken | m20 |
| 7/2 + unsupported duration | m31 |
| Chorus +2→+4→+4→+5 | m42, m44, m49, m54 |
| Percentiles 4.1 / 2.9 / 0.0 / 0.0 | `report.json` `measured.percentiles` |
| Seed `"Em"` over `_e` | `seed.abc` verse 1; m59/m60 |
| `seed-check` PASS | m59, m65 |
| `answer_rate.verse = 0/18` | `report.json` |
| Prose claims | m56, `notes.md`, `seed_sheet.md`, `CHANGES.txt`, `core_review.md` |
| Packager failure | m58 |
| 61 tool calls | session `content[].type == "tool"` |
| Archive integrity | `sha256sum score.abc report.json`; `state.json.report_sha` |
| Reproduce | `python3 analysis/measure_session.py analysis/eval/inbox/deepseek_session_16/opencode_session_16.json --score <unzipped>/score.abc --max-ratio 10 --max-message 8000` |
