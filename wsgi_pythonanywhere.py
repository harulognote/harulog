# +--------------------------------------------------------------------------+
# | HaruLog WSGI Adapter for PythonAnywhere & Public Cloud Hosting           |
# +--------------------------------------------------------------------------+
import sys
import os
from pathlib import Path

# 1. 프로젝트 홈 디렉토리 등록
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 2. 환경 변수(.env) 로드
from dotenv import load_dotenv
env_path = current_dir / '.env'
if env_path.is_file():
    load_dotenv(env_path, interpolate=False, encoding='utf-8-sig')

# PythonAnywhere 클라우드 환경에서는 SQLite 엔진 기본 강제 보장
os.environ.setdefault('DB_ENGINE', 'sqlite')

# 3. Flask 메인 애플리케이션 임포트
from main import app as flask_app
from werkzeug.middleware.proxy_fix import ProxyFix

# 4. 리버스 프록시(Cloudflare / Nginx) 헤더 신뢰 설정 (Proto, Host, For)
flask_app.wsgi_app = ProxyFix(
    flask_app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_port=1,
    x_prefix=1
)

# 5. WSGI 엔트리포인트 (PythonAnywhere는 'application' 객체를 호출함)
def application(environ, start_response):
    # Cloudflare Pages 도메인과의 통신을 위해 CORS 응답 헤더 추가 보장
    def custom_start_response(status, response_headers, exc_info=None):
        origin = environ.get('HTTP_ORIGIN', '')
        headers_dict = dict(response_headers)

        # Origin이 있으면 해당 Origin을 허용하고 자격증명(쿠키) 허용
        if origin:
            headers_dict['Access-Control-Allow-Origin'] = origin
            headers_dict['Access-Control-Allow-Credentials'] = 'true'
            headers_dict['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            headers_dict['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token'

        return start_response(status, list(headers_dict.items()), exc_info)

    # OPTIONS 사전 요청(Preflight) 직접 응답
    if environ.get('REQUEST_METHOD', '').upper() == 'OPTIONS':
        origin = environ.get('HTTP_ORIGIN', '*')
        headers = [
            ('Content-Type', 'text/plain'),
            ('Access-Control-Allow-Origin', origin),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token'),
            ('Access-Control-Max-Age', '86400'),
        ]
        start_response('204 No Content', headers)
        return [b'']

    return flask_app(environ, custom_start_response)

if __name__ == '__main__':
    port = int(os.getenv('APP_PORT', '5000'))
    flask_app.run(host='0.0.0.0', port=port, debug=False)
