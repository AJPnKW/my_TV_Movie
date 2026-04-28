Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')
Set-Location -LiteralPath $RepoRoot.Path

$errors = New-Object System.Collections.Generic.List[string]

function Add-CheckError {
    param([Parameter(Mandatory)][string]$Message)
    $errors.Add($Message) | Out-Null
}

function Test-CommandAvailable {
    param([Parameter(Mandatory)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host '== Git state =='
git status --short --branch

$requiredFiles = @(
    'docs/ARCHITECTURE.md',
    'docs/AI_AGENT_RULES.md',
    'docs/UI_COMPONENTS.md',
    'docs/DOCUMENTATION_STANDARD.md',
    'docs/UI_GAP_ANALYSIS.md',
    'docs/ARCHITECTURE_LOG.md',
    'data/inputs.json',
    'data/data.json',
    'data/catalog_index.json',
    'data/calendar.json',
    'data/watch_sources_index.json',
    'web/index.html',
    'web/calendar.html',
    'web/shows.html',
    'web/movies.html',
    'web/watch_me.html',
    'web/discover.html',
    'web/config.html',
    'web/inputs_editor.html',
    'web/js/action_bar.js',
    'web/js/watch_state_manager.js',
    'web/js/data_loader.js',
    'web/js/trailer_watch_popup_fix.js',
    'web/js/runtime_render_fix.js',
    'web/js/ui_contract_fix.js',
    'web/css/runtime_layout_fix.css',
    'web/css/ui_contract_fix.css',
    'run_local_servers.bat',
    'run_server.bat',
    'run_schema.bat',
    'scripts/generate_schema.py',
    'tools/run_local_servers.bat',
    'tools/start_inputs_editor.cmd',
    'tools/run_smoke_test.ps1',
    'tools/inputs_editor/inputs_editor_server.py',
    'reports/ui_stabilization/asset_optimization.json',
    'reports/ui_stabilization/repo_cleanup_decisions.md',
    'reports/ui_stabilization/ui_stabilization_report.md',
    'reports/ui_stabilization/visual_gap_analysis.md'
)

Write-Host '== Required files =='
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path)) {
        Add-CheckError "Missing required file: $path"
    }
}

Write-Host '== Page shell references =='
$pageFiles = @('web/index.html','web/calendar.html','web/shows.html','web/movies.html','web/watch_me.html','web/discover.html','web/config.html')
foreach ($page in $pageFiles) {
    if (-not (Test-Path -LiteralPath $page)) { continue }
    $text = Get-Content -Raw -LiteralPath $page
    foreach ($needle in @('./js/chrometv_focus.js','./js/app_runtime.js','./css/main_app.css')) {
        if ($text -notlike "*$needle*") {
            Add-CheckError "$page missing shell reference: $needle"
        }
    }
}

Write-Host '== Local launcher contract =='
$rootLauncher = Get-Content -Raw -LiteralPath 'run_server.bat'
$canonicalLauncher = Get-Content -Raw -LiteralPath 'run_local_servers.bat'
$toolsLauncher = Get-Content -Raw -LiteralPath 'tools/run_local_servers.bat'
$editorLauncher = Get-Content -Raw -LiteralPath 'tools/start_inputs_editor.cmd'
$smokeLauncher = Get-Content -Raw -LiteralPath 'tools/run_smoke_test.ps1'
if ($canonicalLauncher -notlike '*tools\run_smoke_test.ps1*') {
    Add-CheckError 'run_local_servers.bat must call tools/run_smoke_test.ps1.'
}
if ($rootLauncher -notlike '*run_local_servers.bat*') {
    Add-CheckError 'run_server.bat must delegate to run_local_servers.bat.'
}
if ($rootLauncher -match 'app\.py|8811|fetch_tmdb\.py|pip install') {
    Add-CheckError 'run_server.bat still contains obsolete app.py/bootstrap launch logic.'
}
if ($toolsLauncher -notlike '*run_local_servers.bat*') {
    Add-CheckError 'tools/run_local_servers.bat must delegate to root run_local_servers.bat.'
}
if ($editorLauncher -notlike '*run_local_servers.bat*') {
    Add-CheckError 'tools/start_inputs_editor.cmd must delegate to root run_local_servers.bat.'
}
if (Test-Path -LiteralPath 'tools/start_inputs_editor.ps1') {
    Add-CheckError 'tools/start_inputs_editor.ps1 should not return as a separate editor-only launcher.'
}
if (Test-Path -LiteralPath 'docs.zip') { Add-CheckError 'Root docs.zip should not be tracked or restored.' }
if (Test-Path -LiteralPath 'docs (2).zip') { Add-CheckError 'Root docs (2).zip should not be tracked or restored.' }
if (Test-Path -LiteralPath 'reports.zip') { Add-CheckError 'Root reports.zip should not be tracked or restored.' }
foreach ($needle in @(
    '$staticPort = 8000',
    '$inputsPort = 8787',
    'tools\inputs_editor\inputs_editor_server.py',
    '/api/health',
    'web/watch_me.html',
    'web/discover.html',
    'web/inputs_editor.html'
)) {
    if ($smokeLauncher -notlike "*$needle*") { Add-CheckError "Local launcher missing contract: $needle" }
}

