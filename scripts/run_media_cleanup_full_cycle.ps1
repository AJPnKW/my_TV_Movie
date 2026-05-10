# FILE: scripts/run_media_cleanup_full_cycle.ps1
# VERSION: v0.4.4
# UPDATED: 2026-05-09
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
    $Line | Tee-Object -FilePath $Log -Append
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

Write-RunLog "Media cleanup full cycle v0.4.4"
Write-RunLog "Repo: $RepoRoot"
Write-RunLog "MediaRoot: $MediaRoot"
Write-RunLog "RunOut: $RunOut"

Invoke-Step "Validate pipeline" {
    Set-Location -LiteralPath $RepoRoot
    powershell -ExecutionPolicy Bypass -File "scripts\validate_media_cleanup_pipeline.ps1"
}

Invoke-Step "Build cleanup plan before apply" {
    Set-Location -LiteralPath $RepoRoot
    powershell -ExecutionPolicy Bypass -File "scripts\run_media_cleanup_plan.ps1"
}

Invoke-Step "Apply safe cleanup plan" {
    Set-Location -LiteralPath $RepoRoot
    powershell -ExecutionPolicy Bypass -File "scripts\apply_media_cleanup_plan.ps1"
}

Invoke-Step "Build cleanup plan after apply" {
    Set-Location -LiteralPath $RepoRoot
    powershell -ExecutionPolicy Bypass -File "scripts\run_media_cleanup_plan.ps1"
}

Invoke-Step "Create current directory listings" {
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
    $ReportsRoot = Join-Path $RepoRoot "reports\media_renamer"
    $ReportCopy = Join-Path $RunOut "latest_reports"
    New-Item -ItemType Directory -Force -Path $ReportCopy | Out-Null

    Get-ChildItem -LiteralPath $ReportsRoot -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $ReportCopy $_.Name) -Recurse -Force
        }

    $LauncherLogs = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
    if (Test-Path -LiteralPath $LauncherLogs) {
        Copy-Item -LiteralPath $LauncherLogs -Destination (Join-Path $RunOut "media_renamer_launcher_logs") -Recurse -Force
    }
}

Invoke-Step "Create upload zip" {
    $ZipOut = "$RunOut.zip"
    Compress-Archive -LiteralPath (Join-Path $RunOut "*") -DestinationPath $ZipOut -Force
    Write-RunLog "UPLOAD THIS FILE: $ZipOut"
}

Write-Host ""
Write-Host "UPLOAD THIS FILE:"
Write-Host "$RunOut.zip"
Write-Host ""
if (-not $env:MEDIA_CLEANUP_NO_PAUSE_PARENT) { Read-Host "Press Enter to close" }
