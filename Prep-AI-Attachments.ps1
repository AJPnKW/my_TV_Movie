<# ============================================================================
Project : my_TV_Movie
File    : Prep-AI-Attachments.ps1
Purpose : Build AI-attachment .txt files directly into:
            <repo>\.txt_files_4_AI_attachments\
          then zip that folder into:
            <repo>\.txt_files_4_AI_attachments\archieves\

Design (per your expectation):
  1) Zip existing attachment files FIRST (snapshot)
  2) Generate/overwrite attachment files into .txt_files_4_AI_attachments\
  3) Zip again AFTER generation (fresh snapshot)

Pinned outputs:
  - Attachments (files): <repo>\.txt_files_4_AI_attachments\
  - Logs:               <repo>\.txt_files_4_AI_attachments\logs\
  - Zips:               <repo>\.txt_files_4_AI_attachments\archieves\

Key exclusions (folders):
  - <repo>\image\
  - <repo>\logs\                (NEW)
  - <repo>\.git\
  - <repo>\node_modules\
  - <repo>\.venv\ and <repo>\venv\
  - <repo>\__pycache__\
  - <repo>\.txt_files_4_AI_attachments\

Key exclusions (extensions):
  - binaries/media/docs/fonts/db/etc
  - .bak (NEW)

Version: 1.3.1 (2025-12-17)
============================================================================ #>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$RepoRoot = (Split-Path -Parent $PSCommandPath)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
function Get-Stamp { Get-Date -Format 'yyyy-MM-dd_HHmmss' }

function Ensure-Dir {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Is-UnderPath {
    param([Parameter(Mandatory)][string]$Child, [Parameter(Mandatory)][string]$Parent)
    $c = [System.IO.Path]::GetFullPath($Child)
    $p = [System.IO.Path]::GetFullPath($Parent)
    return $c.StartsWith($p, [System.StringComparison]::OrdinalIgnoreCase)
}

# -----------------------------------------------------------------------------
# Logging: ONE writer
# -----------------------------------------------------------------------------
$script:LogWriter = $null

function Start-LogWriter {
    param([Parameter(Mandatory)][string]$Path)

    Ensure-Dir -Path (Split-Path -Parent $Path)

    $fs = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::Append,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::ReadWrite
    )

    $sw = New-Object System.IO.StreamWriter($fs, (New-Object System.Text.UTF8Encoding($false)))
    $sw.AutoFlush = $true
    $script:LogWriter = $sw
}

function Stop-LogWriter {
    try {
        if ($null -ne $script:LogWriter) {
            $script:LogWriter.Flush()
            $script:LogWriter.Dispose()
        }
    } catch { }
    $script:LogWriter = $null
}

function Write-Log {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ValidateSet('INFO','WARN','ERROR')][string]$Level = 'INFO'
    )
    $line = "{0} | {1,-5} | {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    if ($null -ne $script:LogWriter) { $script:LogWriter.WriteLine($line) }
}

# -----------------------------------------------------------------------------
# Version detection (patched)
# -----------------------------------------------------------------------------
function Get-VersionFromText {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $false)][string]$SourcePath = ""
    )

    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }

    $t = $Text -replace "`r`n", "`n"
    $ext = ""
    try { $ext = [System.IO.Path]::GetExtension($SourcePath).ToLowerInvariant() } catch { $ext = "" }

    if ($ext -in @(".html",".htm",".js",".ts",".css")) {
        $p_const = '(?im)^\s*(?:const|let|var)?\s*version\s*=\s*["'']v?(\d+(?:\.\d+){0,3})["'']\s*;?\s*$'
        $m = [regex]::Match($t, $p_const)
        if ($m.Success) { return ("v{0}" -f $m.Groups[1].Value) }

        $p_html_label = '(?im)^\s*<!--\s*version\s*[:=]\s*v?(\d+(?:\.\d+){0,3})\s*-->\s*$'
        $m = [regex]::Match($t, $p_html_label)
        if ($m.Success) { return ("v{0}" -f $m.Groups[1].Value) }

        $p_meta = '(?im)\b(?:app\s+)?version\b\s*[:=]\s*v?(\d+(?:\.\d+){0,3})\b'
        $m = [regex]::Match($t, $p_meta)
        if ($m.Success) { return ("v{0}" -f $m.Groups[1].Value) }
    }

    $patterns = @(
        '(?im)^\s*(?:#|//|/\*+|\*|<!--)?\s*version\s*[:=]\s*v?(\d+(?:\.\d+){0,3})\b',
        '(?im)^\s*version\s+\:\s*v?(\d+(?:\.\d+){0,3})\b',
        '(?im)"version"\s*:\s*"?v?(\d+(?:\.\d+){0,3})"?',
        '(?im)^\s*version\s*:\s*v?(\d+(?:\.\d+){0,3})\b'
    )

    foreach ($p in $patterns) {
        $m = [regex]::Match($t, $p)
        if ($m.Success) { return ("v{0}" -f $m.Groups[1].Value) }
    }

    $p_safe = '(?im)\bversion\b[^\n]{0,40}\bv(\d+(?:\.\d+){1,3})\b'
    $m = [regex]::Match($t, $p_safe)
    if ($m.Success) { return ("v{0}" -f $m.Groups[1].Value) }

    return $null
}

