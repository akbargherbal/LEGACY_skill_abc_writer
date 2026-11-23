# Plan — OSTRIS Score Tools (مستودع منفصل)

> **Provenance:** نُقل هذا الملف من `arabmaqamrock/docs/plans/` إلى مستودع المهارة في 2026-11-23.
> المسارات `arabmaqamrock/...` تخص المستودع الخارجي؛ مستودع المهارة هو `skill_abc_writer`.

> **Implementation note (2026-11-23, English):** The separate-repository scope is
> dropped. The tools live in the skill: offline code in
> `02_maqam-score/scripts/ostris/`, contracts in `02_maqam-score/schemas/`, and
> generated evidence in `analysis/out/ostris/`. M0–M5 are implemented and pass
> on the real corpus; M6 implements the deterministic split and the objective
> metrics only. No maqam label or maqam-fit score is produced.
> Progress checklist: `docs/ostris-implementation-checklist.md`.

**Status:** proposal — **M0–M5 implemented; M6 objective half; maqam work deferred**
**Date:** 2026-11-22
**Last updated:** 2026-11-23 — سجل القرارات + تكامل مهارة v0.2.0
**Scope:** مستودع جديد مستقل عن `arabmaqamrock`
**Owner:** Akbar (المستودع الجديد)
**Upstream skill:** `~/Jupyter_Notebooks/OpenCode/skill_abc_writer` (مستودع المهارة الجديد)
**Upstream data:**
- Manifest: `OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json`
- Audio bundle: `OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset.zip`
- Transcripts: `TRANSCRIPTS/YT500` و `TRANSCRIPTS/FADL_SHAKER`
- Labels: `OSTRIS_Arabic_Suno_Finetuning/v3_arabmaqamrock_dataset_manifest.json`

> المسارات أعلاه **نسبية إلى جذر بيانات المشروع**؛ اسم الـ bucket محذوف من هذا المستند.

---

## 0. الهدف في سطر

> تحويل 482 سكورًا/مقطعًا إلى **بريورات + بنك idioms + فحوص + مجموعة تقييم**، تُستهلك عبر CLI صغير،
> بحيث يكتب وكيل المهارة سكورًا **أفضل** بـ **توكنز أقل**، دون المساس بأي بوابة جودة.

**غير الأهداف:**
- ليس chatbot، ولا مولّد موسيقى.
- ليس بديلًا عن `checker.py` في المهارة.
- ليس vector DB فوق 400 سكور كاملة.
- ليس pipeline صوتي كامل.

> **بوابة البدء:** راجع **§13.3**. كل مرحلة لها قرارات محجبة، ولا تبدأ مرحلة
> قبل حسم قراراتها. `ostris audit` (M0) يمكن أن يبدأ الآن؛ لكن لا تُبنى
> priors ولا `plan` ولا `check` قبل حسم قرارات المرحلة.

---

## 1. جرد البيانات (جرد 2026-11-22 — يُعاد التحقق في M0)

> هذه الأرقام من جرد سابق. **M0 audit** يعيد التحقق منها من manifests قبل
> بناء أي بريور أو eval، ويسجّل الفروق إن وُجدت.

| الأصل | المسار | العدد | الحجم | ملاحظات |
|---|---|---:|---:|---|
| Instrumental manifest | `OSTRIS_.../arabic_instrumental_dataset_manifest.json` | **482** | 341 KiB | **460 yt500 + 22 fadhl_shaker، مدمجة بالفعل** |
| Instrumental audio | `OSTRIS_.../arabic_instrumental_dataset.zip` | 482 mp3 | **2.95 GiB** | 36.6 h، 48 kHz |
| YT500 manifest | `TRANSCRIPTS/YT500/_manifest.jsonl` | **495** | 483 KiB | 25 shard، 5 مجموعات مكررة (10 tracks) |
| YT500 transcripts | `TRANSCRIPTS/YT500/YT500/` | 495 tar.gz + 25 shard JSON | ~600 objects | كل tar ~100 KiB |
| FADL transcripts | `TRANSCRIPTS/FADL_SHAKER/` | 15 album JSON/tar + `abc/` | — | يغطي الـ22 |
| Maqam labels (audio) | `OSTRIS_.../v3_arabmaqamrock_dataset_manifest.json` | **438** | — | Ajam 118 · Hijaz 107 · Kurd 101 · Nahawand 112 |

**ملاحظات حاسمة على الأعداد:**
- **482** هو حجم المكتبة الفعلي (460 + 22). الـ**495** هو عدد أغاني YT500 التي جرت ترانكريبتها، وليس حجم المكتبة.
- **460** من الـ495 مستخدمة في المكتبة؛ **35 غير مستخدمة** → مرشحة كـ **held-out** طبيعي (ليست في تدريب اللورا ولا في الـ482).
- **22** من Fadhl Shaker موجودة في manifest الـ482، وترانسكريبتها في `FADL_SHAKER` (15 ألبومًا، كل JSON يضم عدة tracks). الربط بالعنوان/الألبوم.
- **438** تسمية maqam هي audio+caption (ليست ABC)؛ **مستثناة من priors/eval** لأنها من بيانات تدريب v3.

