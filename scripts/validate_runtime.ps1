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
    'docs/00_master_contract.html',
    'docs/index.html',
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
        foreach ($requiredNav in @('Dashboard','Shows','Movies','Calendar','Tracking','Config','Inputs Editor')) {
            if ($navText -notmatch "aria-label=`"$requiredNav`"") {
                Add-CheckError "$page icon-only nav missing required accessible label: $requiredNav"
            }
        }
        foreach ($requiredTab in @('data-tab="dashboard"','data-tab="shows"','data-tab="movies"','data-tab="calendar"','data-tab="manage-watch-state"','data-tab="config"','data-tab="inputs-editor"')) {
            if ($navText -notlike "*$requiredTab*") {
                Add-CheckError "$page icon-only nav missing required primary tab: $requiredTab"
            }
        }
        if ($navText -match 'data-tab="discover"') {
            Add-CheckError "$page primary nav must not expose deferred Discover"
        }
        if ($navText -notmatch '🏠' -or $navText -notmatch '📺' -or $navText -notmatch '🎞️' -or $navText -notmatch '📅' -or $navText -notmatch '✅') {
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
    ForEach-Object { [System.IO.Path]::GetRelativePath($RepoRoot.Path, $_.FullName).Replace('\','/') }
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
foreach ($needle in @(
    'compact percent',
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
    '${cleanType}:show:${id}'
)) {
    if ($watchStateText -notlike "*$needle*") { Add-CheckError "Watch-state key pattern missing: $needle" }
}
if ($watchStateText -match 'return keyFor\(cleanType,id\)') {
    Add-CheckError 'watch_state_manager.js must not fall back to generic type:id keys.'
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
      const result = await page.evaluate(() => {
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
        const discoverCards = Array.from(document.querySelectorAll('#panel-discover .media-card')).map(card => ({
          kind: card.getAttribute('data-kind') || '',
          id: card.getAttribute('data-id') || card.getAttribute('data-show-open') || card.getAttribute('data-movie-open') || ''
        }));
        return {
          tabs,
          logoRect,
          headerRect,
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
            hostScrollWidth: calendarHost ? calendarHost.scrollWidth : 0
          } : null,
          actionButtons,
          dashHeads,
          discoverCards
        };
      });
      const visibleTextLabels = new Set(['Dashboard','Shows','Movies','Calendar','Watch Me','Discover','Config','Inputs Editor','Manage Watch State']);
      const badText = result.tabs.filter(tab => visibleTextLabels.has(tab.text));
      const framedTabs = result.tabs.filter(tab => tab.borderTopWidth > 0 || tab.borderLeftWidth > 0 || tab.borderRadius > 2);
      const missingLabels = result.tabs.filter(tab => !tab.label);
      const requiredTabs = ['dashboard','shows','movies','calendar','manage-watch-state','config','inputs-editor'];
      const missingRequiredTabs = requiredTabs.filter(id => !result.tabs.some(tab => tab.id === id));
      const logoRatio = result.logoRect && result.logoRect.height ? result.logoRect.width / result.logoRect.height : 99;
      const logoBad = !result.logoRect || !result.logoNatural || result.logoNatural.width !== result.logoNatural.height || logoRatio > 1.25 || result.logoRect.width > 44 || result.logoRect.height > 44 || !result.headerRect || result.logoRect.top < result.headerRect.top - 1 || result.logoRect.bottom > result.headerRect.bottom + 1 || result.headerRect.height > 70;
      const manageBad = (pageName === 'config.html' && result.hasManage) || (pageName === 'manage_watch_state.html' && (!result.hasManage || !result.manageHasTable || result.manageCardCount > 0 || result.manageButtonCount < 1 || result.manageColumnCount < 10 || result.manageRowCount < 1));
      const watchBad = pageName === 'watch_me.html' && result.watchListCount < 1;
      const calendarBad = pageName === 'calendar.html' && (!result.calendar || result.calendar.gridColumns !== 7 || result.calendar.weekColumns !== 7 || result.calendar.weekDisplay === 'none' || (viewport.width < 924 && result.calendar.hostScrollWidth <= result.calendar.hostClientWidth));
      const deferredDiscoverInNav = result.tabs.some(tab => tab.id === 'discover');
      const movieNavBad = result.tabs.some(tab => tab.id === 'movies' && tab.text === '🎬');
      const actionBad = result.actionButtons.some(btn => btn.icon === '🎟️' || btn.icon === '▶' || btn.icon === '🎬' || btn.icon === '📏' || btn.icon === '💛' || btn.icon === '⭐' || Math.abs(btn.width - btn.height) > 1 || btn.radius < 7 || btn.radius > 10 || btn.radius >= (btn.width / 2) || !btn.belowImage);
      const stickyBad = pageName === 'index.html' && (!result.dashHeads.some(h => /Current \/ Recent/.test(h.text) && h.position === 'sticky') || !result.dashHeads.some(h => /Watchlist/.test(h.text) && h.position === 'sticky') || !result.dashHeads.some(h => /Upcoming/.test(h.text) && h.position === 'sticky') || !result.dashHeads.some(h => /Recommendations/.test(h.text) && h.position === 'sticky'));
      const discoverBad = pageName === 'discover.html' && result.discoverCards.length > 0;
      const pageErrors = errors.filter(error => !ignoreConsole(error));
      if (badText.length || framedTabs.length || missingLabels.length || missingRequiredTabs.length || deferredDiscoverInNav || movieNavBad || logoBad || manageBad || watchBad || calendarBad || actionBad || stickyBad || discoverBad || pageErrors.length){
        failures.push({ viewport: viewport.name, page: pageName, badText, framedTabs, missingLabels, missingRequiredTabs, deferredDiscoverInNav, movieNavBad, logoRatio, logoRect: result.logoRect, headerRect: result.headerRect, manageButtonCount: result.manageButtonCount, manageHasTable: result.manageHasTable, manageCardCount: result.manageCardCount, manageColumnCount: result.manageColumnCount, manageRowCount: result.manageRowCount, watchListCount: result.watchListCount, calendar: result.calendar, actionButtons: result.actionButtons, dashHeads: result.dashHeads, discoverCards: result.discoverCards, errors: pageErrors });
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
