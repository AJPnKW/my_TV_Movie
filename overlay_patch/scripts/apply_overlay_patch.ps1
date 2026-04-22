Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $repoRoot '.git'))) { throw 'Run this from the repo root: C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie' }

$overlayRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$overlayRoot = Split-Path -Parent $overlayRoot
$logDir = Join-Path $repoRoot 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir 'apply_overlay_patch_2026_04_19.log.txt'
"START $(Get-Date -Format s)" | Set-Content $logFile

function Log([string]$m){ $m | Add-Content $logFile; Write-Host $m }

if (Test-Path (Join-Path $repoRoot '.git\rebase-merge') -or Test-Path (Join-Path $repoRoot '.git\rebase-apply')) {
  Log 'Rebase detected. Aborting rebase.'
  git rebase --abort | Out-Null
}

Log 'Fetching origin.'
git fetch origin | Out-Null

Log 'Restoring live files from origin/main.'
git restore --source origin/main -- 'web/index.html' 'web/css/main_app.css' 'web/css/my_tv_hub.css'

New-Item -ItemType Directory -Path (Join-Path $repoRoot 'web\css') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $repoRoot 'web\js') -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $overlayRoot 'web\css\ui_fix_patch.css') -Destination (Join-Path $repoRoot 'web\css\ui_fix_patch.css') -Force
Copy-Item -LiteralPath (Join-Path $overlayRoot 'web\js\fix_images.js') -Destination (Join-Path $repoRoot 'web\js\fix_images.js') -Force
Log 'Overlay assets copied.'

$indexPath = Join-Path $repoRoot 'web\index.html'
$html = Get-Content $indexPath -Raw
$html = $html -replace '`r`n',''
if ($html -notmatch 'ui_fix_patch\.css') {
  if ($html -match '<link rel="stylesheet" href="\./css/main_app\.css"\s*/?>') {
    $html = $html -replace '(<link rel="stylesheet" href="\./css/main_app\.css"\s*/?>)', "$1`r`n  <link rel=\"stylesheet\" href=\"./css/ui_fix_patch.css\" />"
  } else {
    $html = $html -replace '</head>', "  <link rel=\"stylesheet\" href=\"./css/ui_fix_patch.css\" />`r`n</head>"
  }
}
if ($html -notmatch 'fix_images\.js') {
  $html = $html -replace '</body>', "  <script src=\"./js/fix_images.js\"></script>`r`n</body>"
}
Set-Content -LiteralPath $indexPath -Value $html -Encoding UTF8
Log 'index.html patched.'

git add -- 'web/index.html' 'web/css/ui_fix_patch.css' 'web/js/fix_images.js'
Log 'Staged: web/index.html, web/css/ui_fix_patch.css, web/js/fix_images.js'
Log 'DONE'
