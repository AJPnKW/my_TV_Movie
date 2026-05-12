@echo off
setlocal
set REPO=C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\scripts\run_media_cleanup_launcher.ps1"
endlocal
