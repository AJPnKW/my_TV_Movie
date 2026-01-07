param(
    [string]$index = "web/heated-rivalry.html"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $index)) {
    throw "Cannot find $index"
}

# Backup
Copy-Item $index "$index.BAK" -Force

# Read file
$content = Get-Content $index -Raw

# Define the patch
$patch = @"
/* === SMART POSTER SIZING PATCH (AUTO‑BALANCED) === */
.hero {
  align-items: start;
}

.hero-poster .poster-shell {
  height: auto;
  max-height: 480px;
  width: auto;
  max-width: 100%;
  aspect-ratio: auto;
}

.hero-poster .poster-shell img {
  width: 100%;
  height: auto;
  object-fit: contain;
}

@media (min-width: 900px) {
  .hero {
    grid-auto-rows: 1fr;
  }
  .hero-poster .poster-shell {
    max-height: calc(100% - 20px);
  }
}
/* === END SMART POSTER SIZING PATCH === */
"@

# Insert patch right after .poster-shell img block
$marker = ".poster-shell img {"
$insertPos = $content.IndexOf($marker)

if ($insertPos -lt 0) {
    throw "Could not find .poster-shell img block in index.html"
}

# Find end of that block
$endBrace = $content.IndexOf("}", $insertPos)
if ($endBrace -lt 0) {
    throw "Could not find end of .poster-shell img block"
}

# Insert patch after the closing brace
$updated = $content.Insert($endBrace + 1, "`r`n$patch`r`n")

# Write updated file
Set-Content -Path $index -Value $updated -Encoding UTF8

Write-Host "Poster sizing patch applied successfully."
