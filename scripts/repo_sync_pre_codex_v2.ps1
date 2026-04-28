#requires -version 5.1
<#
FILE: repo_sync_pre_codex_v2.ps1
PURPOSE:
- Validate sync state for both project repos before multi-tab Codex work.
- Avoid fragile native-command pipelines and empty-string parameter failures.
- Write per-repo logs plus one shared summary bundle.
- Never reset dirty work or alter remotes.
- Only run git pull --ff-only origin main when the repo is on main, clean,
  and only behind origin/main.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:RepoPaths = @(
    'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie',
    'C:\Users\andrew\PROJECTS\GitHub\iptv_control_plane'
)

$script:BundleRoot = 'C:\Users\andrew\PROJECTS\GitHub\.ai_uploads'
$script:RunTimestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$script:BundleDir = Join-Path $script:BundleRoot ("repo_sync_pre_codex_{0}" -f $script:RunTimestamp)
$script:ZipPath = '{0}.zip' -f $script:BundleDir

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogPath,

        [AllowEmptyString()]
        [string]$Message = ''
    )

    Add-Content -LiteralPath $LogPath -Value $Message -Encoding UTF8
}

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogPath,

        [AllowEmptyString()]
        [string]$Title = ''
    )

    Write-Log -LogPath $LogPath -Message ''
    Write-Log -LogPath $LogPath -Message ('=' * 80)
    Write-Log -LogPath $LogPath -Message $Title
    Write-Log -LogPath $LogPath -Message ('=' * 80)
}

function New-RepoResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoName,

        [Parameter(Mandatory = $true)]
        [string]$RepoPath,

        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    return [ordered]@{
        repo                  = $RepoName
        path                  = $RepoPath
        branch                = ''
        head                  = ''
        working_tree          = 'unknown'
        remotes               = 'none'
        origin_main_status    = 'missing'
        origin_main_ahead     = ''
        origin_main_behind    = ''
        github_main_status    = 'missing'
        github_main_ahead     = ''
        github_main_behind    = ''
        fetch_state           = 'not_run'
        action_taken          = 'none'
        blocker               = ''
        recommendation        = ''
        log                   = $LogPath
    }
}

function Invoke-ProcessCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    $stdoutPath = Join-Path $env:TEMP ("repo_sync_stdout_{0}.txt" -f ([guid]::NewGuid().ToString('N')))
    $stderrPath = Join-Path $env:TEMP ("repo_sync_stderr_{0}.txt" -f ([guid]::NewGuid().ToString('N')))

    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $FilePath @ArgumentList 1> $stdoutPath 2> $stderrPath
        $exitCode = $LASTEXITCODE

        $stdout = if (Test-Path -LiteralPath $stdoutPath) {
            Get-Content -LiteralPath $stdoutPath -Raw -Encoding UTF8
        }
        else {
            ''
        }

        $stderr = if (Test-Path -LiteralPath $stderrPath) {
            Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8
        }
        else {
            ''
        }

        return [pscustomobject]@{
            ExitCode = $exitCode
            StdOut   = $stdout
            StdErr   = $stderr
        }
    }
    finally {
        Pop-Location

        foreach ($tempPath in @($stdoutPath, $stderrPath)) {
            if (Test-Path -LiteralPath $tempPath) {
                Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Invoke-GitCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$LogPath,

        [switch]$AllowFailure
    )

    $commandText = 'git ' + ($Arguments -join ' ')
    Write-Log -LogPath $LogPath -Message ("> {0}" -f $commandText)

    try {
        $result = Invoke-ProcessCapture -FilePath 'git' -ArgumentList $Arguments -WorkingDirectory $RepoPath
    }
    catch {
        Write-Log -LogPath $LogPath -Message ("PROCESS ERROR: {0}" -f $_.Exception.Message)
        if (-not $AllowFailure) {
            throw
        }

        return [pscustomobject]@{
            ExitCode = 1
            StdOut   = ''
            StdErr   = $_.Exception.Message
            Output   = $_.Exception.Message
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($result.StdOut)) {
        Write-Log -LogPath $LogPath -Message $result.StdOut.TrimEnd()
    }

    if (-not [string]::IsNullOrWhiteSpace($result.StdErr)) {
        Write-Log -LogPath $LogPath -Message $result.StdErr.TrimEnd()
    }

    if (($result.ExitCode -ne 0) -and (-not $AllowFailure)) {
        throw ("Git command failed ({0}): {1}" -f $result.ExitCode, $commandText)
    }

    return [pscustomobject]@{
        ExitCode = $result.ExitCode
        StdOut   = $result.StdOut
        StdErr   = $result.StdErr
        Output   = (($result.StdOut, $result.StdErr) -join [Environment]::NewLine).Trim()
    }
}

function Get-GitFirstLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$LogPath,

        [switch]$AllowFailure
    )

    $result = Invoke-GitCapture -RepoPath $RepoPath -Arguments $Arguments -LogPath $LogPath -AllowFailure:$AllowFailure
    $line = ''

    foreach ($candidate in @($result.StdOut, $result.StdErr)) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        $line = ($candidate -split "`r?`n" | Where-Object { $_.Trim().Length -gt 0 } | Select-Object -First 1)
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            break
        }
    }

    return [pscustomobject]@{
        ExitCode = $result.ExitCode
        Text     = if ($line) { $line.Trim() } else { '' }
    }
}

