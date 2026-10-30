# -*- coding: utf-8 -*-
"""
HaruLog Dual Database Adapter
MariaDB (MySQL)와 SQLite를 완벽히 듀얼 지원하는 데이터베이스 연결 계층.
환경 변수 DB_ENGINE='sqlite' 또는 'mariadb'에 따라 동작하며,
PythonAnywhere 등 무료 클라우드 환경에서는 자동으로 SQLite(harulog.db)를 사용합니다.
"""
import os
import re
import sys
import sqlite3
from pathlib import Path

from datetime import datetime

# 프로젝트 루트 경로
ROOT_DIR = Path(__file__).resolve().parent

class SmartDateTime(str):
    """
    SQLite가 날짜/시간을 문자열로 반환하더라도,
    기존 MariaDB 코드의 .strftime() 및 .isoformat() 호출과 100% 호환되도록 지원하는 스마트 문자열 객체.
    """
    def strftime(self, fmt):
        val = str(self).strip()
        try:
            if 'T' in val:
                dt = datetime.fromisoformat(val)
            elif len(val) == 10:
                dt = datetime.strptime(val, '%Y-%m-%d')
            elif '.' in val:
                dt = datetime.strptime(val.split('.')[0], '%Y-%m-%d %H:%M:%S')
            else:
                dt = datetime.strptime(val[:19], '%Y-%m-%d %H:%M:%S')
            return dt.strftime(fmt)
        except Exception:
            return val

    def isoformat(self):
        val = str(self).strip()
        return val[:10] if len(val) >= 10 and ' ' not in val[:10] else val


def _wrap_row(row):
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str) and len(v) >= 10 and v[4] == '-' and v[7] == '-':
            d[k] = SmartDateTime(v)
    return d

class SQLiteCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self._mock_rows = None
        self._mock_idx = 0

    def execute(self, sql, params=()):
        clean_sql = sql.strip()

        # 1. SHOW COLUMNS FROM table LIKE ... 에뮬레이션
        show_m = re.match(r'^SHOW\s+COLUMNS\s+FROM\s+[`"]?(\w+)[`"]?(?:\s+LIKE\s+(.+))?', clean_sql, re.I)
        if show_m:
            table = show_m.group(1)
            like_expr = show_m.group(2)
            target_col = None
            if like_expr:
                expr = like_expr.strip()
                if expr == '%s' and params:
                    target_col = str(params[0]).strip("'\"% ")
                else:
                    target_col = expr.strip("'\"% ")
            
            try:
                self._cursor.execute(f"PRAGMA table_info('{table}')")
                info_rows = self._cursor.fetchall()
            except Exception:
                info_rows = []

            matched = []
            for col in info_rows:
                col_name = col['name'] if isinstance(col, sqlite3.Row) else col[1]
                col_type = col['type'] if isinstance(col, sqlite3.Row) else col[2]
                col_notnull = col['notnull'] if isinstance(col, sqlite3.Row) else col[3]
                if target_col is None or target_col.lower() == col_name.lower():
                    matched.append({
                        'Field': col_name,
                        'Type': col_type,
                        'Null': 'NO' if col_notnull else 'YES'
                    })

            self._mock_rows = matched
            self._mock_idx = 0
            return self

        # 2. DDL 변환 (MySQL CREATE TABLE/ALTER TABLE 호환)
        if re.match(r'^(CREATE|ALTER)\s+', clean_sql, re.I):
            clean_sql = re.sub(r'ENGINE\s*=\s*\w+.*', '', clean_sql, flags=re.I)
            clean_sql = re.sub(r'DEFAULT\s+CHARSET\s*=\s*\w+', '', clean_sql, flags=re.I)
            clean_sql = re.sub(r'COLLATE\s*=\s*\w+', '', clean_sql, flags=re.I)
            clean_sql = re.sub(r'COLLATE\s+utf8mb4_\w+', '', clean_sql, flags=re.I)
            clean_sql = re.sub(r'AUTO_INCREMENT=\d+', '', clean_sql, flags=re.I)
            clean_sql = re.sub(r'(?:BIG)?INT(?:\(\d+\))?\s+NOT\s+NULL\s+AUTO_INCREMENT\s+PRIMARY\s+KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT', clean_sql, flags=re.I)
            clean_sql = re.sub(r'(?:BIG)?INT(?:\(\d+\))?\s+AUTO_INCREMENT\s+PRIMARY\s+KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT', clean_sql, flags=re.I)
            clean_sql = re.sub(r'AUTO_INCREMENT\s+PRIMARY\s+KEY', 'PRIMARY KEY AUTOINCREMENT', clean_sql, flags=re.I)
            clean_sql = re.sub(r'current_timestamp\(\)', 'CURRENT_TIMESTAMP', clean_sql, flags=re.I)

        # 3. INSERT IGNORE -> INSERT OR IGNORE
        if re.match(r'^INSERT\s+IGNORE\b', clean_sql, re.I):
            clean_sql = re.sub(r'^INSERT\s+IGNORE\b', 'INSERT OR IGNORE', clean_sql, flags=re.I)

        # 4. 파라미터 플레이스홀더 %s -> ? 변환
        if '%s' in clean_sql:
            clean_sql = clean_sql.replace('%s', '?')

        self._mock_rows = None
        return self._cursor.execute(clean_sql, params)

    def fetchone(self):
        if self._mock_rows is not None:
            if self._mock_idx < len(self._mock_rows):
                res = self._mock_rows[self._mock_idx]
                self._mock_idx += 1
                return _wrap_row(res)
            return None
        row = self._cursor.fetchone()
        if row is None:
            return None
        return _wrap_row(row)

    def fetchall(self):
        if self._mock_rows is not None:
            res = self._mock_rows[self._mock_idx:]
            self._mock_idx = len(self._mock_rows)
            return [_wrap_row(r) for r in res]
        rows = self._cursor.fetchall()
        return [_wrap_row(r) for r in rows]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class SQLiteConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return SQLiteCursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        try:
            return self._conn.close()
        except Exception:
            pass

    def is_connected(self):
        return True

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_sqlite_connection(db_path=None):
    if not db_path:
        db_path = os.getenv('SQLITE_DB_PATH', str(ROOT_DIR / 'harulog.db'))
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return SQLiteConnection(conn)


def get_mariadb_connection():
    try:
        import mysql.connector
        from mysql.connector import Error
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'harulog_db'),
            connection_timeout=5,
            port=int(os.getenv('DB_PORT', 3306))
        )
        return conn
    except Exception as e:
        return None


def get_connection():
    """
    환경 설정에 따라 적절한 데이터베이스 커넥션을 반환합니다:
    1. DB_ENGINE == 'sqlite': 항상 SQLite 사용
    2. DB_ENGINE == 'mariadb': MariaDB 시도 (실패 시 None)
    3. 지정되지 않은 경우:
       - harulog.db 파일이 있거나 PythonAnywhere/클라우드 환경이면 SQLite 우선
       - 그렇지 않고 로컬 MariaDB 접속 가능하면 MariaDB 사용
    """
    engine = os.getenv('DB_ENGINE', '').strip().lower()

    if engine == 'sqlite':
        return get_sqlite_connection()
    elif engine == 'mariadb':
        conn = get_mariadb_connection()
        if conn is not None:
            return conn
        print("⚠ MariaDB 연결 실패 (DB_ENGINE=mariadb)")
        return None

    # 자동 감지 모드
    sqlite_file = ROOT_DIR / 'harulog.db'
    is_pythonanywhere = 'PYTHONANYWHERE_DOMAIN' in os.environ or 'pythonanywhere' in os.environ.get('HOME', '')

    if is_pythonanywhere or sqlite_file.is_file():
        return get_sqlite_connection()

    # 로컬 MariaDB 시도
    conn = get_mariadb_connection()
    if conn is not None:
        return conn

    # MariaDB 실패 시 SQLite 자동 활성화
    return get_sqlite_connection()
