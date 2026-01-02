from flask import Flask, request, jsonify, Response
import requests
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    expose_headers=["odoo-cookie"]
)

@app.route('/proxy', methods=['POST', 'OPTIONS'])
def proxy():

    # ✅ معالجة Preflight
    if request.method == 'OPTIONS':
        return Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            }
        )

    # ───────────────────────────────
    # الطلب الفعلي (POST فقط)
    # ───────────────────────────────

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'error': 'Missing JSON body'}), 400

    target_url = payload.get('url')
    method = payload.get('method', 'GET').upper()
    custom_headers = payload.get('headers', {})
    body = payload.get('body')

    if not target_url:
        return jsonify({'error': 'Missing "url"'}), 400

    if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']:
        return jsonify({'error': f'Unsupported method: {method}'}), 400

    # تجهيز الهيدرز للطلب الخارجي
    headers = {
        k: v for k, v in custom_headers.items()
        if k.lower() != 'host'
    }

    try:
        resp = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            json=body if method in ['POST', 'PUT', 'PATCH'] else None,
            params=body if method == 'GET' else None,
            allow_redirects=False
        )

        excluded_headers = [
            'content-encoding',
            'content-length',
            'transfer-encoding',
            'connection'
        ]

        headers_response = []
        cookies_collected = []

        for name, value in resp.raw.headers.items():
            lname = name.lower()
            if lname == 'set-cookie':
                cookies_collected.append(value)
                continue
            if lname not in excluded_headers:
                headers_response.append((name, value))

        # إعادة الكوكي باسم مقروء
        if cookies_collected:
            headers_response.append(
                ('odoo-cookie', ', '.join(cookies_collected))
            )

        return Response(
            resp.content,
            resp.status_code,
            headers_response
        )

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
