# FILE: scripts/validate_media_cleanup_scripts.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$Scripts = @(
  'scripts\media_cleanup_common.ps1',
  'scripts\validate_media_library_page.ps1',
  'scripts\generate_media_library_page.ps1',
  'scripts\qa_media_playback.ps1',
  'scripts\start_media_http_server.ps1',
  'scripts\run_media_cleanup_integrated.ps1'
)
$Forbidden = @('Invoke-NativeProcess', '.ArgumentList.Add', '$Args =', '@Args', 'Ensure-Python', 'Run-Python')
foreach ($Script in $Scripts) {
    $Path = Join-Path $RepoRoot $Script
    if (-not (Test-Path -LiteralPath $Path)) { throw "Missing script: $Script" }
    $Text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    foreach ($Needle in $Forbidden) {
        if ($Text.Contains($Needle)) { throw "Forbidden code pattern '$Needle' found in $Script" }
    }
}
Write-Host 'PASS: Media cleanup PowerShell scripts passed static checks.'
