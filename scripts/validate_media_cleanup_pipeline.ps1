# FILE: scripts/validate_media_cleanup_pipeline.ps1
# VERSION: v0.4.3
# UPDATED: 2026-05-09
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$LogDir = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogDir "validate_$Stamp.log.txt"

function Write-LogLine {
    param([string]$Message)
    $Message | Tee-Object -FilePath $Log -Append
}

function Invoke-NativeLogged {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-LogLine ""
    Write-LogLine "START: $Label"
    $OriginalErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $Output = & $Command 2>&1
    $ExitCode = $LASTEXITCODE
    $ErrorActionPreference = $OriginalErrorActionPreference
    foreach ($Line in $Output) {
        Write-LogLine ([string]$Line)
    }
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
Set-Content -LiteralPath $Log -Value "Validating media cleanup pipeline..." -Encoding UTF8
Write-Host "Validating media cleanup pipeline..."

Invoke-NativeLogged "Repository validator" {
    Invoke-Python312 @("tools\media_renamer\media_validator.py")
}

Invoke-NativeLogged "Pipeline self-test" {
    Invoke-Python312 @("tools\media_renamer\media_cleanup_pipeline.py", "self-test", "--repo-root", $RepoRoot)
}

Write-LogLine ""
Write-LogLine "Validation completed. Log: $Log"
Write-Host "Validation completed. Log: $Log"

if (-not $env:MEDIA_CLEANUP_NO_PAUSE) {
    Read-Host "Press Enter to close"
}