> **M0 finding (2026-11-23, English):** The exact 22-track FADL link is
> `DATASET/fadhl_shaker_instrumental_18_shortlist/shortlist.json` →
> `TRANSCRIPTS/fadhl_shaker_selected_scores` (24 tracks, 23 with ABC) plus the
> reference conditioner ABCs in `DATASET/fadhl_shaker_instrumental_18/abc/`.
> `TRANSCRIPTS/FADL_SHAKER` is a broader 15-album set (140 tracks, 132 with ABC),
> not the 22-track shortlist. One shortlist track (`al_qissa_wama_fiha`) has no
> selected-scores ABC; M0 falls back to its reference conditioner and flags it.

**محتوى tar واحد (مثال `0044_ZLhWlUFmGMA`):**

```
score.abc                 # 2 voices (Vocal + Ins)، chords، % sections
meta.json                 # model, status, duration, abc_sha256
result.json               # warnings, windows, timings
key.lab                   # F#:minor
chord.lab                 # time-stamped chords
structure.lab             # intro/verse/chorus/interlude + times
beat.lab / downbeat.lab   # beats/downbeats
melody_vocal.lab
melody_instrumental.lab
melody_full.lab
transcription.mid
melody.mid / chords.mid
tokens.json / tokens.txt
notation/song_structures.txt, song_keys.txt, song_beats.txt
```

**هذه sidecars تغني عن إعادة اشتقاق كل شيء من ABC.** استخدمها أولًا، ثم استخدم ABC للتحقق.

---

## 2. حقائق حاسمة يجب أن تُبنى عليها الخطة

### 2.1 السكورات للأغاني الأصلية، لا للنسخ الآلية
- `TRANSCRIPTS/YT500/.../meta.json` يقول `source_wav = yt_top_500_music_playlist/audio/...` — أي **الأغنية الأصلية**.
- `arabic_instrumental_dataset` هو **نسخ instrumental** (Suno/OSTRIS) لنفس الأغاني.
- لذلك:
  - للـ priors: استخدم البنية، الكوردات، المقام، الـ `Ins` melody، الـ register — فهي تنتقل.
  - **لا تستخدم** prosody الغناء أو توزيع الـ `Vocal` كقاعدة للمانيفستات instrumental.
  - لا تعتبر الـ ABC وصفًا للـ audio الموجود في الـ zip؛ هما مصدران مختلفان لنفس الأغنية.

### 2.2 لا توجد تسميات maqam في manifest الـ482
- الحقول: `title, artist, duration, caption, lyrics_tags` — لا `maqam`.
- **177 five_stars:** مستثناة من priors/eval (داخل تدريب LoRA v3)، وتُستخدم
  **فقط كمجموعة معايرة قيود** للمهارة (`scripts/calibration.json` و
  `references/numbers.md`). ليست priors ولا eval.
- **438 v3:** مستثناة من priors/eval؛ cross-check فقط إن سُمح.
- الحل: طبقة وسوم تعتمد على:
  1. **قاعدة symbolic**: key + scale-degree + interval + presence of aug-2 / minor-2 / major-3.
  2. **مراجعة يدوية** لعينة طبقية (100–150) من **الـ482** لمعايرة القاعدة وقياس دقتها.
  3. **captions** كإشارة ضعيفة فقط (نادرًا ما تذكر maqam صراحة).
  4. **438 v3** تُستخدم فقط كـ cross-check خارجي إن سُمح؛ لا تدخل priors ولا eval.
- **مهم:** لا تُدرَّب القاعدة على تسميات الـ177 (هي prompt، وتقرير M1 يقول 0%
  Hijaz-shaped). الـ177 تُستخدم لفحص **سلوك** القاعدة فقط، لا لدقة التسمية.
  القرار D3/D4 في §13.
- كل سجل يحمل `maqam`, `maqam_confidence`, `maqam_source`.
- التوقع: ليست كل الأغاني من الأربعة؛ أضف `other/unknown` ولا تُجبر التسمية.

### 2.3 الـ482 = 460 + 22، والـ495 ليست المكتبة
- 22 من Fadhl Shaker **مدمجة** في manifest الـ482؛ transcripts في `TRANSCRIPTS/FADL_SHAKER` (15 ألبومًا).
- 460 yt500 تُربط بـ `(source_rank, video_id)` أو `out_name` (`yt500-0001-fbK2ySlxAW4`).
- **35 transcript غير مستخدمة** من الـ495 → **held-out طبيعي** (ليست في المكتبة ولا في تدريب v3).
- استبعد 5 duplicate groups / 10 tracks من الـ priors والـ eval.

### 2.4 الـ corpus أوسع من الستايل المستهدف
- `arabic_instrumental_dataset` = "Middle Eastern fusion, instrumental" (captions)، وليس بالضرورة `arabmaqamrock, 110 BPM`.
- 177 five_stars كانت أقرب للستايل، لكنها **مستثناة من priors/eval**؛ تُستخدم
  فقط لمعايرة قيود المهارة، لا لبناء priors الـ482. لذلك:
  - استخدم stratified priors: `maqam × mood × form × tempo band`، مع `n` ظاهرًا لكل طبقة.
  - إن كانت الطبقة صغيرة (< 10)، ادمجها أو وسّعها؛ لا تُخرج بريورًا من 3 أمثلة.
  - اقبل أن priors الـ482 قد تكون أوسع/أقل دقة من five_stars؛ وثّق ذلك.

