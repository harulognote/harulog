"""HaruLog v2.7.1 regression tests — no live DB or external API calls."""
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
main.app.config['AUTH_ENABLED']=False
import study_service
import utility_service
import startup
from mysql.connector import Error


class Connection:
    def __init__(self, row=None, fail=False):
        self.row = row
        self.fail = fail
        self.events = []
        self.lastrowid = 9
    def cursor(self, **kwargs): return self
    def execute(self, sql, params=()): self.events.append(('sql', sql, params))
    def fetchone(self): return self.row
    def fetchall(self): return []
    def start_transaction(self): self.events.append(('start',))
    def commit(self):
        self.events.append(('commit',))
        if self.fail: raise Error('simulated write failure')
    def rollback(self): self.events.append(('rollback',))
    def close(self): self.events.append(('close',))
    def is_connected(self): return True


class LogTests(unittest.TestCase):
    def setUp(self):
        self.client = main.app.test_client()
        self.folder = tempfile.TemporaryDirectory()
        self.previous = main.app.config['UPLOAD_FOLDER']
        main.app.config['UPLOAD_FOLDER'] = self.folder.name
        self.old = Path(self.folder.name) / 'existing.jpg'
        self.old.write_bytes(b'original photo')
    def tearDown(self):
        main.app.config['UPLOAD_FOLDER'] = self.previous
        self.folder.cleanup()
    def conn(self, fail=False):
        return Connection({'id': 1, 'file_path': '/uploads/existing.jpg'}, fail)
    def test_rejected_empty_edit_keeps_old_photo(self):
        conn = self.conn()
        with patch.object(main, 'get_db_connection', return_value=conn):
            res = self.client.put('/api/logs/1', json={'content':'', 'remove_file':True})
        self.assertEqual(res.status_code,400)
        self.assertTrue(self.old.exists())
        self.assertNotIn(('commit',), conn.events)
    def test_failed_replacement_keeps_old_and_cleans_new(self):
        with patch.object(main,'get_db_connection',return_value=self.conn(True)):
            res=self.client.post('/api/logs/1',data={'content':'new','file':(io.BytesIO(b'new photo'),'new.jpg')})
        self.assertEqual(res.status_code,500)
        self.assertEqual([p.name for p in Path(self.folder.name).iterdir()], ['existing.jpg'])
    def test_successful_replacement_cleans_old(self):
        with patch.object(main,'get_db_connection',return_value=self.conn()):
            res=self.client.post('/api/logs/1',data={'content':'new','file':(io.BytesIO(b'new photo'),'new.jpg')})
        self.assertEqual(res.status_code,200)
        self.assertFalse(self.old.exists())
        self.assertEqual(len(list(Path(self.folder.name).iterdir())),1)
    def test_failed_delete_keeps_old(self):
        with patch.object(main,'get_db_connection',return_value=self.conn(True)):
            res=self.client.delete('/api/logs/1')
        self.assertEqual(res.status_code,500)
        self.assertTrue(self.old.exists())
    def test_successful_delete_removes_old(self):
        with patch.object(main,'get_db_connection',return_value=self.conn()):
            res=self.client.delete('/api/logs/1')
        self.assertEqual(res.status_code,200)
        self.assertFalse(self.old.exists())
    def test_db_unavailable_does_not_write_upload(self):
        with patch.object(main,'get_db_connection',return_value=None):
            res=self.client.post('/api/logs',data={'content':'new','file':(io.BytesIO(b'data'),'a.jpg')})
        self.assertEqual(res.status_code,503)
        self.assertEqual(len(list(Path(self.folder.name).iterdir())),1)
    def test_missing_log_not_saved(self):
        with patch.object(main,'get_db_connection',return_value=Connection()):
            res=self.client.put('/api/logs/999',json={'content':'new'})
        self.assertEqual(res.status_code,404)
    def test_html_attachment_is_downloaded(self):
        (Path(self.folder.name)/'test.html').write_text('<script>alert(1)</script>')
        res=self.client.get('/uploads/test.html')
        self.assertIn('attachment',res.headers['Content-Disposition'])
        res.close()
    def test_bad_json_content_rejected(self):
        res=self.client.post('/api/logs',json={'content':123})
        self.assertEqual(res.status_code,400)


