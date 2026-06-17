<#
FILE: tools/install_local_launcher.ps1
VERSION: 1.0.0
UPDATED: 2026-06-17T00:00:00Z
CHANGE NOTES:
- Register the repo root in the current user's PATH so run_local_servers.bat
  resolves from any new PowerShell or Command Prompt window.
- Install a user command shim when a current user bin directory is already on PATH,
  so inherited shells can resolve the command immediately.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path.TrimEnd("\", "/")
$launcher = Join-Path $repoRoot "run_local_servers.bat"

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Missing canonical launcher: $launcher"
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $userPath) {
    $userPath = ""
}

$parts = $userPath -split ";" |
    Where-Object { $_ -and $_.Trim() } |
    ForEach-Object { $_.Trim().TrimEnd("\", "/") }

$alreadyRegistered = $parts | Where-Object {
    [string]::Equals($_, $repoRoot, [System.StringComparison]::OrdinalIgnoreCase)
} | Select-Object -First 1

if (-not $alreadyRegistered) {
    $newParts = @($parts) + $repoRoot
    $newPath = ($newParts | Where-Object { $_ -and $_.Trim() }) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added repo root to current user PATH: $repoRoot"
} else {
    Write-Host "Repo root already registered in current user PATH: $repoRoot"
}

$shimRoots = @(
    (Join-Path $env:USERPROFILE "SHELL\bin"),
    (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) }

$processPathParts = ([Environment]::GetEnvironmentVariable("Path", "Process") -split ";") |
    Where-Object { $_ -and $_.Trim() } |
    ForEach-Object { $_.Trim().TrimEnd("\", "/") }

$shimRoot = $null
foreach ($candidate in $shimRoots) {
    $candidateClean = $candidate.TrimEnd("\", "/")
    $onCurrentPath = $processPathParts | Where-Object {
        [string]::Equals($_, $candidateClean, [System.StringComparison]::OrdinalIgnoreCase)
    } | Select-Object -First 1
    if (-not $onCurrentPath) { continue }
    try {
        $testPath = Join-Path $candidateClean ("mytv_launcher_test_" + [guid]::NewGuid().ToString("N") + ".tmp")
        Set-Content -LiteralPath $testPath -Value "test" -Encoding ASCII -ErrorAction Stop
        Remove-Item -LiteralPath $testPath -Force -ErrorAction SilentlyContinue
        $shimRoot = $candidateClean
        break
    } catch {
        $shimRoot = $null
    }
}

if ($shimRoot) {
    $shimPath = Join-Path $shimRoot "run_local_servers.bat"
    $shimBody = @"
@echo off
call "$launcher" %*
"@
    $currentShim = if (Test-Path -LiteralPath $shimPath) { Get-Content -Raw -LiteralPath $shimPath } else { "" }
    if ($currentShim -ne $shimBody) {
        Set-Content -LiteralPath $shimPath -Value $shimBody -Encoding ASCII -NoNewline
        Write-Host "Installed command shim: $shimPath"
    } else {
        Write-Host "Command shim already current: $shimPath"
    }
}

$processPath = [Environment]::GetEnvironmentVariable("Path", "Process")
$processParts = @($processPath -split ";") + $repoRoot
$dedupedProcessParts = New-Object System.Collections.Generic.List[string]
foreach ($part in $processParts) {
    $clean = [string]$part
    $clean = $clean.Trim()
    if (-not $clean) { continue }
    $exists = $false
    foreach ($kept in $dedupedProcessParts) {
        if ([string]::Equals($kept.TrimEnd("\", "/"), $clean.TrimEnd("\", "/"), [System.StringComparison]::OrdinalIgnoreCase)) {
            $exists = $true
            break
        }
    }
    if (-not $exists) {
        $dedupedProcessParts.Add($clean) | Out-Null
    }
}
[Environment]::SetEnvironmentVariable("Path", ($dedupedProcessParts -join ";"), "Process")

$resolved = Get-Command "run_local_servers.bat" -ErrorAction Stop
if ([string]::Equals($resolved.Source, $launcher, [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "Verified command: run_local_servers.bat -> $($resolved.Source)"
} elseif ($shimRoot -and [string]::Equals($resolved.Source, (Join-Path $shimRoot "run_local_servers.bat"), [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "Verified command shim: run_local_servers.bat -> $($resolved.Source)"
} else {
    throw "run_local_servers.bat resolved to '$($resolved.Source)' instead of '$launcher'"
}

Write-Host "Open a new PowerShell window to use the command from any folder."
