from flask import Flask, request, Response, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)

# نترك CORS مفعل بشكل عام، لكننا سنعالج الهيدرز يدوياً للتحكم الأفضل
# CORS(app) -> سنقوم بضبط الهيدرز يدوياً في الدالة لضمان عمل الكوكيز

@app.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({'error': 'Missing "url" parameter'}), 400

    # 1. نسخ الهيدرز من الطلب القادم (مع استثناء الـ Host)
    headers = {key: value for (key, value) in request.headers if key != 'Host'}

    try:
        # 2. إرسال الطلب إلى الـ API الهدف مع الكوكيز القادمة
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies, # تمرير الكوكيز المستلمة
            allow_redirects=False
        )

        # 3. تصفية الهيدرز المستلمة من الـ API
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'access-control-allow-origin']
        headers_response = []
        
        for name, value in resp.raw.headers.items():
            if name.lower() not in excluded_headers:
                # 4. معالجة خاصة للكوكيز (Set-Cookie)
                if name.lower() == 'set-cookie':
                    # نقوم بإزالة 'Domain=...' حتى يقبل المتصفح الكوكي على دومين البروكسي
                    # ونضيف SameSite=None; Secure لضمان عملها في المتصفحات الحديثة
                    cookies_parts = value.split(';')
                    new_cookie_parts = []
                    for part in cookies_parts:
                        if 'domain' not in part.lower(): # إزالة الدومين
                            new_cookie_parts.append(part)
                    
                    # إعادة تجميع الكوكي وتعديله
                    cookie_val = ";".join(new_cookie_parts)
                    # ضمان وجود إعدادات الأمان
                    if "SameSite" not in cookie_val:
                        cookie_val += "; SameSite=None"
                    if "Secure" not in cookie_val:
                        cookie_val += "; Secure"
                        
                    headers_response.append((name, cookie_val))
                else:
                    headers_response.append((name, value))

        # 5. إعداد الاستجابة
        response = Response(resp.content, resp.status_code, headers_response)

        # 6. ضبط هيدرز CORS يدوياً لدعم الكوكيز (Dynamic Origin)
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'

        return response

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

# معالجة طلبات OPTIONS (Preflight) لأن المتصفح يرسلها قبل الطلب الرئيسي
@app.route('/proxy', methods=['OPTIONS'])
def options():
    response = Response()
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
