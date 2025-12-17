@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM =============================================================================
REM Project  : my_TV_Movie
REM File     : prep_AI_attachments.bat
REM Purpose  : Launcher for Prep-AI-Attachments.ps1 with deterministic paths + logs
REM Version  : 1.1.0
REM Date     : 2025-12-17
REM Author   : AJPnKW
REM =============================================================================
REM Key rules:
REM - Repo root is the folder containing THIS .bat (not the current working dir)
REM - Logs go to:    <repo>\.txt_files_4_AI_attachments\logs
REM - Zips go to:    <repo>\.txt_files_4_AI_attachments\archieves
REM - Script is:     <repo>\Prep-AI-Attachments.ps1
REM - No loops. One run only. Optional pause at end.
REM =============================================================================

REM --- Resolve repo root from this file location (stable) ---
set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

set "ATTACH_ROOT=%REPO_ROOT%\.txt_files_4_AI_attachments"
set "LOGS_DIR=%ATTACH_ROOT%\logs"

if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%" >nul 2>&1

REM --- Timestamp for launcher log name ---
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd_HHmmss\""') do set "STAMP=%%i"

set "BATLOG=%LOGS_DIR%\prep_ai_attachments-launch-%STAMP%.log.txt"
set "PS_SCRIPT=%REPO_ROOT%\Prep-AI-Attachments.ps1"

REM --- Emit launch context (both console + file) ---
echo %date% %time% ^| START ^| Launching Prep-AI-Attachments.ps1>"%BATLOG%"
echo REPO_ROOT=%REPO_ROOT%>>"%BATLOG%"
echo ATTACH_ROOT=%ATTACH_ROOT%>>"%BATLOG%"
echo LOGS_DIR=%LOGS_DIR%>>"%BATLOG%"
echo PS_SCRIPT=%PS_SCRIPT%>>"%BATLOG%"

echo.
echo %date% %time% ^| START ^| Launching Prep-AI-Attachments.ps1
echo REPO_ROOT=%REPO_ROOT%
echo ATTACH_ROOT=%ATTACH_ROOT%
echo LOGS_DIR=%LOGS_DIR%

REM --- Export BATLOG for the PowerShell script (so it can skip it if scanning) ---
set "BATLOG=%BATLOG%"

REM --- Prefer pwsh (PowerShell 7+) if available; otherwise fallback to Windows PowerShell 5.1 ---
where pwsh >nul 2>&1
if %errorlevel%==0 (
  echo %date% %time% ^| INFO  ^| Using pwsh>>"%BATLOG%"
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -RepoRoot "%REPO_ROOT%"
) else (
  echo %date% %time% ^| INFO  ^| Using Windows PowerShell 5.1>>"%BATLOG%"
  "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -RepoRoot "%REPO_ROOT%"
)

echo %date% %time% ^| END   ^| Completed Prep-AI-Attachments.ps1>>"%BATLOG%"

echo.
echo Launcher log saved:
echo   %BATLOG%

REM --- Pause (optional). If you don’t want pause, run: prep_AI_attachments.bat --no-pause
if /i "%~1"=="--no-pause" goto :eof

echo Press ENTER to close...
pause >nul

endlocal
