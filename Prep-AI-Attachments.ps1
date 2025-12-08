function Copy-WithTxt {
    param([string]$SourcePath,[string]$TargetFolder)
    $nameOnly = [System.IO.Path]::GetFileName($SourcePath)
    $lowerName = $nameOnly.ToLower()

    # Skip current execution logs
    if ($SourcePath -eq $PsLogPath -or $SourcePath -eq $env:BATLOG) {
        Write-Log "Skipped current execution log: $SourcePath"
        return
    }

    # Skip BAT and PS1 files to prevent circular loops
    if ($lowerName.EndsWith(".bat") -or $lowerName.EndsWith(".ps1")) {
        Write-Log "Skipped script file: $SourcePath"
        return
    }

    # Prevent .txt.txt duplication
    $isAlreadyTxtLike = ($lowerName.EndsWith(".txt") -or $lowerName.EndsWith(".log.txt") -or $lowerName.EndsWith(".md"))

    if (Has-ExcludedExtension -Path $SourcePath) { Write-Log "Excluded by extension: $SourcePath"; return }
    if (Is-DotPrefixed -Name $nameOnly) { Write-Log "Excluded dot-prefixed: $SourcePath"; return }

    $destName = if ($isAlreadyTxtLike) { $nameOnly } else { "$nameOnly.txt" }
    $destPath = Join-Path $TargetFolder $destName

    if (Should-NormalizeUtf8 -Path $SourcePath) {
        Normalize-ToUtf8NoBom -SourcePath $SourcePath -DestPath $destPath
    } else {
        Copy-Item -LiteralPath $SourcePath -Destination $destPath -Force
        Write-Log "Copied (no UTF-8 normalization): $SourcePath -> $destPath"
    }
}
