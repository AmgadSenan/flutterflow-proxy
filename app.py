from flask import Flask, request, jsonify, Response
import requests
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    expose_headers=["odoo-cookie"]
)

@app.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def proxy():
    """
    Universal Proxy Endpoint:
    يستقبل جميع أنواع الطلبات
    ويحمل في جسم الطلب JSON يحتوي:
    {
        "url": "https://example.com/api",
        "headers": {...},
        "body": {...}
    }
    """

    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({'error': 'Missing JSON body'}), 400

    target_url = payload.get('url')
    custom_headers = payload.get('headers', {})
    body = payload.get('body')

    if not target_url:
        return jsonify({'error': 'Missing "url"'}), 400

    # إعداد رؤوس الطلب الصادر
    headers = {
        k: v for k, v in custom_headers.items()
        if k.lower() != 'host'
    }

    try:
        # تمرير نفس نوع الطلب القادم (GET, POST...)
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            json=body if request.method in ['POST', 'PUT', 'PATCH'] else None,
            params=body if request.method == 'GET' else None,
            allow_redirects=False
        )

        # استبعاد بعض الرؤوس غير المفيدة للعميل
        excluded_headers = [
            'content-encoding',
            'content-length',
            'transfer-encoding',
            'connection'
        ]

        headers_response = []
        cookies_collected = []

        # استخراج set-cookie واستبداله باسم جديد
        for name, value in resp.raw.headers.items():
            lname = name.lower()
            if lname == 'set-cookie':
                cookies_collected.append(value)
                continue
            if lname not in excluded_headers:
                headers_response.append((name, value))

        # إعادة الكوكي باسم odoo-cookie
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
