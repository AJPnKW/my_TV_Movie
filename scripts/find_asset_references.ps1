$specPath = "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\docs\FULL authoritative spec"

$patterns = @(
    "image/",
    "shows/",
    "movies/",
    "services_logos",
    "poster",
    "backdrop",
    "still",
    "logo",
    "icon"
)

Select-String -Path "$specPath\*.md" -Pattern $patterns |
    Select-Object Filename, LineNumber, Line |
    Format-Table -AutoSize
