#requires -version 5.1
<#
FILE: repo_sync_pre_codex_v2.ps1
PURPOSE:
- Validate sync state for two repos before Codex work.
- Avoid fragile native command piping.
- Write per-repo logs and one shared summary bundle.
- Never modify remotes or reset local work.
- Only fast-forward pull origin/main when safe:
  * branch = main
  * working tree clean
  * local is behind origin/main only
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repos = @(
    'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie',
    'C:\Users\andrew\PROJECTS\GitHub\iptv_control_plane'
)

$bundleRoot = 'C:\Users\andrew\PROJECTS\GitHub\.ai_uploads'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$bundleDir = Join-Path $bundleRoot ("repo_sync_pre_codex_{0}" -f $timestamp)
$zipPath = "{0}.zip" -f $bundleDir

function Ensure-Directory {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Log {
    param(
        [Parameter(Mandatory)][string]$LogPath,
        [AllowEmptyString()][string]$Message = ''
    )

    Add-Content -LiteralPath $LogPath -Value $Message -Encoding UTF8
}

function Write-Section {
    param(
        [Parameter(Mandatory)][string]$LogPath,
        [Parameter(Mandatory)][string]$Title
    )

    Write-Log -LogPath $LogPath -Message ''
    Write-Log -LogPath $LogPath -Message ('=' * 80)
    Write-Log -LogPath $LogPath -Message $Title
    Write-Log -LogPath $LogPath -Message ('=' * 80)
}

function Invoke-GitCapture {
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$LogPath,
        [switch]$AllowFailure
    )

    $cmdText = 'git ' + ($Arguments -join ' ')
    $stdoutPath = Join-Path $env:TEMP ("git_stdout_{0}.txt" -f ([guid]::NewGuid().ToString('N')))
    $stderrPath = Join-Path $env:TEMP ("git_stderr_{0}.txt" -f ([guid]::NewGuid().ToString('N')))

    Write-Log -LogPath $LogPath -Message ("> {0}" -f $cmdText)

    Push-Location -LiteralPath $RepoPath
    try {
        try {
            & git @Arguments 1> $stdoutPath 2> $stderrPath
            $exitCode = $LASTEXITCODE
        }
        catch {
            $exitCode = if ($LASTEXITCODE) { $LASTEXITCODE } else { 1 }
            Write-Log -LogPath $LogPath -Message ("COMMAND ERROR: {0}" -f $_.Exception.Message)
            if (-not $AllowFailure) {
                throw
            }
        }

        $stdoutText = if (Test-Path -LiteralPath $stdoutPath) {
            Get-Content -LiteralPath $stdoutPath -Raw -Encoding UTF8
        }
        else {
            ''
        }

        $stderrText = if (Test-Path -LiteralPath $stderrPath) {
            Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8
        }
        else {
            ''
        }

        if (-not [string]::IsNullOrWhiteSpace($stdoutText)) {
            Write-Log -LogPath $LogPath -Message $stdoutText.TrimEnd()
        }

        if (-not [string]::IsNullOrWhiteSpace($stderrText)) {
            Write-Log -LogPath $LogPath -Message $stderrText.TrimEnd()
        }

        if (($exitCode -ne 0) -and (-not $AllowFailure)) {
            throw ("Git command failed ({0}): {1}" -f $exitCode, $cmdText)
        }

        return [pscustomobject]@{
            ExitCode = $exitCode
            StdOut   = $stdoutText
            StdErr   = $stderrText
            Output   = (($stdoutText, $stderrText) -join [Environment]::NewLine).Trim()
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

function Get-GitSingleLine {
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$LogPath,
        [switch]$AllowFailure
    )

    $result = Invoke-GitCapture -RepoPath $RepoPath -Arguments $Arguments -LogPath $LogPath -AllowFailure:$AllowFailure
    $line = ''

    if (-not [string]::IsNullOrWhiteSpace($result.StdOut)) {
        $line = (($result.StdOut -split "`r?`n") | Where-Object { $_.Trim().Length -gt 0 } | Select-Object -First 1)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($result.StdErr)) {
        $line = (($result.StdErr -split "`r?`n") | Where-Object { $_.Trim().Length -gt 0 } | Select-Object -First 1)
    }

    return [pscustomobject]@{
        ExitCode = $result.ExitCode
        Text     = if ($null -ne $line) { $line.Trim() } else { '' }
    }
}

function Get-RemoteMap {
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string]$LogPath
    )

    $remoteResult = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('remote', '-v') -LogPath $LogPath -AllowFailure
    $map = [ordered]@{}

    foreach ($line in ($remoteResult.StdOut -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $parts = $line -split '\s+'
        if ($parts.Count -lt 2) {
            continue
        }

        $name = $parts[0]
        $url = $parts[1]

        if (-not $map.Contains($name)) {
            $map[$name] = $url
        }
    }

    return $map
}

function Test-RemoteRefExists {
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string]$RemoteRef,
        [Parameter(Mandatory)][string]$LogPath
    )

    $refPath = "refs/remotes/{0}" -f $RemoteRef
    $result = Invoke-GitCapture -RepoPath $RepoPath -Arguments @('show-ref', '--verify', '--quiet', $refPath) -LogPath $LogPath -AllowFailure
    return ($result.ExitCode -eq 0)
}

