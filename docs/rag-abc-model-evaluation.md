# تقييم نماذج Hugging Face لبناء RAG فوق سكورات ABC

> **Provenance:** نُقل هذا الملف من `arabmaqamrock/docs/plans/` إلى مستودع المهارة في 2026-11-23.
> المسارات `local_workspace/...` و`datasets/five_stars/...` تخص مستودع `arabmaqamrock` الخارجي.

**Status:** تقييم مكتبي (model cards + أوراق + بنية)، بدون تشغيل GPU على هذه الآلة
**Date:** 2026-11-22
**Question:** أي نماذج HF تصلح لبناء نظام استرجاع/ RAG فوق مكتبة سكورات ABC،
بحيث نجد «المقاطع الأكثر تشابهًا» مع مقطع معطى بحسب الثيمات المشتركة (motifs)،
المقام، الأسلوب، والكلمات؟
**Data:**
- `local_workspace/REF_ABC_SCORE_MAQAM.zip`: 40 سكور، 4 مقامات (Ajam 6، Hijaz 9، Kurd 19، Nahawand 6).
- `datasets/five_stars/transcripts/`: 177 سكور مرجعي + صوت + بيانات وصفية (Hijaz 49، Ajam 43، Kurd 43، Nahawand 42). هذا هو corpus التقييم الحقيقي.

---

## 0. TL;DR

1. **لا يوجد نموذج واحد يحل المشكلة.** الاسترجاع بـ «الثيم» ليس مهمة embeddings دلالية فقط؛
   هو مزيج من: (أ) تشابه دلالي/أسلوبي، (ب) تطابق motif لحني/إيقاعي، (ج) مقام/سلّم، (د) كلمات/وصف.
2. **أفضل backbone رمزي (symbolic) على HF هو CLaMP 3 بنسخة `C2`** — يدعم ABC و MIDI و MusicXML
   وصوتًا ونصًا في فضاء مشترك، 768-dim، ورخصته MIT. هو الخيار الأول لـ ABC→ABC و text→ABC.
3. **CLaMP 2 / M3** يليه، لكن M3 الخام ليس encoder استرجاع — يجب استخدام الـ projection المدرَّب
   (checkpoint CLaMP 2 الكامل) أو CLaMP 3 C2.
4. **لجانب النص/الوصف/الكلمات العربية** أفضل خيارات CPU: `Qwen3-Embedding-0.6B` (Apache-2.0،
   32k، 100+ لغة) أو `BGE-M3` (MIT، dense+sparse+ColBERT). هذان ليسا بديلًا عن CLaMP للـ motifs،
   بل طبقة موازية للـ metadata والكلمات.
5. **للصوت** (إن أردت «يشبه من حيث الصوت»): `MERT-v1-95M` أو `MuQ` أو `MusicFM`،
   وCLaMP 3 SAAS للاسترجاع عبر الوسائط. لكن الصوت لا يرى الـ motif المكتوب بدقة.
6. **«الثيمات» في هذا المشروع تحتاج فهرسًا خاصًا بها**: interval n-grams، rhythm n-grams،
   chord transitions، scale-degree/maqam features. هذه موجودة أصلًا في
   `local_workspace/abc_similarity_x/abc_similarity.py` — ويجب أن تبقى جزءًا من الـ RAG،
   لا أن تُستبدل بـ embedding.
7. **الخلاصة المعمارية:** multi-vector / hybrid retrieval + late fusion + reranker،
   وليس «vector DB واحد + cosine» فقط.

---

## 1. لماذا ABC صعب على النماذج العامة؟

| الخاصية في سكوراتنا | الأثر على النموذج |
|---|---|
| ABC لغة notation وليست نصًا طبيعيًا | Text embedders ترى `^F`, `_B`, `z12`, `[V:1]` كرموز OOD؛ BM25/char n-grams قد تتفوق عليها في التطابق الحرفي. |
| صوتان: `V:Vocal` و `V:Ins` | النموذج يجب أن يرى تفاعل الأصوات؛ ABC القياسي يفصل الأصوات، وCLaMP يتوقع **interleaved ABC** حيث بارات الأصوات المتوازية متجاورة. |
| `L:` و `M:` و `Q:` تختلف بين الملفات | لا تقارن أطوال النوتات الخام؛ طبّع إلى ثوانٍ/بارات أولًا. |
| مقامات عربية (Hijaz, Kurd, Nahawand, Ajam) | النماذج الغربية تُدرَّب على مقامات/سلالم مختلفة؛ لا تفترض أنها تلتقط الجنس أو السيكاه. |
| زخارف وأرباع الصوت (microtones) | ABC يدعم `^`/`_` لكن كثيرًا من النماذج لا تفهم ربع الدرجة؛ حوّل إلى MIDI/cents عند الحاجة. |
| سكور طويل (> 512 بار) | CLaMP يقتطع عند 512 patch/بار؛ يجب chunking + تجميع. |
| نفس الأسلوب/الـ prompt في كل الملفات | cosine بين كل السكورات مرتفع (anisotropy)؛ بدون centering/whitening قد «يتشابه كل شيء مع كل شيء». |

---

## 2. تشريح نظام RAG المطلوب

```
                    ┌─────────────────────────────────────────────┐
 Query (track ABC)  │ 1) Canonicalize: parse, normalize, interleave│
 أو (lyrics+maqam)  │ 2) Represent: symbolic / melody / motif /    │
                    │    metadata / audio / lyrics                 │
                    └──────────────────┬──────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 3) Candidate generation (hybrid, top-k لكل فهرس)         │
        │    • CLaMP3 C2 dense (symbolic)                          │
        │    • CLaMP3 C2 dense (melody-only)                       │
        │    • BM25 / char n-gram على ABC                          │
        │    • motif inverted index (interval/rhythm/chord n-grams)│
        │    • Qwen3/BGE-M3 dense (metadata + Arabic lyrics)       │
        │    • MERT/MuQ dense (audio, اختياري)                     │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 4) Fusion: RRF أو أوزان متعلمة                           │
        │ 5) Rerank: GBDT/MLP على 17 مقياسًا + cosine + metadata    │
        │    (أو Qwen3-Reranker للنص فقط)                          │
        └──────────────────────────┬───────────────────────────────┘
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │ 6) LLM synthesis: يشرح سبب التشابه، ويقتبس bars/motifs   │
        │    مع citations إلى ملفات ABC                            │
        └──────────────────────────────────────────────────────────┘
```

