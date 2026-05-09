# FILE: scripts/run_media_cleanup_plan.ps1
# VERSION: v0.4.0
# PURPOSE: Build a non-destructive media cleanup plan.

[CmdletBinding()]
param(
    [string]$MediaRoot = "C:\X1_Share\Recordings"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $RepoRoot

$LogRoot = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogRoot "plan_$Stamp.log.txt"

Write-Host "Building cleanup plan..."
Write-Host "Repo: $RepoRoot"
Write-Host "Media: $MediaRoot"

& py "tools\media_renamer\media_cleanup_pipeline.py" plan --repo-root "$RepoRoot" --media-root "$MediaRoot" 2>&1 | Tee-Object -FilePath $LogPath
if ($LASTEXITCODE -ne 0) {
    throw "Cleanup plan failed. Log: $LogPath"
}

Write-Host "Cleanup plan completed. Log: $LogPath"
Read-Host "Press Enter to close"
