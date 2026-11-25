# خطة الإصلاح الجذري — 0.7.0

**التاريخ:** 2026-11-25
**الحالة:** مسودة للمراجعة. لا كود معدّل. لا تنفيذ قبل الموافقة.
**النطاق:** `02_maqam-score/` (المصدر)، `dist/`، حزمة الجلسة 10، وharness
التشغيل.
**الأساس:** تقرير الهدر `2026-11-25-session-09-waste.md` وتقرير الجلسة
`2026-11-25-deepseek-session-09.md`.

---

## 0. لماذا هذه الخطة ليست ترقيعًا

الترقيع يقول: «أضف تحذيرًا»، «حدّد الـchecker بـ4»، «قلّل التوكنز»، «اكتب
في `task.md` كن حذرًا». هذه الخطة لا تفعل ذلك. هي تغيّر **الطبقات التي
تنتج السلوك**:

| الطبقة | ما كان | ما يصبح |
|---|---|---|
| العقد | ترتيب مزدوج: plan قبل core، وcore مستخرج من score | ترتيب واحد: core أول ملف تكوين |
| القبول | checker واحد يخلط العقد بالذوق؛ WARN يُتجاهل | ثلاث طبقات: عقد، craft موضوعي، ذوق (ناقد) |
| الأدوات | مقاييس عامة؛ الملحّن يكتب سكربتات ليرى | كل سؤال له أداة؛ كل فشل عام له خريطة بارات |
| الحالة | STATE متأخر؛ compaction يمحو السياق | `state.json` من البداية؛ يُفحص |
| الناقد | لا يوجد؛ الخبير البشري هو الناقد | ناقد على الـcore قبل التوسع، بثماني نقاط |
| الميزانية | رقم غير مرئي؛ حلقات بلا حد | ميزانية بالمراحل؛ المقام B |
| الـharness | الوكيل يصلح التثبيت بنفسه | preflight يمنع البدء قبل PASS |

**القاعدة:** إذا احتاج الوكيل معلومة، يجدها في أداة. وإذا احتاج قرارًا
موسيقيًا، يجده في الناقد. وإذا احتاج حالة، يجدها في `state.json`. لا نضيف
قاعدة لكل فشل جديد.

---

## 1. التشخيص في ستة أرقام

| الحقيقة | 07 | 08 | 09 |
|---|---:|---:|---:|
| أول نداء `skill` فشل | نعم | نعم | نعم |
| أكبر كتلة تصميم قبل core | 32,000 | 31,965 | 28,201 |
| كتابات كاملة للسكور | 2 | 2 | 5 |
| تشغيلات checker | 7 | 7 | 17 |
| سكربتات مخصصة | 19 | 14 | 37 + 20 |
| الأذن | 5.5–6 | 6 | 6 (7–7.5 بشري) |

وفي 09 وحده:

| التصنيف | المولّد | الحصة |
|---|---:|---:|
| هدر ذاتي صافٍ قبل تدخلك | 95,783 | 41.2% |
| إصلاحات أول سكور قابلة للتجنب | 20,548 | 8.8% |
| حلقات بعد تدخلك | 75,806 | 32.6% |
| لازم فقط | 40,196 | 17.3% |
| **الإجمالي** | **232,396** | **100%** |

**الاستنتاج:** المشكلة بنيوية ومتكررة. 0.6.0 غيّر النصوص، لا البنية. أول
سكور أسرع، لكن التصميم الكامل، إعادة الكتابة، السكربتات، والحالة بقيت.

---

## 2. الهندسة المستهدفة

```text
[preflight: opencode.json يسجل skill, cwd=session, one model, clean room]
        │
        ▼
syllabify.py  →  prosody.json / phrases.json
        │
        ▼
core_draft.abc (8–16 bars)          ← أول ملف تكوين
        │
        ├── craft.py --phrases       → phrase_table.json
        └── critic (8 points)        → core_review.md
        │
        ▼  (إصلاح الـcore حتى يرضي الناقد)
plan.json (targets + frame)
        │
        ▼
score.abc (توسيع الـcore، كتابة واحدة)
        │
        ├── checker.py               → report.json
        ├── repair.py                → repair.json (بارات/عبارات)
        └── quality.py               → quality.json (أهداف موضوعية)
        │
        ▼  (edit للبارات المسمّاة فقط؛ ≤4 فحوص؛ توقف بعد PASS)
seed.abc + seed_sheet.md + notes.md + CHANGES.txt
        │
        ├── verify_package.py        → verify.json (حزمة + ترتيب + حالة)
        └── craft.py                 → craft.json
        │
        ▼
final critic + render seed.abc + ear verdict
```

