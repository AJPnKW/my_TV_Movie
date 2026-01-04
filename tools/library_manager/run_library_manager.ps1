>>> FILE: tools/library_manager/run_library_manager.ps1
<#
File: run_library_manager.ps1
Project: my_TV_Movie
Tool: Library Manager
Version: v0.2.4 (2026-01-03)
Path: tools\library_manager\run_library_manager.ps1

Purpose:
  Launch local Library Manager web UI (Flask) using repo venv when available,
  with deterministic logging/output folders.

Fixes included:
  - Do not use reserved $Host variable (use $bind_host).
  - Run Python via cmd.exe so native STDERR (e.g., SyntaxWarning) does not terminate PowerShell
    when $ErrorActionPreference = "Stop". Output is still captured to the log.

Usage:
  Set-Location "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\tools\library_manager"
  powershell -ExecutionPolicy Bypass -File .\run_library_manager.ps1

Outputs:
  logs\library_manager_YYYYMMDD_HHMMSS.log.txt
  out\library_inputs.json
  out\validation_report.json
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-LogFile {
  param([string]$LogDir)
  if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  return (Join-Path $LogDir ("library_manager_{0}.log.txt" -f $stamp))
}

function Write-Log {
  param([string]$Path, [string]$Msg)
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $line = "[{0}] {1}" -f $ts, $Msg
  $line | Out-File -LiteralPath $Path -Append -Encoding utf8
  Write-Host $line
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $here "..\..") | Select-Object -ExpandProperty Path

$logDir = Join-Path $here "logs"
$outDir = Join-Path $here "out"
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$log = New-LogFile -LogDir $logDir

Write-Log $log "START Library Manager"
Write-Log $log "Here = $here"
Write-Log $log "RepoRoot = $repoRoot"

# Prefer repo venv, fallback to python on PATH
$venvPy = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPy) {
  $py = $venvPy
  Write-Log $log "Python = $py (repo venv)"
} else {
  $pyCmd = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pyCmd) { throw "python.exe not found on PATH and repo venv missing: $venvPy" }
  $py = $pyCmd.Source
  Write-Log $log "Python = $py (PATH)"
}

# Ensure deps
$req = Join-Path $here "requirements.txt"
if (-not (Test-Path -LiteralPath $req)) {
  @"
flask==3.0.3
requests==2.32.3
"@ | Out-File -LiteralPath $req -Encoding utf8
  Write-Log $log "Wrote requirements.txt"
}

Write-Log $log "Installing/validating dependencies..."
& $py -m pip install -r $req 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8

# Run app
$app = Join-Path $here "library_manager_app.py"
if (-not (Test-Path -LiteralPath $app)) { throw "Missing app file: $app" }

$port = 5177
$bind_host = "127.0.0.1"
$url = "http://$bind_host`:$port/"

Write-Log $log "Launching UI: $url"
Write-Log $log "OutDir = $outDir"

Start-Process $url | Out-Null

# Run via cmd.exe so STDERR is merged into STDOUT and does not terminate PowerShell.
$cmdLine = "`"$py`" `"$app`" --repo-root `"$repoRoot`" --host $bind_host --port $port --out-dir `"$outDir`""
Write-Log $log "Cmd = $cmdLine"

cmd.exe /c $cmdLine 1>> $log 2>>&1

Write-Log $log "DONE"
Write-Host ""
Write-Host "DONE"
Write-Host "Log: $log"
Write-Host "Out: $outDir"
Write-Host ""
Read-Host "Press Enter"
<<< END FILE
