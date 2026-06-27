@echo off
setlocal
cd /d "%~dp0"

REM FILE: run_local_servers.bat
REM VERSION: 1.3.2
REM UPDATED: 2026-06-27T00:00:00Z
REM CHANGE NOTES:
REM - Canonical root launcher for both static app pages and the local Inputs Editor API server.
REM - Starts/reuses port 8000 for static pages and port 8787 for the editor server.
REM - Default the launcher to Chrome.
REM - Opens only the Inputs Editor by default; pass -AllTabs for smoke-test browser tabs.
REM - Verifies that any reused Inputs Editor server on port 8787 belongs to this repo.

powershell -ExecutionPolicy Bypass -File ".\tools\run_smoke_test.ps1" -Browser chrome %*