### 2.1 لماذا core أولًا؟

- الـcore هو **القرار الموسيقي** (خلية، إيقاع، راحة، سجل، قوس). كتابة 82
  بارًا قبله تعني أن التصميم الكامل يسبق النقد، ثم نعيد الكتابة.
- الأهداف (register 70، key، tempo) تأتي من `example/plan.json` و
  `prosody.json`، فلا حاجة لـ`plan.json` كامل قبل الـcore.
- `plan.json` الكامل يُكتب بعد الـcore، ويصف التوسيع لا الأصل.
- الـcore أول ملف؛ `verify_package.py` يفحص البادئة والترتيب (mtime/state)،
  لا المحتوى فقط.

### 2.2 لماذا ثلاث طبقات قبول؟

| الطبقة | الأداة | يفشل على | لا يفشل على |
|---|---|---|---|
| العقد | `checker.py` | parse، bars، syllables، maqam، final rest | الذوق، الميلزما، القوس |
| Craft موضوعي | `quality.py` جديد | unbroken، pause، distinct bars، top_duration، tessitura | الذوق، الهوية اللحنية |
| الذوق | `critic` | لا يفشل؛ يوصي | — |

هذا يحل تناقض 09: المهارة قالت «لا تعد الكتابة بسبب WARN»، والمهمة طلبت
qafla/إيقاع/لازمة. الآن:

- **جلسة تحقق:** الطبقة 2 تشخيص.
- **جلسة جودة:** الطبقة 2 قبول؛ الطبقة 3 نصيحة.
- **لا بوابة ذوق:** الطبقة 3 لا تفشل شيئًا.

الأهداف الصلبة في 0.7.0: `unbroken`, `pause hierarchy`,
`distinct_bar_share`, `top_duration`, `tessitura`. أما `repeated` و`leap`
فتبقيان تقريرًا حتى تُعايرا على 08/09؛ لا نصنع بوابة من رقم متناقض.

### 2.3 لماذا أداة لكل سؤال؟

| السؤال | الأداة | المخرج |
|---|---|---|
| هل السكور صالح؟ | `checker.py` | `report.json` |
| أين فشل المقياس العام؟ | `repair.py` | `repair.json` |
| ما إيقاع/راحة/نفس كل سطر؟ | `craft.py --phrases` | `phrase_table.json` |
| هل الأهداف الموضوعية تحققت؟ | `quality.py` | `quality.json` |
| لماذا رفض الـparser؟ | `abc_tools.py doctor` | رسالة بلوك/بار |
| هل الحزمة والترتيب والحالة سليمة؟ | `verify_package.py` | `verify.json` |
| ما الحالة؟ | `state.json` + `STATE.md` | الحالة |

**قاعدة:** أي رقم جديد يُضاف إلى أداة، لا إلى heredoc. أي فشل عام يُترجم إلى
بارات/عبارات في `repair.json`، لا إلى «أعد كتابة السكور».

### 2.4 لماذا ناقد قبل التوسع؟

- الخبير البشري في 09 كتب ثماني نقاط، وبعدها تحسنت الجودة إلى 7–7.5.
- الناقد يلتقط ما لا يلتقطه aggregate: 17/25 خلية، 0.38s، 14.25s، 0
  ميلزما، لا حوار، لا أوستيناتو، A4، 6 قفزات.
- الناقد على 8–16 بارًا يكلّف ~2k؛ وإعادة كتابة 82 بارًا كلّفت 20k + 16k.
- الناقد لا يكتب سكورًا؛ يكتب 5 ملاحظات مربوطة ببارات. الملحّن يصلح.

### 2.5 لماذا حالة من البداية؟

