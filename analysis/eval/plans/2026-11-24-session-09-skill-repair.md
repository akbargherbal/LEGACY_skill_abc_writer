# خطة إصلاح المهارة تمهيدًا للجلسة 09 — sandbox على VM

**التاريخ:** 2026-11-24
**النطاق:** `02_maqam-score/` (المصدر)، `dist/`، وحزمة الجلسة 09.
**بيئة التنفيذ:** VM معزولة (sandbox) — **ليس هذا الجهاز**.
**المبدأ:** إعادة كتابة العقد والأدوات، لا ترقيع. مصدر حقيقة واحد. لا بوابات للذوق.

---

## 0.1 القرارات المثبتة (2026-11-24)

| القرار | القيمة |
|---|---|
| معيار 10× | **B: score + seed = 52,460** (10× حرفي، بلا أرضية 60k) |
| إعادة الكتابة الكاملة | 1 في المسار الطبيعي؛ **2 كحد أقصى** (إعادة عامة واحدة) |
| أذرع الجودة | 3: سجل 70، قفلة محمولة، إيقاع متنوع |
| هوية الكورس | **نعم** — افتتاح جديد، لا تسلسل للفيرس |
| سرير الغيتار | **اختياري في `seed.abc` فقط** |
| السجل 74 | **يُحذف كافتراضي**؛ تبقى بوابة sanity `74 ± 5` كما هي |
| الضغط | `STATE.md` + تعطيل auto-compaction للجلسات <40 دقيقة |
| الأدوات | `verify_package.py` + `craft.py`؛ 0 سكربتات |

---

## 0. قواعد غير قابلة للتفاوض

1. **لا تعديل على هذا الجهاز.** هذا الملف خطة فقط. كل تغيير في المصدر والاختبارات
   والبناء يحدث داخل VM، على نسخة نظيفة من المستودع.
2. **لا ترقيع.** الملفات الأربعة الأساسية تُعاد صياغتها ككتلة واحدة:
   `task.md`، أقسام العقد في `SKILL.md`، `references/craft.md`، وسطر مساعدة
   `checker.py`. لا نضيف قاعدة لكل فشل جديد.
3. **مصدر حقيقة واحد.** الطريقة والسياسة والأدوات في `SKILL.md`؛ `task.md`
   للجلسة فقط (المدخلات، الهدف، معايير النجاح). لا تكرار للقواعد بين الملفين.
4. **لا بوابات ذوق جديدة.** `checker.py` و`calibration.json` لا يتغيران
   منطقيًا. `craft` تقرير فقط.
5. **رقم واحد للسجل:** 70 (كما في `example/plan.json`). لا 74 في أي ملف.
6. **نسخة واحدة:** 0.6.0. zip واحد، hash واحد، selftest واحد.

---

## 1. الأسباب الجذرية التي تعالجها الخطة

| السبب | الكلفة في 08 | ما يعالجه |
|---|---:|---|
| ترتيب `task.md`: `seed_sheet`/`plan` قبل `core` | 47,302 (36.1%) | عقد واحد بترتيب واحد |
| مقياس عام ضد «تعديل البار المسمى» | 34,132 (26.0%) | سياسة checker واحدة + إعادة كتابة عامة مسموحة مرة |
| لا أداة لـseed/drums/docs/craft | 12,170 (9.3%) | `verify_package.py` + `craft.py` |
| المهارة لم تُحمَّل + compaction قديم | 13 نداء + 12k | تحقق أول نداء + `STATE.md` |

**الهدف:** أن يصبح المسار الصحيح أسهل من المسار الخاطئ، لا أن نضيف تحذيرات.

---

## 2. هندسة المستندات (إعادة كتابة، لا لصق)

### 2.1 `task.md` — صفحة واحدة

**يحذف:** تكرار قواعد العشر أسطر، سياسة checker، أوامر الأدوات، «لا parser».
**يبقي:** المدخلات (الكلمات، الستايل، D Kurd، 80 BPM)، الهدف (جودة/اقتصاد)،
معايير النجاح، وقواعد التوقف. **يشير** إلى `SKILL.md §3` للطريقة.

المخطط:

```
# Session 09 — task
Load the abc-score-writer skill. Work in this directory.
[lyrics + style block]
Key Dm (D Kurd, _E b2), 80 BPM, 4/4. Section layout: ...
Follow SKILL.md §3 for the pipeline, artifacts and checker policy.
Session choices (only these differ):
- register: follow example/plan.json (70), no override
- quality levers: (see §6)
- economy: generated ≤10× score (analyst records; manual stop)
[acceptance list: 6 bullets, no duplication of the skill]
```

