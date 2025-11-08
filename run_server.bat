:: =============================================================================
:: File: run_server.bat
:: Project: my_TV_Movie
:: Version: v1.0.0 (2025-11-09)
::
:: Purpose:
::   Convenience script to run local test server (app.py).
:: =============================================================================
@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Initial build of data.json
python scripts\fetch_tmdb.py

REM Launch server on http://<this_pc_ip>:8811/
python app.py