### 2.5 الجودة غير متساوية
- `status: ok / partial / failed` في meta والـ shard index.
- `warnings` في `result.json`.
- `score.abc` قد يكون ناقصًا/مقطوعًا/بلا chords.
- كل سجل يحمل `quality_score` و`exclude_from_priors` عند الحاجة.

### 2.6 قرارات المستخدم (2026-11-22)

| السؤال | القرار |
|---|---|
| حجم المكتبة | **482** (460 + 22 مدمجة). الـ495 عدد مصادر ترانكريبت، و**35** منها held-out. |
| 177 five_stars | **مستثناة من priors/eval** (داخل تدريب LoRA v3)؛ **معايرة قيود فقط**. |
| 438 v3 | **مستثناة** من priors/eval؛ cross-check فقط إن سُمح. |
| maqam labels | قاعدة symbolic + مراجعة يدوية؛ لا اعتماد على 177. |
| Voices | الـchecker الحالي **يفرض `Vocal` + `Ins`**؛ الافتراضي `Vocal + Ins`، مع دعم `Ins` فقط عند إضافة وضع instrumental للمهارة. |
| المدة/`cap` | **المهارة تملكها**. الأداة تستقبل `bars` أو `target_duration_s` ولا تفسّر `cap=8500`. |
| الاقتباس | **مسموح صريحًا وضمنيًا**، بما في ذلك جملة كاملة أو سطر حرفيًا، إذا خدم الغرض. الأداة **تتبّع وتنسب** ولا تمنع. |

**تفصيل Voices:**
- `checker.py` في المهارة يفرض `VOICES = ("Vocal", "Ins")` وتبادلهما؛ `Ins` فقط **لا يمر** حاليًا.
- لذلك الإصدار الأول يكتب `Vocal` (lead melody) + `Ins` (answer/counter)، حتى في instrumental.
- إن أضافت المهارة وضعًا instrumental (voice واحد + chords)، تُضاف `--voices ins` للأداة.
- الأداة لا تفرض الشكل؛ الـ`schema` يحمل `voices`، والـ`check` يمررها للـchecker.

**تفصيل المدة:**
- `cap` في المانيفست هو `semantic_max_tokens` وليس مدة.
- المهارة تحسب المدة/البارات (`duration_cap.py` + `reference.md` + `syllabify.py`).
- الأداة تقبل `bars` أو `target_duration_s` من الخطة، وتستخدمها فقط لتوليد `plan.json`.
- إن غابا: fallback محايد (3.5–4.5 min) مع `warning: duration_assumed`.

**تفصيل الاقتباس:**
- الاقتباس **مسموح** صريحًا وضمنيًا؛ لا بوابة «أصالة» ترفض.
- `similarity` تقرير وصفي: `max_shared_run`, `source_id`, `bar_range`, `confidence`.
- عند استخدام idiom من corpus، يُسجّل في `plan.json` و`report.json` تحت `quotation`.
- الهدف: **التتبّع والنسبة**، لا المنع. هذا يحمي من الاقتباس غير المقصود ويوثّق المقصود.
- ملاحظة قانونية: المشروع غير تجاري؛ إن نُشر المنتج تجاريًا لاحقًا، تُراجع سياسة الاقتباس.

---

## 3. المبدأ المعماري

```
OFFLINE (مرة واحدة، CPU)
  GCS manifests + transcripts
        │
        ▼
  ingest → canonicalize → QC → features → labels
        │
        ├── track_record.jsonl        (سجل لكل track)
        ├── priors/<stratum>.json     (إحصاءات)
        ├── banks/idioms.jsonl        (2–4 bars)
        ├── banks/similarity/         (k-gram index — للتتبّع لا للمنع)
        └── eval/queries.jsonl        (gold set)

ONLINE (عند الطلب، < 1s)
  manifest song
        │
        ▼
  plan  ──► plan.json
  exemplar (اختياري) ──► 2–4 bars
  check ──► report.json
  similarity ──► report.json   (quotation/provenance، ليس بوابة)
        │
        ▼
  الوكيل يكتب/يصلح phrases، لا يرى corpus كاملًا
```

**قاعدة ذهبية:** لا يدخل الـ corpus السياق. يدخل فقط:
`prior card` + `plan` + `2–4 bars` عند الطلب + `report JSON`.

---

## 4. المخرجات (Artifacts)

| Artifact | الصيغة | يُستهلك بواسطة | حجم تقريبي |
|---|---|---|---:|
| `records.jsonl` | JSONL | build/priors | ~2–5 MB |
| `priors/<maqam>_<form>.json` | JSON | `plan` | ~50–200 KB |
| `idioms.jsonl` | JSONL | `exemplar` | ~1–3 MB |
| `similarity/index.npz` | NumPy | `similarity` | ~5–20 MB |
| `eval/queries.jsonl` | JSONL | `eval` | ~100 KB |
| `manifest_links.csv` | CSV | audit | ~50 KB |

