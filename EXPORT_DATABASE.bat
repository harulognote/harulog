@echo off
setlocal
cd /d "%~dp0"
title HaruLog - Database Exporter

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "tools\export_db.py"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 "tools\export_db.py"
    ) else (
        python "tools\export_db.py"
    )
)

echo.
pause
endlocal
