"""Single-owner application login, protected routes and account settings."""
from collections import defaultdict, deque
from datetime import timedelta
import hmac
import hashlib
import os
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import urlsplit

from flask import g, jsonify, redirect, request, session, send_from_directory, Response
from flask.sessions import SecureCookieSessionInterface
from werkzeug.security import generate_password_hash, check_password_hash

COLUMNS='id username display_name password_hash role status auth_version created_at updated_at'


def init_schema(conn):
    cursor=conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS app_members (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(64) NOT NULL UNIQUE,
            display_name VARCHAR(100) NOT NULL DEFAULT '',
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(16) NOT NULL DEFAULT 'user',
            status VARCHAR(16) NOT NULL DEFAULT 'pending',
            auth_version INT NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS app_system (
            name VARCHAR(64) PRIMARY KEY,value VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS app_admin_audit (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,actor_id BIGINT NOT NULL,target_id BIGINT NOT NULL,
            action VARCHAR(40) NOT NULL,details TEXT NOT NULL,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:cursor.close()


def read_account(get_conn,member_id=None,username=None):
    conn=get_conn()
    if conn is None:raise RuntimeError('DB 연결에 실패했습니다.')
    cursor=None
    try:
        cursor=conn.cursor(dictionary=True)
        if member_id:
            cursor.execute('SELECT * FROM app_members WHERE id=%s',(member_id,))
        elif username is not None:
            cursor.execute('SELECT * FROM app_members WHERE username=%s',(username,))
        else:
            cursor.execute('SELECT * FROM app_members ORDER BY id LIMIT 1')
        return cursor.fetchone()
    finally:
        if cursor is not None:cursor.close()
        conn.close()


def ownership_ready(get_conn):
    conn=get_conn();cursor=None
    try:
        cursor=conn.cursor()
        cursor.execute("SELECT value FROM app_system WHERE name='ownership_v1'")
        if not cursor.fetchone():return False
        from ownership import TABLES

        # SQLite 환경 지원 (PRAGMA table_info 검사)
        import sqlite3
        if hasattr(conn, '_conn') and isinstance(conn._conn, sqlite3.Connection):
            valid_count = 0
            for tbl in TABLES:
                try:
                    cursor.execute(f"PRAGMA table_info('{tbl}')")
                    cols = [r['name'] if isinstance(r, dict) else r[1] for r in cursor.fetchall()]
                    if 'owner_id' in cols:
                        valid_count += 1
                except Exception:
                    pass
            return valid_count == len(TABLES)

        # MariaDB 환경 지원 (information_schema 검사)
        placeholders=','.join(['%s']*len(TABLES))
        cursor.execute("SELECT COUNT(DISTINCT TABLE_NAME) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND COLUMN_NAME='owner_id' AND TABLE_NAME IN ("+placeholders+")",TABLES)
        row=cursor.fetchone()
        if not row:
            return False
        val = row.get('COUNT(DISTINCT TABLE_NAME)') if isinstance(row, dict) else row[0]
        return bool(val == len(TABLES))
    except Exception as e:
        return False
    finally:
        if cursor is not None:cursor.close()
        if conn is not None:conn.close()


class CookieSession(SecureCookieSessionInterface):
    def get_cookie_secure(self,app):return request.is_secure


def csrf_token():
    if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
    return session['csrf']


def validate_credentials(data):
    username=data.get('username','')
    password=data.get('password','')
    if not isinstance(username,str) or not re.fullmatch(r'[^\s:]{3,64}',username):
        raise ValueError('아이디는 공백과 : 없이 3~64자로 입력해 주세요.')
    if not isinstance(password,str) or not 8<=len(password)<=256:
        raise ValueError('비밀번호는 8~256자로 입력해 주세요.')
    if password!=data.get('confirm_password'):
        raise ValueError('새 비밀번호 확인이 일치하지 않습니다.')
    return username,password


def register_routes(app,get_conn):
    app.config.update(SECRET_KEY=secrets.token_hex(32),AUTH_ENABLED=True,
        SESSION_COOKIE_NAME='harulog_session_'+hashlib.sha256((str(Path(__file__).resolve().parent)+'|'+os.getenv('APP_PORT','5000')).encode()).hexdigest()[:10],SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        AUTH_SETUP_TOKEN=secrets.token_urlsafe(32))
    app.session_interface=CookieSession()
    attempts=defaultdict(deque)
    lock=threading.Lock()

    @app.before_request
    def protect():
        if not app.config.get('AUTH_ENABLED',True):return
        public=request.path in ('/login','/static/login.js','/static/style.css','/api/auth/status','/api/auth/login','/api/auth/setup','/api/auth/signup')
        if request.path=='/static/index.html':return redirect('/')
        if public and request.method in ('GET','HEAD') and request.path not in ('/api/auth/status',):return
        try:
            g.account=read_account(get_conn,member_id=session.get('uid')) if session.get('uid') else None
            g.configured=bool(g.account or read_account(get_conn))
        except Exception:
            app.logger.exception('로그인 상태 확인 실패')
            return jsonify(error='로그인 DB를 확인하지 못했습니다. 서버 상태를 확인해 주세요.'),503
        g.authenticated=bool(g.account and g.account['status']=='active' and session.get('uid')==g.account['id'] and session.get('av')==g.account['auth_version'])
        if not public and not g.authenticated:
            session.clear()
            if request.path.startswith('/api/'):return jsonify(error='로그인이 필요합니다.',code='LOGIN_REQUIRED'),401
            return redirect('/login')
        business_api=request.path.startswith('/api/') and not request.path.startswith(('/api/auth/','/api/admin/')) and request.path!='/api/settings/account'
        if not public and (business_api or request.path.startswith('/uploads/')):
            if not ownership_ready(get_conn):return jsonify(error='사용자별 자료 분리를 위한 ownership 마이그레이션이 필요합니다. 관리자에게 문의해 주세요.',code='MIGRATION_REQUIRED'),503
        if request.method not in ('GET','HEAD','OPTIONS'):
            supplied=request.headers.get('X-CSRF-Token','')
            expected=session.get('csrf','')
            origin=request.headers.get('Origin','').rstrip('/')
            allowed_origins={request.host_url.rstrip('/')}
            public_origin=app.config.get('AUTH_PUBLIC_ORIGIN','').rstrip('/')
            if public_origin:
                allowed_origins.add(public_origin)
            env_public=os.getenv('HARULOG_PUBLIC_URL','').rstrip('/')
            if env_public:
                allowed_origins.add(env_public)
            env_allowed=os.getenv('ALLOWED_ORIGINS','')
            if env_allowed:
                for o in env_allowed.split(','):
                    if o.strip(): allowed_origins.add(o.strip().rstrip('/'))
            fwd_host=request.headers.get('X-Forwarded-Host','').strip()
            if fwd_host:
                fwd_proto=request.headers.get('X-Forwarded-Proto', request.scheme or 'https')
                allowed_origins.add(f"{fwd_proto}://{fwd_host}".rstrip('/'))
            # Cloudflare Pages 도메인(*.pages.dev)은 기본 신뢰 허용
            if origin and (origin in allowed_origins or origin.endswith('.pages.dev')):
                pass
            elif origin:
                return jsonify(error='접속 주소가 일치하지 않습니다. 같은 주소에서 화면을 새로고침해 주세요.',code='CSRF_ORIGIN'),403
            if not expected or not hmac.compare_digest(supplied,expected):
                return jsonify(error='요청 인증이 만료되었습니다. 인증을 갱신한 뒤 다시 시도해 주세요.',code='CSRF_EXPIRED'),403

    @app.after_request
    def private_response(response):
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        return response

    @app.get('/login')
    def login_page():return send_from_directory(app.static_folder,'login.html')

    @app.get('/api/auth/status')
    def status():
        return jsonify(configured=g.configured,authenticated=g.authenticated,version='2.9.17',
            role=g.account['role'] if g.authenticated else '',member_id=g.account['id'] if g.authenticated else None,
            migration_required=g.authenticated and not ownership_ready(get_conn),
            username=g.account['username'] if g.authenticated else '',csrf_token=csrf_token(),
            setup_allowed=not g.configured)

    def start_session(account):
        session.clear();session['uid']=account['id'];session['av']=account['auth_version'];session.permanent=True
        return jsonify(ok=True,username=account['username'],csrf_token=csrf_token())

    @app.post('/api/auth/login')
    def login():
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='올바른 입력 형식이 아닙니다.'),400
        username,password=data.get('username',''),data.get('password','')
        source=request.remote_addr or 'unknown'
        with lock:
            now=time.monotonic()
            queue=attempts[source]
            while queue and now-queue[0]>300:queue.popleft()
            if len(queue)>=10:return jsonify(error='로그인 시도가 많습니다. 5분 후 다시 시도해 주세요.'),429
            queue.append(now)
        if not isinstance(username,str) or len(username)>64 or not isinstance(password,str) or len(password)>256:
            return jsonify(error='아이디 또는 비밀번호가 올바르지 않습니다.'),401
        account=read_account(get_conn,username=username)
        valid=bool(account and hmac.compare_digest(username.encode(),account['username'].encode())
                   and check_password_hash(account['password_hash'],password))
        if not valid:return jsonify(error='아이디 또는 비밀번호가 올바르지 않습니다.'),401
        if account['status']!='active':return jsonify(error='승인 대기 또는 이용 중지된 계정입니다.'),403
        with lock:attempts.pop(source,None)
        return start_session(account)

    @app.post('/api/auth/setup')
    def setup():
        if g.configured:return jsonify(error='이미 최초 관리자가 설정되어 있습니다.'),409
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='올바른 입력 형식이 아닙니다.'),400
        token=data.get('setup_token','')
        if (not isinstance(token,str) or not token
                or not hmac.compare_digest(token,app.config['AUTH_SETUP_TOKEN'])):
            return jsonify(error='최초 관리자는 서버 콘솔에 표시된 최신 설정 링크 또는 설정 코드에서 등록해 주세요. 서버 재시작 시 설정 코드가 바뀝니다.',code='SETUP_TOKEN_INVALID'),403
        try:username,password=validate_credentials(data)
        except ValueError as error:return jsonify(error=str(error)),400
        conn=get_conn();cursor=None
        try:
            cursor=conn.cursor()
            cursor.execute("INSERT INTO app_members (id,username,display_name,password_hash,role,status,auth_version) VALUES (1,%s,%s,%s,'admin','active',1)",
                           (username,username,generate_password_hash(password)))
            conn.commit()
            app.config['AUTH_SETUP_TOKEN']=''
            return start_session({'id':1,'username':username,'auth_version':1})
        except Exception:
            if conn is not None:conn.rollback()
            app.logger.exception('최초 관리자 등록 실패')
            return jsonify(error='계정을 등록하지 못했습니다. 다른 창에서 이미 등록했는지 확인해 주세요.'),409
        finally:
            if cursor is not None:cursor.close()
            if conn is not None:conn.close()

    @app.post('/api/auth/signup')
    def signup():
        if not g.configured:return jsonify(error='서버 관리자의 최초 등록을 먼저 진행해 주세요.'),403
        with lock:
            source='signup:'+(request.remote_addr or 'unknown');now=time.monotonic();queue=attempts[source]
            while queue and now-queue[0]>300:queue.popleft()
            if len(queue)>=10:return jsonify(error='가입 시도가 많습니다. 5분 후 다시 시도해 주세요.'),429
            queue.append(now)
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='입력 형식을 확인해 주세요.'),400
        try:username,password=validate_credentials(data)
        except ValueError as error:return jsonify(error=str(error)),400
        display=data.get('display_name') or username
        if not isinstance(display,str) or not 1<=len(display.strip())<=100:return jsonify(error='이름은 1~100자로 입력해 주세요.'),400
        conn=get_conn();cursor=None
        try:
            cursor=conn.cursor()
            cursor.execute("INSERT INTO app_members (username,display_name,password_hash,role,status,auth_version) VALUES (%s,%s,%s,'user','pending',1)",
                           (username,display.strip(),generate_password_hash(password)))
            conn.commit();return jsonify(ok=True,message='가입 신청이 완료되었습니다. 관리자 승인 후 로그인해 주세요.'),201
        except Exception as error:
            conn.rollback()
            if getattr(error,'errno',None)==1062:return jsonify(error='이미 사용 중인 아이디입니다.'),409
            app.logger.exception('회원가입 실패');return jsonify(error='가입 신청에 실패했습니다.'),500
        finally:
            if cursor is not None:cursor.close()
            conn.close()

    @app.post('/api/auth/logout')
    def logout():
        # Overwrite the authenticated cookie with a fresh anonymous session.
        # This is more reliable than relying only on an expiry cookie in mobile
        # browsers behind an HTTPS reverse proxy.
        session.clear()
        session['csrf']=secrets.token_urlsafe(32)
        session.permanent=False
        return jsonify(ok=True,authenticated=False,csrf_token=session['csrf'])

    @app.put('/api/settings/account')
    def update_account():
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='올바른 입력 형식이 아닙니다.'),400
        current=data.get('current_password','')
        if not isinstance(current,str) or len(current)>256 or not check_password_hash(g.account['password_hash'],current):
            return jsonify(error='현재 비밀번호가 올바르지 않습니다.'),403
        try:username,password=validate_credentials(data)
        except ValueError as error:return jsonify(error=str(error)),400
        conn=get_conn();cursor=None
        try:
            cursor=conn.cursor()
            cursor.execute('''UPDATE app_members SET username=%s,password_hash=%s,
                auth_version=auth_version+1,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND auth_version=%s''',
                (username,generate_password_hash(password),g.account['id'],g.account['auth_version']))
            if cursor.rowcount!=1:
                conn.rollback();return jsonify(error='계정이 다른 세션에서 변경되었습니다. 다시 로그인해 주세요.'),409
            conn.commit()
            return start_session({'id':g.account['id'],'username':username,'auth_version':g.account['auth_version']+1})
        except Exception:
            if conn is not None:conn.rollback()
            app.logger.exception('계정 변경 실패')
            return jsonify(error='계정 변경에 실패했습니다.'),500
        finally:
            if cursor is not None:cursor.close()
            if conn is not None:conn.close()


def render_home(app):
    html=(Path(app.static_folder)/'index.html').read_text(encoding='utf-8')
    return Response(html.replace('__HARULOG_CSRF__',csrf_token()),mimetype='text/html')


def announce_setup(app,get_conn,port):
    if not read_account(get_conn):
        print('\n[최초 관리자 설정] 아래 링크 또는 코드를 사용하세요. 다른 사람에게 공유하지 마세요.\n'
              f'http://127.0.0.1:{port}/login#setup={app.config["AUTH_SETUP_TOKEN"]}\n'
              f'최초 관리자 설정 코드: {app.config["AUTH_SETUP_TOKEN"]}\n'
              '외부 로그인 화면에서도 위 코드를 입력해 최초 관리자를 등록할 수 있습니다.\n',flush=True)
