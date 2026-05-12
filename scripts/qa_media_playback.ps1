# FILE: scripts/qa_media_playback.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_renamer_launcher_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('qa_media_playback_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$Script = Join-Path $RepoRoot 'tools\media_renamer\media_playback_qa.py'

Write-MediaCleanupLog -LogPath $Log -Message 'Media playback QA v0.6.8'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('-m','py_compile',$Script) -LogPath $Log -WorkingDirectory $RepoRoot
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @($Script,'scan','--repo',$RepoRoot,'--media-root',$MediaRoot) -LogPath $Log -WorkingDirectory $RepoRoot
Write-MediaCleanupLog -LogPath $Log -Message 'PASS: Playback QA scan completed.'
