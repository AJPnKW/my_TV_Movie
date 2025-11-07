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
