param(
    [switch]$StartApi
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

function Test-HttpJson {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [int]$TimeoutSec = 5
    )
    try {
        $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec $TimeoutSec
        return [pscustomobject]@{
            ok = $true
            status = $response.StatusCode
            body = $response.Content
        }
    } catch {
        return [pscustomobject]@{
            ok = $false
            status = $null
            body = $_.Exception.Message
        }
    }
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python venv not found at $python"
}

$results = [ordered]@{}
$results.git = (git status --short --branch) -join "`n"
$results.python = (& $python --version) -join "`n"

& $python -m pytest tests | Tee-Object -Variable pytestOutput | Out-Null
$results.pytest = ($pytestOutput | Select-Object -Last 3) -join "`n"

$ollama = Test-HttpJson "http://127.0.0.1:11434/api/tags" 5
$results.ollama = if ($ollama.ok) { "HTTP $($ollama.status)" } else { $ollama.body }

$api = Test-HttpJson "http://127.0.0.1:8765/api/status" 5
if (-not $api.ok -and $StartApi) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null
    $out = Join-Path $root "logs\local-api.out.log"
    $err = Join-Path $root "logs\local-api.err.log"
    Start-Process -FilePath $python `
        -ArgumentList @("scripts\start_local_api.py") `
        -WorkingDirectory $root `
        -RedirectStandardOutput $out `
        -RedirectStandardError $err `
        -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 5
    $api = Test-HttpJson "http://127.0.0.1:8765/api/status" 8
}
$results.local_api = if ($api.ok) { "HTTP $($api.status) $($api.body)" } else { $api.body }

[pscustomobject]$results
