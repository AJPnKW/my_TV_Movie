# FILE: scripts/apply_contract_recovery_v2_overlay.ps1
# VERSION: 1.0.0
# UPDATED: 2026-05-09
$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path $repo 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "apply_contract_recovery_v2_overlay_$stamp.log.txt"
function Log([string]$m){ $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $m"; Write-Host $line; Add-Content -LiteralPath $log -Value $line -Encoding UTF8 }
$overlay = Join-Path $repo 'overlay_contract_recovery_v2'
if (-not (Test-Path -LiteralPath (Join-Path $overlay 'docs\00_master_contract.html'))) { throw "Overlay files not found at $overlay" }
$archive = Join-Path $repo "docs\_archive\contracts\00_master_contract_pre_recovery_v2_$stamp.html"
New-Item -ItemType Directory -Force -Path (Split-Path $archive -Parent) | Out-Null
if (Test-Path -LiteralPath (Join-Path $repo 'docs\00_master_contract.html')) { Copy-Item -LiteralPath (Join-Path $repo 'docs\00_master_contract.html') -Destination $archive -Force; Log "ARCHIVED $archive" }
Copy-Item -LiteralPath (Join-Path $overlay 'docs\00_master_contract.html') -Destination (Join-Path $repo 'docs\00_master_contract.html') -Force
Copy-Item -LiteralPath (Join-Path $overlay 'docs\_archive\contracts\README_contract_archive_policy_20260509.html') -Destination (Join-Path $repo 'docs\_archive\contracts\README_contract_archive_policy_20260509.html') -Force
New-Item -ItemType Directory -Force -Path (Join-Path $repo 'codex_prompts') | Out-Null
Copy-Item -LiteralPath (Join-Path $overlay 'codex_prompts\RECOVER_WATCH_POPUP_MEDIA_LIBRARY_MEDIA_QA_V2.txt') -Destination (Join-Path $repo 'codex_prompts\RECOVER_WATCH_POPUP_MEDIA_LIBRARY_MEDIA_QA_V2.txt') -Force
$content = Get-Content -LiteralPath (Join-Path $repo 'docs\00_master_contract.html') -Raw -Encoding UTF8
$required = @('MC-2026-05-09.2','Watch Source Popup Contract','Media Library Page','Media File QA and Repair Pipeline','Runtime Profile / Trailer Light Mode','provider_popup_guard.js must not rebuild')
foreach($r in $required){ if($content -notlike "*$r*"){ throw "Validation failed: missing $r" } }
Log 'VALIDATION PASSED'
Log "LOG_FILE $log"
Log 'NEXT: git add docs codex_prompts logs'
Log 'NEXT: git commit -m "recover contract popup media library media qa v2"'
Log 'NEXT: git push origin main'
