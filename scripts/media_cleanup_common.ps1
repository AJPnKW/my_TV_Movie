# FILE: scripts/media_cleanup_common.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
# CHANGE NOTES:
# - Shared PowerShell helper for Media Cleanup scripts.
# - Uses safe native command execution across Windows PowerShell versions.
# - Uses approved verbs for PSScriptAnalyzer compatibility.
# - Writes clean UTF-8 logs and captures stdout/stderr without NativeCommandError noise.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MediaCleanupRepoRoot {
    $Current = (Get-Location).Path
    while ($Current) {
        if (Test-Path -LiteralPath (Join-Path $Current 'tools\media_renamer')) {
            return $Current
        }
        $Parent = Split-Path -Parent $Current
        if ([string]::IsNullOrWhiteSpace($Parent) -or $Parent -eq $Current) { break }
        $Current = $Parent
    }
    return 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
}

function Write-MediaCleanupLog {
    param(
        [Parameter(Mandatory=$true)][string]$LogPath,
        [Parameter(Mandatory=$true)][string]$Message
    )
    $Parent = Split-Path -Parent $LogPath
    if (-not (Test-Path -LiteralPath $Parent)) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
    $Line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding UTF8
    Write-Host $Line
}

function Get-MediaCleanupPython {
    param([Parameter(Mandatory=$true)][string]$RepoRoot)
    $VenvPython = Join-Path $RepoRoot '.venv_media_cleanup\Scripts\python.exe'
    if (Test-Path -LiteralPath $VenvPython) { return $VenvPython }

    $PreferredPython = 'C:\Users\andrew\_shell\.venv_py312\Scripts\python.exe'
    if (Test-Path -LiteralPath $PreferredPython) { return $PreferredPython }

    $UtilitiesPython = 'C:\Utilities\Python\3.12\python.exe'
    if (Test-Path -LiteralPath $UtilitiesPython) { return $UtilitiesPython }

    $PyLauncher = (Get-Command py.exe -ErrorAction SilentlyContinue)
    if ($null -ne $PyLauncher) {
        return $PyLauncher.Source
    }

    $PythonCommand = (Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($null -ne $PythonCommand) {
        return $PythonCommand.Source
    }

    throw 'Python 3.12 was not found. Install Python 3.12 or restore C:\Users\andrew\_shell\.venv_py312.'
}

function Join-MediaCleanupArgumentList {
    param([string[]]$ArgumentList)
    $Quoted = foreach ($Item in $ArgumentList) {
        if ($null -eq $Item) { continue }
        $Text = [string]$Item
        if ($Text -match '[\s"&|<>^]') {
            '"' + ($Text -replace '"', '\"') + '"'
        } else {
            $Text
        }
    }
    return ($Quoted -join ' ')
}

function Invoke-MediaCleanupNativeCommand {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string[]]$ArgumentList,
        [Parameter(Mandatory=$true)][string]$LogPath,
        [string]$WorkingDirectory = ''
    )

    if (-not (Test-Path -LiteralPath $FilePath) -and -not (Get-Command $FilePath -ErrorAction SilentlyContinue)) {
        throw "Executable not found: $FilePath"
    }

    if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        $WorkingDirectory = (Get-Location).Path
    }

    $TempBase = Join-Path ([System.IO.Path]::GetTempPath()) ('media_cleanup_' + [guid]::NewGuid().ToString('N'))
    $StdOut = $TempBase + '.stdout.log'
    $StdErr = $TempBase + '.stderr.log'
    $ArgumentsText = Join-MediaCleanupArgumentList -ArgumentList $ArgumentList

    Write-MediaCleanupLog -LogPath $LogPath -Message ('CMD: {0} {1}' -f $FilePath, $ArgumentsText)

    $Process = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentsText `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdOut `
        -RedirectStandardError $StdErr `
        -NoNewWindow `
        -PassThru `
        -Wait

    foreach ($OutputFile in @($StdOut, $StdErr)) {
        if (Test-Path -LiteralPath $OutputFile) {
            $Content = Get-Content -LiteralPath $OutputFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if (-not [string]::IsNullOrWhiteSpace($Content)) {
                $CleanContent = $Content -replace "`0", ''
                Add-Content -LiteralPath $LogPath -Value $CleanContent -Encoding UTF8
                Write-Host $CleanContent
            }
            Remove-Item -LiteralPath $OutputFile -Force -ErrorAction SilentlyContinue
        }
    }

    if ($Process.ExitCode -ne 0) {
        throw ('Command failed with exit code {0}: {1} {2}' -f $Process.ExitCode, $FilePath, $ArgumentsText)
    }

    return $Process.ExitCode
}

function Get-MediaCleanupPipelineRepoArgument {
    param([Parameter(Mandatory=$true)][string]$RepoRoot)
    $Pipeline = Join-Path $RepoRoot 'tools\media_renamer\media_cleanup_pipeline.py'
    if (-not (Test-Path -LiteralPath $Pipeline)) { return '--repo' }
    $Text = Get-Content -LiteralPath $Pipeline -Raw -Encoding UTF8
    if ($Text -match '--repo-root') { return '--repo-root' }
    return '--repo'
}

function Get-MediaCleanupLatestPlanDirectory {
    param([Parameter(Mandatory=$true)][string]$RepoRoot)
    $Root = Join-Path $RepoRoot 'reports\media_renamer'
    if (-not (Test-Path -LiteralPath $Root)) { return $null }
    return Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'scan_plan.json') } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-MediaCleanupPlanSummary {
    param([Parameter(Mandatory=$true)][string]$RepoRoot)
    $Plan = Get-MediaCleanupLatestPlanDirectory -RepoRoot $RepoRoot
    if ($null -eq $Plan) { return $null }
    $JsonPath = Join-Path $Plan.FullName 'scan_plan.json'
    $Payload = Get-Content -LiteralPath $JsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    return $Payload.summary
}
