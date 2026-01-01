from flask import Flask, request, jsonify, Response
import requests
from flask_cors import CORS

app = Flask(__name__)
# تفعيل CORS للجميع
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy():
    # 1. الحصول على الرابط الهدف
    target_url = request.args.get('url')
    # 2. الحصول على الكوكيز من الباراميتر (الجديد)
    custom_cookie = request.args.get('cookie')
    
    if not target_url:
        return jsonify({'error': 'Missing "url" parameter'}), 400

    # نسخ الهيدرز القادمة من الطلب الأصلي
    headers = {key: value for (key, value) in request.headers if key != 'Host'}

    # 3. حقن الكوكيز في الهيدر إذا تم تمريرها في الرابط
    if custom_cookie:
        # نقوم بإضافة أو استبدال هيدر الكوكيز بالقيمة القادمة من الرابط
        headers['Cookie'] = custom_cookie

    try:
        # إرسال الطلب إلى الـ API الأصلي
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            allow_redirects=False
        )

        # تجهيز الهيدرز للرد
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_response = [
            (name, value) for (name, value) in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(resp.content, resp.status_code, headers_response)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
