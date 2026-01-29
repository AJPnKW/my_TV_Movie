@echo off
setlocal
cd /d "%~dp0.."

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found in PATH. Install Python or add it to PATH.
  pause
  exit /b 1
)

echo Starting Inputs Editor Server on http://127.0.0.1:8787 ...
start "Inputs Editor Server" cmd /k "python tools\inputs_editor\inputs_editor_server.py --port 8787"

REM give the server a moment to start
timeout /t 1 >nul

start "My TV Hub" "http://127.0.0.1:8787/web/index.html"

echo.
echo Close the Inputs Editor Server window to stop the API.
