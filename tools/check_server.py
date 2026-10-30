# -*- coding: utf-8 -*-
import sys
import os
import socket
import urllib.request
import json
import subprocess
from pathlib import Path

# 콘솔 UTF-8 출력 보장
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

root = Path(__file__).resolve().parent.parent

print("========================================================")
print(" [HaruLog] 서버 및 공개 홈페이지 연동 종합 진단 도구")
print("========================================================")
print(f"프로젝트 경로: {root}\n")

# 1. 5000번 포트 확인
print("[1. 로컬 5000 포트 수신 대기 상태]")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1.0)
is_listening = False
try:
    s.connect(('127.0.0.1', 5000))
    is_listening = True
    print(" ✔ 5000번 포트 리스닝 정상 확인 (서버 동작 중)")
except Exception:
    print(" ℹ 5000번 포트에 실행 중인 서버가 없습니다. (Run_harulog.bat 실행 필요)")
finally:
    s.close()

# 2. 로컬 API 응답 점검
print("\n[2. 로컬 API 엔드포인트 응답 점검 (http://127.0.0.1:5000)]")
if is_listening:
    try:
        req = urllib.request.Request("http://127.0.0.1:5000/api/auth/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(" ✔ /api/auth/status 응답 정상:")
            print(f"    - 버전: {data.get('version')}")
            print(f"    - 인증 상태: {'로그인됨' if data.get('authenticated') else '로그인 대기/정상'}")
            print(f"    - 관리자 초기설정 여부: {'완료됨' if data.get('configured') else '미설정(최초설정 필요)'}")
    except Exception as e:
        print(f" ⚠ 로컬 API 호출 응답 오류: {e}")
else:
    print(" ℹ 로컬 서버 미실행으로 API 테스트 생략")

# 3. Cloudflare Pages 연동 핵심 파일 점검
print("\n[3. Cloudflare Pages 및 배포 파일 점검]")
checks = [
    ("functions/api/[[path]].js", "Cloudflare Pages API 프록시 함수"),
    ("functions/uploads/[[path]].js", "Cloudflare Pages 파일 프록시 함수"),
    ("wsgi_pythonanywhere.py", "PythonAnywhere WSGI 어댑터"),
    ("index.html", "루트 정적 인덱스 (Cloudflare Pages용)"),
    ("login.html", "루트 정적 로그인 페이지"),
    ("LOGIN_AND_PUSH.bat", "GitHub 푸시 & 자동 배포 스크립트"),
    ("CONNECT_PUBLIC_SITE.md", "공개 홈페이지 연결 가이드")
]

all_files_ok = True
for rel_path, desc in checks:
    target = root / rel_path
    if target.is_file():
        print(f" ✔ {desc}: 확인 완료 ({rel_path})")
    else:
        print(f" ❌ {desc} 파일 없음: {rel_path}")
        all_files_ok = False

# 4. Git 저장소 상태 점검
print("\n[4. Git 저장소 및 원격지 연결 상태]")
try:
    p = subprocess.run(["git", "remote", "-v"], cwd=str(root), capture_output=True, text=True, timeout=3)
    if p.returncode == 0 and p.stdout.strip():
        print(" ✔ Git Remote 연결 완료:")
        for line in p.stdout.strip().splitlines():
            print(f"    {line}")
    else:
        print(" ℹ Git 원격 저장소(Remote)가 아직 연결되지 않았습니다.")
        print("    -> GitHub 레포지토리 생성 후 'git remote add origin <URL>'을 실행하세요.")
except Exception:
    print(" ℹ Git 미설치 또는 저장소 미초기화 상태")

print("\n========================================================")
if all_files_ok:
    print(" 🎉 모든 공개 홈페이지 연동 파일이 완벽하게 준비되었습니다!")
    print("    자세한 배포 절차는 CONNECT_PUBLIC_SITE.md 를 확인하세요.")
else:
    print(" ⚠ 일부 연동 파일이 누락되었습니다. 확인 후 다시 시도하세요.")
print("========================================================")
