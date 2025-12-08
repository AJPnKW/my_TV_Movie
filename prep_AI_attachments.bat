@echo off
setlocal enabledelayedexpansion

REM ==========================================================
REM Project:   my_TV_Movie - AI attachment prep
REM Launcher:  prep_AI_attachments.bat
REM Purpose:   Launch PowerShell script with logging AND visible console output
REM Version:   1.0.6 (12-07-2025)
REM ==========================================================

set "PARENT=%cd%"
set "LOGS=%PARENT%\logs"

if not exist "%LOGS%" mkdir "%LOGS%"

REM Use WMIC to get timestamp in MM-DD-YYYY-HHMMSS format
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format \"MM-dd-yyyy-HHmmss\""') do set STAMP=%%i

set "BATLOG=%LOGS%\prep_AI_attachments-launch-%STAMP%.log.txt"
set "PS_SCRIPT=%PARENT%\Prep-AI-Attachments.ps1"

echo [START] %date% %time% Launching Prep-AI-Attachments.ps1 > "%BATLOG%"
echo Parent: %PARENT% >> "%BATLOG%"
echo Logs:   %LOGS%   >> "%BATLOG%"

REM Pass BATLOG to PowerShell via environment
set "BATLOG=%BATLOG%"

if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    echo Using Windows PowerShell 5.1 >> "%BATLOG%"
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
) else (
    echo Using PowerShell (pwsh) >> "%BATLOG%"
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
)

echo [END] %date% %time% Completed Prep-AI-Attachments.ps1 >> "%BATLOG%"

echo.
echo Launcher log saved: %BATLOG%
echo Press ENTER to close...
pause >nul

endlocal
