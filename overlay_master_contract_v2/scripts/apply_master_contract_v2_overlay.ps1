#requires -version 5.1
<#
FILE: scripts/apply_master_contract_v2_overlay.ps1
PURPOSE:
  Apply Master Contract v2 documentation overlay.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$OverlayRoot = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogDir = Join-Path $RepoRoot 'logs'
$LogPath = Join-Path $LogDir ("apply_master_contract_v2_{0}.log.txt" -f $Timestamp)

function Ensure-Directory {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Write-Info {
    param([Parameter(Mandatory=$true)][string]$Message)
    $line = '[INFO] {0}' -f $Message
    Write-Host $line -ForegroundColor Cyan
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Write-WarnVisible {
    param([Parameter(Mandatory=$true)][string]$Message)
    $line = '[WARNING] {0}' -f $Message
    Write-Host $line -ForegroundColor Magenta
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

Ensure-Directory -Path $LogDir
Set-Location -LiteralPath $RepoRoot

if (-not (Test-Path -LiteralPath '.git')) {
    throw "Not a git repo: $RepoRoot"
}

Write-Info 'Applying Master Contract v2 overlay'
Write-WarnVisible 'This warning uses MAGENTA so warnings are visually distinct from normal Git white text.'

$files = @(
    'docs\00_master_contract.html',
    'reports\documentation_consolidation\archive_requirement_extraction_matrix_v2.html',
    'codex_prompts\master_contract_v2_implementation_prompt.txt'
)

foreach ($relativePath in $files) {
    $source = Join-Path $OverlayRoot $relativePath
    $destination = Join-Path $RepoRoot $relativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing overlay file: $source"
    }
    Ensure-Directory -Path (Split-Path -Parent $destination)
    Copy-Item -LiteralPath $source -Destination $destination -Force
    Write-Info ("Updated {0}" -f $relativePath)
}

$content = Get-Content -LiteralPath (Join-Path $RepoRoot 'docs\00_master_contract.html') -Raw -Encoding UTF8
foreach ($needle in @('🎟️','web/watchlist.html</code></td><td class="status-bad">Deprecated','web/discover.html</code></td><td class="status-good">Active','web/watch_me.html</code></td><td class="status-good">Active','Manage Watch State Layout')) {
    if ($content -notlike "*$needle*") {
        throw "Validation failed. Missing v2 contract marker: $needle"
    }
}

Write-Info 'Validation passed for v2 contract markers'
Write-Info ("Log file: {0}" -f $LogPath)
Write-Info 'Next: git add docs reports codex_prompts'
Write-Info 'Next: git commit -m "expand master contract v2 from archived requirements"'