function Get-RemoteInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,

        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    $result = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('remote', '-v') -LogPath $LogPath -AllowFailure
    $map = [ordered]@{}

    foreach ($line in ($result.StdOut -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        if ($line -match '^(?<name>\S+)\s+(?<url>\S+)\s+\((?<kind>fetch|push)\)$') {
            $name = $Matches.name
            $kind = $Matches.kind
            $url = $Matches.url

            if (-not $map.Contains($name)) {
                $map[$name] = [ordered]@{
                    fetch = ''
                    push  = ''
                }
            }

            $map[$name][$kind] = $url
        }
    }

    return $map
}

function Format-RemoteSummary {
    param(
        $RemoteInfo
    )

    if ($null -eq $RemoteInfo -or $RemoteInfo.Count -eq 0) {
        return 'none'
    }

    $parts = foreach ($remoteName in $RemoteInfo.Keys) {
        $fetchUrl = $RemoteInfo[$remoteName].fetch
        $pushUrl = $RemoteInfo[$remoteName].push
        '{0}[fetch={1}; push={2}]' -f $remoteName, $fetchUrl, $pushUrl
    }

    return ($parts -join ' | ')
}

function Test-RemoteRefExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,

        [Parameter(Mandatory = $true)]
        [string]$RemoteRef,

        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    $verifyRef = 'refs/remotes/{0}' -f $RemoteRef
    $result = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('show-ref', '--verify', '--quiet', $verifyRef) -LogPath $LogPath -AllowFailure
    return ($result.ExitCode -eq 0)
}

function Get-AheadBehindStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,

        [Parameter(Mandatory = $true)]
        [string]$LocalRef,

        [Parameter(Mandatory = $true)]
        [string]$RemoteRef,

        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    $result = [ordered]@{
        local_ref  = $LocalRef
        remote_ref = $RemoteRef
        ahead      = ''
        behind     = ''
        status     = 'missing'
    }

    if (-not (Test-RemoteRefExists -RepoPath $RepoPath -RemoteRef $RemoteRef -LogPath $LogPath)) {
        return [pscustomobject]$result
    }

    $counts = Get-GitFirstLine -RepoPath $RepoPath -Arguments @('rev-list', '--left-right', '--count', ('{0}...{1}' -f $LocalRef, $RemoteRef)) -LogPath $LogPath -AllowFailure
    if ($counts.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($counts.Text)) {
        $result.status = 'error'
        return [pscustomobject]$result
    }

    $parts = $counts.Text -split '\s+'
    if ($parts.Count -lt 2) {
        $result.status = 'error'
        return [pscustomobject]$result
    }

    $result.ahead = $parts[0]
    $result.behind = $parts[1]

    if ($parts[0] -eq '0' -and $parts[1] -eq '0') {
        $result.status = 'synced'
    }
    elseif ([int]$parts[0] -eq 0 -and [int]$parts[1] -gt 0) {
        $result.status = 'behind'
    }
    elseif ([int]$parts[0] -gt 0 -and [int]$parts[1] -eq 0) {
        $result.status = 'ahead'
    }
    else {
        $result.status = 'diverged'
    }

    return [pscustomobject]$result
}

