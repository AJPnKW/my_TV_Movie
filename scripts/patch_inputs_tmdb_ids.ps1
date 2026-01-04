# ======================================================================
# [FILE]    scripts/patch_inputs_tmdb_ids.ps1
# [PROJECT] my_TV_Movie
# [PURPOSE] Patch known-bad TMDB ids in inputs/tv_list.txt
#           203397 -> 208397 (School Spirits)  (TMDB)
#           203755 -> 136311 (Shrinking)       (TMDB)
# [VERSION] v1.0.0
# [UPDATED] 2026-01-03
# ======================================================================

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$inFile   = Join-Path $repoRoot "inputs\tv_list.txt"
$logDir   = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$ts    = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$log   = Join-Path $logDir ("patch_inputs_tmdb_ids_{0}.log.txt" -f $ts)
$bak   = Join-Path $logDir ("tv_list.txt.{0}.bak" -f $ts)

function Log([string]$msg) {
  $line = ("{0} | {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg)
  $line | Tee-Object -FilePath $log -Append
}

Log "[patch_inputs_tmdb_ids] START repo_root=$repoRoot"
Log "[patch_inputs_tmdb_ids] input=$inFile"
Log "[patch_inputs_tmdb_ids] log=$log"

if (!(Test-Path -LiteralPath $inFile)) {
  Log "[patch_inputs_tmdb_ids] ERROR missing file: $inFile"
  throw "Missing file: $inFile"
}

Copy-Item -LiteralPath $inFile -Destination $bak -Force
Log "[patch_inputs_tmdb_ids] backup=$bak"

$before = Get-Content -LiteralPath $inFile -Raw -Encoding UTF8

# Replace whole-token occurrences (avoid partial matches)
$after = $before
$after = [regex]::Replace($after, '(?<!\d)203397(?!\d)', '208397')
$after = [regex]::Replace($after, '(?<!\d)203755(?!\d)', '136311')

if ($after -eq $before) {
  Log "[patch_inputs_tmdb_ids] NO CHANGE (ids not found) - leaving file untouched"
  Log "[patch_inputs_tmdb_ids] END"
  exit 0
}

Set-Content -LiteralPath $inFile -Value $after -Encoding UTF8
Log "[patch_inputs_tmdb_ids] PATCHED inputs/tv_list.txt"

# Report counts
$cnt_203397_before = ([regex]::Matches($before, '(?<!\d)203397(?!\d)')).Count
$cnt_203755_before = ([regex]::Matches($before, '(?<!\d)203755(?!\d)')).Count
$cnt_203397_after  = ([regex]::Matches($after , '(?<!\d)203397(?!\d)')).Count
$cnt_203755_after  = ([regex]::Matches($after , '(?<!\d)203755(?!\d)')).Count
$cnt_208397_after  = ([regex]::Matches($after , '(?<!\d)208397(?!\d)')).Count
$cnt_136311_after  = ([regex]::Matches($after , '(?<!\d)136311(?!\d)')).Count

Log ("[patch_inputs_tmdb_ids] 203397 before={0} after={1}" -f $cnt_203397_before, $cnt_203397_after)
Log ("[patch_inputs_tmdb_ids] 203755 before={0} after={1}" -f $cnt_203755_before, $cnt_203755_after)
Log ("[patch_inputs_tmdb_ids] 208397 after={0}" -f $cnt_208397_after)
Log ("[patch_inputs_tmdb_ids] 136311 after={0}" -f $cnt_136311_after)

Log "[patch_inputs_tmdb_ids] END"
Write-Host "DONE. Log: $log"
Write-Host "Backup: $bak"
