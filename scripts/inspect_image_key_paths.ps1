# reports\inspect_image_key_paths.ps1
# Purpose: show where still_local/logo_local/profile_local actually exist in data.json
# Output: reports\image_key_paths.txt

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
Set-Location $repo

New-Item -ItemType Directory -Force ".\reports" | Out-Null
$outFile = ".\reports\image_key_paths.txt"

$d = Get-Content -Raw ".\data\data.json" | ConvertFrom-Json

function Walk($node, $path) {
    if ($null -eq $node) { return }

    # PSCustomObject (JSON object)
    if ($node -is [pscustomobject]) {
        foreach ($p in $node.PSObject.Properties) {
            $name = $p.Name
            $val  = $p.Value
            $pPath = if ($path) { "$path.$name" } else { $name }

            if ($name -in @("still_local","still_path","logo_local","logo_path","profile_local","profile_path","poster_local","poster_path","backdrop_local","backdrop_path")) {
                $preview = ""
                if ($val -is [string]) { $preview = $val }
                elseif ($val -ne $null) { $preview = ($val | Out-String).Trim() }

                [pscustomobject]@{
                    key   = $name
                    path  = $pPath
                    value = $preview
                } | Export-Csv -Path $script:tmpCsv -NoTypeInformation -Append
            }

            Walk $val $pPath
        }
        return
    }

    # Array
    if ($node -is [System.Collections.IEnumerable] -and -not ($node -is [string])) {
        $i = 0
        foreach ($item in $node) {
            Walk $item "$path[$i]"
            $i++
        }
        return
    }
}

# temp CSV then format into readable text
$tmpCsv = Join-Path $env:TEMP ("imgkeys_" + [guid]::NewGuid().ToString("N") + ".csv")
$script:tmpCsv = $tmpCsv
if (Test-Path $tmpCsv) { Remove-Item $tmpCsv -Force }

Walk $d ""

$rows = @()
if (Test-Path $tmpCsv) {
    $rows = Import-Csv $tmpCsv
    Remove-Item $tmpCsv -Force
}

# Summaries
$showsCount  = @($d.shows).Count
$moviesCount = @($d.movies).Count

$hasSeasons = $false
$hasEpisodes = $false
if ($showsCount -gt 0) {
    $firstShowWithSeasons = $d.shows | Where-Object { $_.PSObject.Properties.Name -contains "seasons" -and $_.seasons -and $_.seasons.Count -gt 0 } | Select-Object -First 1
    if ($null -ne $firstShowWithSeasons) {
        $hasSeasons = $true
        $firstSeason = $firstShowWithSeasons.seasons | Select-Object -First 1
        if ($firstSeason -and ($firstSeason.PSObject.Properties.Name -contains "episodes") -and $firstSeason.episodes -and $firstSeason.episodes.Count -gt 0) {
            $hasEpisodes = $true
        }
    }
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("repo_root=$repo")
$lines.Add("shows_count=$showsCount movies_count=$moviesCount")
$lines.Add("shows_have_seasons=$hasSeasons shows_have_episodes=$hasEpisodes")
$lines.Add("")
$lines.Add("=== KEY COUNTS (by key) ===")
$rows | Group-Object key | Sort-Object Count -Descending | ForEach-Object {
    $lines.Add(("{0,-14} {1,6}" -f $_.Name, $_.Count))
}
$lines.Add("")
$lines.Add("=== SAMPLE PATHS (first 30 per key) ===")
foreach ($k in @("still_local","logo_local","profile_local","poster_local","backdrop_local","still_path","logo_path","profile_path")) {
    $lines.Add("")
    $lines.Add("---- $k ----")
    $rows | Where-Object { $_.key -eq $k } | Select-Object -First 30 | ForEach-Object {
        $lines.Add(("{0} = {1}" -f $_.path, $_.value))
    }
}

$lines | Set-Content -Encoding UTF8 $outFile
Write-Host "WROTE $outFile"