function Get-VersionForFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [int]$MaxLines = 80
    )

    try {
        if (-not (Test-Path -LiteralPath $Path)) { return $null }
        $lines = Get-Content -LiteralPath $Path -TotalCount $MaxLines -ErrorAction Stop
        if ($null -eq $lines) { return $null }
        $arr = @()
        if ($lines -is [string]) { $arr = @($lines) } else { $arr = @($lines) }
        if ($arr.Count -eq 0) { return $null }
        $text = ($arr -join "`n")
        return Get-VersionFromText -Text $text -SourcePath $Path
    } catch {
        return $null
    }
}

# -----------------------------------------------------------------------------
# Filtering rules
# -----------------------------------------------------------------------------
function Has-ExcludedExtension {
    param([Parameter(Mandatory)][string]$Path)

    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()

    $excluded = @(
        '.bak',  # NEW
        '.jpg','.jpeg','.png','.gif','.webp','.bmp','.ico','.svg',
        '.mp3','.wav','.flac',
        '.mp4','.mkv','.avi','.mov',
        '.zip','.7z','.rar','.gz','.tar',
        '.exe','.dll','.sys','.msi','.iso',
        '.pdf','.doc','.docx','.ppt','.pptx','.xls','.xlsx',
        '.ttf','.otf','.woff','.woff2',
        '.db','.sqlite','.bin'
    )
    return ($excluded -contains $ext)
}

function Should-NormalizeUtf8 {
    param([Parameter(Mandatory)][string]$Path)
    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    $normalize = @(
        '.txt','.md','.csv','.tsv',
        '.py','.ps1','.bat','.cmd',
        '.html','.htm','.css','.js','.ts',
        '.json','.yml','.yaml',
        '.xml','.ini','.cfg','.conf'
    )
    return ($normalize -contains $ext)
}

# -----------------------------------------------------------------------------
# Attachment naming + zip helper
# -----------------------------------------------------------------------------
function Get-AttachmentFileName {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$SourcePath
    )

    $rel  = [System.IO.Path]::GetRelativePath($RepoRoot, $SourcePath)
    $flat = ($rel -replace '[\\/]', '__')

    $ver = Get-VersionForFile -Path $SourcePath
    if ($ver) {
        Write-Log ("VERSION_FOUND | {0} | {1}" -f $SourcePath, $ver)
        return "{0}__{1}.txt" -f $flat, $ver
    }

    Write-Log ("VERSION_NONE  | {0}" -f $SourcePath)
    return "{0}.txt" -f $flat
}

function Zip-AttachmentsSnapshot {
    param(
        [Parameter(Mandatory)][string]$AttachRoot,
        [Parameter(Mandatory)][string]$ZipPath
    )

    # Only include files directly under attach_root (exclude logs/archieves)
    $files = Get-ChildItem -LiteralPath $AttachRoot -File -ErrorAction Stop
    if ($files.Count -eq 0) { throw "No attachment files found in $AttachRoot" }

    if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }

    Compress-Archive -LiteralPath ($files.FullName) -DestinationPath $ZipPath -Force -ErrorAction Stop
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
$stamp = Get-Stamp
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

$attach_root = Join-Path $RepoRoot '.txt_files_4_AI_attachments'
$logs_dir    = Join-Path $attach_root 'logs'
$zip_dir     = Join-Path $attach_root 'archieves'   # spelling retained
Ensure-Dir -Path $attach_root
Ensure-Dir -Path $logs_dir
Ensure-Dir -Path $zip_dir

$ps_log_path     = Join-Path $logs_dir "Prep-AI-Attachments_$stamp.log.txt"
$transcript_path = Join-Path $logs_dir "Prep-AI-Attachments_$stamp.transcript.txt"

Start-LogWriter -Path $ps_log_path

$transcript_started = $false
try { Start-Transcript -LiteralPath $transcript_path -Force | Out-Null; $transcript_started = $true } catch { $transcript_started = $false }

Write-Log "START prep_ai_attachments_$stamp"
Write-Log "repo_root=$RepoRoot"
Write-Log "attach_root=$attach_root"
Write-Log "logs_dir=$logs_dir"
Write-Log "zip_dir=$zip_dir"
Write-Log "log_path=$ps_log_path"
Write-Log "transcript_path=$transcript_path"
Write-Log "transcript_started=$transcript_started"

