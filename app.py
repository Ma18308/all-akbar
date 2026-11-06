import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# جلب الإعدادات الأساسية فقط
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "Ma18308/all-akbar"
GITHUB_FILE = "alert.txt"
GITHUB_BRANCH = "main"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400

        # إنشاء محتوى التنبيه لكتابته في GitHub
        content_string = f"Ticker: {data.get('ticker')}\nPrice: {data.get('price')}\nAction: {data.get('action')}"
        
        # إرسال البيانات مباشرة إلى GitHub بدون شروط كلمة سر
        url = f"https://github.com{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # جلب ملف الـ SHA إذا كان موجوداً لتحديثه
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        
        import base64
        payload = {
            "message": "TradingView Alert Update",
            "content": base64.b64encode(content_string.encode('utf-8')).decode('utf-8'),
            "branch": GITHUB_BRANCH
        }
        if sha:
            payload["sha"] = sha
            
        put_r = requests.put(url, headers=headers, json=payload)
        
        if put_r.status_code in:
            return jsonify({"status": "ok", "message": "File updated successfully in GitHub"}), 200
        else:
            return jsonify({"status": "error", "message": put_r.text}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
