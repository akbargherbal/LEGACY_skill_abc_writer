# جلسة 10 — حزمة جاهزة وتنفيذ 0.7.0

**التاريخ:** 2026-11-25
**الحزمة:** `dist/session-10-ready.zip`
**SHA-256:** `80b9302441752e512c9b5a0d811fb04f4aec59b97260a35cf2c961fa0951c53e`
**المهارة:** `abc-score-writer` 0.7.0
**Skill zip:** `dist/abc-score-writer-0.7.0.zip`
**SHA-256:** `65a953fa5cb5e684b2478b953591c1a29ba7c08c531a175b782ebe94df8e3c1a`
**`SKILL.md` SHA-256:** `ebc040eafd3cfd26ffe3042d7a364c3c045c66357117a17f3f3e9f12fc545fdd`
**Model:** `deepseek/deepseek-flash#high`

---

## 1. كيف تبدأ

```bash
unzip session-10-ready.zip
cd session-10
opencode --auto
```

ثم الصق محتوى `PROMPT.txt` (خارج مجلد الجلسة):

```text
Read task.md and follow it exactly.
Load the abc-score-writer skill with the skill tool first.
If it fails, stop immediately and write HARNESS_FAIL.md.
Do not read SKILL.md manually.
Work autonomously; do not ask questions. Finish all artifacts.
```

`opencode.json` داخل الحزمة يسجل المهارة من `./skills` ويثبت الموديل من أول
توكن؛ لا symlink عالمي، ولا `@path`، ولا `/skill`.

---

## 2. ما تغير في 0.7.0

### العقد
- ترتيب واحد: `syllabify → core (8–16) → core_review → plan → score →
  seed → sheet/notes`.
- `core_draft.abc` أول ملف تكوين، لا استخراج من سكور.
- `plan.json` بعد الـcore، لا قبله.
- `core_review.md` 5 أسطر نقدية من `references/critic.md`.

### القبول
- `checker.py` يبقى كما هو (contract 0.4.0؛ `calibration.json` بلا تغيير).
- `quality.py` جديد: قبول موضوعي في جلسة الجودة (unbroken، pause، distinct،
  top_duration، tessitura). لا يحكم الذوق.
- `references/critic.md`: 8 نقاط، 5 ملاحظات، لا بوابة.
- `SKILL.md §3.5` توضح: WARN تشخيصي في جلسة التحقق، وقبول موضوعي في جلسة
  الجودة. أزلنا تناقض «لا تعد الكتابة بسبب WARN» المطلق.

### الأدوات
- `craft.py --phrases`: جدول لكل سطر (bars, syllables, start beat, rhythm
  cell, rest before/after, unbroken, register, repeat, leaps, cadence).
- `repair.py`: يحول الفشل العام إلى بارات/عبارات.
- `abc_doctor.py`: يشرح أخطاء parser (بدون تعديل `abc_tools.py`).
- `quality.py`: الأهداف الموضوعية.
- `verify_package.py`: `--state`، `--review`، `--require-core-first`.
- `templates/state.json` + `STATE.md`.

### لم نغيّر
- `checker.py`، `calibration.json`، `abc_tools.py` (pinned hashes pass).
- لا بوابة ذوق، لا استرجاع، لا task list.

---

## 3. W5 — نتائج التحقق

- `selftest`: **PASS**.
- `python3 -m unittest discover -s tests`: **73 OK**.
- `craft --phrases`:
  - 09 نهائي: 26 سطرًا / 26 عبارة.
  - 08: 26 / 26.
  - grid اصطناعي: 4 سطور → **1 عبارة** (merged 3) — يثبت كشف العمى القديم.
- `quality.py`:
  - 08: FAIL (top 78%، distinct 60%، tessitura 94%، pause).
  - 09 نهائي: 4/5 PASS، FAIL `pause hierarchy` (48% تكرار > 40%) — هذه هي
    فجوة 7–7.5 المعروفة، وليست نجاحًا مخفيًا.
  - Positive control بأهداف متساهلة: PASS.
- `repair.py`: يسمّي بارات register/simultaneity/…؛ overlap fixture bars 1–2.
- `abc_doctor.py`: يشرح البلوك المختل.
- `verify_package.py` على 09 نهائي: PASS 0 fail/0 warn.
- W0 smoke على الحزمة المستخرجة: **SKILL_OK** (أول نداء `skill` نجح).

---

## 4. ملاحظة صادقة

الحزمة لا تعد بـ9/10. 09 النهائي ما زال يفشل هدف تدرّج الراحات (48% > 40%).
جلسة 10 هي الاختبار: إن نجح النموذج في تمرير `quality.py` الخمسة مع أذن
≥6، نكون كسرنا الحلقة. إن بقي عند 7–7.5، فالسقف من الموديل/الطبقة الوسيطة،
لا من العقد.

---

## 5. الملفات

- `dist/session-10-ready.zip` — الحزمة.
- `dist/session-10-ready/` — المجلد قبل الضغط.
- `dist/abc-score-writer-0.7.0.zip` — مهارة 0.7.0.
- `analysis/eval/validation/session-10/` — W5 fixtures والنتائج.
- `analysis/eval/plans/2026-11-25-root-repair-v2.md` — الخطة.
- `analysis/eval/reports/2026-11-25-session-09-waste.md` — سجل الهدر.
