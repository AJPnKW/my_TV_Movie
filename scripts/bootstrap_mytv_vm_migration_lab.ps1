#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Dir { param([string]$Path) if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null } }
function Write-Log { param([string]$Message) $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message; Write-Host $line; Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8 }

$RepoRoot = (Get-Location).Path
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ".git"))) { throw "Run from repo root: C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie" }

$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = Join-Path $RepoRoot "reports\vm_migration_bootstrap\$RunStamp"
Ensure-Dir $RunRoot
$script:LogFile = Join-Path $RunRoot "execution.log.txt"
New-Item -ItemType File -Path $script:LogFile -Force | Out-Null

Write-Log "START SHELL-MED bootstrap"
Write-Log "RepoRoot=$RepoRoot"

$Dirs = @(
"deployment","deployment\vm_lab","deployment\vm_prod","deployment\postgres","deployment\api","deployment\webserver",
"deployment\media_library","deployment\wd_tv_live","deployment\trakt_sync","deployment\docs","deployment\logs","deployment\backups",
"codex_prompts","docs\project_history","docs\_archive\contracts","reports\vm_migration_bootstrap"
)
foreach ($d in $Dirs) { Ensure-Dir (Join-Path $RepoRoot $d) }

$evidence = [ordered]@{
 run_stamp=$RunStamp
 repo_root=$RepoRoot
 computer_name=$env:COMPUTERNAME
 user=$env:USERNAME
 powershell=$PSVersionTable.PSVersion.ToString()
 os=(Get-CimInstance Win32_OperatingSystem).Caption
 hyperv_present=[bool](Get-Command Get-VM -ErrorAction SilentlyContinue)
 virtualbox_present=[bool](Get-Command VBoxManage.exe -ErrorAction SilentlyContinue)
 git_present=[bool](Get-Command git -ErrorAction SilentlyContinue)
 python_present=[bool](Get-Command python -ErrorAction SilentlyContinue)
 docker_present=[bool](Get-Command docker -ErrorAction SilentlyContinue)
}
$evidence | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $RunRoot "environment_evidence.json") -Encoding UTF8

try { git status --short | Set-Content -LiteralPath (Join-Path $RunRoot "git_status_short.txt") -Encoding UTF8 } catch {}

@"
# my_TV_Movie deployment folder

Created by SHELL-MED bootstrap.

## Control model
- ChatGPT thread: control tower.
- Lime Green Codex: VM/deployment/infrastructure.
- Forest Green Codex: app/API/database/state logic.
- Medium Green PowerShell: command execution only.

## Target
- X1 Lab VM first.
- HP Production VM later.
- GitHub remains source control.
- PostgreSQL becomes primary write store.
- JSON remains static fallback/import/export.
- Image binaries remain files/assets by default; PostgreSQL stores metadata/paths.
"@ | Set-Content -LiteralPath (Join-Path $RepoRoot "deployment\README.md") -Encoding UTF8

@"
# VM migration bootstrap

## User narrative interpretation
The user wants this project moved from GitHub Pages limitations into a local VM lab and later HP production VM, with server-side API, PostgreSQL, watch-state persistence, Trakt/commercial sync, Media Library, WD TV Live/local network support, and repeatable deployment.

## Work split
- Lime Green Codex: infrastructure/deployment.
- Forest Green Codex: application/API/database.
- Medium Green PowerShell: commands only.
"@ | Set-Content -LiteralPath (Join-Path $RepoRoot "deployment\docs\vm_migration_bootstrap.md") -Encoding UTF8

@"
-- deployment/postgres/schema_draft.sql
CREATE TABLE IF NOT EXISTS media_items (
    media_item_id BIGSERIAL PRIMARY KEY,
    media_type TEXT NOT NULL CHECK (media_type IN ('show','season','episode','movie')),
    tmdb_id BIGINT,
    parent_tmdb_id BIGINT,
    season_number INTEGER,
    episode_number INTEGER,
    title TEXT NOT NULL,
    subtitle TEXT,
    release_date DATE,
    runtime_minutes INTEGER,
    source_json_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watch_state (
    watch_state_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    watch_status TEXT NOT NULL CHECK (watch_status IN ('unwatched','partial','watched')),
    in_watchlist BOOLEAN NOT NULL DEFAULT FALSE,
    is_favourite BOOLEAN NOT NULL DEFAULT FALSE,
    last_watched_at TIMESTAMPTZ,
    source TEXT NOT NULL DEFAULT 'local',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(media_item_id)
);

CREATE TABLE IF NOT EXISTS sync_queue (
    sync_queue_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    sync_target TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS media_files (
    media_file_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    location_profile TEXT NOT NULL,
    device_name TEXT,
    file_path TEXT NOT NULL,
    expected_filename TEXT,
    actual_filename TEXT,
    file_status TEXT NOT NULL DEFAULT 'unknown',
    ffprobe_status TEXT,
    duration_seconds NUMERIC,
    video_codec TEXT,
    audio_codec TEXT,
    container_format TEXT,
    repair_status TEXT,
    qa_json JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"@ | Set-Content -LiteralPath (Join-Path $RepoRoot "deployment\postgres\schema_draft.sql") -Encoding UTF8

@"
# deployment/api/api_contract_draft.md

Base: /api/v1

Endpoints:
- GET /health
- GET /media
- GET /media/{id}
- POST /media/import-json
- GET /watch-state
- PUT /watch-state/{media_item_id}
- GET /sync/queue
- POST /sync/trakt/pull
- POST /sync/trakt/push
- POST /sync/reconcile
- GET /media-library/inventory
- POST /media-library/scan
- POST /media-library/qa
- POST /media-library/remux
- GET /runtime/config
- PUT /runtime/profile

Rules:
- Server mode handles writes.
- Static JSON mode remains read-only fallback.
- All writes create audit/sync history.
- No silent loss of watch actions.
"@ | Set-Content -LiteralPath (Join-Path $RepoRoot "deployment\api\api_contract_draft.md") -Encoding UTF8

Write-Log "Wrote deployment scaffold, schema draft, API draft"
Write-Log "END SHELL-MED bootstrap"

@"
SHELL-MED bootstrap complete.

RunRoot:
$RunRoot

Next:
1. git add deployment docs codex_prompts scripts\bootstrap_mytv_vm_migration_lab.ps1
2. git commit -m "bootstrap mytv vm migration foundation"
3. git push origin main
4. Paste CODEX_LIME prompt into Lime Green Codex
5. After Lime completes, paste CODEX_FOREST prompt into Forest Green Codex
"@ | Set-Content -LiteralPath (Join-Path $RunRoot "summary.txt") -Encoding UTF8
