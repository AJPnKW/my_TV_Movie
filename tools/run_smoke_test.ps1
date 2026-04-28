<#
FILE: tools/run_smoke_test.ps1
VERSION: 1.0.3
UPDATED: 2026-04-28T00:00:00Z
CHANGE NOTES:
- Start the static site server for the repo on port 8000 when needed.
- Start the inputs editor server on port 8787 when needed.
- Open the current app pages in Chrome, with Firefox as the only backup browser.
- Move the script param block before executable statements so PowerShell can parse it correctly.
- Treat 404 responses as unavailable so the editor API server is not skipped.
#>

param(
    [ValidateSet("chrome", "firefox")]
    [string]$Browser = "chrome",
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$staticPort = 8000
$inputsPort = 8787

$staticUrls = @(
    "http://127.0.0.1:$staticPort/web/index.html",
    "http://127.0.0.1:$staticPort/web/calendar.html",
    "http://127.0.0.1:$staticPort/web/shows.html",
    "http://127.0.0.1:$staticPort/web/movies.html",
    "http://127.0.0.1:$staticPort/web/watch_me.html",
    "http://127.0.0.1:$staticPort/web/discover.html",
    "http://127.0.0.1:$staticPort/web/config.html",
    "http://127.0.0.1:$staticPort/web/inputs_editor.html"
)

$inputsUrl = "http://127.0.0.1:$inputsPort/web/inputs_editor.html"

function Test-HttpOk {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Start-ServerWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    Start-Process -FilePath "powershell.exe" -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -ArgumentList @(
        "-NoExit",
        "-EncodedCommand",
        $encoded
    ) | Out-Null
    Start-Sleep -Seconds 2
}

function Resolve-BrowserPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $candidates = if ($Name -eq "chrome") {
        @(
            "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
        )
    } else {
        @(
            "$env:ProgramFiles\Mozilla Firefox\firefox.exe",
            "${env:ProgramFiles(x86)}\Mozilla Firefox\firefox.exe"
        )
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    throw "Could not find $Name browser executable."
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw "Python was not found in PATH."
}

$staticHealthUrl = "http://127.0.0.1:$staticPort/web/index.html"
if (-not (Test-HttpOk -Url $staticHealthUrl)) {
    $staticCommand = @"
Set-Location '$repoRoot'
Write-Host 'Static site server: http://127.0.0.1:$staticPort/web/index.html'
python -m http.server $staticPort
"@
    Start-ServerWindow -Title "my_TV_Movie Static Server" -Command $staticCommand -WorkingDirectory $repoRoot
}

$inputsServerPath = Join-Path $repoRoot "tools\inputs_editor\inputs_editor_server.py"
if (-not (Test-Path $inputsServerPath)) {
    throw "Missing required file: $inputsServerPath"
}

$inputsHealthUrl = "http://127.0.0.1:$inputsPort/api/health"
if (-not (Test-HttpOk -Url $inputsHealthUrl)) {
    $inputsCommand = @"
Set-Location '$repoRoot'
Write-Host 'Inputs editor server: http://127.0.0.1:$inputsPort/web/inputs_editor.html'
python '$inputsServerPath' --port $inputsPort
"@
    Start-ServerWindow -Title "my_TV_Movie Inputs Editor Server" -Command $inputsCommand -WorkingDirectory $repoRoot
}

$urls = $staticUrls + $inputsUrl
if (-not $NoBrowser) {
    $browserPath = Resolve-BrowserPath -Name $Browser
    Start-Process -FilePath $browserPath -ArgumentList $urls | Out-Null
}

if ($NoBrowser) {
    Write-Host "Servers are ready. Browser launch skipped."
} else {
    Write-Host "Opened smoke-test pages in $Browser."
}
Write-Host "Static pages: $staticHealthUrl"
Write-Host "Inputs editor: $inputsUrl"
