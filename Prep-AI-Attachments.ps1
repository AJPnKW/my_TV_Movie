<# ============================================================================
FILE:        Prep-AI-Attachments.ps1
PROJECT:     my_TV_Movie
PURPOSE:
  Prepare curated "AI attachment" files from the repo into:
    <RepoRoot>\.txt_files_4_AI_attachments

WORKFLOW (expected):
  1) PRE-ZIP current top-level attachments -> <AttachRoot>\archieves
  2) CLEAR current top-level attachments (leave logs/archieves folders)
  3) GATHER in-scope repo files -> write renamed copies into <AttachRoot>
  4) ZIP the new attachment set -> <AttachRoot>\archieves
     (attachments remain in place after zip)

OUTPUT LOCATIONS:
  Attachments : <RepoRoot>\.txt_files_4_AI_attachments
  Logs        : <RepoRoot>\.txt_files_4_AI_attachments\logs
  Archives    : <RepoRoot>\.txt_files_4_AI_attachments\archieves

FILENAME RULES (deterministic):
  Non-.txt sources:
    - wrapper .txt always added
      web\index.html -> web__index.html.txt
    - if version detected, append before wrapper:
      web__index.html__v3.3.6.txt

  .txt sources (special rule per your clarification):
    - if NO version detected: keep name as-is (no rename, no .txt.txt)
      tv_list.txt -> tv_list.txt
    - if version detected: inject version BEFORE .txt
      tv_list.txt + v1.0.0 -> tv_list__v1.0.0.txt
    (never tv_list.txt__v1.0.0 and never tv_list.txt__v1.0.0.txt)

VERSION DETECTION (additive; does NOT replace other styles):
  - [VERSION]     v3.3.5
  - Version: 1.2.3 / Version : v2.8.02
  - [UPDATED]     2025-12-14
  - [Build/Iteration Tag]   14.01.03  (captured, not used in filename)

EXCLUSIONS (repo scan):
  Directory SEGMENT excludes (exact segment match, case-insensitive):
    .git, .github, .venv, .env, .my_notes, .archive, .archieve,
    image, logs, reports, .txt_files_4_AI_attachments

  Filename substring excludes (case-insensitive):
    audit, report, compare, copy

  Extension excludes:
    .bak, .tws, plus common binaries/media/archives

LOGGING:
  - One UTF-8 log per run in <LogsDir> + console output
  - Uses single StreamWriter to avoid file-lock / Add-Content contention

VERSION CONTROL:
  Script Version : 2.2.0
  Build Stamp    : 2025-12-17_180500
============================================================================ #>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# SECTION: TIME + PATH RESOLUTION
# =============================================================================
function Get-Stamp { Get-Date -Format 'yyyy-MM-dd_HHmmss' }

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $RepoRoot = $PSScriptRoot
    } elseif ($MyInvocation.MyCommand.Path) {
        $RepoRoot = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
    } else {
        $RepoRoot = (Get-Location).Path
    }
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

$AttachRoot = Join-Path $RepoRoot ".txt_files_4_AI_attachments"
$LogsDir    = Join-Path $AttachRoot "logs"
$ArchiveDir = Join-Path $AttachRoot "archieves"   # keep spelling
$RunStamp   = Get-Stamp
$PsLogPath  = Join-Path $LogsDir ("Prep-AI-Attachments_{0}.log.txt" -f $RunStamp)

# =============================================================================
# SECTION: LOGGING (single writer)
# =============================================================================
$script:LogWriter = $null

function Ensure-Dir {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Start-Log {
    Ensure-Dir -Path $LogsDir
    $fs = [System.IO.File]::Open($PsLogPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
    $script:LogWriter = New-Object System.IO.StreamWriter($fs, (New-Object System.Text.UTF8Encoding($false)))
    $script:LogWriter.AutoFlush = $true
}

function Stop-Log { try { if ($script:LogWriter) { $script:LogWriter.Dispose() } } catch { } }

function Write-Log {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ValidateSet('INFO','WARN','ERROR','DEBUG')]
        [string]$Level = 'INFO'
    )
    $line = "{0} | {1,-5} | {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    if ($script:LogWriter) { $script:LogWriter.WriteLine($line) }
}

# =============================================================================
# SECTION: EXCLUSION CONFIG
# =============================================================================
$ExcludedDirNames = @(
    '.git', '.github', '.venv', '.env', '.my_notes',
    '.archive', '.archieve',
    'image', 'logs', 'reports',
    '.txt_files_4_AI_attachments'
)

$ExcludedNameContains = @(
    'audit', 'report', 'compare', 'copy'
)

$ExcludedExtensions = @(
    '.bak', '.tws',
    '.zip','.7z','.rar','.gz','.tar',
    '.exe','.dll','.sys','.msi','.iso',
    '.jpg','.jpeg','.png','.gif','.webp','.bmp','.ico','.svg',
    '.mp3','.wav','.flac',
    '.mp4','.mkv','.avi','.mov',
    '.ttf','.otf','.woff','.woff2',
    '.db','.sqlite','.bin'
)

