$ErrorActionPreference = 'Stop'
$repo_root = 'C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie'
$editor_port = 8787
$editor_url = "http://127.0.0.1:$editor_port/web/inputs_editor.html"
$health_url = "http://127.0.0.1:$editor_port/api/health"
$server_script = Join-Path $repo_root 'tools\inputs_editor\inputs_editor_server.py'

function Test-EditorHealth {
    try {
        $response = Invoke-WebRequest -Uri $health_url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

Set-Location $repo_root

if (-not (Test-EditorHealth)) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw 'Python was not found in PATH.'
    }

    Start-Process powershell -WindowStyle Normal -ArgumentList @(
        '-NoLogo',
        '-NoExit',
        '-Command',
        "Set-Location `"$repo_root`"; & `"$($python.Source)`" `"$server_script`" --port $editor_port"
    ) | Out-Null

    $healthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-EditorHealth) {
            $healthy = $true
            break
        }
    }
    if (-not $healthy) {
        throw "Inputs editor server did not become healthy on port $editor_port."
    }
}

Start-Process $editor_url | Out-Null
