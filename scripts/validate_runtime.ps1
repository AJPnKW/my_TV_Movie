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

function ConvertTo-RepoRelativePath {
    param([Parameter(Mandatory)][string]$Path)
    $root = $RepoRoot.Path.TrimEnd('\', '/')
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($root.Length).TrimStart('\', '/').Replace('\','/')
    }
    return $full.Replace('\','/')
}

Write-Host '== Git state =='
git status --short --branch

$requiredFiles = @(
    'docs/00_master_contract.html',
    'docs/index.html',
    'docs/ARCHITECTURE_LOG.md',
    'data/inputs.json',
    'data/data.json',
    'data/catalog_index.json',
    'data/calendar.json',
    'data/discover_registry.json',
    'data/watch_sources_index.json',
    'web/index.html',
    'web/calendar.html',
    'web/shows.html',
    'web/movies.html',
    'web/watch_me.html',
    'web/manage_watch_state.html',
    'web/discover.html',
    'web/config.html',
    'web/inputs_editor.html',
    'assets/custom/the_boys_hub_logo2.png',
    'web/js/action_bar.js',
    'web/js/watch_state_manager.js',
    'web/js/data_loader.js',
    'web/js/trailer_watch_popup_fix.js',
    'web/js/runtime_render_fix.js',
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
$pageFiles = @('web/index.html','web/calendar.html','web/shows.html','web/movies.html','web/watch_me.html','web/discover.html','web/config.html','web/manage_watch_state.html')
foreach ($page in $pageFiles) {
    if (-not (Test-Path -LiteralPath $page)) { continue }
    $text = Get-Content -Raw -LiteralPath $page
    foreach ($needle in @('./js/chrometv_focus.js','./js/app_runtime.js','./css/main_app.css')) {
        if ($text -notlike "*$needle*") {
            Add-CheckError "$page missing shell reference: $needle"
        }
    }
    if ($text -like '*./css/my_tv_hub.css*') {
        Add-CheckError "$page must not load legacy my_tv_hub.css; main_app.css is the sole active UI authority."
    }
    foreach ($legacy in @('runtime_layout_fix.css','ui_contract_fix.css','ui_contract_fix.js')) {
        if ($text -like "*$legacy*") { Add-CheckError "$page still references removed compatibility layer: $legacy" }
    }
    $navMatch = [regex]::Match($text, '(?s)<div class="nav" role="tablist" aria-label="Primary">(?<nav>.*?)</div>')
    if (-not $navMatch.Success) {
        Add-CheckError "$page missing primary nav shell"
    } else {
        $navText = $navMatch.Groups['nav'].Value
        if ($navText -match 'data-tab="watch-me"') {
            Add-CheckError "$page primary nav must not expose Watch Me"
        }
        if ($navText -match '>Dashboard<|>Shows<|>Movies<|>Calendar<|>Watch Me<|>Discover<|>Config<|>Inputs Editor<') {
            Add-CheckError "$page primary nav must be icon-only visible text"
        }
        foreach ($requiredNav in @('Dashboard','Shows','Movies','Calendar','Discover','Tracking','Config','Inputs Editor')) {
            if ($navText -notmatch "aria-label=`"$requiredNav`"") {
                Add-CheckError "$page icon-only nav missing required accessible label: $requiredNav"
            }
        }
        foreach ($requiredTab in @('data-tab="dashboard"','data-tab="shows"','data-tab="movies"','data-tab="calendar"','data-tab="discover"','data-tab="manage-watch-state"','data-tab="config"','data-tab="inputs-editor"')) {
            if ($navText -notlike "*$requiredTab*") {
                Add-CheckError "$page icon-only nav missing required primary tab: $requiredTab"
            }
        }
        if ($navText -notmatch '🏠' -or $navText -notmatch '📺' -or $navText -notmatch '🎞️' -or $navText -notmatch '📅' -or $navText -notmatch '🔎' -or $navText -notmatch '✅') {
            Add-CheckError "$page icon-only nav missing required accessible labels"
        }
    }
    if ($text -notlike '*../assets/custom/the_boys_hub_logo2.png*') {
        Add-CheckError "$page missing compact logo shell reference"
    }
}
if (Test-Path -LiteralPath 'web/config_trakt.html') {
    Add-CheckError 'web/config_trakt.html must remain archived; Config and Manage Watch State own active config/watch-state surfaces.'
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
$trackedZipFiles = & git ls-files '*.zip'
foreach ($path in $trackedZipFiles) {
    Add-CheckError "Zip artifact must not be tracked: $path"
}
$zipFiles = Get-ChildItem -LiteralPath $RepoRoot.Path -Recurse -File -Filter '*.zip' -Force |
    Where-Object { $_.FullName -notmatch '\\.git\\' } |
    ForEach-Object { ConvertTo-RepoRelativePath $_.FullName }
foreach ($path in $zipFiles) {
    Add-CheckError "Zip artifact must be cleaned up: $path"
}
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
    'web/js/watch_state_manager.js',
    'web/css/main_app.css'
)
$forbidden = @(
    '▶',
    '📏',
    '🔖',
    '💛',
    '⭐',
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
if ($actionText -like "*watch_list: '🎟️'*") {
    Add-CheckError 'Action bar must use the master-contract watch_list icon.'
}
if ($actionText -notmatch "WATCHED_STATUS_VALUES[\s\S]*'unwatched'[\s\S]*'partial'[\s\S]*'watched'") {
    Add-CheckError 'action_bar.js must expose watched_status tri-state values: unwatched, partial, watched.'
}
foreach ($needle in @(
    'normalizeRatingText'
)) {
    if ($actionText -notlike "*$needle*") { Add-CheckError "Action rating percent contract missing: $needle" }
}
if ($actionText -notmatch '\$\{numeric\}%') {
    Add-CheckError 'Action rating formatter must append a percent sign to compact ratings.'
}

Write-Host '== Card/action layout contract =='
$cardRendererText = Get-Content -Raw -LiteralPath 'web/js/card_renderer.js'
$appRuntimeText = Get-Content -Raw -LiteralPath 'web/js/app_runtime.js'
$popupControllerText = Get-Content -Raw -LiteralPath 'web/js/popup_controller.js'
$mainCssText = Get-Content -Raw -LiteralPath 'web/css/main_app.css'
$runtimeText = Get-Content -Raw -LiteralPath 'web/js/runtime_render_fix.js'
foreach ($legacy in @('web/css/runtime_layout_fix.css','web/css/ui_contract_fix.css','web/js/ui_contract_fix.js')) {
    if (Test-Path -LiteralPath $legacy) { Add-CheckError "Removed compatibility layer returned to active repo: $legacy" }
}
if ($cardRendererText -match 'media-card__surface-badge') {
    Add-CheckError 'card_renderer.js must not render media-card__surface-badge overlays.'
}
if ($appRuntimeText -match 'badgeHtml:\s*availabilityBadgeHtml') {
    Add-CheckError 'app_runtime card render paths must not pass availability badges into cards.'
}
if ($mainCssText -match 'overflow(?:-[xy])?\s*:\s*clip') {
    Add-CheckError 'Action/card CSS must not use overflow: clip.'
}
if ($mainCssText -notmatch '--ui_action_box:\s*clamp') {
    Add-CheckError 'main_app.css must define adaptive action box sizing.'
}
foreach ($needle in @('--contract-poster-w:171px','--contract-poster-h:257px','--contract-still-w:240px','--contract-still-h:135px')) {
    if ($mainCssText -notlike "*$needle*") { Add-CheckError "main_app.css missing media size contract: $needle" }
}
if ($cardRendererText -notlike '*data-media-shape*' -or $cardRendererText -notlike '*data-contract-size*') {
    Add-CheckError 'card_renderer.js must stamp rendered media cards with media-shape and contract-size metadata.'
}
if ($popupControllerText -notlike '*renderMediaDetailBlockHtml*' -or $popupControllerText -notlike '*popup-media-detail*') {
    Add-CheckError 'popup_controller.js must own the unified popup media detail block.'
}
if ($appRuntimeText -notlike '*renderPopupMediaDetailBlock*' -or $appRuntimeText -notlike '*renderMediaDetailBlockHtml*') {
    Add-CheckError 'app_runtime.js must render the popup media detail block before provider groups.'
}
if ($mainCssText -notlike '*Consolidated documentation-contract shell, card, action, and watch-state management rules*') {
    Add-CheckError 'main_app.css must own the finalized card/action/header contract rules.'
}
if ($mainCssText -match '\.logo_txt') {
    Add-CheckError 'main_app.css must not keep the retired .logo_txt implementation.'
}
if ($mainCssText -match '(?s)\.actionbar-btn\s*\{[^}]*border-radius\s*:\s*999px') {
    Add-CheckError 'Action buttons must not use legacy circle/pill border radius.'
}
if ($mainCssText -match '(?s)\.actionbar\s*\{[^}]*border\s*:\s*1px') {
    Add-CheckError 'Action row must not render a framed container.'
}
if (($mainCssText | Select-String -Pattern '(?m)^\s*\.actionbar\s*\{' -AllMatches).Matches.Count -ne 1) {
    Add-CheckError 'main_app.css must expose one canonical .actionbar rule.'
}
if (($mainCssText | Select-String -Pattern '(?m)^\s*\.actionbar-btn\s*\{' -AllMatches).Matches.Count -ne 1) {
    Add-CheckError 'main_app.css must expose one canonical .actionbar-btn rule.'
}
if ($mainCssText -match '(?s)\.tab\s*\{[^}]*border\s*:\s*1px') {
    Add-CheckError 'Primary nav tabs must not keep button borders.'
}
if ($runtimeText -match 'replace\(/%/g') {
    Add-CheckError 'Runtime shims must not strip percent signs from compact ratings.'
}
if ($appRuntimeText -notlike '*panel-manage-watch-state*' -or $appRuntimeText -notlike '*id="manageWatchState"*' -or $appRuntimeText -notlike '*watch-state-matrix*' -or $appRuntimeText -notlike '*data-manage-watch-key*' -or $appRuntimeText -notlike '*data-manage-watch-value*') {
    Add-CheckError 'Manage Watch State must be a standalone reachable view with local toggles.'
}
if ($appRuntimeText -match 'watch-state-manager__item|watch-state-manager__grid') {
    Add-CheckError 'Manage Watch State must render a matrix/tree, not card/grid UI.'
}
$configRenderMatch = [regex]::Match($appRuntimeText, '(?s)async function renderConfig\(\).*?function buildMoviePopupHtml')
if ($configRenderMatch.Success -and $configRenderMatch.Value -match 'manageWatchState|data-manage-watch-key|Trakt mapping') {
    Add-CheckError 'Config must remain app-settings only and must not render Manage Watch State content.'
}

Write-Host '== Watch-state key contract =='
$watchStateText = Get-Content -Raw -LiteralPath 'web/js/watch_state_manager.js'
foreach ($needle in @(
    '${cleanType}:episode:${showId}:${season}:${episode}',
    '${cleanType}:movie:${id}',
    '${cleanType}:show:'
)) {
    if ($watchStateText -notlike "*$needle*") { Add-CheckError "Watch-state key pattern missing: $needle" }
}
if ($watchStateText -match 'return keyFor\(cleanType,id\)') {
    Add-CheckError 'watch_state_manager.js must not fall back to generic type:id keys.'
}
foreach ($needle in @(
    'mytv_watch_sync_queue_v1',
    "'local_only','queued','synced','mismatch','missing_id','validation_issue','auth_required','failed'",
    'WATCHED_VALUES',
    'previous_value',
    'new_value',
    'changed_at',
    'sync_status',
    'validation_status',
    'sync_error',
    'unreleased movie/episode cannot become watched'
)) {
    if ($watchStateText -notlike "*$needle*") { Add-CheckError "watch_state_manager.js missing local-first Trakt/watch-state contract: $needle" }
}
if ($watchStateText -match '(?i)title\s*===|title-only') {
    Add-CheckError 'watch_state_manager.js must not implement title-only matching.'
}
foreach ($needle in @(
    'data-computed-status="trakt"',
    'data-computed-status="mismatch"',
    'data-computed-status="queued"',
    'computedValidationIssue',
    'traktAuthAvailable',
    'readWatchSyncQueue'
)) {
    if ($appRuntimeText -notlike "*$needle*") { Add-CheckError "app_runtime.js missing computed Manage Watch State contract: $needle" }
}
foreach ($needle in @(
    '--calendar-col-min:var(--contract-still-w)',
    '--calendar-grid-gap:10px',
    'repeat(7,minmax(var(--calendar-col-min),1fr))',
    'calc((var(--calendar-col-min) * 7) + (var(--calendar-grid-gap) * 6))'
)) {
    if ($mainCssText -notlike "*$needle*") { Add-CheckError "main_app.css missing shared calendar column contract: $needle" }
}

Write-Host '== Duplicate action/popup handlers =='
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
$masterContract = Get-Content -Raw -LiteralPath 'docs/00_master_contract.html'
foreach ($needle in @(
    'docs/00_master_contract.html',
    'MC-2026-04-30.4',
    'web/manage_watch_state.html',
    'web/discover.html',
    'web/watch_me.html',
    'Boys logo must preserve aspect ratio',
    '🍿 ⌚ 🎫 💕 76%',
    'Primary nav icons are standalone Unicode/web icons',
    'Standalone page: <code>web/manage_watch_state.html</code>',
    'Forbidden active icons'
)) {
    if ($masterContract -notlike "*$needle*") { Add-CheckError "Master contract missing source-of-truth entry: $needle" }
}
$docIndex = Get-Content -Raw -LiteralPath 'docs/index.html'
if ($docIndex -notlike '*00_master_contract.html*') {
    Add-CheckError 'docs/index.html must point to docs/00_master_contract.html.'
}
if ($masterContract -notlike '*Forbidden active icons*') {
    Add-CheckError 'Master contract must document forbidden card action icons.'
}
foreach ($needle in @(
    'requirements, user-provided examples, dimensions, visual targets, state names, and acceptance rules must not be simplified',
    'Abbott Elementary',
    'Team Building',
    'S05E01 • 22 min',
    'Oct 1, 2025',
    'The teachers prepare for the upcoming school year with new faces and big changes on the horizon.',
    'Header cell left/right bounds must align exactly',
    'Trakt status</code>, <code>Mismatch</code>, <code>Queued</code>, and <code>Validation issue</code> are computed',
    'unwatched → partial → watched → unwatched',
    'local queue event',
    'D-pad/Android TV validation',
    'poster Half <code>171x257</code>',
    'narrow still Half <code>240x135</code>',
    'episode source still <code>320x180</code>'
)) {
    if ($masterContract -notlike "*$needle*") { Add-CheckError "Master contract missing MC-2026-04-30.4 detailed rule/example: $needle" }
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
    "assets/posters": 171,
    "assets/stills": 256,
    "assets/backdrops": 780,
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
    try {
        $assetJson = $assetOutput | ConvertFrom-Json
        if ($assetJson.count -gt 0) { Add-CheckError "Oversized runtime assets remain: $($assetJson.count)" }
    } catch {
        Add-CheckError 'Runtime asset size report did not return JSON.'
    }
}

Write-Host '== Loader contract =='
$focusText = Get-Content -Raw -LiteralPath 'web/js/chrometv_focus.js'
foreach ($needle in @(
    "loadScript('./js/watch_state_manager.js');",
    "loadScript('./js/runtime_render_fix.js');",
    "loadScript('./js/trailer_watch_popup_fix.js');"
)) {
    if ($focusText -notlike "*$needle*") { Add-CheckError "Missing focus bootstrap loader: $needle" }
}
foreach ($needle in @('runtime_layout_fix.css','ui_contract_fix.css','ui_contract_fix.js')) {
    if ($focusText -like "*$needle*") { Add-CheckError "Focus bootstrap still loads removed compatibility layer: $needle" }
}

Write-Host '== Rendered nav/logo/watch-state contract =='
if ((Test-CommandAvailable node) -and (Test-CommandAvailable python)) {
    $chromeCandidates = @(
        'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    )
    $chromePath = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $chromePath) {
        Add-CheckError 'Rendered validation requires Chrome or Edge.'
    } elseif (-not (Test-Path -LiteralPath 'node_modules/puppeteer-core')) {
        Add-CheckError 'Rendered validation requires node_modules/puppeteer-core.'
    } else {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), 0)
        $listener.Start()
        $port = $listener.LocalEndpoint.Port
        $listener.Stop()
        $server = Start-Process -FilePath python -ArgumentList @('-m','http.server',"$port",'--bind','127.0.0.1') -WorkingDirectory $RepoRoot.Path -WindowStyle Hidden -PassThru
        try {
            Start-Sleep -Milliseconds 900
            $chromePathJson = $chromePath | ConvertTo-Json
            $renderScript = @"
const puppeteer = require('puppeteer-core');
const executablePath = $chromePathJson;
const base = 'http://127.0.0.1:$port/web/';
  const pages = ['index.html','shows.html','movies.html','calendar.html','discover.html','config.html','manage_watch_state.html','watch_me.html'];
  const viewports = [{name:'android_tv', width:1920, height:1080}, {name:'desktop', width:1366, height:768}, {name:'tablet', width:768, height:1024}, {name:'mobile', width:390, height:844}];
const failures = [];
function ignoreConsole(message){
  return /favicon|ERR_ABORTED|File not found|Config warning\(s\):/.test(message);
}
(async () => {
  const browser = await puppeteer.launch({ executablePath, headless:'new', args:['--no-sandbox','--disable-gpu'] });
  for (const viewport of viewports){
    for (const pageName of pages){
      const page = await browser.newPage();
      await page.setViewport({ width: viewport.width, height: viewport.height, deviceScaleFactor: 1 });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (['error','warning'].includes(message.type())) errors.push(message.text()); });
      await page.goto(base + pageName, { waitUntil:'domcontentloaded', timeout:15000 });
      await page.waitForSelector('.top .nav .tab', { timeout:10000 });
      await new Promise(resolve => setTimeout(resolve, 900));
      let providerDetailRendered = true;
      let providerDetailText = '';
      if (pageName === 'index.html'){
        const providerDetailSample = await page.evaluate(() => {
          const episode = window.MyTVHubSharedModules?.popupController?.renderMediaDetailBlockHtml?.({
            kind:'episode',
            primary:'Abbott Elementary',
            secondary:'Team Building',
            meta:'S05E01 • 22 min',
            date:'Oct 1, 2025',
            overview:'The teachers prepare for the upcoming school year with new faces and big changes on the horizon.'
          }) || '';
          const movie = window.MyTVHubSharedModules?.popupController?.renderMediaDetailBlockHtml?.({
            kind:'movie',
            primary:'Validation Movie',
            meta:'90 min • May 4, 2026',
            overview:'Validation overview'
          }) || '';
          return episode + movie;
        });
        providerDetailRendered = /popup-media-detail/.test(providerDetailSample) && /Abbott Elementary/.test(providerDetailSample) && /Team Building/.test(providerDetailSample) && /S05E01 • 22 min/.test(providerDetailSample) && /Oct 1, 2025/.test(providerDetailSample) && /The teachers prepare/.test(providerDetailSample);
        providerDetailText = providerDetailSample.replace(/<[^>]+>/g, '').trim();
      }
      const result = await page.evaluate(async () => {
        const rect = el => { const r = el.getBoundingClientRect(); return { top:r.top, bottom:r.bottom, left:r.left, right:r.right, width:r.width, height:r.height }; };
        const tabs = Array.from(document.querySelectorAll('.top .nav .tab')).map(tab => {
          const style = getComputedStyle(tab);
          return {
            id: tab.getAttribute('data-tab') || '',
            text: (tab.textContent || '').trim(),
            label: tab.getAttribute('aria-label') || '',
            borderTopWidth: parseFloat(style.borderTopWidth) || 0,
            borderLeftWidth: parseFloat(style.borderLeftWidth) || 0,
            borderRadius: parseFloat(style.borderTopLeftRadius) || 0
          };
        });
        const logo = document.querySelector('.logo img');
        const header = document.querySelector('.top');
        const logoRect = logo ? rect(logo) : null;
        const headerRect = header ? rect(header) : null;
        const headerStickyAncestors = [];
        if (header){
          let node = header.parentElement;
          while (node && node !== document.documentElement){
            const style = getComputedStyle(node);
            headerStickyAncestors.push({
              tag: node.tagName.toLowerCase(),
              id: node.id || '',
              cls: node.className || '',
              overflowX: style.overflowX,
              overflowY: style.overflowY,
              transform: style.transform,
              contain: style.contain
            });
            node = node.parentElement;
          }
        }
        const manage = document.querySelector('#manageWatchState');
        const manageTable = manage ? manage.querySelector('.watch-state-matrix') : null;
        const calendarGrid = document.querySelector('.calendar-month-grid');
        const calendarWeek = document.querySelector('.calendar-week-band');
        const calendarHost = document.querySelector('#calendar');
        const splitColumns = value => String(value || '').split(' ').filter(Boolean).length;
        const actionButtons = Array.from(document.querySelectorAll('.media-card .actionbar-btn')).slice(0, 12).map(btn => {
          const style = getComputedStyle(btn);
          const btnRect = rect(btn);
          const card = btn.closest('.media-card');
          const img = card ? card.querySelector('img') : null;
          const imgRect = img ? rect(img) : null;
          const icon = (btn.textContent || '').trim();
          return {
            icon,
            width: btnRect.width,
            height: btnRect.height,
            radius: parseFloat(style.borderTopLeftRadius) || 0,
            overflow: style.overflow,
            belowImage: !imgRect || btnRect.top >= imgRect.bottom - 2
          };
        });
        const dashHeads = Array.from(document.querySelectorAll('#panel-dashboard > .dash > .dashblock > .dashhead')).map(head => ({ text:(head.textContent || '').trim(), position:getComputedStyle(head).position }));
        const dashboardBlocks = Array.from(document.querySelectorAll('#panel-dashboard > .dash > .dashblock')).map(block => {
          const keys = Array.from(block.querySelectorAll('[data-render-key]')).map(card => card.getAttribute('data-render-key') || '').filter(Boolean);
          const duplicateKeys = Array.from(new Set(keys.filter((key, index) => keys.indexOf(key) !== index)));
          return { title:(block.querySelector('.dashhead h2')?.textContent || '').trim(), keyCount:keys.length, duplicateKeys };
        });
        const sectionHeads = Array.from(document.querySelectorAll('[data-sticky-section-head="1"]')).map(head => {
          const headRect = rect(head);
          const style = getComputedStyle(head);
          return { text:(head.textContent || '').trim(), position:style.position, top:style.top, rect:headRect };
        });
        const recommendationCards = Array.from(document.querySelectorAll('#dashShowRecs .media-card, #dashMovieRecs .media-card')).map(card => {
          const cardRect = rect(card);
          const poster = card.querySelector('.media-card__poster');
          const posterRect = poster ? rect(poster) : null;
          return { width:cardRect.width, height:cardRect.height, posterHeight:posterRect ? posterRect.height : 0 };
        });
        const headerPosition = header ? getComputedStyle(header).position : '';
        const navEntry = performance.getEntriesByType('navigation')[0];
        const perf = navEntry ? {
          domContentLoadedMs: Math.round(navEntry.domContentLoadedEventEnd),
          loadMs: Math.round(navEntry.loadEventEnd),
          responseEndMs: Math.round(navEntry.responseEnd)
        } : null;
        const canScroll = document.documentElement.scrollHeight > window.innerHeight + 100;
        if (canScroll) {
          window.scrollTo(0, Math.min(600, document.documentElement.scrollHeight - window.innerHeight));
          await new Promise(resolve => requestAnimationFrame(resolve));
        }
        const headerAfterScrollRect = header ? rect(header) : null;
        const posterCards = Array.from(document.querySelectorAll('.media-card[data-media-shape="poster"] .media-card__poster')).map(poster => {
          const posterRect = rect(poster);
          return { width:posterRect.width, height:posterRect.height, contract:poster.getAttribute('data-contract-size') || '' };
        });
        const stillCards = Array.from(document.querySelectorAll('.media-card[data-media-shape="still"] .media-card__poster')).map(poster => {
          const posterRect = rect(poster);
          return { width:posterRect.width, height:posterRect.height, contract:poster.getAttribute('data-contract-size') || '' };
        });
        const calendarEpisodeImages = Array.from(document.querySelectorAll('.calendar-item.media-card--episode img')).map(img => img.getAttribute('src') || '');
        const weekendDay = document.querySelector('.calendar-day--weekend');
        const weekdayDay = Array.from(document.querySelectorAll('.calendar-day')).find(day => !day.classList.contains('calendar-day--weekend'));
        const weekendBandDay = document.querySelector('.calendar-week-band__day.is-weekend');
        const firstWeekBand = document.querySelector('.calendar-week-band');
        const firstWeekHeaders = firstWeekBand ? Array.from(firstWeekBand.querySelectorAll('.calendar-week-band__day')).map(rect) : [];
        const firstWeekDays = Array.from(document.querySelectorAll('.calendar-month-grid > .calendar-day')).slice(0, 7).map(rect);
        const calendarAlignment = firstWeekHeaders.map((headerRect, index) => {
          const dayRect = firstWeekDays[index] || null;
          return dayRect ? { index, leftDelta: Math.abs(headerRect.left - dayRect.left), rightDelta: Math.abs(headerRect.right - dayRect.right), widthDelta: Math.abs(headerRect.width - dayRect.width) } : { index, missingDay: true };
        });
        const watchStatusValues = (document.documentElement.getAttribute('data-watched-status-values') || '').split(',').filter(Boolean);
        const watchStateBefore = JSON.parse(localStorage.getItem('mytv_watch_state_v1') || '{}');
        const queueBefore = JSON.parse(localStorage.getItem('mytv_watch_sync_queue_v1') || '[]');
        const watchButton = Array.from(document.querySelectorAll('[data-watch-state-action="toggle-watched-status"]')).find(btn => !/not_yet_released|unreleased/.test(btn.getAttribute('data-release-status') || btn.getAttribute('data-watch-availability') || '')) || document.querySelector('[data-watch-state-action="toggle-watched-status"]');
        if (watchButton) watchButton.click();
        await new Promise(resolve => requestAnimationFrame(resolve));
        const watchStateAfter = JSON.parse(localStorage.getItem('mytv_watch_state_v1') || '{}');
        const queueAfter = JSON.parse(localStorage.getItem('mytv_watch_sync_queue_v1') || '[]');
        const manageComputed = manage ? {
          trakt: Array.from(manage.querySelectorAll('[data-computed-status="trakt"]')).map(el => (el.textContent || '').trim()).filter(Boolean),
          mismatch: Array.from(manage.querySelectorAll('[data-computed-status="mismatch"]')).map(el => (el.textContent || '').trim()).filter(Boolean),
          queued: Array.from(manage.querySelectorAll('[data-computed-status="queued"]')).map(el => (el.textContent || '').trim()).filter(Boolean)
        } : null;
        const discoverCards = Array.from(document.querySelectorAll('#panel-discover .media-card')).map(card => ({
          kind: card.getAttribute('data-kind') || '',
          id: card.getAttribute('data-id') || card.getAttribute('data-show-open') || card.getAttribute('data-movie-open') || ''
        }));
        const discoverRegistryRows = document.querySelectorAll('#panel-discover .discover-registry__table tbody tr').length;
        const discoverEmptyState = !!document.querySelector('#panel-discover .discover-empty');
        return {
          tabs,
          logoRect,
          headerRect,
          headerStickyAncestors,
          logoNatural: logo ? { width:logo.naturalWidth, height:logo.naturalHeight } : null,
          hasManage: !!manage,
          manageButtonCount: manage ? manage.querySelectorAll('[data-manage-watch-key]').length : 0,
          manageHasTable: !!manageTable,
          manageCardCount: manage ? manage.querySelectorAll('.watch-state-manager__item, .media-card').length : 0,
          manageColumnCount: manageTable ? manageTable.querySelectorAll('thead th').length : 0,
          manageRowCount: manageTable ? manageTable.querySelectorAll('tbody tr').length : 0,
          watchListCount: document.querySelectorAll('.watchme-list-item').length,
          calendar: calendarGrid ? {
            gridColumns: splitColumns(getComputedStyle(calendarGrid).gridTemplateColumns),
            weekColumns: calendarWeek ? splitColumns(getComputedStyle(calendarWeek).gridTemplateColumns) : 0,
            weekDisplay: calendarWeek ? getComputedStyle(calendarWeek).display : '',
            hostClientWidth: calendarHost ? calendarHost.clientWidth : 0,
            hostScrollWidth: calendarHost ? calendarHost.scrollWidth : 0,
            duplicateCellDateCount: document.querySelectorAll('.calendar-day__date').length,
            weekBandDateCount: document.querySelectorAll('.calendar-week-band__date').length,
            weekendDayCount: document.querySelectorAll('.calendar-day--weekend').length,
            weekendBandDayCount: document.querySelectorAll('.calendar-week-band__day.is-weekend').length,
            weekendBackground: weekendDay ? getComputedStyle(weekendDay).backgroundColor : '',
            weekdayBackground: weekdayDay ? getComputedStyle(weekdayDay).backgroundColor : '',
            weekendBandBackground: weekendBandDay ? getComputedStyle(weekendBandDay).backgroundColor : '',
            episodeImageSrcs: calendarEpisodeImages,
            alignment: calendarAlignment
          } : null,
          watchStateAction: {
            hasWatchButton: !!watchButton,
            watchedValues: watchStatusValues,
            beforeKeys: Object.keys(watchStateBefore).length,
            afterKeys: Object.keys(watchStateAfter).length,
            queueBefore: Array.isArray(queueBefore) ? queueBefore.length : 0,
            queueAfter: Array.isArray(queueAfter) ? queueAfter.length : 0,
            hasQueuedRecord: Array.isArray(queueAfter) && queueAfter.some(item => item && item.sync_status === 'queued' && item.item_key && item.previous_value != null && item.new_value != null)
          },
          manageComputed,
          actionButtons,
          dashHeads,
          sectionHeads,
          dashboardBlocks,
          recommendationCards,
          posterCards,
          stillCards,
          headerPosition,
          headerAfterScrollRect,
          canScroll,
          perf,
          discoverCards,
          discoverRegistryRows,
          discoverEmptyState
        };
      });
      result.providerDetailRendered = providerDetailRendered;
      result.providerDetailText = providerDetailText;
      const visibleTextLabels = new Set(['Dashboard','Shows','Movies','Calendar','Watch Me','Discover','Config','Inputs Editor','Manage Watch State']);
      const badText = result.tabs.filter(tab => visibleTextLabels.has(tab.text));
      const framedTabs = result.tabs.filter(tab => tab.borderTopWidth > 0 || tab.borderLeftWidth > 0 || tab.borderRadius > 2);
      const missingLabels = result.tabs.filter(tab => !tab.label);
      const requiredTabs = ['dashboard','shows','movies','calendar','discover','manage-watch-state','config','inputs-editor'];
      const missingRequiredTabs = requiredTabs.filter(id => !result.tabs.some(tab => tab.id === id));
      const logoRatio = result.logoRect && result.logoRect.height ? result.logoRect.width / result.logoRect.height : 99;
      const logoBad = !result.logoRect || !result.logoNatural || result.logoNatural.width !== result.logoNatural.height || logoRatio > 1.25 || result.logoRect.width > 44 || result.logoRect.height > 44 || !result.headerRect || result.logoRect.top < result.headerRect.top - 1 || result.logoRect.bottom > result.headerRect.bottom + 1 || result.headerRect.height > 70;
      const manageBad = (pageName === 'config.html' && result.hasManage) || (pageName === 'manage_watch_state.html' && (!result.hasManage || !result.manageHasTable || result.manageCardCount > 0 || result.manageButtonCount < 1 || result.manageColumnCount < 10 || result.manageRowCount < 1));
      const watchBad = pageName === 'watch_me.html' && result.watchListCount < 1;
      const calendarBad = pageName === 'calendar.html' && (!result.calendar || result.calendar.gridColumns !== 7 || result.calendar.weekColumns !== 7 || result.calendar.weekDisplay === 'none' || (viewport.width < 924 && result.calendar.hostScrollWidth <= result.calendar.hostClientWidth));
      const calendarAlignmentBad = pageName === 'calendar.html' && (!result.calendar || !result.calendar.alignment || result.calendar.alignment.length !== 7 || result.calendar.alignment.some(pair => pair.missingDay || pair.leftDelta > 1 || pair.rightDelta > 1 || pair.widthDelta > 1));
      const calendarDuplicateDateBad = pageName === 'calendar.html' && (!result.calendar || result.calendar.duplicateCellDateCount !== 0 || result.calendar.weekBandDateCount < 7);
      const calendarWeekendBad = pageName === 'calendar.html' && (!result.calendar || result.calendar.weekendDayCount < 1 || result.calendar.weekendBandDayCount < 1 || result.calendar.weekendBackground === result.calendar.weekdayBackground);
      const calendarStillBad = pageName === 'calendar.html' && (!result.calendar || result.calendar.episodeImageSrcs.some(src => /poster/i.test(src)));
      const movieNavBad = result.tabs.some(tab => tab.id === 'movies' && tab.text === '🎬');
      const actionBad = result.actionButtons.some(btn => btn.icon === '🎟️' || btn.icon === '▶' || btn.icon === '🎬' || btn.icon === '📏' || btn.icon === '💛' || btn.icon === '⭐' || Math.abs(btn.width - btn.height) > 1 || btn.radius < 7 || btn.radius > 10 || btn.radius >= (btn.width / 2) || !btn.belowImage);
      const stickyBad = pageName === 'index.html' && (!result.dashHeads.some(h => /Current \/ Recent/.test(h.text) && h.position === 'sticky') || !result.dashHeads.some(h => /Watchlist/.test(h.text) && h.position === 'sticky') || !result.dashHeads.some(h => /Upcoming/.test(h.text) && h.position === 'sticky') || !result.dashHeads.some(h => /Recommendations/.test(h.text) && h.position === 'sticky'));
      const topNavBad = result.headerPosition !== 'sticky' || (result.canScroll && (!result.headerAfterScrollRect || Math.abs(result.headerAfterScrollRect.top) > 1));
      const stickyAncestorBad = result.headerStickyAncestors.some(node => /(hidden|auto|clip)/.test(String(node.overflowX || '') + ' ' + String(node.overflowY || '')) || (node.transform && node.transform !== 'none') || (node.contain && node.contain !== 'none'));
      const sectionStickyBad = ['index.html','shows.html','movies.html','discover.html'].includes(pageName) && (!result.sectionHeads.length || result.sectionHeads.some(head => head.position !== 'sticky' || !head.top || head.top === 'auto'));
      const dashboardDuplicateBad = pageName === 'index.html' && result.dashboardBlocks.some(block => block.duplicateKeys.length > 0);
      const recommendationBad = pageName === 'index.html' && result.recommendationCards.some(card => card.width > 230 || card.posterHeight > 360);
      const posterSizeBad = result.posterCards.some(card => card.width > 176 || card.height > 267 || card.contract !== '171x257');
      const stillSizeBad = result.stillCards.some(card => card.width > 245 || card.height > 140 || card.contract !== '240x135');
      const popupDetailBad = pageName === 'index.html' && (!result.providerDetailRendered || !result.providerDetailText);
      const watchStateActionBad = pageName === 'index.html' && (!result.watchStateAction || !result.watchStateAction.watchedValues.includes('partial') || !result.watchStateAction.hasWatchButton || !result.watchStateAction.hasQueuedRecord);
      const manageComputedBad = pageName === 'manage_watch_state.html' && (!result.manageComputed || !result.manageComputed.trakt.length || !result.manageComputed.mismatch.length || !result.manageComputed.queued.length || result.manageComputed.mismatch.some(value => !['true','false'].includes(value)) || result.manageComputed.queued.some(value => !['true','false'].includes(value)));
      const performanceBad = result.perf && (result.perf.loadMs > 10000 || result.perf.domContentLoadedMs > 8000);
      const discoverBad = pageName === 'discover.html' && (!result.discoverRegistryRows || !result.discoverEmptyState || result.discoverCards.length > 0);
      const pageErrors = errors.filter(error => !ignoreConsole(error));
      if (badText.length || framedTabs.length || missingLabels.length || missingRequiredTabs.length || movieNavBad || logoBad || manageBad || watchBad || calendarBad || calendarAlignmentBad || calendarDuplicateDateBad || calendarWeekendBad || calendarStillBad || actionBad || stickyBad || topNavBad || stickyAncestorBad || sectionStickyBad || dashboardDuplicateBad || recommendationBad || posterSizeBad || stillSizeBad || popupDetailBad || watchStateActionBad || manageComputedBad || performanceBad || discoverBad || pageErrors.length){
        failures.push({ viewport: viewport.name, page: pageName, badText, framedTabs, missingLabels, missingRequiredTabs, movieNavBad, logoRatio, logoRect: result.logoRect, headerRect: result.headerRect, headerPosition: result.headerPosition, headerAfterScrollRect: result.headerAfterScrollRect, headerStickyAncestors: result.headerStickyAncestors, canScroll: result.canScroll, manageButtonCount: result.manageButtonCount, manageHasTable: result.manageHasTable, manageCardCount: result.manageCardCount, manageColumnCount: result.manageColumnCount, manageRowCount: result.manageRowCount, watchListCount: result.watchListCount, calendar: result.calendar, actionButtons: result.actionButtons, dashHeads: result.dashHeads, sectionHeads: result.sectionHeads, dashboardBlocks: result.dashboardBlocks, recommendationCards: result.recommendationCards, posterCards: result.posterCards, stillCards: result.stillCards, providerDetailRendered: result.providerDetailRendered, providerDetailText: result.providerDetailText, watchStateAction: result.watchStateAction, manageComputed: result.manageComputed, perf: result.perf, discoverCards: result.discoverCards, discoverRegistryRows: result.discoverRegistryRows, discoverEmptyState: result.discoverEmptyState, errors: pageErrors });
      }
      await page.close();
    }
  }
  await browser.close();
  if (failures.length){
    console.log(JSON.stringify({ failures }, null, 2));
    process.exit(1);
  }
  console.log(JSON.stringify({ rendered_contract: 'passed', pages, viewports: viewports.map(v => v.name) }));
})().catch(error => { console.error(error); process.exit(1); });
"@
            $renderScriptPath = Join-Path $RepoRoot.Path '.tmp-rendered-contract-check.cjs'
            Set-Content -LiteralPath $renderScriptPath -Value $renderScript -NoNewline
            $renderOutput = & node $renderScriptPath 2>&1
            $renderExit = $LASTEXITCODE
            Remove-Item -LiteralPath $renderScriptPath -Force -ErrorAction SilentlyContinue
            Write-Host $renderOutput
            if ($renderExit -ne 0) {
                Add-CheckError "Rendered nav/logo/watch-state contract failed: $renderOutput"
            }
        } finally {
            if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
        }
    }
} else {
    Add-CheckError 'Rendered validation requires node and python.'
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
