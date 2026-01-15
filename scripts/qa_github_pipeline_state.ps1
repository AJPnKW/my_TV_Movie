param(
  [string]$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie",
  [string]$Owner = "AJPnKW",
  [string]$Repo = "my_TV_Movie",
  [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

function NowStamp { (Get-Date).ToString("yyyyMMdd_HHmmss") }

$logDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir ("qa_github_pipeline_state." + (NowStamp) + ".log.txt")

# Tee everything to file + console
Start-Transcript -Path $logPath | Out-Null

try {
  Write-Host "=== QA START ==="
  Write-Host "RepoRoot : $RepoRoot"
  Write-Host "Remote   : $Owner/$Repo ($Branch)"
  Write-Host "Log      : $logPath"
  Write-Host ""

  # Local git status
  Write-Host "=== LOCAL GIT STATUS ==="
  git -C $RepoRoot status
  Write-Host ""

  # Raw URLs
  $baseRaw = "https://raw.githubusercontent.com/$Owner/$Repo/refs/heads/$Branch"
  $urlWorkflow = "$baseRaw/.github/workflows/build-data.yml"
  $urlConfig   = "$baseRaw/web/config.json"
  $urlData     = "$baseRaw/data/data.json"
  $urlDlScript = "$baseRaw/scripts/download_tmdb_assets.py"

  Write-Host "=== REMOTE URLS ==="
  Write-Host $urlWorkflow
  Write-Host $urlConfig
  Write-Host $urlData
  Write-Host $urlDlScript
  Write-Host ""

  function Get-RemoteText([string]$url) {
    (Invoke-WebRequest -UseBasicParsing -Uri $url).Content
  }

  # Fetch remote files
  Write-Host "=== FETCH REMOTE FILES ==="
  $remoteWorkflow = Get-RemoteText $urlWorkflow
  $remoteConfig   = Get-RemoteText $urlConfig
  $remoteData     = Get-RemoteText $urlData
  $remoteDlScript = Get-RemoteText $urlDlScript
  Write-Host "OK: downloaded workflow/config/data/downloader from GitHub raw"
  Write-Host ""

  # Parse remote JSONs
  $cfg = $remoteConfig | ConvertFrom-Json
  $data = $remoteData | ConvertFrom-Json

  # QA 1 — Workflow contains downloader step
  Write-Host "=== QA 1: WORKFLOW CONTAINS ASSET DOWNLOADER STEP ==="
  $hasDownloaderStep = $remoteWorkflow -match "download_tmdb_assets\.py"
  Write-Host ("build-data.yml contains download_tmdb_assets.py step: " + ($hasDownloaderStep ? "YES" : "NO"))
  if (-not $hasDownloaderStep) {
    Write-Host "FAIL: Add this step after run_pipeline_full.py:"
    Write-Host "  - name: Download TMDB assets"
    Write-Host "    run: python scripts/download_tmdb_assets.py"
  }
  Write-Host ""

  # QA 2 — Config folder mappings
  Write-Host "=== QA 2: CONFIG IMAGE FOLDERS ==="
  $folders = $cfg.image_cache.folders
  $keys = @("shows_poster","shows_backdrop","seasons_poster","episodes_stills","movies_poster","movies_backdrop")
  foreach ($k in $keys) {
    $v = $folders.$k
    Write-Host ("config image_cache.folders.{0} = {1}" -f $k, $v)
  }
  $badCfg = ($remoteConfig -match "/assets/images/tmdb") -or ($remoteConfig -match '"folders_legacy"') -or ($remoteConfig -match '"streaming_services"')
  Write-Host ("config contains legacy keys/paths (/assets/images/tmdb, folders_legacy, streaming_services): " + ($badCfg ? "YES" : "NO"))
  Write-Host ""

  # QA 3 — data.json path scheme + generated time + builder
  Write-Host "=== QA 3: DATA.JSON PATHS + BUILD METADATA ==="
  Write-Host ("data.meta.generated_utc = " + $data.meta.generated_utc)
  Write-Host ("data.meta.builder.script = " + $data.meta.builder.script)
  Write-Host ("data.meta.builder.version = " + $data.meta.builder.version)
  $hasLegacyPaths = $remoteData -match "/assets/images/tmdb/"
  Write-Host ("data.json contains /assets/images/tmdb/: " + ($hasLegacyPaths ? "YES" : "NO"))
  $hasAssetsCanonical = $remoteData -match '"/assets/(posters|backdrops|stills)/'
  Write-Host ("data.json contains canonical /assets/(posters|backdrops|stills)/: " + ($hasAssetsCanonical ? "YES" : "NO"))
  Write-Host ""

  # QA 4 — Local vs Remote quick diff (hash)
  Write-Host "=== QA 4: LOCAL VS REMOTE HASH (config/workflow) ==="
  function Sha256Text([string]$s) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($s)
    $sha = [Security.Cryptography.SHA256]::Create()
    ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
  }

  $localWorkflowPath = Join-Path $RepoRoot ".github\workflows\build-data.yml"
  $localConfigPath   = Join-Path $RepoRoot "web\config.json"

  if (Test-Path $localWorkflowPath) {
    $localWorkflow = Get-Content $localWorkflowPath -Raw
    Write-Host ("workflow sha256 local : " + (Sha256Text $localWorkflow))
    Write-Host ("workflow sha256 remote: " + (Sha256Text $remoteWorkflow))
  } else {
    Write-Host "workflow local file missing: $localWorkflowPath"
  }

  if (Test-Path $localConfigPath) {
    $localConfig = Get-Content $localConfigPath -Raw
    Write-Host ("config sha256 local : " + (Sha256Text $localConfig))
    Write-Host ("config sha256 remote: " + (Sha256Text $remoteConfig))
  } else {
    Write-Host "config local file missing: $localConfigPath"
  }

  Write-Host ""
  Write-Host "=== QA END ==="
}
finally {
  Stop-Transcript | Out-Null
  Write-Host "Wrote QA log: $logPath"
}
