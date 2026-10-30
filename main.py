# HaruLog v2.9.17
from flask import Flask, jsonify, request, send_from_directory
import re
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.parse
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading
import study_service
import score_service
import invoice_service
import settings_service
import utility_service
import pet_service
import auth_service
import ownership
from flask import g, has_request_context, abort
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), interpolate=False, encoding='utf-8-sig')

app = Flask(__name__, static_folder='static')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

@app.errorhandler(413)
def upload_too_large(error):
    return jsonify({'error': '첨부 요청은 32MB 이하로 전송해 주세요.'}), 413

def save_uploaded_file(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}" + (f".{ext}" if ext else "")
    dest_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        file.save(dest_path)
    except OSError:
        delete_uploaded_file('/uploads/' + filename)
        raise
    return f"/uploads/{filename}"

def delete_uploaded_file(file_path):
    if not file_path:
        return
    filename = os.path.basename(file_path)
    target = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(target):
        try:
            os.remove(target)
        except OSError:
            app.logger.warning('첨부파일 정리 실패: %s', filename)

import db_adapter

def get_raw_db_connection():
    return db_adapter.get_connection()

def get_db_connection():
    conn=get_raw_db_connection()
    if conn is None:return None
    if has_request_context() and app.config.get('AUTH_ENABLED',True):
        member=getattr(g,'account',None)
        if not member:
            conn.close();abort(401)
        return ownership.Connection(conn,member['id'])
    return conn

def ensure_column(cursor, table, column, definition):
    # 테이블/컬럼/정의는 소스에 고정된 값만 전달합니다.
    cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", (column,))
    if cursor.fetchone() is None:
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


