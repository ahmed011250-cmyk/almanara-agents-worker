"""🤖 فريق الذكاء — الـ worker (أحمد، ٧ نوفمبر ٢٠٢٦).

بياخد المهمة من «المنارة» (GET /lab/team-ai/api/<goal>/next بتوكن التشغيل)، يكلّم أول مزوّد مجاني شغّال، ويرجّع الرد
(POST .../result/<task>). «المنارة» هي اللي بتقرر الخطوة اللي بعدها؛ هنا مفيش أي منطق ولا تعليمات — بس «كلّم الموديل».

الطرق:
- public (كلام أسهم وترند): Groq ← Cerebras ← NVIDIA ← Gemini ← OpenRouter
- private (أي بيانات عملاء/موظفين، حتى بعد الإخفاء): Groq ← Cerebras بس (مابيحتفظوش بالبيانات)
429 حد الدقيقة ← نستنى ثواني ونعيد. الحد اليومي لكل المزوّدين ← {"limit": true} والمهمة تستنى بكرة. مفيش أي API مدفوع.
مكتبة بايثون العادية بس (من غير pip) عشان التشغيل يخلص في ثواني ويوفّر دقايق GitHub.
اللوج: رقم المهمة والوكيل والمزوّد والوقت بس — عمره ما بيطبع الكلام اللي اتبعت أو الرد.
"""
from __future__ import annotations

import json
import re
import os
import time
import urllib.error
import urllib.request

BASE = os.environ.get("BASE", "").rstrip("/")
GOAL = os.environ.get("GOAL_ID", "")
TOKEN = os.environ.get("RUN_TOKEN", "")
DEADLINE = time.time() + int(os.environ.get("MAX_SECONDS", "720"))       # ١٢ دقيقة وبعدين نسيب الباقي للتشغيل الجاي

DEFAULTS = {"groq": "openai/gpt-oss-120b,qwen/qwen3.8-27b,openai/gpt-oss-20b",
            "cerebras": "gpt-oss-120b,qwen-3-235b-a22b-instruct-2507",
            "nvidia": "deepseek-ai/deepseek-v4.1-flash",
            "gemini": "gemini-3.8-flash",
            "openrouter": ""}
