@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title HaruLog - Server Diagnostics

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "tools\check_server.py"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 "tools\check_server.py"
    ) else (
        python "tools\check_server.py"
    )
)

echo.
pause
endlocal