**قاعدة:** إذا احتاج الوكيل معلومة عن الأداة أو الترتيب، يجدها في مكان واحد.

### 2.2 `SKILL.md` — إعادة صياغة أربعة أقسام

1. **§3 Pipeline** — ترتيب واحد:
   `syllabify → plan (targets + bars from prosody) → core (8–16) → score →
   seed → seed_sheet/notes`. لا `seed_sheet` قبل `core`. لا إطار 82 بارًا
   قبل أول ملف.
2. **§3.5 Checker** — سياسة واحدة:
   - تشغيل واحد بعد أول `score.abc`؛
   - كل تشغيل لاحق بعد إصلاح **مسمّى**؛
   - توقف بعد النجاح؛
   - فشل صلب **عام** (مثل `repeated_share`) يسمح بإعادة كتابة واحدة كاملة
     + تشغيل تحقق واحد؛ أي خطأ contract بعدها يُصلح بتعديل مسمّى ويُحسب
     ضمن السقف **4**؛
   - لا إعادة تشغيل بعد النجاح.
3. **§3.4 Tool map** — قائمة واحدة واضحة:
   `syllabify.py`، `checker.py` (score verifier)، `verify_package.py`
   (seed/drums/docs/core)، `craft.py` (تقرير)، `abc_tools.py`
   (`inspect/strip-chords/compare` — للـscore فقط). تحذف جملة
   «the checker is the way to use it» و«the skill's only verifier».
4. **§3.2/§3.3 Register** — 70 فقط. تحذف «mean 74 … for a full song» أو
   تقيدها بجملة واحدة: «70 هو الافتراضي؛ 74 لنموذج نسائي/تينور عالٍ فقط».

**قاعدة:** بعد التحرير، `grep -R "74"` و`grep -R "only verifier"` و
`grep -R "count them.*by eye"` يجب أن تعطي صفرًا أو سطرًا واحدًا مبررًا.

### 2.3 `SKILL.md` §3.3 + `references/craft.md` §10 — إزالة مسار «source repo / by eye»

- استبدال فقرة `SKILL.md` §3.3: «In the source repo … if you only have the
  shipped zip, count them on 4–8 phrases by eye» بـ: «Run `craft.py score.abc
  --seed seed.abc --json craft.json`؛ إن لم يوجد، فهذه علة في الحزمة، لا في
  الوكيل».
- استبدال فقرة `craft.md` §10: «Run `analysis/measure_craft.py` … if you have
  the source repo» بـ: «Run `craft.py …`».
- إبقاء المنهج (cell/period/cadence) كما هو. لا أرقام جديدة.
- إضافة سطر: «`craft` تقرير، ليس بوابة؛ لا تعد كتابة السكور لأجل رقم».

### 2.4 `checker.py --help`

- سطر واحد: «This is the **score** verifier. For seed/drums/docs use
  `verify_package.py`.»
- **لا تغيير في المنطق أو `calibration.json`.**

### 2.5 `CHANGELOG.md`

- 0.6.0: «One contract, one toolchain, one state. Removed the order
  contradiction and the 70/74 split; added verify_package/craft; no gate
  changes.»

---

## 3. الأدوات (تُكتب مرة واحدة، تُوسَّع لا تُعاد)

### 3.1 `scripts/verify_package.py` (جديد)

**الوظيفة:** فحص الحزمة كاملة، لا السكور وحده.

```
python3 verify_package.py \
  --score score.abc --seed seed.abc --plan plan.json \
  --phrases phrases.json --core core_draft.abc \
  --sheet seed_sheet.md --notes notes.md \
  --report report.json --json verify.json
```

**الفحوص (كلها بنيوية، لا ذوق):**
1. parse score (صوتان) + seed (3 أصوات/كوردات/Drums) بآلة حالة بسيطة؛
2. إزالة الكوردات ومقارنة Vocal/Ins بين score وseed (تطابق حرفي)؛
3. Drums: 82 بارًا، fills عند نهايات المقاطع/مجموعات 4 بارات، سكتات 77–82؛
4. `core_draft` = أول 8–16 بارًا من score؛
5. `seed_sheet.md` و`notes.md` = 10 أسطر مرقمة بلا عنوان/فراغ؛
6. `plan.json`: `strict_shape:false`، الأهداف كاملة، `register 70`؛
7. تقرير: PASS/FAIL + قائمة الفروق؛ لا يعدل شيئًا.

**قاعدة:** أي فحص جديد يُضاف هنا، لا في heredoc.