$schemaLauncher = Get-Content -Raw -LiteralPath 'run_schema.bat'
if ($schemaLauncher -notlike '*scripts\generate_schema.py*' -or $schemaLauncher -notlike '*--no-pause*') {
    Add-CheckError 'run_schema.bat must run scripts/generate_schema.py and support --no-pause validation.'
}

Write-Host '== JS syntax =='
if (-not (Test-CommandAvailable node)) {
    Add-CheckError 'node is not available for JS syntax checks'
} else {
    Get-ChildItem -LiteralPath 'web/js' -Filter '*.js' | ForEach-Object {
        & node --check $_.FullName | Out-Null
        if ($LASTEXITCODE -ne 0) { Add-CheckError "JS syntax failed: $($_.FullName)" }
    }
}

Write-Host '== Python syntax =='
if (-not (Test-CommandAvailable python)) {
    Add-CheckError 'python is not available for Python syntax checks'
} else {
    & python -m py_compile scripts/build_split_runtime.py scripts/optimize_runtime_assets.py scripts/generate_schema.py
    if ($LASTEXITCODE -ne 0) { Add-CheckError 'Python syntax failed' }
}

Write-Host '== JSON parse =='
$jsonFiles = @(Get-ChildItem -LiteralPath 'data' -Filter '*.json' -File | ForEach-Object { $_.FullName })
$jsonFiles += (Resolve-Path -LiteralPath 'web/config.json').Path
foreach ($jsonFile in $jsonFiles) {
    try {
        Get-Content -Raw -LiteralPath $jsonFile | ConvertFrom-Json | Out-Null
    } catch {
        Add-CheckError "JSON parse failed: $jsonFile"
    }
}

Write-Host '== Forbidden drift markers =='
$scanFiles = @(
    'web/js/action_bar.js',
    'web/js/app_runtime.js',
    'web/js/chrometv_focus.js',
    'web/js/data_loader.js',
    'web/js/runtime_render_fix.js',
    'web/js/trailer_watch_popup_fix.js',
    'web/js/ui_contract_fix.js',
    'web/js/watch_state_manager.js',
    'web/css/main_app.css',
    'web/css/runtime_layout_fix.css',
    'web/css/ui_contract_fix.css',
    'docs/ARCHITECTURE.md',
    'docs/UI_COMPONENTS.md',
    'docs/DOCUMENTATION_STANDARD.md',
    'docs/README.md',
    'docs/movie_card.md',
    'docs/episode_card.md',
    'docs/show_card.md',
    'docs/movie_popup.md'
)
$forbidden = @(
    '▶',
    '📏',
    '🔖',
    '💛',
    '⭐',
    '76%',
    '.slice(0,3)',
    '<<<<<<<',
    '>>>>>>>',
    'TODO placeholder',
    'Apply overlay',
    'ui_fix_patch',
    'fix_images.js',
    'bookmark as current watch_list icon'
)
foreach ($file in $scanFiles) {
    if (-not (Test-Path -LiteralPath $file)) { continue }
    $text = Get-Content -Raw -LiteralPath $file
    foreach ($needle in $forbidden) {
        if ($text.Contains($needle)) {
            Add-CheckError "Forbidden marker '$needle' found in $file"
        }
    }
}

Write-Host '== Placeholder and overlay artifacts =='
$driftPaths = @(
    'overlay',
    'overlay_patch',
    'overlay_ui_contract',
    'README_APPLY.md',
    'README_overlay_apply.txt'
)
foreach ($path in $driftPaths) {
    if (Test-Path -LiteralPath $path) { Add-CheckError "Obsolete drift artifact still exists: $path" }
}
$badNames = & git ls-files |
    Where-Object {
        $_ -notmatch '^docs/_archive/' -and
        $_ -match '(?i)(placeholder|apply_overlay|overlay_patch|ui_fix_patch|fix_images\.js)'
    }
foreach ($path in $badNames) {
    Add-CheckError "Forbidden placeholder/overlay file name: $path"
}

