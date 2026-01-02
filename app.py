from flask import Flask, request, jsonify, Response
import requests
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    expose_headers=["odoo-cookie"]  # 🔥 هذا هو المفتاح
)

@app.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy():
    target_url = request.args.get('url')

    if not target_url:
        return jsonify({'error': 'Missing "url" parameter'}), 400

    headers = {k: v for k, v in request.headers if k.lower() != 'host'}

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']

        headers_response = []
        cookies_collected = []

        for name, value in resp.raw.headers.items():
            lname = name.lower()
            if lname == 'set-cookie':
                cookies_collected.append(value)
                continue
            if lname not in excluded_headers:
                headers_response.append((name, value))

        if cookies_collected:
            headers_response.append(
                ('odoo-cookie', ', '.join(cookies_collected))
            )

        return Response(resp.content, resp.status_code, headers_response)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
