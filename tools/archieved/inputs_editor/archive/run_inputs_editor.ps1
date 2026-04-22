<#
FILE: tools/inputs_editor/run_inputs_editor.ps1
VERSION: 1.0.1
DATE: 2026-01-19

CHANGELOG
- 1.0.1: Add explicit version header + section comments. No functional changes.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"
Set-Location $repo

python ".\tools\inputs_editor\inputs_editor_server.py" --port 8787
Read-Host "Press Enter"
