"""Administrator-only member management. It does not grant access to member records."""
import json
from flask import g,jsonify,request,session
from werkzeug.security import check_password_hash,generate_password_hash

FIELDS='id,username,display_name,role,status,created_at,updated_at'


def register_routes(app,get_conn):
    @app.before_request
    def admin_guard():
        if request.path.startswith('/api/admin/'):
            account=getattr(g,'account',None)
            if not account or account.get('role')!='admin' or account.get('status')!='active':
                return jsonify(error='관리자 권한이 필요합니다.'),403

    @app.get('/api/admin/members')
    def members():
        try:page=max(1,int(request.args.get('page','1')))
        except ValueError:return jsonify(error='페이지를 확인해 주세요.'),400
        q=request.args.get('q','').strip()[:100]
        conn=get_conn();cursor=None
        try:
            cursor=conn.cursor(dictionary=True)
            term='%'+q+'%'
            cursor.execute('SELECT COUNT(*) AS total FROM app_members WHERE username LIKE %s OR display_name LIKE %s',(term,term))
            total=cursor.fetchone()['total']
            cursor.execute('SELECT '+FIELDS+' FROM app_members WHERE username LIKE %s OR display_name LIKE %s ORDER BY id LIMIT 100 OFFSET %s',(term,term,(page-1)*100))
            return jsonify(members=[{key:row.get(key) for key in FIELDS.split(',')} for row in cursor.fetchall()],total=total,page=page,page_size=100)
        finally:
            if cursor is not None:cursor.close()
            conn.close()

    @app.route('/api/admin/members/<int:member_id>',methods=['PUT','DELETE'])
    def change_member(member_id):
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict):return jsonify(error='입력 형식을 확인해 주세요.'),400
        password=data.get('admin_password','')
        if not isinstance(password,str) or len(password)>256 or not check_password_hash(g.account['password_hash'],password):
            return jsonify(error='관리자 본인의 현재 비밀번호를 확인해 주세요.'),403
        role=data.get('role','user');status=data.get('status','pending')
        if request.method!='DELETE' and (role not in ('admin','user') or status not in ('active','pending','suspended','deleted')):
            return jsonify(error='역할 또는 상태가 올바르지 않습니다.'),400
        new_password=data.get('new_password','')
        if not isinstance(new_password,str) or (new_password and not 8<=len(new_password)<=256):
            return jsonify(error='재설정 비밀번호는 8~256자여야 합니다.'),400
        conn=get_conn();cursor=None
        try:
            conn.start_transaction()
            cursor=conn.cursor(dictionary=True)
            # A common lock order serializes concurrent changes to the active administrator set.
            cursor.execute("SELECT id,auth_version FROM app_members WHERE role='admin' AND status='active' ORDER BY id FOR UPDATE")
            admins=cursor.fetchall()
            if not any(a['id']==g.account['id'] and a['auth_version']==g.account['auth_version'] for a in admins):
                conn.rollback();return jsonify(error='관리 권한 또는 로그인이 변경되었습니다. 다시 로그인해 주세요.'),403
            cursor.execute('SELECT * FROM app_members WHERE id=%s FOR UPDATE',(member_id,))
            target=cursor.fetchone()
            if not target:conn.rollback();return jsonify(error='멤버가 없습니다.'),404
            if request.method=='DELETE':role=target['role'];status='deleted'
            if member_id==g.account['id'] and (status!='active' or role!='admin'):
                conn.rollback();return jsonify(error='자신의 관리자 권한을 회수하거나 계정을 정지·삭제할 수 없습니다.'),409
            if target['role']=='admin' and target['status']=='active' and (role!='admin' or status!='active') and len(admins)<=1:
                conn.rollback();return jsonify(error='마지막 활성 관리자는 권한 회수·정지·삭제할 수 없습니다.'),409
            username=data.get('username',target['username'])
            name=data.get('display_name',target['display_name'])
            import re
            if not isinstance(username,str) or not re.fullmatch(r'[^\s:]{3,64}',username) or not isinstance(name,str) or not 1<=len(name.strip())<=100:
                conn.rollback();return jsonify(error='아이디 또는 이름을 확인해 주세요.'),400
            hashed=generate_password_hash(new_password) if new_password else target['password_hash']
            cursor.execute('''UPDATE app_members SET username=%s,display_name=%s,role=%s,status=%s,password_hash=%s,
                auth_version=auth_version+1,updated_at=CURRENT_TIMESTAMP WHERE id=%s''',
                (username,name.strip(),role,status,hashed,member_id))
            details=json.dumps({'before':{k:target[k] for k in ('username','display_name','role','status')},
                'after':{'username':username,'display_name':name.strip(),'role':role,'status':status},'password_reset':bool(new_password)},ensure_ascii=False)
            cursor.execute('INSERT INTO app_admin_audit (actor_id,target_id,action,details) VALUES (%s,%s,%s,%s)',
                (g.account['id'],member_id,'member_delete' if request.method=='DELETE' else 'member_update',details))
            conn.commit()
            # 본인이 현재 비밀번호로 재확인한 관리 작업은 현재 세션만 새 버전으로
            # 이어가고, 같은 계정의 다른 기존 세션은 만료시킨다.
            if member_id==g.account['id']:
                session['av']=target['auth_version']+1
            return jsonify(ok=True,member={'id':member_id,'username':username,'display_name':name.strip(),
                'role':role,'status':status},message='멤버를 삭제 처리했습니다. 자료는 보존됩니다.' if status=='deleted' else '멤버 정보를 변경했습니다.')
        except Exception as error:
            conn.rollback()
            if getattr(error,'errno',None)==1062:return jsonify(error='이미 사용 중인 아이디입니다.'),409
            app.logger.exception('멤버 변경 실패');return jsonify(error='멤버 변경에 실패했습니다.'),500
        finally:
            if cursor is not None:cursor.close()
            conn.close()

    @app.get('/api/admin/audit')
    def audit():
        conn=get_conn();cursor=None
        try:
            cursor=conn.cursor(dictionary=True)
            cursor.execute('SELECT id,actor_id,target_id,action,details,created_at FROM app_admin_audit ORDER BY id DESC LIMIT 100')
            return jsonify(records=cursor.fetchall())
        finally:
            if cursor is not None:cursor.close()
            conn.close()
