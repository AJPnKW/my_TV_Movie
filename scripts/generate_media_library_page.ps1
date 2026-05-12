# FILE: scripts/generate_media_library_page.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_renamer_launcher_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('generate_media_library_page_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$Script = Join-Path $RepoRoot 'tools\media_renamer\media_library_page.py'

Write-MediaCleanupLog -LogPath $Log -Message 'Generate media library page v0.6.8'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @($Script,'--repo',$RepoRoot,'--media-root',$MediaRoot,'--http-base','http://AJP-Laptop-X1CG10:8010') -LogPath $Log -WorkingDirectory $RepoRoot
Write-MediaCleanupLog -LogPath $Log -Message 'PASS: Media_Library.html generated.'
Write-Host 'HTML: C:\X1_Share\Recordings\Media_Library.html'
Write-Host 'GitHub copy: C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\web\Media_Library.html'
