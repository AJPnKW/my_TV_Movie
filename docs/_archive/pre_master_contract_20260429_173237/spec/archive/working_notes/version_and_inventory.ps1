# Working parent folder
$Root = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\docs\FULL authoritative spec"

# Inventory file
$Inventory = Join-Path $Root "SPEC_INVENTORY.csv"

# Ensure inventory exists
if (-not (Test-Path $Inventory)) {
    "FileName,Folder,SizeBytes,Created,Retired" | Out-File $Inventory -Encoding UTF8
}

# Get all .md files (non-versioned or versioned)
$files = Get-ChildItem -Path $Root -Recurse -Filter *.md

foreach ($file in $files) {

    $name = $file.BaseName
    $ext  = $file.Extension
    $dir  = $file.DirectoryName

    # Detect version suffix
    if ($name -match "_V(\d+)\.(\d+)$") {
        # Existing version found → increment
        $major = [int]$matches[1]
        $minor = [int]$matches[2]

        $minor++
        $newVersion = "{0}.{1:00}" -f $major, $minor
        $baseName = $name -replace "_V\d+\.\d+$",""
    }
    else {
        # No version → start at V0.00
        $baseName = $name
        $newVersion = "0.00"
    }

    # Build new filename
    $newFileName = "${baseName}_V$newVersion$ext"
    $newPath = Join-Path $dir $newFileName

    # Copy file to new version
    Copy-Item -Path $file.FullName -Destination $newPath -Force

    # Update inventory: retire old version
    $escapedOld = $file.Name.Replace('"','""')
    $lines = Get-Content $Inventory
    $updated = $lines | ForEach-Object {
        if ($_ -like "$escapedOld,*" -and $_ -notlike "*,Retired") {
            $_ -replace ",$", ",$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        } else {
            $_
        }
    }
    $updated | Set-Content $Inventory -Encoding UTF8

    # Add new version to inventory
    $size = (Get-Item $newPath).Length
    $created = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "`"$newFileName`",""$dir`",$size,$created,""" | Add-Content $Inventory -Encoding UTF8
}