كل شيء قابل للتوليد من المصادر؛ لا نُدخل assets ثقيلة في git.

---

## 5. عقود البيانات

### 5.1 `track_record`

```json
{
  "id": "yt500-0044-ZLhWlUFmGMA",
  "source": "yt500",
  "source_rank": 44,
  "video_id": "ZLhWlUFmGMA",
  "title": "Saharna Ya Leil",
  "artist": "Elissa",
  "duration_s": 258.5,
  "audio_uri": "yt500_instrumental/tracks/.../audio.mp3",
  "abc_uri": "TRANSCRIPTS/YT500/YT500/shard-01/0044_....tar.gz",
  "key": "F#:minor",
  "maqam": "Hijaz",
  "maqam_confidence": 0.82,
  "maqam_source": "symbolic_classifier+manual",
  "mood_tags": ["yearning", "melancholic"],
  "mood_source": "caption_lexicon",
  "meter": "4/4",
  "tempo": 130,
  "bars": 84,
  "sections": [{"name":"intro","bars":8,"role":"establish"}, ...],
  "voices": ["Vocal","Ins"],
  "range": {"vocal":[60,72],"ins":[55,79]},
  "density": 1.9,
  "silence": 0.31,
  "quality_score": 0.9,
  "flags": [],
  "duplicate_of": null
}
```

### 5.2 `plan.json`

```json
{
  "maqam": "Hijaz",
  "tempo": 110,
  "meter": "4/4",
  "voices": "vocal+ins",              // أو "ins" عند دعم المهارة
  "target_duration_s": 240,           // من المهارة؛ لا يُشتق من cap
  "bars": 84,
  "sections": [
    {"name":"intro","bars":8,"role":"establish maqam","cadence":"open"},
    {"name":"verse","bars":16,"role":"statement","cadence":"5th"},
    {"name":"chorus","bars":16,"role":"hook","cadence":"tonic"}
  ],
  "range": [60, 69],
  "density": 1.8,
  "silence": 0.30,
  "motifs": ["A","A'","B","C"],
  "chords": ["Fm","Bbm","C7","Fm"],
  "source": {"prior":"hijaz_aaab", "n": 34, "confidence":"high"},
  "warnings": []
}
```

**قاعدة:** إذا مرّرت المهارة `bars`، استخدمه؛ وإذا مرّرت `target_duration_s` فقط،
اشتق `bars` من `tempo` و`meter`. لا تقرأ `cap` من المانيفست.

> **تعارض مخطط (يجب حسمه — D5):** هذا `plan.json` عالي المستوى **ليس** مخطط
> `checker.py`. `checker.py` v0.2.0 يطلب 15 مفتاحًا:
> `key, tempo, meter, unit, bars, syllables, sections(strings), melisma_min,
> melisma_max, register{mean,top,tolerance}, max_top_duration_share,
> min_distinct_durations, ties_min, min_fill_notes, chords_min`.
> لا تمرّر `brief.json` مباشرة إلى `checker.py`؛ إما أن يُخرج `ostris plan`
> **`brief.json` + `skill_plan.json`**، أو يبني `ostris check` مخطط المهارة من
> `brief.json` + النص/البارات. راجع D5 في §13.

### 5.3 `report.json`

```json
{
  "pass": true,
  "failures": [],
  "warnings": [
    {"code":"density","value":2.6,"target":"1.6-2.2","bar":31}
  ],
  "measured": {"bars":84,"cadence":"tonic","range":[60,69],"density":2.6},
  "similarity": {"max_shared_run":5,"source":null,"bar_range":null},
  "quotation": {"used":false,"source_id":null,"bars":0,"confidence":0.0},
  "maqam_fit": {"scale_degree_cos":0.91,"aug2_present":true}
}
```

> **دمج مع تقرير المهارة (D10):** `checker.py` v0.2.0 يُخرج
> `{ok, checks:[{tag,name,ok,class,detail}], measured{percentiles}, calibration_version}`.
> لا تستبدله: أضف `skill_report` كحقل nested، أو ادمج `checks` مع `class`.
> `pass` هنا يعني «لا FAIL في contract/sanity»، وليس «لا WARN».

---

## 6. هيكل المستودع

```text
ostris-score-tools/
  README.md
  pyproject.toml
  LICENSE
  src/ostris/
    __init__.py
    cli.py
    ingest/
      gcs.py
      yt500.py
      instrumental.py
      fadl.py
      links.py
    parse/
      abc.py
      canonical.py
      quality.py
    features/
      form.py
      melody.py
      rhythm.py
      harmony.py
      prosody.py
      maqam.py
      mood.py
    corpus/
      records.py
      priors.py
      banks.py
      similarity.py
      eval_set.py
    serve/
      plan.py
      exemplar.py
      check.py
      search.py
      state.py
    schemas/
      track_record.schema.json
      prior.schema.json
      plan.schema.json
      report.schema.json
  data/            # gitignored
    records/
    priors/
    banks/
    eval/
  tests/
    fixtures/
    test_parse.py
    test_priors.py
    test_plan.py
    test_check.py
  docs/
    data-contract.md
    evaluation.md
    integration.md
    provenance.md
  scripts/
    sync_manifests.sh
    build_all.sh
```

