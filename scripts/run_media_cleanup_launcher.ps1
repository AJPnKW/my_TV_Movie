# FILE: scripts/run_media_cleanup_launcher.ps1
# VERSION: v0.4.4
$ErrorActionPreference = "Stop"
$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
Set-Location -LiteralPath $RepoRoot
powershell -ExecutionPolicy Bypass -File scripts\run_media_cleanup_plan.ps1
