# أهدافي الأساسية

> **Reconstruct, don't patch.**
> أعد بناء العمل، لا تُرقّعه. اجعل كل قرار متماسكًا ومكتفيًا بذاته.

## 1. الهدفان، بالترتيب الصارم

### 1.1 الجودة أولًا: 9/10 أو أعلى

- الأذن هي الحكم النهائي. `checker` والبطاقة أدوات تشخيص وقياس، وليست بديلًا عن السمع.
- لا حكم موسيقي ولا درجة جودة بدون ملف صوتي مُستمع له. إن غاب الصوت، تبقى الجودة معلّقة ولا ندّعي نتيجة.
- لا أرضى بأقل من 9/10، ولا أعتبر أي درجة أدنى نهاية مقبولة.
- لا نقبل تراجعًا عن أفضل نتيجة سمعية موثقة؛ التحسين هو المسار الوحيد.
- لا جدوى اقتصادية على حساب أداء ركيك.

### 1.2 الجدوى: ≤10×

- السكور النهائي (`score.abc`) صغير، نحو 2,100–3,000 توكن.
- أي استهلاك يتجاوز 10 أضعاف حجم السكور في `output + reasoning` فشل منظومي.
- الرقابة على الميزانية يدوية من طرفي: أنا أراقب الجلسة وأنهيها إذا طالت. لا مراقبات آلية معقدة، ولا ضغط لتقليص الجودة مقابل التوكنز.
- الاقتصاد يُصلح بعدد القرارات، لا بتقليل التفكير: قرارات قليلة كبيرة أرخص من عشرات القرارات الصغيرة.
- 1–4 مسودات كاملة. إذا نجا نفس الخطأ الحرج بعد إعادتين كاملتين، نتوقف: المشكلة في النموذج أو المنهج، لا في عدد المسودات.
- لا ميكرو-إديت: لا كتابة سطرًا بسطر، ولا ترقيعًا بارًا بارًا. النزول البطيء لا يختصر الطريق؛ يجعلك لا ترى الجبل.

## 2. تقسيم العمل

- **النموذج يؤلف ويرندر السكور كاملًا.** النموذج اللغوي (LLM) أقوى في رؤية الأنماط والموتيفات والقوس العاطفي من رؤية نوتة واحدة.
- **بايثون يفحص ويمنع الهلوسة.** يجمع البارات، يتحقق من البنية، ويطبع الأرقام. لا يختار نوتة، ولا يوسّع وصفة، ولا يؤلف.
- **الأذن تحكم.** البطاقة تكشف الأخطاء؛ لا تحكم على الجمال.

## 3. طريقة العمل: مسودة كاملة، ثم إعادة بناء

```text
init -> draft (whole) -> scorecard -> rewrite (whole) -> scorecard
     -> polish seams -> release
```

- يكتب النموذج `score.abc` كاملًا (أو 2–3 مقاطع كبيرة) بعد `init`.
- لا `line` ولا `patch` ولا `core` ولا meter سطري في المسار الأساسي. لا سكربتات قياس أو تحليل يدوية.
- بعد كل مسودة تطبع البطاقة: KEY BANDS / BLOCKING / POLISH / SEAMS.
- الإصلاح إعادة كتابة كاملة (أو مقطع كامل)، لا patch. 1–4 مرات.
- الفكرة والوصلة هما وحدة العمل، لا السطر.
- `parse error` → أصلح جمع البارات أولًا؛ لا رقم آخر ذو معنى.
- `simultaneity` → السقف 4 وحدات إجمالًا، لا لكل بار.
- `repeated notes` → الحد 20%؛ التكرار يُصمم في الفكرة، لا يُرقّع في النهاية.

## 4. البطاقة ومعايير القبول

- البطاقة تقرأ أحكامها من `checker.py`. لا نخفض `checker.py` أو `calibration.json`، ولا نضيف بوابات ذوق.
- 0 blocking في النهاية.
- بلا micro-repair متأخر: لا تعديل بعد pass، ولا patch بعد مسودة كاملة.
- repeats ≥20%، register 69–79، simultaneity ≤4، 1–4 مسودات، ≤24 خطوة مستخدمة (سقف التشغيل شبكة أمان، لا هدف).
- ≤10× (أو ≤20× مع فحص نهائي ناجح، كمرحلة جزئية).
- الجودة: لا حكم بدون صوت؛ الهدف 9/10+.

## 5. كيف نقرأ الأخطاء

- لا ألوم كاتب السكور أو النموذج تلقائيًا. أسأل: لماذا فعل ذلك؟ كيف فسّر التعليمات؟ هل السبب في تعليماتنا أو أدواتنا أو بيئة التشغيل، أم في قدرة النموذج أو المنهج؟
- في المسودة الكاملة، الخطأ المتوقع عالمي (سجل، تكرار، تداخل، وصلات)، لا خطأ سطر. عالجه بإعادة كتابة، لا بترقيع.
- إذا تجاهل النموذج رقمًا مطبوعًا، اسأل أولًا: هل طبعت البطاقة الحد الأدنى والاتجاه؟ رقم بلا حد أدنى يُتجاهل، وهذا خلل عندنا.
- إذا كانت البطاقة واضحة والبيئة نظيفة وبعد 4 مسودات لم يصل: غيّر النموذج أو المنهج، ولا تزد التعليمات.
- كل تجربة تغيّر متغيرًا واحدًا فقط، في بيئة نظيفة، وعلى نفس النموذج، حتى تُعرف السببية. لا تغيير في النموذج أو البرومبت أو الخطوات في منتصف الجلسة.
- إذا تحققت الجدوى دون تراجع سمعي: ننتقل إلى رفع الجودة. إذا تراجعت الجودة: فشل. إذا كانت البيئة نظيفة والتعليمات واضحة ومع ذلك عجز الكاتب: نعدّل المنهج أو النموذج.

