$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$UploadRoot = Join-Path $RepoRoot ".ai_uploads"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunName = "hp290_stage03_allocate_media_volume_$Stamp"
$RunOut = Join-Path $UploadRoot $RunName
$LocalZip = Join-Path $UploadRoot "$RunName.zip"
$Log = Join-Path $RunOut "x1_launcher.log.txt"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RemoteScriptLocal = Join-Path $ScriptDir "remote\stage_03_allocate_media_volume.sh"
$RemoteTarget = "andrew@theboys-hp290"
$RemoteScript = "/tmp/stage_03_allocate_media_volume_$Stamp.sh"
$RemoteZip = "/home/andrew/media_server_setup_evidence/stage_03_allocate_media_volume_$Stamp.zip"
$LvSize = "700G"

New-Item -ItemType Directory -Force -Path $RunOut | Out-Null
New-Item -ItemType Directory -Force -Path $UploadRoot | Out-Null

function Write-StageLog {
    param([string]$Message)
    $Line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $Line | Tee-Object -FilePath $Log -Append
}

function Invoke-LoggedNative {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    $SafeLabel = $Label -replace '[^A-Za-z0-9_-]', '_'
    $StdOut = Join-Path $RunOut "$SafeLabel.stdout.log.txt"
    $StdErr = Join-Path $RunOut "$SafeLabel.stderr.log.txt"

    Write-StageLog ""
    Write-StageLog "START: $Label"
    Write-StageLog "CMD: $FilePath $($ArgumentList -join ' ')"

    & $FilePath @ArgumentList 1> $StdOut 2> $StdErr
    $ExitCode = $LASTEXITCODE

    if (Test-Path -LiteralPath $StdOut) {
        Get-Content -LiteralPath $StdOut -Raw -ErrorAction SilentlyContinue | Add-Content -LiteralPath $Log -Encoding UTF8
    }
    if (Test-Path -LiteralPath $StdErr) {
        Get-Content -LiteralPath $StdErr -Raw -ErrorAction SilentlyContinue | Add-Content -LiteralPath $Log -Encoding UTF8
    }

    if ($ExitCode -ne 0) {
        Write-StageLog "FAIL: $Label exit_code=$ExitCode"
        throw "$Label failed. See $Log"
    }

    Write-StageLog "PASS: $Label"
}

if (-not (Test-Path -LiteralPath $RemoteScriptLocal)) {
    throw "Missing remote script: $RemoteScriptLocal"
}

Write-StageLog "HP290 Stage 03 media volume allocation"
Write-StageLog "Run folder: $RunOut"
Write-StageLog "Remote script: $RemoteScript"
Write-StageLog "Remote zip: $RemoteZip"
Write-StageLog "Local zip: $LocalZip"
Write-StageLog "Requested LV size: $LvSize"

Invoke-LoggedNative -Label "Check SSH" -FilePath "ssh" -ArgumentList @("-V")
Invoke-LoggedNative -Label "Copy stage 03 script to HP" -FilePath "scp" -ArgumentList @($RemoteScriptLocal, "${RemoteTarget}:$RemoteScript")

Write-StageLog ""
Write-StageLog "START: Run stage 03 script on HP"
Write-StageLog "You may be prompted for the HP sudo password."
& ssh -tt $RemoteTarget "bash $RemoteScript $Stamp $LvSize" 2>&1 | Tee-Object -FilePath (Join-Path $RunOut "Run_stage_03_script_on_HP.console.log.txt")
$RemoteExitCode = $LASTEXITCODE
if ($RemoteExitCode -ne 0) {
    Write-StageLog "FAIL: Run stage 03 script on HP exit_code=$RemoteExitCode"
    throw "Stage 03 remote script failed. See $RunOut"
}
Write-StageLog "PASS: Run stage 03 script on HP"

Invoke-LoggedNative -Label "Copy stage 03 ZIP back to X1" -FilePath "scp" -ArgumentList @("${RemoteTarget}:$RemoteZip", $LocalZip)

if (-not (Test-Path -LiteralPath $LocalZip)) {
    throw "Expected ZIP was not copied back: $LocalZip"
}

Write-StageLog "COMPLETE"
Write-StageLog "UPLOAD THIS ZIP: $LocalZip"

Write-Host ""
Write-Host "UPLOAD THIS ZIP:"
Write-Host $LocalZip
Write-Host ""
Read-Host "Press Enter to close"
