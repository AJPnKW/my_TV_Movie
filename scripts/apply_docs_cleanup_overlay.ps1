# Version: 1.0.0
# Purpose: Safe docs-tree cleanup and normalization overlay apply script.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = 'INFO'
    )
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    Add-Content -Path $script:LogFile -Value $line
}

function Ensure-Directory {
    param([string]$PathValue)
    if (-not (Test-Path -LiteralPath $PathValue)) {
        New-Item -ItemType Directory -Path $PathValue -Force | Out-Null
    }
}

function Write-Inventory {
    param(
        [string]$RootPath,
        [string]$OutputPath
    )
    Get-ChildItem -LiteralPath $RootPath -Recurse -File |
        Sort-Object FullName |
        Select-Object FullName, Length, LastWriteTime |
        Format-Table -AutoSize |
        Out-String -Width 4096 |
        Set-Content -Path $OutputPath -Encoding UTF8
}

function Move-IfExists {
    param(
        [string]$SourcePath,
        [string]$TargetPath
    )
    if (Test-Path -LiteralPath $SourcePath) {
        Ensure-Directory -PathValue ([System.IO.Path]::GetDirectoryName($TargetPath))
        if (Test-Path -LiteralPath $TargetPath) {
            Write-Log "Target already exists, skipping move: $TargetPath" 'WARN'
        }
        else {
            Move-Item -LiteralPath $SourcePath -Destination $TargetPath
            Write-Log "Moved: $SourcePath -> $TargetPath"
        }
    }
    else {
        Write-Log "Source not found, skipping: $SourcePath" 'WARN'
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$DocsRoot = Join-Path $RepoRoot 'docs'
if (-not (Test-Path -LiteralPath $DocsRoot)) {
    throw "Docs folder not found at: $DocsRoot"
}

$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunRoot = Join-Path $RepoRoot ".ai_downloads\docs_cleanup_$Timestamp"
$BackupRoot = Join-Path $RunRoot 'backup'
$LogsRoot = Join-Path $RunRoot 'logs'
$ReportsRoot = Join-Path $RunRoot 'reports'
$ArchiveRoot = Join-Path $DocsRoot "_archive\$Timestamp"
$SpecArchiveRoot = Join-Path $DocsRoot 'spec\archive'

Ensure-Directory -PathValue $RunRoot
Ensure-Directory -PathValue $BackupRoot
Ensure-Directory -PathValue $LogsRoot
Ensure-Directory -PathValue $ReportsRoot
Ensure-Directory -PathValue $ArchiveRoot
Ensure-Directory -PathValue $SpecArchiveRoot

$script:LogFile = Join-Path $LogsRoot 'apply_docs_cleanup_overlay.log.txt'
"Docs cleanup overlay run started" | Set-Content -Path $script:LogFile -Encoding UTF8

Write-Log "Repo root: $RepoRoot"
Write-Log "Docs root: $DocsRoot"

$BackupZip = Join-Path $BackupRoot 'docs_pre_cleanup.zip'
Write-Log "Creating backup zip: $BackupZip"
if (Test-Path -LiteralPath $BackupZip) { Remove-Item -LiteralPath $BackupZip -Force }
Compress-Archive -Path (Join-Path $DocsRoot '*') -DestinationPath $BackupZip -CompressionLevel Optimal

$PreInventory = Join-Path $ReportsRoot 'docs_inventory_before.txt'
$PostInventory = Join-Path $ReportsRoot 'docs_inventory_after.txt'
Write-Inventory -RootPath $DocsRoot -OutputPath $PreInventory
Write-Log "Wrote pre-clean inventory"

# Safe archive moves.
Move-IfExists -SourcePath (Join-Path $DocsRoot 'doc_folder-.md-files.zip') -TargetPath (Join-Path $ArchiveRoot 'source_drops\doc_folder-.md-files.zip')
Move-IfExists -SourcePath (Join-Path $DocsRoot 'actual text of the ChatGPT responsesQ1-Q5.txt') -TargetPath (Join-Path $ArchiveRoot 'chat_exports\actual text of the ChatGPT responsesQ1-Q5.txt')
Move-IfExists -SourcePath (Join-Path $DocsRoot 'spec\..NOTES for the FULL authoritative spec+plan.md') -TargetPath (Join-Path $ArchiveRoot 'spec_working_noise\..NOTES for the FULL authoritative spec+plan.md')
Move-IfExists -SourcePath (Join-Path $DocsRoot 'spec\my_TV_Movies- authoritative spec.tws') -TargetPath (Join-Path $ArchiveRoot 'spec_binary_workspace\my_TV_Movies- authoritative spec.tws')
Move-IfExists -SourcePath (Join-Path $DocsRoot 'spec\archived,Section 5.6 #U2014 Person Popup (future phase).md') -TargetPath (Join-Path $SpecArchiveRoot 'Section 5.6 - Person Popup (future phase).md')

# Safe filename normalization for active spec docs.
$RenameMap = @(
    @{ Old = 'Section 0 #U2014 Index.md'; New = 'Section 0 - Index.md' },
    @{ Old = 'Section 1 #U2014 Global Rules.md'; New = 'Section 1 - Global Rules.md' },
    @{ Old = 'Section 2 #U2014 Architecture.md'; New = 'Section 2 - Architecture.md' },
    @{ Old = 'Section 3 #U2014 Data Model.md'; New = 'Section 3 - Data Model.md' },
    @{ Old = 'Section 4 #U2014 UI (each view separately).md'; New = 'Section 4 - UI (each view separately).md' },
    @{ Old = 'Section 4.1 #U2014 Calendar View.md'; New = 'Section 4.1 - Calendar View.md' },
    @{ Old = 'Section 4.2 #U2014 Shows View.md'; New = 'Section 4.2 - Shows View.md' },
    @{ Old = 'Section 4.3 #U2014 Movies View.md'; New = 'Section 4.3 - Movies View.md' },
    @{ Old = 'Section 4.4 #U2014 Live TV View.md'; New = 'Section 4.4 - Live TV View.md' },
    @{ Old = 'Section 4.5 #U2014 Config View.md'; New = 'Section 4.5 - Config View.md' },
    @{ Old = 'Section 4.6 #U2014 Explore View (future phase).md'; New = 'Section 4.6 - Explore View (future phase).md' },
    @{ Old = 'Section 4.7 #U2014 Profiles View (future phase).md'; New = 'Section 4.7 - Profiles View (future phase).md' },
    @{ Old = 'Section 4.8 #U2014 Watchlist - Watched Filters (future phase).md'; New = 'Section 4.8 - Watchlist - Watched Filters (future phase).md' },
    @{ Old = 'Section 4.9 #U2014 Watchlist (Standalone Page).md'; New = 'Section 4.9 - Watchlist (Standalone Page).md' },
    @{ Old = 'Section 5 #U2014 Popups.md'; New = 'Section 5 - Popups.md' },
    @{ Old = 'Section 5.1 #U2014 Show Popup (P1).md'; New = 'Section 5.1 - Show Popup (P1).md' },
    @{ Old = 'Section 5.2 #U2014 Season Popup (P2).md'; New = 'Section 5.2 - Season Popup (P2).md' },
    @{ Old = 'Section 5.3 #U2014 Episode Popup (P3).md'; New = 'Section 5.3 - Episode Popup (P3).md' },
    @{ Old = 'Section 5.4 #U2014 Movie Popup (P4).md'; New = 'Section 5.4 - Movie Popup (P4).md' },
    @{ Old = 'Section 5.5 #U2014 Collection Popup (future phase).md'; New = 'Section 5.5 - Collection Popup (future phase).md' },
    @{ Old = 'Section 6 #U2014 UX.md'; New = 'Section 6 - UX.md' },
    @{ Old = 'Section 7 #U2014 Assets.md'; New = 'Section 7 - Assets.md' },
    @{ Old = 'Section 8 #U2014 Scripts.md'; New = 'Section 8 - Scripts.md' },
    @{ Old = 'Section 9 #U2014 Workflow.md'; New = 'Section 9 - Workflow.md' },
    @{ Old = 'Section 10 #U2014 Versioning.md'; New = 'Section 10 - Versioning.md' },
    @{ Old = 'Section 11 #U2014 Errors.md'; New = 'Section 11 - Errors.md' },
    @{ Old = 'Section 12 #U2014 Future#U2011Phase.md'; New = 'Section 12 - Future-Phase.md' },
    @{ Old = 'Section 13 #U2014 Invariants.md'; New = 'Section 13 - Invariants.md' }
)

foreach ($Entry in $RenameMap) {
    $OldPath = Join-Path $DocsRoot ("spec\" + $Entry.Old)
    $NewPath = Join-Path $DocsRoot ("spec\" + $Entry.New)
    if (Test-Path -LiteralPath $OldPath) {
        if (Test-Path -LiteralPath $NewPath) {
            Write-Log "Normalized target already exists, skipping rename: $NewPath" 'WARN'
        }
        else {
            Rename-Item -LiteralPath $OldPath -NewName $Entry.New
            Write-Log "Renamed: $($Entry.Old) -> $($Entry.New)"
        }
    }
}

Write-Inventory -RootPath $DocsRoot -OutputPath $PostInventory
Write-Log "Wrote post-clean inventory"

$RunZip = Join-Path $RunRoot 'docs_cleanup_run_bundle.zip'
if (Test-Path -LiteralPath $RunZip) { Remove-Item -LiteralPath $RunZip -Force }
Compress-Archive -Path (Join-Path $RunRoot '*') -DestinationPath $RunZip -CompressionLevel Optimal
Write-Log "Created run bundle zip: $RunZip"

Write-Log "Completed docs cleanup overlay apply"
Write-Host ''
Write-Host 'DONE'
Write-Host "Run folder: $RunRoot"
Write-Host "Run zip:    $RunZip"
Read-Host 'Press Enter to close'
