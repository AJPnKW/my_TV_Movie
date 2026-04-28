@echo off
setlocal
cd /d "%~dp0"

REM FILE: run_local_servers.bat
REM VERSION: 1.3.0
REM UPDATED: 2026-04-28T00:00:00Z
REM CHANGE NOTES:
REM - Canonical root launcher for both static app pages and the local Inputs Editor API server.
REM - Starts/reuses port 8000 for static pages and port 8787 for the editor server.
REM - Default the launcher to Chrome.

powershell -ExecutionPolicy Bypass -File ".\tools\run_smoke_test.ps1" -Browser chrome %*
