# FILE: scripts/apply_contract_popup_recovery_overlay.ps1
# VERSION: v1.0.0
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path ".").Path
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "apply_contract_popup_recovery_overlay_$stamp.log.txt"
function Log($msg) { $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg; Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8; Write-Host $line }
Log "START contract popup recovery overlay"
$sourceContract = Join-Path $repoRoot "overlay_contract_popup_recovery\docs\00_master_contract.html"
if (-not (Test-Path -LiteralPath $sourceContract)) { throw "Missing overlay contract: $sourceContract" }
$activeContract = Join-Path $repoRoot "docs\00_master_contract.html"
$archiveDir = Join-Path $repoRoot "docs\_archive\contracts"
New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null
if (Test-Path -LiteralPath $activeContract) {
    $archivePath = Join-Path $archiveDir "00_master_contract_pre_popup_recovery_$stamp.html"
    Copy-Item -LiteralPath $activeContract -Destination $archivePath -Force
    Log "ARCHIVED $archivePath"
}
Copy-Item -LiteralPath $sourceContract -Destination $activeContract -Force
Log "INSTALLED docs\00_master_contract.html"
$archivePolicySrc = Join-Path $repoRoot "overlay_contract_popup_recovery\docs\_archive\contracts\README_contract_archive_policy_20260509.html"
if (Test-Path -LiteralPath $archivePolicySrc) { Copy-Item -LiteralPath $archivePolicySrc -Destination (Join-Path $archiveDir "README_contract_archive_policy_20260509.html") -Force; Log "INSTALLED archive policy" }
$promptSrc = Join-Path $repoRoot "overlay_contract_popup_recovery\codex_prompts\RECOVER_WATCH_POPUP_MEDIA_LIBRARY_MEDIA_QA.txt"
$promptDstDir = Join-Path $repoRoot "codex_prompts"
New-Item -ItemType Directory -Force -Path $promptDstDir | Out-Null
Copy-Item -LiteralPath $promptSrc -Destination (Join-Path $promptDstDir "RECOVER_WATCH_POPUP_MEDIA_LIBRARY_MEDIA_QA.txt") -Force
Log "INSTALLED codex prompt"
$content = Get-Content -LiteralPath $activeContract -Raw -Encoding UTF8
$required = @("Watch Source Popup Contract", "provider_popup_guard.js Rule", "Streaming Provider Lifecycle", "Runtime Profile / Trailer Light Mode", "Media File QA / Cleanup Pipeline", "Media Library Page", "Repository Inventory and Runtime Ownership Map", "Version History", "Section lineage")
foreach ($needle in $required) { if ($content -notlike "*$needle*") { throw "VALIDATION FAILED missing contract text: $needle" } }
Log "VALIDATION PASSED"
Log "NEXT: git add docs codex_prompts"
Log "NEXT: git commit -m 'recover master contract popup media library and media qa details'"
Log "NEXT: git push origin main"
Log "END contract popup recovery overlay"
