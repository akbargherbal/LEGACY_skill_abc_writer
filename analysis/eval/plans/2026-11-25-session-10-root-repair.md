# خطة الإصلاح الجذري — 0.7.0 والجلسة 10

**التاريخ:** 2026-11-25
**النطاق:** `02_maqam-score/` (المصدر)، `dist/`، حزمة الجلسة 10، وharness
التشغيل.
**المبدأ:** لا ترقيع. لا نضيف قاعدة لكل فشل جديد. نعيد تصميم الطبقات التي
أنتجت الهدر: العقد، الأدوات، الحالة، والناقد.

**الأساس:** تقرير الهدر `analysis/eval/reports/2026-11-25-session-09-waste.md`
وتقرير الجلسة `analysis/eval/reports/2026-11-25-deepseek-session-09.md`.

---

## 0. ما تقوله البيانات (ملخص)

| الحقيقة | الرقم |
|---|---:|
| مولّد 09 | 232,396 |
| هدر ذاتي صافٍ قبل تدخلك | 95,783 (41.2%) |
| إصلاحات أول سكور قابلة للتجنب | 20,548 (8.8%) |
| حلقات بعد تدخلك | 75,806 (32.6%) |
| لازم فقط | 40,196 (17.3%) |
| أول نداء `skill` فشل | 07/08/09 = 3/3 |
| أكبر كتلة تصميم قبل core | 32k / 32k / 28k |
| كتابات كاملة للسكور | 2 / 2 / 5 |
| تشغيلات checker | 7 / 7 / 17 |
| سكربتات مخصصة | 19 / 14 / 37+20 |
| الأذن | 5.5–6 / 6 / 6 (7–7.5 بشري) |

**الاستنتاج:** التغييرات الأربعة في 0.6.0 (ترتيب، سياسة checker، سلسلة أدوات،
حالة) لم تكسر الأنماط. أول سكور أسرع، لكن التصميم الكامل وإعادة الكتابة
والسكربتات والحالة بقيت. المشكلة في **بنية القبول والأدوات**، لا في جهد
النموذج وحده.

---

## 1. المبادئ العشرة

1. **مصدر حقيقة واحد.** الطريقة والسياسة والأدوات في `SKILL.md`؛ `task.md`
   للجلسة فقط (المدخلات، الخيارات، معايير النجاح). لا تكرار.
2. **ترتيب واحد:** `syllabify → core (8–16) → critic → plan → score → seed
   → sheet/notes`. الـcore أول ملف تكوين، لا استخراج من السكور.
3. **ثلاث طبقات قبول:** عقد (checker)، craft موضوعي (quality)، ذوق (critic).
   لا تخلط طبقة بطبقة.
4. **كل رقم له أداة.** لا heredoc، لا parser خاص، لا stats script.
5. **حالة واحدة:** `state.json` + `STATE.md` من البداية، لا بعد الـcompaction.
6. **ناقد قبل التوسع:** 8–16 بارًا تُراجَع موسيقيًا قبل الـ82.
7. **ميزانية بالمراحل، ومقام واحد واضح:** B = score+seed (قرار مطلوب).
8. **موديل واحد في الجلسة.** لا تبديل في المنتصف.
9. **لا بوابات ذوق، ولا تخفيض `calibration.json`، ولا استرجاع/exemplar، ولا
   task list.**
10. **الأذن هي الحكم.** الأرقام تشخيص، ولا تُعلن 9/10 بدون رندر وسماع.

---

## 2. القرارات المعمارية

### 2.1 الترتيب — الـcore أولًا

**المسار الواحد:**

```text
syllabify.py
  → core_draft.abc (8–16 بارًا)
  → core_review.md (ناقد)
  → إصلاح الـcore
  → plan.json (الأهداف + الإطار من prosody)
  → score.abc (توسيع الـcore، كتابة واحدة)
  → seed.abc
  → seed_sheet.md / notes.md
  → checker / repair / quality / verify / craft
```

**التغييرات:**

- `task.md` يقول صراحة: «أول ملف تكوين هو `core_draft.abc`. لا `plan.json`
  ولا `score.abc` قبلها. لا تصميم 82 بارًا قبل الـcore.»
- `SKILL.md §3` يُعاد ترتيبه: الـcore قبل الـplan الكامل. الأهداف (register
  70، key، tempo) تأتي من `example/plan.json` و`prosody.json`؛ `plan.json`
  الكامل يُكتب بعد الـcore.
