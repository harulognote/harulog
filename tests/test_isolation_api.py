"""Real Flask routes and two login sessions against isolated SQLite business rows."""
from datetime import datetime
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import main,startup,ownership
from test_auth import Database,HASH,PASSWORD


class Hybrid:
    def __init__(self,members,sql):self.members=members;self.sql=sql;self.global_conn=members.connect()
    def cursor(self,**kwargs):return HybridCursor(self,self.global_conn.cursor(**kwargs),kwargs.get('dictionary',False))
    def commit(self):self.sql.commit();self.global_conn.commit()
    def rollback(self):self.sql.rollback();self.global_conn.rollback()
    def start_transaction(self):self.global_conn.start_transaction()
    def close(self):pass


class HybridCursor:
    def __init__(self,conn,global_cursor,dictionary):self.conn=conn;self.global_cursor=global_cursor;self.dictionary=dictionary;self.local=None
    def execute(self,sql,params=()):
        if re.search(r'\bapp_(members|system|admin_audit)\b',sql) or 'information_schema.COLUMNS' in sql:self.local=None;return self.global_cursor.execute(sql,params)
        text=re.sub(r'\bFOR UPDATE\b','',sql,flags=re.I).replace('%s','?').replace('INSERT IGNORE','INSERT OR IGNORE')
        self.local=self.conn.sql.execute(text,params)
    def _row(self,row):
        if row is None:return None
        if not self.dictionary:return tuple(row)
        item=dict(row)
        if item.get('created_at'):item['created_at']=datetime.fromisoformat(item['created_at'])
        return item
    def fetchone(self):return self._row(self.local.fetchone()) if self.local is not None else self.global_cursor.fetchone()
    def fetchall(self):return [self._row(r) for r in self.local.fetchall()] if self.local is not None else self.global_cursor.fetchall()
    @property
    def lastrowid(self):return self.local.lastrowid if self.local is not None else self.global_cursor.lastrowid
    @property
    def rowcount(self):return self.local.rowcount if self.local is not None else self.global_cursor.rowcount
    def close(self):pass


class IsolationAPITests(unittest.TestCase):
    def setUp(self):
        self.db=Database({'id':1,'username':'owner','password_hash':HASH,'auth_version':1})
        self.db.members[2]={'id':2,'username':'member','display_name':'Member','password_hash':HASH,'auth_version':1,'role':'user','status':'active'}
        self.sql=sqlite3.connect(':memory:');self.sql.row_factory=sqlite3.Row
        for table in ownership.TABLES:
            cols=startup.REQUIRED_COLUMNS[table].split()
            self.sql.execute('CREATE TABLE '+table+' (owner_id INTEGER,'+','.join(c+(' INTEGER' if c in ('id','video_id') else ' TEXT') for c in cols if c!='owner_id')+')')
        self.folder=tempfile.TemporaryDirectory();self.old_folder=main.app.config['UPLOAD_FOLDER'];self.old_enabled=main.app.config['AUTH_ENABLED']
        main.app.config.update(AUTH_ENABLED=True,UPLOAD_FOLDER=self.folder.name)
        for uid,filename in [(1,'alice.jpg'),(2,'bob.jpg')]:
            Path(self.folder.name,filename).write_bytes(b'photo')
            self.sql.execute('INSERT INTO daily_logs(owner_id,id,content,file_path,created_at) VALUES(?,?,?,?,?)',(uid,uid,'secret-'+str(uid),'/uploads/'+filename,'2026-10-28 10:00:00'))
        self.sql.commit()
        self.patch=patch.object(main.mysql.connector,'connect',side_effect=lambda **kwargs:Hybrid(self.db,self.sql));self.patch.start()
        self.admin=main.app.test_client();self.user=main.app.test_client()
        for client,name in [(self.admin,'owner'),(self.user,'member')]:
            csrf=client.get('/api/auth/status').json['csrf_token']
            self.assertEqual(client.post('/api/auth/login',json={'username':name,'password':PASSWORD},headers={'X-CSRF-Token':csrf}).status_code,200)
    def tearDown(self):
        self.patch.stop();main.app.config.update(AUTH_ENABLED=self.old_enabled,UPLOAD_FOLDER=self.old_folder);self.folder.cleanup();self.sql.close()
    def headers(self,client):return {'X-CSRF-Token':client.get('/api/auth/status').json['csrf_token']}
    def test_admin_list_contains_only_own_records(self):
        rows=self.admin.get('/api/logs').json;self.assertEqual([r['content'] for r in rows],['secret-1'])
    def test_user_list_contains_only_own_records(self):
        rows=self.user.get('/api/logs').json;self.assertEqual([r['content'] for r in rows],['secret-2'])
    def test_admin_cannot_download_user_photo(self):
        self.assertEqual(self.admin.get('/uploads/bob.jpg').status_code,404)
        self.assertEqual(self.admin.get('/uploads/alice.jpg').status_code,200)
    def test_user_cannot_download_admin_photo(self):self.assertEqual(self.user.get('/uploads/alice.jpg').status_code,404)
    def test_user_cannot_delete_admin_record_or_photo(self):
        res=self.user.delete('/api/logs/1',headers=self.headers(self.user))
        self.assertEqual(res.status_code,404);self.assertTrue(Path(self.folder.name,'alice.jpg').exists())
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM daily_logs WHERE id=1').fetchone()[0],1)
    def test_user_cannot_update_admin_record(self):
        res=self.user.put('/api/logs/1',json={'content':'stolen'},headers=self.headers(self.user))
        self.assertEqual(res.status_code,404)
        self.assertEqual(self.sql.execute('SELECT content FROM daily_logs WHERE id=1').fetchone()[0],'secret-1')
    def test_new_record_forced_to_session_owner(self):
        res=self.user.post('/api/logs',json={'content':'new','owner_id':1},headers=self.headers(self.user))
        self.assertEqual(res.status_code,201)
        self.assertEqual(self.sql.execute("SELECT owner_id FROM daily_logs WHERE content='new'").fetchone()[0],2)
    def test_regular_user_admin_api_denied(self):self.assertEqual(self.user.get('/api/admin/members').status_code,403)


if __name__=='__main__':unittest.main()
