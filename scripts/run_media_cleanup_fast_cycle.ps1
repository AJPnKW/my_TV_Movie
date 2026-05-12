# FILE: scripts/run_media_cleanup_fast_cycle.ps1
# VERSION: v0.6.8
# UPDATED: 2026-05-11
# NOTE: Kept for GUI compatibility. Calls the integrated pipeline.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
& 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\scripts\run_media_cleanup_integrated.ps1'
