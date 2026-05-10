# FILE: scripts/run_media_cleanup_plan.ps1
# VERSION: v0.4.3
# UPDATED: 2026-05-09
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$MediaRoot = "C:\X1_Share\Recordings"
$LogDir = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogDir "plan_$Stamp.log.txt"

function Write-LogLine {
    param([string]$Message)
    $Message | Tee-Object -FilePath $Log -Append
}

function Invoke-NativeLogged {
    param([string]$Label, [scriptblock]$Command)
    Write-LogLine ""
    Write-LogLine "START: $Label"
    $OriginalErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $Output = & $Command 2>&1
    $ExitCode = $LASTEXITCODE
    $ErrorActionPreference = $OriginalErrorActionPreference
    foreach ($Line in $Output) { Write-LogLine ([string]$Line) }
    if ($ExitCode -ne 0) {
        Write-LogLine "FAIL: $Label (exit code $ExitCode)"
        throw "$Label failed. Log: $Log"
    }
    Write-LogLine "PASS: $Label"
}

function Invoke-Python312 {
    param([string[]]$Arguments)
    $Python = Join-Path $RepoRoot ".venv_media_cleanup\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $Python)) {
        py -3.12 -m venv (Join-Path $RepoRoot ".venv_media_cleanup")
    }
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Python 3.12 venv was not created at $Python"
    }
    & $Python @Arguments
}

Set-Location -LiteralPath $RepoRoot
Set-Content -LiteralPath $Log -Value "Building cleanup plan..." -Encoding UTF8
Write-LogLine "Repo: $RepoRoot"
Write-LogLine "Media: $MediaRoot"
Write-Host "Building cleanup plan..."
Write-Host "Repo: $RepoRoot"
Write-Host "Media: $MediaRoot"

Invoke-NativeLogged "Build cleanup plan" {
    Invoke-Python312 @("tools\media_renamer\media_cleanup_pipeline.py", "plan", "--repo-root", $RepoRoot, "--media-root", $MediaRoot)
}

Write-LogLine "Cleanup plan completed. Log: $Log"
Write-Host "Cleanup plan completed. Log: $Log"
if (-not $env:MEDIA_CLEANUP_NO_PAUSE) { Read-Host "Press Enter to close" }