- يُحذف تناقض README/B: لا `plan → core` ولا «plan لا يسبق core» في نفس
  الوقت. الترتيب واحد.
- `verify_package.py` يفحص:
  - `core_draft.abc` بادئة حرفية لأول 8–16 بارًا من `score.abc`؛
  - زمن/ترتيب: الـcore أقدم من `score.abc`؛
  - `seed_sheet.md` بعد `score.abc`.
- لا يُقبل «core مستخرج من score» كبديل. الترتيب مقاس، لا محتوى فقط.

### 2.2 طبقات القبول — إزالة تناقض WARN

**الطبقة 1 — العقد (`checker.py`):**
- يبقى كما هو منطقيًا و`calibration.json` بلا تغيير.
- يفشل على parse/bars/syllables/maqam/final rest/… فقط.
- `strict_shape: false` يبقى.

**الطبقة 2 — craft موضوعي (`quality.py` جديد):**
- أداة جديدة، لا تعدل `checker.py`.
- تقرأ `score.abc`، `plan.json`، `craft.json`، و`quality_targets.json`
  (خيارات الجلسة).
- تفشل فقط على أهداف **موضوعية** أعلنتها الجلسة، وليس على الذوق:
  1. `unbroken_seconds_max` ≤ الهدف.
  2. تدرّج الراحات: caesura 0.5–0.75 ث، نهاية البيت 1.0–1.5 ث، نهاية
     المقطع أطول؛ لا أكثر من X راحة متطابقة.
  3. `top_duration_share` ≤ الهدف (مثلًا 0.55–0.60، لا 0.65).
  4. `distinct_bar_share` ≥ الهدف (0.75).
  5. `tessitura_share_ge_c5` ≤ الهدف (0.60).
  6. `repeated_share` و`leap4_share`: **تقرير/معايرة، لا بوابة صلبة** في
     0.7.0. النطاق المقترح يُثبت بعد اختبار 08/09؛ الخبير قال 36% كثير،
     والنهائي 21%، والـcorpus 26–42%. لا نجعل رقمًا متناقضًا بوابة.
- هذه ليست بوابات ذوق؛ هي النقاط القابلة للقياس التي ذكرها الخبير. الأهداف
  الصلبة: unbroken، pause، distinct، top_duration، tessitura. أما repeated
  وleap فتشخيص حتى تُعاير.

**الطبقة 3 — الذوق (`critic`، لا بوابة):**
- `core_review.md` بعد الـcore، قبل الـplan/score.
- 8 نقاط الخبير: خلايا الإيقاع، بدايات الأشطر، تدرّج الراحات، الميلزما،
  الحوار، الأوستيناتو، القوس، الحركة اللحنية.
- مخرج الناقد: **5 ملاحظات كحد أقصى**، كل واحدة مربوطة ببار/عبارة، بلغة
  موسيقية. لا سكور، لا بوابة رقمية.
- الملحّن يصلح الـcore ويكتب في `core_review.md` ماذا غيّر.
- ناقد ثانٍ على السكور النهائي اختياري.

**تعديل نصّي واحد في `SKILL.md §3.5`:**
> «On a style or shape WARN, do not rewrite the score» → «In a validity run,
> a WARN is diagnostic. In a quality run, the declared Layer-2 targets are
> acceptance; fix them. Taste stays with the critic.»

### 2.3 الأداة لكل سؤال — Tool coverage matrix

| السؤال | الأداة | المخرج |
|---|---|---|
| هل السكور صالح؟ | `checker.py` | `report.json` |
| أين فشل المقياس العام؟ | `repair.py` (جديد) | `repair.json` (بارات/عبارات) |
| هل الحزمة متسقة؟ | `verify_package.py` | `verify.json` |
| هل الإيقاع/الراحات/النفس لكل سطر؟ | `craft.py --phrases` (جديد) | `phrase_table.json` |
| هل الأهداف الموضوعية تحققت؟ | `quality.py` (جديد) | `quality.json` |
| لماذا رفض الـparser؟ | `abc_tools.py doctor` (جديد) | رسالة تشرح البلوك/البار |
| ما الحالة؟ | `state.json` + `STATE.md` | الحالة |

**قاعدة:** إذا احتاج الملحّن رقمًا غير موجود، يُوسَّع أحد هذه الملفات، لا
يُكتب heredoc.

**تفاصيل:**