> **`parse/abc.py` (D14):** يجب أن يلفّ/يثبّت `abc_tools.py` نفسه (نفس عقد
> الرندر) أو يثبّت hash له. لا تكتب parser متسامحًا جديدًا؛ الـ checker
> والـ renderer يشتركان في نفس اللهجة.

---

## 7. CLI (السطح الذي تراه المهارة)

```bash
# offline
ostris audit                    # counts, mapping, parse failures, duplicates
ostris build                    # records → priors → banks → eval

# online
ostris plan     --manifest song.json --bars 84 --voices vocal+ins --out plan.json
ostris plan     --manifest song.json --duration-s 240 --out plan.json   # بديل
ostris exemplar --maqam hijaz --function cadence --mood yearning --bars 2
ostris check    score.abc --plan plan.json --voices vocal+ins --json report.json
ostris similarity score.abc --json          # alias: originality
ostris state    --plan plan.json --report report.json
ostris search   score.abc --top 5          # optional
ostris eval     --suite v1 --out results/
```

**قواعد الإخراج:**
- JSON فقط عند `--json`.
- لا يطبع السكور كاملًا أبدًا.
- كل خطأ يحمل `code`, `bar`, `fix`.

---

## 8. مراحل التنفيذ

### M0 — Audit & contracts (3 أيام)
**Deliverables:**
- `manifest_links.csv`: 482 → 460 yt500 + 22 fadl، مع missing.
- `audit.json`: parse success، bars incomplete، missing chords، duration mismatch، duplicates.
- schemas v1 + fixtures.

**Gate:** ≥95% من 460 قابلة للربط والتحليل؛ قائمة الـ missing مع قرار.
**+ إعادة التحقق** من أرقام §1 (482/495/35/438/2.95GiB/36.6h) من manifests.
**+** لا تُبنى priors/plan/check قبل حسم قرارات M1/M2/M4/M5 في §13.3؛
الـ audit يمكن أن يبدأ الآن.

### M1 — Ingest & canonicalize (أسبوع)
- تنزيل manifests + عينة tar.gz (لا الـ2.95GiB كاملة).
- استخراج `score.abc` + sidecars.
- canonical ABC (توحيد `L/M/Q`، voices، sections) **مع الحفاظ على `M:` و`[K:...]`**
  — لا تفرض 4/4 (D9).
- ربط FADL.
**Gate:** 460 + 22 في `records.jsonl`، مع `provenance` لكل حقل.

### M2 — Features & labels (1–2 أسبوع)
- form/bars/sections من `structure.lab` + ABC.
- melody/rhythm/harmony/prosody.
- maqam classifier: **قاعدة symbolic + مراجعة يدوية على الـ482** (D3)؛
  **لا تدريب على تسميات 177** (هي prompt، M1: 0% Hijaz). الـ177 فحص سلوك فقط.
- mood tags من captions + lexicon، مراجعة 50.
**Gate:** ≥90% من 460 لها `maqam` مع confidence **بما فيها `other/unknown`**؛
تقرير دقة على **عينة مراجعة من 482**، وفحص سلوك على 177 — لا «دقة على 177».

> **Amended 2026-11-23 (English):** no expert maqam review is available. M2
> implements the objective feature layer and an unreviewed coarse
> `mode_hypothesis`; `maqam` stays `null`. The replacement gate is 482/482
> feature rows, 482/482 mode-hypothesis rows, and zero named-maqam claims.
> The original maqam coverage/accuracy gate is deferred with D3 and D12.

### M3 — Priors & plan (أسبوع)
- quantiles لكل stratum، مع `n` و`confidence`.
- backoff للطبقات الصغيرة.
- `plan` generator + fixtures.
- **المخرج (D5):** `brief.json` + `skill_plan.json` (15 مفتاحًا)، لا `plan.json` غامض.
**Gate:** 10 مانيفستات تجريبية → `skill_plan.json` صالح 100%، bars داخل ±10% من الهدف.

### M4 — Idioms, similarity, check (أسبوع)
- استخراج 2–4 bars لكل function/maqam.
- k-gram similarity index (تتبّع الاقتباس، لا منعه).
- `check` يجمع: skill checker + maqam fit + priors + similarity.
- **سياسة البوابات (D8):** `contract` + `sanity` = FAIL؛ `style` = WARN افتراضيًا.
  `ostris check` لا يفشل على WARN.
**Gate:** 3 سكورات معروفة (جيد/متوسط/سيئ) → report يميزها، مع `class` و`percentiles`.

### M5 — Integration (أسبوع)
- تثبيت نسخة المهارة: **v0.2.0** + hash `checker.py` + hash `calibration.json` (D7).
- `ostris check` يمرّر `--require-final-rest` عند الرندر، ويترك `style` WARN
  افتراضيًا؛ `--strict-style` اختياري.
