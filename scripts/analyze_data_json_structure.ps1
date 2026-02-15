<#
==============================================================================
[FILE]    scripts/analyze_data_json_structure.ps1
[PROJECT] my_TV_Movie
[ROLE]    Summarize data\data.json structure + size hotspots (no secrets)
[VERSION] v1.0.0
[UPDATED] 2026-02-02
==============================================================================
#>
#
# powershell -ExecutionPolicy Bypass -File .\scripts\analyze_data_json_structure.ps1
#

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param(
        [Parameter(Mandatory=$true)][string]$Message,
        [Parameter(Mandatory=$true)][string]$LogPath
    )
    $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line = "[$ts] $Message"
    Write-Host $line
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

function Get-TypeName {
    param($Value)
    if ($null -eq $Value) { return "null" }
    if ($Value -is [System.Collections.IDictionary]) { return "object" }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) { return "array" }
    return $Value.GetType().Name.ToLowerInvariant()
}

function Get-TopKeys {
    param($Obj)

    if ($null -eq $Obj) { return @() }

    # Hashtable / dictionary
    if ($Obj -is [System.Collections.IDictionary]) {
        return @($Obj.Keys | Sort-Object)
    }

    # PSCustomObject
    if ($Obj -is [psobject]) {
        return @($Obj.PSObject.Properties.Name | Sort-Object)
    }

    return @()
}


function Sample-Shape {
    param(
        [AllowNull()]
        $Value,
        [int]$Depth = 0,
        [int]$MaxDepth = 4
    )

    $t = Get-TypeName $Value
    if ($Depth -ge $MaxDepth) { return @{ type = $t } }

    if ($null -eq $Value) { return @{ type = "null" } }

    # IDictionary (hashtable)
    if ($Value -is [System.Collections.IDictionary]) {
        $out = @{ type = "object"; keys = @{} }
        foreach ($k in ($Value.Keys | Sort-Object)) {
            $out.keys[$k] = Sample-Shape -Value $Value[$k] -Depth ($Depth+1) -MaxDepth $MaxDepth
        }
        return $out
    }

    # PSCustomObject
    if ($Value -is [psobject] -and -not ($Value -is [string])) {
        $props = @($Value.PSObject.Properties)
        if ($props.Length -gt 0) {
            $out = @{ type = "object"; keys = @{} }
            foreach ($p in ($props | Sort-Object Name)) {
                $out.keys[$p.Name] = Sample-Shape -Value $p.Value -Depth ($Depth+1) -MaxDepth $MaxDepth
            }
            return $out
        }
    }

    # Array / list
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $arr = @($Value)
        $out = @{ type = "array"; count = $arr.Length }
        if ($arr.Length -gt 0) {
            $out.sample0 = Sample-Shape -Value $arr[0] -Depth ($Depth+1) -MaxDepth $MaxDepth
        }
        return $out
    }

    return @{ type = $t }
}


function Estimate-JsonSize {
    param($Value)
    try {
        $json = $Value | ConvertTo-Json -Depth 100 -Compress
        return ($json.Length)
    } catch {
        return 0
    }
}

# ---------- Paths ----------
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $repoRoot "..") | Select-Object -ExpandProperty Path
$dataPath = Join-Path $repoRoot "data\data.json"
$logsDir  = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logPath = Join-Path $logsDir "analyze_data_json_structure_$stamp.log.txt"
$shapePath = Join-Path $logsDir "analyze_data_json_structure_$stamp.shape.json"

Write-Log -Message "--- START ---" -LogPath $logPath
Write-Log -Message "repo_root : $repoRoot" -LogPath $logPath
Write-Log -Message "data_json : $dataPath" -LogPath $logPath
Write-Log -Message "log      : $logPath" -LogPath $logPath
Write-Log -Message "shape    : $shapePath" -LogPath $logPath

if (-not (Test-Path $dataPath)) {
    Write-Log -Message "ERROR: data\data.json not found." -LogPath $logPath
    Write-Host "`nPress Enter to exit..."
    [void][Console]::ReadLine()
    exit 2
}

# ---------- Load JSON ----------
Write-Log -Message "Loading JSON..." -LogPath $logPath
$raw = Get-Content -Path $dataPath -Raw -Encoding UTF8
$bytes = [System.Text.Encoding]::UTF8.GetByteCount($raw)
$mb = [Math]::Round($bytes / 1MB, 2)
Write-Log -Message "data.json size: $mb MB ($bytes bytes)" -LogPath $logPath

$data = $raw | ConvertFrom-Json

# ---------- Top-level summary ----------
$topKeys = Get-TopKeys $data
Write-Log -Message ("top_keys: " + ($topKeys -join ", ")) -LogPath $logPath

$shows = @($data.shows)
$movies = @($data.movies)
$errors = @($data.errors)

Write-Log -Message ("counts: shows={0} movies={1} errors={2}" -f $shows.Count, $movies.Count, $errors.Count) -LogPath $logPath

# ---------- ID coverage ----------
function Count-IdCoverage {
    param(
        [Parameter(Mandatory=$true)][array]$Items,
        [Parameter(Mandatory=$true)][string[]]$Fields
    )
    $out = @{}
    foreach ($f in $Fields) { $out[$f] = 0 }
    foreach ($it in $Items) {
        foreach ($f in $Fields) {
            if ($null -ne $it.$f -and ("" + $it.$f).Trim().Length -gt 0) {
                $out[$f]++
            }
        }
    }
    return $out
}

$movieIdFields = @("tmdb_id","trakt_id","imdb_id")
$showIdFields  = @("tmdb_id","trakt_id","imdb_id","tvdb_id")

$movieIds = Count-IdCoverage -Items $movies -Fields $movieIdFields
$showIds  = Count-IdCoverage -Items $shows  -Fields $showIdFields

Write-Log -Message "movie id coverage:" -LogPath $logPath
foreach ($k in $movieIdFields) {
    Write-Log -Message ("  {0,-10} {1,6}/{2}" -f $k, $movieIds[$k], $movies.Count) -LogPath $logPath
}
Write-Log -Message "show id coverage:" -LogPath $logPath
foreach ($k in $showIdFields) {
    Write-Log -Message ("  {0,-10} {1,6}/{2}" -f $k, $showIds[$k], $shows.Count) -LogPath $logPath
}

# ---------- “What is heavy?” quick sizing ----------
Write-Log -Message "Estimating section sizes (char length of JSON, compressed)..." -LogPath $logPath

$sections = @()
foreach ($k in $topKeys) {
    $val = $data.$k
    $sz = Estimate-JsonSize $val
    $sections += [PSCustomObject]@{ key=$k; approx_chars=$sz }
}
$sections = @($sections | Sort-Object approx_chars -Descending)

Write-Log -Message "top sections by size:" -LogPath $logPath
$take = [Math]::Min(10, @($sections).Count)
for ($i=0; $i -lt $take; $i++) {
    $row = $sections[$i]
    Write-Log -Message ("  {0,-18} {1,12:N0} chars" -f $row.key, $row.approx_chars) -LogPath $logPath
}

# ---------- Shape sample (writes a separate JSON file) ----------
Write-Log -Message "Writing shape sample (depth=4)..." -LogPath $logPath
$shape = Sample-Shape -Value $data -MaxDepth 4
($shape | ConvertTo-Json -Depth 50) | Set-Content -Path $shapePath -Encoding UTF8

Write-Log -Message "--- DONE ---" -LogPath $logPath
Write-Host "`nCompleted."
Write-Host "Log   : $logPath"
Write-Host "Shape : $shapePath"
Write-Host "`nPress Enter to exit..."
[void][Console]::ReadLine()