def prepare_schema():
    conn = get_db_connection()
    if conn is None:
        raise RuntimeError('DB 연결 실패: .env 및 MariaDB 실행 상태를 확인해 주세요.')
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                content TEXT NOT NULL,
                file_path VARCHAR(255) NULL,
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        ensure_column(cursor, "daily_logs", "file_path", 'VARCHAR(255) NULL')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_videos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                youtube_id VARCHAR(50) NOT NULL,
                script TEXT NOT NULL,
                language VARCHAR(50) NOT NULL DEFAULT 'ID',
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        ensure_column(cursor, "study_videos", "language", "VARCHAR(50) NOT NULL DEFAULT 'ID'")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vocab_list (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id INT NULL,
                word VARCHAR(100) NOT NULL,
                meaning VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        ensure_column(cursor, "vocab_list", "video_id", 'INT NULL')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_dictations (
                video_id INT PRIMARY KEY,
                content LONGTEXT NOT NULL,
                updated_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')

        conn.commit()
        score_service.init_schema(conn)
        invoice_service.init_schema(conn)
        settings_service.init_schema(conn)
        utility_service.init_schema(conn)
        pet_service.init_schema(conn)
        auth_service.init_schema(conn)
        conn.commit()
        print("명시적으로 요청한 DB 구조 준비 완료. 기존 자료 변환은 수행하지 않았습니다.")
    except Error as e:
        conn.rollback()
        raise RuntimeError("DB 구조 준비 실패: DB 권한과 서버 로그를 확인해 주세요.") from e
    finally:
        if conn.is_connected():
            if cursor is not None:
                cursor.close()
            conn.close()

auth_service.register_routes(app, get_raw_db_connection)
import admin_service
admin_service.register_routes(app, get_raw_db_connection)

@app.route('/')
def index():
    return auth_service.render_home(app)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if app.config.get('AUTH_ENABLED',True):
        conn=get_db_connection()
        if conn is None:abort(503)
        cursor=conn.cursor()
        try:
            owned=False
            for table,column in [('daily_logs','file_path'),('golf_rounds','photo_path'),('expense_invoices','photo_path'),('pets','photo_path'),('pet_records','photo_path')]:
                cursor.execute(f'SELECT id FROM {table} WHERE {column}=%s LIMIT 1',('/uploads/'+filename,))
                if cursor.fetchone():owned=True;break
            if not owned:abort(404)
        finally:cursor.close();conn.close()
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename,
                               as_attachment=filename.rsplit('.', 1)[-1].lower() not in
                               ('jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mp3', 'wav', 'pdf'))

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, content, file_path, created_at FROM daily_logs ORDER BY id DESC')
        logs = cursor.fetchall()
        return jsonify([{
            'id': l['id'],
            'content': l['content'],
            'file_path': l.get('file_path') or '',
            'created_at': l['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        } for l in logs])
    except Error as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

def log_payload():
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get('content', ''), str):
            raise ValueError('올바른 기록 내용을 입력해 주세요.')
        if not isinstance(data.get('remove_file', False), bool):
            raise ValueError('첨부 삭제 여부를 확인해 주세요.')
        return data.get('content', '').strip(), None, data.get('remove_file', False)
    return (request.form.get('content') or '').strip(), request.files.get('file'), request.form.get('remove_file') == 'true'


@app.route('/api/logs', methods=['POST'])
@app.route('/api/logs/<int:log_id>', methods=['PUT', 'POST'])
def save_log(log_id=None):
    try:
        content, file, remove_file = log_payload()
        has_file = bool(file and file.filename)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    new_path = old_path = None
    committed = False
    try:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        if log_id is not None:
            cursor.execute('SELECT id, file_path FROM daily_logs WHERE id=%s FOR UPDATE', (log_id,))
            row = cursor.fetchone()
            if row is None:
                return jsonify({'error': '해당 기록을 찾을 수 없습니다.'}), 404
            old_path = row['file_path']
        if not content and not has_file and (remove_file or not old_path):
            return jsonify({'error': '내용 또는 파일을 입력해 주세요.'}), 400
        if has_file:
            new_path = save_uploaded_file(file)
        stored_path = new_path or (None if remove_file else old_path)
        if log_id is None:
            cursor.execute('INSERT INTO daily_logs (content,file_path,created_at) VALUES (%s,%s,%s)',
                           (content, stored_path, datetime.now()))
            log_id = cursor.lastrowid
            status = 201
        else:
            cursor.execute('UPDATE daily_logs SET content=%s,file_path=%s WHERE id=%s',
                           (content, stored_path, log_id))
            status = 200
        conn.commit()
        committed = True
        if old_path and old_path != stored_path:
            delete_uploaded_file(old_path)
        return jsonify({'status': 'success', 'log': {'id': log_id, 'content': content, 'file_path': stored_path or ''}}), status
    except (Error, OSError):
        conn.rollback()
        app.logger.exception('기록 저장 실패')
        return jsonify({'error': '기록을 저장하지 못했습니다.'}), 500
    finally:
        if not committed and new_path:
            delete_uploaded_file(new_path)
        if cursor is not None:
            cursor.close()
        conn.close()


@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, file_path FROM daily_logs WHERE id=%s FOR UPDATE', (log_id,))
        row = cursor.fetchone()
        if row is None:
            return jsonify({'error': '해당 기록을 찾을 수 없습니다.'}), 404
        cursor.execute('DELETE FROM daily_logs WHERE id=%s', (log_id,))
        conn.commit()
        delete_uploaded_file(row['file_path'])
        return jsonify({'status': 'success'})
    except Error:
        conn.rollback()
        app.logger.exception('기록 삭제 실패')
        return jsonify({'error': '기록을 삭제하지 못했습니다.'}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


@app.route('/api/study/videos', methods=['GET'])
def get_videos():
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        lang = request.args.get('language', '').strip()
        if lang and lang != '전체':
            cursor.execute('SELECT id, title, youtube_id, script, language FROM study_videos WHERE language = %s ORDER BY id DESC', (lang,))
        else:
            cursor.execute('SELECT id, title, youtube_id, script, language FROM study_videos ORDER BY id DESC')
        return jsonify(cursor.fetchall())
    except Error as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

def extract_youtube_id(url):
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url):
        return url
    parsed = urlparse(url if '://' in url else 'https://' + url)
    if parsed.scheme not in ('http', 'https'):
        return None
    host = (parsed.hostname or '').lower()
    parts = parsed.path.strip('/').split('/')
    video_id = ''
    if host in ('youtu.be', 'www.youtu.be'):
        video_id = parts[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
                  'youtube-nocookie.com', 'www.youtube-nocookie.com'):
        if parsed.path.rstrip('/') == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in ('shorts', 'embed', 'live'):
            video_id = parts[1]
    return video_id if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id) else None


def normalize_lang_code(val):
    if not val: return 'ID'
    v = str(val).strip()
    vu = v.upper()
    if vu in ('ID', 'US', 'JP', 'CN', 'ETC'): return vu
    if '인도네시아' in v: return 'ID'
    if '영어' in v or vu == 'EN': return 'US'
    if '일본' in v or vu == 'JA': return 'JP'
    if '중국' in v or vu == 'ZH': return 'CN'
    return 'ETC'

@app.route('/api/study/videos', methods=['POST'])
def add_video():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or any(not isinstance(data.get(k), str) for k in ('title', 'url', 'script')):
        return jsonify({'error': '제목, 유튜브 주소, 스크립트를 입력해 주세요.'}), 400
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    script = data.get('script', '').strip()
    language = normalize_lang_code(data.get('language', 'ID'))
    
    youtube_id = extract_youtube_id(url)
        
    if not title or not url or not script:
        return jsonify({'error': '모든 필드를 입력해 주세요.'}), 400
    if not youtube_id:
        return jsonify({'error': '올바른 유튜브 주소 또는 11자리 영상 ID를 입력해 주세요.'}), 400
    if len(title) > 255:
        return jsonify({'error': '영상 제목은 255자 이내로 입력해 주세요.'}), 400
        
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패: 서버의 MariaDB 설정을 확인해 주세요.'}), 503
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO study_videos (title, youtube_id, script, language, created_at) VALUES (%s, %s, %s, %s, %s)', 
                       (title, youtube_id, script, language, datetime.now()))
        conn.commit()
        return jsonify({'status': 'success'}), 201
    except Error:
        conn.rollback()
        app.logger.exception('영상 등록 실패')
        return jsonify({'error': '영상 저장에 실패했습니다. 서버 로그를 확인해 주세요.'}), 500
    finally:
        if cursor is not None: cursor.close()
        conn.close()

@app.route('/api/study/videos/<int:video_id>', methods=['PUT'])
def update_video(video_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or any(not isinstance(data.get(k), str) for k in ('title', 'url', 'script')):
        return jsonify({'error': '제목, 유튜브 주소, 스크립트를 입력해 주세요.'}), 400
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    script = data.get('script', '').strip()
    language = normalize_lang_code(data.get('language', 'ID'))
    
    youtube_id = extract_youtube_id(url)
        
    if not title or not url or not script:
        return jsonify({'error': '모든 필드를 입력해 주세요.'}), 400
    if not youtube_id:
        return jsonify({'error': '올바른 유튜브 주소 또는 11자리 영상 ID를 입력해 주세요.'}), 400
    if len(title) > 255:
        return jsonify({'error': '영상 제목은 255자 이내로 입력해 주세요.'}), 400
        
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패: 서버의 MariaDB 설정을 확인해 주세요.'}), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id FROM study_videos WHERE id = %s', (video_id,))
        if cursor.fetchone() is None:
            return jsonify({'error': '해당 영상을 찾을 수 없습니다.'}), 404

        cursor.execute(
            'UPDATE study_videos SET title = %s, youtube_id = %s, script = %s, language = %s WHERE id = %s',
            (title, youtube_id, script, language, video_id)
        )
        conn.commit()
        return jsonify({
            'status': 'success',
            'video': {
                'id': video_id,
                'title': title,
                'youtube_id': youtube_id,
                'script': script,
                'language': language
            }
        })
    except Error:
        conn.rollback()
        app.logger.exception('영상 수정 실패')
        return jsonify({'error': '영상 수정에 실패했습니다. 서버 로그를 확인해 주세요.'}), 500
    finally:
        if cursor is not None: cursor.close()
        conn.close()

@app.route('/api/study/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify(error='DB 연결 실패: 서버의 MariaDB 설정을 확인해 주세요.'), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id FROM study_videos WHERE id = %s FOR UPDATE', (video_id,))
        if cursor.fetchone() is None:
            return jsonify(error='해당 영상을 찾을 수 없습니다.'), 404
        cursor.execute('DELETE FROM vocab_list WHERE video_id = %s', (video_id,))
        cursor.execute('DELETE FROM study_dictations WHERE video_id = %s', (video_id,))
        cursor.execute('DELETE FROM study_videos WHERE id = %s', (video_id,))
        conn.commit()
        return jsonify(status='success')
    except Exception:
        conn.rollback()
        app.logger.exception('영상 삭제 실패')
        return jsonify(error='영상 삭제에 실패했습니다. 서버 로그를 확인해 주세요.'), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

# 인도네시아어 및 영어 일상 핵심 사전
ID_KO_DICT = {
    'saya': '나, 저', 'aku': '나', 'kamu': '너, 당신', 'anda': '당신, 귀하',
    'dia': '그, 그녀', 'mereka': '그들', 'kita': '우리 (듣는이 포함)', 'kami': '우리 (듣는이 제외)',
    'ini': '이것, 이', 'itu': '저것, 그', 'apa': '무엇', 'siapa': '누구',
    'kapan': '언제', 'dimana': '어디에서', 'di mana': '어디에서', 'kemana': '어디로', 'ke mana': '어디로',
    'bagaimana': '어떻게', 'mengapa': '왜', 'kenapa': '왜', 'berapa': '얼마, 몇',
    'ya': '네', 'tidak': '아니다, 안 하다', 'bukan': '아니다 (~가 아님)', 'belum': '아직',
    'sudah': '이미, 벌써', 'akan': '할 것이다', 'bisa': '할 수 있다', 'boleh': '해도 좋다',
    'mau': '원하다, ~할 것이다', 'ingin': '바라다, 싶다', 'harus': '해야 한다',
    'ada': '있다', 'tidak ada': '없다', 'jadi': '그래서, 되다', 'karena': '때문에',
    'tetapi': '하지만', 'tapi': '하지만', 'dan': '그리고', 'atau': '또는',
    'dengan': '~와 함께, ~로', 'untuk': '~를 위해', 'dari': '~로부터', 'ke': '~로', 'di': '~에, ~에서',
    'hari': '날, 하루', 'hari ini': '오늘', 'kemarin': '어제', 'besok': '내일',
    'pagi': '아침', 'siang': '낮, 정오', 'sore': '오후', 'malam': '밤, 저녁',
    'jam': '시, 시간', 'waktu': '시간, 때', 'menit': '분', 'detik': '초',
    'minggu': '주, 일요일', 'bulan': '달, 월', 'tahun': '년, 해',
    'senang': '기쁜, 좋다', 'baik': '좋은, 잘', 'bagus': '멋진, 훌륭한', 'buruk': '나쁜',
    'besar': '큰', 'kecil': '작은', 'banyak': '많은', 'sedikit': '적은',
    'baru': '새로운', 'lama': '오래된, 오래 걸리는', 'cepat': '빠른', 'lambat': '느린',
    'mahal': '비싼', 'murah': '저렴한', 'mudah': '쉬운', 'susah': '어려운, 힘든', 'sulit': '어려운',
    'makan': '먹다', 'minum': '마시다', 'tidur': '자다', 'bangun': '일어나다',
    'pergi': '가다', 'datang': '오다', 'pulang': '귀가하다', 'jalan': '길, 걷다',
    'belajar': '공부하다', 'bekerja': '일하다', 'kerja': '일', 'istirahat': '쉬다, 휴식',
    'bicara': '말하다', 'kata': '단어, 말', 'tahu': '알다', 'mengerti': '이해하다',
    'paham': '이해하다', 'membaca': '읽다', 'menulis': '쓰다', 'mendengar': '듣다', 'melihat': '보다',
    'membeli': '사다', 'beli': '사다', 'menjual': '팔다', 'jual': '팔다', 'bayar': '지불하다',
    'uang': '돈', 'harga': '가격', 'toko': '가게', 'pasar': '시장', 'kantor': '사무실', 'rumah': '집',
    'kamar': '방', 'toilet': '화장실', 'hotel': '호텔', 'sekolah': '학교', 'stasiun': '역', 'bandara': '공항',
    'teman': '친구', 'keluarga': '가족', 'orang': '사람', 'anak': '아이, 자녀', 'ibu': '어머니, 사모님', 'bapak': '아버지, 선생님',
    'terima kasih': '감사합니다', 'sama-sama': '천만에요', 'maaf': '죄송합니다', 'permisi': '실례합니다',
    'tolong': '부탁합니다, 도와주세요', 'selamat': '축하, 안녕', 'selamat pagi': '좋은 아침',
    'selamat siang': '좋은 낮', 'selamat sore': '좋은 오후', 'selamat malam': '좋은 밤',
    'selamat jalan': '안녕히 가세요', 'selamat tinggal': '안녕히 계세요', 'sampai jumpa': '또 만나요',
    'sekarang': '지금', 'nanti': '나중에', 'tadi': '방금, 아까', 'selalu': '항상', 'sering': '자주',
    'kadang-kadang': '때때로', 'jarang': '드물게', 'tidak pernah': '결코 아닌', 'semua': '모든',
    'saja': '오직, 그냥', 'hanya': '오직, 단지', 'juga': '또한', 'lagi': '다시, 더',
    'sangat': '매우', 'sekali': '매우, 한번', 'terlalu': '너무, 지나치게', 'kurang': '부족한',
    'masalah': '문제', 'tidak apa-apa': '괜찮아요', 'tentu': '물론', 'mungkin': '아마도',
    'benar': '맞는, 진짜', 'salah': '틀린, 잘못'
}

BASIC_DICT = {
    'apple': '사과', 'book': '책', 'cat': '고양이', 'dog': '개', 'elephant': '코끼리',
    'friend': '친구', 'good': '좋은', 'happy': '행복한', 'house': '집', 'important': '중요한',
    'journey': '여정/여행', 'knowledge': '지식', 'learn': '배우다', 'morning': '아침', 'nature': '자연',
    'opportunity': '기회', 'people': '사람들', 'question': '질문', 'remember': '기억하다', 'study': '공부하다',
    'time': '시간', 'understand': '이해하다', 'victory': '승리', 'water': '물', 'yesterday': '어제',
    'convenient': '편리한', 'conversation': '대화', 'practice': '연습하다', 'listen': '듣다', 'speak': '말하다',
    'pronunciation': '발음', 'vocabulary': '어휘/단어', 'grammar': '문법', 'sentence': '문장', 'expression': '표현',
    'beautiful': '아름다운', 'difficult': '어려운', 'easy': '쉬운', 'challenge': '도전', 'success': '성공',
    'habit': '습관', 'daily': '매일의/일상', 'routine': '루틴/일과', 'improve': '향상시키다', 'focus': '집중하다',
    'nihon': '일본', 'arigatou': '감사합니다', 'ohayou': '좋은아침'
}

DICT_CACHE = {}
DICT_CACHE_LOCK = threading.Lock()

def translate_word_to_korean(word, lang='ID'):
    """내장 사전 확인 후, 없으면 무료 웹 번역 API로 실시간 한국어 뜻 조회 및 캐시."""
    w_clean = word.strip().lower()
    if not w_clean: return ''
    
    # 1. 인도네시아어 또는 영어 내장 사전 확인
    if lang == 'ID' and w_clean in ID_KO_DICT:
        return ID_KO_DICT[w_clean]
    if lang == 'US' and w_clean in BASIC_DICT:
        return BASIC_DICT[w_clean]
    
    # 2. 캐시 확인
    cache_key = f"{lang}:{w_clean}"
    with DICT_CACHE_LOCK:
        if cache_key in DICT_CACHE:
            return DICT_CACHE[cache_key]
        
    # 3. 실시간 번역 API 호출
    lang_map = {'ID': 'id', 'US': 'en', 'JP': 'ja', 'CN': 'zh-CN', 'ETC': 'auto'}
    sl = lang_map.get(lang.upper(), 'auto')
    try:
        url = f'https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl=ko&dt=t&q={urllib.parse.quote(word)}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            translated = ''.join([part[0] for part in data[0] if part and part[0]]).strip()
            if translated:
                with DICT_CACHE_LOCK:
                    if len(DICT_CACHE) >= 3000:
                        DICT_CACHE.pop(next(iter(DICT_CACHE)))
                    DICT_CACHE[cache_key] = translated
                return translated
    except Exception:
        pass
    return ''

@app.route('/api/study/videos/<int:video_id>/vocab/generate', methods=['POST'])
def generate_video_vocab(video_id):
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, title, script, language FROM study_videos WHERE id = %s', (video_id,))
        video = cursor.fetchone()
        if not video:
            return jsonify({'error': '영상을 찾을 수 없습니다.'}), 404

        video_lang = normalize_lang_code(video.get('language'))

        req_data = request.get_json(silent=True)
        if req_data is None:
            req_data = {}
        if not isinstance(req_data, dict):
            return jsonify({'error': '올바른 단어 목록을 전송해 주세요.'}), 400
        custom_words = req_data.get('words')

        if 'words' in req_data:
            words = study_service.validate_words(custom_words)
            # 영상 행 잠금으로 같은 영상의 동시 일괄 저장도 순서대로 처리합니다.
            conn.rollback()
            cursor.execute('SELECT id FROM study_videos WHERE id=%s FOR UPDATE', (video_id,))
            if cursor.fetchone() is None:
                return jsonify({'error': '영상을 찾을 수 없습니다.'}), 404
            saved_count = skipped_count = 0
            for w, m in words:
                if study_service.insert_word(cursor, video_id, w, m):
                    saved_count += 1
                else:
                    skipped_count += 1
            conn.commit()
            return jsonify({'status': 'success', 'saved_count': saved_count, 'skipped_count': skipped_count})

        # 외부 번역 중에는 DB 연결을 유지하지 않습니다.
        cursor.close()
        cursor = None
        conn.close()
        conn = None
        # 스크립트에서 자동 추출 분석
        script = video['script'] or ''
        extracted = []
        seen = set()

        # 1. 줄 단위 "단어 : 뜻" 패턴 (예: "makan : 먹다" 또는 "rumah - 집")
        for line in script.splitlines():
            line = line.strip()
            if not line: continue
            match = re.match(r'^([A-Za-z0-9가-힣ぁ-んァ-ヶ一-龥\s]{2,40})\s*[:=\-–—]\s*(.+)$', line)
            if match and re.search(r'[가-힣]', match[2]):
                w = match[1].strip()
                m = match[2].strip()
                if w.lower() not in seen and len(w) <= 100:
                    seen.add(w.lower())
                    extracted.append({'word': w, 'meaning': m[:255]})
                    if len(extracted) >= 30:
                        break

        # 2. 스크립트에서 단어 토큰 추출 및 사전/번역 매핑
        tokens = study_service.extract_tokens(script, video_lang)
        selected = []
        for token in tokens:
            if len(extracted) + len(selected) >= 30:
                break
            low = token.lower()
            if low not in seen:
                seen.add(low)
                selected.append(token)
            if len(extracted) + len(selected) >= 30:
                break
        with ThreadPoolExecutor(max_workers=5) as pool:
            meanings = pool.map(lambda word: translate_word_to_korean(word, video_lang), selected)
            extracted.extend({'word': word, 'meaning': meaning} for word, meaning in zip(selected, meanings))
        extracted = extracted[:30]

        return jsonify({
            'video_id': video_id,
            'title': video['title'],
            'language': video_lang,
            'extracted_words': extracted
        })
    except Error:
        if conn is not None:
            conn.rollback()
        app.logger.exception('단어장 생성 실패')
        return jsonify({'error': '단어장 생성 중 오류가 발생했습니다.'}), 500
    except ValueError as error:
        if conn is not None:
            conn.rollback()
        return jsonify({'error': str(error)}), 400
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@app.route('/api/study/vocab', methods=['GET'])
def get_vocab():
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        video_id = request.args.get('video_id')
        search_q = request.args.get('q', '').strip().lower()

        sql = '''SELECT v.id, v.video_id, v.word, v.meaning, v.created_at, s.title as video_title
                 FROM vocab_list v LEFT JOIN study_videos s ON v.video_id = s.id'''
        params = []
        conditions = []

        if video_id:
            conditions.append('v.video_id = %s')
            params.append(video_id)

        if search_q:
            conditions.append('(LOWER(v.word) LIKE %s OR LOWER(v.meaning) LIKE %s OR LOWER(COALESCE(s.title, "")) LIKE %s)')
            like_val = f"%{search_q}%"
            params.extend([like_val, like_val, like_val])

        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)

        # 사용자 요청: 단어는 항상 알파벳순(A-Z)으로 조회
        sql += ' ORDER BY LOWER(v.word) ASC, v.id DESC'

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for r in rows:
            if r['created_at']:
                r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(rows)
    except Error as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

@app.route('/api/study/vocab', methods=['POST'])
def add_vocab():
    data = request.get_json(silent=True)
    try:
        if not isinstance(data, dict):
            raise ValueError('올바른 단어를 입력해 주세요.')
        word, meaning = study_service.validate_words([data])[0]
        video_id = data.get('video_id')
        if video_id not in (None, ''):
            if isinstance(video_id, bool) or not re.fullmatch(r'[1-9][0-9]*', str(video_id)):
                raise ValueError('영상 번호를 확인해 주세요.')
            video_id = int(video_id)
        else:
            video_id = None
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        if video_id is not None:
            cursor.execute('SELECT id FROM study_videos WHERE id=%s FOR UPDATE', (video_id,))
            if cursor.fetchone() is None:
                return jsonify({'error': '영상을 찾을 수 없습니다.'}), 404
        else:
            # 일반 단어 저장도 사용자 프로필의 고정 행을 잠가 직렬화합니다.
            cursor.execute("INSERT IGNORE INTO personal_profile (id,name,nickname,updated_at) VALUES (1,'','',%s)", (datetime.now(),))
            cursor.execute('SELECT id FROM personal_profile WHERE id=1 FOR UPDATE')
            cursor.fetchone()
        if not study_service.insert_word(cursor, video_id, word, meaning):
            return jsonify({'error': '같은 영상(또는 일반 단어장)에 이미 등록된 단어입니다.'}), 409
        conn.commit()
        return jsonify({'status': 'success'}), 201
    except Error:
        conn.rollback()
        app.logger.exception('단어 저장 실패')
        return jsonify({'error': '단어를 저장하지 못했습니다.'}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

@app.route('/api/study/vocab/<int:vocab_id>', methods=['DELETE'])
def delete_vocab(vocab_id):
    conn = get_db_connection()
    if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM vocab_list WHERE id = %s', (vocab_id,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Error as e: return jsonify({'error': str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

# HaruLog v2.9.17 — 영상별 받아쓰기 조회·갱신 저장
@app.route('/api/study/videos/<int:video_id>/dictation', methods=['GET', 'PUT'])
def video_dictation(video_id):
    content = None
    if request.method == 'PUT':
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get('content'), str):
            return jsonify({'error': '올바른 받아쓰기 내용을 전송해 주세요.'}), 400
        content = data['content']

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'DB 연결에 실패했습니다.'}), 503

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id FROM study_videos WHERE id = %s', (video_id,))
        if cursor.fetchone() is None:
            return jsonify({'error': '등록된 영상이 없습니다.'}), 404

        if request.method == 'GET':
            cursor.execute(
                'SELECT content FROM study_dictations WHERE video_id = %s',
                (video_id,)
            )
            row = cursor.fetchone()
            return jsonify({'content': row['content'] if row else ''})

        cursor.execute('''
            INSERT INTO study_dictations (video_id, content, updated_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                content = VALUES(content),
                updated_at = VALUES(updated_at)
        ''', (video_id, content, datetime.now()))
        conn.commit()
        return jsonify({'status': 'success'})
    except Error:
        conn.rollback()
        app.logger.exception('받아쓰기 조회·저장 실패')
        return jsonify({'error': '받아쓰기 처리에 실패했습니다. 서버 로그를 확인해 주세요.'}), 500
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

score_service.register_routes(app, get_db_connection)
invoice_service.register_routes(app, get_db_connection)
settings_service.register_routes(app, get_db_connection)
utility_service.register_routes(app, get_db_connection)
pet_service.register_routes(app, get_db_connection, save_uploaded_file, delete_uploaded_file)

if __name__ == '__main__':
    import startup
    raise SystemExit(startup.main())