function Get-Recommendation {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$RepoResult
    )

    if ($RepoResult.blocker -eq 'repo_path_missing') {
        return 'fix missing repo path before any downstream work'
    }

    if ($RepoResult.blocker -eq 'not_git_repo') {
        return 'fix repo checkout before downstream work'
    }

    if ($RepoResult.fetch_state -eq 'fetch_failed') {
        return 'manual remote/fetch review required before downstream work'
    }

    if ($RepoResult.working_tree -eq 'dirty') {
        return 'do not pull or rebase here; preserve local changes and work from current checkout'
    }

    if ($RepoResult.origin_main_status -eq 'diverged' -or $RepoResult.github_main_status -eq 'diverged') {
        return 'manual branch reconciliation required before sync actions'
    }

    if ($RepoResult.origin_main_status -eq 'behind' -and $RepoResult.action_taken -ne 'pulled_ff_only_origin_main') {
        return 'repo is behind origin/main; update only after workspace is clean'
    }

    if ($RepoResult.origin_main_status -eq 'ahead') {
        return 'local commits exist; do not overwrite them'
    }

    if ($RepoResult.origin_main_status -eq 'synced' -or $RepoResult.github_main_status -eq 'synced') {
        return 'safe for downstream work on current checkout'
    }

    return 'review repo log for remote/ref specifics'
}

