import os
import json
import base64
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

GITHUB_TOKEN   = os.environ["GITHUB_TOKEN"]
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "Ma18308/all-akbar")
GITHUB_FILE    = os.environ.get("GITHUB_FILE", "alert.txt")
GITHUB_BRANCH  = os.environ.get("GITHUB_BRANCH", "main")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def replace_file(new_content: str):
    """يستبدل محتوى الملف بالكامل (وينشئه إن لم يكن موجوداً)."""
    for _ in range(3):
        r = requests.get(API, headers=HEADERS,
                         params={"ref": GITHUB_BRANCH}, timeout=5)
        if r.status_code == 200:
            sha = r.json()["sha"]
        elif r.status_code == 404:
            sha = None
        else:
            r.raise_for_status()

        payload = {
            "message": f"TradingView alert {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC",
            "content": base64.b64encode(new_content.encode("utf-8")).decode(),
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        p = requests.put(API, headers=HEADERS, json=payload, timeout=5)
        if p.status_code in (200, 201):
            return
        if p.status_code in (409, 422):
            continue
        p.raise_for_status()
    raise RuntimeError("Failed to update file after retries")


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.args.get("key") != WEBHOOK_SECRET:
        return jsonify(error="unauthorized"), 401

    raw = request.get_data(as_text=True).strip()
    if not raw:
        return jsonify(error="empty body"), 400

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw}  # إن لم تكن JSON صالحة نحفظها كما هي

    if isinstance(data, dict):
        data["received_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        replace_file(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    except Exception as e:
        return jsonify(error=str(e)), 500

    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
