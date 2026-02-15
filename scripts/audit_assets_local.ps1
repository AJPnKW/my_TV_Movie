#!/usr/bin/env pwsh
# ==============================================================================
# [FILE]    scripts/audit_asset_path_drift.ps1
# [PROJECT] my_TV_Movie
# [ROLE]    Detect drift between data.json *_local paths and repo assets folder
# [VERSION] v1.0.0
# [UPDATED] 2026-02-02
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log([string]$msg) {
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[$ts] $msg"
}

function Get-RepoRoot {
  # Robust even when invoked via -File or dot-sourcing
  if ($PSCommandPath) {
    return (Resolve-Path (Join-Path (Split-Path -Parent $PSCommandPath) "..")).Path
  }
  if ($MyInvocation.MyCommand.Path) {
    return (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
  }
  return (Get-Location).Path
}

function Collect-LocalPaths($node, [string]$jsonPath = "$") {
  $out = New-Object System.Collections.Generic.List[object]

  if ($null -eq $node) { return $out }

  # Hashtable / PSCustomObject
  if ($node -is [System.Collections.IDictionary]) {
    foreach ($k in $node.Keys) {
      $v = $node[$k]
      $p = "$jsonPath.$k"
      if ($k -like "*_local" -and $v -is [string] -and $v.Trim().Length -gt 0) {
        $out.Add([pscustomobject]@{ json_path=$p; local_value=$v })
      }
      foreach ($row in (Collect-LocalPaths -node $v -jsonPath $p)) { $out.Add($row) }
    }
    return $out
  }

  # PSCustomObject
  if ($node -is [pscustomobject]) {
    foreach ($prop in $node.PSObject.Properties) {
      $k = $prop.Name
      $v = $prop.Value
      $p = "$jsonPath.$k"
      if ($k -like "*_local" -and $v -is [string] -and $v.Trim().Length -gt 0) {
        $out.Add([pscustomobject]@{ json_path=$p; local_value=$v })
      }
      foreach ($row in (Collect-LocalPaths -node $v -jsonPath $p)) { $out.Add($row) }
    }
    return $out
  }

  # Arrays / Lists
  if ($node -is [System.Collections.IEnumerable] -and -not ($node -is [string])) {
    $i = 0
    foreach ($item in $node) {
      $p = "$jsonPath[$i]"
      foreach ($row in (Collect-LocalPaths -node $item -jsonPath $p)) { $out.Add($row) }
      $i++
    }
    return $out
  }

  return $out
}

function Normalize-LocalToRepoPath([string]$repoRoot, [string]$localVal) {
  $v = $localVal.Trim()

  # normalize slashes
  $v = $v -replace "\\","/"

  # strip leading "./"
  if ($v.StartsWith("./")) { $v = $v.Substring(2) }

  # strip leading "web/" if someone stored that
  if ($v.StartsWith("web/")) { $v = $v.Substring(4) }

  # if it already starts with "assets/", map to repo_root\assets\...
  if ($v.StartsWith("assets/")) {
    return (Join-Path $repoRoot ($v -replace "/","\"))
  }

  # if it starts with "/assets/", treat as web-rooted and map to repo_root\assets\...
  if ($v.StartsWith("/assets/")) {
    $vv = $v.Substring(1)
    return (Join-Path $repoRoot ($vv -replace "/","\"))
  }

  # if it starts with "http", it's not local
  if ($v -match '^(http|https)://') {
    return $null
  }

  # otherwise: treat as relative to repo root (last-resort)
  return (Join-Path $repoRoot ($v -replace "/","\"))
}

# ---------------- main ----------------
$repoRoot = Get-RepoRoot
$dataJson = Join-Path $repoRoot "data\data.json"
$assetsRoot = Join-Path $repoRoot "assets"
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$stamp = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")
$outCsv = Join-Path $logsDir "audit_asset_path_drift_$stamp.csv"

Write-Log "--- START ---"
Write-Log "repo_root   : $repoRoot"
Write-Log "data_json   : $dataJson"
Write-Log "assets_root : $assetsRoot"
Write-Log "output_csv  : $outCsv"

if (-not (Test-Path $dataJson)) { throw "ERROR: Missing data\data.json" }
if (-not (Test-Path $assetsRoot)) { throw "ERROR: Missing assets\ folder at repo root" }

Write-Log "Loading JSON..."
$jsonText = Get-Content -LiteralPath $dataJson -Raw -Encoding UTF8
$data = $jsonText | ConvertFrom-Json

$paths = Collect-LocalPaths -node $data -jsonPath "$"
Write-Log ("local_fields_found : {0}" -f $paths.Count)

$rows = foreach ($p in $paths) {
  $repoPath = Normalize-LocalToRepoPath -repoRoot $repoRoot -localVal $p.local_value
  $exists = $false
  $kind = "unknown"

  if ($null -eq $repoPath) {
    $kind = "non_local"
  } else {
    $exists = Test-Path -LiteralPath $repoPath
    $norm = ($p.local_value.Trim() -replace "\\","/")
    if ($norm.StartsWith("web/")) { $kind = "drift_web_prefix" }
    elseif ($norm.StartsWith("./web/")) { $kind = "drift_web_prefix" }
    elseif ($norm -match "web/assets/") { $kind = "drift_web_assets" }
    elseif ($norm.StartsWith("assets/") -or $norm.StartsWith("/assets/")) { $kind = "assets_relative" }
    else { $kind = "other_relative" }
  }

  [pscustomobject]@{
    json_path   = $p.json_path
    local_value = $p.local_value
    kind        = $kind
    repo_path   = $repoPath
    exists      = $exists
  }
}

$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $outCsv

$missing = @($rows | Where-Object { $_.kind -ne "non_local" -and $_.repo_path -and -not $_.exists })
$byKind = $rows | Group-Object kind | Sort-Object Count -Descending

Write-Log ("missing_count : {0}" -f $missing.Count)
Write-Log "breakdown:"
foreach ($g in $byKind) {
  Write-Log ("  {0,-18} {1,6}" -f $g.Name, $g.Count)
}

Write-Log "--- END ---"
Write-Host ""
Write-Host "Press Enter to exit..."
[void](Read-Host)
