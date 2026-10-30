"""HaruLog v1.9.0 — 본인 기본정보와 동반자 주소록."""
from datetime import datetime
from flask import jsonify, request
from mysql.connector import Error


def init_schema(conn):
    cursor=conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS personal_profile (
            id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, nickname VARCHAR(100) NOT NULL,
            updated_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS golf_contacts (
            id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL,
            nickname VARCHAR(100) NOT NULL, phone VARCHAR(80) NOT NULL,
            address VARCHAR(500) NOT NULL, memo TEXT NOT NULL,
            created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:cursor.close()


def validate(data, contact=False):
    if not isinstance(data,dict):raise ValueError('올바른 기본정보를 입력해 주세요.')
    keys=[('name',100),('nickname',100)]
    if contact:keys += [('phone',80),('address',500),('memo',2000)]
    result={}
    for key,maximum in keys:
        value=data.get(key,'')
        if not isinstance(value,str) or len(value.strip())>maximum:raise ValueError(f'{key} 입력값을 확인해 주세요.')
        result[key]=value.strip()
    if not result['name']:raise ValueError('성명을 입력해 주세요.')
    return result


def register_routes(app,get_conn):
    @app.route('/api/settings',methods=['GET'])
    def get_settings():
        conn=get_conn()
        if conn is None:return jsonify({'error':'DB 연결 실패'}),503
        cursor=None
        try:
            cursor=conn.cursor(dictionary=True)
            cursor.execute('SELECT name,nickname FROM personal_profile WHERE id=1')
            profile=cursor.fetchone() or {'name':'','nickname':''}
            cursor.execute('SELECT id,name,nickname,phone,address,memo FROM golf_contacts ORDER BY name,id')
            return jsonify({'profile':profile,'contacts':cursor.fetchall()})
        except Error:
            app.logger.exception('기본설정 조회 실패');return jsonify({'error':'기본설정을 불러오지 못했습니다.'}),500
        finally:
            if cursor is not None:cursor.close()
            conn.close()

    @app.route('/api/settings/profile',methods=['PUT'])
    def save_profile():
        try:data=validate(request.get_json(silent=True))
        except ValueError as error:return jsonify({'error':str(error)}),400
        conn=get_conn()
        if conn is None:return jsonify({'error':'DB 연결 실패'}),503
        cursor=None
        try:
            cursor=conn.cursor()
            cursor.execute('''INSERT INTO personal_profile (id,name,nickname,updated_at) VALUES (1,%s,%s,%s)
                ON DUPLICATE KEY UPDATE name=VALUES(name),nickname=VALUES(nickname),updated_at=VALUES(updated_at)''',
                (data['name'],data['nickname'],datetime.now()))
            conn.commit();return jsonify({'status':'success'})
        except Error:
            conn.rollback();app.logger.exception('본인정보 저장 실패');return jsonify({'error':'본인정보를 저장하지 못했습니다.'}),500
        finally:
            if cursor is not None:cursor.close()
            conn.close()

    @app.route('/api/settings/contacts',methods=['POST'])
    @app.route('/api/settings/contacts/<int:contact_id>',methods=['PUT','DELETE'])
    def change_contact(contact_id=None):
        if request.method!='DELETE':
            try:data=validate(request.get_json(silent=True),True)
            except ValueError as error:return jsonify({'error':str(error)}),400
        conn=get_conn()
        if conn is None:return jsonify({'error':'DB 연결 실패'}),503
        cursor=None
        try:
            cursor=conn.cursor()
            if contact_id is not None:
                cursor.execute('SELECT id FROM golf_contacts WHERE id=%s',(contact_id,))
                if cursor.fetchone() is None:return jsonify({'error':'동반자 정보가 없습니다.'}),404
            if request.method=='DELETE':
                cursor.execute('DELETE FROM golf_contacts WHERE id=%s',(contact_id,))
            else:
                values=(data['name'],data['nickname'],data['phone'],data['address'],data['memo'],datetime.now())
                if contact_id is None:
                    cursor.execute('''INSERT INTO golf_contacts (name,nickname,phone,address,memo,updated_at,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)''',values+(datetime.now(),))
                    contact_id=cursor.lastrowid
                else:
                    cursor.execute('UPDATE golf_contacts SET name=%s,nickname=%s,phone=%s,address=%s,memo=%s,updated_at=%s WHERE id=%s',values+(contact_id,))
            conn.commit();return jsonify({'status':'success','id':contact_id}),201 if request.method=='POST' else 200
        except Error:
            conn.rollback();app.logger.exception('동반자 정보 처리 실패');return jsonify({'error':'동반자 정보를 처리하지 못했습니다.'}),500
        finally:
            if cursor is not None:cursor.close()
            conn.close()
