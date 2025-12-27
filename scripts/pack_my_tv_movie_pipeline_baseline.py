<# =======================================================================================
FILE: pack_my_tv_movie_pipeline_baseline.ps1
PURPOSE: Create a single ZIP containing ALL pipeline + web config + inputs + docs needed
         for end-to-end reproduction, and AUDIT that required files are included.

OUTPUT:
- ZIP:  <repo>\_ai_baselines_pipeline_FULL_<timestamp>.zip
- LOG:  <repo>\_ai_baselines_pipeline_FULL_<timestamp>.log.txt

COMPAT:
- Windows PowerShell 5.1 compatible (NO ternary operator, NO null-coalescing)

RULES:
- No silent failures
- Hard-fail if any REQUIRED files are missing
- Includes an audit table (found/missing/included)
- Includes a completion summary + waits for Enter
======================================================================================= #>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

function New-Stamp { Get-Date -Format "yyyy-MM-dd_HH-mm-ss" }

function Write-Log {
  param([string]$Msg)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
  $line | Tee-Object -FilePath $LogPath -Append | Out-Host
}

function Resolve-RepoPath {
  param([string]$RelPath)
  Join-Path $RepoRoot $RelPath
}

function Find-FirstByName {
  param([string]$FileName)
  Get-ChildItem -Path $RepoRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ieq $FileName } |
    Select-Object -First 1
}

function Add-AuditRow {
  param(
    [string]$Key,
    [string]$Wanted,
    [string]$Resolved,
    [bool]$Found,
    [bool]$Required
  )
  $script:Audit += New-Object psobject -Property @{
    key       = $Key
    required  = $Required
    wanted    = $Wanted
    found     = $Found
    resolved  = $Resolved
    included  = $false
  }
}

# -------------------------
# Init
# -------------------------
if (-not (Test-Path $RepoRoot)) {
  throw "RepoRoot not found: $RepoRoot"
}

$stamp   = New-Stamp
$ZipPath = Join-Path $RepoRoot ("_ai_baselines_pipeline_FULL_{0}.zip" -f $stamp)
$LogPath = Join-Path $RepoRoot ("_ai_baselines_pipeline_FULL_{0}.log.txt" -f $stamp)

$script:Audit = @()
$IncludeFiles = New-Object System.Collections.Generic.List[string]

Write-Log "START pack baseline"
Write-Log ("RepoRoot: {0}" -f $RepoRoot)
Write-Log ("ZipPath : {0}" -f $ZipPath)
Write-Log ("LogPath : {0}" -f $LogPath)

# -------------------------
# REQUIRED (hard fail if missing)
# -------------------------
$RequiredRel = @(
  "build-data.yml",
  "fetch_tmdb.py",
  "fetch_trakt.py",
  "sync_trakt.py",
  "web\config.json",
  "web\config.js",
  "web\config.html",
  "data\data.json"
)

$RequiredByName = @(
  "requirements.txt",
  "parse_txt_to_json.py"
)

# -------------------------
# OPTIONAL (included if present)
# -------------------------
$OptionalRel = @(
  "inputs\tv_list.txt",
  "inputs\movies_list.txt",
  "tv_list.txt",
  "movies_list.txt",
  "README.md",
  "docs\FULL authoritative spec\Mandatory-PIPELINE SOLUTION.txt"
)

$OptionalByGlob = @(
  "docs\**\*.md",
  "docs\**\*.txt"
)

# -------------------------
# Resolve REQUIRED relative paths
# -------------------------
Write-Log "Resolving REQUIRED relative paths..."
foreach ($rel in $RequiredRel) {
  $abs = Resolve-RepoPath $rel
  $found = Test-Path $abs
  $resolved = ""
  if ($found) { $resolved = $abs }

  Add-AuditRow -Key ("REQ_REL:" + $rel) -Wanted $rel -Resolved $resolved -Found $found -Required $true
  if ($found) { $IncludeFiles.Add($abs) | Out-Null }
}

# -------------------------
# Resolve REQUIRED by-name files (anywhere under repo)
# -------------------------
Write-Log "Resolving REQUIRED by-name files..."
foreach ($name in $RequiredByName) {
  $hit = Find-FirstByName $name
  $found = ($hit -ne $null)
  $resolved = ""
  if ($found) { $resolved = $hit.FullName }

  Add-AuditRow -Key ("REQ_NAME:" + $name) -Wanted $name -Resolved $resolved -Found $found -Required $true
  if ($found) { $IncludeFiles.Add($hit.FullName) | Out-Null }
}

