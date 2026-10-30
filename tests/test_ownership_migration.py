from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import startup,migration_service as migration,manage,ownership


class OwnershipMigrationTests(unittest.TestCase):
    def conn(self):
        conn=Mock();cursor=Mock();cursor.fetchone.return_value=(1,);cursor.fetchall.return_value=[]
        def make_cursor(**kwargs):
            if kwargs.get('dictionary'):
                c=Mock();c.fetchall.return_value=[];return c
            return cursor
        conn.cursor.side_effect=make_cursor
        return conn,cursor
    def available(self):return {t:set(c.split()) for t,c in startup.REQUIRED_COLUMNS.items()}
    def test_cli_accepts_explicit_owner(self):
        with patch.object(sys,'argv',['manage.py','migrate','ownership','--owner-id','1','--apply','--backup-confirmed']),patch.object(startup,'require_environment',return_value=Path(sys.executable)),patch.object(manage,'migrate') as change:
            self.assertEqual(manage.main(),0)
            change.assert_called_once_with('ownership',True,True,1)
    def test_plan_is_select_only(self):
        conn,cursor=self.conn()
        with patch.object(startup,'schema_columns',return_value=self.available()):text=migration.inspect_ownership(conn,1)
        for call in cursor.execute.call_args_list:self.assertTrue(call.args[0].startswith('SELECT '))
        conn.commit.assert_not_called();self.assertIn('소유자',text)
    def test_apply_assigns_only_unowned_records_and_sets_marker_last(self):
        conn,cursor=self.conn()
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=self.available()):migration.apply_ownership(1)
        sql=[c.args[0] for c in cursor.execute.call_args_list]
        updates=[s for s in sql if s.startswith('UPDATE ')]
        self.assertEqual(len(updates),len(ownership.TABLES))
        self.assertTrue(all('WHERE owner_id IS NULL' in s for s in updates))
        self.assertIn("'ownership_v1'",sql[-1]);conn.commit.assert_called_once()
        self.assertFalse(any('DELETE FROM' in s or 'DROP TABLE' in s for s in sql))
    def test_missing_owner_denied_before_connect(self):
        with patch.object(startup,'connect_database') as conn,self.assertRaises(RuntimeError):migration.apply_ownership(None)
        conn.assert_not_called()
    def test_failure_never_marks_ready(self):
        conn,cursor=self.conn()
        def execute(sql,params=()):
            if sql.startswith('ALTER TABLE study_videos'):raise RuntimeError('DDL failure')
        cursor.execute.side_effect=execute
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=self.available()):
            with self.assertRaises(RuntimeError):migration.apply_ownership(1)
        self.assertFalse(any("'ownership_v1'" in c.args[0] for c in cursor.execute.call_args_list))
        conn.commit.assert_not_called();conn.rollback.assert_called_once()
    def test_manual_apply_requires_backup_flag(self):
        conn,cursor=self.conn()
        with patch.object(startup,'ensure_config'),patch.object(startup,'connect_database',return_value=conn),patch.object(migration,'inspect_ownership',return_value='plan'),patch.object(migration,'apply_ownership') as apply:
            with self.assertRaises(RuntimeError):manage.migrate('ownership',True,False,1)
            apply.assert_not_called()


if __name__=='__main__':unittest.main()