### 3.2 `scripts/craft.py` (منقول من `analysis/measure_craft.py`)

- نفس المنطق والأرقام، لكن **داخل الحزمة**.
- `--json craft.json` ويطبع: rhythm variety، unique bars، end-long، cadence
  ladder، tessitura، duration spread، chorus lift، melisma.
- **تقرير فقط**؛ لا يقرأه `checker.py`؛ لا FAIL.

### 3.3 `abc_tools.py`

- يبقى score parser كما هو (vendored؛ لا تعديل).
- `verify_package.py` يملك parser الـseed (3 أصوات/كوردات/Drums) لأن
  `abc_tools.VOICES = ("Vocal","Ins")` ويرفض `V: Drums`.
- توثيق `inspect/strip-chords/compare` في `SKILL.md` tool map؛ الوكيل
  **يشغّلها** ولا يقرأ المصدر.

### 3.4 `scripts/selftest.sh` + `tests/`

- `selftest.sh`: يشغّل `syllabify` + `checker` + `verify_package` +
  `craft` على `example/`، ويطبع `selftest: PASS`.
- `tests/test_verify_package.py`: مثال ناجح، seed غير متطابق (FAIL)،
  Drums ناقص (FAIL)، 10 أسطر خاطئة (FAIL)، core ليس بادئة (FAIL).
- `tests/test_craft.py`: أرقام 08 المعروفة (0.77، 0.60، 0.04) كاختبار
  انحدار.
- `tests/test_checker.py`/`test_syllabify.py` بلا تغيير.

### 3.5 `STATE.md` — قالب، لا سكربت

`templates/STATE.md`:

```
# STATE
## Done
## Verified
## Decisions
## Next
```

- `task.md` يطلب نسخه إلى مساحة العمل وتحديثه بعد كل ملف/فحص.
- بعد أي compaction: `cat STATE.md task.md` ثم `jq .measured report.json`.
- لا نكتب أداة له؛ الملف نفسه هو الأداة.

---

## 4. الاختبارات والقبول (قبل أي جلسة)

| الاختبار | الأمر | القبول |
|---|---|---|
| Unit | `python3 -m unittest discover -s 02_maqam-score/tests` | كلها PASS |
| Selftest | `bash 02_maqam-score/scripts/selftest.sh` | `selftest: PASS` |
| Checker انحدار | checker على `analysis/eval/runs/...-08/deliverables/score.abc` | PASS 0 hard، 3 WARN، `measured` مطابق |
| Verifier على 08 | `verify_package.py` على مخرجات 08 | يمرر البنية؛ يكشف أي عدم تطابق seed/drums/docs |
| Craft على 08 | `craft.py` | 0.77 / 0.60 / 0.04 / 9-8-6-2-1 |
| Example | verifier + craft على `example/` | PASS |
| Zip | `unzip -l` + `sha256sum` | لا ملفات غريبة؛ hash مسجل |
| Clean room | `find agent -maxdepth 1` | `task.md input skills` فقط |
| Skill load | أول نداء `skill` في OpenCode | ينجح — وإلا توقف |

**قاعدة:** لا تُبنى الحزمة النهائية قبل نجاح كل ما سبق.

---

## 5. بناء الـVM والغرفة النظيفة

### 5.1 تجهيز الـVM

```bash
# على هذا الجهاز: حزمة نقل فقط، بلا تعديل
git bundle create /tmp/skill_abc_writer.bundle --all

# على VM معزولة (snapshot قبل البدء، بلا شبكة بعد النقل)
git clone /tmp/skill_abc_writer.bundle skill_abc_writer
cd skill_abc_writer
python3 --version            # 3.10+
python3 -m unittest discover -s 02_maqam-score/tests
bash 02_maqam-score/scripts/selftest.sh | tail -3
```

### 5.2 بناء الحزمة

```bash
# بناء حزمة جذرها abc-score-writer/ (كما في 0.5.3)
rm -rf /tmp/stage && mkdir -p /tmp/stage/abc-score-writer
rsync -a --exclude '__pycache__' --exclude '*.pyc' \
  02_maqam-score/ /tmp/stage/abc-score-writer/
cd /tmp/stage
zip -r "$OLDPWD/dist/abc-score-writer.zip" abc-score-writer
cd "$OLDPWD"
sha256sum dist/abc-score-writer.zip | tee dist/abc-score-writer.sha256
unzip -l dist/abc-score-writer.zip | head -6
```

- النسخة 0.6.0 في `CHANGELOG.md`.
- لا `analysis/` داخل الـzip (الأدوات الآن في `scripts/`).

