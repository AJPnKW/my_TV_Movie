# FILE: scripts/validate_media_cleanup_dependencies.ps1
# VERSION: v0.5.6
# UPDATED: 2026-05-10
# CHANGE NOTES:
# - Validates PySide6/shiboken6 from the dedicated GUI venv.
# - Captures full stdout/stderr without Windows PowerShell NativeCommandError noise.
# - Fails if obsolete shiboken is importable.
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$VenvRoot = Join-Path $RepoRoot ".venv_media_cleanup_gui"
$Python = Join-Path $VenvRoot "Scripts\python.exe"
$LogDir = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogDir "dependency_validate_$Stamp.log.txt"

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
        [string[]]$Arguments
    )

    Write-Log "START: $Label"
    $TempBase = Join-Path $env:TEMP ("media_cleanup_validate_{0}_{1}" -f $Label.Replace(" ","_").Replace(":","_"), [guid]::NewGuid().ToString("N"))
    $StdOut = "$TempBase.out.txt"
    $StdErr = "$TempBase.err.txt"

    $Process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $StdOut -RedirectStandardError $StdErr

    $OutText = ""
    $ErrText = ""
    if (Test-Path -LiteralPath $StdOut) { $OutText = Get-Content -LiteralPath $StdOut -Raw -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $StdErr) { $ErrText = Get-Content -LiteralPath $StdErr -Raw -ErrorAction SilentlyContinue }

    if (-not [string]::IsNullOrWhiteSpace($OutText)) { Add-Content -LiteralPath $Log -Value $OutText -Encoding UTF8 }
    if (-not [string]::IsNullOrWhiteSpace($ErrText)) {
        Add-Content -LiteralPath $Log -Value "[stderr]" -Encoding UTF8
        Add-Content -LiteralPath $Log -Value $ErrText -Encoding UTF8
    }

    Remove-Item -LiteralPath $StdOut,$StdErr -Force -ErrorAction SilentlyContinue

    if ($Process.ExitCode -ne 0) {
        Write-Log "FAIL: $Label exit code $($Process.ExitCode)"
        throw "$Label failed. Log: $Log"
    }

    Write-Log "PASS: $Label exit code $($Process.ExitCode)"
}

Write-Log "Media Cleanup dependency validation v0.5.6"
Write-Log "Repo: $RepoRoot"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Missing GUI Python venv. Run scripts\repair_media_cleanup_dependencies.ps1 first. Expected: $Python"
}

$ValidationScript = Join-Path $env:TEMP ("validate_media_cleanup_deps_{0}.py" -f [guid]::NewGuid().ToString("N"))
@'
from __future__ import annotations

import importlib.metadata as metadata
import importlib.util
import sys

errors: list[str] = []

if importlib.util.find_spec("shiboken") is not None:
    errors.append("Obsolete package/module 'shiboken' is importable. Remove it. Only shiboken6 is valid.")

try:
    import PySide6
    from PySide6.QtCore import qVersion
except Exception as exc:
    errors.append(f"PySide6 import failed: {exc!r}")

try:
    import shiboken6
except Exception as exc:
    errors.append(f"shiboken6 import failed: {exc!r}")

try:
    print(f"PySide6={metadata.version('PySide6')}")
except Exception as exc:
    errors.append(f"PySide6 version lookup failed: {exc!r}")

try:
    print(f"shiboken6={metadata.version('shiboken6')}")
except Exception as exc:
    errors.append(f"shiboken6 version lookup failed: {exc!r}")

try:
    print(f"Qt={qVersion()}")
except Exception as exc:
    errors.append(f"Qt version lookup failed: {exc!r}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Dependency validation passed.")
'@ | Set-Content -LiteralPath $ValidationScript -Encoding UTF8

try {
    Invoke-CapturedProcess -Label "Validate PySide6 and shiboken6" -FilePath $Python -Arguments @($ValidationScript)
}
finally {
    Remove-Item -LiteralPath $ValidationScript -Force -ErrorAction SilentlyContinue
}

$Launcher = Join-Path $RepoRoot "tools\media_renamer\media_cleanup_launcher.py"
if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Missing launcher: $Launcher"
}
$LauncherText = Get-Content -LiteralPath $Launcher -Raw -Encoding UTF8
if ($LauncherText -match "(?i)tkinter") {
    throw "Tkinter reference found in launcher. PySide6 only is allowed."
}

Write-Log "Dependency validation completed. Log: $Log"
Write-Host ""
Write-Host "Dependency validation completed."
Write-Host "Log: $Log"