- 09: compaction عند msg62، STATE عند msg111. 125,279 مولّد بعد compaction،
  منها 24,822 في الجولة الأولى.
- `state.json` يحمل: phase، آخر ملف، آخر فحص، pass، hash، next، open issues.
- بعد compaction: أول أداة تقرأ `state.json`؛ لا إعادة تشغيل فحص PASS.

### 2.6 لماذا ميزانية بالمراحل؟

- الوكيل لا يرى عدّاد التوكنز؛ لا نطلب منه الالتزام برقم غير مرئي.
- المحلل يوقف عند حد المرحلة.
- المقام B (score+seed) هو الممكن؛ score-only مستحيل حتى بكتابة مثالية
  (الإخراج المرئي 31,898 = 1.53× الحد).
- المسار الطبيعي يجب أن يقع تحت السقف لأن الحلقات أُزيلت.

---

## 3. حزم العمل

### W0 — حزمة صريحة: `opencode.json` داخل الجلسة

**المخرج:** `opencode.json` داخل حزمة الجلسة + `CERTIFIED.md`.

**محتوى مجلد الجلسة:**

```text
session-10/
├── task.md
├── input/            lyrics.txt, style.md
├── skills/
│   └── abc-score-writer/
│       └── SKILL.md
└── opencode.json
```

