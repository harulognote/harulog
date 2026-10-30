"""HaruLog v1.9.0: 라운드 관리 및 로컬 스코어카드 OCR."""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import warnings
import recognition_service
import hashlib
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature
from datetime import date, datetime
from pathlib import Path

from flask import jsonify, request
from mysql.connector import Error
try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ModuleNotFoundError:
    Image = ImageOps = None
    UnidentifiedImageError = OSError

OCR_TICKETS = URLSafeTimedSerializer(secrets.token_hex(32), salt='golf-ocr-review')

def image_digest(image):
    return hashlib.sha256(image.tobytes() + str(image.size).encode()).hexdigest()

def ocr_ticket(image):
    return OCR_TICKETS.dumps({'image':image_digest(image)})

def valid_ocr_ticket(image, token):
    try:
        return OCR_TICKETS.loads(token, max_age=600).get('image') == image_digest(image)
    except (BadSignature, TypeError, ValueError):
        return False

MAX_PHOTO_BYTES = 12 * 1024 * 1024


def init_schema(conn):
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS golf_rounds (
            id INT AUTO_INCREMENT PRIMARY KEY,
            played_on DATE NOT NULL,
            course_name VARCHAR(150) NOT NULL,
            golf_club VARCHAR(150) NOT NULL DEFAULT '',
            player_name VARCHAR(100) NOT NULL DEFAULT '본인',
            front_score SMALLINT NOT NULL,
            back_score SMALLINT NOT NULL,
            companions_json TEXT NOT NULL,
            memo TEXT NOT NULL,
            photo_path VARCHAR(255) NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            INDEX idx_golf_played_on (played_on, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
        for column,definition in [('player_nickname',"VARCHAR(100) NOT NULL DEFAULT ''"),('hole_scores_json','TEXT NULL')]:
            cursor.execute(f"SHOW COLUMNS FROM golf_rounds LIKE '{column}'")
            if cursor.fetchone() is None:
                cursor.execute(f'ALTER TABLE golf_rounds ADD COLUMN {column} {definition}')
        cursor.execute("SHOW COLUMNS FROM golf_rounds LIKE 'golf_club'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE golf_rounds ADD COLUMN golf_club VARCHAR(150) NOT NULL DEFAULT ''")
    finally:
        cursor.close()


def positive_int(value, field, maximum):
    if isinstance(value, bool) or not re.fullmatch(r'\d+', str(value or '')):
        raise ValueError(f'{field}은 정수로 입력해 주세요.')
    value = int(value)
    if not 1 <= value <= maximum:
        raise ValueError(f'{field}은 1~{maximum} 범위로 입력해 주세요.')
    return value


def validate_round(data):
    if not isinstance(data, dict):
        raise ValueError('올바른 라운드 정보를 입력해 주세요.')
    def string(key, maximum, required=False, default=''):
        value = data.get(key, default)
        if not isinstance(value, str):
            raise ValueError('문자 입력값을 확인해 주세요.')
        value = value.strip()
        if (required and not value) or len(value) > maximum:
            raise ValueError(f'{key} 입력값을 확인해 주세요. (최대 {maximum}자)')
        return value
    played_on = string('played_on', 10, True)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', played_on):
        raise ValueError('라운드 날짜를 확인해 주세요.')
    try:
        date.fromisoformat(played_on)
    except ValueError:
        raise ValueError('라운드 날짜를 확인해 주세요.') from None
    companions = data.get('companions', [])
    if not isinstance(companions, list) or len(companions) > 20:
        raise ValueError('동반자는 최대 20명까지 입력해 주세요.')
    clean = []
    for row in companions:
        if not isinstance(row, dict) or not isinstance(row.get('name'), str):
            raise ValueError('동반자 이름을 확인해 주세요.')
        name = row['name'].strip()
        if not name or len(name) > 100:
            raise ValueError('동반자 이름은 1~100자로 입력해 주세요.')
        nickname = row.get('nickname', '')
        if not isinstance(nickname, str) or len(nickname.strip()) > 100:
            raise ValueError('동반자 별명은 100자 이내로 입력해 주세요.')
        contact_id = row.get('contact_id')
        if contact_id is not None:contact_id=positive_int(contact_id, '동반자 번호', 2147483647)
        clean.append({'name': name, 'nickname': nickname.strip(), 'contact_id':contact_id, 'total_score': positive_int(row.get('total_score'), '동반자 총점', 400)})
    golf_club = string('golf_club', 150)
    course_name = string('course_name', 150)
    if not golf_club and not course_name:
        raise ValueError('골프장명 또는 기존 코스명을 입력해 주세요.')
    hole_scores=data.get('hole_scores')
    if hole_scores is not None:
        if not isinstance(hole_scores,list) or len(hole_scores)!=18:
            raise ValueError('1~18홀 점수를 모두 입력해 주세요.')
        hole_scores=[positive_int(value,f'{i+1}홀 점수',99) for i,value in enumerate(hole_scores)]
        front_score,back_score=sum(hole_scores[:9]),sum(hole_scores[9:])
    else:
        front_score=positive_int(data.get('front_score'),'전반 점수',891)
        back_score=positive_int(data.get('back_score'),'후반 점수',891)
    return {
        'played_on': played_on,
        'player_nickname':string('player_nickname',100),
        'hole_scores':hole_scores,
        'golf_club': golf_club,
        'course_name': course_name,
        'player_name': string('player_name', 100) or '본인',
        'front_score': front_score,
        'back_score': back_score,
        'companions': clean,
        'memo': string('memo', 5000),
    }


def read_photo(file):
    if Image is None:
        raise ValueError('사진 처리 패키지 Pillow가 없습니다. 실행 배치파일로 패키지를 설치하거나 pip install -r requirements.txt를 실행해 주세요.')
    if not file or not file.filename:
        raise ValueError('스코어카드 사진을 선택해 주세요.')
    content = file.stream.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        raise ValueError('사진은 12MB 이하로 선택해 주세요.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValueError('JPG, PNG, WEBP 사진을 선택해 주세요.')
                if source.width * source.height > 25_000_000:
                    raise ValueError('사진 해상도가 너무 큽니다. 2,500만 화소 이하로 줄여 주세요.')
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((4000, 4000))
                return image
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('읽을 수 없는 사진입니다. JPG 또는 PNG로 변환해 주세요.') from None


def extract_candidates(text):
    """명확한 전후반/총점 또는 18홀 숫자 행만 후보로 반환. 사용자가 선택."""
    candidates = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or re.search(r'\b(?:hole|par|hdcp|handicap|yard|meter)\b', line, re.I):
            continue
        front = re.search(r'(?:OUT|FRONT|전반)\s*[:=]?\s*(\d{2,3})', line, re.I)
        back = re.search(r'(?:IN|BACK|후반)\s*[:=]?\s*(\d{2,3})', line, re.I)
        pair = None
        verified_holes = False
        if front and back:
            pair = (int(front[1]), int(back[1]))
        else:
            # 숫자가 붙은 이름·날짜·홀번호를 점수 행으로 오인하지 않도록 전체 행을 검사.
            match = re.fullmatch(r'([^\d]*?)\s*((?:\d+\s*[|,;\s]+)+\d+)\s*', line)
            if match:
                nums = [int(n) for n in re.findall(r'\d+', match[2])]
                if len(nums) == 3 and nums[0] + nums[1] == nums[2]:
                    pair = (nums[0], nums[1])
                elif len(nums) == 18 and all(1 <= n <= 15 for n in nums) and sum(nums) > 54:
                    pair = (sum(nums[:9]), sum(nums[9:]))
                elif len(nums) in (20, 21):
                    holes = nums[:9] + nums[10:19]
                    if all(1 <= n <= 15 for n in holes) and sum(nums[:9]) == nums[9] and sum(nums[10:19]) == nums[19]:
                        if len(nums) == 20 or nums[20] == nums[9] + nums[19]:
                            pair = (nums[9], nums[19])
                            verified_holes = True
        if pair and all(10 <= n <= 200 for n in pair):
            candidates.append({'label': line[:250], 'front_score': pair[0], 'back_score': pair[1], 'total_score': sum(pair), 'verified_holes': verified_holes})
    return candidates[:30]


def find_tesseract():
    configured = os.getenv('TESSERACT_CMD', '').strip().strip('"')
    if configured:
        if Path(configured).is_file(): return configured
        command = shutil.which(configured)
        if command: return command
    command = shutil.which('tesseract')
    if command: return command
    for root in (os.getenv('ProgramFiles'), os.getenv('ProgramFiles(x86)'), os.getenv('LOCALAPPDATA')):
        if root:
            for relative in ('Tesseract-OCR/tesseract.exe', 'Programs/Tesseract-OCR/tesseract.exe'):
                path = Path(root) / relative
                if path.is_file(): return str(path)
    path = Path(__file__).resolve().parent / 'tools' / 'Tesseract-OCR' / 'tesseract.exe'
    return str(path) if path.is_file() else None


def run_ocr(image):
    command = find_tesseract()
    if not command:
        raise RuntimeError('Tesseract OCR 실행 파일이 없습니다. Tesseract를 설치하거나 기존 설치 경로를 TESSERACT_CMD에 지정해 주세요. 기본 설치 위치는 자동 탐색합니다. 직접 입력과 사진 첨부도 가능합니다.')
    with tempfile.TemporaryDirectory(prefix='harulog_ocr_') as folder:
        filename = str(Path(folder) / 'card.png')
        ImageOps.autocontrast(ImageOps.grayscale(image)).save(filename)
        try:
            result = subprocess.run([command, filename, 'stdout', '-l', 'eng', '--psm', '6'],
                                    capture_output=True, timeout=45, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError('사진 인식 실행에 실패했거나 시간이 초과되었습니다. OCR 설치 경로 또는 사진을 확인해 주세요.') from None
        if result.returncode:
            raise RuntimeError('사진 인식에 실패했습니다. Tesseract의 eng 언어 데이터를 확인해 주세요.')
        return result.stdout.decode('utf-8', errors='replace').strip()


def ocr_result(image):
    text = run_ocr(image)
    candidates = extract_candidates(text)
    reasons = recognition_service.golf_ocr_check(candidates)
    return {'text':text, 'candidates':candidates, 'source':'OCR', 'needs_review':bool(reasons), 'review_reasons':reasons}


def register_routes(app, get_conn):
    def photo_file():
        return request.files.get('photo')

    def delete_photo(path):
        if path and path.startswith('/uploads/golf_'):
            Path(app.config['UPLOAD_FOLDER'], os.path.basename(path)).unlink(missing_ok=True)

    def save_photo(image):
        filename = f'golf_{uuid.uuid4().hex}.jpg'
        image.save(Path(app.config['UPLOAD_FOLDER']) / filename, format='JPEG', quality=90)
        return '/uploads/' + filename

    def payload():
        if request.is_json:
            return request.get_json(silent=True)
        try:
            return json.loads(request.form.get('data', ''))
        except (ValueError, TypeError):
            raise ValueError('올바른 라운드 정보를 전송해 주세요.') from None

    @app.route('/api/golf/rounds', methods=['GET'])
    def list_golf_rounds():
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결에 실패했습니다.'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM golf_rounds ORDER BY played_on DESC, id DESC')
            rows = cursor.fetchall()
            for row in rows:
                row['played_on'] = row['played_on'].isoformat()
                row['companions'] = json.loads(row.pop('companions_json'))
                row['hole_scores']=json.loads(row.pop('hole_scores_json')) if row.get('hole_scores_json') else None
                row.pop('hole_scores_json',None)
                row['total_score'] = row['front_score'] + row['back_score']
                for key in ('created_at', 'updated_at'):
                    row[key] = row[key].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(rows)
        except (Error, ValueError):
            app.logger.exception('라운드 목록 조회 실패')
            return jsonify({'error': '라운드 목록을 불러오지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/golf/rounds', methods=['POST'])
    @app.route('/api/golf/rounds/<int:round_id>', methods=['PUT'])
    def save_golf_round(round_id=None):
        try:
            data = validate_round(payload())
            image = read_photo(photo_file()) if photo_file() and photo_file().filename else None
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결에 실패했습니다.'}), 503
        cursor = None
        new_photo = old_photo = None
        committed = False
        try:
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            if round_id is not None:
                cursor.execute('SELECT photo_path,front_score,back_score,hole_scores_json FROM golf_rounds WHERE id = %s FOR UPDATE', (round_id,))
                row = cursor.fetchone()
                if row is None:
                    return jsonify({'error': '라운드가 없습니다.'}), 404
                old_photo = row['photo_path']
                if data['hole_scores'] is None:
                    if row['hole_scores_json']:
                        return jsonify({'error':'기존 홀별 점수는 모두 입력하여 수정해 주세요.'}),400
                    data['front_score'],data['back_score']=row['front_score'],row['back_score']
            elif data['hole_scores'] is None:
                return jsonify({'error':'새 라운드는 1~18홀 점수를 모두 입력해 주세요.'}),400
            if image:
                new_photo = save_photo(image)
            remove_photo = request.form.get('remove_photo') == '1'
            stored_photo = new_photo or (None if remove_photo else old_photo)
            values = (data['played_on'], data['course_name'], data['golf_club'], data['player_name'], data['front_score'], data['back_score'],
                      json.dumps(data['companions'], ensure_ascii=False), data['memo'], stored_photo, datetime.now(), data['player_nickname'], json.dumps(data['hole_scores']) if data['hole_scores'] is not None else None)
            if round_id is None:
                cursor.execute('''INSERT INTO golf_rounds (played_on, course_name, golf_club, player_name, front_score, back_score,
                    companions_json, memo, photo_path, updated_at, player_nickname, hole_scores_json, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', values + (datetime.now(),))
                round_id = cursor.lastrowid
            else:
                cursor.execute('''UPDATE golf_rounds SET played_on=%s, course_name=%s, golf_club=%s, player_name=%s, front_score=%s,
                    back_score=%s, companions_json=%s, memo=%s, photo_path=%s, updated_at=%s, player_nickname=%s, hole_scores_json=%s WHERE id=%s''', values + (round_id,))
            conn.commit()
            committed = True
            if old_photo and old_photo != stored_photo:
                try:
                    delete_photo(old_photo)
                except OSError:
                    app.logger.warning('이전 스코어카드 사진 정리 실패')
            return jsonify({'status': 'success', 'id': round_id}), 201 if request.method == 'POST' else 200
        except (Error, OSError):
            conn.rollback()
            app.logger.exception('라운드 저장 실패')
            return jsonify({'error': '라운드를 저장하지 못했습니다.'}), 500
        finally:
            if not committed and new_photo:
                try:
                    delete_photo(new_photo)
                except OSError:
                    app.logger.warning('미저장 스코어카드 사진 정리 실패')
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/golf/rounds/<int:round_id>', methods=['DELETE'])
    def delete_golf_round(round_id):
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결에 실패했습니다.'}), 503
        cursor = None
        try:
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT photo_path FROM golf_rounds WHERE id = %s FOR UPDATE', (round_id,))
            row = cursor.fetchone()
            if row is None:
                return jsonify({'error': '라운드가 없습니다.'}), 404
            cursor.execute('DELETE FROM golf_rounds WHERE id = %s', (round_id,))
            conn.commit()
            try:
                delete_photo(row['photo_path'])
            except OSError:
                app.logger.warning('삭제한 라운드 사진 정리 실패')
            return jsonify({'status': 'success'})
        except Error:
            conn.rollback()
            app.logger.exception('라운드 삭제 실패')
            return jsonify({'error': '라운드를 삭제하지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/golf/recognition-status', methods=['GET'])
    def golf_recognition_status():
        key, model = recognition_service.existing_ai_settings()
        return jsonify({'ocr_available':bool(find_tesseract()),'ai_key_configured':recognition_service.usable_key(key),
                        'model':model, 'key_validated':False})

    @app.route('/api/golf/ocr', methods=['POST'])
    def golf_card_ocr():
        try:
            image = read_photo(photo_file())
            try:
                result = ocr_result(image)
            except RuntimeError as error:
                return jsonify({'error':str(error), 'needs_review':True,'ocr_ticket':ocr_ticket(image)}),503
            if result['needs_review']: result['ocr_ticket'] = ocr_ticket(image)
            return jsonify(result)
        except ValueError as error:
            return jsonify({'error': str(error)}), 400

    @app.route('/api/golf/ai', methods=['POST'])
    def golf_card_ai():
        try:
            image = read_photo(photo_file())
            key, _ = recognition_service.existing_ai_settings()
            if not recognition_service.usable_key(key):
                return jsonify({'error':'기존 API 키가 연결되지 않았습니다. 서버에서 manage.py link-ai 명령를 실행하여 골프 프로젝트의 .env 파일을 지정한 뒤 서버를 재시작해 주세요. 키 값은 화면에 입력하지 않습니다.','error_code':'AI_KEY_NOT_CONFIGURED'}),503
            # 같은 사진에 대해 최근 OCR 실패를 확인한 서명값이 있으면 OCR을 반복하지 않음.
            if not valid_ocr_ticket(image, request.form.get('ocr_ticket','')):
                try:
                    ocr = ocr_result(image)
                    if not ocr['needs_review']:
                        return jsonify({'error':'OCR에서 홀별 점수와 합계를 검증했습니다. 해당 결과를 먼저 확인해 주세요.'}),409
                except RuntimeError:
                    pass
            mode = request.form.get('input_mode', 'AUTO')
            if mode not in ('AUTO','ACTUAL_STROKES','OVER_PAR'):
                return jsonify({'error':'점수 해석 방식을 확인해 주세요.'}),400
            result = recognition_service.golf_candidates(recognition_service.ai_json(image, recognition_service.GOLF_PROMPT),mode)
            result['source'] = 'AI'
            result['text'] = '\n'.join(result['warnings'])
            return jsonify(result)
        except ValueError as error: return jsonify({'error':str(error)}),400
        except RuntimeError as error: return jsonify({'error':str(error)}),503
        except Exception:
            app.logger.exception('AI 스코어 분석 처리 오류')
            return jsonify({'error':'서버에서 AI 결과를 처리하지 못했습니다. 서버 로그를 확인해 주세요.','error_code':'AI_RESULT_PROCESSING_FAILED'}),500