- إضافة قسم TOOLS إلى `SKILL.md` (3 أوامر فقط).
- wrapper يعمل في `/content/chat` وعلى CPU.
- **الوضع instrumental (D6):** إما `Vocal+Ins` فقط في v1، أو `--voices ins` بعد
  إضافته للمهارة. لا تفترض أن `Ins` فقط يمرّ.
**Gate:** جلسة كاملة على مانيفست واحد: plan → write → check → patch، دون corpus في السياق.

### M6 — Evaluation (أسبوع)
- 12–16 مانيفست محجوزًا **من الـ35 غير المستخدمة في YT500** (D13)، لا من الـ177.
- A/B: prompt-only vs tool-assisted.
- مقاييس الجودة + التوكنز + الزمن.
- **D1:** إن كان الهدف ABC quality، فالتقييم على ABC؛ إن كان audio، أضف جلسة رندر.
**Gate:** non-inferiority في الجودة، وتوفير ≥30% في التوكنز.

### M7 — Hardening & handoff (3–5 أيام)
- docs، provenance، licensing، reproducible build.
- CI على fixtures.
- release v0.1.

---

## 9. خطة التقييم (جودة + كلفة)

### 9.1 مهام الاسترجاع/الوسوم
| المهمة | الموجب | السلب الصعب |
|---|---|---|
| maqam retrieval | نفس `maqam` | نفس key/tempo، مقام مختلف |
| same song/take | نفس `title+artist` أو duplicate group | عنوان مشابه |
| section match | نفس section في نسخة أخرى | نفس maqam، قسم مختلف |
| text→ABC | caption/lyrics | نفس maqam، وصف مختلف |

**المقاييس:** Recall@1/5/10، MRR، nDCG@10، silhouette، linear probe.

> **تنبيه (D12):** تسميات maqam في مجموعة الاسترجاع يجب أن تكون **مراجعة
> يدويًا**، لا prompt tags. وإلا فالاسترجاع يقيس تسمية النموذج لنفسه.

### 9.2 مهام التوليد
- 12–16 مانيفست محجوز **من الـ35 غير المستخدمة في YT500** (D13)، لا من الـ177.
- A: prompt + skill فقط.
- B: + `plan` + `exemplar` + `check`.
- قياس:
  - validity (bars/ties/accents/voices)
  - structural conformity
  - maqam conformity (scale-degree + aug-2 presence)
  - mood (blind human)
  - quotation/similarity (max shared run، المصدر، هل يخدم الغرض)
  - render success
  - tokens / wall time / first-pass acceptance / repair count

### 9.3 بوابة الإصدار
> لا تُعتمد B إلا إذا كانت **غير أدنى** من A في الجودة (non-inferiority)،
> وأفضل في التوكنز/الزمن. أي انحدار في أي بُعد جودة = رفض.

---

## 10. التكامل مع المهارة

### 10.1 الشروط المسبقة (من المهارة)
- **`checker.py` v0.2.0** (وليس v1):
  - `--json` يُخرج `{ok, checks:[{tag,name,ok,class,detail}], measured{percentiles}, calibration_version}`.
  - `--require-final-rest` يجعل السكتة الأخيرة عقد رندر؛ بدونها WARN.
  - `--strict-style` يحوّل `style` إلى FAIL؛ افتراضيًا `style` = WARN.
  - `--calibration` لتثبيت `scripts/calibration.json`.
  - `VOICES = ("Vocal","Ins")` ما زال إلزاميًا؛ `Ins` فقط غير مدعوم (D6).
- **مخطط المهارة:** `skill_plan.json` بـ 15 مفتاحًا (D5)، وليس `brief.json` عالي المستوى.
- **`abc_tools.py`** parser/dialect (D14) — لا parser جديد.
- **`references/numbers.md`** هو سجل الأرقام البشري؛ `scripts/calibration.json`
  هو النسخة الآلية. لا تنسخ الأرقام إلى `ostris` يدويًا.
- **`syllabify.py` v0.2 `--json`** يُخرج أيضًا `pace`, `case_ratio`,
  `seconds_per_bar`, `tempo_source`, `syllables_p25/p75`.
- **المهارة تمرّر `bars` أو `target_duration_s`**؛ الأداة لا تفسّر `cap`.
- version/hash مثبتة في `ostris.toml`: `skill_version = 0.2.0` + hash
  `checker.py` + hash `calibration.json` (D7).

### 10.2 ما يُضاف إلى `SKILL.md`
```text
## TOOLS (ostris v0.1)
1) ostris plan --manifest <song> --bars <n> --voices vocal+ins
                --out brief.json --skill-plan skill_plan.json
   (أو --duration-s <s> بدل --bars)
2) ostris exemplar --maqam <m> --function <f> --mood <mood> --bars 2
3) ostris check score.abc --plan skill_plan.json --voices vocal+ins --json report.json

Rules:
- Do not paste the corpus.
- Do not write your own checker.
- Do not websearch lyrics.
- Do not install packages.
- Patch; do not rewrite.
- Duration/bars belong to the skill, not to the corpus tool.
- WARN is not FAIL; fix contract/sanity, read style.
- Pass --require-final-rest before rendering.
```

