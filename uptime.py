"""🚨 إنذار وقوع «المنارة» (أحمد ٨ نوفمبر) — بيشتغل من GitHub Actions كل ٥ دقايق (الريبو public ← ببلاش).

- بيجرّب كل لينك في UPTIME_URLS (افتراضي: /healthz/db اللي بيجرّب القاعدة فعلاً). أول محاولة فشلت ← يستنى ٢٠ ثانية ويعيد،
  عشان مايزعجكش على تهنيجة ثانية.
- وقع ← Issue بعنوان «🚨 …» + رسالة تيليجرام. رجع ← يقفل الـ Issue + «✅ رجع بعد X دقيقة». مرة واحدة لكل وقعة.
- بطيء (أكتر من SLOW_MS) ← مرة واحدة في الساعة بالكتير.
- stdlib بس. مفيش أي مفتاح بيتطبع.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

URLS = [u.strip() for u in (os.environ.get("UPTIME_URLS") or "https://team.almanara.info/healthz/db").split(",") if u.strip()]
SLOW_MS = int(os.environ.get("SLOW_MS") or 8000)
TG_TOKEN = os.environ.get("ALERT_TG_TOKEN", "").strip()
TG_CHAT = os.environ.get("ALERT_TG_CHAT", "").strip()
GH = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
LABEL = "down"


def req(method: str, url: str, body=None, headers=None, timeout=40):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": "almanara-uptime", "Content-Type": "application/json",
                                                                       **(headers or {})})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as x:
            return x.status, x.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return 0, type(e).__name__


def probe(url: str) -> tuple[bool, int, str]:
    t0 = time.monotonic()
    code, body = req("GET", url, timeout=40)
    ms = int((time.monotonic() - t0) * 1000)
    ok = code == 200 and '"ok"' in body
    return ok, ms, (f"HTTP {code}" if code else body or "مفيش رد")


def gh(method: str, path: str, body=None):
    code, raw = req(method, f"https://api.github.com/repos/{REPO}{path}", body,
                    {"Authorization": f"Bearer {GH}", "Accept": "application/vnd.github+json"})
    try:
        return code, json.loads(raw) if raw else {}
    except ValueError:
        return code, {}


def telegram(text: str) -> None:
    if not (TG_TOKEN and TG_CHAT):
        print("⚠️ مفيش ALERT_TG_TOKEN/ALERT_TG_CHAT — الإنذار في الـ Issue بس")
        return
    code, _ = req("POST", f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", {"chat_id": TG_CHAT, "text": text})
    print(f"تيليجرام ← {code}")


def open_issue(url: str):
    code, items = gh("GET", f"/issues?state=open&labels={LABEL}&per_page=50")
    for it in items if isinstance(items, list) else []:
        if url in (it.get("body") or ""):
            return it
    return None


def main() -> int:
    now = datetime.now(timezone.utc)
    for url in URLS:
        name = url.split("//")[-1].split("/")[0]
        ok, ms, why = probe(url)
        if not ok:
            time.sleep(20)                                        # تهنيجة ثانية؟ نعيد مرة
            ok, ms, why = probe(url)
        issue = open_issue(url)
        print(f"{name}: {'✅' if ok else '❌'} {ms}ms {'' if ok else why}")
        if not ok and not issue:
            gh("POST", "/issues", {"title": f"🚨 {name} واقع", "labels": [LABEL],
                                   "body": f"{url}\n\nأول ما لاحظنا: {now:%Y-%m-%d %H:%M} UTC\nالسبب: {why}"})
            telegram(f"🚨 «المنارة» مش بترد\n{name} — {why}\nهبعتلك أول ما ترجع.")
        elif ok and issue:
            start = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            mins = max(1, int((now - start).total_seconds() // 60))
            gh("POST", f"/issues/{issue['number']}/comments", {"body": f"✅ رجع بعد حوالي {mins} دقيقة ({ms}ms)"})
            gh("PATCH", f"/issues/{issue['number']}", {"state": "closed"})
            telegram(f"✅ «المنارة» رجعت بعد حوالي {mins} دقيقة")
        elif ok and ms > SLOW_MS and now.minute < 5:              # بطء ← مرة في الساعة بالكتير
            telegram(f"🐢 «المنارة» بطيئة: {ms / 1000:.1f} ثانية عشان ترد ({name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
