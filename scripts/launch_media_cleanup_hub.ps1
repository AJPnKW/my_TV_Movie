# FILE: scripts/launch_media_cleanup_hub.ps1
# VERSION: v0.5.4
# PURPOSE: Location-independent launcher for the Media Cleanup Hub.
$ErrorActionPreference = "Stop"
$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$Launcher = Join-Path $RepoRoot "scripts\run_media_cleanup_launcher.ps1"
if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Missing Media Cleanup Hub launcher: $Launcher"
}
Set-Location -LiteralPath $RepoRoot
powershell -NoProfile -ExecutionPolicy Bypass -File $Launcher
