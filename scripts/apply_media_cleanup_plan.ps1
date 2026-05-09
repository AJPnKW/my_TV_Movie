# FILE: scripts/apply_media_cleanup_plan.ps1
# VERSION: v0.4.0
# PURPOSE: Apply safe actions from the latest media cleanup plan.

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
$LogPath = Join-Path $LogRoot "apply_$Stamp.log.txt"

Write-Host "Applying latest safe cleanup plan..."
Write-Host "Repo: $RepoRoot"
Write-Host "Media: $MediaRoot"

& py "tools\media_renamer\media_cleanup_pipeline.py" apply --repo-root "$RepoRoot" --media-root "$MediaRoot" 2>&1 | Tee-Object -FilePath $LogPath
if ($LASTEXITCODE -ne 0) {
    throw "Cleanup apply failed. Log: $LogPath"
}

Write-Host "Cleanup apply completed. Log: $LogPath"
Read-Host "Press Enter to close"
