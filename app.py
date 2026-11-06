import os
import json
import base64
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "Ma18308/all-akbar")
GITHUB_FILE    = os.environ.get("GITHUB_FILE", "alert.txt")
GITHUB_BRANCH  = os.environ.get("GITHUB_BRANCH", "main")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def replace_file(new_content: str):
    """يستبدل محتوى الملف، وينشئه إن لم يكن موجوداً."""
    last_error = ""
    for _ in range(3):
        r = requests.get(API, headers=HEADERS,
                         params={"ref": GITHUB_BRANCH}, timeout=5)
        if r.status_code == 200:
            sha = r.json()["sha"]
        elif r.status_code == 404:
            sha = None  # الملف غير موجود، سيُنشأ الآن
        else:
            raise RuntimeError(f"GitHub GET {r.status_code}: {r.text[:200]}")

        payload = {
            "message": f"TradingView alert {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC",
            "content": base64.b64encode(new_content.encode("utf-8")).decode(),
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        p = requests.put(API, headers=HEADERS, json=payload, timeout=5)
        if p.status_code in (200, 201):
            return "created" if p.status_code == 201 else "updated"
        last_error = f"GitHub PUT {p.status_code}: {p.text[:200]}"
        if p.status_code in (409, 422):  # تعارض نسخ، أعد المحاولة
            continue
        break
    raise RuntimeError(last_error)


@app.route("/", methods=["GET"])
def health():
    missing = [n for n, v in [("GITHUB_TOKEN", GITHUB_TOKEN),
                              ("WEBHOOK_SECRET", WEBHOOK_SECRET)] if not v]
    if missing:
        return jsonify(status="misconfigured", missing=missing), 500
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if not WEBHOOK_SECRET or request.args.get("key") != WEBHOOK_SECRET:
        return jsonify(error="unauthorized"), 401

    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify(error="empty body"), 400

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw}

    if isinstance(data, dict):
        data["received_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        data = {"data": data,
                "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    try:
        result = replace_file(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    except Exception as e:
        return jsonify(error=str(e)), 500

    return jsonify(status="ok", file=GITHUB_FILE, action=result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