- `craft.py --phrases` يطبع لكل سطر: `line`, `section`, `bar_start/end`,
  `syllables`, `notes`, `start_beat`, `rhythm_cell`, `rest_before_s`,
  `rest_after_s`, `unbroken_s`, `register_mean`, `repeated`, `leaps`,
  `end_degree`. هذا الجدول هو ما كشفه الخبير يدويًا.
- `repair.py` يقرأ `report.json` + `score.abc` + `phrases.json` ويحوّل كل
  فشل عام إلى قائمة بارات/عبارات:
  - `register_mean`: بارات/مقاطع خارج النطاق.
  - `repeated_share`: بارات فيها تكرار زائد.
  - `simultaneity`: أزواج البارات/الأصوات.
  - `distinct_bar_share`: مفاتيح البارات المكررة ومواقعها.
  - `top_duration_share`: البارات التي تهيمن عليها القيمة.
- `abc_tools.py doctor`: يشرح `expected V: Ins` وأمثاله: أي بلوك، أي بار،
  وكم بار في كل صوت. لا يعدل السكور.
- `report.json` schema موثق في `schemas/report.schema.json` + `--help`:
  `tag` (وليس `status`)، `class`, `name`, `detail`, `ok`.
- المثال `example/score.abc` يصبح صوتين، 4 بارات على الأقل، ببلوكات متساوية.

### 2.4 الحالة — `state.json` + `STATE.md`

- يُنشأ `state.json` من القالب **قبل أول ملف**.
- يُحدَّث بعد كل أداة/فحص:
  - `phase`, `last_artifact`, `last_check`, `pass`, `report_sha`,
    `next_action`, `open_issues`, `files`, `generated_estimate`.
- `verify_package.py` يفحص:
  - كل ملف مطلوب له entry؛
  - `report_sha` يطابق `report.json`؛
  - `STATE.md` ليس أقدم من آخر فحص.
- بعد الـcompaction: أول أداة تقرأ `state.json`؛ لا إعادة تشغيل فحص مسجل
  كـPASS.
- لا تعتمد على ملخص الـcompaction كحالة وحيدة.

### 2.5 الناقد — قبل التوسع

**المدخل:**
- `core_draft.abc` (8–16 بارًا).
- أول 4–6 أسطر من `prosody.json` (المقاطع/الأطوال).
- أهداف الجلسة (register 70، qafla، rhythm، chorus).
- 8 نقاط الخبير.

**المخرج:**
- `core_review.md`: 5 أسطر مرقمة كحد أقصى.
- كل سطر: «البار X: المشكلة → الإصلاح المقترح».
- لا أرقام aggregate، لا سكور بديل.

**الاختيار:**
- نفس الموديل مع prompt ناقد صارم أولًا (متغير واحد).
- إن فشل في التقاط 8 النقاط على core اختباري، استخدم ناقدًا أقوى.
- لا تخلط تغيير الملحّن وتغيير الناقد في جلسة واحدة.

### 2.6 الميزانية — B بالمراحل

**المقام (قرار مطلوب):**
- 10× score فقط = 20,820: **مستحيل** حتى بكتابة مثالية (الإخراج المرئي
  31,898 في الطور الأول = 1.53×).
- 10× score+seed = 75,130: ممكن للكتابة (58,974 = 0.78×)، لكن التفكير
  تجاوزه (2.31×).
- **التوصية: B = score+seed.** score-only يبقى تشخيصًا.

**ميزانية المراحل (مقترحة):**

| المرحلة | المخرج | سقف المولّد |
|---|---|---:|
| 0. preflight | skill/cwd/model | 0 (خارج الجلسة) |
| 1. syllabify + core | `core_draft.abc` | 8k |
| 2. critic + fix | `core_review.md` | 6k |
| 3. plan + score | `plan.json`, `score.abc` | 12k |
| 4. checker + repair | `report.json`, `repair.json` | 12k |
| 5. seed/docs/verify | `seed.abc`, docs | 10k |
| 6. final critic | ملاحظات | 4k |
| **الإجمالي** | | **≤52k** (تحت B) |

- المحلل يوقف عند حد المرحلة، لا عند الإجمالي فقط.
- الوكيل لا يرى العدّاد؛ لا نطلب منه «الالتزام بالاقتصاد» كرقم غير مرئي.
- المسار الطبيعي يجب أن يقع تحت السقف لأن الحلقات أُزيلت. إن تجاوز، بيانات
  المرحلة تحدد أين.

---

## 3. حزم العمل

### W0 — Harness preflight (خارج المهارة)