`opencode.json` (مثال):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "deepseek/deepseek-flash#high",
  "default_agent": "build",
  "skills": ["./skills"],
  "permissions": [
    { "action": "skill", "resource": "abc-score-writer", "effect": "allow" }
  ],
  "update": "disable",
  "share": "disabled"
}
```

- `skills: ["./skills"]` يسجل المهارة من داخل الحزمة؛ لا symlink عالمي.
- `model` يثبت الموديل المدفوع من البداية؛ لا إضافة لاحقة كما في 09.
- `permissions` تسمح بتحميل المهارة صراحة.
- `update`/`share` يمنعان مفاجآت أثناء الجلسة.

**W0 يفحص:**
1. `opencode.json` موجود وصالح، و`skills` يشير إلى `./skills`.
2. `skills/abc-score-writer/SKILL.md` موجود، والـID `abc-score-writer`.
3. cwd = مجلد الجلسة، والمحتوى فقط `task.md`/`input/`/`skills/`/
   `opencode.json`؛ لا `README`/`BRIEF`/`checklist`.
4. الموديل/variant مثبتان كما في `opencode.json`.
5. hashes المهارة والـzip.
6. اختبار دخان: `opencode --auto` في مجلد الجلسة، أول `skill` call ينجح.

**لا تبدأ الجلسة المقاسة قبل PASS.** إذا فشل: عيب إعداد، لا مهارة.

### W1 — إعادة كتابة العقد

**المخرج:** `task.md` صفحة واحدة + `SKILL.md` §3/§3.5/§3.3 + `CHANGELOG`.

**التغييرات:**
- `task.md`: core-first صراحة؛ `quality_run: true`؛ `quality_targets.json`؛
  معايير قبول قابلة للفحص؛ لا تكرار لسياسة checker.
- `SKILL.md §3`: الترتيب الجديد `syllabify → core → critic → plan → score
  → seed → sheet/notes`.
- `SKILL.md §3.5`: سياسة WARN المصححة:
  «In a validity run, WARN is diagnostic. In a quality run, the declared
  Layer-2 targets are acceptance. Taste stays with the critic.»
- Tool map (§2.3) في مكان واحد.
- حذف تناقض README/B حول plan/core.
- `grep` tests: لا «74» كافتراضي، لا «only verifier»، لا «do not rewrite for
  WARN» بدون شرط.

### W2 — الأدوات

**المخرج:** `craft.py --phrases`, `repair.py`, `quality.py`,
`abc_tools.py doctor`, `schemas/report.schema.json`, مثال 2-voice 4-bar,
`verify_package.py` محدّث.

**التفاصيل:**
- `craft.py --phrases`: لكل سطر — line, section, bars, syllables, notes,
  start_beat, rhythm_cell, rest_before/after, unbroken, register_mean,
  repeated, leaps, end_degree.
- `repair.py`: يحوّل كل فشل عام إلى بارات/عبارات. لا يغيّر `checker.py`.
- `quality.py`: يقرأ `quality_targets.json` + `craft.json` + `report.json`;
  يفشل على الأهداف الموضوعية فقط.
- `abc_tools.py doctor`: يشرح أخطاء البلوك/البار.
- `verify_package.py`: يفحص core prefix + order + state freshness + package.
- `example/score.abc`: صوتان، 4 بارات، بلوكات متساوية.

**الاختبار:** شغّل الأدوات على 08 و09 (الأول والنهائي). يجب أن:
- يسمّي `repair.py` بارات `register 66.24` و`simultaneity 270`.
- يلتقط `craft --phrases` 17/25 خلية و0.38s و14.25s في 09 الأول.
- يفشل `quality.py` 08 (distinct/top_duration/tessitura/pause)، ويفشل 09
  الأول (distinct/top_duration/unbroken/pause). 09 النهائي يمرّر 4/5 ويفشل
  `pause hierarchy` (48% تكرار > 40%) — هذه هي الفجوة المعروفة 7–7.5. اختبار
  إيجابي بأهداف متساهلة يمرّر، لإثبات مسار PASS.
- يشرح `doctor` أخطاء t1/t4/n2.

### W3 — الحالة والميزانية

**المخرج:** `state.json` template، `STATE.md`، `BUDGET.md`،
`verify_package` state check.

**التفاصيل:**
- state من أول أداة، تحديث بعد كل ملف/فحص.
- `BUDGET.md`: سقوف المراحل (core 8k، critic 6k، score 12k، checker/repair
  12k، seed/docs 10k، final 4k).
- بعد compaction: اقرأ `state.json` أولًا؛ لا فحص مكرر.

### W4 — الناقد

**المخرج:** `critic.md` prompt + `core_review.md` template + اختبار.

**التفاصيل:**
- 8 نقاط: خلايا الإيقاع، بدايات الأشطر، تدرّج الراحات، الميلزما، الحوار،
  الأوستيناتو، القوس، الحركة اللحنية.
- 5 ملاحظات كحد أقصى، كل واحدة: «البار X: المشكلة → الإصلاح».
- لا سكور بديل، لا أرقام aggregate.
- اختبار على core 09 الأول: هل يلتقط 17/25، 0.38s، 14.25s؟
- إن فشل: ناقد أقوى. لا نغيّر الملحّن والناقد معًا.

### W5 — التحقق

**المخرج:** dry run + session 10.

**التفاصيل:**
- Dry run بلا موديل: 08/09 عبر الأدوات.
- `selftest.sh` يمر.
- `preflight.sh` يمر على بيئة نظيفة.
- session 10 وفق البروتوكول (§4).
- قياس A–I + الأذن من رندر Suno.

---

## 3.6 W0/W5: شهادة إصدار، لا سكربت لكل جلسة

فهمت اعتراضك: لا `bash automate-script.sh`، ولا `go.sh`. تبقى طريقة البدء
كما هي:

```bash
cd /path/to/session
opencode --auto
```

ثم الـprompt. لا سكربت تشغيل.

### أين ذهب W0/W5؟

**W0/W5 ليستا خطوة لكل جلسة. هما شهادة إصدار تُنفذ مرة واحدة عند تجهيز
الـVM/الحزمة:**

| البوابة | متى | ماذا | المخرج |
|---|---|---|---|
| W0 | مرة عند تجهيز الحزمة | `opencode.json` + skill + model + cwd + اختبار skill قصير | `CERTIFIED.md` + `preflight.json` |
| W5 | مرة عند بناء الإصدار | تشغيل الأدوات على 08/09 ومقارنة القيم | `validation.json` |

بعد الشهادة، كل جلسة تبدأ كالمعتاد. لا تعيد W0/W5 إلا إذا:
- غيّرت الـVM/الحزمة/الإصدار،
- أو تغيّر مسار تثبيت المهارة،
- أو أردت التحقق من إصدار جديد.

### بدء الجلسة (كما كانت)

```bash
cd /path/to/session
opencode --auto
```

**Prompt:**

```text
Read task.md and follow it exactly.
Load the abc-score-writer skill with the skill tool first.
If it fails, stop immediately and write HARNESS_FAIL.md.
Do not read SKILL.md manually.
Work autonomously; do not ask questions. Finish all artifacts.
```

- لا `go.sh`.
- لا `tmux` إجباري (استخدمه إن أردت حماية من انقطاع SSH).
- لا `timeout` إجباري؛ توقف الجلسة كما اعتدت.
- لا `summarize.py` إجباري؛ التصدير يكفي، والتحليل بعدي.

### ماذا لو فشل `skill` في الجلسة؟

- الـprompt يقول: توقف واكتب `HARNESS_FAIL.md`.
- إن استمر الوكيل، الجلسة غير صالحة؛ ترى ذلك في التصدير.
- لا سكربت يمنعها، لكن الفشل يحدث في أول دقيقة، فالتكلفة منخفضة.
- الحل الجذري: تثبيت صحيح + شهادة W0. ليس سكربت لكل جلسة.

### الاختبار الصغير في W0

- نعم، فيه استدعاء API قصير: جلسة `opencode --auto` (أو `opencode run`)
  تطلب تحميل المهارة وطباعة `SKILL_OK`/`SKILL_FAIL`.
- هذا جزء من الشهادة، لا من الجلسة المقاسة.
- إن أردت، اجعله أول رسالة في جلسة اختبار عادية؛ لا سكربت.

### الأدوات الجديدة

- `craft.py --phrases`، `repair.py`، `quality.py`، `doctor` يستخدمها
  **الوكيل داخل الجلسة**، بأوامر عادية.
- لا سكربت خارجي يلفّ الجلسة.
- W5 يثبت أنها تعمل قبل الإصدار، ثم تصبح جزءًا من `skills/` كأي أداة.


---

## 4. بروتوكول الجلسة 10

| المرحلة | المخرج | الحد |
|---|---|---:|
| 0. شهادة مسبقة | skill/cwd/model | مرة عند التجهيز |
| 1. syl + core | `core_draft.abc` | 8k |
| 2. critic + fix | `core_review.md` | 6k |
| 3. plan + score | `plan.json`, `score.abc` | 12k |
| 4. checker + repair | `report.json`, `repair.json` | 12k |
| 5. seed/docs/verify | `seed.abc`, `seed_sheet.md`, `notes.md` | 10k |
| 6. final critic | ملاحظات | 4k |

**قواعد توقف:**
- أول `skill` فشل أو cwd ملوث → غير صالح.
- لا core أولًا → توقف.
- تجاوز سقف مرحلة → توقف.
- كتابة كاملة ثانية للسكور → توقف.
- فحص بعد PASS → توقف.
- هدف Layer-2 لم يُصلح → لا تعلن النجاح.
- الأذن <6 → فشل الجودة.

---

## 5. معايير القبول A–I

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

**نجاح:** A صالح، B–F ناجحة، الأذن ≥6. **الهدف 9 مرحلة تالية.**
**فشل:** A غير صالح، أو F >B، أو الأذن <6. القرار منهج/موديل، لا بوابة أخرى.

---

## 6. ما لا نفعله

- لا بوابة ذوق جديدة.
- لا تعديل `checker.py`/`calibration.json` لتسهيل النجاح.
- لا استرجاع/exemplar/phrase bank.
- لا task list.
- لا رقع نصية («كن حذرًا»، «لا تنسَ»).
- لا تبديل موديل في المنتصف.
- لا قراءة `SKILL.md` يدويًا بعد فشل `skill`.
- لا إعادة كتابة كاملة كإصلاح.
- لا heredoc/parser/stats.
- لا إعلان جودة من الأرقام؛ الأذن مطلوبة.

---

## 7. القرارات المطلوبة

| # | القرار | التوصية | البديل |
|---|---|---|---|
| 1 | مقام الـ10× | **B = score+seed** | score-only (مستحيل كتابةً) |
| 2 | الناقد | **نفس الموديل + prompt ناقد** أولًا | موديل أقوى للناقد |
| 3 | Layer-2 الصلبة | **unbroken، pause، distinct، top_duration، tessitura** | إضافة repeated/leap بعد المعايرة |
| 4 | موديل 10 | **`deepseek-flash/high` المدفوع** | المجاني (مقارنة 08) |
| 5 | التنفيذ | **VM نظيفة** | هذا المستودع |
| 6 | الـIR | **مؤجل إلى 0.8.0** | الآن (renderer + contract) |

---

## 8. خيار مؤجل: طبقة وسيطة (Score IR)

إذا بقيت إعادة الكتابة والسكربتات بعد 0.7.0، فالسبب الأعمق أن النموذج يكتب
ABC حرًا ثم يقيسه بمقاييس عامة. الحل الجذري التالي:

```text
phrases.json (cells, rhythms, rests, register, cadence)
  → render.py
  → score.abc / seed.abc