# -------------------------
# Resolve OPTIONAL relative paths
# -------------------------
Write-Log "Resolving OPTIONAL relative paths..."
foreach ($rel in $OptionalRel) {
  $abs = Resolve-RepoPath $rel
  $found = Test-Path $abs
  $resolved = ""
  if ($found) { $resolved = $abs }

  Add-AuditRow -Key ("OPT_REL:" + $rel) -Wanted $rel -Resolved $resolved -Found $found -Required $false
  if ($found) { $IncludeFiles.Add($abs) | Out-Null }
}

# -------------------------
# Resolve OPTIONAL globs
# -------------------------
Write-Log "Resolving OPTIONAL globs..."
foreach ($glob in $OptionalByGlob) {
  $absGlob = Resolve-RepoPath $glob
  $hits = Get-ChildItem -Path $absGlob -File -Force -ErrorAction SilentlyContinue
  if ($hits -and $hits.Count -gt 0) {
    foreach ($h in $hits) {
      Add-AuditRow -Key ("OPT_GLOB:" + $glob + ":" + $h.FullName) -Wanted $glob -Resolved $h.FullName -Found $true -Required $false
      $IncludeFiles.Add($h.FullName) | Out-Null
    }
  }
}

# -------------------------
# Audit: hard fail on missing REQUIRED
# -------------------------
$missingReq = @($Audit | Where-Object { $_.required -eq $true -and $_.found -eq $false })
if ($missingReq.Count -gt 0) {
  Write-Log "FAIL: Missing REQUIRED files:"
  ($missingReq | Select-Object key, wanted | Format-Table -AutoSize | Out-String).TrimEnd() | ForEach-Object { Write-Log $_ }
  Write-Log "STOP (missing required). No ZIP created."
  Read-Host "Press Enter to exit"
  exit 1
}

# -------------------------
# De-dup include list + mark included in audit
# -------------------------
$IncludeFiles = @($IncludeFiles | Select-Object -Unique)
$includeSet = New-Object "System.Collections.Generic.HashSet[string]" ([StringComparer]::OrdinalIgnoreCase)
foreach ($f in $IncludeFiles) { [void]$includeSet.Add($f) }

foreach ($row in $Audit) {
  if ($row.found -and $row.resolved -and $includeSet.Contains($row.resolved)) { $row.included = $true }
}

Write-Log ("Files selected for ZIP: {0}" -f $IncludeFiles.Count)

# -------------------------
# Create ZIP
# -------------------------
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Write-Log "Creating ZIP..."
Compress-Archive -Path $IncludeFiles -DestinationPath $ZipPath -Force

# -------------------------
# Validate ZIP contents
# -------------------------
Write-Log "Validating ZIP contents..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipList = New-Object "System.Collections.Generic.List[string]"
$zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
try {
  foreach ($entry in $zip.Entries) {
    $zipList.Add($entry.FullName) | Out-Null
  }
} finally {
  $zip.Dispose()
}

$missingInZip = New-Object System.Collections.Generic.List[string]
foreach ($abs in $IncludeFiles) {
  $leaf = Split-Path $abs -Leaf
  $ok = $false
  foreach ($z in $zipList) {
    if ($z -like ("*" + $leaf)) { $ok = $true; break }
  }
  if (-not $ok) { $missingInZip.Add($abs) | Out-Null }
}

if ($missingInZip.Count -gt 0) {
  Write-Log "FAIL: Some selected files were not found inside the ZIP (unexpected):"
  foreach ($m in $missingInZip) { Write-Log (" - " + $m) }
  Write-Log "STOP (zip validation failed)."
  Read-Host "Press Enter to exit"
  exit 2
}

# -------------------------
# Output audit table
# -------------------------
Write-Log "AUDIT (required/found/included):"
(($Audit |
  Select-Object required, found, included, wanted, resolved |
  Sort-Object required -Descending, found -Ascending, included -Ascending, wanted |
  Format-Table -AutoSize | Out-String).TrimEnd()) | ForEach-Object { Write-Log $_ }

# -------------------------
# Completion summary
# -------------------------
Write-Log "SUCCESS"
Write-Log ("ZIP created: {0}" -f $ZipPath)
Write-Log ("LOG saved  : {0}" -f $LogPath)
Write-Log ("Total files zipped: {0}" -f $IncludeFiles.Count)

Read-Host "Press Enter to exit"


would a pythign scipt be better more stable and have better coding outcomes?
