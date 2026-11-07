# 🤖 almanara-agents-worker — فريق الذكاء

الـ worker بتاع «فريق الذكاء» في «المنارة». «المنارة» بتصحّيه بس لما أحمد يبعت هدف (مفيش مواعيد ثابتة).
بياخد المهام بتوكن مؤقت، يكلّم مزوّد مجاني، ويرجّع الرد. التعليمات والقرارات كلها في «المنارة» (`app/team_ai.py`).

## المفاتيح (Settings ← Secrets and variables ← Actions ← Secrets)
`GROQ_API_KEY` · `CEREBRAS_API_KEY` · `NVIDIA_API_KEY` · `GEMINI_API_KEY` · `OPENROUTER_API_KEY` — أي واحد مش متحط بيتساب.

## الموديلات (اختياري — Variables)
`GROQ_MODELS` · `CEREBRAS_MODELS` · `NVIDIA_MODELS` · `GEMINI_MODELS` · `OPENROUTER_MODELS` (مفصولة بفاصلة).

## الأمان
- بيانات عملاء/موظفين ← Groq وCerebras بس. فعّل **Zero Data Retention** من إعدادات Groq.
- اللوج مابيطبعش أي كلام اتبعت أو رد.