- `preflight.sh`:
  - `~/.config/opencode/skills/abc-score-writer/SKILL.md` موجود وsymlink
    يحل؛
  - `agent/` يحتوي فقط `task.md`/`input/`/`skills/`؛ لا `README`/`BRIEF`/
    `checklist`؛
  - cwd = `agent/`؛
  - الموديل/variant مسجلان؛
  - hashes للمهارة والـzip.
- اختبار دخان: أول `skill` call في جلسة تجريبية ينجح. إن فشل، توقف.
- تحديث `README`/`VM-SETUP` بالخطوات الصحيحة (`@abc-score-writer` أو
  `skill` tool، لا `@path`/`/`).
- لا تبدأ الجلسة المقاسة قبل PASS.

### W1 — إعادة كتابة العقد

- `task.md`: صفحة واحدة. ترتيب core-first. معايير قبول قابلة للفحص. لا
  تكرار لسياسة checker. `quality_run: true` و`quality_targets.json`.
- `SKILL.md`:
  - §3 pipeline بالترتيب الجديد.
  - §3.5 سياسة checker + جملة WARN المصححة.
  - §3.3 core قبل plan/score.
  - Tool map (§2.3).
- حذف تناقض README/B حول plan/core.
- اختبارات grep: لا «74» كافتراضي، لا «only verifier»، لا «do not rewrite
  for WARN» بدون شرط.

### W2 — الأدوات

- `craft.py --phrases` + `phrase_table.json`.
- `repair.py` + `repair.json`.
- `abc_tools.py doctor`.
- `schemas/report.schema.json` + `--help`.
- `example/score.abc` صوتان، 4 بارات.
- `quality.py` + `quality.json`.
- `verify_package.py`: core order + state freshness + phrase table.
- اختبارات على 08 و09 (الأول والنهائي): هل الأداة تلتقط ما التقطه الخبير؟

### W3 — الحالة والميزانية

- `state.json` template + `STATE.md`.
- `verify_package.py` يفحص الحالة.
- `BUDGET.md` بسقوف المراحل.
- إعداد `compaction` للجلسة المقاسة (إن أمكن) أو الاعتماد على `state.json`.

### W4 — الناقد

- `critic.md` prompt + `core_review.md` template.
- 8 نقاط، 5 ملاحظات كحد أقصى.
- اختبار على core من 09 الأول: هل يلتقط 17/25 خلية، 0.38s، 14.25s؟
- اختيار الناقد (نفس الموديل/أقوى) — قرار.

### W5 — التحقق

- Dry run بلا موديل: شغّل الأدوات على 08/09.
- `quality.py` يجب أن:
  - يفشل 08 (rhythm/distinct/end_long/tessitura)；
  - يبين أهداف 09 النهائي؛
  - يمرر/يفشل 09 الأول بما يتفق مع الخبير.
- `repair.py` يجب أن يسمّي بارات `register 66.24` و`simultaneity 270`.
- `abc_tools.py doctor` يجب أن يشرح أخطاء t1/t4/n2.
- جلسة معايرة كاملة (session 10) بعد PASS.

---

## 4. بروتوكول الجلسة 10

1. **Preflight** (W0) — PASS.
2. **Phase 0:** اقرأ `task.md` + `state.json`؛ syllabify مرة واحدة.
3. **Phase 1:** `core_draft.abc` 8–16 بارًا. لا plan/score.
4. **Phase 2:** `craft.py --phrases` + ناقد؛ `core_review.md`؛ إصلاح الـcore.
5. **Phase 3:** `plan.json`؛ `score.abc` كتابة واحدة.
6. **Phase 4:** `checker.py`؛ `repair.py`؛ `edit` للبارات المسمّاة؛ ≤4
   تشغيلات؛ توقف بعد PASS؛ `quality.py`.
7. **Phase 5:** `seed.abc`؛ `seed_sheet.md`/`notes.md`؛ `verify_package.py`؛
   `craft.py`.
8. **Phase 6:** ناقد نهائي؛ رندر `seed.abc`؛ حكم الأذن.

**قواعد توقف:**
- أول `skill` فشل، أو cwd ملوث → الجلسة غير صالحة.
- لا `core` أولًا → توقف.
- تجاوز سقف مرحلة → توقف.
- كتابة كاملة ثانية للسكور → توقف.
- فحص بعد PASS → توقف.
- هدف Layer-2 لم يُصلح → لا تُعلن النجاح.
- الأذن <6 → فشل الجودة.

