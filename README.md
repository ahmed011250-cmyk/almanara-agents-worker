# 🤖 almanara-agents-worker — فريق الذكاء

الـ worker بتاع «فريق الذكاء» في «المنارة». «المنارة» بتصحّيه لما أحمد يبعت هدف أو في مواعيد الفريق (من إعدادات فريق الذكاء).
بياخد المهام بتوكن مؤقت، يكلّم مزوّد مجاني، ويرجّع الرد. التعليمات والقرارات كلها في «المنارة» (`app/team_ai.py`).

## المفاتيح (Settings ← Secrets and variables ← Actions ← Secrets)
طابور الشغل العام، من الأهم: Gemini ← Groq ← Mistral ← Cerebras ← Z.ai ← Cloudflare ← NVIDIA ← OpenRouter.
`GEMINI_API_KEY` · `GROQ_API_KEY` · `MISTRAL_API_KEY` · `CEREBRAS_API_KEY` · `ZAI_API_KEY` · `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` · `NVIDIA_API_KEY` · `OPENROUTER_API_KEY`
أي واحد مش متحط بيتساب. الترتيب يتغيّر من Variable اسمها `LANE_PUBLIC` (مثلاً `groq,gemini,mistral`).
🔒 بيانات العملاء/الموظفين: Groq ← Cerebras بس، ومابيتغيّرش.

## الموديلات (اختياري — Variables)
`GROQ_MODELS` · `CEREBRAS_MODELS` · `NVIDIA_MODELS` · `GEMINI_MODELS` · `OPENROUTER_MODELS` · `MISTRAL_MODELS` · `ZAI_MODELS` · `CLOUDFLARE_MODELS` (مفصولة بفاصلة).

## الأمان
- بيانات عملاء/موظفين ← Groq وCerebras بس. فعّل **Zero Data Retention** من إعدادات Groq.
- اللوج مابيطبعش أي كلام اتبعت أو رد.

## 🚨 إنذار الوقوع (`uptime.yml` كل ٥ دقايق)
بيجرّب `https://team.almanara.info/healthz/db` (بيكلّم القاعدة فعلاً). وقع ← Issue + رسالة تيليجرام، رجع ← يقفلها ويبعت «رجع».
Secrets: `ALERT_TG_TOKEN` (توكن بوت تيليجرام) · `ALERT_TG_CHAT` (رقم الشات بتاعك). Variables (اختياري): `UPTIME_URLS` (لينكات بفاصلة) · `SLOW_MS`.

## 🎙️ تجربة صوت Habibi (`habibi.yml` بالإيد)
Actions ← «تجربة صوت Habibi» ← Run workflow. السعودي (تجربة شخصية بس — رخصته غير تجارية) أو المصري (Apache 2.0 — تجاري مسموح). الصوت بيطلع في Artifacts.
