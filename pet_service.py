"""HaruLog 펫스토리: 최소 개체정보, 족보, 개체별 사진 기록."""
from datetime import date, datetime
from flask import jsonify, request
from mysql.connector import Error


SEXES = {'male', 'female', 'unknown'}
STATUSES = {'active', 'deceased', 'transferred', 'inactive'}
SPECIES = {'cat', 'dog', 'bird', 'rabbit', 'fish', 'reptile', 'other'}


def init_schema(conn):
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS pets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            species VARCHAR(20) NOT NULL DEFAULT 'other',
            registration_no VARCHAR(100) NULL,
            sex VARCHAR(20) NOT NULL DEFAULT 'unknown',
            birth_date DATE NULL,
            death_date DATE NULL,
            breed VARCHAR(100) NOT NULL DEFAULT '',
            color VARCHAR(100) NOT NULL DEFAULT '',
            microchip_no VARCHAR(100) NOT NULL DEFAULT '',
            sire_id INT NULL,
            dam_id INT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            notes TEXT NOT NULL,
            photo_path VARCHAR(255) NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            UNIQUE KEY uq_pets_registration_no (registration_no),
            KEY idx_pets_name (name),
            KEY idx_pets_sire (sire_id),
            KEY idx_pets_dam (dam_id),
            CONSTRAINT fk_pets_sire FOREIGN KEY (sire_id) REFERENCES pets(id),
            CONSTRAINT fk_pets_dam FOREIGN KEY (dam_id) REFERENCES pets(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:
        cursor.close()


def init_records_schema(conn):
    """Create only the independent pet-record feature table."""
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS pet_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            owner_id BIGINT NOT NULL,
            pet_id INT NOT NULL,
            record_date DATE NOT NULL,
            content TEXT NOT NULL,
            photo_path VARCHAR(255) NULL,
            created_at DATETIME NOT NULL,
            KEY idx_pet_records_owner_pet_date (owner_id,pet_id,record_date),
            CONSTRAINT fk_pet_records_pet FOREIGN KEY (pet_id) REFERENCES pets(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:
        cursor.close()


def init_lineage_schema(conn):
    """Store explicit generations without altering the existing pets table."""
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS pet_lineage (
            pet_id INT NOT NULL,
            owner_id BIGINT NOT NULL,
            generation_no INT NOT NULL,
            PRIMARY KEY (owner_id,pet_id),
            KEY idx_pet_lineage_generation (owner_id,generation_no),
            CONSTRAINT fk_pet_lineage_pet FOREIGN KEY (pet_id) REFERENCES pets(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:
        cursor.close()


def _text(data, key, maximum, required=False):
    value = data.get(key, '')
    if value is None:
        value = ''
    if not isinstance(value, str) or len(value.strip()) > maximum:
        raise ValueError(f'{key} 입력값을 확인해 주세요.')
    value = value.strip()
    if required and not value:
        raise ValueError('반려동물 이름을 입력해 주세요.')
    return value


def _date(data, key, label):
    value = _text(data, key, 10)
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f'{label}을 확인해 주세요.')
    if parsed > date.today():
        raise ValueError(f'{label}은 미래 날짜일 수 없습니다.')
    return parsed


def _optional_id(data, key):
    value = data.get(key)
    if value in ('', None):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError('부모 개체를 다시 선택해 주세요.')
    if value < 1:
        raise ValueError('부모 개체를 다시 선택해 주세요.')
    return value


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('반려동물 정보를 확인해 주세요.')
    sex = data.get('sex', 'unknown')
    status = data.get('status', 'active')
    species = data.get('species', 'other')
    if sex not in SEXES:
        raise ValueError('성별을 확인해 주세요.')
    if status not in STATUSES:
        raise ValueError('상태를 확인해 주세요.')
    if species not in SPECIES:
        raise ValueError('반려동물 종류를 확인해 주세요.')
    birth_date = _date(data, 'birth_date', '생년월일')
    try:
        generation_no = int(data.get('generation_no', 1))
    except (TypeError, ValueError):
        raise ValueError('세대를 확인해 주세요.')
    if not 1 <= generation_no <= 50:
        raise ValueError('세대는 1부터 50까지 입력할 수 있습니다.')
    death_date = _date(data, 'death_date', '사망일')
    if birth_date and death_date and death_date < birth_date:
        raise ValueError('사망일은 생년월일보다 빠를 수 없습니다.')
    return {
        'name': _text(data, 'name', 100, True),
        'species': species,
        'registration_no': _text(data, 'registration_no', 100) or None,
        'sex': sex,
        'birth_date': birth_date,
        'death_date': death_date,
        'breed': _text(data, 'breed', 100),
        'color': _text(data, 'color', 100),
        'microchip_no': _text(data, 'microchip_no', 100),
        'sire_id': _optional_id(data, 'sire_id'),
        'dam_id': _optional_id(data, 'dam_id'),
        'status': status,
        'notes': _text(data, 'notes', 3000),
        'generation_no': generation_no,
    }


def _rows(cursor):
    cursor.execute('''SELECT id,name,species,registration_no,sex,birth_date,death_date,breed,color,
                      microchip_no,sire_id,dam_id,status,notes,photo_path,created_at,updated_at
                      FROM pets ORDER BY name,id''')
    return cursor.fetchall()


def _rows_with_generation(cursor):
    rows = _rows(cursor)
    cursor.execute('SELECT pet_id,generation_no FROM pet_lineage')
    generations = {row['pet_id']: row['generation_no'] for row in cursor.fetchall()}
    for row in rows:
        row['generation_no'] = int(generations.get(row['id'], 1))
    return rows


def _json_row(row):
    item = dict(row)
    for key in ('birth_date', 'death_date'):
        item[key] = item[key].isoformat() if item.get(key) else ''
    for key in ('created_at', 'updated_at'):
        item[key] = item[key].strftime('%Y-%m-%d %H:%M:%S') if item.get(key) else ''
    item['registration_no'] = item.get('registration_no') or ''
    item['photo_path'] = item.get('photo_path') or ''
    return item


def _validate_relations(cursor, pet_id, data):
    if data['generation_no'] == 1 and (data['sire_id'] or data['dam_id']):
        raise ValueError('1세대에는 부모를 연결할 수 없습니다.')
    if data['sire_id'] and data['sire_id'] == data['dam_id']:
        raise ValueError('부와 모는 같은 반려동물일 수 없습니다.')
    if pet_id and pet_id in (data['sire_id'], data['dam_id']):
        raise ValueError('자기 자신을 부모로 지정할 수 없습니다.')
    parents = {}
    for parent_id, label, expected in ((data['sire_id'], '부', 'male'), (data['dam_id'], '모', 'female')):
        if not parent_id:
            continue
        cursor.execute('''SELECT p.id,p.species,p.sex,p.birth_date,COALESCE(l.generation_no,1) generation_no
                          FROM pets p LEFT JOIN pet_lineage l ON l.pet_id=p.id WHERE p.id=%s''', (parent_id,))
        parent = cursor.fetchone()
        if not parent:
            raise ValueError(f'{label} 개체를 찾을 수 없습니다.')
        if parent['sex'] not in (expected, 'unknown'):
            raise ValueError(f'{label} 개체의 성별이 맞지 않습니다.')
        if parent['species'] != data['species']:
            raise ValueError(f'{label} 개체의 동물 종류가 자녀와 다릅니다.')
        if int(parent['generation_no']) != data['generation_no'] - 1:
            raise ValueError(f'{label} 개체는 바로 앞 세대({data["generation_no"]-1}세대)여야 합니다.')
        if data['birth_date'] and parent['birth_date'] and parent['birth_date'] >= data['birth_date']:
            raise ValueError(f'{label}의 생년월일은 자묘보다 빨라야 합니다.')
        parents[parent_id] = parent
    if not pet_id:
        return
    cursor.execute('''SELECT p.id,COALESCE(l.generation_no,1) generation_no
                      FROM pets p LEFT JOIN pet_lineage l ON l.pet_id=p.id
                      WHERE p.sire_id=%s OR p.dam_id=%s''', (pet_id,pet_id))
    if any(int(child['generation_no']) != data['generation_no'] + 1 for child in cursor.fetchall()):
        raise ValueError('연결된 자녀가 있어 자녀 바로 앞 세대가 아닌 값으로 변경할 수 없습니다.')
    cursor.execute('SELECT id,sire_id,dam_id FROM pets')
    graph = {row['id']: (row['sire_id'], row['dam_id']) for row in cursor.fetchall()}
    graph[pet_id] = (data['sire_id'], data['dam_id'])
    def reaches_self(node, seen):
        if node is None:
            return False
        if node == pet_id:
            return True
        if node in seen:
            return False
        return any(reaches_self(parent, seen | {node}) for parent in graph.get(node, (None, None)))
    if any(reaches_self(parent_id, set()) for parent_id in (data['sire_id'], data['dam_id'])):
        raise ValueError('순환하는 족보 관계는 저장할 수 없습니다.')


def _tree(by_id, pet_id, generations, seen=None):
    if not pet_id or pet_id in (seen or set()) or pet_id not in by_id:
        return None
    row = by_id[pet_id]
    node = {key: row.get(key) for key in ('id', 'name', 'species', 'registration_no', 'sex', 'birth_date',
                                           'breed', 'color', 'status', 'photo_path')}
    if generations > 1:
        visited = (seen or set()) | {pet_id}
        node['sire'] = _tree(by_id, row.get('sire_id'), generations - 1, visited)
        node['dam'] = _tree(by_id, row.get('dam_id'), generations - 1, visited)
    return node


def _record_json(row):
    item = dict(row)
    item['record_date'] = item['record_date'].isoformat() if item.get('record_date') else ''
    item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S') if item.get('created_at') else ''
    item['photo_path'] = item.get('photo_path') or ''
    return item


def register_routes(app, get_conn, save_file, delete_file):
    def pet_photo():
        photo = request.files.get('photo') if request.files else None
        if not photo or not photo.filename:
            return None
        extension = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else ''
        if extension not in {'jpg', 'jpeg', 'png', 'webp'}:
            raise ValueError('반려동물 사진은 JPG, PNG, WebP 파일만 등록할 수 있습니다.')
        return photo

    @app.route('/api/pets', methods=['GET', 'POST'])
    def pets_collection():
        if request.method == 'POST':
            data = request.form.to_dict() if request.content_type and request.content_type.startswith('multipart/form-data') else request.get_json(silent=True)
            try:
                clean = validate(data)
            except ValueError as error:
                return jsonify({'error': str(error)}), 400
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        photo_path = None
        try:
            cursor = conn.cursor(dictionary=True)
            if request.method == 'GET':
                return jsonify([_json_row(row) for row in _rows_with_generation(cursor)])
            _validate_relations(cursor, None, clean)
            photo = pet_photo()
            if photo:
                photo_path = save_file(photo)
            now = datetime.now()
            cursor.execute('''INSERT INTO pets
                (name,species,registration_no,sex,birth_date,death_date,breed,color,microchip_no,
                 sire_id,dam_id,status,notes,photo_path,created_at,updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (clean['name'], clean['species'], clean['registration_no'], clean['sex'], clean['birth_date'],
                 clean['death_date'], clean['breed'], clean['color'], clean['microchip_no'],
                 clean['sire_id'], clean['dam_id'], clean['status'], clean['notes'],
                 photo_path, now, now))
            pet_id = cursor.lastrowid
            cursor.execute('INSERT INTO pet_lineage (pet_id,generation_no) VALUES (%s,%s)',
                           (pet_id,clean['generation_no']))
            conn.commit()
            return jsonify({'status': 'success', 'id': pet_id}), 201
        except Error as error:
            conn.rollback()
            if photo_path:
                delete_file(photo_path)
            if getattr(error, 'errno', None) == 1062:
                return jsonify({'error': '이미 등록된 혈통등록번호입니다.'}), 409
            app.logger.exception('반려동물 정보 처리 실패')
            return jsonify({'error': '반려동물 정보를 처리하지 못했습니다.'}), 500
        except (OSError, ValueError) as error:
            conn.rollback()
            if photo_path:
                delete_file(photo_path)
            return jsonify({'error': str(error)}), 400
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/pets/<int:pet_id>', methods=['PUT', 'DELETE'])
    def pet_item(pet_id):
        if request.method == 'PUT':
            data = request.form.to_dict() if request.content_type and request.content_type.startswith('multipart/form-data') else request.get_json(silent=True)
            try:
                clean = validate(data)
            except ValueError as error:
                return jsonify({'error': str(error)}), 400
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        new_photo = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM pets WHERE id=%s', (pet_id,))
            current = cursor.fetchone()
            if not current:
                return jsonify({'error': '반려동물 정보를 찾을 수 없습니다.'}), 404
            if request.method == 'DELETE':
                cursor.execute("UPDATE pets SET status='inactive',updated_at=%s WHERE id=%s", (datetime.now(), pet_id))
                conn.commit()
                return jsonify({'status': 'success'})
            _validate_relations(cursor, pet_id, clean)
            photo = pet_photo()
            new_photo = save_file(photo) if photo else current.get('photo_path')
            cursor.execute('''UPDATE pets SET name=%s,species=%s,registration_no=%s,sex=%s,birth_date=%s,
                death_date=%s,breed=%s,color=%s,microchip_no=%s,sire_id=%s,dam_id=%s,
                status=%s,notes=%s,photo_path=%s,updated_at=%s WHERE id=%s''',
                (clean['name'], clean['species'], clean['registration_no'], clean['sex'], clean['birth_date'],
                 clean['death_date'], clean['breed'], clean['color'], clean['microchip_no'],
                 clean['sire_id'], clean['dam_id'], clean['status'], clean['notes'],
                 new_photo, datetime.now(), pet_id))
            cursor.execute('SELECT pet_id FROM pet_lineage WHERE pet_id=%s', (pet_id,))
            if cursor.fetchone():
                cursor.execute('UPDATE pet_lineage SET generation_no=%s WHERE pet_id=%s',
                               (clean['generation_no'],pet_id))
            else:
                cursor.execute('INSERT INTO pet_lineage (pet_id,generation_no) VALUES (%s,%s)',
                               (pet_id,clean['generation_no']))
            conn.commit()
            if photo and current.get('photo_path') and current['photo_path'] != new_photo:
                delete_file(current['photo_path'])
            return jsonify({'status': 'success'})
        except Error as error:
            conn.rollback()
            if new_photo and new_photo != (current.get('photo_path') if 'current' in locals() else None):
                delete_file(new_photo)
            if getattr(error, 'errno', None) == 1062:
                return jsonify({'error': '이미 등록된 혈통등록번호입니다.'}), 409
            app.logger.exception('반려동물 정보 변경 실패')
            return jsonify({'error': '반려동물 정보를 변경하지 못했습니다.'}), 500
        except (OSError, ValueError) as error:
            conn.rollback()
            return jsonify({'error': str(error)}), 400
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/pets/<int:pet_id>/pedigree', methods=['GET'])
    def pet_pedigree(pet_id):
        try:
            generations = max(1, min(int(request.args.get('generations', 4)), 6))
        except ValueError:
            return jsonify({'error': '표시 세대를 확인해 주세요.'}), 400
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            rows = [_json_row(row) for row in _rows(cursor)]
            by_id = {row['id']: row for row in rows}
            tree = _tree(by_id, pet_id, generations)
            return jsonify({'pedigree': tree}) if tree else (jsonify({'error': '족보를 찾을 수 없습니다.'}), 404)
        except Error:
            app.logger.exception('족보 조회 실패')
            return jsonify({'error': '족보를 불러오지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.get('/api/pets/lineage')
    def pet_lineage():
        species = request.args.get('species','').strip()
        if species and species not in SPECIES:
            return jsonify({'error': '반려동물 종류를 확인해 주세요.'}), 400
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            rows = [_json_row(row) for row in _rows_with_generation(cursor)]
            if species:
                rows = [row for row in rows if row['species'] == species]
            rows.sort(key=lambda row: (row['generation_no'],row['name'],row['id']))
            return jsonify({'pets': rows})
        except Error:
            app.logger.exception('세대별 족보 조회 실패')
            return jsonify({'error': '족보를 불러오지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/pets/<int:pet_id>/records', methods=['GET', 'POST'])
    def pet_records(pet_id):
        data = request.form.to_dict() if request.method == 'POST' else None
        try:
            record_date = _date(data, 'record_date', '기록일') if data is not None else None
            content = _text(data, 'content', 3000) if data is not None else None
            if data is not None and not record_date:
                raise ValueError('기록일을 입력해 주세요.')
            if data is not None and not content:
                raise ValueError('기록 내용을 입력해 주세요.')
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        photo_path = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id,name FROM pets WHERE id=%s', (pet_id,))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'error': '반려동물 정보를 찾을 수 없습니다.'}), 404
            if request.method == 'GET':
                cursor.execute('''SELECT id,pet_id,record_date,content,photo_path,created_at
                                  FROM pet_records WHERE pet_id=%s ORDER BY record_date DESC,id DESC''', (pet_id,))
                return jsonify({'pet': pet, 'records': [_record_json(row) for row in cursor.fetchall()]})
            photo = pet_photo()
            if photo:
                photo_path = save_file(photo)
            cursor.execute('''INSERT INTO pet_records (pet_id,record_date,content,photo_path,created_at)
                              VALUES (%s,%s,%s,%s,%s)''',
                           (pet_id, record_date, content, photo_path, datetime.now()))
            conn.commit()
            return jsonify({'status': 'success', 'id': cursor.lastrowid}), 201
        except Error:
            conn.rollback()
            if photo_path:
                delete_file(photo_path)
            app.logger.exception('반려동물 기록 처리 실패')
            return jsonify({'error': '반려동물 기록을 처리하지 못했습니다.'}), 500
        except (OSError, ValueError) as error:
            conn.rollback()
            if photo_path:
                delete_file(photo_path)
            return jsonify({'error': str(error)}), 400
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.delete('/api/pets/<int:pet_id>/records/<int:record_id>')
    def delete_pet_record(pet_id, record_id):
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id,photo_path FROM pet_records WHERE id=%s AND pet_id=%s', (record_id,pet_id))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '기록을 찾을 수 없습니다.'}), 404
            cursor.execute('DELETE FROM pet_records WHERE id=%s AND pet_id=%s', (record_id,pet_id))
            conn.commit()
            if row.get('photo_path'):
                delete_file(row['photo_path'])
            return jsonify({'status': 'success'})
        except Error:
            conn.rollback()
            app.logger.exception('반려동물 기록 삭제 실패')
            return jsonify({'error': '기록을 삭제하지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

