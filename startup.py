"""HaruLog v2.9.13: run only; installation and migrations live in manage.py."""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REQUIRED_COLUMNS = {
    'app_members': 'id username display_name password_hash role status auth_version created_at updated_at',
    'app_system': 'name value',
    'app_admin_audit': 'id actor_id target_id action details created_at',
    'daily_logs': 'id content file_path created_at',
    'study_videos': 'id title youtube_id script language created_at',
    'vocab_list': 'id video_id word meaning created_at',
    'study_dictations': 'video_id content updated_at',
    'golf_rounds': 'id played_on course_name golf_club player_name player_nickname front_score back_score companions_json memo photo_path created_at updated_at hole_scores_json',
    'expense_invoices': 'id billing_month invoice_number property_name unit_name due_date paid_date paid items_json readings_json billed_total memo photo_path ocr_text created_at updated_at',
    'personal_profile': 'id name nickname updated_at',
    'golf_contacts': 'id name nickname phone address memo created_at updated_at',
    'utility_records': 'id billing_month electricity_usage electricity_fee water_usage water_fee telecom_fee gas_fee other_fee total_fee memo created_at updated_at',
    'pets': 'id name species registration_no sex birth_date death_date breed color microchip_no sire_id dam_id status notes photo_path created_at updated_at',
    'pet_records': 'id owner_id pet_id record_date content photo_path created_at',
    'pet_lineage': 'pet_id owner_id generation_no',
}


def require_environment():
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        raise RuntimeError('기존 .venv가 없습니다. 자동 설치하지 않습니다. README.md의 수동 설치 절차를 확인해 주세요.')
    check = subprocess.run([str(python), '-c',
        'import sys; assert sys.version_info >= (3,10); import flask,mysql.connector,dotenv,PIL,waitress,tinysegmenter,jieba'],
        capture_output=True)
    if check.returncode:
        raise RuntimeError('기존 Python 환경 또는 필수 패키지를 확인해 주세요. 자동 설치하지 않습니다. README.md에 설치 절차가 있습니다.')
    return python


def ensure_config():
    from dotenv import dotenv_values
    path = ROOT / '.env'
    if not path.is_file():
        raise RuntimeError('.env가 없습니다. 자동 생성하지 않습니다. README.md에 따라 기존 설정을 복원하거나 직접 준비해 주세요.')
    values = dotenv_values(path, interpolate=False, encoding='utf-8-sig')
    for key in ('DB_HOST','DB_PORT','DB_USER','DB_PASSWORD','DB_NAME','APP_HOST','APP_PORT',
                'GOLFSCORE_ENV_FILE','TESSERACT_CMD','OPENAI_API_KEY','OPENAI_VISION_MODEL',
                'CLOUDFLARED_PATH',
                'HARULOG_PUBLIC_URL','HARULOG_CONNECTION'):
        if values.get(key) is not None:
            os.environ.setdefault(key, values[key])
    if not re.fullmatch(r'[A-Za-z0-9_]{1,64}', os.getenv('DB_NAME', 'harulog_db')):
        raise RuntimeError('DB_NAME은 영문·숫자·밑줄로 1~64자 입력해 주세요.')
    for key, default in [('DB_PORT','3306'), ('APP_PORT','5000')]:
        try:
            if not 1 <= int(os.getenv(key, default)) <= 65535:
                raise ValueError()
        except ValueError:
            raise RuntimeError(f'{key}는 1~65535 범위여야 합니다.') from None
    if os.getenv('HARULOG_CONNECTION','quick') not in ('quick','fixed','local'):
        raise RuntimeError('HARULOG_CONNECTION은 quick, fixed, local 중 하나로 지정해 주세요.')


def connect_database():
    import db_adapter
    conn = db_adapter.get_connection()
    if conn is None:
        raise RuntimeError('데이터베이스에 연결할 수 없습니다. .env 설정 또는 harulog.db 상태를 확인해 주세요.')
    return conn


def schema_columns(conn):
    cursor = conn.cursor()
    try:
        import sqlite3
        if hasattr(conn, '_conn') and isinstance(conn._conn, sqlite3.Connection):
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r['name'] if isinstance(r, dict) else r[0] for r in cursor.fetchall() if not (r['name'] if isinstance(r, dict) else r[0]).startswith('sqlite_')]
            available = {}
            for t in tables:
                cursor.execute(f"PRAGMA table_info('{t}')")
                available[t] = {r['name'] if isinstance(r, dict) else r[1] for r in cursor.fetchall()}
            return available

        cursor.execute('SELECT TABLE_NAME,COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s',
                       (os.getenv('DB_NAME','harulog_db'),))
        available = {}
        for row in cursor.fetchall():
            table = row['TABLE_NAME'] if isinstance(row, dict) else row[0]
            column = row['COLUMN_NAME'] if isinstance(row, dict) else row[1]
            available.setdefault(table, set()).add(column)
        return available
    finally:
        cursor.close()


def validate_schema(available, include_pets=True):
    missing=[]
    for table, columns in REQUIRED_COLUMNS.items():
        if table in ('pets','pet_records','pet_lineage','app_members','app_system','app_admin_audit') and not include_pets:
            continue
        absent=set(columns.split())-available.get(table,set())
        if absent:
            missing.append(table+': '+', '.join(sorted(absent)))
    if missing:
        raise RuntimeError('기존 DB 구조에 마이그레이션이 필요합니다. 자동 변경하지 않습니다. '
                           'README.md의 별도 마이그레이션 절차를 확인해 주세요. 누락: '+'; '.join(missing))


