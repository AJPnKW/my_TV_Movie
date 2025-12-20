$root = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"

$old = Join-Path $root "image"
$new = Join-Path $root "assets"

# Mapping of old → new folders
$map = @{
    "posters"    = "posters"
    "backdrops"  = "backdrops"
    "stills"     = "stills"
    "logos"      = "logos"
    "icons"      = "icons"
    "fallback"   = "fallback"
    "collections"= "collections"
}

Write-Host "Starting asset migration..." -ForegroundColor Cyan

foreach ($key in $map.Keys) {
    $oldPath = Join-Path $old $key
    $newPath = Join-Path $new $map[$key]

    if (Test-Path $oldPath) {
        if (-not (Test-Path $newPath)) {
            New-Item -ItemType Directory -Path $newPath | Out-Null
        }

        Get-ChildItem -Path $oldPath -File -Recurse | ForEach-Object {
            $dest = Join-Path $newPath $_.Name
            Move-Item -Path $_.FullName -Destination $dest -Force
            Write-Host "Moved: $($_.FullName) → $dest"
        }
    }
}

Write-Host "Migration complete." -ForegroundColor Green