function Is-ExcludedPath {
    <#
      Correct segment-based directory exclusion (prevents over-matching).
    #>
    param([Parameter(Mandatory)][string]$FullPath)

    $full = [System.IO.Path]::GetFullPath($FullPath)

    # A) Directory segment exclusion
    $dir = [System.IO.Path]::GetDirectoryName($full)
    $segments = @()
    if (-not [string]::IsNullOrWhiteSpace($dir)) { $segments = $dir -split '[\\/]'}
    foreach ($seg in $segments) {
        foreach ($d in $ExcludedDirNames) {
            if ($seg.Equals($d, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
        }
    }

    # B) Filename contains exclusion
    $name = [System.IO.Path]::GetFileName($full)
    foreach ($sub in $ExcludedNameContains) {
        if ($name.IndexOf($sub, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { return $true }
    }

    # C) Extension exclusion
    $ext = [System.IO.Path]::GetExtension($full)
    foreach ($x in $ExcludedExtensions) {
        if ($ext.Equals($x, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    }

    return $false
}

# =============================================================================
# SECTION: VERSION DETECTION (additive)
# =============================================================================
function Get-VersionInfoFromFile {
    param([Parameter(Mandatory)][string]$Path)

    $version  = ""
    $updated  = ""
    $buildtag = ""

    try { $lines = Get-Content -LiteralPath $Path -TotalCount 200 -ErrorAction Stop }
    catch { return [pscustomobject]@{ version=""; updated=""; buildtag="" } }

    foreach ($line in $lines) {
        $t = ($line + "").Trim()

        # [VERSION] v3.3.5
        if (-not $version) {
            $m = [regex]::Match($t, '^\[VERSION\]\s*(v?\d+(?:\.\d+){0,3})\s*$', 'IgnoreCase')
            if ($m.Success) {
                $version = $m.Groups[1].Value
                if ($version -notmatch '^(?i)v') { $version = "v$version" }
                continue
            }
        }

        # Version: 1.2.3 / Version : v2.8.02
        if (-not $version -and $t -match '(?i)\bversion\b') {
            $m = [regex]::Match($t, '(?i)\bversion\b\s*[:=]\s*(v?\d+(?:\.\d+){0,3})')
            if ($m.Success) {
                $version = $m.Groups[1].Value
                if ($version -notmatch '^(?i)v') { $version = "v$version" }
                continue
            }
        }

        # [UPDATED] 2025-12-14
        if (-not $updated) {
            $m = [regex]::Match($t, '^\[UPDATED\]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*$')
            if ($m.Success) { $updated = $m.Groups[1].Value; continue }
        }

        # [Build/Iteration Tag] 14.01.03
        if (-not $buildtag) {
            $m = [regex]::Match($t, '^\[Build/Iteration Tag\]\s*([0-9]{1,3}(?:\.[0-9]{1,3}){1,4})\s*$', 'IgnoreCase')
            if ($m.Success) { $buildtag = $m.Groups[1].Value; continue }
        }
    }

    [pscustomobject]@{ version=$version; updated=$updated; buildtag=$buildtag }
}

# =============================================================================
# SECTION: ATTACHMENT FILE NAMING
# =============================================================================
function Get-RepoRelativePath {
    param([Parameter(Mandatory)][string]$Base, [Parameter(Mandatory)][string]$FullPath)
    $b = [System.IO.Path]::GetFullPath($Base).TrimEnd('\')
    $f = [System.IO.Path]::GetFullPath($FullPath)
    if ($f.Length -le $b.Length) { return "" }
    return $f.Substring($b.Length).TrimStart('\')
}

function Make-AttachmentFileName {
    <#
      Implements your clarified .txt rule:
        tv_list.txt (no version) -> tv_list.txt
        tv_list.txt (version)    -> tv_list__v1.0.0.txt

      Non-.txt rule:
        scripts\fetch_tmdb.py (version) -> scripts__fetch_tmdb.py__vX.Y.Z.txt
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$SourcePath,
        [Parameter(Mandatory=$false)][AllowEmptyString()][string]$Version = ""
    )

    $rel = Get-RepoRelativePath -Base $RepoRoot -FullPath $SourcePath
    if ([string]::IsNullOrWhiteSpace($rel)) { return "" }

    $encoded = $rel -replace '\\', '__'

    $ext = [System.IO.Path]::GetExtension($SourcePath)
    $isTxt = $ext.Equals('.txt', [System.StringComparison]::OrdinalIgnoreCase)

    $v = ($Version + "").Trim()

    if ($isTxt) {
        if ([string]::IsNullOrWhiteSpace($v)) {
            # keep original .txt name as-is
            return $encoded
        }

        # inject version before .txt
        if ($encoded.ToLowerInvariant().EndsWith(".txt")) {
            $base = $encoded.Substring(0, $encoded.Length - 4)
            return ("{0}__{1}.txt" -f $base, $v)
        }

        # safety fallback
        return ("{0}__{1}.txt" -f $encoded, $v)
    }

    # non-.txt: append version (if any) then wrap with .txt
    if (-not [string]::IsNullOrWhiteSpace($v) -and ($encoded -notmatch '(?i)__v\d')) {
        $encoded = "{0}__{1}" -f $encoded, $v
    }
    return ($encoded + ".txt")
}

# =============================================================================
# SECTION: ZIP + CLEAR (top-level only)
# =============================================================================
function Get-AttachmentsTopLevelFiles {
    param([Parameter(Mandatory)][string]$AttachRoot)
    Get-ChildItem -LiteralPath $AttachRoot -File -ErrorAction Stop
}

function Compress-AttachmentsTopLevel {
    param(
        [Parameter(Mandatory)][string]$AttachRoot,
        [Parameter(Mandatory)][string]$ZipPath
    )

    $topFiles = Get-AttachmentsTopLevelFiles -AttachRoot $AttachRoot
    if (-not $topFiles -or $topFiles.Count -eq 0) {
        Write-Log "No top-level attachment files to zip in: $AttachRoot" "INFO"
        return $false
    }

    $paths = $topFiles | Select-Object -ExpandProperty FullName
    Compress-Archive -LiteralPath $paths -DestinationPath $ZipPath -Force
    Write-Log "ZIP created: $ZipPath" "INFO"
    return $true
}

function Clear-AttachmentsTopLevel {
    param([Parameter(Mandatory)][string]$AttachRoot)

    $topFiles = Get-AttachmentsTopLevelFiles -AttachRoot $AttachRoot
    foreach ($f in $topFiles) {
        Remove-Item -LiteralPath $f.FullName -Force
    }
    Write-Log "Cleared top-level attachment files from: $AttachRoot" "INFO"
}

# =============================================================================
# SECTION: MAIN
# =============================================================================
try {
    Ensure-Dir -Path $AttachRoot
    Ensure-Dir -Path $LogsDir
    Ensure-Dir -Path $ArchiveDir
    Start-Log

    Write-Log "START Prep-AI-Attachments run=$RunStamp" "INFO"
    Write-Log "RepoRoot=$RepoRoot" "INFO"
    Write-Log "AttachRoot=$AttachRoot" "INFO"
    Write-Log "LogsDir=$LogsDir" "INFO"
    Write-Log "ArchiveDir=$ArchiveDir" "INFO"
    Write-Log "PsLogPath=$PsLogPath" "INFO"

    # STEP 1: PRE-ZIP existing attachments then clear them
    $preZip = Join-Path $ArchiveDir ("AI_Attachments_PRE_{0}.zip" -f $RunStamp)
    if (Compress-AttachmentsTopLevel -AttachRoot $AttachRoot -ZipPath $preZip) {
        Clear-AttachmentsTopLevel -AttachRoot $AttachRoot
    } else {
        Write-Log "PRE-ZIP skipped (no existing attachments)." "INFO"
    }

    # STEP 2: GATHER
    Write-Log "Scanning repo files (recursive)..." "INFO"
    $scanned = 0; $excluded = 0; $written = 0; $versioned = 0

    $repoFiles = Get-ChildItem -LiteralPath $RepoRoot -Recurse -File -Force -ErrorAction Stop

    foreach ($rf in $repoFiles) {
        $scanned++

        if (Is-ExcludedPath -FullPath $rf.FullName) { $excluded++; continue }

        $vi = Get-VersionInfoFromFile -Path $rf.FullName
        $v  = ($vi.version + "")
        if (-not [string]::IsNullOrWhiteSpace($v)) { $versioned++ }

        $destName = Make-AttachmentFileName -RepoRoot $RepoRoot -SourcePath $rf.FullName -Version $v
        if ([string]::IsNullOrWhiteSpace($destName)) { $excluded++; continue }

        $destPath = Join-Path $AttachRoot $destName
        Copy-Item -LiteralPath $rf.FullName -Destination $destPath -Force
        $written++
    }

    Write-Log "Scan summary: scanned=$scanned written=$written excluded=$excluded versioned=$versioned" "INFO"

    # STEP 3: ZIP new attachments (do NOT clear them)
    $runZip = Join-Path $ArchiveDir ("AI_Attachments_{0}.zip" -f $RunStamp)
    if (Compress-AttachmentsTopLevel -AttachRoot $AttachRoot -ZipPath $runZip) {
        Write-Log "Run ZIP ready: $runZip" "INFO"
    } else {
        Write-Log "Run ZIP NOT created (no attachments found after gather)." "WARN"
    }

    Write-Log "DONE" "INFO"
    Write-Host ""
    Write-Host "OUTPUTS:"
    Write-Host "  LOG : $PsLogPath"
    Write-Host "  ZIP : $runZip"
    Write-Host ""
    Write-Host "Press ENTER to close..."
    [void](Read-Host)

} catch {
    try { Write-Log ("ERROR: {0}" -f $_.Exception.Message) "ERROR" } catch { }
    Write-Host ""
    Write-Host "FAILED. See log:"
    Write-Host "  $PsLogPath"
    Write-Host ""
    Write-Host "Press ENTER to close..."
    [void](Read-Host)
    exit 1
} finally {
    Stop-Log
}
