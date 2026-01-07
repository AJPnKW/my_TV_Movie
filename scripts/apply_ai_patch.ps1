# scripts\apply_ai_patch.ps1
# Applies the newest .zip patch from: <repo>\.ai_downloads
# - backs up any overwritten files into: <repo>\.ai_downloads\backups\<timestamp>\
# - writes a log into: <repo>\.ai_downloads\logs\
# - auto-picks newest zip unless -ZipName is provided
# - copies extracted paths into REPO ROOT (zip should contain web\..., data\..., etc)

[CmdletBinding()]
param(
  [string]$ZipName = "",
  [string]$PatchInboxRelative = ".ai_downloads"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Find-RepoRoot {
  param([string]$StartDir)
  $d = (Resolve-Path -LiteralPath $StartDir).Path
  while ($true) {
    if (Test-Path -LiteralPath (Join-Path $d ".git")) { return $d }
    $parent = Split-Path -Parent $d
    if (-not $parent -or $parent -eq $d) { throw "Repo root not found (no .git above $StartDir)" }
    $d = $parent
  }
}

$repoRoot   = Find-RepoRoot -StartDir $PSScriptRoot
$patchInbox = Join-Path $repoRoot $PatchInboxRelative
$logDir     = Join-Path $patchInbox "logs"
Ensure-Dir $patchInbox
Ensure-Dir $logDir

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir ("apply_ai_patch_{0}.log.txt" -f $ts)

function Log([string]$msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  $line | Tee-Object -FilePath $logPath -Append
}

Log "START apply_ai_patch"
Log "repo_root=$repoRoot"
Log "patch_inbox=$patchInbox"
Log "log=$logPath"

# pick zip from inbox
$zipPath = $null
if ($ZipName -and $ZipName.Trim() -ne "") {
  $zipPath = Join-Path $patchInbox $ZipName
  if (-not (Test-Path -LiteralPath $zipPath)) { throw "Zip not found: $zipPath" }
} else {
  $z = Get-ChildItem -LiteralPath $patchInbox -File -Filter "*.zip" |
       Sort-Object LastWriteTime -Descending |
       Select-Object -First 1
  if (-not $z) { throw "No .zip files found in: $patchInbox" }
  $zipPath = $z.FullName
}
Log "zip=$zipPath"

# temp extract
$temp = Join-Path $env:TEMP ("my_tv_movie_patch_" + [guid]::NewGuid().ToString("N"))
Ensure-Dir $temp

Log "extract_to=$temp"
Expand-Archive -LiteralPath $zipPath -DestinationPath $temp -Force

# FORCE array so .Length always exists (single file => 1)
$extractedFiles = @(Get-ChildItem -LiteralPath $temp -Recurse -File)
if ($extractedFiles.Length -eq 0) { throw "Zip extracted zero files." }

# backup overwritten files (in inbox backups)
$backupRoot = Join-Path (Join-Path $patchInbox "backups") $ts
Ensure-Dir $backupRoot

Log "backup_root=$backupRoot"
Log ("files_in_patch={0}" -f $extractedFiles.Length)

# 1) backup anything that will be overwritten
$idx = 0
foreach ($f in $extractedFiles) {
  $idx++
  $rel  = $f.FullName.Substring($temp.Length).TrimStart("\","/")
  $dest = Join-Path $repoRoot $rel

  $pct = if ($extractedFiles.Length -gt 0) { [int](($idx / [double]$extractedFiles.Length) * 100) } else { 0 }
  Write-Progress -Activity "Applying patch" -Status "$idx / $($extractedFiles.Length): $rel" -PercentComplete $pct

  if (Test-Path -LiteralPath $dest) {
    $destRelDir = Split-Path -Parent $rel
    $bkDir = Join-Path $backupRoot $destRelDir
    Ensure-Dir $bkDir
    Copy-Item -LiteralPath $dest -Destination (Join-Path $bkDir (Split-Path -Leaf $dest)) -Force
  }
}

# 2) copy patch contents into repo root
$idx = 0
foreach ($f in $extractedFiles) {
  $idx++
  $rel  = $f.FullName.Substring($temp.Length).TrimStart("\","/")
  $dest = Join-Path $repoRoot $rel
  $destDir = Split-Path -Parent $dest
  Ensure-Dir $destDir

  $pct = if ($extractedFiles.Length -gt 0) { [int](($idx / [double]$extractedFiles.Length) * 100) } else { 0 }
  Write-Progress -Activity "Copying files" -Status "$idx / $($extractedFiles.Length): $rel" -PercentComplete $pct

  Copy-Item -LiteralPath $f.FullName -Destination $dest -Force
}

Write-Progress -Activity "Applying patch" -Completed

# cleanup
Remove-Item -LiteralPath $temp -Recurse -Force

Log "DONE patch applied"
Log "backup=$backupRoot"
Log "END"

Write-Host ""
Write-Host "PATCH APPLIED:" $zipPath
Write-Host "BACKUP:" $backupRoot
Write-Host "LOG:" $logPath
Read-Host "Press Enter"