### 5.3 غرفة الجلسة 09

```bash
mkdir -p session-09/agent/input
cp analysis/eval/inbox/deepseek_session_09/task.md session-09/agent/
cp analysis/eval/inbox/deepseek_session_09/input/* session-09/agent/input/
unzip dist/abc-score-writer.zip -d session-09/agent/skills/
# يجب أن يصبح: session-09/agent/skills/abc-score-writer/
mkdir -p ~/.config/opencode/skills
ln -sfn "$PWD/session-09/agent/skills/abc-score-writer" \
        ~/.config/opencode/skills/abc-score-writer
readlink -f ~/.config/opencode/skills/abc-score-writer
```

- **قبل الجلسة الحقيقية:** جلسة تجريبية فارغة، أول نداء `skill` يجب أن ينجح.
  إن فشل: أوقف، أصلح الرابط، لا تبدأ.
- ملفات المحلل (`README.md`، `checklist.md`، `notes.md`، التصدير) **خارج**
  `agent/`.
- سجّل: الموديل/الـvariant، offline، hash الـzip.

---

## 6. عقد الجلسة 09 (ما يُكتب في `task.md`)

### 6.1 الترتيب

1. `syllabify.py --sections ...` مرة واحدة.
2. `plan.json`: الأهداف من القالب + البارات/المقاطع من `prosody.json`. **لا
   إطار 82 بارًا قبل `core`**.
3. `core_draft.abc`: 8–16 بارًا = أول السكور. اكتبه قبل تصميم البقية.
4. `score.abc`: extension من الـcore، لا تصميم جديد.
5. `seed.abc`: نفس اللحن + كوردات + Drums.
6. `seed_sheet.md` و`notes.md`: 10 أسطر، **بعد** السكور.

### 6.2 سياسة checker

- تشغيل بعد أول سكور؛ كل تشغيل بعد إصلاح مسمّى؛ توقف بعد النجاح.
- فشل عام واحد يسمح بإعادة كتابة واحدة + تحقق واحد؛ أي خطأ contract بعدها
  يُصلح بتعديل مسمّى ويُحسب ضمن السقف 4.
- لا إعادة تشغيل بعد النجاح.

### 6.3 الأدوات والحالة

- `checker.py --json report.json` للـscore.
- `verify_package.py` للحزمة.
- `craft.py` للتقرير.
- **0 سكربتات.** إن نقص فحص، وسّع `verify_package.py`.
- `STATE.md` بعد كل معلم. بعد compaction: STATE → task → report.

### 6.4 أذرع الجودة (ثلاثة فقط)

1. **السجل:** الفيرس 70–71، الكورس 74–76؛ `tessitura ≥ C5 ≤ 0.60`.
2. **القفلة:** كل نهاية مقطع/سطر تحمل ربعًا أو أطول؛ `end_long 0.25–0.50`؛
   آخر نغمة في القطعة ≥ نصف ثانية مع زخرفة 3–5 نغمات.
3. **الإيقاع:** `rhythm_variety ≥ 0.85`، `distinct_bar_share ≥ 0.75`،
   `top_duration ≤ 0.70`، `repeated 26–35%` بمدد متنوعة (`d3 d1`، لا شطر كل
   شيء إلى `d2 d2`).

**قرار الكورس (مطلوب):** افتتاح جديد، ليس تسلسلًا لافتتاح الفيرس؛ أبقِ
ذيلًا مميزًا.
**اختياري:** سرير غيتار في `seed.abc` تحت الصوت (لا في `score.abc`).

### 6.5 قواعد التوقف

- لا `core_draft.abc` بعد **8 نداءات تأليف** (لا تُحتسب قراءات التوثيق) →
  توقف وسجّل «front-loaded».
- 10× يدوي: المحلل يوقف الجلسة.
- إعادة كتابة كاملة واحدة فقط (للفشل العام)؛ الثانية = توقف.
- بعد pass: توقف.

---

## 7. معيار 10× — **معتمد: B عند 52,460**

| المقام | 10× | المولّد في 08 | النسبة |
|---|---:|---:|---:|
| score فقط | 18,910 | 131,138 | **69.3×** |
| score + seed | 52,460 | 131,138 | **25.0×** |
| الحزمة كاملة | 191,130 | 131,138 | **6.9×** |
| الـoutput المرئي وحده | — | 22,551 | **11.9× score** |

**القاعدة الحالية (score-only) غير قابلة للتحقيق رياضيًا:** الـoutput المرئي
وحده 11.9×. القرار قبل الجلسة:

