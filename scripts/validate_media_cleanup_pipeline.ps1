# FILE: scripts/validate_media_cleanup_pipeline.ps1
# VERSION: v0.4.0
# PURPOSE: Validate the media cleanup pipeline without changing media files.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $RepoRoot

$LogRoot = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogRoot "validate_$Stamp.log.txt"

Write-Host "Validating media cleanup pipeline..."
& py "scripts\validate_media_renamer.py" 2>&1 | Tee-Object -FilePath $LogPath
if ($LASTEXITCODE -ne 0) {
    throw "Validation failed. Log: $LogPath"
}

Write-Host "Validation completed. Log: $LogPath"
Read-Host "Press Enter to close"
