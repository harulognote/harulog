from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import Flask,jsonify
from werkzeug.security import check_password_hash
import auth_service as auth,admin_service
from test_auth import Database,HASH,PASSWORD


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.db=Database({'id':1,'username':'owner','password_hash':HASH,'auth_version':1})
        self.db.members[2]={'id':2,'username':'member','display_name':'Member','password_hash':HASH,'auth_version':1,'role':'user','status':'active','created_at':'now','updated_at':'now'}
        self.app=Flask(__name__);auth.register_routes(self.app,self.db.connect);admin_service.register_routes(self.app,self.db.connect)
        self.client=self.app.test_client()
    def status(self,client=None):return (client or self.client).get('/api/auth/status').json
    def login(self,name='owner',client=None):
        c=client or self.client
        return c.post('/api/auth/login',json={'username':name,'password':PASSWORD},headers={'X-CSRF-Token':self.status(c)['csrf_token']})
    def modify(self,id=2,delete=False,client=None,**changes):
        c=client or self.client
        data={'username':'member','display_name':'Member','role':'user','status':'active','admin_password':PASSWORD};data.update(changes)
        return c.open('/api/admin/members/'+str(id),method='DELETE' if delete else 'PUT',json=data,headers={'X-CSRF-Token':self.status(c)['csrf_token']})
    def test_anonymous_cannot_list(self):self.assertEqual(self.client.get('/api/admin/members').status_code,401)
    def test_user_cannot_list_or_modify(self):
        self.login('member');self.assertEqual(self.client.get('/api/admin/members').status_code,403)
        self.assertEqual(self.modify().status_code,403)
    def test_role_status_reported_to_owner_only(self):
        self.login();self.assertEqual(self.status()['role'],'admin')
        self.client.post('/api/auth/logout',headers={'X-CSRF-Token':self.status()['csrf_token']})
        self.login('member');self.assertEqual(self.status()['role'],'user')
    def test_admin_list_no_hashes(self):
        self.login();res=self.client.get('/api/admin/members')
        self.assertEqual(res.status_code,200)
        # A real SQL cursor projects fields. The query itself must exclude hashes.
        sql=[s for s,p in self.db.calls if 'LIMIT 100 OFFSET' in s][-1]
        self.assertNotIn('password_hash',sql);self.assertNotIn('SELECT *',sql)
    def test_wrong_admin_password(self):
        self.login();self.assertEqual(self.modify(admin_password='wrong').status_code,403)
    def test_approve_pending_member(self):
        self.db.members[2]['status']='pending';self.login()
        self.assertEqual(self.modify(status='active').status_code,200);self.assertEqual(self.db.members[2]['status'],'active')
    def test_suspend_revokes_session(self):
        other=self.app.test_client();self.login('member',other);self.login()
        self.assertEqual(self.modify(status='suspended').status_code,200)
        self.assertEqual(self.status(other)['authenticated'],False)
    def test_promote_and_audit(self):
        self.login();self.assertEqual(self.modify(role='admin').status_code,200)
        self.assertEqual(self.db.members[2]['role'],'admin');self.assertEqual(len(self.db.audit),1)
        self.assertNotIn(PASSWORD,self.db.audit[0]['details']);self.assertNotIn('password_hash',self.db.audit[0]['details'])
    def test_self_demote_denied(self):
        self.login();self.assertEqual(self.modify(1,username='owner',role='user').status_code,409)
        self.assertEqual(self.db.members[1]['role'],'admin')
    def test_self_delete_denied(self):
        self.login();self.assertEqual(self.modify(1,delete=True).status_code,409)
    def test_self_name_change_keeps_reauthenticated_current_session(self):
        self.login();res=self.modify(1,username='owner',display_name='새 이름',role='admin',status='active')
        self.assertEqual(res.status_code,200);self.assertEqual(res.json['member']['display_name'],'새 이름')
        self.assertEqual(self.status()['authenticated'],True)
        self.assertEqual(self.client.get('/api/admin/members').status_code,200)
    def test_delete_preserves_member_and_data_identity(self):
        self.login();self.assertEqual(self.modify(delete=True).status_code,200)
        self.assertEqual(self.db.members[2]['status'],'deleted');self.assertEqual(self.db.members[2]['id'],2)
        self.assertEqual(self.db.audit[-1]['action'],'member_delete')
    def test_restore_deleted_member(self):
        self.db.members[2]['status']='deleted';self.login();self.assertEqual(self.modify(status='active').status_code,200)
        self.assertEqual(self.db.members[2]['id'],2)
    def test_password_reset(self):
        self.login();self.assertEqual(self.modify(new_password='reset-password-123').status_code,200)
        self.assertTrue(check_password_hash(self.db.members[2]['password_hash'],'reset-password-123'))
    def test_failed_commit_keeps_member_and_audit(self):
        self.login();self.db.fail=True;self.assertEqual(self.modify(status='suspended').status_code,500)
        self.assertEqual(self.db.members[2]['status'],'active');self.assertEqual(self.db.audit,[])
    def test_invalid_role(self):
        self.login();self.assertEqual(self.modify(role='root').status_code,400)
    def test_missing_member(self):
        self.login();self.assertEqual(self.modify(id=999).status_code,404)
    def test_signup_forces_pending_user(self):
        res=self.client.post('/api/auth/signup',json={'username':'newuser','password':PASSWORD,'confirm_password':PASSWORD,'role':'admin','status':'active'},headers={'X-CSRF-Token':self.status()['csrf_token']})
        self.assertEqual(res.status_code,201)
        new=self.db.members[3];self.assertEqual(new['role'],'user');self.assertEqual(new['status'],'pending')
    def test_pending_login_denied(self):
        self.db.members[2]['status']='pending';self.assertEqual(self.login('member').status_code,403)
    def test_business_blocked_before_migration(self):
        self.db.ready=False;self.app.add_url_rule('/api/logs',view_func=lambda:jsonify(ok=True))
        self.login();self.assertEqual(self.client.get('/api/logs').status_code,503)
        self.assertEqual(self.client.get('/api/admin/members').status_code,200)
    def test_admin_cannot_access_other_data_by_role(self):
        from ownership import scoped_sql
        self.login();self.assertIn('owner_id=1',scoped_sql('SELECT * FROM daily_logs',self.status()['member_id']))


    def test_signup_accepts_eight_characters(self):
        response=self.client.post('/api/auth/signup',json={'username':'newuser','password':'abcd1234','confirm_password':'abcd1234'},headers={'X-CSRF-Token':self.status()['csrf_token']})
        self.assertEqual(response.status_code,201)
    def test_admin_reset_accepts_eight_characters(self):
        self.login();self.assertEqual(self.modify(new_password='abcd1234').status_code,200)
    def test_admin_reset_rejects_seven_characters(self):
        self.login();self.assertEqual(self.modify(new_password='abc1234').status_code,400)


if __name__=='__main__':unittest.main()
