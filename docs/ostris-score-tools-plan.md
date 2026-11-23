# Plan — OSTRIS Score Tools (مستودع منفصل)

> **Provenance:** نُقل هذا الملف من `arabmaqamrock/docs/plans/` إلى مستودع المهارة في 2026-11-23.
> المسارات `arabmaqamrock/...` تخص المستودع الخارجي؛ مستودع المهارة هو `skill_abc_writer`.

**Status:** proposal — يبدأ بعد تثبيت مهارة `maqam-score` (v1 frozen)
**Date:** 2026-11-22
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

---

## 1. جرد البيانات (تم التحقق 2026-11-22)

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
- **177 five_stars و438 v3 مستثناة** من priors/eval بقرار المشروع (داخل تدريب LoRA v3).
- الحل: طبقة وسوم تعتمد على:
  1. **قاعدة symbolic**: key + scale-degree + interval + presence of aug-2 / minor-2 / major-3.
  2. **مراجعة يدوية** لعينة طبقية (100–150) لمعايرة القاعدة وقياس دقتها.
  3. **captions** كإشارة ضعيفة فقط (نادرًا ما تذكر maqam صراحة).
  4. **438 v3** تُستخدم فقط كـ cross-check خارجي إن سُمح؛ لا تدخل priors ولا eval.
- كل سجل يحمل `maqam`, `maqam_confidence`, `maqam_source`.
- التوقع: ليست كل الأغاني من الأربعة؛ أضف `other/unknown` ولا تُجبر التسمية.

### 2.3 الـ482 = 460 + 22، والـ495 ليست المكتبة
- 22 من Fadhl Shaker **مدمجة** في manifest الـ482؛ transcripts في `TRANSCRIPTS/FADL_SHAKER` (15 ألبومًا).
- 460 yt500 تُربط بـ `(source_rank, video_id)` أو `out_name` (`yt500-0001-fbK2ySlxAW4`).
- **35 transcript غير مستخدمة** من الـ495 → **held-out طبيعي** (ليست في المكتبة ولا في تدريب v3).
- استبعد 5 duplicate groups / 10 tracks من الـ priors والـ eval.

### 2.4 الـ corpus أوسع من الستايل المستهدف
- `arabic_instrumental_dataset` = "Middle Eastern fusion, instrumental" (captions)، وليس بالضرورة `arabmaqamrock, 110 BPM`.
- 177 five_stars كانت أقرب للستايل، لكنها **مستثناة**؛ لذلك:
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
| 177 five_stars | **مستثناة** من priors/eval (داخل تدريب LoRA v3). |
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

### M1 — Ingest & canonicalize (أسبوع)
- تنزيل manifests + عينة tar.gz (لا الـ2.95GiB كاملة).
- استخراج `score.abc` + sidecars.
- canonical ABC (توحيد `L/M/Q`، voices، sections).
- ربط FADL.
**Gate:** 460 + 22 في `records.jsonl`، مع `provenance` لكل حقل.

### M2 — Features & labels (1–2 أسبوع)
- form/bars/sections من `structure.lab` + ABC.
- melody/rhythm/harmony/prosody.
- maqam classifier: تدريب/معايرة على 177 five_stars، تطبيق على 460، مراجعة 100 يدويًا.
- mood tags من captions + lexicon، مراجعة 50.
**Gate:** ≥90% من 460 لها `maqam` مع confidence؛ تقرير دقة على 177.

### M3 — Priors & plan (أسبوع)
- quantiles لكل stratum، مع `n` و`confidence`.
- backoff للطبقات الصغيرة.
- `plan` generator + fixtures.
**Gate:** 10 مانيفستات تجريبية → plan صالح 100%، bars داخل ±10% من الهدف.

### M4 — Idioms, similarity, check (أسبوع)
- استخراج 2–4 bars لكل function/maqam.
- k-gram similarity index (تتبّع الاقتباس، لا منعه).
- `check` يجمع: skill checker + maqam fit + priors + similarity.
**Gate:** 3 سكورات معروفة (جيد/متوسط/سيئ) → report يميزها.

