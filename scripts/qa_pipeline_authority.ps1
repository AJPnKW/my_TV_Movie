# ==============================================================================
# QA PIPELINE AUTHORITY — my_TV_Movie
# Confirms GitHub workflow is the authoritative, repeatable system
# Outputs to console + logs/qa_pipeline_authority_*.log.txt
# ==============================================================================

$ErrorActionPreference = "Stop"

$Repo       = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$OwnerRepo = "AJPnKW/my_TV_Movie"
$Branch    = "main"

$LogDir = Join-Path $Repo "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("qa_pipeline_authority_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log.txt")

function Log($m) {
  $line = "$(Get-Date -Format s) | $m"
  $line | Tee-Object -FilePath $Log -Append
}

Log "START QA — Pipeline Authority"

# ------------------------------------------------------------------------------
# QA 1 — GitHub raw files (authoritative)
# ------------------------------------------------------------------------------
$raw = "https://raw.githubusercontent.com/$OwnerRepo/$Branch"

$checks = @{
  "config.json"     = "$raw/web/config.json"
  "fetch_tmdb.py"   = "$raw/scripts/fetch_tmdb.py"
  "workflow.yml"    = "$raw/.github/workflows/build-data.yml"
  "data.json"       = "$raw/data/data.json"
}

foreach ($k in $checks.Keys) {
  try {
    $c = Invoke-RestMethod $checks[$k] -TimeoutSec 30
    Log "OK GitHub raw $k loaded"
  } catch {
    Log "FAIL GitHub raw $k not accessible"
    throw
  }
}

# ------------------------------------------------------------------------------
# QA 2 — Workflow must run full pipeline
# ------------------------------------------------------------------------------
$wf = Invoke-RestMethod $checks["workflow.yml"]

$mustContain = @(
  "python scripts/run_pipeline_full.py",
  "download_tmdb_assets.py"
)

foreach ($m in $mustContain) {
  if ($wf -notmatch [regex]::Escape($m)) {
    Log "FAIL workflow missing: $m"
    throw
  }
}
Log "OK workflow includes full pipeline + asset download"

# ------------------------------------------------------------------------------
# QA 3 — data.json must NOT contain legacy paths
# ------------------------------------------------------------------------------
$data = Invoke-RestMethod $checks["data.json"]

$legacy = "/assets/images/tmdb/"
$jsonText = (Invoke-RestMethod $checks["data.json"] -Raw)

if ($jsonText -match [regex]::Escape($legacy)) {
  Log "FAIL data.json still contains legacy paths"
  throw
}
Log "OK data.json contains canonical asset paths only"

# ------------------------------------------------------------------------------
# QA 4 — Every referenced asset must exist in repo
# ------------------------------------------------------------------------------
$missing = @()

function CheckPath($p) {
  if (-not $p) { return }
  $fs = Join-Path $Repo ($p.TrimStart("/") -replace "/", "\")
  if (-not (Test-Path $fs)) {
    $script:missing += $p
  }
}

foreach ($s in $data.shows) {
  CheckPath $s.poster_local
  CheckPath $s.backdrop_local
  foreach ($se in $s.seasons) {
    CheckPath $se.poster_local
    foreach ($ep in $se.episodes) {
      CheckPath $ep.still_local
    }
  }
}

foreach ($m in $data.movies) {
  CheckPath $m.poster_local
  CheckPath $m.backdrop_local
}

if ($missing.Count -gt 0) {
  Log "FAIL missing assets referenced in data.json = $($missing.Count)"
  $missing | Select-Object -First 25 | ForEach-Object { Log "MISSING $_" }
  throw
}

Log "OK all data.json assets exist in repo"

# ------------------------------------------------------------------------------
Log "SUCCESS — GitHub pipeline is authoritative and stable"
Log "END QA"
