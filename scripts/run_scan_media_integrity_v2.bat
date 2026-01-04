@echo off
setlocal
set SCRIPT=C:\Utilities\scripts\scan_media_integrity_v2.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
echo.
echo (Window kept open by launcher)
pause