- **A.** score-only ≤10× — يتطلب كتابة أقل وتفكيرًا أقل؛ صعب لكنه ممكن إذا
  مُنع التصميم المسبق.
- **B.** score+seed، والميزانية = `max(10×, 60k)` = **60k** — واقعي.
- **C.** الحزمة ≤10× — يمرر 08 (6.9×) لكنه يخلط JSON الأدوات بالكتابة.

**التوصية:** B للجلسة 09، مع تسجيل A كتشخيص. **تم اعتماد B عند 52,460.**

---

## 8. التشغيل والقياس

### 8.1 قبل التشغيل

- [ ] zip hash مسجل؛ `selftest: PASS`.
- [ ] أول `skill` call ينجح.
- [ ] الغرفة نظيفة: `task.md` + `input/` + `skills/` فقط.
- [ ] `STATE.md` موجود وفارغ.
- [ ] الموديل/الـvariant مسجل (same as 08).

### 8.2 أثناء التشغيل

- المحلل يراقب: أول `core`، أول `score`، أول checker، عدد التشغيلات،
  عدد السكربتات، الحجم المولّد.
- 10×: إيقاف يدوي عند التجاوز.
- لا تدخل في الشوط إلا عند فشل harness.

### 8.3 بعد التشغيل

- تصدير OpenCode JSON.
- حساب: generated/score، score+seed، cache، wall، tool calls، checker runs،
  full writes، scripts.
- `craft.py` على السكور.
- رندر Suno من `seed.abc` + حكم الأذن (6 كحد أدنى، 9 هدف).
- تقرير: `analysis/eval/reports/2026-11-25-deepseek-session-09.md`.

### 8.4 قرار

- جودة ≥6 واقتصاد ≤10× (المقام المتفق): انتقل إلى رفع الجودة.
- جودة <6: غيّر المنهج أو الموديل؛ لا تخفض العتبة.
- اقتصاد >10×: عقد/أداة؛ لا مزيد من البوابات.

---

## 9. تعريف الإنجاز (Definition of Done)

| المحور | الشرط |
|---|---|
| العقد | `task.md` صفحة واحدة؛ لا 74؛ لا «only verifier»؛ لا «count by eye»؛ لا تناقض ترتيب |
| الأدوات | `verify_package.py` + `craft.py` داخل الحزمة؛ 0 سكربتات في الجلسة |
| الاختبارات | unit + selftest + انحدار 08 + example كلها PASS |
| الحزمة | zip 0.6.0، hash، لا ملفات غريبة |
| الـVM | غرفة نظيفة؛ أول `skill` call ناجح |
| الجلسة | 1 كتابة كاملة في المسار الطبيعي، و2 كحد أقصى (إعادة عامة واحدة)، ≤4 checker، 0 سكربتات، كل المخرجات |
| القياس | تقرير بالأرقام + رندر Suno + حكم أذن |
| الجودة | ≥6 (حد عدم التراجع)، والهدف 9 |

---

## 10. المخاطر

| الخطر | التخفيف |
|---|---|
| إعادة كتابة `SKILL.md` تُدخل تناقضًا جديدًا | خريطة «مصدر حقيقة واحد»؛ grep بعد التحرير؛ مراجعة بشرية |
| الوكيل يكتب سكربتًا رغم الأداة | `task.md` يقول «وسّع verify_package»؛ سجّل السبب إن حدث |
| `verify_package` يصبح بوابة ذوق | فحوصه بنيوية فقط؛ craft تقرير |
| 10× غير واقعي | قرار المقام قبل التشغيل (§7) |
| فشل تحميل المهارة مجددًا | جلسة تجريبية قبل الجلسة الحقيقية |
| compaction يعيد الفوضى | `STATE.md` + تعطيل auto-compaction للجلسات <40 دقيقة |
| إعادة كتابة عامة ثانية | توقف فوري عند الثانية |

---

## 11. الترتيب الزمني المقترح

1. **يوم 1:** تدقيق + إعادة كتابة `task.md` وأقسام `SKILL.md` و`craft.md`
   وسطر `checker --help`. لا كود.
2. **يوم 2:** `verify_package.py` + `craft.py` + الاختبارات.
3. **يوم 3:** بناء الـzip + VM + غرفة نظيفة + جلسة تجريبية (skill load) +
   تشغيل الأداة على مخرجات 08.
4. **يوم 4:** جلسة 09 + القياس + التقرير.

**لا تبدأ الجلسة 09 قبل أن يمر §4 كاملًا.**
