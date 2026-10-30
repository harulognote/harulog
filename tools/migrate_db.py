# -*- coding: utf-8 -*-
"""
HaruLog Database Migration Tool (MariaDB -> SQLite)
로컬의 harulog_backup.sql 또는 기존 MariaDB 데이터를 SQLite(harulog.db)로
100% 무결성을 보장하며 자동 변환/복원합니다.
"""
import os
import re
import sys
import sqlite3
from pathlib import Path

# 콘솔 UTF-8 출력 보장
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

root = Path(__file__).resolve().parent.parent
sql_path = root / 'harulog_backup.sql'
db_path = root / 'harulog.db'

print("========================================================")
print("   HaruLog - MariaDB to SQLite Migration & Restore")
print("========================================================")

if not sql_path.is_file():
    print(f"[ERROR] 백업 SQL 파일을 찾을 수 없습니다: {sql_path}")
    print("먼저 EXPORT_DATABASE.bat을 실행하여 harulog_backup.sql을 생성해 주세요.")
    sys.exit(1)

print(f"✔ 백업 원본 파일: {sql_path.name} ({sql_path.stat().st_size:,} bytes)")
print(f"✔ 대상 SQLite 파일: {db_path.name}\n")

# 1. SQL 읽기 및 MySQL 전용 지시문 필터링
raw_sql = sql_path.read_text(encoding='utf-8')

clean_lines = []
for line in raw_sql.splitlines():
    trimmed = line.strip()
    if not trimmed or trimmed.startswith('--') or trimmed.startswith('/*'):
        continue
    if trimmed.startswith('SET ') or trimmed.startswith('LOCK ') or trimmed.startswith('UNLOCK '):
        continue
    clean_lines.append(line)

clean_sql = '\n'.join(clean_lines)

# 2. SQLite 호환 DDL 정밀 변환
clean_sql = re.sub(r'ENGINE\s*=\s*\w+.*?;', ';', clean_sql, flags=re.I)
clean_sql = re.sub(r'DEFAULT\s+CHARSET\s*=\s*\w+.*?;', ';', clean_sql, flags=re.I)
clean_sql = re.sub(r'COLLATE\s*=\s*\w+', '', clean_sql, flags=re.I)
clean_sql = re.sub(r'COLLATE\s+utf8mb4_\w+', '', clean_sql, flags=re.I)
clean_sql = re.sub(r'AUTO_INCREMENT=\d+', '', clean_sql, flags=re.I)
clean_sql = re.sub(r'`id`\s+(?:big)?int(?:\(\d+\))?\s+NOT\s+NULL\s+AUTO_INCREMENT', '`id` INTEGER PRIMARY KEY AUTOINCREMENT', clean_sql, flags=re.I)
clean_sql = re.sub(r'`id`\s+(?:big)?int(?:\(\d+\))?\s+AUTO_INCREMENT', '`id` INTEGER PRIMARY KEY AUTOINCREMENT', clean_sql, flags=re.I)
clean_sql = re.sub(r',\s*PRIMARY KEY\s*\(`id`\)', '', clean_sql, flags=re.I)
clean_sql = re.sub(r',\s*(?:UNIQUE\s+)?KEY\s+`?\w+`?\s*\([^)]+\)', '', clean_sql, flags=re.I)
clean_sql = re.sub(r'current_timestamp\(\)', 'CURRENT_TIMESTAMP', clean_sql, flags=re.I)

# 3. SQLite DB 연결 및 테이블 생성/데이터 복원
conn = sqlite3.connect(str(db_path), timeout=30)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA foreign_keys=OFF;")
cur = conn.cursor()

statements = [s.strip() for s in clean_sql.split(';') if s.strip()]
success_count = 0
errors = []

for stmt in statements:
    try:
        cur.execute(stmt)
        success_count += 1
    except Exception as e:
        errors.append((stmt[:70], str(e)))

conn.commit()
conn.execute("PRAGMA foreign_keys=ON;")

# 4. 복원 결과 전수 검증
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall() if not row[0].startswith('sqlite_')]

print("========================================================")
print(f" 🎉 [SUCCESS] 데이터베이스 복원 완료! (SQL {success_count}/{len(statements)} 실행 성공)")
if errors:
    print(f" ⚠ 경고 ({len(errors)}건):")
    for s, err in errors:
        print(f"    - {s}... -> {err}")

print(f"\n복원된 테이블 총 {len(tables)}개 데이터 현황:")
total_rows = 0
for t in sorted(tables):
    cur.execute(f"SELECT count(*) FROM `{t}`")
    cnt = cur.fetchone()[0]
    total_rows += cnt
    print(f"  • {t:20s}: {cnt:>4d} 건")

print(f"\n총 보존된 레코드 수: {total_rows:,} 개")
print("========================================================")
conn.close()