```

- الملحّن يكتب قرارات موسيقية في JSON مضغوط، لا 82 بارًا ABC.
- `render.py` يضمن الصياغة والبارات والتايات.
- `repair/quality` يعملان على الـIR؛ التعديل خلية/سطر، لا `sed`.
- التكلفة: renderer + contract جديد + اختبارات؛ قد يقيّد الزخارف.
- **لا ننتقل إليه الآن.** نضيف `phrase_table`/`repair`/`quality` أولًا.
  إذا بقيت الحلقات، فهو الخيار التالي، لا رقعة أخرى.

---

## 9. لماذا قد تفشل هذه الخطة، وماذا نفعل؟

| الخطر | الإشارة | القرار |
|---|---|---|
| الوكيل يتجاوز الترتيب | core ليس أول ملف | المحلل يوقف؛ W0/W1 يعيدان التصميم |
| `quality.py` يصبح بوابة ذوق | أهداف غير موضوعية | نبقيه على 5 أهداف؛ الذوق للناقد |
| الناقد ضعيف | لا يلتقط 8 نقاط على core 09 | موديل أقوى للناقد |
| الميزانية تتجاوز | مرحلة > سقفها | المحلل يوقف؛ بيانات المرحلة |
| الجودة <8 | الأذن | موديل/منهج، لا بوابة |
| الحلقات تعود | scripts/rewrites | الـIR هو الخيار الجذري |

---

## 10. تعريف الانتهاء

- W0–W5 منفذة ومختبرة.
- `selftest.sh` و`preflight.sh` يمران.
- اختبارات الأدوات على 08/09 تمر.
- جلسة 10 تعطي A–I مع أرقام.
- الأذن من رندر Suno، لا من `craft.json`.
- لا نعتبر 6/10 نجاحًا؛ هي حد عدم التراجع. الهدف 9.

---

## 11. حالة التنفيذ (2026-11-25)

- 0.7.0 منفذ في `02_maqam-score/`.
- `dist/abc-score-writer-0.7.0.zip`:
  `65a953fa5cb5e684b2478b953591c1a29ba7c08c531a175b782ebe94df8e3c1a`
- `dist/session-10-ready.zip`:
  `80b9302441752e512c9b5a0d811fb04f4aec59b97260a35cf2c961fa0951c53e`
- W0 smoke على الحزمة المستخرجة: **SKILL_OK** (أول نداء `skill` نجح).
- `selftest`: PASS؛ `tests`: 73 OK.
- W5:
  - `craft --phrases`: 09 نهائي 26/26؛ 08 26/26؛ grid 4 سطور → 1 عبارة
    (merged 3) — يثبت كشف العمى القديم.
  - `quality.py`: 08 يفشل في top/distinct/tessitura/pause؛ 09 النهائي يمرّر
    4/5 ويفشل `pause hierarchy` (48% > 40%) — الفجوة المعروفة 7–7.5.
  - `repair.py`: يسمّي بارات؛ overlap fixture bars 1–2.
  - `abc_doctor.py`: يشرح البلوك المختل؛ `verify_package` 09 نهائي PASS.
- الحزمة تحتوي `opencode.json` (skills/model)، `task.md`، `input/`،
  `skills/abc-score-writer/`، `quality_targets.json`، و`PROMPT.txt` خارج
  مجلد الجلسة.

