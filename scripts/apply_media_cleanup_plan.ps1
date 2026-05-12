# FILE: scripts/apply_media_cleanup_plan.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_renamer_launcher_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('apply_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$RepoArg = Get-MediaCleanupPipelineRepoArgument -RepoRoot $RepoRoot

Write-MediaCleanupLog -LogPath $Log -Message 'Applying cleanup plan v0.6.8'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('tools\media_renamer\media_cleanup_pipeline.py','apply',$RepoArg,$RepoRoot,'--media-root',$MediaRoot) -LogPath $Log -WorkingDirectory $RepoRoot
Write-MediaCleanupLog -LogPath $Log -Message 'PASS: Cleanup apply completed.'