---

## 5. معايير القبول (A–I)

| البند | المعيار |
|---|---|
| A | صالح: skill أول مرة، cwd نظيف، موديل واحد، تصدير كامل |
| B | core أول ملف؛ لا plan/score قبله؛ أكبر كتلة <10k؛ pre-score <10k |
| C | checker ≤4؛ كتابة واحدة؛ لا فحص بعد PASS |
| D | 0 سكربتات؛ repair/quality/craft/verify مستخدمة |
| E | register 70؛ mean 70–72؛ tessitura ≤0.60 |
| F | مولّد ≤ 10× score+seed (B) |
| G | الأذن ≥6 (الهدف 9)؛ 3/5 craft؛ لازمة جديدة؛ قفلة محمولة |
| H | state حديث؛ بعد compaction <2k |
| I | إحالة الأسباب: plan/model/harness |

**نجاح الخطة:** A صالح، B–F ناجحة، الأذن ≥6. **الهدف 9 مرحلة تالية.**
**فشل:** A غير صالح، أو F >B، أو الأذن <6. القرار منهج/موديل، لا بوابة أخرى.

---

## 6. ما لا نفعله

- لا بوابة ذوق جديدة.
- لا تعديل في `checker.py` أو `calibration.json` لتسهيل النجاح.
- لا استرجاع/exemplar/phrase bank.
- لا task list.
- لا رقع نصية («كن حذرًا»، «لا تنسَ») — البنية تمنع الخطأ.
- لا تبديل موديل في منتصف الجلسة.
- لا قراءة `SKILL.md` يدويًا بعد فشل `skill`.
- لا إعادة كتابة كاملة كإصلاح.
- لا heredoc/parser/stats script.
- لا إعلان جودة من الأرقام؛ الأذن مطلوبة.

---

## 7. قرارات مطلوبة قبل التنفيذ

1. **المقام:** B = score+seed (موصى به) أم score-only؟ البيانات تقول
   score-only مستحيل حتى بكتابة مثالية.
2. **الناقد:** نفس الموديل مع prompt ناقد (متغير واحد) أم موديل أقوى
   للناقد فقط؟
3. **أهداف Layer-2 الصلبة:** unbroken، pause، distinct، top_duration،
   tessitura. هل نضيف/نحذف؟ (repeated/leap يبقيان تقريرًا حتى المعايرة.)
4. **موديل الجلسة 10:** `deepseek-flash/high` المدفوع (استقرار) أم المجاني
   (مقارنة مباشرة بـ08)؟ لا تبديل في المنتصف.
5. **التنفيذ:** الآن على هذا المستودع، أم على VM نظيفة كما في خطة 09؟

---

## 8. تعريف الانتهاء

- W0–W5 منفذة ومختبرة.
- `selftest.sh` يمر، واختبارات الأدوات الجديدة تمر على 08/09.
- `preflight.sh` يمر على بيئة نظيفة.
- جلسة 10 تعطي A–I مع أرقام؛ الأذن من رندر Suno.
- لا نعتبر 6/10 نجاحًا؛ هي حد عدم التراجع. الهدف 9.

---

## 9. خيار مؤجل: طبقة وسيطة (Score IR)

**لماذا نذكره:** إذا بقيت إعادة الكتابة الكاملة والسكربتات بعد 0.7.0، فالسبب
الأعمق أن النموذج يكتب ABC حرًا ثم يقيسه بمقاييس عامة. الحل الجذري التالي
هو طبقة وسيطة:

```text
phrases.json (cells, rhythms, rests, register, cadence)
  → render.py
  → score.abc / seed.abc
```

- الملحّن يكتب **قرارات موسيقية** (خلية، إيقاع سطر، راحة، قفلة) في JSON
  مضغوط، لا 82 بارًا من ABC.
- `render.py` يضمن الصياغة والبارات والتايات؛ لا أخطاء `D5 3` أو `Z10`.
- `repair.py`/`quality.py` يعملان على الـIR، والتعديل الموضعي يصبح تعديل
  خلية/سطر، لا `sed` على السكور.
- التكلفة: بناء renderer + contract جديد + اختبارات؛ قد يقيّد بعض الزخارف.
- **القرار:** لا ننتقل إليه في 0.7.0. نضيف `phrase_table`/`repair`/`quality`
  أولًا ونختبر الفرضية. إذا بقيت الحلقات، فالـIR هو الخيار التالي، لا رقعة
  أخرى.
