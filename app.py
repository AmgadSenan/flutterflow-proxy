from flask import Flask, request, jsonify, Response
import requests
from flask_cors import CORS

app = Flask(__name__)
# تفعيل CORS للجميع للسماح لـ FlutterFlow بالاتصال
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy():
    # 1. الحصول على رابط الـ API الحقيقي من المتغيرات
    # مثال للاستخدام: https://your-proxy.onrender.com/proxy?url=https://api.example.com/login
    target_url = request.args.get('url')
    
    if not target_url:
        return jsonify({'error': 'Missing "url" parameter'}), 400

    # 2. تجهيز الهيدرز (Headers)
    # نقوم بنسخ الهيدرز القادمة من FlutterFlow ولكن نحذف الـ Host لتجنب المشاكل
    headers = {key: value for (key, value) in request.headers if key != 'Host'}

    try:
        # 3. إرسال الطلب إلى الـ API الأصلي
        # نستخدم نفس الـ Method (POST, GET, etc) ونفس البيانات (Body/JSON)
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

        # 4. تجهيز الهيدرز التي سنعيدها لـ FlutterFlow
        # نستثني بعض الهيدرز الخاصة بالنقل لتجنب الأخطاء
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_response = [
            (name, value) for (name, value) in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        # 5. إرجاع الاستجابة (Response) كما جاءت من الـ API الأصلي
        return Response(resp.content, resp.status_code, headers_response)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
