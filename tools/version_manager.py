# -*- coding: utf-8 -*-
"""
HaruLog Version Manager & Packager
코드베이스 전체의 버전을 일괄 동기화하고, 최신 버전명으로 zip 패키지를 생성합니다.
"""
import re
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
    return '2.9.14'

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

    # 5. static/index.html & static/static/index.html
    for p in [root / 'static' / 'index.html', root / 'static' / 'static' / 'index.html']:
        if p.is_file():
            content = p.read_text(encoding='utf-8')
            content = re.sub(r'\?v=\d+\.\d+\.\d+', f'?v={new_ver}', content)
            content = re.sub(r'v\d+\.\d+\.\d+', f'v{new_ver}', content)
            p.write_text(content, encoding='utf-8')

    # 6. static/login.html & static/static/login.html
    for p in [root / 'static' / 'login.html', root / 'static' / 'static' / 'login.html']:
        if p.is_file():
            content = p.read_text(encoding='utf-8')
            content = re.sub(r'\?v=\d+\.\d+\.\d+', f'?v={new_ver}', content)
            content = re.sub(r'HaruLog v\d+\.\d+\.\d+', f'HaruLog v{new_ver}', content)
            p.write_text(content, encoding='utf-8')

    print(f"✔ 모든 소스 파일 및 화면 텍스트에 v{new_ver} 동기화 완료")

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

    print(f"📦 패키징 완료: {zip_path.name} ({zip_path.stat().st_size:,} bytes, 파일 {count}개 포함)")
    return zip_path

if __name__ == '__main__':
    target_ver = sys.argv[1] if len(sys.argv) > 1 else '2.9.15'
    set_version(target_ver)
    package_zip(target_ver)
