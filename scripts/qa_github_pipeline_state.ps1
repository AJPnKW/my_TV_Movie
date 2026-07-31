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

Start-Transcript -Path $logPath | Out-Null

try {
  Write-Host "=== QA START ==="
  Write-Host "RepoRoot : $RepoRoot"
  Write-Host "Remote   : $Owner/$Repo ($Branch)"
  Write-Host "Log      : $logPath"
  Write-Host ""

  Write-Host "=== LOCAL GIT STATUS ==="
  git -C $RepoRoot status
  Write-Host ""

  $baseRaw = "https://raw.githubusercontent.com/$Owner/$Repo/refs/heads/$Branch"
  $urlWorkflow = "$baseRaw/.github/workflows/build-data.yml"
  $urlConfig   = "$baseRaw/web/config.json"
  $urlData     = "$baseRaw/data/data.json"

  Write-Host "=== REMOTE URLS ==="
  Write-Host $urlWorkflow
  Write-Host $urlConfig
  Write-Host $urlData
  Write-Host ""

  function Get-RemoteText([string]$url) {
    (Invoke-WebRequest -UseBasicParsing -Uri $url).Content
  }

  Write-Host "=== FETCH REMOTE FILES ==="
  $remoteWorkflow = Get-RemoteText $urlWorkflow
  $remoteConfig   = Get-RemoteText $urlConfig
  $remoteData     = Get-RemoteText $urlData
  Write-Host "OK: downloaded workflow/config/single runtime catalog from GitHub raw"
  Write-Host ""

  $cfg = $remoteConfig | ConvertFrom-Json
  $data = $remoteData | ConvertFrom-Json

  Write-Host "=== QA 1: WORKFLOW USES CANONICAL PIPELINE RUNNER ==="
  $hasCanonicalRunner = ($remoteWorkflow -match "run:\s+python scripts/run_pipeline_tmdb_trakt\.py")
  $commitsRuntimeArtifacts = ($remoteWorkflow -match "git add data/data\.json data/watch_state_queue\.json")
  if ($hasCanonicalRunner) {
    Write-Host "build-data.yml runs scripts/run_pipeline_tmdb_trakt.py: YES"
  } else {
    Write-Host "build-data.yml runs scripts/run_pipeline_tmdb_trakt.py: NO"
    Write-Host "FAIL: build-data.yml must run the canonical production pipeline runner"
  }
  if ($commitsRuntimeArtifacts) {
    Write-Host "build-data.yml commits single runtime catalog artifacts: YES"
  } else {
    Write-Host "build-data.yml commits single runtime catalog artifacts: NO"
    Write-Host "FAIL: build-data.yml must add data/data.json and data/watch_state_queue.json"
  }
  Write-Host ""

  Write-Host "=== QA 2: CONFIG IMAGE FOLDERS ==="
  $folders = $cfg.image_cache.folders
  $keys = @("shows_poster","shows_backdrop","seasons_poster","episodes_stills","movies_poster","movies_backdrop")
  foreach ($k in $keys) {
    $v = $folders.$k
    Write-Host ("config image_cache.folders.{0} = {1}" -f $k, $v)
  }

  $badCfg = (($remoteConfig -match "/assets/images/tmdb") -or ($remoteConfig -match '"folders_legacy"'))
  if ($badCfg) {
    Write-Host "config contains legacy keys/paths (/assets/images/tmdb, folders_legacy): YES"
  } else {
    Write-Host "config contains legacy keys/paths (/assets/images/tmdb, folders_legacy): NO"
  }
  Write-Host ""

  Write-Host "=== QA 3: DATA.JSON PATHS + BUILD METADATA ==="
  Write-Host ("data.meta.generated_utc = " + $data.meta.generated_utc)
  Write-Host ("data.meta.builder.script = " + $data.meta.builder.script)
  Write-Host ("data.meta.builder.version = " + $data.meta.builder.version)

  $hasLegacyPaths = ($remoteData -match "/assets/images/tmdb/")
  if ($hasLegacyPaths) {
    Write-Host "data.json contains /assets/images/tmdb/: YES"
  } else {
    Write-Host "data.json contains /assets/images/tmdb/: NO"
  }

  $hasAssetsCanonical = ($remoteData -match '"/assets/(posters|backdrops|stills)/')
  if ($hasAssetsCanonical) {
    Write-Host 'data.json contains canonical "/assets/(posters|backdrops|stills)/": YES'
  } else {
    Write-Host 'data.json contains canonical "/assets/(posters|backdrops|stills)/": NO'
  }
  Write-Host ("data.json shows = " + (($data.shows | Measure-Object).Count))
  Write-Host ("data.json movies = " + (($data.movies | Measure-Object).Count))
  Write-Host ""

  Write-Host "=== QA 4: LOCAL VS REMOTE HASH (config/workflow) ==="
  function Normalize-TextForHash([string]$s) {
    if ($null -eq $s) { return "" }
    return ($s -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd("`n") + "`n"
  }

  function Sha256Text([string]$s) {
    $normalized = Normalize-TextForHash $s
    $bytes = [Text.Encoding]::UTF8.GetBytes($normalized)
    $sha = [Security.Cryptography.SHA256]::Create()
    ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
  }

  $localWorkflowPath = Join-Path $RepoRoot ".github\workflows\build-data.yml"
  $localConfigPath   = Join-Path $RepoRoot "web\config.json"

  if (Test-Path $localWorkflowPath) {
    $localWorkflow = Get-Content $localWorkflowPath -Raw
    $localWorkflowHash = Sha256Text $localWorkflow
    $remoteWorkflowHash = Sha256Text $remoteWorkflow
    Write-Host ("workflow sha256 local : " + $localWorkflowHash)
    Write-Host ("workflow sha256 remote: " + $remoteWorkflowHash)
    Write-Host ("workflow normalized match: " + ($(if ($localWorkflowHash -eq $remoteWorkflowHash) { "YES" } else { "NO" })))
  } else {
    Write-Host "workflow local file missing: $localWorkflowPath"
  }

  if (Test-Path $localConfigPath) {
    $localConfig = Get-Content $localConfigPath -Raw
    $localConfigHash = Sha256Text $localConfig
    $remoteConfigHash = Sha256Text $remoteConfig
    Write-Host ("config sha256 local : " + $localConfigHash)
    Write-Host ("config sha256 remote: " + $remoteConfigHash)
    Write-Host ("config normalized match: " + ($(if ($localConfigHash -eq $remoteConfigHash) { "YES" } else { "NO" })))
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
