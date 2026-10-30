# -*- coding: utf-8 -*-
"""
HaruLog Version Manager & Packager
코드베이스 전체의 버전을 일괄 동기화하고, 정적 자산 동기화 및 최신 버전명으로 zip 패키지를 생성합니다.
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Windows 콘솔 UTF-8 출력 보장
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

root = Path(__file__).resolve().parent.parent

def get_current_version():
    auth_file = root / 'auth_service.py'
    text = auth_file.read_text(encoding='utf-8')
    m = re.search(r"version\s*=\s*'(\d+\.\d+\.\d+)'", text)
    if m:
        return m.group(1)
    return '2.9.15'

def set_version(new_ver):
    print(f"🔄 코드베이스 버전 동기화 진행 중: v{new_ver}")

    # 1. auth_service.py
    auth_file = root / 'auth_service.py'
    content = auth_file.read_text(encoding='utf-8')
    content = re.sub(r"version\s*=\s*'\d+\.\d+\.\d+'", f"version='{new_ver}'", content)
    auth_file.write_text(content, encoding='utf-8')

    # 2. main.py
    main_file = root / 'main.py'
    content = main_file.read_text(encoding='utf-8')
    content = re.sub(r"# HaruLog v\d+\.\d+\.\d+", f"# HaruLog v{new_ver}", content)
    main_file.write_text(content, encoding='utf-8')

    # 3. startup.py
    startup_file = root / 'startup.py'
    content = startup_file.read_text(encoding='utf-8')
    content = re.sub(r"HaruLog v\d+\.\d+\.\d+", f"HaruLog v{new_ver}", content)
    startup_file.write_text(content, encoding='utf-8')

    # 4. cloudflare_service.py
    cf_file = root / 'cloudflare_service.py'
    if cf_file.is_file():
        content = cf_file.read_text(encoding='utf-8')
        content = re.sub(r"HaruLog v\d+\.\d+\.\d+", f"HaruLog v{new_ver}", content)
        cf_file.write_text(content, encoding='utf-8')

    # 5. static/pets.js
    pets_file = root / 'static' / 'pets.js'
    if pets_file.is_file():
        content = pets_file.read_text(encoding='utf-8')
        content = re.sub(r"PET_CLIENT_VERSION\s*=\s*'\d+\.\d+\.\d+'", f"PET_CLIENT_VERSION='{new_ver}'", content)
        content = re.sub(r"// HaruLog v\d+\.\d+\.\d+", f"// HaruLog v{new_ver}", content)
        pets_file.write_text(content, encoding='utf-8')

    # 6. static/index.html
    idx_file = root / 'static' / 'index.html'
    if idx_file.is_file():
        content = idx_file.read_text(encoding='utf-8')
        content = re.sub(r'\?v=\d+\.\d+\.\d+', f'?v={new_ver}', content)
        content = re.sub(r'<span class="app-version">v\d+\.\d+\.\d+</span>', f'<span class="app-version">v{new_ver}</span>', content)
        idx_file.write_text(content, encoding='utf-8')

    # 7. static/login.html
    login_file = root / 'static' / 'login.html'
    if login_file.is_file():
        content = login_file.read_text(encoding='utf-8')
        content = re.sub(r'\?v=\d+\.\d+\.\d+', f'?v={new_ver}', content)
        content = re.sub(r'HaruLog v\d+\.\d+\.\d+', f'HaruLog v{new_ver}', content)
        login_file.write_text(content, encoding='utf-8')

    # 8. static/ -> static/static/ 복제본 일괄 동기화 (Pages 라우팅 호환성 유지)
    static_dir = root / 'static'
    static_nested = root / 'static' / 'static'
    if static_nested.exists():
        for src_file in static_dir.glob('*'):
            if src_file.is_file():
                dest_file = static_nested / src_file.name
                shutil.copy2(src_file, dest_file)

    print(f"✔ 모든 소스 파일 및 static/static 복제본에 v{new_ver} 동기화 완료")

def run_db_migration():
    mig_script = root / 'tools' / 'migrate_db.py'
    if mig_script.is_file():
        print("🔄 데이터베이스 마이그레이션 및 \\r\\n 개행 정제 실행 중...")
        res = subprocess.run([sys.executable, str(mig_script)], cwd=str(root), capture_output=True, text=True, encoding='utf-8')
        if res.returncode == 0:
            print("✔ SQLite 데이터베이스 무결 복원 및 줄바꿈 정제 완료")
        else:
            print(f"⚠ 마이그레이션 경고: {res.stderr}")

def package_zip(version):
    parent = root.parent
    zip_name = f"HaruLog_v{version}.zip"
    zip_path = parent / zip_name

    exclude_dirs = {'.git', '.venv', '__pycache__', 'node_modules', 'dist', 'build'}
    exclude_exts = {'.zip', '.tar', '.gz'}

    count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in root.rglob('*'):
            if any(part in exclude_dirs for part in item.parts):
                continue
            if item.is_file():
                if item.suffix.lower() in exclude_exts:
                    continue
                arcname = item.relative_to(root)
                zf.write(item, arcname)
                count += 1

    print(f"📦 배포 패키지 생성 완료: {zip_path.name} ({zip_path.stat().st_size:,} bytes, 파일 {count}개 포함)")
    return zip_path

if __name__ == '__main__':
    target_ver = sys.argv[1] if len(sys.argv) > 1 else '2.9.16'
    set_version(target_ver)
    run_db_migration()
    package_zip(target_ver)
