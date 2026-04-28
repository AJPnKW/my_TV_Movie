@echo off
setlocal
cd /d "%~dp0.."

REM Compatibility wrapper. The canonical launcher lives at repo root:
REM run_local_servers.bat

call "%~dp0..\run_local_servers.bat" %*