function Get-AheadBehindStatus {
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string]$LocalRef,
        [Parameter(Mandatory)][string]$RemoteRef,
        [Parameter(Mandatory)][string]$LogPath
    )

    $status = [ordered]@{
        local_ref  = $LocalRef
        remote_ref = $RemoteRef
        ahead      = ''
        behind     = ''
        status     = 'missing'
    }

    if (-not (Test-RemoteRefExists -RepoPath $RepoPath -RemoteRef $RemoteRef -LogPath $LogPath)) {
        return [pscustomobject]$status
    }

    $localSha = (Get-GitSingleLine -RepoPath $RepoPath -Arguments @('rev-parse', $LocalRef) -LogPath $LogPath -AllowFailure).Text
    $remoteSha = (Get-GitSingleLine -RepoPath $RepoPath -Arguments @('rev-parse', $RemoteRef) -LogPath $LogPath -AllowFailure).Text

    if ([string]::IsNullOrWhiteSpace($localSha) -or [string]::IsNullOrWhiteSpace($remoteSha)) {
        return [pscustomobject]$status
    }

    $countsResult = Get-GitSingleLine -RepoPath $RepoPath -Arguments @('rev-list', '--left-right', '--count', ('{0}...{1}' -f $LocalRef, $RemoteRef)) -LogPath $LogPath -AllowFailure
    if ($countsResult.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($countsResult.Text)) {
        $status.status = 'error'
        return [pscustomobject]$status
    }

    $parts = $countsResult.Text -split '\s+'
    if ($parts.Count -lt 2) {
        $status.status = 'error'
        return [pscustomobject]$status
    }

    $status.ahead = $parts[0]
    $status.behind = $parts[1]

    if ($parts[0] -eq '0' -and $parts[1] -eq '0') {
        $status.status = 'synced'
    }
    elseif ([int]$parts[0] -gt 0 -and $parts[1] -eq '0') {
        $status.status = 'ahead'
    }
    elseif ($parts[0] -eq '0' -and [int]$parts[1] -gt 0) {
        $status.status = 'behind'
    }
    else {
        $status.status = 'diverged'
    }

    return [pscustomobject]$status
}

function Format-RemoteSummary {
    param($RemoteMap)

    if ($null -eq $RemoteMap -or $RemoteMap.Count -eq 0) {
        return 'none'
    }

    return (($RemoteMap.GetEnumerator() | ForEach-Object { '{0}={1}' -f $_.Key, $_.Value }) -join '; ')
}

Ensure-Directory -Path $bundleRoot
Ensure-Directory -Path $bundleDir

$summaryRows = New-Object System.Collections.Generic.List[object]

