@echo off
setlocal
cd /d "%~dp0.."

REM FILE: tools/run_local_servers.bat
REM VERSION: 1.1.1
REM UPDATED: 2026-03-14T00:00:00Z
REM CHANGE NOTES:
REM - Route the old launcher entry point to the new smoke-test script.
REM - Preserve a double-clickable Windows entry point for local validation.
REM - Default the launcher to Chrome only.

powershell -ExecutionPolicy Bypass -File ".\tools\run_smoke_test.ps1" -Browser chrome
