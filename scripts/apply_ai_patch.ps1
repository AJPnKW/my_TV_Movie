<#
.SYNOPSIS
  Apply an AI-delivered zip patch from .ai_downloads into the repo root, with automatic backups + logging.

.DESCRIPTION
  - Patch zips are expected to be downloaded into: <repo>\.ai_downloads
  - This script lives in: <repo>\scripts\apply_ai_patch.ps1
  - By default, applies the newest *.zip in .ai_downloads (excluding logs/backups folders).
  - Creates backups of any files that will be overwritten into: <repo>\.ai_downloads\backups\<timestamp>\
  - Writes a log to: <repo>\.ai_downloads\logs\apply_ai_patch_<timestamp>.log.txt

.PARAMETER ZipName
  Optional. Exact filename of the patch zip (must exist in .ai_downloads).

.PARAMETER PatchInbox
  Optional. Folder containing patch zips (default: <repo>\.ai_downloads).

.PARAMETER RepoRoot
  Optional. Repo root (default: parent of this script's folder).

.PARAMETER NoPause
  Optional. Do not wait for Enter at end.

.PARAMETER WhatIf
  Optional. Dry-run: show what would happen, do not copy files.

.NOTES
  Version: 1.3.0
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$ZipName,

  [Parameter(Mandatory=$false)]
  [string]$PatchInbox,

  [Parameter(Mandatory=$false)]
  [string]$RepoRoot,

  [Parameter(Mandatory=$false)]
  [switch]$NoPause,

  [Parameter(Mandatory=$false)]
  [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
  param([string]$Message)
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  $line = "[$ts] $Message"
  Write-Host $line
  if ($script:LogPath) {
    Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
  }
}

function Resolve-RepoRoot {
  param([string]$Maybe)
  if ($Maybe) { return (Resolve-Path -LiteralPath $Maybe).Path }
  # script path = <repo>\scripts\apply_ai_patch.ps1
  $scriptsDir = Split-Path -Parent $PSCommandPath
  $root = Split-Path -Parent $scriptsDir
  return (Resolve-Path -LiteralPath $root).Path
}

function Resolve-PatchInbox {
  param([string]$Maybe, [string]$Root)
  if ($Maybe) { return (Resolve-Path -LiteralPath $Maybe).Path }
  $p = Join-Path $Root ".ai_downloads"
  return (Resolve-Path -LiteralPath $p).Path
}

function Get-NewestZip {
  param([string]$Inbox)
  $zips = @(Get-ChildItem -LiteralPath $Inbox -File -Filter "*.zip" -ErrorAction Stop | Sort-Object LastWriteTime -Descending)
  if ($zips.Count -lt 1) { throw "No .zip files found in: $Inbox" }
  return $zips[0].FullName
}

function Get-PayloadRoot {
  param([string]$ExtractTo)
  # If there's exactly one top-level folder and no top-level files, treat that folder as the payload root.
  $top = @(Get-ChildItem -LiteralPath $ExtractTo -Force)
  $topDirs  = @($top | Where-Object { $_.PSIsContainer })
  $topFiles = @($top | Where-Object { -not $_.PSIsContainer })
  if ($topDirs.Count -eq 1 -and $topFiles.Count -eq 0) {
    return $topDirs[0].FullName
  }
  return $ExtractTo
}

function Get-RelativePath {
  param([string]$Base, [string]$Full)
  $b = (Resolve-Path -LiteralPath $Base).Path.TrimEnd('\')
  $f = (Resolve-Path -LiteralPath $Full).Path
  if ($f.Length -le $b.Length) { return "" }
  if ($f.Substring(0, $b.Length).ToLowerInvariant() -ne $b.ToLowerInvariant()) { return $f }
  return $f.Substring($b.Length).TrimStart('\')
}

# ---------- main ----------
$extractTo = $null
try {
  $root  = Resolve-RepoRoot -Maybe $RepoRoot
  $inbox = Resolve-PatchInbox -Maybe $PatchInbox -Root $root

  $ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
  $logDir = Join-Path $inbox "logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $script:LogPath = Join-Path $logDir ("apply_ai_patch_{0}.log.txt" -f $ts)

  Write-Log "START apply_ai_patch"
  Write-Log "version=1.3.0"
  Write-Log "repo_root=$root"
  Write-Log "patch_inbox=$inbox"
  Write-Log "log=$script:LogPath"

  $zipPath = $null
  if ($ZipName) {
    $zipPath = Join-Path $inbox $ZipName
    if (-not (Test-Path -LiteralPath $zipPath)) { throw "Missing zip: $zipPath" }
    $zipPath = (Resolve-Path -LiteralPath $zipPath).Path
  } else {
    $zipPath = Get-NewestZip -Inbox $inbox
  }
  Write-Log "zip=$zipPath"

  $extractTo = Join-Path $env:TEMP ("my_tv_movie_patch_" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $extractTo | Out-Null
  Write-Log "extract_to=$extractTo"

  Expand-Archive -LiteralPath $zipPath -DestinationPath $extractTo -Force

  $payloadRoot = Get-PayloadRoot -ExtractTo $extractTo
  Write-Log "payload_root=$payloadRoot"

  $payloadFiles = @(Get-ChildItem -LiteralPath $payloadRoot -Recurse -File -Force)
  Write-Log ("files_in_patch={0}" -f $payloadFiles.Count)

  if ($payloadFiles.Count -lt 1) { throw "Patch payload contains no files." }

  foreach ($pf in $payloadFiles) {
    $rel = Get-RelativePath -Base $payloadRoot -Full $pf.FullName
    if ($rel -match '^(?i)\.ai_downloads\\') {
      throw "Patch contains .ai_downloads content (blocked): $rel"
    }
  }

  $backupRoot = Join-Path (Join-Path $inbox "backups") $ts
  New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
  Write-Log "backup_root=$backupRoot"

  $toOverwrite = @()
  foreach ($pf in $payloadFiles) {
    $rel  = Get-RelativePath -Base $payloadRoot -Full $pf.FullName
    $dest = Join-Path $root $rel
    if (Test-Path -LiteralPath $dest) {
      $toOverwrite += [pscustomobject]@{ Rel=$rel; Dest=$dest; Src=$pf.FullName }
    }
  }
  Write-Log ("files_to_overwrite={0}" -f $toOverwrite.Count)

  if ($WhatIf) {
    Write-Log "WHATIF enabled (no copy will occur)"
    Write-Log "DONE (whatif)"
    return
  }

  foreach ($x in $toOverwrite) {
    $bk = Join-Path $backupRoot $x.Rel
    $bkDir = Split-Path -Parent $bk
    New-Item -ItemType Directory -Force -Path $bkDir | Out-Null
    Copy-Item -LiteralPath $x.Dest -Destination $bk -Force
  }

  Copy-Item -LiteralPath (Join-Path $payloadRoot "*") -Destination $root -Recurse -Force

  Write-Log "DONE patch applied"
  Write-Log "backup=$backupRoot"

} catch {
  try { Write-Log ("ERROR: " + $_.Exception.Message) } catch {}
  throw
} finally {
  try {
    if ($extractTo -and (Test-Path -LiteralPath $extractTo)) {
      Remove-Item -LiteralPath $extractTo -Recurse -Force
    }
  } catch {
    try { Write-Log ("WARN cleanup_failed: " + $_.Exception.Message) } catch {}
  }
  try { Write-Log "END" } catch {}
  if (-not $NoPause) { Read-Host "Press Enter" | Out-Null }
}
