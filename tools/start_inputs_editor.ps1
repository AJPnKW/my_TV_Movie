$ErrorActionPreference = 'Stop'
$repo_root = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$editor_port = 8787
$editor_url = "http://127.0.0.1:$editor_port/web/inputs_editor.html"
$server_script = Join-Path $repo_root 'tools\inputs_editor\inputs_editor_server.py'
Set-Location $repo_root
$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and
    $_.CommandLine -like "*inputs_editor_server.py*" -and
    $_.CommandLine -like "*--port $editor_port*"
}
if (-not $existing) {
    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-Command',
        "cd `"$repo_root`"; python `"$server_script`" --port $editor_port"
    )
    Start-Sleep -Seconds 3
}
Start-Process $editor_url