function Process-Repo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath
    )

    $repoName = Split-Path -Path $RepoPath -Leaf
    $logsDir = Join-Path $RepoPath 'logs'
    Ensure-Directory -Path $logsDir

    $logPath = Join-Path $logsDir ("repo_sync_pre_codex_v2_{0}.log.txt" -f $script:RunTimestamp)
    Set-Content -LiteralPath $logPath -Value ("START {0}" -f (Get-Date -Format 's')) -Encoding UTF8

    $repoResult = New-RepoResult -RepoName $repoName -RepoPath $RepoPath -LogPath $logPath

    try {
        Write-Section -LogPath $logPath -Title 'REPO VALIDATION'

        if (-not (Test-Path -LiteralPath $RepoPath)) {
            $repoResult.working_tree = 'missing'
            $repoResult.blocker = 'repo_path_missing'
            Write-Log -LogPath $logPath -Message ("ERROR: repo path missing: {0}" -f $RepoPath)
            return [pscustomobject]$repoResult
        }

        if (-not (Test-Path -LiteralPath (Join-Path $RepoPath '.git'))) {
            $repoResult.working_tree = 'not_git_repo'
            $repoResult.blocker = 'not_git_repo'
            Write-Log -LogPath $logPath -Message ("ERROR: .git missing: {0}" -f $RepoPath)
            return [pscustomobject]$repoResult
        }

        Write-Log -LogPath $logPath -Message ("repo_ok={0}" -f $RepoPath)

        Write-Section -LogPath $logPath -Title 'REMOTE URLS BEFORE FETCH'
        $remoteInfo = Get-RemoteInfo -RepoPath $RepoPath -LogPath $logPath
        $repoResult.remotes = Format-RemoteSummary -RemoteInfo $remoteInfo

        Write-Section -LogPath $logPath -Title 'FETCH ALL REMOTES'
        $fetchResult = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('fetch', '--all', '--prune') -LogPath $logPath -AllowFailure
        $repoResult.fetch_state = if ($fetchResult.ExitCode -eq 0) { 'ok' } else { 'fetch_failed' }

        Write-Section -LogPath $logPath -Title 'POST-FETCH STATE'
        $branchLine = Get-GitFirstLine -RepoPath $RepoPath -Arguments @('branch', '--show-current') -LogPath $logPath -AllowFailure
        $repoResult.branch = if ([string]::IsNullOrWhiteSpace($branchLine.Text)) { 'DETACHED' } else { $branchLine.Text }

        $headLine = Get-GitFirstLine -RepoPath $RepoPath -Arguments @('rev-parse', 'HEAD') -LogPath $logPath -AllowFailure
        $repoResult.head = $headLine.Text

        $statusResult = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('status', '--porcelain') -LogPath $logPath -AllowFailure
        $repoResult.working_tree = if ([string]::IsNullOrWhiteSpace($statusResult.StdOut)) { 'clean' } else { 'dirty' }

        Write-Log -LogPath $logPath -Message ("branch={0}" -f $repoResult.branch)
        Write-Log -LogPath $logPath -Message ("head={0}" -f $repoResult.head)
        Write-Log -LogPath $logPath -Message ("working_tree={0}" -f $repoResult.working_tree)
        Write-Log -LogPath $logPath -Message ("fetch_state={0}" -f $repoResult.fetch_state)

        Write-Section -LogPath $logPath -Title 'AHEAD BEHIND STATUS'
        $originStatus = Get-AheadBehindStatus -RepoPath $RepoPath -LocalRef 'HEAD' -RemoteRef 'origin/main' -LogPath $logPath
        $githubStatus = Get-AheadBehindStatus -RepoPath $RepoPath -LocalRef 'HEAD' -RemoteRef 'github/main' -LogPath $logPath

        $repoResult.origin_main_status = $originStatus.status
        $repoResult.origin_main_ahead = $originStatus.ahead
        $repoResult.origin_main_behind = $originStatus.behind
        $repoResult.github_main_status = $githubStatus.status
        $repoResult.github_main_ahead = $githubStatus.ahead
        $repoResult.github_main_behind = $githubStatus.behind

        Write-Log -LogPath $logPath -Message ("remotes={0}" -f $repoResult.remotes)
        Write-Log -LogPath $logPath -Message ("origin/main={0}; ahead={1}; behind={2}" -f $repoResult.origin_main_status, $repoResult.origin_main_ahead, $repoResult.origin_main_behind)
        Write-Log -LogPath $logPath -Message ("github/main={0}; ahead={1}; behind={2}" -f $repoResult.github_main_status, $repoResult.github_main_ahead, $repoResult.github_main_behind)

        if ($repoResult.fetch_state -eq 'fetch_failed') {
            $repoResult.blocker = 'fetch_failed'
        }

        $canPullOriginMain = (
            $repoResult.fetch_state -eq 'ok' -and
            $repoResult.branch -eq 'main' -and
            $repoResult.working_tree -eq 'clean' -and
            $repoResult.origin_main_status -eq 'behind' -and
            $repoResult.origin_main_ahead -eq '0'
        )

        if ($canPullOriginMain) {
            Write-Section -LogPath $logPath -Title 'AUTO FAST FORWARD PULL ORIGIN MAIN'
            $pullResult = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('pull', '--ff-only', 'origin', 'main') -LogPath $logPath -AllowFailure

            if ($pullResult.ExitCode -eq 0) {
                $repoResult.action_taken = 'pulled_ff_only_origin_main'

                $repoResult.head = (Get-GitFirstLine -RepoPath $RepoPath -Arguments @('rev-parse', 'HEAD') -LogPath $logPath -AllowFailure).Text
                $originStatus = Get-AheadBehindStatus -RepoPath $RepoPath -LocalRef 'HEAD' -RemoteRef 'origin/main' -LogPath $logPath
                $githubStatus = Get-AheadBehindStatus -RepoPath $RepoPath -LocalRef 'HEAD' -RemoteRef 'github/main' -LogPath $logPath

                $repoResult.origin_main_status = $originStatus.status
                $repoResult.origin_main_ahead = $originStatus.ahead
                $repoResult.origin_main_behind = $originStatus.behind
                $repoResult.github_main_status = $githubStatus.status
                $repoResult.github_main_ahead = $githubStatus.ahead
                $repoResult.github_main_behind = $githubStatus.behind
            }
            else {
                $repoResult.action_taken = 'pull_attempt_failed'
                $repoResult.blocker = 'ff_pull_failed'
            }
        }

        Write-Section -LogPath $logPath -Title 'FINAL REMOTE URLS'
        $finalRemoteInfo = Get-RemoteInfo -RepoPath $RepoPath -LogPath $logPath
        $repoResult.remotes = Format-RemoteSummary -RemoteInfo $finalRemoteInfo
        $repoResult.recommendation = Get-Recommendation -RepoResult $repoResult
        Write-Log -LogPath $logPath -Message ("recommendation={0}" -f $repoResult.recommendation)
        Write-Log -LogPath $logPath -Message ("DONE {0}" -f (Get-Date -Format 's'))

        return [pscustomobject]$repoResult
    }
    catch {
        Write-Section -LogPath $logPath -Title 'UNHANDLED ERROR'
        Write-Log -LogPath $logPath -Message $_.Exception.ToString()
        $repoResult.working_tree = 'error'
        $repoResult.blocker = if ($_.Exception.Message) { $_.Exception.Message } else { 'unhandled_error' }
        $repoResult.recommendation = 'manual script/log review required'
        return [pscustomobject]$repoResult
    }
    finally {
        Write-Log -LogPath $logPath -Message ''
    }
}

