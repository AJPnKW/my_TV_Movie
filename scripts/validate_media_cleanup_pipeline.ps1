$ErrorActionPreference = "Stop"

$Repo = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$LogRoot = Join-Path $Repo "reports\media_renamer_launcher_logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogRoot "validate_$Stamp.log.txt"

function Write-RunLog {
    param([string]$Message)
    $Line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $Line | Tee-Object -FilePath $Log -Append
}

$Python = "C:\Users\andrew\_shell\.venv_py312\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "py"
    $ArgsPrefix = @("-3.12")
} else {
    $ArgsPrefix = @()
}

Set-Location -LiteralPath $Repo
Write-RunLog "Validating media cleanup pipeline..."
& $Python @ArgsPrefix "scripts\validate_media_renamer.py" 2>&1 | Tee-Object -FilePath $Log -Append
if ($LASTEXITCODE -ne 0) { throw "Validation failed. See log: $Log" }
Write-RunLog "Validation completed. Log: $Log"
Read-Host "Press Enter to close"
