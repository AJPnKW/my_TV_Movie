<#
FILE: tools/run_smoke_test.ps1
VERSION: 1.0.5
UPDATED: 2026-06-27T00:00:00Z
CHANGE NOTES:
- Start the static site server for the repo on port 8000 when needed.
- Start the inputs editor server on port 8787 when needed.
- Open the current app pages in Chrome, with Firefox as the only backup browser.
- Move the script param block before executable statements so PowerShell can parse it correctly.
- Treat 404 responses as unavailable so the editor API server is not skipped.
- Default browser launch to the local Inputs Editor only; use -AllTabs for smoke-test tabs.
- Verify the editor health endpoint belongs to this repo before reusing port 8787.
- Use the resolved Python command and wait for servers to become ready after launch.
#>

param(
    [ValidateSet("chrome", "firefox")]
    [string]$Browser = "chrome",
    [switch]$NoBrowser,
    [switch]$AllTabs
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

function ConvertTo-PowerShellSingleQuotedLiteral {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    return "'" + ($Value -replace "'", "''") + "'"
}

function Test-InputsEditorHealth {
    try {
        $response = Invoke-RestMethod -Uri $inputsHealthUrl -TimeoutSec 2
        if (-not $response.ok) { return $false }
        $healthRepoRoot = ""
        if ($null -ne $response.repo_root) {
            $healthRepoRoot = [string]$response.repo_root
        }
        return ($healthRepoRoot -and ([System.IO.Path]::GetFullPath($healthRepoRoot).TrimEnd('\') -ieq [System.IO.Path]::GetFullPath($repoRoot).TrimEnd('\')))
    } catch {
        return $false
    }
}

function Wait-HttpOk {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $Url) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Wait-InputsEditorHealth {
    param(
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-InputsEditorHealth) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
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
$pythonExe = $pythonCommand.Source
$pythonLiteral = ConvertTo-PowerShellSingleQuotedLiteral -Value $pythonExe
$repoRootLiteral = ConvertTo-PowerShellSingleQuotedLiteral -Value $repoRoot

$staticHealthUrl = "http://127.0.0.1:$staticPort/web/index.html"
if (-not (Test-HttpOk -Url $staticHealthUrl)) {
    $staticCommand = @"
Set-Location $repoRootLiteral
Write-Host 'Static site server: http://127.0.0.1:$staticPort/web/index.html'
& $pythonLiteral -m http.server $staticPort
"@
    Start-ServerWindow -Title "my_TV_Movie Static Server" -Command $staticCommand -WorkingDirectory $repoRoot
    if (-not (Wait-HttpOk -Url $staticHealthUrl)) {
        throw "Static site server did not become ready at $staticHealthUrl."
    }
}

$inputsServerPath = Join-Path $repoRoot "tools\inputs_editor\inputs_editor_server.py"
if (-not (Test-Path $inputsServerPath)) {
    throw "Missing required file: $inputsServerPath"
}

$inputsHealthUrl = "http://127.0.0.1:$inputsPort/api/health"
$inputsServerLiteral = ConvertTo-PowerShellSingleQuotedLiteral -Value $inputsServerPath
if (-not (Test-InputsEditorHealth)) {
    if (Test-HttpOk -Url $inputsHealthUrl) {
        throw "Port $inputsPort is serving a different process or repo. Stop that process, then run run_local_servers.bat again."
    }
    $inputsCommand = @"
Set-Location $repoRootLiteral
Write-Host 'Inputs editor server: http://127.0.0.1:$inputsPort/web/inputs_editor.html'
& $pythonLiteral $inputsServerLiteral --port $inputsPort
"@
    Start-ServerWindow -Title "my_TV_Movie Inputs Editor Server" -Command $inputsCommand -WorkingDirectory $repoRoot
    if (-not (Wait-InputsEditorHealth)) {
        throw "Inputs editor server did not become ready at $inputsHealthUrl."
    }
}

$urls = if ($AllTabs) { $staticUrls + $inputsUrl } else { @($inputsUrl) }
if (-not $NoBrowser) {
    $browserPath = Resolve-BrowserPath -Name $Browser
    Start-Process -FilePath $browserPath -ArgumentList $urls | Out-Null
}

if ($NoBrowser) {
    Write-Host "Servers are ready. Browser launch skipped."
} elseif ($AllTabs) {
    Write-Host "Opened smoke-test pages in $Browser."
} else {
    Write-Host "Opened Inputs Editor in $Browser. Use -AllTabs for the full smoke-test page set."
}
Write-Host "Static pages: $staticHealthUrl"
Write-Host "Inputs editor: $inputsUrl"
