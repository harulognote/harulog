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
print("   HaruLog - GitHub Push & Multi-Account Manager")
print("========================================================")
print(f"프로젝트 경로: {root}\n")

# 1. Cloudflare Pages 빌드 출력 디렉토리 확인 (static 폴더)
static_dir = root / 'static'
if not (static_dir / 'index.html').is_file():
    print("[ERROR] static/index.html 파일이 존재하지 않습니다.")
    sys.exit(1)
print("✔ Cloudflare Pages 정적 에셋 확인 완료 (static/ 디렉토리)")

# 2. Git 설치 확인
git_bin = shutil.which('git')
if not git_bin:
    print("\n[ERROR] Git이 설치되어 있지 않거나 PATH에 없습니다.")
    print("Git 설치 후 다시 실행해 주세요: https://git-scm.com/")
    sys.exit(1)

# 3. Git 초기화 및 격리 설정 (CenterHub와 독립)
dot_git = root / '.git'
if not dot_git.is_dir():
    print("✔ Git 저장소 초기화 중...")
    subprocess.run(['git', 'init'], cwd=str(root), check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', 'https://harulognote@github.com/harulognote/harulog.git'], cwd=str(root))
else:
    # 계정 충돌 방지: origin URL에 harulognote 명시
    res_url = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=str(root), capture_output=True, text=True)
    curr_url = res_url.stdout.strip() if res_url.returncode == 0 else ''
    if 'harulognote@' not in curr_url and '@' not in curr_url:
        subprocess.run(['git', 'remote', 'set-url', 'origin', 'https://harulognote@github.com/harulognote/harulog.git'], cwd=str(root))

# 센터허브(wookyunghub)와 자격 증명 충돌 방지: URL 경로별 자격 증명 분리
subprocess.run(['git', 'config', '--local', 'credential.useHttpPath', 'true'], cwd=str(root))
subprocess.run(['git', 'config', '--local', 'user.name', 'harulognote'], cwd=str(root))

# 현재 설정된 이메일 확인 (기본값: jhjungbiz@gmail.com)
res_email = subprocess.run(['git', 'config', '--local', 'user.email'], cwd=str(root), capture_output=True, text=True)
current_email = res_email.stdout.strip() if res_email.returncode == 0 and res_email.stdout.strip() else 'jhjungbiz@gmail.com'
subprocess.run(['git', 'config', '--local', 'user.email', current_email], cwd=str(root))

print(f"✔ 하루로그 Git 계정: harulognote")
print(f"✔ 하루로그 인증 이메일: {current_email}")
print(f"✔ 저장소 자격 증명 분리 (credential.useHttpPath=true): 활성화됨\n")

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

# 5. GitHub 푸시 실행
print("\n[GitHub 푸시 시작]")
print("원격 저장소(harulognote/harulog)로 전송 중입니다...\n")

push_res = subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=str(root))

if push_res.returncode == 0:
    print("\n========================================================")
    print(" 🎉 [SUCCESS] 하루로그(HaruLog) GitHub 푸시가 완료되었습니다!")
    print("    Cloudflare Pages에서 자동으로 빌드 및 배포가 시작됩니다.")
    print("========================================================")
    sys.exit(0)

# 푸시 실패 시 (동일 PC 계정 충돌 등)
print("\n========================================================")
print(" ⚠ [INFO] 푸시 인증 실패 또는 다른 계정(CenterHub 등)과 충돌 발생")
print("========================================================")
print(" 동일 PC에 여러 GitHub 계정이 등록되어 있는 경우,")
print(" GitHub 개인 액세스 토큰(PAT)을 사용하면 100% 확실하게 푸시할 수 있습니다.\n")

print(" 1. GitHub 토큰(PAT) 입력하여 즉시 푸시 (권장 - 1초 완료)")
print(" 2. 이메일 주소 변경 후 브라우저 로그인 재시도")
print(" 3. Windows 자격 증명 캐시 초기화 후 재시도")
print(" 4. 종료")

choice = input("\n 원하는 작업 번호를 입력하세요 [1/2/3/4] (기본 1): ").strip()
if choice in ('', '1'):
    print("\n--- [GitHub Personal Access Token 안내] ---")
    print("1) 브라우저에서 https://github.com/settings/tokens 접속 (harulognote 계정)")
    print("2) 'Generate new token (classic)' 클릭 -> Note에 'harulog' 입력")
    print("3) 'repo' 항목 체크 후 하단 'Generate token' 버튼 클릭")
    print("4) 생성된 토큰(ghp_... 또는 github_pat_...)을 복사하여 아래에 붙여넣으세요.")
    token = input("\n토큰 붙여넣기: ").strip()
    if token:
        token_url = f"https://{token}@github.com/harulognote/harulog.git"
        subprocess.run(['git', 'remote', 'set-url', 'origin', token_url], cwd=str(root))
        print("\n✔ 토큰 적용 완료. 다시 푸시를 시도합니다...")
        push_retry = subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=str(root))
        if push_retry.returncode == 0:
            print("\n 🎉 [SUCCESS] 하루로그가 성공적으로 푸시되었습니다!")
            print("    이후부터는 LOGIN_AND_PUSH.bat만 누르면 자동으로 푸시됩니다.")
        else:
            print("\n ❌ 토큰 인증에 실패했습니다. 토큰 권한(repo)을 확인해 주세요.")

elif choice == '2':
    new_email = input(f"새로 사용할 인증 이메일 주소 입력 (현재: {current_email}): ").strip()
    if new_email:
        subprocess.run(['git', 'config', '--local', 'user.email', new_email], cwd=str(root))
        print(f"✔ 인증 이메일을 '{new_email}'로 설정했습니다.")
    subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=str(root))

elif choice == '3':
    print("Windows Credential Manager의 GitHub 캐시를 삭제합니다...")
    subprocess.run('cmdkey /delete:LegacyGeneric:target=git:https://github.com', shell=True)
    print("✔ 캐시 삭제 완료. 다시 푸시합니다 (로그인 창이 뜨면 harulognote로 로그인하세요):")
    subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=str(root))

print("========================================================")
