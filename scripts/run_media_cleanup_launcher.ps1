# FILE: scripts/run_media_cleanup_launcher.ps1
# VERSION: v0.4.0
# PURPOSE: Launch the optional two-button PySide6 cleanup launcher.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $RepoRoot

$Venv = Join-Path $RepoRoot ".venv_media_cleanup_launcher"
$PythonExe = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    py -m venv $Venv
}
& $PythonExe -m pip install --upgrade pip --no-cache-dir
& $PythonExe -m pip install PySide6==6.10.3 --no-cache-dir
& $PythonExe "tools\media_renamer\media_cleanup_launcher.py"
