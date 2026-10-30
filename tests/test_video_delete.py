"""Deletion transaction checks without a live database or web server."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


class VideoDeleteTests(unittest.TestCase):
    def run_delete(self, row, failure=False):
        source = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        node = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'delete_video')
        node.decorator_list = []
        conn = Mock()
        cursor = conn.cursor.return_value
        cursor.fetchone.return_value = row
        if failure:
            cursor.execute.side_effect = [None, None, RuntimeError('write failed')]
        namespace = {'get_db_connection': lambda: conn, 'jsonify': lambda **kw: kw, 'app': Mock()}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'delete_video', 'exec'), namespace)
        return namespace['delete_video'](7), conn, cursor

    def test_success_removes_children_then_parent_and_commits(self):
        result, conn, cursor = self.run_delete({'id': 7})
        self.assertEqual(result, {'status': 'success'})
        queries = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn('FOR UPDATE', queries[0])
        self.assertEqual([q.split()[2] for q in queries[1:]], ['vocab_list', 'study_dictations', 'study_videos'])
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    def test_missing_or_other_owner_has_no_delete(self):
        result, conn, cursor = self.run_delete(None)
        self.assertEqual(result[1], 404)
        self.assertEqual(cursor.execute.call_count, 1)
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_failure_rolls_back(self):
        result, conn, cursor = self.run_delete({'id': 7}, True)
        self.assertEqual(result[1], 500)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
