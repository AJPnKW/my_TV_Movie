$ErrorActionPreference = "Stop"
$RepoRoot = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
$MediaRoot = "C:\X1_Share\Recordings"
$LogDir = Join-Path $RepoRoot "reports\media_renamer_launcher_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Script:Log = Join-Path $LogDir ((Split-Path -Leaf $PSCommandPath).Replace('.ps1','') + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log.txt')
function Log([string]$m){ $line='[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),$m; Write-Host $line; Add-Content -LiteralPath $Script:Log -Value $line -Encoding UTF8 }
function Ensure-Python(){
  $venv = Join-Path $RepoRoot '.venv_media_cleanup'
  $py = Join-Path $venv 'Scripts\python.exe'
  if (!(Test-Path -LiteralPath $py)){
    Log "Creating Python 3.12 venv"
    & py -3.12 -m venv $venv *>> $Script:Log
    if ($LASTEXITCODE -ne 0){ throw "Python venv creation failed. Log: $Script:Log" }
  }
  if (!(Test-Path -LiteralPath $py)){ throw "Python executable missing: $py" }
  return $py
}
function Run-Python([string[]]$Args,[string]$Label){
  $py=Ensure-Python
  Log "START: $Label"
  Log ("CMD: {0} {1}" -f $py, ($Args -join ' '))
  & $py @Args *>> $Script:Log
  $code=$LASTEXITCODE
  Log "EXIT: $Label = $code"
  if ($code -ne 0){ throw "$Label failed. Log: $Script:Log" }
}
function RepoArg(){
  $p=Join-Path $RepoRoot 'tools\media_renamer\media_cleanup_pipeline.py'
  if (!(Test-Path -LiteralPath $p)){ throw "Missing pipeline: $p" }
  $t=Get-Content -LiteralPath $p -Raw -Encoding UTF8
  if ($t -match '--repo-root'){ return '--repo-root' }
  return '--repo'
}
Set-Location -LiteralPath $RepoRoot

Log 'Repair Your Friends and Neighbors playback v0.6.6'
$script=Join-Path $RepoRoot 'tools\media_renamer\media_playback_qa.py'
Run-Python @($script,'repair-known','--repo',$RepoRoot,'--media-root',$MediaRoot) 'Repair known playback files'
Log "PASS. Log: $Script:Log"
