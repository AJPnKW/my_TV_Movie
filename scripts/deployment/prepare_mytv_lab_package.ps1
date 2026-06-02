[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$OutputDir = (Join-Path $RepoRoot 'deployment\packages')
)

$ErrorActionPreference = 'Stop'

function Add-PackageItem {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$StageRoot
    )

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        throw "Required package source missing: $SourcePath"
    }

    $targetPath = Join-Path $StageRoot $RelativePath
    $targetParent = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $targetPath -Force
}

$repo = Resolve-Path -LiteralPath $RepoRoot
$repoPath = $repo.Path

$requiredFiles = @(
    'deployment\README.md',
    'deployment\docs\vm_migration_bootstrap.md',
    'deployment\vm_lab\README.md',
    'deployment\vm_lab\bootstrap_ubuntu_mytv_lab.sh',
    'deployment\vm_lab\validate_mytv_lab.sh',
    'deployment\webserver\README.md',
    'docs\mytv_vm_migration_control_plan.html'
)

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$packageName = "mytv-lab-vm-bootstrap-$stamp"
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) $packageName
$zipPath = Join-Path $OutputDir "$packageName.zip"

if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

foreach ($relativeFile in $requiredFiles) {
    $source = Join-Path $repoPath $relativeFile
    Add-PackageItem -SourcePath $source -RelativePath $relativeFile -StageRoot $stageRoot
}

$manifestPath = Join-Path $stageRoot 'LAB_PACKAGE_MANIFEST.txt'
$manifestLines = @(
    'my_TV_Movie X1 lab VM bootstrap package',
    "Created: $(Get-Date -Format o)",
    "Repo: $repoPath",
    '',
    'Included files:'
) + $requiredFiles

Set-Content -LiteralPath $manifestPath -Value $manifestLines -Encoding UTF8

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -Path (Join-Path $stageRoot '*') -DestinationPath $zipPath -Force

Write-Host "Created package: $zipPath"
Write-Host 'No VM was created. Copy the package to the Ubuntu lab VM or unpack it from the host as needed.'
