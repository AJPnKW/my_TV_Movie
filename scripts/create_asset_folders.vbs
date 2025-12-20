' ============================================================
' Create canonical asset folder structure for My TV Hub
' Spec‑aligned folder layout (Section 7 — Assets)
' ============================================================

Option Explicit

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

' Root folder
CreateFolderIfMissing "assets"

' Posters
CreateFolderIfMissing "assets\posters"
CreateFolderIfMissing "assets\posters\shows"
CreateFolderIfMissing "assets\posters\seasons"
CreateFolderIfMissing "assets\posters\movies"

' Backdrops
CreateFolderIfMissing "assets\backdrops"
CreateFolderIfMissing "assets\backdrops\shows"
CreateFolderIfMissing "assets\backdrops\movies"

' Episode stills
CreateFolderIfMissing "assets\stills"
CreateFolderIfMissing "assets\stills\episodes"

' Logos
CreateFolderIfMissing "assets\logos"
CreateFolderIfMissing "assets\logos\services"
CreateFolderIfMissing "assets\logos\services\archive"

' Icons
CreateFolderIfMissing "assets\icons"

' Fallback images
CreateFolderIfMissing "assets\fallback"

' Collections (future-phase)
CreateFolderIfMissing "assets\collections"

WScript.Echo "Canonical asset folder structure created successfully."

' ============================================================
' Helper function
' ============================================================
Sub CreateFolderIfMissing(path)
    If Not fso.FolderExists(path) Then
        fso.CreateFolder(path)
    End If
End Sub
