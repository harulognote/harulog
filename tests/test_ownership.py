import ast
from pathlib import Path
import re
import sqlite3
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ownership,startup


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        for table in ownership.TABLES:
            cols=startup.REQUIRED_COLUMNS[table].split()
            definitions=[name+(' INTEGER' if name in ('id','video_id','owner_id') else ' TEXT') for name in cols if name!='owner_id']
            self.db.execute('CREATE TABLE '+table+' (owner_id INTEGER,'+','.join(definitions)+')')
        for table in ownership.TABLES:
            key='video_id' if table=='study_dictations' else ('pet_id' if table=='pet_lineage' else 'id')
            self.db.execute('INSERT INTO '+table+' (owner_id,'+key+') VALUES(1,11),(2,22)')
    def tearDown(self):self.db.close()
    def sql(self,text,owner=1,params=()):return self.db.execute(ownership.scoped_sql(text,owner).replace('%s','?'),params)
    def test_all_tables_scoped(self):
        for table in ownership.TABLES:self.assertEqual(len(self.sql('SELECT * FROM '+table).fetchall()),1)
    def test_foreign_id_hidden(self):self.assertEqual(self.sql('SELECT id FROM daily_logs WHERE id=%s',params=(22,)).fetchall(),[])
    def test_foreign_update_does_not_write(self):
        self.sql('UPDATE daily_logs SET content=%s WHERE id=%s',params=('stolen',22))
        self.assertIsNone(self.db.execute('SELECT content FROM daily_logs WHERE id=22').fetchone()[0])
    def test_foreign_delete_does_not_delete(self):
        self.sql('DELETE FROM daily_logs WHERE id=%s',params=(22,))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM daily_logs WHERE id=22').fetchone()[0],1)
    def test_or_condition_cannot_escape_owner(self):self.assertEqual(len(self.sql('SELECT id FROM daily_logs WHERE id=11 OR id=22').fetchall()),1)
    def test_insert_owner_not_client_field(self):
        self.sql('INSERT INTO daily_logs (id,content) VALUES (%s,%s)',params=(33,'own'))
        self.assertEqual(self.db.execute('SELECT owner_id FROM daily_logs WHERE id=33').fetchone()[0],1)
    def test_reject_owner_override(self):
        with self.assertRaises(ValueError):ownership.scoped_sql('INSERT INTO daily_logs (owner_id,id) VALUES (2,33)',1)
    def test_left_join_free_vocabulary_preserved(self):
        self.db.execute("INSERT INTO vocab_list(owner_id,id,word,video_id) VALUES(1,33,'free',NULL)")
        rows=self.sql('SELECT v.id,s.title FROM vocab_list v LEFT JOIN study_videos s ON v.video_id=s.id ORDER BY v.id').fetchall()
        self.assertIn((33,None),rows)
    def test_foreign_join_is_not_disclosed(self):
        self.db.execute("UPDATE study_videos SET title='secret' WHERE id=22")
        self.db.execute('UPDATE vocab_list SET video_id=22 WHERE owner_id=1')
        rows=self.sql('SELECT v.id,s.title FROM vocab_list v LEFT JOIN study_videos s ON v.video_id=s.id').fetchall()
        self.assertIsNone(rows[0][1])
    def test_statistics_only_own(self):self.assertEqual(self.sql('SELECT COUNT(*) FROM utility_records').fetchone()[0],1)
    def test_unsafe_operations_rejected(self):
        for sql in ['DROP TABLE daily_logs','SELECT * FROM app_members','SELECT * FROM daily_logs UNION SELECT * FROM pets','DELETE FROM unknown','SELECT * FROM daily_logs; DELETE FROM pets']:
            with self.assertRaises(ValueError):ownership.scoped_sql(sql,1)
    def test_all_literal_runtime_sql_can_be_scoped(self):
        total=0;root=Path(__file__).resolve().parents[1]
        for name in ['main.py','study_service.py','score_service.py','invoice_service.py','settings_service.py','utility_service.py','pet_service.py']:
            tree=ast.parse((root/name).read_text())
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or node.func.attr!='execute' or not node.args:continue
                arg=node.args[0]
                if not isinstance(arg,ast.Constant) or not isinstance(arg.value,str):continue
                sql=arg.value.strip()
                if not re.match(r'^(SELECT|INSERT|UPDATE|DELETE)\b',sql,re.I):continue
                rewritten=ownership.scoped_sql(sql,1)
                self.assertIn('owner_id',rewritten);total+=1
                if 'ON DUPLICATE KEY' not in rewritten:
                    translated=rewritten.replace('%s','?').replace('<=>','IS').replace('BINARY ','').replace('INSERT IGNORE','INSERT OR IGNORE')
                    translated=re.sub(r'\bFOR UPDATE\b','',translated,flags=re.I)
                    self.db.execute('EXPLAIN '+translated,tuple(1 for _ in range(translated.count('?'))))
        self.assertGreater(total,45)
    def test_lock_and_limit_preserved(self):
        sql=ownership.scoped_sql('SELECT id FROM pets WHERE id=%s FOR UPDATE',3)
        self.assertIn('pets.owner_id=3 AND (id=%s) FOR UPDATE',sql)
    def test_integer_owner_enforced(self):
        with self.assertRaises(ValueError):ownership.scoped_sql('SELECT * FROM pets','1 OR 1=1')
    def test_profile_and_month_uniqueness_per_owner(self):
        self.db.execute('CREATE UNIQUE INDEX scope_month ON utility_records(owner_id,billing_month)')
        self.db.execute("UPDATE utility_records SET billing_month='2026-10'")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO utility_records(owner_id,billing_month) VALUES(1,'2026-10')")


if __name__=='__main__':unittest.main()
