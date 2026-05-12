# FILE: scripts/start_media_http_server.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$MediaRoot = 'C:\X1_Share\Recordings'
. (Join-Path $RepoRoot 'scripts\media_cleanup_common.ps1')
$LogDir = Join-Path $RepoRoot 'reports\media_http_server_logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('media_http_server_{0}.log.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Err = Join-Path $LogDir ('media_http_server_{0}.err.txt' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
$Script = Join-Path $RepoRoot 'tools\media_renamer\media_http_server.py'
$ArgumentText = Join-MediaCleanupArgumentList -ArgumentList @($Script,'--root',$MediaRoot,'--host','0.0.0.0','--port','8010')

Write-MediaCleanupLog -LogPath $Log -Message 'Start media HTTP server v0.6.8'
Write-MediaCleanupLog -LogPath $Log -Message ('CMD: {0} {1}' -f $Python, $ArgumentText)
$Process = Start-Process -FilePath $Python -ArgumentList $ArgumentText -WorkingDirectory $RepoRoot -RedirectStandardOutput $Log -RedirectStandardError $Err -WindowStyle Minimized -PassThru
$PidFile = Join-Path $LogDir 'media_http_server.pid.txt'
Set-Content -LiteralPath $PidFile -Value ([string]$Process.Id) -Encoding UTF8
Write-Host 'Media HTTP server started.'
Write-Host 'URL: http://AJP-Laptop-X1CG10:8010/Media_Library.html'
Write-Host "PID: $($Process.Id)"
Write-Host "Log: $Log"
Write-Host "Error log: $Err"
