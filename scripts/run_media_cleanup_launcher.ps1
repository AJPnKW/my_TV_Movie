# FILE: scripts/run_media_cleanup_launcher.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$Python = Join-Path $RepoRoot '.venv_media_cleanup\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    py -3.12 -m venv (Join-Path $RepoRoot '.venv_media_cleanup')
    $Python = Join-Path $RepoRoot '.venv_media_cleanup\Scripts\python.exe'
}
& $Python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: PySide6==6.10.3
& $Python (Join-Path $RepoRoot 'tools\media_renamer\media_cleanup_launcher.py')
