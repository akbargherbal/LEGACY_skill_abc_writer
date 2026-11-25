# OpenCode skill loading — ملاحظة harness (خارج خطة المهارة)

**التاريخ:** 2026-11-25
**الغرض:** تسجيل سبب فشل تحميل المهارة في 07/08/09، والفصل بينه وبين
عيب المهارة أو النموذج. هذه ملاحظة إعداد/تشغيل، لا تغيير في المهارة.

---

## 1. الخطأ ليس في المهارة ولا في `skill` tool

OpenCode يكتشف المهارات من مسارات محددة فقط:

| النطاق | المسار |
|---|---|
| Global | `~/.config/opencode/skills` |
| Global compatibility | `~/.claude/skills`، `~/.agents/skills` |
| Project | `.opencode/skills` |
| Project compatibility | `.claude/skills`، `.agents/skills` |
| Config | `skills` array في `opencode.json(c)` |

المهارة في الجلسات كانت في:

```text
agent/skills/abc-score-writer/SKILL.md
```

وهذا **ليس** مسار اكتشاف. لذلك `skill({id:"abc-score-writer"})` فشل.

التوثيق: <https://opencode.ai/docs/skills>

---

## 2. `@` و`/` ليسا تثبيتًا

| ما كُتب | ما هو | ما حدث |
|---|---|---|
| `@skills/abc-score-writer/` (07/08) | إرفاق مجلد بالرسالة | الوكيل قرأ `SKILL.md` يدويًا؛ `skill` tool فشل |
| `/abc-score-writer` (09) | نص/أمر، ليس تحميل مهارة | لا إرفاق؛ الوكيل بحث في الأب وقرأ `README`/`BRIEF`/`checklist` |
| `@abc-score-writer` | Mention للمهارة (بعد الاكتشاف) | لم يُستخدم |
| `skill({id:"abc-score-writer"})` | التحميل الرسمي | فشل لأن المهارة غير مكتشفة |

**الخلاصة:** في 07 و08 و09، أول نداء `skill` فشل. الـ`@` في 08 لم ينجح؛
فقط جعل ملفات المهارة متاحة للقراءة. الـ`/` في 09 كان أسوأ لأنه لم يُرفق
شيئًا، فبحث الوكيل ووجد ملفات التحليل.

---

## 3. التثبيت الصحيح

```bash
cd /content/session-09/agent
mkdir -p ~/.config/opencode/skills
ln -sfn "$PWD/skills/abc-score-writer" \
  ~/.config/opencode/skills/abc-score-writer

test -f ~/.config/opencode/skills/abc-score-writer/SKILL.md \
  && echo "skill discoverable"
readlink -f ~/.config/opencode/skills/abc-score-writer
```

ثم ابدأ OpenCode من `agent/`، لا من الأب.

بديل project-local:

```bash
cd /content/session-09/agent
mkdir -p .opencode/skills
ln -sfn "$PWD/skills/abc-score-writer" \
  .opencode/skills/abc-score-writer
```

أو في `agent/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["./skills"]
}
```

بعد التثبيت، استخدم واحدًا من:

```text
Load the `abc-score-writer` skill with the `skill` tool.
If it fails, stop and report the error. Do not read SKILL.md manually.
```

أو Mention:

```text
@abc-score-writer
```

**لا** تستخدم `@skills/abc-score-writer/` ولا `/abc-score-writer`.

---

## 4. ماذا يترتب على الفشل من المرة الأولى؟

1. **الجلسة غير صالحة.** شرط A في الـbrief يفشل. لا يمكن نسب النتيجة إلى
   المهارة أو الخطة.
2. **المحتوى ناقص.** القراءة اليدوية لا تعطي base directory، ولا قائمة
   الملفات الداعمة، ولا وصف المهارة/صلاحياتها كما يراها النموذج.
3. **التلوث.** في 09 قرأ الوكيل `README` و`SESSION-09-BRIEF` و`checklist`
   لأنه كان يبحث. هذا أعطاه مفتاح الإجابة وأسباب فشل 08.
4. **الكلفة.** 09: **5,606 توكنز** و8 رسائل قبل نجاح المهارة (1–8)، ثم
   قراءة ملفات التحليل. 08: فشل أيضًا، لكن الأثر أقل لأن الـcwd كان نظيفًا.
5. **السلوك.** قد لا يلتزم الوكيل بقيود المهارة (لا parser، لا إعادة كتابة
   بسبب WARN) لأنه لم يستقبلها بالطريقة الرسمية.
6. **القياس.** التوكنز والزمن يشملان الإعداد، و«أول نداء skill» و«الغرفة
   النظيفة» يفشلان. لا يصح مقارنة الجلسات إذا تكرر.

**القاعدة:** إذا فشل أول نداء `skill`، توقف. أصلح التثبيت. ابدأ جلسة جديدة.
لا تسمح للوكيل بقراءة `SKILL.md` يدويًا ولا بالاستمرار في جلسة ملوثة.

---

## 5. هل هو عيب OpenCode؟

- **وظيفيًا: لا.** الاكتشاف والتحميل موثقان، والرسالة صحيحة.
- **تجربة استخدام: نعم، قابلة للتحسين.** الرسالة لا تفرّق بين «غير موجودة»
  و«غير مصرح بها»، ولا تقترح المسار، ولا تفرّق بين `@path` و`@skill-id`.
  هذا تحسين مشروع، لكنه ليس سبب الفشل.
- **السبب الأساسي عندنا:** لم يُنفَّذ symlink قبل الجلسة، وبدأنا من الأب،
  وسمحنا للوكيل بالاستمرار بعد فشل أول نداء. هذا عيب إعداد/بروتوكول، لا
  عيب المهارة.
