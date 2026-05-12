# FILE: scripts/validate_media_library_page.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_renamer_launcher_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('validate_media_library_page_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$Script = Join-Path $RepoRoot 'tools\media_renamer\media_library_page.py'

Write-MediaCleanupLog -LogPath $Log -Message 'Validate media library page v0.6.8'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('-m','py_compile',$Script) -LogPath $Log -WorkingDirectory $RepoRoot
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @($Script,'--self-test','--repo',$RepoRoot,'--media-root',$MediaRoot) -LogPath $Log -WorkingDirectory $RepoRoot

$RequiredMarkers = @('data-layout="compact-tree-v0.6.8"','Copy HTTP','Copy UNC','Copy SMB','new 7d','new 14d')
$Generated = Join-Path $MediaRoot 'Media_Library.html'
if (Test-Path -LiteralPath $Generated) {
    $Html = Get-Content -LiteralPath $Generated -Raw -Encoding UTF8
    foreach ($Marker in $RequiredMarkers) {
        if ($Html -notlike "*$Marker*") { throw "Generated page missing marker: $Marker" }
    }
}
Write-MediaCleanupLog -LogPath $Log -Message 'PASS: Media library validation completed.'
