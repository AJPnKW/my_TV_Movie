# FILE: scripts/run_media_cleanup_integrated.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_renamer_launcher_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('integrated_cleanup_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$RepoArg = Get-MediaCleanupPipelineRepoArgument -RepoRoot $RepoRoot

Write-MediaCleanupLog -LogPath $Log -Message 'Integrated media cleanup pipeline v0.6.8'
for ($Pass = 1; $Pass -le 5; $Pass++) {
    Write-MediaCleanupLog -LogPath $Log -Message ("START: Plan pass {0}" -f $Pass)
    Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('tools\media_renamer\media_cleanup_pipeline.py','plan',$RepoArg,$RepoRoot,'--media-root',$MediaRoot) -LogPath $Log -WorkingDirectory $RepoRoot
    $Summary = Get-MediaCleanupPlanSummary -RepoRoot $RepoRoot
    $Ready = 0
    if ($null -ne $Summary -and $null -ne $Summary.ready_to_fix) { $Ready = [int]$Summary.ready_to_fix }
    Write-MediaCleanupLog -LogPath $Log -Message ("Plan pass {0}: ready_to_fix={1}" -f $Pass, $Ready)
    if ($Ready -le 0) { break }
    Write-MediaCleanupLog -LogPath $Log -Message ("START: Apply pass {0}" -f $Pass)
    Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('tools\media_renamer\media_cleanup_pipeline.py','apply',$RepoArg,$RepoRoot,'--media-root',$MediaRoot) -LogPath $Log -WorkingDirectory $RepoRoot
}

Write-MediaCleanupLog -LogPath $Log -Message 'START: Playback QA and repair for all media files'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('tools\media_renamer\media_playback_qa.py','repair','--repo',$RepoRoot,'--media-root',$MediaRoot) -LogPath $Log -WorkingDirectory $RepoRoot

Write-MediaCleanupLog -LogPath $Log -Message 'START: Generate Media Library page'
Invoke-MediaCleanupNativeCommand -FilePath $Python -ArgumentList @('tools\media_renamer\media_library_page.py','--repo',$RepoRoot,'--media-root',$MediaRoot,'--http-base','http://AJP-Laptop-X1CG10:8010') -LogPath $Log -WorkingDirectory $RepoRoot
Write-MediaCleanupLog -LogPath $Log -Message 'PASS: Integrated media cleanup pipeline completed.'