class UtilityTests(unittest.TestCase):
    def test_invalid_numbers_rejected(self):
        for value in ['-100','abc','1e3','1.234','1,23','NaN','Infinity','9'*100,True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                utility_service.validate_utility_record({'billing_month':'2026-10','electricity_fee':value})
    def test_valid_total(self):
        data=utility_service.validate_utility_record({'billing_month':'2026-10','electricity_fee':'1,234.50','water_fee':'10.25'})
        self.assertEqual(data['total_fee'],'1244.75')
    def test_explicit_total_zero_kept(self):
        data=utility_service.validate_utility_record({'billing_month':'2026-10','electricity_fee':'100','total_fee':'0'})
        self.assertEqual(data['total_fee'],'0.00')
    def test_usage_overflow_rejected(self):
        with self.assertRaises(ValueError):
            utility_service.validate_utility_record({'billing_month':'2026-10','water_usage':'100000000'})
    def test_invalid_month_rejected(self):
        for month in ['0000-01','2026-13','2026-1']:
            with self.subTest(month=month), self.assertRaises(ValueError):
                utility_service.validate_utility_record({'billing_month':month})
    def test_recent_24_months_chronological(self):
        class Stats(Connection):
            def execute(self,sql,params=()): self.sql=sql
            def fetchall(self):
                # fixture with 36 months; use the actual requested sort/limit
                rows=[]
                for year in [2024,2025,2026]:
                    for month in range(1,13):
                        row=dict(billing_month=f'{year}-{month:02d}')
                        row.update({k:0 for k in ['electricity_fee','water_fee','telecom_fee','total_fee','electricity_usage','water_usage']})
                        rows.append(row)
                return sorted(rows,key=lambda r:r['billing_month'],reverse='DESC' in self.sql)[:24]
        from flask import Flask
        app=Flask('utility-test');utility_service.register_routes(app,lambda:Stats())
        res=app.test_client().get('/api/utility/stats')
        self.assertEqual(res.json['months'][0],'2025-01')
        self.assertEqual(res.json['months'][-1],'2026-12')
    def test_duplicate_month_returns_conflict(self):
        from flask import Flask
        class Duplicate(Connection):
            def execute(self,*args):raise Error(errno=1062,msg='duplicate')
        app=Flask('utility-duplicate');utility_service.register_routes(app,lambda:Duplicate())
        res=app.test_client().post('/api/utility/records',json={'billing_month':'2026-10'})
        self.assertEqual(res.status_code,409)
    def test_nonexistent_update_returns_404(self):
        from flask import Flask
        app=Flask('utility-missing');utility_service.register_routes(app,lambda:Connection())
        res=app.test_client().put('/api/utility/records/99',json={'billing_month':'2026-10'})
        self.assertEqual(res.status_code,404)


class StudyTests(unittest.TestCase):
    def test_japanese_and_chinese_extract_words(self):
        self.assertTrue(study_service.extract_tokens('私は日本語を勉強します。','JP'))
        self.assertTrue(study_service.extract_tokens('今天学习中文。','CN'))
    def test_invalid_words_rejected(self):
        for value in [[],[123],[{'word':1,'meaning':'뜻'}],[{'word':'x'*101,'meaning':'뜻'}]]:
            with self.subTest(value=value),self.assertRaises(ValueError):study_service.validate_words(value)
    def test_duplicate_insert_skipped(self):
        conn=Connection({'id':1})
        self.assertFalse(study_service.insert_word(conn,1,'Makan','먹다'))
        self.assertEqual(len(conn.events),1)
    def test_batch_duplicate_and_new_word(self):
        class Words(Connection):
            def __init__(self):super().__init__();self.words={'makan'}
            def execute(self,sql,params=()):
                if 'FROM study_videos' in sql:self.row={'id':1,'title':'A','script':'makan','language':'ID'}
                elif 'SELECT id FROM vocab_list' in sql:self.row={'id':3} if params[1].lower() in self.words else None
                elif 'INSERT INTO vocab_list' in sql:self.words.add(params[1].lower())
        db=Words()
        with patch.object(main,'get_db_connection',return_value=db):
            res=main.app.test_client().post('/api/study/videos/1/vocab/generate',json={'words':[{'word':'Makan','meaning':'먹다'},{'word':'rumah','meaning':'집'},{'word':'RUMAH','meaning':'집'}]})
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json['saved_count'],1)
        self.assertEqual(res.json['skipped_count'],2)
    def test_extraction_releases_db_before_translation(self):
        db=Connection({'id':1,'title':'A','script':'makan rumah','language':'ID'})
        def translate(*args):
            self.assertIn(('close',),db.events)
            return '뜻'
        with patch.object(main,'get_db_connection',return_value=db),patch.object(main,'translate_word_to_korean',side_effect=translate):
            res=main.app.test_client().post('/api/study/videos/1/vocab/generate',json={})
        self.assertEqual(res.status_code,200)
        self.assertEqual(len(res.json['extracted_words']),2)
    def test_invalid_batch_returns_400(self):
        db=Connection({'id':1,'title':'A','script':'makan','language':'ID'})
        with patch.object(main,'get_db_connection',return_value=db):
            res=main.app.test_client().post('/api/study/videos/1/vocab/generate',json={'words':[7]})
        self.assertEqual(res.status_code,400)
    def test_schema_preparation_preserves_language_values(self):
        class Schema(Connection):
            def __init__(self):super().__init__();self.languages=['영어','인도네시아어','US','ID']
            def execute(self,sql,params=()):
                if sql.startswith('UPDATE study_videos SET language=%s'):
                    self.languages=[params[0] if x==params[1] else x for x in self.languages]
            def fetchone(self):return {'Field':'exists'}
        db=Schema()
        with patch.object(main,'get_db_connection',return_value=db):main.prepare_schema()
        self.assertEqual(db.languages,['영어','인도네시아어','US','ID'])
    def test_no_foreign_dictionary_shortcut(self):
        with patch.object(main.urllib.request,'urlopen',side_effect=OSError('offline')):
            self.assertEqual(main.translate_word_to_korean('apple','ID'),'')
        self.assertEqual(main.translate_word_to_korean('apple','US'),'사과')


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        Path(self.folder.name, '.env').write_text('DB_HOST=127.0.0.1\nDB_NAME=harulog_db\n',encoding='utf-8')
        self.root_patch = patch.object(startup, 'ROOT', Path(self.folder.name))
        self.root_patch.start()
    def tearDown(self):
        self.root_patch.stop()
        self.folder.cleanup()
    def test_bad_port_rejected(self):
        with patch.dict(os.environ,{'APP_PORT':'70000'}),self.assertRaises(RuntimeError):startup.ensure_config()
    def test_db_name_injection_rejected(self):
        with patch.dict(os.environ,{'DB_NAME':'x`; DROP DATABASE x;'}),self.assertRaises(RuntimeError):startup.ensure_config()
    def test_missing_database_gives_actionable_error(self):
        with patch.object(startup,'ensure_config'),patch.dict(os.environ,{'HARULOG_CONNECTION':'local'}),patch.object(startup,'prepare_new_features',side_effect=Error(errno=1049)),self.assertRaisesRegex(RuntimeError,'기존 DB'):
            startup.run()
    def test_schema_failure_stops_startup(self):
        with patch.object(main,'get_db_connection',return_value=None),self.assertRaises(RuntimeError):main.prepare_schema()


if __name__=='__main__':
    unittest.main()
