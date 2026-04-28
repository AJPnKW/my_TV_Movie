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
    'reports/ui_stabilization/asset_optimization.json'
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
    & python -m py_compile scripts/build_split_runtime.py scripts/optimize_runtime_assets.py
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
    'docs/UI_COMPONENTS.md'
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
    'Apply overlay'
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
        $_ -match '(?i)(placeholder|apply_overlay|overlay_patch)'
    }
foreach ($path in $badNames) {
    Add-CheckError "Forbidden placeholder/overlay file name: $path"
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
