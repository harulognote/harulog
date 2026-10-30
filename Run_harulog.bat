@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Existing .venv Python is missing. Nothing was installed.
    echo See README.md for manual installation instructions.
    pause
    exit /b 1
)
if not exist "startup.py" (
    echo [ERROR] startup.py is missing. Check the HaruLog folder.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" startup.py
set "HARULOG_EXIT=%errorlevel%"
if not "%HARULOG_EXIT%"=="0" (
    echo [ERROR] HaruLog stopped. See the message above and README.md.
    pause
)
exit /b %HARULOG_EXIT%
