import os
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

URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def write_file(text: str):
    last_error = ""
    for _ in range(3):
        r = requests.get(URL, headers=HEADERS,
                         params={"ref": GITHUB_BRANCH}, timeout=5)
        if r.status_code == 200:
            sha = r.json().get("sha")
        elif r.status_code == 404:
            sha = None  # الملف غير موجود، سيُنشأ
        else:
            raise RuntimeError(f"GitHub GET {r.status_code}: {r.text[:200]}")

        payload = {
            "message": "TradingView Alert Update",
            "content": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        p = requests.put(URL, headers=HEADERS, json=payload, timeout=5)
        if p.status_code in (200, 201):
            return "created" if p.status_code == 201 else "updated"
        last_error = f"GitHub PUT {p.status_code}: {p.text[:200]}"
        if p.status_code in (409, 422):  # تعارض نسخ، أعد المحاولة
            continue
        break
    raise RuntimeError(last_error)


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if not WEBHOOK_SECRET or request.args.get("key") != WEBHOOK_SECRET:
        return jsonify(status="error", message="unauthorized"), 401

    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        raw = request.get_data(as_text=True).strip()
        if not raw:
            return jsonify(status="error", message="No data received"), 400
        data = {"raw": raw}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if "raw" in data:
        content = f"Raw: {data['raw']}\nTime: {now} UTC\n"
    else:
        content = (
            f"Ticker: {data.get('ticker', '-')}\n"
            f"Price: {data.get('price', '-')}\n"
            f"Action: {data.get('action', '-')}\n"
            f"Time: {now} UTC\n"
        )

    try:
        result = write_file(content)
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500

    return jsonify(status="ok", file=GITHUB_FILE, action=result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
