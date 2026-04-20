Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"

if (!(Test-Path ".git")) { throw "NOT A GIT REPOSITORY" }

New-Item -ItemType Directory -Path "logs" -Force | Out-Null

$log = "logs\repo_ui_inventory.log.txt"
"START $(Get-Date -Format s)" | Set-Content $log
"" | Add-Content $log

"=== CURRENT BRANCH ===" | Add-Content $log
git branch --show-current | Add-Content $log
"" | Add-Content $log

"=== REMOTES ===" | Add-Content $log
git remote -v | Add-Content $log
"" | Add-Content $log

"=== GIT STATUS SHORT ===" | Add-Content $log
git status --short | Add-Content $log
"" | Add-Content $log

"=== TOP LEVEL ===" | Add-Content $log
Get-ChildItem -Force | Select-Object Mode,Length,LastWriteTime,Name | Format-Table -AutoSize | Out-String | Add-Content $log
"" | Add-Content $log

"=== WEB TREE (depth 3) ===" | Add-Content $log
Get-ChildItem "web" -Recurse -Depth 3 -Force |
    Select-Object FullName |
    ForEach-Object { $_.FullName.Replace((Get-Location).Path + '\','') } |
    Add-Content $log
"" | Add-Content $log

"=== HTML FILES ===" | Add-Content $log
Get-ChildItem -Recurse -File -Include *.html |
    ForEach-Object { $_.FullName.Replace((Get-Location).Path + '\','') } |
    Add-Content $log
"" | Add-Content $log

"=== CSS FILES ===" | Add-Content $log
Get-ChildItem -Recurse -File -Include *.css |
    ForEach-Object { $_.FullName.Replace((Get-Location).Path + '\','') } |
    Add-Content $log
"" | Add-Content $log

"=== JS FILES ===" | Add-Content $log
Get-ChildItem -Recurse -File -Include *.js |
    ForEach-Object { $_.FullName.Replace((Get-Location).Path + '\','') } |
    Add-Content $log
"" | Add-Content $log

"=== INDEX.HTML HEAD/BOTTOM ===" | Add-Content $log
if (Test-Path "web\index.html") {
    $html = Get-Content "web\index.html"
    "----- first 80 lines -----" | Add-Content $log
    $html | Select-Object -First 80 | Add-Content $log
    "" | Add-Content $log
    "----- last 40 lines -----" | Add-Content $log
    $html | Select-Object -Last 40 | Add-Content $log
} else {
    "MISSING: web\index.html" | Add-Content $log
}
"" | Add-Content $log

"DONE $(Get-Date -Format s)" | Add-Content $log
Write-Host "DONE"
Write-Host "LOG: logs\repo_ui_inventory.log.txt"
