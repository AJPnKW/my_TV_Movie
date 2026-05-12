# FILE: scripts/repair_your_friends_neighbors_playback.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_renamer_launcher_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('repair_your_friends_neighbors_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$Script = Join-Path $RepoRoot 'tools\media_renamer\media_playback_qa.py'

Write-MediaCleanupLog -LogPath $Log -Message 'Targeted repair for Your Friends & Neighbors v0.6.8'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @($Script,'repair','--repo',$RepoRoot,'--media-root',$MediaRoot,'--title-filter','Your Friends') -LogPath $Log -WorkingDirectory $RepoRoot
Write-MediaCleanupLog -LogPath $Log -Message 'PASS: Targeted repair completed.'
