# FILE: scripts/media_cleanup_common.ps1
# VERSION: v0.6.4
# UPDATED: 2026-05-11
# PURPOSE: Shared, location-independent helper for Media Cleanup Hub scripts.
$ErrorActionPreference = "Stop"

function Get-MediaCleanupRepoRoot {
    $Fixed = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
    if (Test-Path -LiteralPath (Join-Path $Fixed "tools\media_renamer\media_cleanup_pipeline.py")) { return $Fixed }
    $Here = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Candidate = Resolve-Path -LiteralPath (Join-Path $Here "..") -ErrorAction SilentlyContinue
    if ($Candidate -and (Test-Path -LiteralPath (Join-Path $Candidate.Path "tools\media_renamer\media_cleanup_pipeline.py"))) { return $Candidate.Path }
    throw "Cannot find my_TV_Movie repo root. Expected $Fixed"
}

function Get-MediaCleanupPython {
    param([string]$RepoRoot)
    $Venv = Join-Path $RepoRoot ".venv_media_cleanup\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $Venv)) {
        $Py = Get-Command py -ErrorAction SilentlyContinue
        if (-not $Py) { throw "Python launcher 'py' was not found." }
        $Result = Invoke-NativeProcess -FilePath $Py.Source -Arguments @("-3.12", "-m", "venv", (Join-Path $RepoRoot ".venv_media_cleanup")) -LogPath $null
        if ($Result.ExitCode -ne 0) { throw "Could not create Python 3.12 venv: $($Result.Output)" }
    }
    if (-not (Test-Path -LiteralPath $Venv)) { throw "Python venv was not created at $Venv" }
    return $Venv
}

function New-CleanUtf8Writer {
    param([string]$Path)
    $Dir = Split-Path -Parent $Path
    if ($Dir) { New-Item -ItemType Directory -Force -Path $Dir | Out-Null }
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    return New-Object System.IO.StreamWriter($Path, $false, $Encoding)
}

function Write-CleanLog {
    param([string]$Path, [string]$Message)
    $Dir = Split-Path -Parent $Path
    if ($Dir) { New-Item -ItemType Directory -Force -Path $Dir | Out-Null }
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    $Clean = ($Message -replace "`0", "")
    [System.IO.File]::AppendAllText($Path, $Clean + [Environment]::NewLine, $Encoding)
}

function Invoke-NativeProcess {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [string]$LogPath
    )
    $Psi = New-Object System.Diagnostics.ProcessStartInfo
    $Psi.FileName = $FilePath
    foreach ($Arg in $Arguments) { [void]$Psi.ArgumentList.Add($Arg) }
    $Psi.UseShellExecute = $false
    $Psi.RedirectStandardOutput = $true
    $Psi.RedirectStandardError = $true
    $Psi.CreateNoWindow = $true
    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $Psi
    [void]$Process.Start()
    $StdOut = $Process.StandardOutput.ReadToEnd()
    $StdErr = $Process.StandardError.ReadToEnd()
    $Process.WaitForExit()
    $Output = (($StdOut, $StdErr) -join [Environment]::NewLine) -replace "`0", ""
    if ($LogPath) { Write-CleanLog -Path $LogPath -Message $Output }
    return [pscustomobject]@{ ExitCode = $Process.ExitCode; Output = $Output }
}

function Get-MediaCleanupPipelineRepoArg {
    param([string]$Python, [string]$PipelinePath, [string]$LogPath)
    $Help = Invoke-NativeProcess -FilePath $Python -Arguments @($PipelinePath, "-h") -LogPath $LogPath
    if ($Help.Output -match "--repo-root") { return "--repo-root" }
    if ($Help.Output -match "--repo") { return "--repo" }
    throw "Could not determine repo argument from media_cleanup_pipeline.py -h"
}

function Invoke-MediaCleanupPipeline {
    param(
        [Parameter(Mandatory=$true)][ValidateSet("plan", "apply")][string]$Mode,
        [Parameter(Mandatory=$true)][string]$RepoRoot,
        [Parameter(Mandatory=$true)][string]$MediaRoot,
        [Parameter(Mandatory=$true)][string]$LogPath
    )
    $Python = Get-MediaCleanupPython -RepoRoot $RepoRoot
    $Pipeline = Join-Path $RepoRoot "tools\media_renamer\media_cleanup_pipeline.py"
    if (-not (Test-Path -LiteralPath $Pipeline)) { throw "Missing pipeline: $Pipeline" }
    $RepoArg = Get-MediaCleanupPipelineRepoArg -Python $Python -PipelinePath $Pipeline -LogPath $LogPath
    $Args = @($Pipeline, $Mode, $RepoArg, $RepoRoot, "--media-root", $MediaRoot)
    $Result = Invoke-NativeProcess -FilePath $Python -Arguments $Args -LogPath $LogPath
    if ($Result.ExitCode -ne 0) { throw "media_cleanup_pipeline.py $Mode failed with exit code $($Result.ExitCode). Log: $LogPath`n$($Result.Output)" }
    return $Result.Output
}

function Get-LatestMediaReportDir {
    param([string]$RepoRoot)
    $Root = Join-Path $RepoRoot "reports\media_renamer"
    if (-not (Test-Path -LiteralPath $Root)) { return $null }
    return Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
