@echo off
setlocal
cd /d "%~dp0"
title HaruLog - GitHub Push and Deploy

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "tools\git_push.py"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 "tools\git_push.py"
    ) else (
        python "tools\git_push.py"
    )
)

echo.
pause
endlocal
