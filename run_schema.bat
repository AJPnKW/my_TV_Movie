@echo off
setlocal
cd /d "%~dp0"

REM FILE: run_schema.bat
REM VERSION: 1.1.0
REM UPDATED: 2026-04-28T00:00:00Z
REM PURPOSE:
REM - Generate schema.json from data/data.json using the repo-local schema script.

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

if /I "%~1"=="--no-pause" (
  python scripts\generate_schema.py
) else (
  python scripts\generate_schema.py --pause
)
