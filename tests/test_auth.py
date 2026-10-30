"""Browser login, first-owner protection, session revocation and personal settings."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import Flask,jsonify
from werkzeug.security import generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import auth_service as auth

PASSWORD='initial-password-123'
HASH=generate_password_hash(PASSWORD)


class Database:
    def __init__(self,account=None):
        self.members={};self.fail=False;self.calls=[];self.audit=[];self.ready=True
        self.account=account
    @property
    def account(self):return self.members.get(1)
    @account.setter
    def account(self,value):
        if value:self.members[1]={**deepcopy(value),'role':value.get('role','admin'),'status':value.get('status','active'),'display_name':value.get('display_name','Owner')}
        else:self.members.pop(1,None)
    def connect(self):return Connection(self)


class Connection:
    def __init__(self,db):self.db=db;self.result=[];self.rowcount=1;self.pending=None;self.pending_audit=[];self.lastrowid=0;self.dictionary=False
    def cursor(self,**kwargs):self.dictionary=kwargs.get('dictionary',False);return self
    def start_transaction(self):self.pending=deepcopy(self.db.members)
    def execute(self,sql,params=()):
        self.db.calls.append((sql,params));rows=self.pending if self.pending is not None else self.db.members
        if 'FROM information_schema.COLUMNS' in sql:
            from ownership import TABLES
            self.result=[{'total':len(TABLES)}];return
        if 'FROM app_system' in sql:self.result=[{'value':'1'}] if self.db.ready else [];return
        if sql.startswith('SELECT') and 'FROM app_admin_audit' in sql:self.result=deepcopy(self.db.audit);return
        if sql.startswith('SELECT') and 'FROM app_members' in sql:
            selected=list(rows.values())
            if "role='admin'" in sql:selected=[r for r in selected if r['role']=='admin' and r['status']=='active']
            elif 'WHERE id=%s' in sql:selected=[r for r in selected if r['id']==params[0]]
            elif 'WHERE username=%s' in sql:selected=[r for r in selected if r['username']==params[0]]
            if 'LIKE' in sql:
                q=params[0].strip('%');selected=[r for r in selected if q in r['username'] or q in r['display_name']]
            if 'COUNT(*)' in sql:self.result=[{'total':len(selected)}];return
            if 'ORDER BY id' in sql:selected.sort(key=lambda r:r['id'])
            if 'LIMIT 1' in sql and 'LIMIT 100' not in sql:selected=selected[:1]
            self.result=deepcopy(selected);return
        if sql.startswith('INSERT INTO app_admin_audit'):
            self.pending_audit.append({'id':len(self.db.audit)+1,'actor_id':params[0],'target_id':params[1],'action':params[2],'details':params[3],'created_at':'now'});return
        if sql.startswith('INSERT INTO app_members'):
            if self.pending is None:self.pending=deepcopy(self.db.members)
            if any(r['username']==params[0] for r in self.pending.values()) or ('(id,' in sql and 1 in self.pending):
                from mysql.connector import Error
                raise Error('duplicate',errno=1062)
            identifier=1 if '(id,' in sql else max(self.pending.keys(),default=0)+1
            self.pending[identifier]={'id':identifier,'username':params[0],'display_name':params[1],'password_hash':params[2],
                'auth_version':1,'role':'admin' if '(id,' in sql else 'user','status':'active' if '(id,' in sql else 'pending','created_at':'now','updated_at':'now'}
            self.lastrowid=identifier;return
        if sql.startswith('UPDATE app_members'):
            if self.pending is None:self.pending=deepcopy(self.db.members)
            if len(params)==4:
                username,hashed,identifier,version=params;target=self.pending[identifier];self.rowcount=int(target['auth_version']==version)
                if self.rowcount:target.update(username=username,password_hash=hashed,auth_version=version+1)
            else:
                username,name,role,status,hashed,identifier=params;target=self.pending[identifier]
                target.update(username=username,display_name=name,role=role,status=status,password_hash=hashed,auth_version=target['auth_version']+1)
            return
    def fetchone(self):
        if not self.result:return None
        value=self.result[0];return value if self.dictionary else tuple(value.values())
    def fetchall(self):return self.result if self.dictionary else [tuple(r.values()) for r in self.result]
    def commit(self):
        if self.db.fail:raise RuntimeError('simulated commit failure')
        if self.pending is not None:self.db.members=self.pending;self.pending=None
        self.db.audit.extend(self.pending_audit);self.pending_audit=[]
    def rollback(self):self.pending=None;self.pending_audit=[]
    def close(self):pass


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.db=Database({'id':1,'username':'owner','password_hash':HASH,'auth_version':1})
        self.app=Flask(__name__,static_folder=str(Path(__file__).resolve().parents[1]/'static'))
        auth.register_routes(self.app,self.db.connect)
        self.app.add_url_rule('/',endpoint='home',view_func=lambda:auth.render_home(self.app))
        self.app.add_url_rule('/api/private',endpoint='private',view_func=lambda:jsonify(value='private'),methods=['GET','POST','DELETE'])
        self.app.add_url_rule('/uploads/photo.jpg',endpoint='photo',view_func=lambda:'private photo')
        self.client=self.app.test_client()
    def status(self,client=None):return (client or self.client).get('/api/auth/status').json
    def login(self,client=None,password=PASSWORD):
        client=client or self.client;csrf=self.status(client)['csrf_token']
        return client.post('/api/auth/login',json={'username':'owner','password':password},headers={'X-CSRF-Token':csrf})
    def setup(self,client=None,**changes):
        client=client or self.client
        csrf=self.status(client)['csrf_token']
        data={'username':'owner','password':PASSWORD,'confirm_password':PASSWORD,'setup_token':self.app.config['AUTH_SETUP_TOKEN']};data.update(changes)
        return client.post('/api/auth/setup',json=data,headers={'X-CSRF-Token':csrf})
    def test_private_routes_require_login(self):
        self.assertEqual(self.client.get('/').status_code,302)
        self.assertEqual(self.client.get('/api/private').status_code,401)
        self.assertEqual(self.client.get('/uploads/photo.jpg').status_code,302)
    def test_login_page_and_assets_public(self):
        for path in ['/login','/static/login.js','/static/style.css']:
            self.assertEqual(self.client.get(path).status_code,200)
    def test_successful_login_and_logout(self):
        self.assertEqual(self.login().status_code,200)
        self.assertEqual(self.client.get('/api/private').status_code,200)
        csrf=self.status()['csrf_token']
        logout=self.client.post('/api/auth/logout',headers={'X-CSRF-Token':csrf})
        self.assertEqual(logout.status_code,200);self.assertFalse(logout.json['authenticated']);self.assertTrue(logout.json['csrf_token'])
        self.assertIn(self.app.config['SESSION_COOKIE_NAME']+'=',logout.headers['Set-Cookie'])
        self.assertNotIn('Thu, 01 Jan 1970',logout.headers['Set-Cookie'])
        self.assertFalse(self.status()['authenticated'])
        self.assertEqual(self.client.get('/api/private').status_code,401)
    def test_wrong_password(self):self.assertEqual(self.login(password='wrong').status_code,401)
    def test_login_missing_csrf(self):self.assertEqual(self.client.post('/api/auth/login',json={}).status_code,403)
    def test_mutation_requires_csrf(self):
        self.login();self.assertEqual(self.client.post('/api/private').status_code,403)
        self.assertEqual(self.client.post('/api/private',headers={'X-CSRF-Token':self.status()['csrf_token']}).status_code,200)
    def test_foreign_origin_rejected(self):
        self.login()
        self.assertEqual(self.client.post('/api/private',headers={'X-CSRF-Token':self.status()['csrf_token'],'Origin':'https://evil.example'}).status_code,403)

    def test_registered_tunnel_origin_is_accepted(self):
        self.app.config['AUTH_PUBLIC_ORIGIN']='https://issued-name.trycloudflare.com'
        response=self.client.post('/api/private',headers={
            'X-CSRF-Token':self.status()['csrf_token'],
            'Origin':'https://issued-name.trycloudflare.com'})
        self.assertNotEqual(response.status_code,403)
    def test_status_never_discloses_hash(self):
        self.assertNotIn('password',str(self.status()));self.assertEqual(self.status()['username'],'')
    def test_first_setup_requires_local_console_token(self):
        self.db.account=None
        self.assertEqual(self.setup(setup_token='wrong').status_code,403)
        self.assertIsNone(self.db.account)
        self.assertEqual(self.setup().status_code,200)
        self.assertNotEqual(self.db.account['password_hash'],PASSWORD)
        self.assertEqual(self.client.get('/api/private').status_code,200)
    def test_console_token_allows_setup_from_external_address(self):
        self.db.account=None
        response=self.client.get('/api/auth/status',base_url='https://public.example')
        self.assertTrue(response.json['setup_allowed'])
        response=self.client.post('/api/auth/setup',base_url='https://public.example',json={'username':'owner','password':PASSWORD,'confirm_password':PASSWORD,'setup_token':self.app.config['AUTH_SETUP_TOKEN']},headers={'X-CSRF-Token':response.json['csrf_token']})
        self.assertEqual(response.status_code,200);self.assertIsNotNone(self.db.account)
    def test_existing_owner_cannot_be_overwritten(self):self.assertEqual(self.setup().status_code,409)
    def test_weak_password_rejected(self):
        self.db.account=None;self.assertEqual(self.setup(password='short',confirm_password='short').status_code,400)
    def test_confirmation_required(self):
        self.db.account=None;self.assertEqual(self.setup(confirm_password='different').status_code,400)
    def change(self,**changes):
        data={'username':'newowner','current_password':PASSWORD,'password':'new-password-123','confirm_password':'new-password-123'};data.update(changes)
        return self.client.put('/api/settings/account',json=data,headers={'X-CSRF-Token':self.status()['csrf_token']})
    def test_account_change_revokes_other_sessions(self):
        other=self.app.test_client();self.login(other);self.login()
        self.assertEqual(self.change().status_code,200)
        self.assertEqual(self.db.account['username'],'newowner')
        self.assertEqual(self.client.get('/api/private').status_code,200)
        self.assertEqual(other.get('/api/private').status_code,401)
    def test_account_change_checks_current_password(self):
        self.login();self.assertEqual(self.change(current_password='wrong').status_code,403)
        self.assertEqual(self.db.account['username'],'owner')
    def test_failed_account_change_keeps_account(self):
        self.login();self.db.fail=True
        self.assertEqual(self.change().status_code,500);self.assertEqual(self.db.account['username'],'owner')
    def test_html_has_csrf_and_personal_settings(self):
        self.login();response=self.client.get('/')
        self.assertIn('accountForm',response.text);self.assertNotIn('__HARULOG_CSRF__',response.text)
    def test_no_store_on_private_and_public(self):
        self.assertEqual(self.client.get('/login').headers['Cache-Control'],'no-store')
        self.login();self.assertEqual(self.client.get('/api/private').headers['Cache-Control'],'no-store')
    def test_session_cookie_is_httponly_and_samesite(self):
        response=self.login();cookie=response.headers['Set-Cookie']
        self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Lax',cookie)
    def test_proxy_https_cookie_is_secure(self):
        self.app.wsgi_app=ProxyFix(self.app.wsgi_app,x_for=0,x_proto=1)
        response=self.client.get('/api/auth/status',headers={'X-Forwarded-Proto':'https'})
        self.assertIn('Secure',response.headers['Set-Cookie'])
    def test_rate_limit(self):
        for _ in range(10):self.assertEqual(self.login(password='wrong').status_code,401)
        self.assertEqual(self.login(password='wrong').status_code,429)
    def test_database_unavailable_fails_closed(self):
        self.db.connect=lambda:None
        # Registration captured the original callable, so make its read fail instead.
        from unittest.mock import patch
        with patch.object(auth,'read_account',side_effect=RuntimeError('offline')):
            self.assertEqual(self.client.get('/api/private').status_code,503)


    def test_first_admin_accepts_exactly_eight_characters(self):
        self.db.account=None
        self.assertEqual(self.setup(password='abcd1234',confirm_password='abcd1234').status_code,200)
    def test_first_admin_rejects_seven_characters(self):
        self.db.account=None
        self.assertEqual(self.setup(password='abc1234',confirm_password='abc1234').status_code,400)
    def test_personal_password_accepts_eight_characters(self):
        self.login()
        self.assertEqual(self.change(password='abcd1234',confirm_password='abcd1234').status_code,200)
    def test_csrf_expiry_does_not_write_and_refresh_recovers(self):
        self.db.account=None
        token=self.status()['csrf_token']
        with self.client.session_transaction() as sess:sess['csrf']='changed-by-another-tab'
        data={'username':'owner','password':'abcd1234','confirm_password':'abcd1234','setup_token':self.app.config['AUTH_SETUP_TOKEN']}
        failed=self.client.post('/api/auth/setup',json=data,headers={'X-CSRF-Token':token})
        self.assertEqual(failed.status_code,403);self.assertEqual(failed.json['code'],'CSRF_EXPIRED');self.assertIsNone(self.db.account)
        fresh=self.status()['csrf_token']
        self.assertEqual(self.client.post('/api/auth/setup',json=data,headers={'X-CSRF-Token':fresh}).status_code,200)
    def test_origin_error_is_not_reported_as_expired(self):
        token=self.status()['csrf_token']
        response=self.client.post('/api/auth/login',json={},headers={'X-CSRF-Token':token,'Origin':'https://different.example'})
        self.assertEqual(response.json['code'],'CSRF_ORIGIN')
    def test_invalid_console_token_has_actionable_code(self):
        self.db.account=None
        response=self.setup(setup_token='stale-token')
        self.assertEqual(response.json['code'],'SETUP_TOKEN_INVALID');self.assertIsNone(self.db.account)


    def test_public_setup_without_console_token_is_denied(self):
        self.db.account=None
        response=self.client.get('/api/auth/status',base_url='https://public.example')
        self.assertNotIn(self.app.config['AUTH_SETUP_TOKEN'],str(response.json))
        response=self.client.post('/api/auth/setup',base_url='https://public.example',json={'username':'owner','password':'abcd1234','confirm_password':'abcd1234','setup_token':''},headers={'X-CSRF-Token':response.json['csrf_token']})
        self.assertEqual(response.status_code,403);self.assertIsNone(self.db.account)
    def test_lan_setup_with_correct_console_token(self):
        self.db.account=None
        state=self.client.get('/api/auth/status',base_url='http://10.0.2.13:5000').json
        response=self.client.post('/api/auth/setup',base_url='http://10.0.2.13:5000',json={'username':'owner','password':'abcd1234','confirm_password':'abcd1234','setup_token':self.app.config['AUTH_SETUP_TOKEN']},headers={'X-CSRF-Token':state['csrf_token']})
        self.assertEqual(response.status_code,200)
    def test_server_reports_current_version(self):self.assertEqual(self.status()['version'],'2.9.13')


if __name__=='__main__':unittest.main()
