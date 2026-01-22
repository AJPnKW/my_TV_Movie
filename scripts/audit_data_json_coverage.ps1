<#
FILE: scripts/audit_data_json_coverage.ps1
PROJECT: my_TV_Movie
VERSION: 1.0.0
UPDATED: 2026-01-22
PURPOSE:
  Audit data/data.json for:
   - structural integrity (movies, shows, seasons, episodes)
   - missing keys (including links + local asset path fields)
   - fail-fast defects (e.g., number_of_seasons>0 but seasons[] missing/empty)
OUTPUTS:
  out\qa_data_json_audit\<utc_stamp>\*
    - summary.txt
    - missing_movies.csv
    - missing_shows.csv
    - missing_seasons.csv
    - missing_episodes.csv
    - structural_defects.csv
NOTES:
  - Does not modify repo files.
  - Designed to surface "dropped" fields across pipeline changes.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-UtcStamp {
  return (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmssZ")
}

function New-Dir([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
  }
}

function Write-Text([string]$Path, [string[]]$Lines) {
  $Lines -join "`r`n" | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Has-Prop($obj, [string]$prop) {
  if ($null -eq $obj) { return $false }
  return ($obj.PSObject.Properties.Name -contains $prop)
}

function Get-Prop($obj, [string]$prop) {
  if (Has-Prop $obj $prop) { return $obj.$prop }
  return $null
}

function Missing-Fields($obj, [string[]]$required) {
  $missing = New-Object System.Collections.Generic.List[string]
  foreach ($f in $required) {
    if (-not (Has-Prop $obj $f)) { $missing.Add($f) | Out-Null; continue }
    $v = Get-Prop $obj $f
    if ($null -eq $v) { $missing.Add($f) | Out-Null; continue }
    if ($v -is [string] -and [string]::IsNullOrWhiteSpace($v)) { $missing.Add($f) | Out-Null; continue }
  }
  return $missing
}

function Ensure-Array($v) {
  if ($null -eq $v) { return @() }
  if ($v -is [System.Array]) { return $v }
  return @($v)
}

# ---- Repo paths ----
$repoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$dataJsonPath = Join-Path $repoRoot "data\data.json"
$outRoot = Join-Path $repoRoot "out\qa_data_json_audit"
$stamp = Get-UtcStamp
$outDir = Join-Path $outRoot $stamp
New-Dir $outDir

$logSummary = New-Object System.Collections.Generic.List[string]
$logSummary.Add("QA DATA.JSON AUDIT | utc=$stamp") | Out-Null
$logSummary.Add("repo_root=$repoRoot") | Out-Null
$logSummary.Add("data_json=$dataJsonPath") | Out-Null

if (-not (Test-Path -LiteralPath $dataJsonPath)) {
  throw "Missing file: $dataJsonPath"
}

# ---- Load JSON ----
$jsonRaw = Get-Content -LiteralPath $dataJsonPath -Raw -Encoding UTF8
$data = $jsonRaw | ConvertFrom-Json


# ---- Required fields (tune here only if your schema differs) ----
# NOTE: includes "local path" fields commonly dropped during refactors.
$reqMovie = @(
  "tmdb_id","title","poster_path","backdrop_path",
  "poster_local","backdrop_local",
  "links"
)
$reqMovieLinks = @("tmdb","vidsrc","videasy")

$reqShow = @(
  "tmdb_id","name","poster_path","backdrop_path",
  "poster_local","backdrop_local",
  "number_of_seasons","number_of_episodes",
  "seasons","links"
)
$reqShowLinks = @("tmdb","vidsrc","videasy")

$reqSeason = @(
  "tmdb_season_id","season_number","name","episode_count",
  "poster_path","poster_local",
  "episodes"
)

$reqEpisode = @(
  "tmdb_episode_id","episode_number","name",
  "air_date","runtime",
  "still_path","still_local",
  "links"
)
$reqEpisodeLinks = @("tmdb","vidsrc","videasy")

# ---- Collectors ----
$missingMovies = New-Object System.Collections.Generic.List[object]
$missingShows = New-Object System.Collections.Generic.List[object]
$missingSeasons = New-Object System.Collections.Generic.List[object]
$missingEpisodes = New-Object System.Collections.Generic.List[object]
$structuralDefects = New-Object System.Collections.Generic.List[object]

# ---- Helpers to record ----
function Add-MissingRow($list, $kind, $id, $title, $path, $missingFields) {
  $list.Add([pscustomobject]@{
    kind = $kind
    tmdb_id = $id
    title = $title
    json_path = $path
    missing_fields = ($missingFields -join "|")
  }) | Out-Null
}

function Add-Defect($kind, $id, $title, $path, $defect) {
  $structuralDefects.Add([pscustomobject]@{
    kind = $kind
    tmdb_id = $id
    title = $title
    json_path = $path
    defect = $defect
  }) | Out-Null
}

# ---- Audit movies ----
$movies = Ensure-Array (Get-Prop $data "movies")
$logSummary.Add(("movies_total={0}" -f $movies.Count)) | Out-Null

for ($i=0; $i -lt $movies.Count; $i++) {
  $m = $movies[$i]
  $mid = Get-Prop $m "tmdb_id"
  $mtitle = Get-Prop $m "title"
  $mpath = "$.movies[$i]"

  $miss = Missing-Fields $m $reqMovie
  if ($miss.Count -gt 0) { Add-MissingRow $missingMovies "movie" $mid $mtitle $mpath $miss }

  # links object checks
  if (Has-Prop $m "links") {
    $lnk = Get-Prop $m "links"
    $lmiss = Missing-Fields $lnk $reqMovieLinks
    if ($lmiss.Count -gt 0) { Add-MissingRow $missingMovies "movie.links" $mid $mtitle "$mpath.links" $lmiss }
  } else {
    Add-Defect "movie" $mid $mtitle $mpath "missing links object"
  }
}

# ---- Audit shows / seasons / episodes ----
$shows = Ensure-Array (Get-Prop $data "shows")
$logSummary.Add(("shows_total={0}" -f $shows.Count)) | Out-Null

$episodeTotal = 0
$seasonTotal = 0

for ($si=0; $si -lt $shows.Count; $si++) {
  $s = $shows[$si]
  $sid = Get-Prop $s "tmdb_id"
  $sname = Get-Prop $s "name"
  $spath = "$.shows[$si]"

  $miss = Missing-Fields $s $reqShow
  if ($miss.Count -gt 0) { Add-MissingRow $missingShows "show" $sid $sname $spath $miss }

  # fail-fast structural invariant: if number_of_seasons>0 then seasons must be non-empty
  $nos = Get-Prop $s "number_of_seasons"
  $seasons = Ensure-Array (Get-Prop $s "seasons")
  if (($nos -as [int]) -gt 0 -and $seasons.Count -eq 0) {
    Add-Defect "show" $sid $sname $spath "number_of_seasons>0 but seasons[] is missing/empty"
  }

  # show links checks
  if (Has-Prop $s "links") {
    $lnk = Get-Prop $s "links"
    $lmiss = Missing-Fields $lnk $reqShowLinks
    if ($lmiss.Count -gt 0) { Add-MissingRow $missingShows "show.links" $sid $sname "$spath.links" $lmiss }
  } else {
    Add-Defect "show" $sid $sname $spath "missing links object"
  }

  for ($sj=0; $sj -lt $seasons.Count; $sj++) {
    $seasonTotal++
    $sea = $seasons[$sj]
    $seaId = Get-Prop $sea "tmdb_season_id"
    $seaNum = Get-Prop $sea "season_number"
    $seaName = Get-Prop $sea "name"
    $seapath = "$spath.seasons[$sj]"

    $smiss = Missing-Fields $sea $reqSeason
    if ($smiss.Count -gt 0) { Add-MissingRow $missingSeasons "season" $seaId ("$sname S$seaNum $seaName") $seapath $smiss }

    $episodes = Ensure-Array (Get-Prop $sea "episodes")
    $ecount = Get-Prop $sea "episode_count"
    if (($ecount -as [int]) -gt 0 -and $episodes.Count -eq 0) {
      Add-Defect "season" $seaId ("$sname S$seaNum $seaName") $seapath "episode_count>0 but episodes[] is missing/empty"
    }

    for ($ei=0; $ei -lt $episodes.Count; $ei++) {
      $episodeTotal++
      $ep = $episodes[$ei]
      $epId = Get-Prop $ep "tmdb_episode_id"
      $epNum = Get-Prop $ep "episode_number"
      $epName = Get-Prop $ep "name"
      $eppath = "$seapath.episodes[$ei]"

      $emiss = Missing-Fields $ep $reqEpisode
      if ($emiss.Count -gt 0) { Add-MissingRow $missingEpisodes "episode" $epId ("$sname S$seaNum E$epNum $epName") $eppath $emiss }

      if (Has-Prop $ep "links") {
        $elnk = Get-Prop $ep "links"
        $elmiss = Missing-Fields $elnk $reqEpisodeLinks
        if ($elmiss.Count -gt 0) { Add-MissingRow $missingEpisodes "episode.links" $epId ("$sname S$seaNum E$epNum $epName") "$eppath.links" $elmiss }
      } else {
        Add-Defect "episode" $epId ("$sname S$seaNum E$epNum $epName") $eppath "missing links object"
      }
    }
  }
}

$logSummary.Add(("seasons_total={0}" -f $seasonTotal)) | Out-Null
$logSummary.Add(("episodes_total={0}" -f $episodeTotal)) | Out-Null

# ---- Write outputs ----
$summaryPath = Join-Path $outDir "summary.txt"
Write-Text $summaryPath ($logSummary.ToArray())

$missingMoviesPath   = Join-Path $outDir "missing_movies.csv"
$missingShowsPath    = Join-Path $outDir "missing_shows.csv"
$missingSeasonsPath  = Join-Path $outDir "missing_seasons.csv"
$missingEpisodesPath = Join-Path $outDir "missing_episodes.csv"
$defectsPath         = Join-Path $outDir "structural_defects.csv"

$missingMovies   | Export-Csv -LiteralPath $missingMoviesPath   -NoTypeInformation -Encoding UTF8
$missingShows    | Export-Csv -LiteralPath $missingShowsPath    -NoTypeInformation -Encoding UTF8
$missingSeasons  | Export-Csv -LiteralPath $missingSeasonsPath  -NoTypeInformation -Encoding UTF8
$missingEpisodes | Export-Csv -LiteralPath $missingEpisodesPath -NoTypeInformation -Encoding UTF8
$structuralDefects | Export-Csv -LiteralPath $defectsPath       -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "DONE: QA DATA.JSON AUDIT"
Write-Host ("OUT: {0}" -f $outDir)
Write-Host ("SUMMARY: {0}" -f $summaryPath)
Write-Host ""
Write-Host "FILES:"
Write-Host ("  {0}" -f $missingMoviesPath)
Write-Host ("  {0}" -f $missingShowsPath)
Write-Host ("  {0}" -f $missingSeasonsPath)
Write-Host ("  {0}" -f $missingEpisodesPath)
Write-Host ("  {0}" -f $defectsPath)
Write-Host ""
Read-Host "Press Enter"
