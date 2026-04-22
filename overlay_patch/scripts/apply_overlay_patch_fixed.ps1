Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'

if ((Test-Path '.git\rebase-merge') -or (Test-Path '.git\rebase-apply')) {
    git rebase --abort
}

git fetch origin

$indexPath = 'web\index.html'
$cssTarget = 'web\css\ui_fix_patch.css'
$jsTarget  = 'web\js\fix_images.js'

New-Item -ItemType Directory -Force -Path 'web\css' | Out-Null
New-Item -ItemType Directory -Force -Path 'web\js'  | Out-Null
New-Item -ItemType Directory -Force -Path 'logs'    | Out-Null

Copy-Item -LiteralPath '.\overlay_patch\web\css\ui_fix_patch.css' -Destination $cssTarget -Force
Copy-Item -LiteralPath '.\overlay_patch\web\js\fix_images.js'      -Destination $jsTarget  -Force

git restore --source=origin/main -- 'web/index.html' 'web/css/main_app.css'

$html = Get-Content -LiteralPath $indexPath -Raw

if ($html -notmatch 'ui_fix_patch\.css') {
    if ($html -match '<link rel="stylesheet" href="\./css/main_app\.css"\s*/?>') {
        $html = $html -replace '(<link rel="stylesheet" href="\./css/main_app\.css"\s*/?>)', ('$1' + "`r`n" + '  <link rel="stylesheet" href="./css/ui_fix_patch.css" />')
    }
    else {
        $html = $html -replace '</head>', ('  <link rel="stylesheet" href="./css/ui_fix_patch.css" />' + "`r`n" + '</head>')
    }
}

if ($html -notmatch 'fix_images\.js') {
    $html = $html -replace '</body>', ('  <script src="./js/fix_images.js"></script>' + "`r`n" + '</body>')
}

$html = $html -replace '`r`n', ''
Set-Content -LiteralPath $indexPath -Value $html -Encoding UTF8

git add -- 'web/index.html' 'web/css/main_app.css' 'web/css/ui_fix_patch.css' 'web/js/fix_images.js'

$logLines = @()
$logLines += 'DONE'
$logLines += (git status --short)
Set-Content -LiteralPath 'logs\apply_overlay_patch_2026_04_19.log.txt' -Value $logLines -Encoding UTF8

Write-Host 'DONE'
Write-Host 'Log: logs\apply_overlay_patch_2026_04_19.log.txt'
