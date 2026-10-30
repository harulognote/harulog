# -*- coding: utf-8 -*-
"""HaruLog - Database Exporter (harulog_db -> harulog_backup.sql)"""
import os
import sys
from pathlib import Path
from datetime import datetime

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv(root / '.env', interpolate=False, encoding='utf-8-sig')

import mysql.connector

def escape_sql_val(val):
    if val is None:
        return 'NULL'
    if isinstance(val, bool):
        return '1' if val else '0'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (datetime,)):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    val_str = str(val).replace('\\', '\\\\').replace("'", "''").replace('\r', '\\r').replace('\n', '\\n')
    return f"'{val_str}'"

def export_database():
    output_path = root / 'harulog_backup.sql'
    print(f"[INFO] harulog_db 데이터베이스 연결 시도 중...")
    
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'harulog_db'),
        port=int(os.getenv('DB_PORT', 3306))
    )
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"[INFO] 발견된 테이블 목록: {len(tables)}개")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- HaruLog Database Backup\n")
        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("SET NAMES utf8mb4;\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

        for table in tables:
            print(f"  * 내보내는 중: {table} ...", end="", flush=True)
            # 1. CREATE TABLE DDL
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_sql = cursor.fetchone()[1]
            f.write(f"-- --------------------------------------------------------\n")
            f.write(f"-- Table structure for `{table}`\n")
            f.write(f"-- --------------------------------------------------------\n")
            f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
            f.write(f"{create_sql};\n\n")

            # 2. INSERT Data
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description]

            if rows:
                f.write(f"-- Dumping data for table `{table}` ({len(rows)} rows)\n")
                f.write(f"LOCK TABLES `{table}` WRITE;\n")
                
                # Batch inserts (50 rows per batch)
                batch_size = 50
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    values_list = []
                    for row in batch:
                        escaped_vals = [escape_sql_val(v) for v in row]
                        values_list.append(f"({', '.join(escaped_vals)})")
                    
                    cols_str = ', '.join([f"`{c}`" for c in col_names])
                    f.write(f"INSERT INTO `{table}` ({cols_str}) VALUES\n")
                    f.write(',\n'.join(values_list) + ';\n')
                
                f.write("UNLOCK TABLES;\n\n")
            print(f" 완료 ({len(rows)}행)")

        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")

    cursor.close()
    conn.close()
    size_kb = output_path.stat().st_size / 1024
    print(f"\n[SUCCESS] 백업 파일 생성 완료: {output_path.name} ({size_kb:.1f} KB)")

if __name__ == '__main__':
    try:
        export_database()
    except Exception as e:
        print(f"\n[ERROR] 백업 도중 오류 발생: {e}")
        sys.exit(1)
