@echo off
echo Current directory: %cd%
cd /d "%~dp0\.."
echo Changed to: %cd%
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python scripts\generate_schema.py
pause
