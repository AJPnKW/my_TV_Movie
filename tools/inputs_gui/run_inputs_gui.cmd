@echo off
setlocal
set "REPO=%~dp0..\..\.."
for %%I in ("%REPO%") do set "REPO=%%~fI"
cd /d "%REPO%" || (echo FAILED: cd "%REPO%" & exit /b 1)
python -m tools.inputs_gui.inputs_gui_app
endlocal