### M5 — Integration (أسبوع)
- تثبيت نسخة المهارة (hash).
- إضافة قسم TOOLS إلى `SKILL.md` (3 أوامر فقط).
- wrapper يعمل في `/content/chat` وعلى CPU.
**Gate:** جلسة كاملة على مانيفست واحد: plan → write → check → patch، دون corpus في السياق.

### M6 — Evaluation (أسبوع)
- 12–16 مانيفست محجوزًا.
- A/B: prompt-only vs tool-assisted.
- مقاييس الجودة + التوكنز + الزمن.
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

### 9.2 مهام التوليد
- 12–16 مانيفست محجوز (lyrics + maqam + mood + sections).
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
- `checker.py --json` بعقد ثابت؛ حاليًا `VOICES = ("Vocal","Ins")` إلزامي.
- `plan.json` schema.
- `abc_tools.py` parser/dialect.
- `syllabify.py --json` (للمانيفستات ذات الكلمات).
- **المهارة تمرّر `bars` أو `target_duration_s`**؛ الأداة لا تفسّر `cap`.
- version/hash مثبتة في `ostris.toml`.

### 10.2 ما يُضاف إلى `SKILL.md`
```text
## TOOLS (ostris v0.1)
1) ostris plan --manifest <song> --bars <n> --voices vocal+ins --out plan.json
   (أو --duration-s <s> بدل --bars)
2) ostris exemplar --maqam <m> --function <f> --mood <mood> --bars 2
3) ostris check score.abc --plan plan.json --voices vocal+ins --json report.json

Rules:
- Do not paste the corpus.
- Do not write your own checker.
- Do not websearch lyrics.
- Do not install packages.
- Patch; do not rewrite.
- Duration/bars belong to the skill, not to the corpus tool.
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

## 13. أسئلة مفتوحة (تحتاج حسمًا قبل M2)

**تم حسمها (2026-11-22):**
- ~~حجم المكتبة~~ → **482** (460 + 22)؛ الـ495 مصادر، و35 held-out.
- ~~177 five_stars~~ → **مستثناة** من priors/eval.
- ~~438 v3~~ → **مستثناة** من priors/eval؛ cross-check فقط إن سُمح.
- ~~Vocal + Ins أم Ins~~ → الافتراضي **Vocal + Ins** لأن الـchecker يفرضه؛ `Ins` فقط لاحقًا.
- ~~cap أم duration~~ → **المهارة تملكها**؛ الأداة تستقبل `bars`/`target_duration_s`.
- ~~الاقتباس~~ → **مسموح صريحًا وضمنيًا**، بما في ذلك جملة كاملة/سطر حرفيًا؛ الأداة تتبّع وتنسب ولا تمنع.

**مسجّل بانتظار إجابة المستخدم:**
| # | السؤال | الحالة |
|---:|---|---|
| 1 | الهدف النهائي: **ABC quality** أم **rendered audio quality**؟ | ⏳ بانتظار |
| 2 | الـ35 held-out: لتقييم **التوليد** أم **الاسترجاع** فقط؟ | ⏳ بانتظار |
| 3 | مراجعة maqam: **482 كاملة** أم **عينة 100–150** مع confidence؟ | ⏳ بانتظار |
| 4 | هل تُستخدم **438 v3** كـ cross-check مسموح، أم تُترك تمامًا؟ | ⏳ بانتظار |

> هذه لا تعطّل M0. تُحسم قبل M2/M6 حسب الجدول.

---

## 14. تعريف النجاح

| البُعد | الهدف |
|---|---|
| تغطية البيانات | ≥95% من 482 مرتبطة ومحللة |
| maqam coverage | ≥90% بتسمية موثوقة |
| plan validity | 100% من المانيفستات |
| check | 100% hard gates، warnings قابلة للتنفيذ |
| quotation | 100% من الاقتباسات المتعمدة موثّقة (`source_id`, `bar_range`) |
| جودة | non-inferiority في تقييم أعمى |
| كلفة | ≥30% خفض توكنز (هدف 30–40k/سكور) |
| integration | 3 أوامر فقط من المهارة |
| reproducibility | build من GCS في أمر واحد |
