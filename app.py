from flask import Flask, request, Response, jsonify
import requests

app = Flask(__name__)

# قائمة بالهيدرز التي يجب عدم تمريرها لتجنب تضارب بروتوكول HTTP
# (Hop-by-hop headers)
EXCLUDED_HEADERS = [
    'content-encoding', 'content-length', 'transfer-encoding', 'connection', 'host'
]

@app.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy():
    # --- 1. التعامل مع طلبات Pre-flight (OPTIONS) ---
    # المتصفح يرسل هذا الطلب أولاً للتأكد من السماح بالاتصال
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    target_url = request.args.get('url')
    if not target_url:
        return jsonify({'error': 'Missing "url" parameter'}), 400

    # --- 2. تجهيز الهيدرز المرسلة للـ API ---
    # نأخذ كل الهيدرز من المتصفح (بما فيها الكوكيز) ونستثني الهيدرز الخاصة بالسيرفر
    headers = {
        key: value for key, value in request.headers 
        if key.lower() not in EXCLUDED_HEADERS
    }

    try:
        # --- 3. إرسال الطلب الفعلي ---
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies, # تمرير الكوكيز بشكل صريح
            allow_redirects=False,
            stream=True # مهم جداً لاستقبال البيانات الكبيرة
        )

        # --- 4. بناء الاستجابة للمتصفح ---
        # نقوم بإنشاء كائن Response وننقل إليه المحتوى والـ Status Code
        response = Response(resp.content, resp.status_code)

        # نقل الهيدرز من الـ API إلى المتصفح (بما فيها Set-Cookie)
        for name, value in resp.raw.headers.items():
            if name.lower() not in EXCLUDED_HEADERS:
                response.headers.add(name, value)

        # --- 5. إضافة هيدرز الـ CORS الضرورية للكوكيز ---
        return _add_cors_headers(response)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

def _build_cors_preflight_response():
    response = Response()
    return _add_cors_headers(response)

def _add_cors_headers(response):
    # للحصول على الكوكيز، يجب ألا نستخدم * في Origin
    # بدلاً من ذلك، نقرأ الـ Origin من الطلب ونعيده كما هو
    request_origin = request.headers.get('Origin')
    
    if request_origin:
        response.headers['Access-Control-Allow-Origin'] = request_origin
        response.headers['Access-Control-Allow-Credentials'] = 'true' # هذا هو المفتاح للكوكيز
    
    response.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', 'Authorization, Content-Type, Cookie, X-Requested-With')
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
