@echo off
setlocal
cd /d "%~dp0.."

REM Compatibility wrapper. The canonical launcher starts both required servers.
call "%~dp0..\run_local_servers.bat" %*
