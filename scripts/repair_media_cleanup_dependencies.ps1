# FILE: scripts/repair_media_cleanup_dependencies.ps1
# VERSION: v0.5.6
# UPDATED: 2026-05-10
# CHANGE NOTES:
# - Uses Start-Process with stdout/stderr files to avoid Windows PowerShell NativeCommandError noise.
# - Does not run pip uninstall shiboken unless the obsolete module is actually importable.
# - Installs GUI dependencies from requirements-gui.txt using binary wheels only.
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$VenvRoot = Join-Path $RepoRoot ".venv_media_cleanup_gui"
$Python = Join-Path $VenvRoot "Scripts\python.exe"
$LogDir = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogDir "dependency_repair_$Stamp.log.txt"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $Line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $Log -Value $Line -Encoding UTF8
    Write-Host $Line
}

function Invoke-CapturedProcess {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments,
        [int[]]$AllowedExitCodes = @(0)
    )

    Write-Log "START: $Label"
    $TempBase = Join-Path $env:TEMP ("media_cleanup_{0}_{1}" -f $Label.Replace(" ","_").Replace(":","_"), [guid]::NewGuid().ToString("N"))
    $StdOut = "$TempBase.out.txt"
    $StdErr = "$TempBase.err.txt"

    $Process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $StdOut -RedirectStandardError $StdErr

    if (Test-Path -LiteralPath $StdOut) {
        Get-Content -LiteralPath $StdOut -Raw -ErrorAction SilentlyContinue | Add-Content -LiteralPath $Log -Encoding UTF8
    }
    if (Test-Path -LiteralPath $StdErr) {
        $ErrText = Get-Content -LiteralPath $StdErr -Raw -ErrorAction SilentlyContinue
        if (-not [string]::IsNullOrWhiteSpace($ErrText)) {
            Add-Content -LiteralPath $Log -Value "[stderr]" -Encoding UTF8
            Add-Content -LiteralPath $Log -Value $ErrText -Encoding UTF8
        }
    }

    Remove-Item -LiteralPath $StdOut,$StdErr -Force -ErrorAction SilentlyContinue

    if ($AllowedExitCodes -notcontains $Process.ExitCode) {
        Write-Log "FAIL: $Label exit code $($Process.ExitCode)"
        throw "$Label failed. Log: $Log"
    }

    Write-Log "PASS: $Label exit code $($Process.ExitCode)"
}

Write-Log "Media Cleanup dependency repair v0.5.6"
Write-Log "Repo: $RepoRoot"
Write-Log "Venv: $VenvRoot"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Log "Creating Python 3.12 virtual environment"
    Invoke-CapturedProcess -Label "Create venv" -FilePath "py" -Arguments @("-3.12", "-m", "venv", $VenvRoot)
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment was not created: $Python"
}

Invoke-CapturedProcess -Label "Upgrade pip tooling" -FilePath $Python -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")

$CheckObsoleteScript = Join-Path $env:TEMP ("check_obsolete_shiboken_{0}.py" -f [guid]::NewGuid().ToString("N"))
@'
from __future__ import annotations
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("shiboken") else 1)
'@ | Set-Content -LiteralPath $CheckObsoleteScript -Encoding UTF8

$ObsoleteCheck = Start-Process -FilePath $Python -ArgumentList @($CheckObsoleteScript) -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru
Remove-Item -LiteralPath $CheckObsoleteScript -Force -ErrorAction SilentlyContinue

if ($ObsoleteCheck.ExitCode -eq 0) {
    Invoke-CapturedProcess -Label "Remove obsolete shiboken package" -FilePath $Python -Arguments @("-m", "pip", "uninstall", "-y", "shiboken")
}
else {
    Write-Log "Obsolete shiboken package is not installed; no uninstall needed."
}

$Requirements = Join-Path $RepoRoot "tools\media_renamer\requirements-gui.txt"
if (-not (Test-Path -LiteralPath $Requirements)) {
    throw "Missing requirements file: $Requirements"
}

Invoke-CapturedProcess -Label "Install GUI dependencies" -FilePath $Python -Arguments @("-m", "pip", "install", "--no-cache-dir", "--only-binary=:all:", "-r", $Requirements)

Write-Log "Dependency repair completed. Log: $Log"
Write-Host ""
Write-Host "Dependency repair completed."
Write-Host "Log: $Log"
