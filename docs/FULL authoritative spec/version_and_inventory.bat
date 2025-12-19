@echo off
setlocal enabledelayedexpansion

REM --- Set working directory ---
set ROOT=C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\docs\FULL authoritative spec

REM --- Timestamp for log file ---
for /f "tokens=1-3 delims=/- " %%a in ("%date%") do (
    set YYYY=%%c
    set MM=%%a
    set DD=%%b
)
for /f "tokens=1-3 delims=:." %%a in ("%time%") do (
    set HH=%%