def prepare_new_features():
    """Only missing independent feature tables may be created during normal startup."""
    conn=connect_database()
    try:
        available=schema_columns(conn)
        # Never bootstrap a wrong/empty DB or repair an existing table implicitly.
        validate_schema(available,include_pets=False)
        import pet_service
        import auth_service
        created=False
        for table,initialize in [('pets',pet_service.init_schema),('pet_records',pet_service.init_records_schema),
                                 ('pet_lineage',pet_service.init_lineage_schema)]:
            if table in available:
                absent=set(REQUIRED_COLUMNS[table].split())-available[table]
                if absent:raise RuntimeError(table+'의 기존 구조에 별도 마이그레이션이 필요합니다.')
            else:
                try:initialize(conn)
                except Exception:raise RuntimeError('신규 '+table+' 테이블 생성에 실패했습니다. DB CREATE 권한을 확인해 주세요.') from None
                created=True
                print('[OK] 신규 기능 테이블 생성: '+table,flush=True)
        auth_tables=('app_members','app_system','app_admin_audit')
        for table in auth_tables:
            if table in available and set(REQUIRED_COLUMNS[table].split())-available[table]:
                raise RuntimeError(table+'의 기존 구조에 별도 마이그레이션이 필요합니다.')
        if any(t not in available for t in auth_tables):
            try:auth_service.init_schema(conn)
            except Exception:raise RuntimeError('회원 관리 테이블 생성에 실패했습니다. DB CREATE 권한을 확인해 주세요.') from None
            created=True
            print('[OK] 회원·권한 관리 신규 테이블 준비 완료. 기존 자료 이관은 실행하지 않았습니다.',flush=True)
        if created:validate_schema(schema_columns(conn))
        if 'cats' in available:
            cursor=conn.cursor()
            try:
                cursor.execute('SELECT COUNT(*) FROM cats')
                cats=cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM pets')
                pets=cursor.fetchone()[0]
                if cats and not pets:
                    print('[NOTICE] 기존 cats 자료가 있습니다. pets로 자동 복사하지 않습니다. '
                          '펫스토리 목록은 현재 비어 있습니다. README.md의 cats-to-pets 마이그레이션을 확인해 주세요.',flush=True)
            finally:
                cursor.close()
    finally:
        conn.close()


def run():
    ensure_config()
    mode=os.getenv('HARULOG_CONNECTION','quick')
    # Validate all required external configuration before attempting any feature DDL.
    if mode!='local':
        import cloudflare_service as cf
        if mode=='quick':cf.find_cloudflared(ROOT)
        else:cf.public_url(os.getenv('HARULOG_PUBLIC_URL',''))
    try:
        prepare_new_features()
    except Exception as error:
        code=getattr(error,'errno',None)
        hints={1049:'DB가 없습니다. 올바른 기존 DB와 .env를 확인해 주세요. 실행 중 DB를 생성하지 않습니다.',
               1045:'DB 계정·비밀번호·권한을 확인해 주세요.',
               2003:'MariaDB 서비스와 DB_HOST/DB_PORT를 확인해 주세요.'}
        if code in hints:raise RuntimeError(hints[code]) from None
        raise
    import main
    import auth_service
    auth_service.announce_setup(main.app,main.get_raw_db_connection,int(os.getenv('APP_PORT','5000')))
    if mode!='local':
        from werkzeug.middleware.proxy_fix import ProxyFix
        main.app.wsgi_app=ProxyFix(main.app.wsgi_app,x_for=0,x_proto=1,x_host=0,x_port=0,x_prefix=0)
    import score_service
    if not score_service.find_tesseract():
        print('[INFO] Tesseract 미설치: OCR 제한. 수동 입력 가능. 설치는 README.md를 확인해 주세요.',flush=True)
    import recognition_service
    key,_=recognition_service.existing_ai_settings()
    if not recognition_service.usable_key(key):
        print('[INFO] AI 키 미연결: AI 기능 제한. 설정은 README.md를 확인해 주세요.',flush=True)
    if mode!='local':
        cf.run(main.app,ROOT,int(os.getenv('APP_PORT','5000')),existing=(mode=='fixed'))
        return
    from waitress import serve
    host,port=os.getenv('APP_HOST','0.0.0.0'),int(os.getenv('APP_PORT','5000'))
    print(f'HaruLog v2.9.13 Local URL: http://127.0.0.1:{port} (bind {host})',flush=True)
    serve(main.app,host=host,port=port,threads=8,max_request_body_size=32*1024*1024)


def main():
    try:
        os.chdir(ROOT)
        if len(sys.argv)>1:
            raise RuntimeError('실행 옵션은 .env에서 설정합니다. 설치/마이그레이션은 README.md의 manage.py 명령을 사용해 주세요.')
        python=require_environment()
        if os.path.normcase(os.path.abspath(sys.executable))!=os.path.normcase(os.path.abspath(python)):
            return subprocess.call([str(python),str(ROOT/'startup.py')])
        run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        print('[ERROR] '+str(error),file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
