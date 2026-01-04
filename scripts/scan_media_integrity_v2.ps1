#requires -Version 5.1
<#
scan_media_integrity_v2.ps1
- Scans media under C:\X1_Share\Media
- Writes human-readable console summary + CSV + log
- Optionally moves suspects to dated quarantine folder
- Skips folders starting with "_" (e.g., _Artwork, _Reports, _Quarantine)
- Uses ffprobe for quick container/stream checks; optional deep decode with ffmpeg

Run examples:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Utilities\scripts\scan_media_integrity_v2.ps1
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Utilities\scripts\scan_media_integrity_v2.ps1 -WhatIf
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Utilities\scripts\scan_media_integrity_v2.ps1 -DeepDecode
#>

[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [string]$RootPath = "C:\X1_Share\Media",
  [int]$MinDurationSeconds = 120,
  [switch]$DeepDecode,
  [int]$DeepDecodeSeconds = 90,
  [switch]$MoveSuspects = $true,
  [string[]]$IncludeExtensions = @(".mp4",".mkv",".ts",".m4v",".avi",".mov",".mpg",".mpeg",".wmv",".m2ts",".webm",".mp3",".m4a",".flac",".aac",".wav",".ogg",".srt",".ass",".vtt")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-Folder([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

function Get-ToolPath([string]$Tool) {
  $cmd = Get-Command $Tool -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Path) { return $cmd.Path }
  $p = Join-Path "C:\Utilities\bin" ($Tool + ".exe")
  if (Test-Path -LiteralPath $p) { return $p }
  throw "Missing required tool '$Tool'. Expected it in PATH or at $p"
}

function NowStamp() { Get-Date -Format "yyyyMMdd_HHmmss" }
function TodayStamp() { Get-Date -Format "yyyy-MM-dd" }

function Write-Log([string]$Msg) {
  $line = "{0} | {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
  $script:logLines.Add($line) | Out-Null
}

function Safe-RelPath([string]$Base, [string]$Full) {
  $b = (Resolve-Path -LiteralPath $Base).Path.TrimEnd("\")
  $f = (Resolve-Path -LiteralPath $Full).Path
  if ($f.StartsWith($b, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $f.Substring($b.Length).TrimStart("\")
  }
  return $Full
}

function Invoke-FfprobeJson([string]$FfprobeExe, [string]$FilePath) {
  # IMPORTANT: pass args as an array so the INPUT_FILE is always present + properly quoted
  $args = @(
    "-v","error",
    "-print_format","json",
    "-show_format",
    "-show_streams",
    "--",
    $FilePath
  )
  $out = & $FfprobeExe @args 2>&1
  if ($LASTEXITCODE -ne 0) {
    return @{ ok=$false; raw=$out }
  }
  try {
    $json = $out | ConvertFrom-Json -ErrorAction Stop
    return @{ ok=$true; json=$json; raw=$out }
  } catch {
    return @{ ok=$false; raw=$out }
  }
}

function Invoke-DeepDecode([string]$FfmpegExe, [string]$FilePath, [int]$Seconds) {
  # Decode first N seconds; any decode error marks as suspect.
  $args = @(
    "-v","error",
    "-xerror",
    "-ss","00:00:00",
    "-t",("{0}" -f $Seconds),
    "-i",$FilePath,
    "-f","null",
    "-"
  )
  $out = & $FfmpegExe @args 2>&1
  return @{ ok=($LASTEXITCODE -eq 0); raw=$out }
}

function Get-TextEncodingInfo([string]$FilePath) {
  # Only for subtitle/text-like files. Not meaningful for .mp4/.mkv containers.
  $ext = [IO.Path]::GetExtension($FilePath).ToLowerInvariant()
  if ($ext -notin @(".srt",".ass",".vtt")) { return @{ is_text=$false } }

  try {
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
      return @{ is_text=$true; encoding="UTF-8-BOM"; ok=$true }
    }
    # Heuristic: try strict UTF-8 decode
    $utf8 = New-Object System.Text.UTF8Encoding($false,$true)
    $null = $utf8.GetString($bytes)
    return @{ is_text=$true; encoding="UTF-8"; ok=$true }
  } catch {
    return @{ is_text=$true; encoding="Non-UTF8 (likely ANSI/other)"; ok=$false }
  }
}

# ---------- Paths ----------
$ffprobe = Get-ToolPath "ffprobe"
$ffmpeg  = Get-ToolPath "ffmpeg"

$reports = Join-Path $RootPath "_Reports"
$quarBase = Join-Path $RootPath "_Quarantine"
$runStamp = NowStamp
$runDate  = TodayStamp
$quarantine = Join-Path $quarBase $runDate

New-Folder $reports
New-Folder $quarBase
New-Folder $quarantine

$csvPath = Join-Path $reports ("scan_media_integrity_v2__{0}.csv" -f $runStamp)
$logPath = Join-Path $reports ("scan_media_integrity_v2__{0}.log.txt" -f $runStamp)

$script:logLines = New-Object System.Collections.Generic.List[string]

Write-Log "START scan_media_integrity_v2"
Write-Log ("root_path={0} | deep_decode={1} | move_suspects={2} | min_duration_seconds={3}" -f $RootPath, $DeepDecode.IsPresent, $MoveSuspects.IsPresent, $MinDurationSeconds)
Write-Log ("ffprobe={0} | ffmpeg={1}" -f $ffprobe, $ffmpeg)

# ---------- Discover ----------
$all = Get-ChildItem -LiteralPath $RootPath -Recurse -File -Force |
  Where-Object {
    $ext = $_.Extension.ToLowerInvariant()
    $okExt = $IncludeExtensions -contains $ext
    if (-not $okExt) { return $false }

    # Skip folders that begin with "_" anywhere under RootPath
    $relDir = Safe-RelPath $RootPath $_.DirectoryName
    foreach ($part in ($relDir -split "\\+")) {
      if ($part.StartsWith("_")) { return $false }
    }
    return $true
  }

Write-Log ("discovered_files={0}" -f $all.Count)

# ---------- Scan ----------
$results = New-Object System.Collections.Generic.List[object]
$okCount = 0
$susCount = 0
$idx = 0
$total = [Math]::Max(1,$all.Count)

foreach ($f in $all) {
  $idx++
  $pct = [Math]::Floor(($idx / $total) * 100)
  Write-Progress -Activity "Scanning media" -Status ("{0}% ({1}/{2}) {3}" -f $pct,$idx,$total,$f.Name) -PercentComplete $pct

  $row = [ordered]@{
    timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    status = "OK"
    suspect = $false
    moved_to = ""
    reason_codes = ""
    device_risks = ""
    deep_decode = $DeepDecode.IsPresent
    deep_decode_details = ""
    path = $f.FullName
    rel_path = Safe-RelPath $RootPath $f.FullName
    file_name = $f.Name
    extension = $f.Extension.ToLowerInvariant()
    size_bytes = $f.Length
    last_write = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
    container = ""
    duration_seconds = $null
    has_video = $null
    has_audio = $null
    video_codec = ""
    video_profile = ""
    video_pix_fmt = ""
    width = $null
    height = $null
    audio_codec = ""
    audio_channels = $null
    ffprobe_details = ""
    text_encoding = ""
    text_encoding_ok = $null
  }

  $reasons = New-Object System.Collections.Generic.List[string]

  # Quick file sanity
  if ($f.Length -lt 1024) { $reasons.Add("TINY_FILE") | Out-Null }
  if ($f.LastWriteTime -gt (Get-Date).AddMinutes(5)) { $reasons.Add("FUTURE_TIMESTAMP") | Out-Null }

  # Text encoding (subs only)
  $enc = Get-TextEncodingInfo $f.FullName
  if ($enc.is_text) {
    $row.text_encoding = $enc.encoding
    $row.text_encoding_ok = [bool]$enc.ok
    if (-not $enc.ok) { $reasons.Add("SUBTITLE_NON_UTF8") | Out-Null }
  }

  # ffprobe
  $probe = Invoke-FfprobeJson $ffprobe $f.FullName
  if (-not $probe.ok) {
    $reasons.Add("FFPROBE_FAILED") | Out-Null
    $row.ffprobe_details = ($probe.raw -join " ").Trim()
  } else {
    $j = $probe.json
    $row.container = $j.format.format_name
    $dur = $null
    if ($j.format.duration) {
      [double]::TryParse([string]$j.format.duration, [ref]$dur) | Out-Null
      $row.duration_seconds = [int][Math]::Round($dur)
      if ($row.duration_seconds -lt $MinDurationSeconds) { $reasons.Add("TOO_SHORT") | Out-Null }
    } else {
      $reasons.Add("NO_DURATION") | Out-Null
    }

    $streams = @($j.streams)
    $v = $streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1
    $a = $streams | Where-Object { $_.codec_type -eq "audio" } | Select-Object -First 1

    $row.has_video = [bool]$v
    $row.has_audio = [bool]$a

    if ($v) {
      $row.video_codec = $v.codec_name
      $row.video_profile = ($v.profile | ForEach-Object { $_ }) -join ""
      $row.video_pix_fmt = ($v.pix_fmt | ForEach-Object { $_ }) -join ""
      $row.width  = $v.width
      $row.height = $v.height
    }
    if ($a) {
      $row.audio_codec = $a.codec_name
      $row.audio_channels = $a.channels
    }

    if (-not $v -and -not $a) { $reasons.Add("NO_STREAMS") | Out-Null }
  }

  # Optional deep decode
  if ($DeepDecode.IsPresent -and -not ($reasons -contains "FFPROBE_FAILED")) {
    $dd = Invoke-DeepDecode $ffmpeg $f.FullName $DeepDecodeSeconds
    if (-not $dd.ok) {
      $reasons.Add("DEEP_DECODE_FAILED") | Out-Null
      $row.deep_decode_details = ($dd.raw -join " ").Trim()
    }
  }

  if ($reasons.Count -gt 0) {
    $row.status = "SUSPECT"
    $row.suspect = $true
    $row.reason_codes = ($reasons -join "|")

    $susCount++
    Write-Log ("SUSPECT | {0} | {1} | {2}" -f $row.rel_path, $row.reason_codes, ($row.ffprobe_details.Substring(0,[Math]::Min(250, $row.ffprobe_details.Length))))

    if ($MoveSuspects.IsPresent) {
      $dest = Join-Path $quarantine $row.rel_path
      $destDir = Split-Path -Parent $dest
      New-Folder $destDir

      if ($PSCmdlet.ShouldProcess($f.FullName, "Move to quarantine: $dest")) {
        Move-Item -LiteralPath $f.FullName -Destination $dest -Force
        $row.moved_to = $dest
        Write-Log ("MOVED | {0} -> {1}" -f $row.rel_path, (Safe-RelPath $RootPath $dest))
      } else {
        $row.moved_to = "(WhatIf) $dest"
      }
    }
  } else {
    $okCount++
  }

  $results.Add([pscustomobject]$row) | Out-Null
}

Write-Progress -Activity "Scanning media" -Completed

# ---------- Write outputs ----------
$results | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $csvPath
$script:logLines | Out-File -Encoding UTF8 -LiteralPath $logPath

# ---------- Console summary (human readable) ----------
$reasonCounts = $results |
  Where-Object { $_.suspect } |
  ForEach-Object { $_.reason_codes -split "\|" } |
  Where-Object { $_ } |
  Group-Object |
  Sort-Object Count -Descending

$extCounts = $results | Group-Object extension | Sort-Object Count -Descending

Write-Host ""
Write-Host "DONE"
Write-Host ("Scanned : {0}" -f $results.Count)
Write-Host ("OK     : {0}" -f $okCount)
Write-Host ("Suspect: {0}" -f $susCount)
Write-Host ("Quarantine: {0}" -f $quarantine)
Write-Host ("CSV: {0}" -f $csvPath)
Write-Host ("Log: {0}" -f $logPath)
Write-Host ""

Write-Host "Top Suspect Reasons:"
if ($reasonCounts.Count -eq 0) {
  Write-Host "  (none)"
} else {
  $reasonCounts | Select-Object -First 12 | ForEach-Object {
    "{0,6}  {1}" -f $_.Count, $_.Name
  } | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "Files by extension:"
$extCounts | Select-Object -First 12 | ForEach-Object {
  "{0,6}  {1}" -f $_.Count, $_.Name
} | ForEach-Object { Write-Host "  $_" }

Write-Host ""
$null = Read-Host "Press Enter"
