:: =============================================================================
:: File: run_server.bat
:: Project: my_TV_Movie
:: Version: v1.1.0 (2026-04-28)
::
:: Purpose:
::   Compatibility entry point. Delegates to the canonical local launcher.
:: =============================================================================
@echo off
setlocal
cd /d "%~dp0"
call "%~dp0tools\run_local_servers.bat" %*