function Write-SummaryBundle {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Rows
    )

    Ensure-Directory -Path $script:BundleRoot
    Ensure-Directory -Path $script:BundleDir

    foreach ($row in $Rows) {
        if (Test-Path -LiteralPath $row.log) {
            $bundleLogName = '{0}_{1}' -f $row.repo, [IO.Path]::GetFileName($row.log)
            Copy-Item -LiteralPath $row.log -Destination (Join-Path $script:BundleDir $bundleLogName) -Force
        }
    }

    $summaryPath = Join-Path $script:BundleDir 'repo_sync_summary.txt'
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add(("repo_sync_pre_codex_v2 run: {0}" -f (Get-Date -Format 's')))
    $lines.Add(("bundle_dir={0}" -f $script:BundleDir))
    $lines.Add(("zip_path={0}" -f $script:ZipPath))
    $lines.Add('')

    foreach ($row in $Rows) {
        $lines.Add(('[{0}]' -f $row.repo))
        $lines.Add(("path={0}" -f $row.path))
        $lines.Add(("branch={0}" -f $row.branch))
        $lines.Add(("head={0}" -f $row.head))
        $lines.Add(("working_tree={0}" -f $row.working_tree))
        $lines.Add(("remotes={0}" -f $row.remotes))
        $lines.Add(("fetch_state={0}" -f $row.fetch_state))
        $lines.Add(("origin/main status={0}; ahead={1}; behind={2}" -f $row.origin_main_status, $row.origin_main_ahead, $row.origin_main_behind))
        $lines.Add(("github/main status={0}; ahead={1}; behind={2}" -f $row.github_main_status, $row.github_main_ahead, $row.github_main_behind))
        $lines.Add(("action_taken={0}" -f $row.action_taken))
        $lines.Add(("blocker={0}" -f $row.blocker))
        $lines.Add(("recommendation={0}" -f $row.recommendation))
        $lines.Add(("log={0}" -f $row.log))
        $lines.Add('')
    }

    Set-Content -LiteralPath $summaryPath -Value $lines -Encoding UTF8

    if (Test-Path -LiteralPath $script:ZipPath) {
        Remove-Item -LiteralPath $script:ZipPath -Force
    }

    Compress-Archive -Path (Join-Path $script:BundleDir '*') -DestinationPath $script:ZipPath -Force

    return $summaryPath
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'git is not available on PATH'
}

$results = foreach ($repoPath in $script:RepoPaths) {
    Process-Repo -RepoPath $repoPath
}

$summaryFile = Write-SummaryBundle -Rows $results

Write-Host ''
Write-Host 'DONE'
Write-Host ("SUMMARY: {0}" -f $summaryFile)
Write-Host ("ZIP: {0}" -f $script:ZipPath)