### 10.3 ما لا تفعله الأداة
- لا تكتب السكور نيابة عن الوكيل.
- لا تعيد ترتيب اختيارات الوكيل.
- لا تخفي تحذيرات الجودة.

---

## 11. المخاطر والتخفيف

| الخطر | الأثر | التخفيف |
|---|---|---|
| لا maqam labels في 482 | priors غير دقيقة | قاعدة symbolic + مراجعة يدوية 100–150 + confidence |
| الأصول vocal والهدف instrumental | priors مضللة | استخدم `Ins`/structure/chords فقط؛ لا prosody |
| SheetSage2 أخطاء | priors ملوثة | quality_score + استبعاد + أوزان |
| 22 FADL mapping | نقص تغطية | ربط بالعنوان/الألبوم من `FADL_SHAKER` |
| corpus أوسع من الستايل | priors باهتة | strata + اعتراف بأنها أوسع من five_stars |
| popularity bias | "جيد" ≠ "قابل للتأليف" | لا تعاملها كـ gold؛ eval منفصل |
| overfitting | موسيقى متشابهة | deviation allowance + held-out eval |
| copyright | derivative work | الاقتباس مسموح بقرار المشروع؛ وثّق `quotation` provenance؛ راجع السياسة إن تجاري |
| تعقيد الأداة | الوكيل يتجنبها | CLI 3 أوامر + JSON + docs قصيرة |

---

## 12. أول 10 أيام (تنفيذي)

1. **Day 1:** إنشاء المستودع + schemas + fixtures + `sync_manifests.sh`.
2. **Day 2:** `audit`: ربط 482 → transcripts، تعداد missing/duplicates، parse كل ABC.
3. **Day 3:** تقرير QC + قرارات exclude + mapping FADL.
4. **Day 4:** canonicalizer + features v0 (form/melody/rhythm).
5. **Day 5:** maqam rule-based classifier (key + scale-degree + intervals)؛ تقرير على عينة يدوية.
6. **Day 6:** تطبيقه على 482 + عينة مراجعة 100–150.
7. **Day 7:** `priors` v0 لـ Hijaz + Kurd؛ مراجعة يدوية للبطاقات.
8. **Day 8:** `plan` generator + 10 manifests تجريبية.
9. **Day 9:** `check` + `similarity` v0.
10. **Day 10:** جلسة تكامل واحدة + قياس توكنز/جودة مبدئي.

**قرار البوابة بعد Day 10:** هل البريورات + plan تحسّن الجودة؟ إن لا، لا تكمل بناء banks/search قبل إعادة تصميم الطبقة.

---

## 13. قرارات ما قبل التنفيذ

> **القاعدة:** كل قرار هنا له خيارات وتوصية ومرحلة يحجبها. لا تبدأ المرحلة
> المحجوبة قبل الحسم. الحالة: ⏳ مفتوح · 🔶 موصى به بانتظار تأكيد · ✅ محسوم.

### 13.1 محسومة سابقًا (2026-11-22)

- ~~حجم المكتبة~~ → **482** (460 + 22)؛ الـ495 مصادر، و35 held-out.
- ~~177 five_stars~~ → **مستثناة من priors/eval**؛ تُستخدم الآن **لمعايرة القيود فقط**.
- ~~438 v3~~ → **مستثناة** من priors/eval؛ cross-check فقط إن سُمح.
- ~~Vocal + Ins أم Ins~~ → الافتراضي **Vocal + Ins** لأن الـchecker يفرضه؛ `Ins` فقط لاحقًا.
- ~~cap أم duration~~ → **المهارة تملكها**؛ الأداة تستقبل `bars`/`target_duration_s`.
- ~~الاقتباس~~ → **مسموح صريحًا وضمنيًا**، بما في ذلك جملة كاملة/سطر حرفيًا؛ الأداة تتبّع وتنسب ولا تمنع.

### 13.2 قرارات مطلوبة

