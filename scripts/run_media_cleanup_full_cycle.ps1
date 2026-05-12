# FILE: scripts/run_media_cleanup_full_cycle.ps1
# VERSION: v0.5.6
# UPDATED: 2026-05-10
# CHANGE NOTES:
# - Runs validation, iterative plan/apply, and media library generation.
# - Creates upload ZIP after logs are no longer locked.
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$MediaRoot = "C:\X1_Share\Recordings"
$UploadRoot = Join-Path $RepoRoot ".ai_uploads"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunOut = Join-Path $UploadRoot "media_cleanup_full_cycle_$Stamp"
$Log = Join-Path $RunOut "execution.log.txt"

New-Item -ItemType Directory -Force -Path $RunOut | Out-Null
$env:MEDIA_CLEANUP_NO_PAUSE = "1"

function Write-RunLog {
    param([string]$Message)
    $Line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $Log -Value $Line -Encoding UTF8
    Write-Host $Line
}

function Invoke-Step {
    param([string]$Label, [scriptblock]$Command)
    Write-RunLog ""
    Write-RunLog "START: $Label"
    try {
        $Output = & $Command 2>&1
        foreach ($Line in $Output) { Write-RunLog ([string]$Line) }
        Write-RunLog "PASS: $Label"
    }
    catch {
        Write-RunLog "FAIL: $Label"
        Write-RunLog $_.Exception.Message
        throw
    }
}

function Get-LatestPlanSummary {
    $ReportsRoot = Join-Path $RepoRoot "reports\media_renamer"
    $Latest = Get-ChildItem -LiteralPath $ReportsRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "scan_plan.json") } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $Latest) { return $null }
    $Plan = Get-Content -LiteralPath (Join-Path $Latest.FullName "scan_plan.json") -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        PlanDir = $Latest.FullName
        ReadyToFix = [int]$Plan.summary.ready_to_fix
    }
}

Write-RunLog "Media cleanup full cycle v0.5.6"
Write-RunLog "Repo: $RepoRoot"
Write-RunLog "MediaRoot: $MediaRoot"
Write-RunLog "RunOut: $RunOut"

Invoke-Step "Validate pipeline" {
    Set-Location -LiteralPath $RepoRoot
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\validate_media_cleanup_pipeline.ps1"
}

for ($Pass = 1; $Pass -le 5; $Pass++) {
    Invoke-Step "Build cleanup plan pass $Pass" {
        Set-Location -LiteralPath $RepoRoot
        powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\run_media_cleanup_plan.ps1"
    }

    $Summary = Get-LatestPlanSummary
    if ($Summary) {
        Write-RunLog ("Plan pass {0}: ready_to_fix={1}; plan={2}" -f $Pass, $Summary.ReadyToFix, $Summary.PlanDir)
        if ($Summary.ReadyToFix -le 0) { break }
    }

    Invoke-Step "Apply safe cleanup plan pass $Pass" {
        Set-Location -LiteralPath $RepoRoot
        powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\apply_media_cleanup_plan.ps1"
    }
}

Invoke-Step "Generate media library page" {
    Set-Location -LiteralPath $RepoRoot
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\generate_media_library_page.ps1"
}

Invoke-Step "Create current directory listing" {
    $ListingTxt = Join-Path $RunOut "recordings_tree_after_cleanup.log.txt"
    $ListingCsv = Join-Path $RunOut "recordings_tree_after_cleanup.csv"

    Get-ChildItem -LiteralPath $MediaRoot -Recurse -Force |
        Select-Object FullName, Name, Extension, Length, LastWriteTime, Mode |
        Export-Csv -LiteralPath $ListingCsv -NoTypeInformation -Encoding UTF8

    Get-ChildItem -LiteralPath $MediaRoot -Recurse -Force |
        Sort-Object FullName |
        Format-Table Mode, LastWriteTime, Length, FullName -AutoSize |
        Out-String -Width 4096 |
        Set-Content -LiteralPath $ListingTxt -Encoding UTF8
}

Invoke-Step "Collect latest reports" {
    $ReportsRoot = Join-Path $RepoRoot "reports"
    $ReportCopy = Join-Path $RunOut "reports"
    if (Test-Path -LiteralPath $ReportsRoot) {
        Copy-Item -LiteralPath $ReportsRoot -Destination $ReportCopy -Recurse -Force
    }
    Copy-Item -LiteralPath (Join-Path $MediaRoot "Media_Library.html") -Destination (Join-Path $RunOut "Media_Library.html") -Force -ErrorAction SilentlyContinue
    Copy-Item -LiteralPath (Join-Path $MediaRoot "Media_Library.json") -Destination (Join-Path $RunOut "Media_Library.json") -Force -ErrorAction SilentlyContinue
}

$ZipOut = "$RunOut.zip"
Compress-Archive -LiteralPath (Join-Path $RunOut "*") -DestinationPath $ZipOut -Force

Write-RunLog "UPLOAD THIS FILE: $ZipOut"
Write-Host ""
Write-Host "Media cleanup complete."
Write-Host "Media Library:"
Write-Host (Join-Path $MediaRoot "Media_Library.html")
Write-Host ""
Write-Host "UPLOAD THIS FILE:"
Write-Host $ZipOut
Write-Host ""
if (-not $env:MEDIA_CLEANUP_NO_PAUSE_PARENT) { Read-Host "Press Enter to close" }