**تعريفان يجب فصلهما:**

| نوع التشابه | إشارته الأساسية | النموذج/الأداة |
|---|---|---|
| **Semantic / style** (نفس المزاج، الحقبة، التوزيع، الآلات) | embedding دلالي | CLaMP 3، MERT، Qwen3/BGE-M3 للوصف |
| **Motivic / thematic** (نفس الجملة اللحنية أو الإيقاعية) | تطابق n-grams + DTW | `abc_similarity.py` + فهرس motif |
| **Maqam / scale** | توزيع الدرجات بعد التطبيع | interval hist، scale-degree، jins detection |
| **Lyrical theme** | نص عربي | Qwen3-Embedding / BGE-M3 / Arabic embedder |

---

## 3. خريطة النماذج على Hugging Face

### 3.1 نماذج رمزية (Symbolic-native) — الأقرب لمشكلتنا

| النموذج | HF ID | المدخل | الأبعاد | الحجم | الرخصة | مُدرَّب للاسترجاع؟ | الحكم |
|---|---|---|---|---|---|---|---|
| **CLaMP 3 C2** | [`sander-wood/clamp3`](https://huggingface.co/sander-wood/clamp3) | interleaved ABC، MIDI، MusicXML، صوت، نص، صور | 768 | 2.52 GB | MIT | نعم (contrastive) | **الأفضل للـ symbolic retrieval**؛ استخدم وزن `c2` لا `saas` إن كان الاسترجاع ABC↔ABC. |
| **CLaMP 2** | [`sander-wood/clamp2`](https://huggingface.co/sander-wood/clamp2) | ABC، MIDI + نص 101 لغة | 768 | 4.45 GB (كامل) / 1.36 GB (M3) | MIT | نعم | بديل ناضج؛ أضعف من CLaMP3 في الاسترجاع، لكنه قوي في التصنيف. |
| **CLaMP 1** | [`sander-wood/clamp-small-1024`](https://huggingface.co/sander-wood/clamp-small-1024) | ABC + نص إنجليزي | 1024 | صغير | MIT | نعم | legacy؛ إنجليزي فقط؛ لا تبدأ به. |
| **M3 فقط** | جزء من `clamp2` | ABC، MIDI | 768 | 1.36 GB | MIT | **لا** (self-supervised) | ليس encoder استرجاع؛ بدون projection قد يعطي تشابهًا شبه ثابت. |
| **MusicBERT** | [`manoskary/musicbert`](https://huggingface.co/manoskary/musicbert) | OctupleMIDI | 768 | 118M | MIT | لا (MLM) | يحتاج ABC→MIDI؛ جيد للبنية والأنماط، ليس للاسترجاع الجاهز. |
| **MIDI-BERT** | [`KooNakata/MIDI-BERT`](https://huggingface.co/KooNakata/MIDI-BERT) | MIDI | 768 | ~ | غير محدد | لا | بحثي؛ الرخصة غير واضحة؛ لا أنصح به إنتاجيًا. |
| **ABC LLMs** | [`Seeker38/Qwen2.5-3b-abc-notation`](https://huggingface.co/Seeker38/Qwen2.5-3b-abc-notation) وغيرها | نص/ABC | — | 3B/9B | غير محدد | لا | توليد ABC، ليس embedding؛ يصلح كـ answer synthesizer فقط. |

**ملاحظات حاسمة:**
- CLaMP 2/3 يتوقعان **interleaved ABC** (بارات الأصوات المتوازية في سطر واحد مع `[V:1]`)،
  وليس ABC القياسي الذي يفصل الأصوات. ملفاتنا `V: Vocal` / `V: Ins` كتل منفصلة →
  يجب preprocessing (`batch_interleaved_abc.py` أو equivalent).
- CLaMP 3 `C2` بُني على CLaMP 2 ثم دُرِّب على M4-RAG (2.31M زوج) — وهو الأقوى في
  الاسترجاع متعدد اللغات، لكنه لم يُدرَّب على مقامات عربية تحديدًا.
- CLaMP 3 `SAAS` أفضل للصوت؛ `C2` أفضل للـ symbolic. لا تخلط.
- أرقام الورقة: على ABC العربي، CLaMP 3 C2 يحقق MRR **0.3155** مقابل CLaMP 2 **0.2298**
  (تحسّن ~37% نسبيًا)، وعلى ABC→MIDI cross-modal: S→P = **0.4547**، P→S = **0.5293**.

### 3.2 نماذج صوتية (Audio) — إذا أردنا «يشبه من حيث الصوت»

| النموذج | HF ID | المدخل | الحجم | الرخصة | الحكم |
|---|---|---|---|---|---|
| **MERT-v1-95M** | [`m-a-p/MERT-v1-95M`](https://huggingface.co/m-a-p/MERT-v1-95M) | صوت | 95M | CC-BY-NC-4.0 | خفيف وقوي؛ أفضل بداية للـ audio embeddings. |
| **MERT-v1-330M** | [`m-a-p/MERT-v1-330M`](https://huggingface.co/m-a-p/MERT-v1-330M) | صوت | 330M | CC-BY-NC-4.0 | جودة أعلى، كلفة أعلى. |
| **MERT-v2-FullSong** | [`m-a-p/MERT-v2-FullSong`](https://huggingface.co/m-a-p/MERT-v2-FullSong) | صوت كامل | 632M | CC-BY-NC-4.0 | للأغاني الطويلة (long-form). |
| **music2vec-v1** | [`m-a-p/music2vec-v1`](https://huggingface.co/m-a-p/music2vec-v1) | صوت | 95M | CC-BY-NC-4.0 | بديل خفيف. |
| **MuQ-large** | [`OpenMuQ/MuQ-large-msd-iter`](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter) | صوت | 333M | CC-BY-NC-4.0 | SOTA audio SSL؛ جيد للـ timbre/structure. |
| **MuQ-MuLan-large** | [`OpenMuQ/MuQ-MuLan-large`](https://huggingface.co/OpenMuQ/MuQ-MuLan-large) | صوت + نص | ~ | CC-BY-NC-4.0 | فضاء مشترك audio-text؛ مفيد للـ text→audio. |
| **MusicFM** | [`tky823/MusicFM`](https://huggingface.co/tky823/MusicFM) | صوت | 329M | MIT/Apache-2.0 | **رخصة مريحة**؛ بديل جيد إن أردت تجنب NC. |
| **CLAP** | [`laion/clap-htsat-unfused`](https://huggingface.co/laion/clap-htsat-unfused) | صوت + نص | ~ | Apache-2.0 | إنجليزي؛ أضعف للموسيقى من MERT/MuQ. |
| **CLaMP 3 SAAS** | نفس `sander-wood/clamp3` | صوت (MERT features) + نص | 2.52 GB | MIT | إذا كان الاستعلام صوتًا أو تريد audio↔ABC. |

### 3.3 نماذج نصية (Text) — للوصف، الكلمات العربية، والـ metadata

| النموذج | HF ID | الأبعاد | الحجم | الرخصة | الحكم |
|---|---|---|---|---|---|
| **Qwen3-Embedding-0.6B** | [`Qwen/Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 1024 (MRL 32–1024) | 595M | Apache-2.0 | **أفضل خيار CPU/metadata**؛ 32k، 100+ لغة، instruct. |
| **Qwen3-Embedding-4B** | [`Qwen/Qwen3-Embedding-4B`](https://huggingface.co/Qwen/Qwen3-Embedding-4B) | 2560 | 4B | Apache-2.0 | جودة أعلى؛ يحتاج GPU عمليًا. |
| **BGE-M3** | [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3) | 1024 | 568M | MIT | dense + sparse + ColBERT؛ 8192؛ ممتاز للـ hybrid. |
| **gte-multilingual-base** | [`Alibaba-NLP/gte-multilingual-base`](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) | 768 | 305M | Apache-2.0 | خفيف، 8192، 70+ لغة؛ أفضل نسبة جودة/كلفة. |
| **multilingual-e5-large-instruct** | [`intfloat/multilingual-e5-large-instruct`](https://huggingface.co/intfloat/multilingual-e5-large-instruct) | 1024 | 560M | MIT | 512 token فقط؛ جيد للنصوص القصيرة. |
| **jina-embeddings-v3** | [`jinaai/jina-embeddings-v3`](https://huggingface.co/jinaai/jina-embeddings-v3) | 1024 | 572M | **CC-BY-NC-4.0** | 8192، 89 لغة، task LoRA؛ جيد لكن رخصته NC. |
| **Arabic-specific** | ابحث عن `Arabic-Triplet-Matryoshka` / `Arabic_text_embedding_for_sts` | — | — | varies | فقط إذا كانت الكلمات/الوصف العربي يهيمنان؛ غالبًا Qwen3/BGE-M3 يكفيان. |

**ملاحظة:** لا تضع ABC الخام كوثيقة نصية وتتوقع أن يفهمه text embedder. الأفضل:
«بطاقة سكور» منظمة (key, meter, tempo, chord progression, sections, motif summary, lyrics theme)
هي التي تُ embedding؛ وABC الخام يذهب إلى BM25/char n-grams.

### 3.4 Rerankers و ingestion

| النموذج | HF ID | الحجم | الرخصة | الاستخدام |
|---|---|---|---|---|
| **bge-reranker-v2-m3** | [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 568M | Apache-2.0 | rerank للنص/الوصف متعدد اللغات. |
| **Qwen3-Reranker-0.6B** | [`Qwen/Qwen3-Reranker-0.6B`](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | 595M | Apache-2.0 | rerank قوي، 32k، instruct. |
| **gte-multilingual-reranker-base** | [`Alibaba-NLP/gte-multilingual-reranker-base`](https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base) | 306M | Apache-2.0 | خفيف ورخيص. |
| **SheetSage2** | [`m-a-p/SheetSage2`](https://huggingface.co/m-a-p/SheetSage2) | 57M | CC-BY-NC-4.0 | **تحويل صوت→ABC فقط**؛ ليس embedder. |
| **Text2Music (BART)** | [`sander-wood/text-to-music`](https://huggingface.co/sander-wood/text-to-music) | 140M | MIT | text→ABC؛ يمكن استخدامه لتوليد وصف/استعلام، لا للاسترجاع. |

**لا تستخدم SheetSage2 للاسترجاع** — هو بوابة إدخال (transcription)، وليس تمثيلًا دلاليًا.
**لا تستخدم LLM مولّد ABC كـ embedder** — مخرجاته نصوص، وليس فضاء متجهات مستقر.

---

## 4. الأدلة الرقمية من الأوراق (وليس من تشغيلنا)

| النموذج | المهمة | المقياس | الرقم |
|---|---|---|---|
| CLaMP 2 | WikiMT text→ABC (1010 زوج) | MRR / HR@1 / HR@10 | 0.3438 / 0.2705 / 0.4870 |
| CLaMP 2 | MidiCaps text→MIDI | MRR / HR@1 / HR@10 | 0.2695 / 0.1653 / 0.4782 |
| CLaMP 3 C2 | ABC عربي (WikiMT-X) | MRR | **0.3155** |
| CLaMP 2 | ABC عربي (WikiMT-X) | MRR | 0.2298 |
| CLaMP 3 C2 | ABC→MIDI (S→P) | MRR | 0.4547 |
| CLaMP 3 C2 | MIDI→ABC (P→S) | MRR | 0.5293 |
| Qwen3-Embedding-0.6B | MTEB Multilingual | Mean(Task) | 64.33 |
| BGE-M3 | MTEB Multilingual | Mean(Task) | 59.56 |
| multilingual-e5-large-instruct | MTEB Multilingual | Mean(Task) | 63.22 |

**كيف نقرأ هذه الأرقام:**
- حتى SOTA على text→ABC يحقق MRR ≈ 0.31 على 1010 مرشحًا. أي أن «أفضل تطابق» ليس مضمونًا
  حتى مع CLaMP 3. توقّع أن الـ retrieval سيكون **candidate generation**، ثم rerank/LLM.
- الأرقام أعلاه على مجموعات غربية/عامة، وليست على مقامات عربية أو على corpusنا.
  لا تنقل الأرقام كما هي؛ استخدمها فقط لترتيب الخيارات.
- CLaMP 3 يتفوق على CLaMP 2 في الاسترجاع، لكن الورقة نفسها تقول إنه **لا يتفوق عليه
  في تصنيف الـ symbolic** (لأنه دُرِّب على نصف كمية البيانات الرمزية). إذا كان هدفك
  تصنيف المقام/النوع، CLaMP 2 قد يكون ندًّا قويًا.

---

## 5. مصفوفة القرار (حكم هندسي، وليس benchmark)

**المعايير (0–5):**
- **ABC**: دعم ABC الأصلي.
- **Maqam**: التقاط السلّم/الجنس/المقام.
- **Motif**: التقاط الجملة اللحنية/الإيقاعية الحرفية.
- **Semantic**: الأسلوب/المزاج/التوزيع.
- **Arabic**: دعم النص العربي.
- **Evidence**: وجود دليل استرجاع منشور.
- **License**: ملاءمة الرخصة (5 = MIT/Apache).
- **CPU**: جدوى التشغيل بدون GPU.
- **Integration**: سهولة الدمج مع pipeline الحالي.

| النموذج | ABC | Maqam | Motif | Semantic | Arabic | Evidence | License | CPU | Integration | الحكم |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **CLaMP 3 C2** | 5 | 2 | 3 | 5 | 4 | 4 | 5 | 2 | 3 | **العمود الفقري الرمزي** |
| CLaMP 2 | 5 | 2 | 3 | 4 | 3 | 3 | 5 | 2 | 3 | بديل/مقارنة |
| M3 خام | 5 | 2 | 3 | 2 | 1 | 1 | 5 | 3 | 2 | backbone فقط، ليس retrieval |
| MusicBERT | 1 | 1 | 3 | 2 | 1 | 1 | 5 | 4 | 2 | يحتاج MIDI؛ ليس جاهزًا |
| MIDI-BERT | 1 | 1 | 3 | 2 | 1 | 1 | 2 | 4 | 2 | لا أنصح إنتاجيًا |
| MERT-v1-95M | 0 | 1 | 2 | 4 | 1 | 3 | 4 | 3 | 3 | طبقة صوت |
| MuQ-MuLan | 0 | 1 | 2 | 5 | 3 | 3 | 4 | 3 | 3 | صوت + نص |
| MusicFM | 0 | 1 | 2 | 4 | 1 | 2 | 5 | 3 | 3 | صوت برخصة مريحة |
| CLAP | 0 | 0 | 1 | 3 | 1 | 2 | 5 | 3 | 3 | إنجليزي/ضعيف |
| **Qwen3-Emb-0.6B** | 2 | 2 | 1 | 3 | 5 | 5 | 5 | 4 | 5 | **طبقة metadata/lyrics** |
| **BGE-M3** | 2 | 2 | 2 | 3 | 5 | 5 | 5 | 3 | 4 | **hybrid dense+sparse** |
| gte-multilingual-base | 2 | 2 | 1 | 3 | 5 | 4 | 5 | 4 | 4 | خفيف |
| e5-large-instruct | 2 | 2 | 1 | 3 | 4 | 4 | 5 | 3 | 4 | نصوص قصيرة |
| jina-v3 | 2 | 2 | 1 | 3 | 5 | 4 | 3 | 3 | 4 | NC |
| SheetSage2 | 5 | 1 | 1 | 0 | 0 | 1 | 4 | 3 | 3 | ingestion فقط |
| ABC LLM | 4 | 3 | 2 | 2 | 4 | 1 | 2 | 1 | 2 | synthesis فقط |

**القراءة:** لا يوجد صف واحد > 35. هذا طبيعي: المشكلة متعددة الإشارات.
القرار الصحيح هو **تركيب**، وليس اختيار نموذج واحد.

---

## 6. ماذا يعني هذا لمشروعنا تحديدًا؟

### 6.1 طبيعة الـ corpus
- `REF_ABC_SCORE_MAQAM.zip` = 40 سكور **مُولَّد/مُختار**، موزعة 6/9/19/6 على 4 مقامات.
  التسمية هنا هي **prompt** وليست ground truth موسيقية؛ لا تصلح وحدها كمجموعة تقييم.
- `datasets/five_stars/transcripts/` = 177 سكورًا مرجعيًا، مع:
  - صوت MP3،
  - `poem_slug` و `lyric_group_id` و `take` (مفيدة كـ true positives للثيم/القصيدة)،
  - `maqam` (49/43/43/42)،
  - `original_title`.
  هذا هو corpus التقييم الصحيح.
- سكورات `five_stars` فيها صوتان لحنيان (`Vocal` + `Ins`) **بدون chord symbols**،
  بينما سكورات `REF` فيها `Vocal` غالبًا = rests + chord symbols (وأحيانًا جملة غنائية) و`Ins` = melody.
  لذلك:
  - مقاييس الـ harmony في `abc_similarity.py` تعمل على `REF` ولا تعمل على `five_stars`.
  - على `five_stars` اعتمد على melody/rhythm/motif + audio.

### 6.2 ما نريد فهرسته (لكل سكور)
1. **score-level symbol vector** — CLaMP 3 C2 على interleaved ABC كامل.
2. **melody-only vector** — CLaMP 3 C2 على صوت `Ins`/اللحن فقط (بعد إزالة الـ rests).
3. **section-level vectors** — كل 8 أو 16 بارًا مع overlap (للاسترجاع الموضعي للـ motif).
4. **motif fingerprint** — interval 4-grams، rhythm 4-grams، chord transitions،
   scale-degree histogram بعد التطبيع على التونيك.
5. **metadata vector** — Qwen3/BGE-M3 على بطاقة نصية:
   `maqam, key, meter, tempo, sections, instrumentation, mood, lyrics theme`.
6. **lyrics vector** — نص عربي (اختياري لكنه مهم لـ «ثيم الكلمات»).
7. **audio vector** — MERT/MuQ على MP3 (اختياري).

### 6.3 لماذا multi-vector؟
لأن «الثيم» قد يكون:
- جملة لحنية متطابقة → motif index,
- نفس المقام/الجنس → scale-degree features,
- نفس المزاج/التوزيع → CLaMP/MERT,
- نفس القصيدة/الكلمات → lyrics vector,
- نفس التقسيم/الشكل → section vectors.
دمج هذه في متجه واحد يعني أن إحداها ستطغى على الأخرى.

---

## 7. التصميم المقترح (عملي)

### 7.1 Index schema (Qdrant / pgvector / LanceDB)

```json
{
  "id": "five_stars/<track_id>",
  "vectors": {
    "symbolic":  [0.0, "... 768"],
    "melody":    [0.0, "... 768"],
    "metadata":  [0.0, "... 1024"],
    "audio":     [0.0, "... 768"]
  },
  "payload": {
    "maqam": "Hijaz",
    "key": "Fm",
    "meter": "4/4",
    "tempo": 128,
    "n_bars": 120,
    "sections": ["intro","verse","chorus","outro"],
    "chords": ["Fm","Bbm","C7"],
    "poem_slug": "...",
    "lyric_group_id": "...",
    "take": "SONG_B",
    "duration_s": 240,
    "source": "five_stars",
    "abc_path": "datasets/five_stars/transcripts/<id>.abc",
    "audio_path": "datasets/five_stars/audio/<maqam>/<id>.mp3"
  },
  "motifs": {
    "interval_4grams": ["+2,+1,-3,+2", "..."],
    "rhythm_4grams":   ["1,0.5,0.5,2", "..."],
    "chord_4grams":    ["Fm,Bbm,C7,Fm", "..."]
  }
}
```

### 7.2 خط الأنابيب

```python
# ---------- offline: build index ----------
for score in corpus_177:
    abc = read(score)
    abc_i = to_interleaved(abc)            # CLaMP requires interleaved
    v_sym = clamp3_c2.encode(abc_i)        # 768, normalize
    v_mel = clamp3_c2.encode(melody_only(abc_i))
    v_meta = qwen3.encode(score_card(score))   # 1024
    motifs = motif_fingerprint(abc)        # sets of n-grams
    sections = window_vectors(abc_i, bars=16, hop=8)
    index.upsert(...)

# ---------- online: query ----------
def query(track_abc=None, text=None, audio=None, top_k=50):
    pools = []
    if track_abc:
        q_i = to_interleaved(track_abc)
        pools.append(index.search("symbolic", clamp3_c2.encode(q_i), k=top_k))
        pools.append(index.search("melody",   clamp3_c2.encode(melody_only(q_i)), k=top_k))
        pools.append(bm25.search(track_abc, k=top_k))
        pools.append(motif_index.search(motif_fingerprint(track_abc), k=top_k))
    if text:
        pools.append(index.search("metadata", qwen3.encode(text), k=top_k))
        pools.append(bm25_text.search(text, k=top_k))
    if audio:
        pools.append(index.search("audio", mert.encode(audio), k=top_k))

    cand = rrf(pools)                      # Reciprocal Rank Fusion
    return ltr_rerank(cand, features=[
        "cos_symbolic", "cos_melody", "cos_metadata", "cos_audio",
        "interval_4gram_f1", "rhythm_4gram_f1", "chord_transition_f1",
        "scale_degree_cos", "same_maqam", "same_key", "tempo_ratio",
        "duration_ratio", "section_overlap"
    ])
```

### 7.3 الأوزان المقترحة للـ fusion (بداية، ثم تعلّمها)
| الإشارة | الوزن المبدئي | لماذا |
|---|:--:|---|
| CLaMP3 C2 symbolic | 0.30 | أفضل دلالي/أسلوبي |
| motif n-gram F1 | 0.25 | «الثيم» الحرفي |
| scale-degree/maqam | 0.15 | المقام |
| BM25/char n-gram | 0.10 | تطابق حرفي/أسماء |
| metadata (Qwen3) | 0.10 | وصف/كلمات |
| audio (MERT) | 0.10 | الصوت الفعلي |
هذه أوزان بداية فقط؛ يجب تعلمها من أزواج موسومة (LambdaRank/GBDT).

---

## 8. خطة التقييم على 177 سكورًا (بدل 40)

### 8.1 المهام

| المهمة | الاستعلام | الموجب | السلب الصعب |
|---|---|---|---|
| **T1: maqam retrieval** | track ABC | نفس `maqam` | نفس الـ key/tempo لكن مقام مختلف |
| **T2: same poem** | track ABC | نفس `poem_slug` أو `lyric_group_id` | نفس المقام لكن قصيدة مختلفة |
| **T3: same song / take** | track ABC | نفس `original_title` | عنوان/قصيدة مختلفة |
| **T4: text→ABC** | lyrics أو description | السكور المرتبط | نفس المقام، كلمات مختلفة |
| **T5: audio→ABC** | MP3 | السكور المرتبط | نفس المقام، صوت مختلف |

### 8.2 المقاييس
- **Recall@1/5/10**، **MRR**، **nDCG@10**.
- **Silhouette** على المقام (للتحقق من عدم انهيار التمثيل).
- **Linear probe** (logistic regression) على المقام، مع split بحسب `poem_slug`
  لمنع التسريب.
- **Baseline العشوائي** لـ T1: `Σ p_i² = (49²+43²+43²+42²)/177² ≈ 0.251`.
  أي hit@1 ≤ 0.25 لا يعني شيئًا.
- **Human eval** لـ 50 زوجًا: «هل يشتركان في ثيم؟» 1–5، مع 3 مستمعين.

### 8.3 Baselines التي يجب تشغيلها
1. BM25 على ABC الخام.
2. `abc_similarity.py` composite (17 مقياسًا).
3. motif-only (interval/rhythm n-grams).
4. CLaMP 3 C2 symbolic فقط.
5. Qwen3/BGE-M3 على metadata فقط.
6. fusion (المقترح).
7. (اختياري) MERT audio فقط.

**لا تحكم على نموذج من رقم واحد.** قارن كل واحد مقابل هذه الـ baselines.

---

## 9. التشغيل بدون GPU (واقع هذه الآلة)

| الخيار | CPU | الملاحظات |
|---|---|---|
| BM25 + motif features + `abc_similarity.py` | ✅ سريع | يعمل اليوم على 177 سكورًا في ثوانٍ. |
| Qwen3-Embedding-0.6B (TEI CPU) | ✅ | 0.6B؛ مناسب للـ metadata/lyrics. |
| BGE-M3 (dense/sparse) | ⚠️ | يعمل لكن أبطأ؛ 568M. |
| gte-multilingual-base | ✅ | 305M؛ أفضل نسبة جودة/كلفة على CPU. |
| CLaMP 3 C2 | ⚠️ | 2.5GB؛ يعمل على CPU لكن ~عشرات الثواني لكل سكور، وليس تفاعليًا. |
| CLaMP 2 | ⚠️ | 4.45GB؛ أثقل. |
| MERT/MuQ | ⚠️ | ممكن على CPU لكن بطيء؛ الأفضل GPU. |
| SheetSage2 | ⚠️ | تحويل صوت→ABC؛ GPU مفضل. |

**الخطة العملية بدون GPU:**
1. ابنِ الفهرس على Colab (L4/T4) مرة واحدة — أنت أصلًا تستخدم `setup_colab.sh`.
2. خزّن المتجهات + payload في Qdrant/LanceDB/pgvector.
3. على هذه الآلة: استخدم Qwen3/BGE-M3 + BM25 + motif للاستعلام السريع.
4. إذا احتجت CLaMP3 C2 تفاعليًا: HF Inference Endpoint أو Space، أو precompute.

**تنبيه:** `gorse-io/CLaMP3-SAAS-GGUF` هو نسخة **SAAS (صوت)** وليس `C2` الرمزي،
ورخصته CC-BY-NC-4.0. لا تعتبره بديلًا CPU لـ ABC symbolic.

---

## 10. المخاطر والقيود

| الخطر | الأثر | التخفيف |
|---|---|---|
| Domain shift: لا تدريب على maqam عربي | التمثيل قد يخلط المقامات | scale-degree features + linear probe + human eval |
| Anisotropy: cosine مرتفع بين كل السكورات | «كل شيء يشبه كل شيء» | center/whiten، أو استخدم المسافة من المتوسط، أو rerank |
| Interleaved ABC غير مطبّق | CLaMP يعمل تحت قدرته | preprocessing إلزامي + اختبار A/B |
| سكورات > 512 بار | اقتطاع | chunk + تجميع مرجح |
| أرباع الصوت/الزخارف | فقدان تفاصيل | حوّل إلى MIDI/cents، أو أضف features خام |
| التسميات في `REF` هي prompts | تقييم مضلل | استخدم `five_stars` كـ gold |
| 177 ملفًا فقط | overfitting | group split بحسب `poem_slug`، وhuman eval |
| رخص NC | لا مشكلة الآن (المشروع CC-BY-NC) | وثّق كل رخصة عند النشر |
| Text embedders لا تفهم ABC | تشابه سطحي | لا تعتمد عليها وحدها |

---

## 11. التوصية النهائية

### Tier 0 — اليوم، بدون GPU (ابدأ هنا)
- **BM25/char n-grams** على ABC.
- **`abc_similarity.py`** (17 مقياسًا) كـ feature vector.
- **motif fingerprints** (interval/rhythm n-grams) + فهرس مقلوب.
- **Qwen3-Embedding-0.6B** أو **gte-multilingual-base** على بطاقة السكور + الكلمات.
- النتيجة: نظام استرجاع hybrid يعمل فورًا، وقابل للقياس.

### Tier 1 — الأفضل جودة (يحتاج GPU للفهرسة)
- **CLaMP 3 C2** كـ symbolic backbone (768-dim).
- **BGE-M3** dense+sparse للـ metadata/lyrics.
- **fusion + reranker** (GBDT/MLP على 17 مقياسًا + cosine).
- فهرسة على Colab، استعلام على CPU أو endpoint.

### Tier 2 — إذا أردت «يشبه من حيث الصوت»
- **MERT-v1-95M** أو **MuQ-large** أو **MusicFM** (رخصة مريحة).
- **CLaMP 3 SAAS** للـ cross-modal audio↔ABC.
- أضف audio vector كإشارة رابعة في الـ fusion.

### لا أنصح به
- **SheetSage2** للاسترجاع (استخدمه للتحويل فقط).
- **M3 الخام** كـ retrieval encoder (بدون projection).
- **LLM مولّد ABC** كـ embedder.
- **text embedder وحده** لـ «الثيمات».
- **jina-v3** إذا كانت رخصة NC مشكلة في سياقك (رغم أن المشروع NC أصلًا).
- **MIDI-BERT** برخصة غير واضحة.

---

## 12. الخطوات التالية (أسبوع واحد)

1. **Canonicalizer**: `abc → interleaved ABC` + melody-only + section windows.
2. **Index 177** في Qdrant/LanceDB باستخدام Tier 0 (بدون GPU).
3. **شغّل الـ 7 baselines** في §8.3، وسجّل Recall@1/5/10 وMRR وnDCG.
4. **اختر** أفضل إشارتين/ثلاث للإشارة، ثم أضف CLaMP3 C2 على Colab.
5. **Human eval** على 50 زوجًا (ثيم مشترك؟) لضبط الأوزان.
6. **وثّق** الرخص والأحجام في `docs/plans/` قبل أي نشر.

---

## 13. Appendix — فحص أولي على 40 ملفًا (CPU، ليس benchmark)

> هذا فحص feasibility فقط، وليس حكمًا على CLaMP 3 C2. أُجري قبل قرار «عدم تشغيل النماذج».

**البيانات:** 40 سكورًا، Ajam 6 / Hijaz 9 / Kurd 19 / Nahawand 6.
**Baseline العشوائي لـ hit@1:** `Σ p_i² ≈ 0.34`.

| الطريقة | hit@1 | hit@3 | MRR | within−between cosine gap |
|---|---:|---:|---:|---:|
| `abc_similarity.py` composite | 0.45 | 0.68 | 0.60 | — |
| M3 الخام (mean pooling) | 0.475 | 0.75 | 0.652 | **0.001** |
| M3 الخام (max pooling) | 0.375 | 0.625 | 0.546 | 0.000 |
| interval-hist (mod 12) | 0.475 | 0.675 | 0.626 | 0.010 |
| pitch-class hist + best rotation | 0.45 | 0.725 | 0.617 | — |

**التفسير:**
- الأرقام فوق العشوائي قليلًا، لكن **gap ≈ 0.001** يعني أن M3 الخام لا يفصل المقامات؛
  التمثيل مضغوط في اتجاه مشترك (anisotropy).
- `abc_similarity.py` وinterval-hist أفضل قليلًا، لأنها تقيس المحتوى اللحني مباشرة.
- هذا يدعم الاستنتاج: **M3 الخام ليس encoder استرجاع**؛ استخدم CLaMP 3 C2 projection.
- التسميات نفسها (prompt-derived) قد تكون مشوشة، لذا لا تبنِ قرارًا على 40 ملفًا.

---

## 14. حالة الاستخدام المحددة: 400 سكور، استعلام أغنية كاملة أو مقطع

**السؤال:** لدي 400 سكور ABC. أريد عند الطلب: (أ) أكثر 5 أغاني تشبه أغنية X في
اللحن والمزاج، (ب) أكثر 5 أغاني تشبه مقطعًا (interlude) من أغنية X.
**الجواب المختصر:** **CLaMP 3 C2 — البرج الرمزي فقط**، مع طبقة motif خفيفة
وتمثيل منفصل للحن. لا تحتاج vector DB ولا ANN عند 400 سكور.

### 14.1 لماذا CLaMP 3 C2 تحديدًا؟

| السبب | التفصيل |
|---|---|
| ABC أصلي | يتعامل مع interleaved ABC مباشرة؛ لا حاجة لتحويل MIDI/صوت. |
| 768-dim | متجه عالمي مضغوط، مناسب للاسترجاع الدقيق. |
| تدريب contrastive مع النص | يلتقط «المزاج/الأسلوب» ضمنيًا، وليس فقط النغمة. |
| الحجم الفعلي صغير | `symbolic_model` + `symbolic_proj` = **93M params (~370MB fp32)** فقط من checkpoint 2.5GB. |
| MIT | متوافق مع المشروع. |
| دليل | MRR 0.3155 على ABC عربي (أعلى من CLaMP 2: 0.2298). |

**لا تُحمّل النموذج الكامل.** من `weights_clamp3_c2...pth` خذ فقط:

```python
ck = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
sym  = {k[len("symbolic_model."):]: v for k, v in ck["model"].items()
        if k.startswith("symbolic_model.")}
proj = {k[len("symbolic_proj."):]: v for k, v in ck["model"].items()
        if k.startswith("symbolic_proj.")}
# build M3PatchEncoder(BertConfig(...)) + Linear(768, 768), load, eval
```

هذا يقلل الذاكرة من 2.5GB إلى ~370MB، ويجعل التحميل والاستدلال على CPU عمليًا.

### 14.2 الفهرس المطلوب (400 سكور)

| الطبقة | العدد التقريبي | الأبعاد | الحجم | الغرض |
|---|---:|---:|---:|---|
| score-level (full) | 400 | 768 | ~1.2 MB | مزاج/أسلوب عام |
| score-level (melody-only) | 400 | 768 | ~1.2 MB | تشابه اللحن |
| section-level | 2,400 (≈6/سكور) | 768 | ~7.4 MB | استعلام مقطع / interlude |
| motif sets | 2,400 | — | ~صغير | تطابق الثيم الحرفي |
| metadata/lyrics (اختياري) | 400 | 1024 | ~1.6 MB | استعلام نصي |

**الخلاصة:** كل الفهرس < 15 MB. `numpy.argsort` أو `faiss.IndexFlatIP` يكفي؛
البحث < 10ms. لا حاجة إلى Qdrant/pgvector/HNSW.

### 14.3 خط الأنابيب

```python
# ---------- offline (مرة واحدة) ----------
for s in songs_400:
    abc   = read(s)
    inter = to_interleaved(abc)
    full  = enc(inter)                    # 768
    mel   = enc(melody_only(inter))       # 768
    secs  = split_sections(inter)         # % intro / verse / chorus / interlude
    vsec  = [(enc(sec), meta) for sec in secs]
    motifs = motif_fingerprint(abc)
    store(full, mel, vsec, motifs)

# ---------- query: full song ----------
q_full = enc(to_interleaved(q))
q_mel  = enc(melody_only(to_interleaved(q)))
scores = 0.45*cos(q_full, FULL) + 0.45*cos(q_mel, MEL) + 0.10*motif_overlap(q, CORPUS)
top5   = argsort(scores)[-5:]

# ---------- query: segment (interlude) ----------
q_seg = enc(segment_abc)
seg_hits = search(vsec_index, q_seg, k=50)      # section-level
# aggregate to songs: max أو mean لأفضل مقطعين لكل أغنية
song_scores = aggregate_by_song(seg_hits, top_n=2)
top5 = argsort(song_scores)[-5:]
```

**لماذا 0.45/0.45/0.10؟** لأن طلبك «اللحن والمزاج» بالتساوي تقريبًا، والـ motif
كعامل ترجيح صغير. عدّلها بعد التقييم على 177/400.

### 14.4 الاستعلام بمقطع (segment query)

- إذا كان المقطع معروف الحدود (interlude/verse/chorus) → استخدمه كوحدة section.
- إذا كان مقطعًا حرًا → خذ نافذة 16 بارًا مع overlap 8 بارات، أو 8 بارات إذا كان قصيرًا.
- ابحث في **section-level index**، ثم اجمع النتائج لكل أغنية:
  `score(song) = max_i cos(q, section_i)` أو متوسط أفضل مقطعين.
- لا تخلط section vectors مع full-score vectors في نفس الفهرس؛ استخدم named vectors.
- للتحقق النهائي من أعلى 50 مرشحًا: أضف DTW/interval-4gram F1 (رخيص على 50 فقط).

### 14.5 السرعة المتوقعة (تقديرية — تحتاج قياسًا)

| الخطوة | CPU (هذه الآلة) | GPU (Colab) |
|---|---|---|
| تحميل البرج الرمزي | ~1–3 ثوانٍ | ~1 ثانية |
| embedding سكور كامل | ~0.3–1.5 ثانية | ~20–50 ms |
| embedding مقطع | ~0.1–0.5 ثانية | ~10–20 ms |
| بحث في 400/2,400 متجهًا | < 10 ms | < 1 ms |
| **إجمالي استعلام** | **~0.5–2 ثانية** | **~50–100 ms** |

الفهرسة الكاملة (400 سكور + 2,400 section) على CPU: **~10–30 دقيقة** تقديريًا،
وعلى GPU: **دقائق**. لذلك «الاسترجاع السريع عند الطلب» يتحقق دون GPU:
احسب مرة واحدة، واحفظ المتجهات.

### 14.6 لماذا ليس نموذجًا آخر؟

| البديل | لماذا لا يكون الأساس |
|---|---|
| CLaMP 2 | أضعف في الاسترجاع؛ checkpoint 4.45GB؛ M3 وحده ليس retrieval-trained. |
| Text embedder (Qwen3/BGE-M3) | لا يرى اللحن؛ يرى وصفًا مولّدًا فقط. يصلح للاستعلام النصي/metadata. |
| MERT/MuQ | يحتاج صوتًا؛ سكور ABC ليس صوتًا. يتطلب render (fluidsynth) ويضيف كلفة. |
| MusicBERT/MIDI-BERT | يحتاج ABC→MIDI؛ ليس retrieval-trained؛ رخصة MIDI-BERT غير واضحة. |
| SheetSage2 | تحويل صوت→ABC فقط. |
| ABC LLM | توليد، ليس embedding. |

### 14.7 «المزاج» تحديدًا

CLaMP 3 C2 يلتقط المزاج ضمنيًا من التدريب النصي. لتحسينه:

1. **إن وُجدت تسميات mood** (ولو 177 سكورًا): درّب linear probe / logistic regression
   على متجهات CLaMP3 — رخيص جدًا (ثوانٍ) وغالبًا أفضل من zero-shot.
2. **بدون تسميات:** حمّل برج النص أيضًا (`text_model` + `text_proj`، ~278M إضافية)،
   وابنِ بنك عبارات مزاج عربية/إنجليزية («طربي»، «حزين»، «حماسي»، «هادئ»، «غامض»،
   «ملحمي»، «حنين»)، ثم cosine بين متجه السكور ومتجهات العبارات → mood tags.
3. **لا تجعل mood مرشحًا صلبًا (hard filter) في البداية** — استخدمه كإشارة ترجيح،
   لأن التسميات العربية غير موثوقة وقد تقصي نتائج جيدة.

### 14.8 التوصية النهائية لهذه الحالة

> **CLaMP 3 C2 (symbolic tower only) + melody-only vector + section-level index +
> motif n-grams + cosine/FAISS flat.** أضف Qwen3/BGE-M3 فقط إذا أردت الاستعلام
> بالنص أو الكلمات. لا تستخدم vector DB معقدًا عند 400 سكور.

---

## 15. المراجع السريعة

- CLaMP 3: [HF](https://huggingface.co/sander-wood/clamp3) · [GitHub](https://github.com/sanderwood/clamp3) · [Paper](https://arxiv.org/abs/2502.10362)
- CLaMP 2: [HF](https://huggingface.co/sander-wood/clamp2) · [GitHub](https://github.com/sanderwood/clamp2) · [Paper](https://arxiv.org/abs/2410.13267)
- CLaMP 1: [HF](https://huggingface.co/sander-wood/clamp-small-1024) · [Paper](https://arxiv.org/abs/2304.11029)
- MERT: [HF](https://huggingface.co/m-a-p/MERT-v1-95M) · [Paper](https://arxiv.org/abs/2306.00107)
- MuQ: [HF](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter)
- MusicFM: [HF](https://huggingface.co/tky823/MusicFM)
- Qwen3-Embedding: [HF](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- BGE-M3: [HF](https://huggingface.co/BAAI/bge-m3)
- gte-multilingual: [HF](https://huggingface.co/Alibaba-NLP/gte-multilingual-base)
- Datasets: [M4-RAG](https://huggingface.co/datasets/sander-wood/m4-rag) · [WikiMT-X](https://huggingface.co/datasets/sander-wood/wikimt-x) · [WikiMusicText](https://huggingface.co/datasets/sander-wood/wikimusictext) · [The Session ABC](https://huggingface.co/datasets/uetchy/thesession)
