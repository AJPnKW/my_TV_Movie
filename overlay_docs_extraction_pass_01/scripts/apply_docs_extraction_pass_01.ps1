#requires -version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepoRoot = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$OverlayRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $RepoRoot 'logs'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogPath = Join-Path $LogDir ("apply_docs_extraction_pass_01_{0}.log.txt" -f $Stamp)
function Ensure-Directory { param([string]$Path) if(-not(Test-Path -LiteralPath $Path)){ New-Item -ItemType Directory -Force -Path $Path | Out-Null } }
function Write-Log { param([string]$Message) $line='[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),$Message; Write-Host $line; Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 }
Ensure-Directory $LogDir
Write-Log 'START docs extraction pass 01 overlay'
Set-Location -LiteralPath $RepoRoot
if(-not(Test-Path -LiteralPath '.git')){ throw 'Not a git repository' }
$files=@(
 'docs\_extraction\extraction_pass_01_working_log.html',
 'docs\_extraction\master_contract_change_control_amendment.html',
 'reports\documentation_consolidation\source_document_register.csv',
 'reports\documentation_consolidation\heading_line_index.csv',
 'reports\documentation_consolidation\requirement_signal_line_index.csv',
 'reports\documentation_consolidation\documentation_gap_register_pass_01.html'
)
foreach($rel in $files){
  $src=Join-Path $OverlayRoot $rel
  $dst=Join-Path $RepoRoot $rel
  if(-not(Test-Path -LiteralPath $src)){ throw "Missing overlay file: $src" }
  Ensure-Directory (Split-Path -Parent $dst)
  Copy-Item -LiteralPath $src -Destination $dst -Force
  Write-Log "INSTALLED $rel"
}
Write-Log 'VALIDATION PASSED'
Write-Log 'NEXT: git add docs/_extraction reports/documentation_consolidation'
Write-Log 'NEXT: git commit -m "record documentation extraction pass 01"'
Write-Log 'END docs extraction pass 01 overlay'
