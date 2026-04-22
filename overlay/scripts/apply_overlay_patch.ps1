#requires -version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$overlayRoot = Split-Path -Parent $PSScriptRoot
$defaultProjectRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
if (Test-Path (Join-Path $defaultProjectRoot ".git")) { $projectRoot = $defaultProjectRoot } else { throw "Could not find project root." }

Set-Location $projectRoot
if (!(Test-Path ".git")) { throw "NOT A GIT REPOSITORY: $projectRoot" }

New-Item -ItemType Directory -Force -Path "logs","web\css","web\js" | Out-Null
$log = Join-Path $projectRoot "logs\apply_overlay_patch_2026_04_19.log.txt"
"START $(Get-Date -Format s)" | Set-Content $log
"PROJECT_ROOT: $projectRoot" | Add-Content $log

$gitDir = Join-Path $projectRoot ".git"
if ((Test-Path (Join-Path $gitDir "rebase-merge")) -or (Test-Path (Join-Path $gitDir "rebase-apply"))) {
  git rebase --abort | Add-Content $log
  "REBASE_ABORTED: yes" | Add-Content $log
} else {
  "REBASE_ABORTED: no" | Add-Content $log
}

git fetch origin | Add-Content $log
git checkout origin/main -- web/index.html 2>> $log
if (Test-Path "web/css/main_app.css") { git checkout origin/main -- web/css/main_app.css 2>> $log }

Copy-Item -LiteralPath (Join-Path $overlayRoot "web\css\ui_fix_patch.css") -Destination "web\css\ui_fix_patch.css" -Force
Copy-Item -LiteralPath (Join-Path $overlayRoot "web\js\fix_images.js") -Destination "web\js\fix_images.js" -Force
"OVERLAY_FILES_COPIED: yes" | Add-Content $log

$indexPath = "web\index.html"
if (!(Test-Path $indexPath)) { throw "MISSING: web\index.html" }
$html = Get-Content $indexPath -Raw
$html = $html -replace '`r`n', ''
if ($html -notmatch 'ui_fix_patch\.css') { $html = $html -replace '</head>', "  <link rel=""stylesheet"" href=""./css/ui_fix_patch.css"" />`r`n</head>" }
if ($html -notmatch 'fix_images\.js') { $html = $html -replace '</body>', "  <script src=""./js/fix_images.js""></script>`r`n</body>" }
Set-Content -Path $indexPath -Value $html -Encoding UTF8
"INDEX_PATCHED: yes" | Add-Content $log

git status --short | Add-Content $log
"DONE $(Get-Date -Format s)" | Add-Content $log
Write-Host "PATCH APPLIED"
Write-Host "LOG: logs\apply_overlay_patch_2026_04_19.log.txt"
Write-Host "NEXT: open http://127.0.0.1:8000/web/index.html and Ctrl+F5"
Read-Host "Press Enter to exit"
