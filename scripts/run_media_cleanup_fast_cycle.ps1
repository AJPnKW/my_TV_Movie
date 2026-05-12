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

Log 'Fast cleanup cycle v0.6.6'
$pipeline=Join-Path $RepoRoot 'tools\media_renamer\media_cleanup_pipeline.py'
$ra=RepoArg
for($pass=1;$pass -le 5;$pass++){
  Run-Python @($pipeline,'plan',$ra,$RepoRoot,'--media-root',$MediaRoot) "Plan pass $pass"
  $latest=Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'reports\media_renamer') -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'scan_plan.json') } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $ready=0
  if($latest){ $json=Get-Content -LiteralPath (Join-Path $latest.FullName 'scan_plan.json') -Raw -Encoding UTF8 | ConvertFrom-Json; $ready=[int]$json.summary.ready_to_fix }
  Log "ready_to_fix=$ready"
  if($ready -le 0){ break }
  Run-Python @($pipeline,'apply',$ra,$RepoRoot,'--media-root',$MediaRoot) "Apply pass $pass"
}
$gen=Join-Path $RepoRoot 'tools\media_renamer\media_library_page.py'
Run-Python @($gen,'generate','--repo',$RepoRoot,'--media-root',$MediaRoot,'--http-host','AJP-Laptop-X1CG10','--http-port','8010') 'Generate library page'
Log "PASS. Log: $Script:Log"
