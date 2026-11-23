# analysis/ — معايرة قيود `maqam-score` على 177 سكور

هذا المجلد يحتوي أداة القياس التي تنتج `docs/constraints-calibration.md`.
لا يعدّل شيئًا في المهارة؛ يقرأ فقط سكورات `five_stars` ويعيد إنتاج الأرقام.

## التشغيل

```bash
python3 analysis/calibrate_177.py \
  --corpus ~/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars \
  --out analysis/out
```

المخرجات:

| الملف | المحتوى |
|---|---|
| `out/tracks.jsonl` | صف لكل مقطع: القياسات الخام + حكم كل بوابة |
| `out/summary.json` | التوزيعات، نسب الاجتياز، مقارنة A6، ومجموعة **حدود الانحطاط** (`sanity_gate_set`) |
| `measure_phrasing.py` | shape: أطول غناء متصل، تكرار النغمة، القفلات، الطسيتورا، وفرق verse→chorus — على 177 أو على ملف واحد |
| `verify_0_4_0.py` | بوابة قبول 0.4.0: المثال strict، الـ phrases، السكور القديم، القالب، والـ177 إن وُجد |

**قاعدة 95%:** البوابات الصلبة يجب أن تمرّر ≥95% من الـ 177. المجموعة الأساسية
(9 حدود: 6 للصلاحية + 3 للشكل) تمرّر **175/177 = 98.9%**؛ وإضافة اختيارية
(سجل أعلى + tie) تمرّر 174/177. قياسات الشكل (unbroken، repeated، endings)
تأتي من `analysis/measure_phrasing.py`؛ التفاصيل في
`docs/constraints-calibration.md §3.1` و`references/reference.md §7.5`.

## اختبار التكامل

```bash
python3 analysis/test_checker_corpus.py \
  --corpus ~/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars
```

النتيجة الحالية: **177/177 parse**، و**175/177 (98.9%)** تمرّ البوابات الصلبة
الافتراضية. مع `--require-final-rest` تمرّ 161/177 (91.0%) لأن السكتة الأخيرة
عقد رندر اختياري.

## لماذا محلل خاص؟

`checker.py` يرفض تغيير `M:` داخل الجسم. **121 من 177** سكورًا فيها تغيير meter،
وتسعة أمتار مختلفة تظهر في المجموعة. لذلك لا يستطيع الـ checker قراءة معظم
السكورات التي يُفترض أن يصفها. المحلل هنا يقبل `M:`/`K:` داخل الجسم، ثم يطبّق
نفس تعريفات الـ checker للـ ties، والمدد، والكوردات، والكادنس، والصمت.

للتحقق من التطابق: على الـ 56 ملفًا التي يقبلها `checker.parse`، نتائج البوابات
متطابقة تمامًا (0 فروق).

## القيود

- السكورات ترانزكريبت SheetSage2 لرندرات Suno، ليست تأليفًا بشريًا.
- التسميات `maqam` هي **ما طُلب** في الـ prompt، لا ما قيس (تقرير M1: 0% Hijaz).
- لا كوردات في أي من الـ 177 سكورًا؛ قياس C8 غير ممكن من هذا الداتاست.
- الكلمات من `lyrics.jsonl`، والمدة من `manifest.jsonl`.
