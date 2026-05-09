@echo off
setlocal
cd /d "%~dp0\.."
py scripts\run_media_renamer.py
pause