OPENAI_URLS = {"groq": os.environ.get("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions"),
               "cerebras": os.environ.get("CEREBRAS_URL", "https://api.cerebras.ai/v1/chat/completions"),
               "nvidia": os.environ.get("NVIDIA_URL", "https://integrate.api.nvidia.com/v1/chat/completions"),
               "openrouter": os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")}
GEMINI_URL = os.environ.get("GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/models/")
LANES = {"public": ["groq", "cerebras", "nvidia", "gemini", "openrouter"], "private": ["groq", "cerebras"]}
JSON_MODE = {"groq", "cerebras"}
KEYS = {"groq": "GROQ_API_KEY", "cerebras": "CEREBRAS_API_KEY", "nvidia": "NVIDIA_API_KEY",
        "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
DEAD: set[str] = set()          # مزوّد خلص حده **اليومي** (كل موديلاته) ← مانجرّبوش تاني في التشغيل ده
DEAD_M: set[tuple[str, str]] = set()   # موديل بعينه خلص حده اليومي


class Limit(Exception):
    """429. daily=True لو الحد اليومي (RPD/TPD/PerDay) — غير كده ده حد الدقيقة: نستنى ثواني ونكمّل."""

    def __init__(self, daily: bool, wait: float):
        super().__init__("limit")
        self.daily, self.wait = daily, wait


def limit_of(body: str, headers) -> Limit:
    """Groq: «…per day (RPD)/(TPD)» أو «per minute (RPM/TPM) … try again in 7.6s». Gemini: «PerDay/PerMinute»."""
    b = body or ""
    daily = bool(re.search(r"per day|\(RPD\)|\(TPD\)|PerDay|per_day|daily", b, re.I)) and not re.search(r"per minute|PerMinute", b, re.I)
    wait = 20.0
    try:
        wait = float((headers or {}).get("retry-after") or wait)
    except (TypeError, ValueError):
        pass
    m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", b)
    if m:
        wait = int(m.group(1) or 0) * 60 + float(m.group(2))
    if wait > 600:                     # «حاول كمان ساعات» = يومي عملياً
        daily = True
    return Limit(daily, min(max(wait, 2.0), 600.0))


def models_of(p: str) -> list[str]:
    return [m.strip() for m in (os.environ.get(p.upper() + "_MODELS") or DEFAULTS[p]).split(",") if m.strip()]


def http(method: str, url: str, body: dict | None = None, headers: dict | None = None, timeout: int = 120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "User-Agent": "almanara-agents", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode("utf-8", "replace")[:2000]
        except Exception:  # noqa: BLE001
            err = ""
        return e.code, {"_error": err, "_headers": {k.lower(): v for k, v in (e.headers or {}).items()}}


def ask(p: str, model: str, t: dict) -> str:
    key = os.environ.get(KEYS[p], "").strip()
    if p == "gemini":
        body = {"systemInstruction": {"parts": [{"text": t["system"]}]},
                "contents": [{"role": "user", "parts": [{"text": t["prompt"]}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": t.get("max_tokens", 1500),
                                     **({"responseMimeType": "application/json"} if t.get("json") else {})}}
        code, r = http("POST", GEMINI_URL + model + ":generateContent", body, {"x-goog-api-key": key})
        if code == 429:
            raise limit_of(r.get("_error", ""), r.get("_headers"))
        if code != 200:
            raise RuntimeError(f"{code}")
        parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return "".join(str(x.get("text") or "") for x in parts)
    body = {"model": model, "temperature": 0.7, "max_tokens": t.get("max_tokens", 1500),
            "messages": [{"role": "system", "content": t["system"]}, {"role": "user", "content": t["prompt"]}]}
    if t.get("json") and p in JSON_MODE:
        body["response_format"] = {"type": "json_object"}
    code, r = http("POST", OPENAI_URLS[p], body, {"Authorization": "Bearer " + key})
    if code == 429:
        raise limit_of(r.get("_error", ""), r.get("_headers"))
    if code != 200:
        raise RuntimeError(f"{code}")
    return str(((r.get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def run(t: dict) -> dict:
    """أول مزوّد يرد. حد الدقيقة ← نجرّب موديل تاني، ولو كله مستني نستنى ثواني ونعيد (لحد آخر الوقت).
    الحد اليومي لكل الموديلات في الطريق ← limit (المهمة تستنى بكرة). أي غلط تاني ← error."""
    lane = LANES.get(t.get("lane"), LANES["private"])            # مش معروف ← الطريق الخاص (الأأمن)
    prefer = [p for p in (t.get("prefer") or []) if p in lane]   # «المنارة» ممكن تقدّم مزوّد جوه نفس الطريق بس (مثلاً Gemini للكتابة)
    lane = prefer + [p for p in lane if p not in prefer]
    while True:
        errors, waits = [], []
        for p in lane:
            if p in DEAD or not os.environ.get(KEYS[p], "").strip():
                continue
            for m in models_of(p):
                if (p, m) in DEAD_M:
                    continue
                t0 = time.time()
                try:
                    text = ask(p, m, t)
                except Limit as lim:
                    if lim.daily:
                        DEAD_M.add((p, m))
                        print(f"  {p}/{m.split('/')[-1]}: الحد اليومي خلص")
                        if all((p, x) in DEAD_M for x in models_of(p)):
                            DEAD.add(p)
                    else:
                        waits.append(lim.wait)
                        print(f"  {p}/{m.split('/')[-1]}: حد الدقيقة — بعد {lim.wait:.0f}ث")
                    continue
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{p}:{str(e)[:40]}")
                    continue
                if text.strip():
                    return {"text": text, "provider": p, "model": m, "secs": int(time.time() - t0)}
                errors.append(f"{p}:فاضي")
        if waits:
            nap = min(min(waits) + 1, 65)
            if time.time() + nap + 30 < DEADLINE:
                time.sleep(nap)                                   # حد الدقيقة ← نستنى ونعيد
                continue
            return {"error": "حد الدقيقة والوقت خلص — هتكمّل في التشغيل الجاي"}
        live = [p for p in lane if p not in DEAD and os.environ.get(KEYS[p], "").strip()]
        if not live and any(os.environ.get(KEYS[p], "").strip() for p in lane):
            return {"limit": True}
        if errors:
            return {"error": "؛ ".join(errors)[:300]}
        return {"error": "مفيش ولا مفتاح مزوّد متحط في GitHub Secrets"}


def main() -> int:
    if not (BASE and GOAL and TOKEN):
        print("ناقص BASE أو GOAL_ID أو RUN_TOKEN")
        return 1
    h = {"Authorization": "Bearer " + TOKEN}
    done = 0
    while time.time() < DEADLINE:
        code, nxt = http("GET", f"{BASE}/lab/team-ai/api/{GOAL}/next", headers=h, timeout=30)
        if code != 200:
            print(f"«المنارة» رجّعت {code}")
            return 1
        t = nxt.get("task")
        if not t:
            print(f"✅ خلصنا — {done} مهمة" + (" (السقف اليومي خلص)" if nxt.get("why") == "cap" else ""))
            return 0
        res = run(t)
        code, _ = http("POST", f"{BASE}/lab/team-ai/api/{GOAL}/result/{t['id']}", res, h, timeout=30)
        print(f"• مهمة {t['id']} ({t['agent']}): {res.get('provider') or ('حد' if res.get('limit') else 'غلط')} "
              f"{res.get('secs', '')}ث ← {code}")
        done += 1
        if res.get("limit") and not [p for p in LANES.get(t.get("lane"), LANES["private"]) if p not in DEAD and os.environ.get(KEYS[p])]:
            print("🌙 كل المزوّدين خلصوا — الباقي بكرة")
            return 0
    print("⏱ الوقت خلص — الباقي في التشغيل الجاي")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