Write-Host '== Icon contract =='
$actionText = Get-Content -Raw -LiteralPath 'web/js/action_bar.js'
foreach ($needle in @(
    "watch_source: '🍿'",
    "watched_status: '⌚'",
    "watch_list: '🎫'",
    "favourite: '💕'",
    "ACTION_BAR_ORDER = Object.freeze"
)) {
    if ($actionText -notlike "*$needle*") { Add-CheckError "Action icon contract missing: $needle" }
}
if ($actionText -match "rating:\s*'[^']+'") {
    Add-CheckError 'Rating icon must stay empty; rating renders as compact text.'
}

Write-Host '== Duplicate action/popup handlers =='
$appRuntimeText = Get-Content -Raw -LiteralPath 'web/js/app_runtime.js'
$popupShimText = Get-Content -Raw -LiteralPath 'web/js/trailer_watch_popup_fix.js'
if ($popupShimText -notlike '*__myTvHubTrailerWatchPopupFixLoaded*') {
    Add-CheckError 'Popup shim does not expose loaded guard.'
}
if ($appRuntimeText -like '*function wireWatchSourceButtons*' -and $appRuntimeText -notlike '*if (window.__myTvHubTrailerWatchPopupFixLoaded) return;*') {
    Add-CheckError 'app_runtime watch-source fallback is not guarded by trailer_watch_popup_fix.'
}
$activeActionOwners = @('web/js/action_bar.js')
foreach ($jsFile in Get-ChildItem -LiteralPath 'web/js' -Filter '*.js' -File) {
    $text = Get-Content -Raw -LiteralPath $jsFile.FullName
    if ($jsFile.Name -ne 'action_bar.js' -and $text -match 'CONTRACT_ICONS\s*=|ACTION_BAR_ORDER\s*=|function\s+renderActionBarHtml|export\s+function\s+renderActionBarHtml') {
        Add-CheckError "Duplicate action/icon owner detected: web/js/$($jsFile.Name)"
    }
}

Write-Host '== Documentation source-of-truth consistency =='
$docStandard = Get-Content -Raw -LiteralPath 'docs/DOCUMENTATION_STANDARD.md'
foreach ($needle in @(
    'web/js/action_bar.js',
    'web/js/watch_state_manager.js',
    'web/js/trailer_watch_popup_fix.js',
    'web/js/data_loader.js',
    'web/css/main_app.css',
    'scripts/validate_runtime.ps1',
    'popcorn, watch, ticket, double-heart, compact numeric rating'
)) {
    if ($docStandard -notlike "*$needle*") { Add-CheckError "Documentation standard missing source-of-truth entry: $needle" }
}
$currentDocs = @('docs/ARCHITECTURE.md','docs/UI_COMPONENTS.md','docs/DOCUMENTATION_STANDARD.md','docs/README.md')
foreach ($doc in $currentDocs) {
    $text = Get-Content -Raw -LiteralPath $doc
    if ($text -match '🔖|💛|⭐|▶|76%') {
        Add-CheckError "Current source-of-truth doc contains deprecated icon marker: $doc"
    }
}

Write-Host '== Runtime asset size report =='
if (Test-CommandAvailable python) {
    $assetCheck = @'
import json
from pathlib import Path
try:
    from PIL import Image
except Exception:
    print("PIL unavailable; skipping dimension report")
    raise SystemExit(0)
targets = {
    "assets/posters": 420,
    "assets/stills": 900,
    "assets/backdrops": 900,
}
oversized = []
for folder, max_width in targets.items():
    root = Path(folder)
    if not root.exists():
        continue
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        try:
            with Image.open(path) as img:
                width, height = img.size
        except Exception:
            continue
        if width > max_width:
            oversized.append({"path": str(path).replace("\\", "/"), "width": width, "height": height, "target_max_width": max_width})
print(json.dumps({"oversized_runtime_assets": oversized[:25], "count": len(oversized)}, indent=2))
'@
    $assetOutput = $assetCheck | & python
    Write-Host $assetOutput
    if ($LASTEXITCODE -ne 0) { Add-CheckError 'Runtime asset size report failed' }
}

Write-Host '== Loader contract =='
$focusText = Get-Content -Raw -LiteralPath 'web/js/chrometv_focus.js'
foreach ($needle in @(
    "loadCss('./css/runtime_layout_fix.css');",
    "loadCss('./css/ui_contract_fix.css');",
    "loadScript('./js/watch_state_manager.js');",
    "loadScript('./js/runtime_render_fix.js');",
    "loadScript('./js/trailer_watch_popup_fix.js');",
    "loadScript('./js/ui_contract_fix.js');"
)) {
    if ($focusText -notlike "*$needle*") { Add-CheckError "Missing focus bootstrap loader: $needle" }
}

if ($errors.Count -gt 0) {
    Write-Host ''
    Write-Host 'VALIDATION FAILED'
    foreach ($err in $errors) { Write-Host "ERROR: $err" }
    exit 1
}

Write-Host ''
Write-Host 'VALIDATION PASSED'
exit 0