# Excluded folders (absolute)
$exclude_folders = @(
    (Join-Path $RepoRoot '.git'),
    (Join-Path $RepoRoot 'node_modules'),
    (Join-Path $RepoRoot '.venv'),
    (Join-Path $RepoRoot 'venv'),
    (Join-Path $RepoRoot '__pycache__'),
    (Join-Path $RepoRoot '.txt_files_4_AI_attachments'),
    (Join-Path $RepoRoot 'image'),
    (Join-Path $RepoRoot 'logs')   # NEW
)

# Snapshot ZIP BEFORE generation
try {
    $zip_before = Join-Path $zip_dir "my_TV_Movie_AI_attachments_BEFORE_$stamp.zip"
    Write-Log "ZIPPING BEFORE generation -> $zip_before"
    Zip-AttachmentsSnapshot -AttachRoot $attach_root -ZipPath $zip_before
    Write-Log "ZIP BEFORE created: $zip_before"
} catch {
    Write-Log ("ZIP BEFORE skipped/failed: {0}" -f $_.Exception.Message) 'WARN'
}

# Generate/overwrite attachment files directly in attach_root
[int]$scanned  = 0
[int]$written  = 0
[int]$excluded = 0
[int]$errors   = 0

$all = Get-ChildItem -LiteralPath $RepoRoot -Recurse -File -Force -ErrorAction Stop
$idx = 0
$total = $all.Count

foreach ($f in $all) {
    $idx++
    $scanned++

    if ($total -gt 0) {
        $pct = [math]::Floor(($idx / $total) * 100)
        Write-Progress -Activity "Prep AI Attachments" -Status "$idx / $total" -PercentComplete $pct
    }

    $path = $f.FullName

    # Exclude folder trees
    $skip = $false
    foreach ($xf in $exclude_folders) {
        if (Test-Path -LiteralPath $xf) {
            if (Is-UnderPath -Child $path -Parent $xf) { $skip = $true; break }
        }
    }
    if ($skip) { $excluded++; continue }

    # Exclude by extension (includes .bak now)
    if (Has-ExcludedExtension -Path $path) { $excluded++; continue }

    # Skip current run logs/transcript and BAT log
    if ($path -ieq $ps_log_path) { $excluded++; continue }
    if ($path -ieq $transcript_path) { $excluded++; continue }
    if ($env:BATLOG -and $env:BATLOG.Trim() -ne '' -and ($path -ieq $env:BATLOG)) { $excluded++; continue }

    # Skip the attachment tool scripts themselves
    $ln = $f.Name.ToLowerInvariant()
    if ($ln -eq 'prep-ai-attachments.ps1' -or $ln -eq 'prep_ai_attachments.bat') { $excluded++; continue }

    try {
        $out_name = Get-AttachmentFileName -RepoRoot $RepoRoot -SourcePath $path
        $out_path = Join-Path $attach_root $out_name

        if (Should-NormalizeUtf8 -Path $path) {
            $raw = Get-Content -LiteralPath $path -Raw -ErrorAction Stop
            [System.IO.File]::WriteAllText($out_path, $raw, (New-Object System.Text.UTF8Encoding($false)))
        } else {
            Copy-Item -LiteralPath $path -Destination $out_path -Force
        }

        $written++
    } catch {
        $errors++
        Write-Log ("WRITE error: {0} :: {1}" -f $path, $_.Exception.Message) 'ERROR'
    }
}

# Snapshot ZIP AFTER generation
try {
    $zip_after = Join-Path $zip_dir "my_TV_Movie_AI_attachments_AFTER_$stamp.zip"
    Write-Log "ZIPPING AFTER generation -> $zip_after"
    Zip-AttachmentsSnapshot -AttachRoot $attach_root -ZipPath $zip_after
    Write-Log "ZIP AFTER created: $zip_after"
} catch {
    $errors++
    Write-Log ("ZIP AFTER failed: {0}" -f $_.Exception.Message) 'ERROR'
}

Write-Progress -Activity "Prep AI Attachments" -Completed
Write-Log ("SUMMARY scanned={0} written={1} excluded={2} errors={3}" -f $scanned, $written, $excluded, $errors)

Write-Host ""
Write-Host "DONE."
Write-Host "Attachments folder:"
Write-Host "  $attach_root"
Write-Host "Zips folder:"
Write-Host "  $zip_dir"
Write-Host "Log:"
Write-Host "  $ps_log_path"
Write-Host "Transcript:"
Write-Host "  $transcript_path"
Write-Host ""

try { if ($transcript_started) { Stop-Transcript | Out-Null } } catch { }
Stop-LogWriter