foreach ($repo in $repos) {
    $repoName = Split-Path -Path $repo -Leaf
    $logsDir = Join-Path $repo 'logs'
    $logPath = Join-Path $logsDir ("repo_sync_pre_codex_{0}.log.txt" -f $timestamp)

    try {
        Ensure-Directory -Path $logsDir
        Set-Content -LiteralPath $logPath -Value ("START {0}" -f (Get-Date -Format 's')) -Encoding UTF8

        if (-not (Test-Path -LiteralPath $repo)) {
            Write-Log -LogPath $logPath -Message ("ERROR: repo path missing: {0}" -f $repo)
            $summaryRows.Add([pscustomobject]@{
                repo                 = $repoName
                path                 = $repo
                branch               = ''
                head                 = ''
                working_tree         = 'missing_repo'
                remotes              = 'none'
                origin_main_status   = 'missing'
                origin_main_ahead    = ''
                origin_main_behind   = ''
                github_main_status   = 'missing'
                github_main_ahead    = ''
                github_main_behind   = ''
                action_taken         = 'none'
                blocker              = 'repo_path_missing'
                log                  = $logPath
            })
            continue
        }

        if (-not (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
            Write-Log -LogPath $logPath -Message ("ERROR: not a git repo: {0}" -f $repo)
            $summaryRows.Add([pscustomobject]@{
                repo                 = $repoName
                path                 = $repo
                branch               = ''
                head                 = ''
                working_tree         = 'not_git_repo'
                remotes              = 'none'
                origin_main_status   = 'missing'
                origin_main_ahead    = ''
                origin_main_behind   = ''
                github_main_status   = 'missing'
                github_main_ahead    = ''
                github_main_behind   = ''
                action_taken         = 'none'
                blocker              = 'not_git_repo'
                log                  = $logPath
            })
            continue
        }

        Write-Section -LogPath $logPath -Title 'REMOTE URLS BEFORE'
        $remoteMap = Get-RemoteMap -RepoPath $repo -LogPath $logPath

        Write-Section -LogPath $logPath -Title 'FETCH ALL'
        $fetchResult = Invoke-GitCapture -RepoPath $repo -Arguments @('fetch', '--all', '--prune') -LogPath $logPath -AllowFailure
        $fetchState = if ($fetchResult.ExitCode -eq 0) { 'ok' } else { 'fetch_failed' }

        $branch = (Get-GitSingleLine -RepoPath $repo -Arguments @('branch', '--show-current') -LogPath $logPath -AllowFailure).Text
        if ([string]::IsNullOrWhiteSpace($branch)) {
            $branch = 'DETACHED'
        }

        $head = (Get-GitSingleLine -RepoPath $repo -Arguments @('rev-parse', 'HEAD') -LogPath $logPath -AllowFailure).Text
        $statusResult = Invoke-GitCapture -RepoPath $repo -Arguments @('status', '--short') -LogPath $logPath -AllowFailure
        $workingTree = if ([string]::IsNullOrWhiteSpace($statusResult.StdOut)) { 'clean' } else { 'dirty' }

        Write-Section -LogPath $logPath -Title 'POST-FETCH STATUS'
        Write-Log -LogPath $logPath -Message ("branch={0}" -f $branch)
        Write-Log -LogPath $logPath -Message ("head={0}" -f $head)
        Write-Log -LogPath $logPath -Message ("working_tree={0}" -f $workingTree)
        Write-Log -LogPath $logPath -Message ("fetch_state={0}" -f $fetchState)

        $originStatus = Get-AheadBehindStatus -RepoPath $repo -LocalRef 'HEAD' -RemoteRef 'origin/main' -LogPath $logPath
        $githubStatus = Get-AheadBehindStatus -RepoPath $repo -LocalRef 'HEAD' -RemoteRef 'github/main' -LogPath $logPath

        Write-Section -LogPath $logPath -Title 'SYNC STATUS'
        Write-Log -LogPath $logPath -Message ("remotes={0}" -f (Format-RemoteSummary -RemoteMap $remoteMap))
        Write-Log -LogPath $logPath -Message ("origin/main={0}; ahead={1}; behind={2}" -f $originStatus.status, $originStatus.ahead, $originStatus.behind)
        Write-Log -LogPath $logPath -Message ("github/main={0}; ahead={1}; behind={2}" -f $githubStatus.status, $githubStatus.ahead, $githubStatus.behind)

        $actionTaken = 'none'
        $blocker = if ($fetchState -eq 'fetch_failed') { 'fetch_failed' } else { '' }

        if (
            $fetchState -eq 'ok' -and
            $branch -eq 'main' -and
            $workingTree -eq 'clean' -and
            $originStatus.status -eq 'behind'
        ) {
            Write-Section -LogPath $logPath -Title 'AUTO FAST-FORWARD PULL origin/main'
            $pullResult = Invoke-GitCapture -RepoPath $repo -Arguments @('pull', '--ff-only', 'origin', 'main') -LogPath $logPath -AllowFailure

            if ($pullResult.ExitCode -eq 0) {
                $actionTaken = 'pulled_ff_only_origin_main'
                $originStatus = Get-AheadBehindStatus -RepoPath $repo -LocalRef 'HEAD' -RemoteRef 'origin/main' -LogPath $logPath
                $githubStatus = Get-AheadBehindStatus -RepoPath $repo -LocalRef 'HEAD' -RemoteRef 'github/main' -LogPath $logPath
            }
            else {
                $actionTaken = 'pull_attempt_failed'
                $blocker = 'ff_pull_failed'
            }
        }

        Write-Section -LogPath $logPath -Title 'FINAL REMOTE URLS'
        $finalRemoteMap = Get-RemoteMap -RepoPath $repo -LogPath $logPath
        Write-Log -LogPath $logPath -Message ("DONE {0}" -f (Get-Date -Format 's'))

        $summaryRows.Add([pscustomobject]@{
            repo                 = $repoName
            path                 = $repo
            branch               = $branch
            head                 = $head
            working_tree         = $workingTree
            remotes              = (Format-RemoteSummary -RemoteMap $finalRemoteMap)
            origin_main_status   = $originStatus.status
            origin_main_ahead    = $originStatus.ahead
            origin_main_behind   = $originStatus.behind
            github_main_status   = $githubStatus.status
            github_main_ahead    = $githubStatus.ahead
            github_main_behind   = $githubStatus.behind
            action_taken         = $actionTaken
            blocker              = $blocker
            log                  = $logPath
        })
    }
    catch {
        if (-not (Test-Path -LiteralPath $logPath)) {
            Ensure-Directory -Path $logsDir
            Set-Content -LiteralPath $logPath -Value ("START {0}" -f (Get-Date -Format 's')) -Encoding UTF8
        }

        Write-Section -LogPath $logPath -Title 'UNHANDLED ERROR'
        Write-Log -LogPath $logPath -Message $_.Exception.ToString()

        $summaryRows.Add([pscustomobject]@{
            repo                 = $repoName
            path                 = $repo
            branch               = ''
            head                 = ''
            working_tree         = 'error'
            remotes              = 'unknown'
            origin_main_status   = 'error'
            origin_main_ahead    = ''
            origin_main_behind   = ''
            github_main_status   = 'error'
            github_main_ahead    = ''
            github_main_behind   = ''
            action_taken         = 'none'
            blocker              = $_.Exception.Message
            log                  = $logPath
        })
    }
    finally {
        if (Test-Path -LiteralPath $logPath) {
            Copy-Item -LiteralPath $logPath -Destination (Join-Path $bundleDir ([IO.Path]::GetFileName($logPath))) -Force
        }
    }
}

$summaryPath = Join-Path $bundleDir 'repo_sync_summary.txt'
$summaryLines = New-Object System.Collections.Generic.List[string]
$summaryLines.Add(("repo_sync_pre_codex_v2 run: {0}" -f (Get-Date -Format 's')))
$summaryLines.Add(("bundle_dir: {0}" -f $bundleDir))
$summaryLines.Add(("zip_path: {0}" -f $zipPath))
$summaryLines.Add('')

foreach ($row in $summaryRows) {
    $summaryLines.Add(('[' + $row.repo + ']'))
    $summaryLines.Add(("path={0}" -f $row.path))
    $summaryLines.Add(("branch={0}" -f $row.branch))
    $summaryLines.Add(("head={0}" -f $row.head))
    $summaryLines.Add(("working_tree={0}" -f $row.working_tree))
    $summaryLines.Add(("remotes={0}" -f $row.remotes))
    $summaryLines.Add(("origin/main status={0}; ahead={1}; behind={2}" -f $row.origin_main_status, $row.origin_main_ahead, $row.origin_main_behind))
    $summaryLines.Add(("github/main status={0}; ahead={1}; behind={2}" -f $row.github_main_status, $row.github_main_ahead, $row.github_main_behind))
    $summaryLines.Add(("action_taken={0}" -f $row.action_taken))
    $summaryLines.Add(("blocker={0}" -f $row.blocker))
    $summaryLines.Add(("log={0}" -f $row.log))
    $summaryLines.Add('')
}

$summaryLines | Set-Content -LiteralPath $summaryPath -Encoding UTF8

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -Path (Join-Path $bundleDir '*') -DestinationPath $zipPath -Force

Write-Host ''
Write-Host 'DONE'
Write-Host ("SUMMARY: {0}" -f $summaryPath)
Write-Host ("ZIP: {0}" -f $zipPath)
