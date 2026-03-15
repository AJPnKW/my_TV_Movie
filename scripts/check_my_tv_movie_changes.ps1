# ============================================================
# Script: check_my_tv_movie_changes.ps1
# Purpose: Detect real repo changes made by Codex
# ============================================================

$repo = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$logroot = Join-Path $repo "logs"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logdir = Join-Path $logroot $timestamp

New-Item -ItemType Directory -Force -Path $logdir | Out-Null

$report = Join-Path $logdir "summary.txt"

Write-Host ""
Write-Host "Checking repo for Codex changes..."
Write-Host ""

"=== Repo Change Check ===" | Out-File $report
"Timestamp: $timestamp" | Out-File $report -Append
"" | Out-File $report -Append

# ------------------------------------------------------------
# Check for new runtime modules
# ------------------------------------------------------------

"--- Runtime Modules ---" | Out-File $report -Append

$runtimeFiles = @(
"$repo\web\js\app_runtime.js",
"$repo\web\js\data_loader.js",
"$repo\web\js\card_renderer.js",
"$repo\web\js\popup_controller.js",
"$repo\web\js\action_bar.js",
"$repo\web\js\config_loader.js"
)

foreach ($file in $runtimeFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        "FOUND: $file ($size bytes)" | Out-File $report -Append
        Write-Host "FOUND:" $file
    }
    else {
        "MISSING: $file" | Out-File $report -Append
        Write-Host "MISSING:" $file
    }
}

"" | Out-File $report -Append

# ------------------------------------------------------------
# Check HTML pages for recent modification
# ------------------------------------------------------------

"--- HTML Pages ---" | Out-File $report -Append

$pages = @(
"$repo\web\index.html",
"$repo\web\shows.html",
"$repo\web\movies.html",
"$repo\web\calendar.html",
"$repo\web\discover.html",
"$repo\web\config.html"
)

foreach ($p in $pages) {
    if (Test-Path $p) {
        $file = Get-Item $p
        $sizeKB = [math]::Round($file.Length / 1KB,2)
        $modified = $file.LastWriteTime
        "$p | $sizeKB KB | Modified: $modified" | Out-File $report -Append
        Write-Host "$p | $sizeKB KB | Modified: $modified"
    }
}

"" | Out-File $report -Append

# ------------------------------------------------------------
# Detect inline JS/CSS blocks
# ------------------------------------------------------------

"--- Inline Runtime Check ---" | Out-File $report -Append

foreach ($p in $pages) {

    if (Test-Path $p) {

        $content = Get-Content $p -Raw

        $styleBlocks = ([regex]::Matches($content,"<style")).Count
        $scriptBlocks = ([regex]::Matches($content,"<script")).Count

        "$p | STYLE blocks: $styleBlocks | SCRIPT blocks: $scriptBlocks" |
            Out-File $report -Append

        Write-Host "$p | STYLE blocks:" $styleBlocks "| SCRIPT blocks:" $scriptBlocks
    }
}

"" | Out-File $report -Append

# ------------------------------------------------------------
# Check report outputs from Codex
# ------------------------------------------------------------

"--- Codex Reports ---" | Out-File $report -Append

$reports = Get-ChildItem "$repo\reports" -Recurse -ErrorAction SilentlyContinue

foreach ($r in $reports) {
    $r.FullName | Out-File $report -Append
}

Write-Host ""
Write-Host "Report written to:"
Write-Host $report
