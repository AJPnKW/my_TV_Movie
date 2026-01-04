# ======================================================================
# [FILE]    scripts/patch_inputs_cleanup_headers.ps1
# [PROJECT] my_TV_Movie
# [PURPOSE] Remove stray header/comment lines from inputs/*.txt that
#           break parsing (e.g., "﻿# File: tv_list.txt|")
# [VERSION] v1.0.0
# [UPDATED] 2026-01-03
# ======================================================================

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logDir   = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$ts  = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$log = Join-Path $logDir ("patch_inputs_cleanup_headers_{0}.log.txt" -f $ts)

function Log([string]$msg) {
  $line = ("{0} | {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg)
  $line | Tee-Object -FilePath $log -Append
}

Log "[cleanup_headers] START repo_root=$repoRoot"
Log "[cleanup_headers] log=$log"

$targets = @(
  (Join-Path $repoRoot "inputs\tv_list.txt"),
  (Join-Path $repoRoot "inputs\movies_list.txt"),
  (Join-Path $repoRoot "inputs\watchlist.txt")
)

foreach ($f in $targets) {
  if (!(Test-Path -LiteralPath $f)) {
    Log "[cleanup_headers] SKIP missing: $f"
    continue
  }

  $bak = Join-Path $logDir ("{0}.{1}.bak" -f (Split-Path $f -Leaf), $ts)
  Copy-Item -LiteralPath $f -Destination $bak -Force
  Log "[cleanup_headers] backup=$bak"

  $lines  = Get-Content -LiteralPath $f -Encoding UTF8
  $before = $lines.Count

  # Remove:
  # - any line that (after trimming BOM/whitespace) starts with "#"
  # - any blank lines
  $clean = foreach ($ln in $lines) {
    $t = $ln
    if ($null -eq $t) { continue }
    $t = $t.Trim()
    $t = $t.Trim([char]0xFEFF)  # BOM
    if ($t.Length -eq 0) { continue }
    if ($t.StartsWith("#")) { continue }
    $ln
  }

  $after = @($clean).Count

  Set-Content -LiteralPath $f -Value $clean -Encoding UTF8
  Log ("[cleanup_headers] cleaned {0} lines: {1} -> {2}" -f $f, $before, $after)
}

Log "[cleanup_headers] END"
Write-Host "DONE. Log: $log"