| # | القرار | الخيارات | التوصية | يحجب | الحالة |
|---:|---|---|---|---|---|
| **D1** | هدف الجودة النهائي | ABC quality / rendered audio / كلاهما | **ABC أولًا**؛ audio في M6 إن توفر رندر | M6 | 🔶 ABC only — no render/audio judge |
| **D2** | وظيفة الـ35 held-out | توليد / استرجاع / كلاهما | **كلاهما**؛ 12–16 للتوليد والباقي للاسترجاع | M6 | ✅ 2026-11-23 (14 + 17) |
| **D3** | مراجعة maqam | 482 كاملة / عينة 100–150 / مرحلتان | **مرحلتان:** 120 عينة + كل low-confidence | M2 | ⏸️ deferred — no reviewer |
| **D4** | 438 v3 | تُترك / cross-check / تدريب | **cross-check فقط**؛ لا تدريب ولا priors/eval | M2 | ✅ 2026-11-23 |
| **D5** | مخطط `plan.json` | `brief.json`+`skill_plan.json` / ملف واحد / `check` يبني | **`brief.json` + `skill_plan.json`** | M1/M3/M5 | ✅ 2026-11-23 |
| **D6** | الوضع instrumental | إضافة `--voices ins` الآن / `Vocal+Ins` فقط / checker منفصل | **`Vocal+Ins` في v1**؛ instrumental لاحقًا | M1/M5 | ✅ 2026-11-23 |
| **D7** | عقد المهارة | تثبيت v0.2.0 + flags / تجميد v1 | **v0.2.0** + hash + `--require-final-rest` | M1/M5 | ✅ 2026-11-23 |
| **D8** | سياسة البوابات | contract+sanity / +style / درجة مركبة | **contract+sanity فقط hard**؛ style WARN | M4/M5/M6 | ✅ 2026-11-23 |
| **D9** | المتر المتغير | حفظ `M:` / توحيد 4/4 / رفض | **حفظ `M:` و`[K:...]`** | M1 | ✅ 2026-11-23 |
| **D10** | دمج `report.json` | `skill_report` nested / دمج مسطح / ملفان | **nested + `class`** | M4/M5 | ✅ 2026-11-23 |
| **D11** | دور 177 | calibration only / priors/eval / تجاهل | **calibration only** | M2/M6 | ✅ 2026-11-23 |
| **D12** | تعريف maqam coverage | labelled incl. other / accuracy / كلاهما | **coverage + accuracy منفصلان** | M2/M6 | ⏸️ N/A until D3 |
| **D13** | مصدر held-out | 35 / 177 / خارجي | **35 YT500 غير المستخدمة** | M6 | ✅ 2026-11-23 |
| **D14** | parser | vendor `abc_tools` / جديد / pin hash | **vendor أو pin hash** | M1 | ✅ 2026-11-23 |
| **D15** | السكتة الأخيرة | عقد دائم / WARN + flag / تجاهل | **WARN + `--require-final-rest`** | M5 | ✅ 2026-11-23 |
| **D16** | sanity على 482 | تطبيقها / فقط على السكور المولّد / لا | **فقط على السكور المولّد**، لا priors الـ482 | M2/M4 | ✅ 2026-11-23 |

> **M2 amendment (2026-11-23):** no expert maqam review is available. D3 and
> D12 are **deferred**, not satisfied. D4 (cross-check only), D11 (calibration
> only), and D16 (generated scores only) are recorded. M2 builds deterministic
> features plus an explicitly unreviewed `mode_hypothesis`; `maqam` remains
> `null`. No maqam coverage or accuracy is claimed. See
> `docs/ostris-decisions.md` and `docs/ostris-m2-features.md`.

> **M3–M6 implementation note (2026-11-23, English):** D5/D8/D10/D13/D15 are
> applied as recorded above. M3 builds objective priors and generates
> `brief.json` + `skill_plan.json`; M4 builds a structural idiom bank, an
> interval k-gram index, and a combined `check`; M5 wires the three online
> commands into `SKILL.md` and a wrapper; M6 builds the deterministic held-out
> split and scores supplied runs. D1 stays ABC-only (no audio judge) and D2 is
> applied as 14 generation + 17 retrieval tracks. No maqam label or maqam-fit
> score is produced. See `docs/ostris-m3-priors-plan.md`,
> `docs/ostris-m4-idioms-check.md`, and
> `docs/ostris-m5-m6-integration-eval.md`.

### 13.3 بوابة البدء

> **M1 gate resolved (2026-11-23):** D5, D6, D7, D9, D14 are recorded with
> concrete pins in `docs/ostris-decisions.md`. M1 (`ostris build`) is
> implemented and passes on 482/482 tracks. M2–M6 gates are recorded in §13.2
> and in the stage reports; D3/D12 remain deferred.

- **قبل M1:** D5, D6, D7, D9, D14. ✅
- **قبل M2:** D3, D4, D11, D12, D16. — D4/D11/D16 ✅ 2026-11-23; D3/D12
  ⏸️ deferred because no expert maqam review is available.
- **قبل M4/M5:** D8, D10, D15.
- **قبل M6:** D1, D2, D13.
- **M0 audit** يمكن أن يبدأ الآن؛ لا يبنى priors/plan/check قبله.

---

## 14. تعريف النجاح

| البُعد | الهدف |
|---|---|
| تغطية البيانات | ≥95% من 482 مرتبطة ومحللة (بعد M0 audit) |
| maqam coverage | **not claimed**: no reviewed labels; deferred with D3/D12 |
| feature coverage (M2) | 482/482 deterministic feature rows; 482/482 unreviewed mode hypotheses |
| plan validity | 100% من المانيفستات تُنتج `skill_plan.json` صالحًا (D5) |
| check | 100% **contract + sanity**؛ `style` warnings معروضة وقابلة للتنفيذ (D8) |
| quotation | 100% من الاقتباسات المتعمدة موثّقة (`source_id`, `bar_range`) |
| جودة | non-inferiority في تقييم أعمى |
| كلفة | ≥30% خفض توكنز (هدف 30–40k/سكور) |
| integration | 3 أوامر فقط من المهارة |
| reproducibility | build من جذر البيانات في أمر واحد |