## 6. ثوابت لا تُمس

- لا بوابات للذوق، ولا جعل الأرقام هدفًا. أهداف الشكل تبقى `WARN` تشخيصية.
- لا ادعاء بلا فحص: كل رقم أو استنتاج مثبت من السجل والمخرجات الفعلية.
- الوضوح والبساطة: تشخيص مباشر بالأرقام والأسباب وخطوة الإصلاح التالية، لا تقارير طويلة.
- لا ميكرو-إديت: لا سطرًا بسطر، ولا patch بارًا بارًا. الإصلاح مسودة كاملة.
- لا بايثون كمؤلف.
- لا حكم بلا سمع.

## 7. أين تُصرف ميزانية التفكير

- تُصرف على: الشكل، الموتيفات، قوس التسجيل، الكادنس، الوصلات، التوتر/الانفراج، واختيار ما يُحذف.
- لا تُصرف على: جمع البارات، إعادة قراءة المتر، محاذاة السطور، كتابة سكربتات مؤقتة، أو فك ألغاز الأدوات.
- 10,000 توكن يجب أن ترفع السكور درجة موسيقية، لا أن تصلح خطأ أداة.

## 8. المعيار الحاكم

- الأذن تحكم، والبطاقة تحرس، وبايثون يمنع الهلوسة.
- النموذج يؤلف الكل، والإنسان يقرر متى نتوقف.
- إن تعارضت السرعة مع الجودة، فالجودة أولًا. وإن تعارضت الجودة مع الجدوى، نغيّر المنهج لا المعيار.

---

# Thesis: Fast Whole-Draft Rendering with Guardrails and Seam Polishing

## 1. The Core Premise

Creating a small musical score (~3,000 characters/tokens) should be fast, coherent, and musically driven. When a workflow forces an LLM to write and verify millimeter by millimeter—agonizing over, checking, and rewriting each tiny fragment before the whole piece exists—it burns massive compute (100×+ overhead) while blinding the model to the overall musical arc.

Instead of crawling down the mountain in millimeter steps to find the "perfect" path up front, **descend fast**: produce the full draft quickly, see the whole terrain, and steer to the right destination through a few decisive revision passes.

---

## 2. Division of Labor: Pattern Recognition vs. Hallucination Control

Each part of the system should do only what it is naturally built for:

- **The LLM is the Composer (Pattern Recognition):**  
  Large language models excel at recognizing, planning, and rendering large-scale patterns, motifs, phrasing, and emotional arcs. Writing 3,000 characters of music is trivial for an LLM—it must be given the freedom to draw, plan, and render the entire piece using its pattern-recognition strength.
- **Code (Python) is the Guardrail (Anti-Hallucination Firewall):**  
  LLMs hallucinate—they miscount beats, break syntax, or drift outside declared constraints. Deterministic scripts exist strictly to catch those hallucinations and verify objective structural rules. **Code never composes, selects notes, or expands templates into music** (writing music with rules and dictionaries is as misguided as trying to write a novel with an English dictionary and a grammar script).
- **The Ear is the Final Judge:**  
  Automated metrics and checkers are diagnostic tools—like a map or a level—not the definition of good music. They catch errors; they do not judge beauty, and they never replace listening to audio.

---

## 3. The Mental Model: "Render and Polish," Not Character-by-Character Typing

Think of composing not as linear next-token typing, but as rendering a cohesive scene made of connected musical ideas (_Idea 1, Idea 2, Idea 3 … Idea N_):

1. **Draft Whole, Under Clear Criteria:**  
   Provide the lyrics, style, and hard constraints, then let the LLM plan and write the complete score in one flow (or a couple of large sections). Do not stop to micro-edit single notes or lines ten times while the rest of the song doesn't exist yet.
2. **Check Globally for Hallucinations:**  
   Run deterministic validation on the complete draft to surface objective errors (bar math, syntax, hard structural violations).
3. **Polish and Repair Ideas & Joints (1–4 Passes):**  
   Review the full piece for flow, coherence, anomalies, and dissonance so that every section transitions seamlessly:
   - If **Idea 3** is weak or broken, fix **Idea 3**.
   - If changing **Idea 3** loosens the transition ("joint") into **Idea 4**, adjust and tighten that joint.
   - Keep revisions decisive and bounded (1 to 4 passes), rather than endless micro-patching.
4. **Judge by Listening:**  
   Once the draft is structurally sound and seamlessly joined, render the audio and evaluate musical quality with the ear.

---

## 4. Non-Negotiable Principles

- **Write first, refine second:** A fast, complete, imperfect draft beats a slow, fragmented, over-checked partial draft.
- **Spend thinking on art, not arithmetic:** LLM reasoning should go into musical taste, motif development, tension/release, and seamless transitions—never into counting units or working around brittle micro-steps.
- **Never let code write the art:** Automation verifies constraints and catches hallucinations; it never replaces the creative act.
- **Bounded iteration:** Fix defects decisively in a handful of passes; never fall into an infinite micro-editing loop.
- **Economics follow granularity:** Token efficiency comes naturally from making a small number of whole-piece creative decisions rather than dozens of fragmented local guesses.
