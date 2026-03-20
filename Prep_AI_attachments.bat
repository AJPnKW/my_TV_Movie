@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================================
REM Project : my_TV_Movie
REM File    : Prep_AI_attachments.bat
REM Purpose : Launch Prep-AI-Attachments.ps1 with live console output + launcher log
REM Version : 2.1.0 (2025-12-17_180000)
REM ============================================================================

set "REPO_ROOT=C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
set "ATTACH_ROOT=%REPO_ROOT%\.txt_files_4_AI_attachments"
set "LOGS_DIR=%ATTACH_ROOT%\logs"

if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%" >nul 2>&1

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmmss"') do set "STAMP=%%i"
set "LAUNCH_LOG=%LOGS_DIR%\prep_ai_attachments-launch-%STAMP%.log.txt"

echo %DATE% %TIME% ^| START ^| Launching Prep-AI-Attachments.ps1
echo REPO_ROOT=%REPO_ROOT%
echo ATTACH_ROOT=%ATTACH_ROOT%
echo LOGS_DIR=%LOGS_DIR%
echo LAUNCH_LOG=%LAUNCH_LOG%
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "& { " ^
  "  $ll = '%LAUNCH_LOG%';" ^
  "  '--- LAUNCH START ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ---' | Out-File -FilePath $ll -Append -Encoding utf8;" ^
  "  & '%REPO_ROOT%\Prep-AI-Attachments.ps1' -RepoRoot '%REPO_ROOT%' 2>&1 | Tee-Object -FilePath $ll -Append;" ^
  "  $ec = $LASTEXITCODE;" ^
  "  '--- LAUNCH END ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' exit=' + $ec + ' ---' | Out-File -FilePath $ll -Append -Encoding utf8;" ^
  "  exit $ec" ^
  " }"

echo.
echo Launcher log saved:
echo   %LAUNCH_LOG%
echo.
set /p "X=Press ENTER to close..."
endlocal
