# 🌐 HaruLog 공개 홈페이지 연결 가이드 (CenterHub 방식)

본 문서는 **하루로그(HaruLog)**를 **센터허브(CenterHub)**와 동일한 최신 아키텍처(Cloudflare Pages + Pages Functions 프록시 + PythonAnywhere/서버 백엔드 + GitHub 자동 배포)로 공개 홈페이지에 연결하고 배포하는 전체 절차를 안내합니다.

---

## 📌 0. 하루로그(HaruLog) vs 센터허브(CenterHub) 비교 및 정체성 구분

두 프로젝트는 목적과 데이터베이스 구조가 서로 다르므로 배포 시 환경설정 방식에 차이가 있습니다:

| 구분 | 하루로그 (HaruLog) | 센터허브 (CenterHub) |
| :--- | :--- | :--- |
| **핵심 목적** | 개인 일상 기록, 외국어 학습(스크립트/단어장), 골프 스코어, 공과금 영수증 OCR, 펫 족보 | 단체/동호회 커뮤니티 허브, 재정/회비 관리, 행사 참석명단, 간행물 e-Book 열람 |
| **데이터베이스** | **MariaDB / MySQL 필수** (`harulog_db`) | **파일 기반 (JSON, SQLite, PDF 등 외부 DB 불필요)** |
| **백엔드 엔진** | Python Flask WSGI (`main.py`) | Python 표준 SimpleHTTP WSGI (`server.py`) |
| **기본 포트** | **5000** | **9010** |
| **서버 DB 설정** | PythonAnywhere 무료 내장 MySQL 생성 또는 자체 MariaDB 연결 필수 | 별도 DB 설정 없이 폴더 압축 해제만으로 구동 |

---

## 📌 1. 전체 연결 아키텍처 개요

센터허브와 동일하게 **프론트엔드 CDN 배포**와 **백엔드 API 서버**를 유기적으로 결합하여, 비용 없이 최고 속도와 안정성을 확보하는 구조입니다.

```
[ 사용자 (모바일/PC 브라우저) ]
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Cloudflare Pages (무료 글로벌 CDN + HTTPS 자동 적용)       │
│    - 주소: https://<프로젝트명>.pages.dev 또는 커스텀 도메인  │
│    - 정적 리소스 서빙: HTML, CSS, JS, 웹앱 매니페스트         │
├─────────────────────────────────────────────────────────────┤
│ 2. Cloudflare Pages Functions (리버스 프록시)                │
│    - functions/api/[[path]].js     -> 백엔드 API 투명 중계   │
│    - functions/uploads/[[path]].js -> 백엔드 첨부파일 중계   │
└─────────────────────────────────────────────────────────────┘
          │ (백엔드로 프록시 전달)
          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 백엔드 서버 (PythonAnywhere 또는 개인 서버/VPS)            │
│    - wsgi_pythonanywhere.py (표준 WSGI 어댑터)              │
│    - main.py (Flask 2.9.13 엔진 & 인증/보안 시스템)           │
│    - MariaDB / MySQL 데이터베이스                            │
└─────────────────────────────────────────────────────────────┘
```

> **💡 이 방식의 핵심 장점:**
> 1. **CORS 및 쿠키 문제 완전 해결**: 프론트엔드와 백엔드가 같은 도메인(`/api/...`)으로 통신하므로 브라우저 보안 정책에 구애받지 않고 로그인/세션이 완벽하게 유지됩니다.
> 2. **무료 & 최고 속도**: 전 세계 어디서든 Cloudflare 엣지 네트워크를 통해 초고속으로 로딩됩니다.
> 3. **원클릭 자동 배포**: `LOGIN_AND_PUSH.bat` 더블클릭 한 번으로 GitHub에 올라가고, Cloudflare Pages가 수초 내에 자동 배포됩니다.

---

## 🚀 2. 단계별 구축 및 연결 절차

### 1단계: GitHub 저장소(Repository) 준비 및 소스 푸시

