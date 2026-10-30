# -*- coding: utf-8 -*-
"""HaruLog - Database Importer / Restorer (harulog_backup.sql -> target DB)"""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv(root / '.env', interpolate=False, encoding='utf-8-sig')

import mysql.connector

def import_database(sql_file='harulog_backup.sql'):
    backup_file = root / sql_file
    if not backup_file.is_file():
        print(f"[ERROR] 백업 파일을 찾을 수 없습니다: {backup_file}")
        sys.exit(1)

    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'harulog_db')

    print(f"[INFO] 복원 대상 데이터베이스: {db_user}@{db_host}:{db_port}/{db_name}")
    print(f"[INFO] 백업 파일 로드 중: {backup_file.name} ({backup_file.stat().st_size / 1024:.1f} KB)")

    conn = mysql.connector.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        database=db_name
    )
    cursor = conn.cursor()

    with open(backup_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 문장 단위 분리 실행
    statements = sql_content.split(';\n')
    success_count = 0

    print("[INFO] SQL 문장 실행 및 복원 진행 중...")
    for stmt in statements:
        cleaned = stmt.strip()
        if not cleaned:
            continue
        try:
            cursor.execute(cleaned)
            success_count += 1
        except Exception as e:
            # 주석이나 빈 블록 제외한 에러 출력
            if not cleaned.startswith('--'):
                print(f"  [WARN] 쿼리 실행 경고: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n[SUCCESS] 데이터베이스 복원 완료! (총 {success_count}개 SQL 블록 적용)")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'harulog_backup.sql'
    try:
        import_database(target)
    except Exception as e:
        print(f"\n[ERROR] 복원 도중 오류 발생: {e}")
        sys.exit(1)
