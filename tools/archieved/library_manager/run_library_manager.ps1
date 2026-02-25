<#
File: run_library_manager.ps1
Project: my_TV_Movie
Tool: Library Manager
Version: v0.2.6 (2026-01-04)
Path: tools\library_manager\run_library_manager.ps1

What this fixes:
- “This site can’t be reached” happened because Python exited immediately (usually missing TMDB env vars).
- This launcher now:
  1) Loads local .env if present (repoRoot\.env and tools\library_manager\.env)
  2) Starts the server and keeps the process running
  3) Waits for port 5177 to be listening before opening the browser
  4) If Python exits, prints exit code + tail of log

Logging:
  tools\library_manager\logs\library_manager_YYYYMMDD_HHMMSS.log.txt
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-LogFile {
  param([string]$LogDir)
  if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  Join-Path $LogDir ("library_manager_{0}.log.txt" -f $stamp)
}

function Write-Log {
  param([string]$Path, [string]$Msg)
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $line = "[{0}] {1}" -f $ts, $Msg
  $line | Out-File -LiteralPath $Path -Append -Encoding utf8
  Write-Host $line
}

function Load-DotEnv {
  param([string]$DotEnvPath, [string]$LogPath)

  if (-not (Test-Path -LiteralPath $DotEnvPath)) { return }

  Write-Log $LogPath "Loading env from: $DotEnvPath"
  $lines = Get-Content -LiteralPath $DotEnvPath -Encoding utf8 -ErrorAction SilentlyContinue
  foreach ($ln in $lines) {
    $t = ($ln ?? "").Trim()
    if (-not $t) { continue }
    if ($t.StartsWith("#")) { continue }

    # KEY=VALUE (VALUE may be quoted)
    $eq = $t.IndexOf("=")
    if ($eq -lt 1) { continue }

    $k = $t.Substring(0, $eq).Trim()
    $v = $t.Substring($eq + 1).Trim()

    if ($v.StartsWith('"') -and $v.EndsWith('"') -and $v.Length -ge 2) { $v = $v.Substring(1, $v.Length - 2) }
    if ($v.StartsWith("'") -and $v.EndsWith("'") -and $v.Length -ge 2) { $v = $v.Substring(1, $v.Length - 2) }

    if ($k) {
      $env:$k = $v
    }
  }
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

# Load optional .env files (repo root and tool folder)
Load-DotEnv -DotEnvPath (Join-Path $repoRoot ".env") -LogPath $log
Load-DotEnv -DotEnvPath (Join-Path $here ".env") -LogPath $log

# Ensure deps (requirements.txt must exist)
$req = Join-Path $here "requirements.txt"
if (-not (Test-Path -LiteralPath $req)) { throw "Missing requirements.txt at: $req" }

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

# Start python in this window (blocks while server runs)
# Capture output to log while still showing it live
$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
  # kick off a background job to open browser once port is listening
  Start-Job -ScriptBlock {
    param($h, $p, $u)
    for ($i=0; $i -lt 60; $i++) {
      try {
        if (Test-NetConnection -ComputerName $h -Port $p -InformationLevel Quiet) {
          Start-Process $u | Out-Null
          break
        }
      } catch {}
      Start-Sleep -Milliseconds 500
    }
  } -ArgumentList $bind_host, $port, $url | Out-Null

  $output = & $py $app --repo-root $repoRoot --host $bind_host --port $port --out-dir $outDir 2>&1
  $exit = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $oldEap
}

# Log whatever python emitted
$output | Out-File -LiteralPath $log -Append -Encoding utf8

if ($exit -ne 0) {
  Write-Log $log "ERROR: Python exited with code $exit"
  Write-Host ""
  Write-Host "ERROR: Python exited with code $exit"
  Write-Host "Log: $log"
  Write-Host ""
  Write-Host "Last 60 log lines:"
  Get-Content -LiteralPath $log -Tail 60 -ErrorAction SilentlyContinue
  Write-Host ""
  Read-Host "Press Enter"
  exit $exit
}

Write-Log $log "DONE"
Write-Host ""
Write-Host "DONE"
Write-Host "Log: $log"
Write-Host "Out: $outDir"
Write-Host ""
Read-Host "Press Enter"