1. [GitHub](https://github.com/)에 로그인하고 새 저장소(New Repository)를 생성합니다.
   - 예: `harulog` (Public 또는 Private 모두 가능)
2. 로컬 하루로그 폴더(`c:\Users\SAMSUNG\Documents\test\test1`)에서 Git 원격 저장소를 연결합니다.
   - 터미널(CMD/PowerShell)을 열고:
   ```bash
   git init
   git remote add origin https://github.com/<본인계정>/harulog.git
   ```
3. 폴더 내 **`LOGIN_AND_PUSH.bat`** 파일을 더블클릭합니다.
   - 자동으로 루트 파일(`index.html`, `login.html`)과 Cloudflare Functions를 정리하여 GitHub `main` 브랜치로 푸시합니다.

---

### 2단계: Cloudflare Pages 생성 및 Functions 연동

1. [Cloudflare 대시보드](https://dash.cloudflare.com/)에 로그인합니다.
2. 좌측 메뉴에서 **[Workers & Pages]** $\rightarrow$ **[Create application]** $\rightarrow$ **[Pages]** 탭 선택 $\rightarrow$ **[Connect to Git]** 클릭.
3. 1단계에서 푸시한 **`harulog`** GitHub 저장소를 선택하고 **[Begin setup]**을 클릭합니다.
4. 배포 설정을 입력합니다:
   - **Project name**: 원하는 이름 입력 (예: `harulog` $\rightarrow$ `https://harulog.pages.dev` 주소 부여)
   - **Production branch**: `main`
   - **Framework preset**: `None`
   - **Build command**: (비워둠)
   - **Build output directory**: `.` (점 하나만 입력하여 루트 디렉토리 지정)
5. **[Environment variables (환경 변수)]** 설정 (선택/권장):
   - 변수 추가:
     - Variable name: `BACKEND_URL`
     - Value: 3단계에서 생성할 백엔드 주소 (예: `https://<아이디>.pythonanywhere.com`)
6. **[Save and Deploy]** 버튼을 클릭합니다.
   - 1분 내에 전세계로 배포가 완료되며 `https://<프로젝트명>.pages.dev` 링크가 생성됩니다.

---

### 3단계: 백엔드 서버(PythonAnywhere) 설정

PythonAnywhere(센터허브와 동일한 방식)에 백엔드 Flask 서버를 배포합니다:

1. [PythonAnywhere](https://www.pythonanywhere.com/)에 로그인합니다.
2. **[Web]** 탭으로 이동 $\rightarrow$ **[Add a new web app]** 클릭.
   - 도메인: 기본 도메인 선택 (예: `<계정명>.pythonanywhere.com`)
   - 프레임워크 선택 화면에서 **[Manual configuration (not Django)]** $\rightarrow$ **Python 3.10** (또는 3.11) 선택.
3. **[Consoles]** 탭에서 **Bash Console**을 열고 소스 가져오기:
   ```bash
   git clone https://github.com/<본인계정>/harulog.git ~/harulog
   cd ~/harulog
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **데이터베이스(MySQL/MariaDB) 설정 및 환경 변수 (`.env`) 작성**:
   - **중요**: 센터허브와 달리 하루로그는 **MariaDB/MySQL이 반드시 필요**합니다.
   
   **A. PythonAnywhere 무료 내장 MySQL을 사용할 경우 (가장 권장):**
   1. PythonAnywhere 대시보드의 **[Databases]** 탭으로 이동합니다.
   2. MySQL 암호(Password)를 설정하고 **[Set password]**를 클릭합니다.
   3. 하단의 **Create database** 칸에 `harulog_db`를 입력하고 **[Create]**를 누르면 `<계정명>$harulog_db`가 생성됩니다.
   4. 상단에 표시되는 호스트 주소(예: `<계정명>.mysql.pythonanywhere-services.com`)를 확인합니다.
   5. Bash 콘솔에서 `.env` 파일을 작성합니다 (`cp .env.example .env` 후 `nano .env`):
   ```ini
   DB_HOST=<계정명>.mysql.pythonanywhere-services.com
   DB_PORT=3306
   DB_USER=<계정명>
   DB_PASSWORD=<설정한_MySQL_비밀번호>
   DB_NAME=<계정명>$harulog_db
   ALLOWED_ORIGINS=https://<프로젝트명>.pages.dev
   ```

   **B. 자체 Linux/VPS 서버(Ubuntu, AWS EC2 등)를 사용할 경우:**
   - 서버의 로컬 MariaDB를 그대로 연결합니다:
   ```ini
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_db_password
   DB_NAME=harulog_db
   ALLOWED_ORIGINS=https://<프로젝트명>.pages.dev
   ```

   > **💡 자동 스키마 생성 안내:**
   > 하루로그는 빈 데이터베이스만 생성해두면, 첫 실행 시 모든 테이블(`daily_logs`, `study_videos`, `expense_invoices`, `app_members` 등)을 **자동으로 생성하고 마이그레이션**하므로 수동 SQL 생성이 필요 없습니다.

5. **WSGI 설정 파일 연결**:
   - PythonAnywhere의 **[Web]** 탭 $\rightarrow$ **Code** 섹션의 **WSGI configuration file** 링크 클릭.
   - 기본 내용을 모두 지우고 프로젝트에 포함된 `wsgi_pythonanywhere.py` 내용을 지정:
   ```python
   import sys
   import os
   from pathlib import Path

   project_home = '/home/<본인계정>/harulog'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   from dotenv import load_dotenv
   load_dotenv(os.path.join(project_home, '.env'), interpolate=False, encoding='utf-8-sig')

   from wsgi_pythonanywhere import application
   ```
6. **[Web]** 탭 상단의 녹색 **[Reload <도메인>]** 버튼을 클릭합니다.

---

### 4단계: 기존 로컬 harulog_db 데이터 & 첨부파일 이전 (Migration)

로컬에 누적된 기존 데이터(일기, 스터디 영상/단어장, 골프스코어, 공과금 영수증, 펫 족보 등 15개 테이블)와 첨부 사진을 새 서버로 완벽히 이전합니다:

#### 1) 로컬 DB 백업 추출 (원클릭)
- 로컬 하루로그 폴더에서 **`EXPORT_DATABASE.bat`** 파일을 더블클릭합니다.
- `harulog_backup.sql` 파일(약 70~100KB)이 자동으로 생성됩니다.

#### 2) 서버로 백업 파일 업로드
- **방법 A (GitHub 경유):**
  - `harulog_backup.sql`이 포함된 상태로 `LOGIN_AND_PUSH.bat` 실행 후, PythonAnywhere 콘솔에서 `git pull` 실행.
- **방법 B (PythonAnywhere 파일 탭 직접 업로드):**
  - PythonAnywhere 대시보드의 **[Files]** 탭 $\rightarrow$ `/home/<계정명>/harulog/` 폴더 이동 $\rightarrow$ **Upload a file** 버튼으로 `harulog_backup.sql` 직접 업로드.

#### 3) 서버 데이터베이스로 데이터 복원 (Restore)
- PythonAnywhere **Bash 콘솔**에서 아래 명령어 실행 (한 줄로 복원 완료):
  ```bash
  cd ~/harulog
  python tools/import_db.py
  ```
  *(성공 시: `[SUCCESS] 데이터베이스 복원 완료! (총 30개 SQL 블록 적용)` 메시지 출력)*

#### 4) 첨부파일(`uploads/`) 폴더 동기화
- 로컬의 `uploads/` 폴더 안의 이미지 파일들을 압축(`uploads.zip`)하여 PythonAnywhere의 `~/harulog/`로 업로드한 뒤, 콘솔에서 압축을 풉니다:
  ```bash
  cd ~/harulog
  unzip -o uploads.zip
  ```

---

### 5단계: 최종 동작 점검 및 운영

1. 브라우저에서 Cloudflare Pages 주소(`https://<프로젝트명>.pages.dev`)에 접속합니다.
2. 첫 화면에서 정상적으로 로그인 화면이 열리고, 백엔드와 연결되어 최초 관리자 등록 또는 로그인이 원활히 동작하는지 확인합니다.
3. 로컬에서 진단이 필요할 때는 **`CHECK_HARULOG_SERVER.bat`**을 실행하면 포트, 프로세스, API 응답, Cloudflare 연동 파일 상태를 즉시 점검할 수 있습니다.

---

## 📂 3. 프로젝트 내 연동 관련 파일 안내

- [functions/api/[[path]].js](file:///c:/Users/SAMSUNG/Documents/test/test1/functions/api/[[path]].js): Cloudflare Pages API 리버스 프록시 핸들러
- [functions/uploads/[[path]].js](file:///c:/Users/SAMSUNG/Documents/test/test1/functions/uploads/[[path]].js): 업로드 사진 및 파일 중계 핸들러
- [wsgi_pythonanywhere.py](file:///c:/Users/SAMSUNG/Documents/test/test1/wsgi_pythonanywhere.py): PythonAnywhere/클라우드용 고성능 WSGI 어댑터
- [LOGIN_AND_PUSH.bat](file:///c:/Users/SAMSUNG/Documents/test/test1/LOGIN_AND_PUSH.bat): 원클릭 GitHub 푸시 및 Cloudflare Pages 자동 배포 스크립트
- [CHECK_HARULOG_SERVER.bat](file:///c:/Users/SAMSUNG/Documents/test/test1/CHECK_HARULOG_SERVER.bat): 서버 및 공개 홈페이지 연동 종합 진단 도구
