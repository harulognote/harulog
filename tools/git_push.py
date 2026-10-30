# -*- coding: utf-8 -*-
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Windows 콘솔 UTF-8 출력 보장
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

root = Path(__file__).resolve().parent.parent

print("========================================================")
print("   HaruLog - GitHub Push and Cloudflare Deploy")
print("========================================================")
print(f"프로젝트 경로: {root}\n")

# 1. Cloudflare Pages용 루트 정적 파일 최신화
static_dir = root / 'static'
for name in ('index.html', 'login.html'):
    src = static_dir / name
    dst = root / name
    if src.is_file():
        shutil.copy2(src, dst)
print("✔ Cloudflare Pages 루트 정적 파일 동기화 완료")

# 2. Git 설치 확인
git_bin = shutil.which('git')
if not git_bin:
    print("\n[ERROR] Git이 설치되어 있지 않거나 PATH에 없습니다.")
    print("Git 설치 후 다시 실행해 주세요: https://git-scm.com/")
    sys.exit(1)

# 3. Git 초기화 및 origin 확인
dot_git = root / '.git'
if not dot_git.is_dir():
    print("✔ Git 저장소 초기화 중...")
    subprocess.run(['git', 'init'], cwd=str(root), check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', 'https://harulognote@github.com/harulognote/harulog.git'], cwd=str(root))
else:
    # 계정 충돌 방지: harulognote 계정 명시
    subprocess.run(['git', 'remote', 'set-url', 'origin', 'https://harulognote@github.com/harulognote/harulog.git'], cwd=str(root))

# 로컬 사용자 설정 (센터허브와 계정 분리)
subprocess.run(['git', 'config', 'user.name', 'harulognote'], cwd=str(root), stderr=subprocess.DEVNULL)
subprocess.run(['git', 'config', 'user.email', 'harulognote@gmail.com'], cwd=str(root), stderr=subprocess.DEVNULL)

# main 브랜치 설정
subprocess.run(['git', 'branch', '-M', 'main'], cwd=str(root), stderr=subprocess.DEVNULL)

# 4. 스테이징 & 커밋
print("✔ 파일 스테이징 진행 중 (git add .)...")
subprocess.run(['git', 'add', '.'], cwd=str(root), check=True)

commit_msg = f"Update HaruLog for Cloudflare Pages ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
res = subprocess.run(['git', 'commit', '-m', commit_msg], cwd=str(root), capture_output=True, text=True)
if res.returncode == 0:
    print(f"✔ 커밋 완료: {commit_msg}")
else:
    print("ℹ 새로운 변경 사항이 없거나 이미 최신 상태입니다.")

# 5. GitHub 푸시
print("\n[GitHub 푸시 시작]")
print("원격 저장소(https://github.com/harulognote/harulog)로 전송 중입니다...")
print("(브라우저 인증 창이 열리면 로그인을 완료해 주세요)\n")

push_res = subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=str(root))

print("\n========================================================")
if push_res.returncode == 0:
    print(" 🎉 [SUCCESS] GitHub 업로드가 성공적으로 완료되었습니다!")
    print("    Cloudflare Pages에서 자동으로 빌드 및 배포가 시작됩니다.")
else:
    print(" ⚠ [INFO] 'main' 브랜치 푸시 재시도 중...")
    push_retry = subprocess.run(['git', 'push', '-u', 'origin', 'HEAD'], cwd=str(root))
    if push_retry.returncode == 0:
        print(" 🎉 [SUCCESS] GitHub 업로드가 성공적으로 완료되었습니다!")
    else:
        print(" ❌ [ERROR] GitHub 푸시에 실패했습니다.")
        print("    - GitHub 로그인 창이 뜨면 로그인/인증을 완료해 주세요.")
        print("    - 원격 저장소 권한 및 인터넷 연결을 확인해 주세요.")
print("========================================================")
