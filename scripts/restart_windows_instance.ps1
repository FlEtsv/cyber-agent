param(
    [switch]$ApiOnly,
    [switch]$KeepTaskboardListener,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"

function Get-AgentProcessTargets {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -like "python*" -and
            $_.CommandLine -and
            $_.CommandLine -match [regex]::Escape([string]$Root) -and
            (
                $_.CommandLine -match "main\.py" -or
                $_.CommandLine -match "uvicorn app\.api\.server" -or
                $_.CommandLine -match "scripts[\\/]start_local_api\.py" -or
                ((-not $KeepTaskboardListener) -and $_.CommandLine -match "scripts[\\/]taskboard_listener\.py")
            )
        } |
        Select-Object ProcessId, ParentProcessId, Name, CommandLine
}

function Wait-HttpOk {
    param([string[]]$Url, [int]$TimeoutSec = 25)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        foreach ($candidate in $Url) {
            try {
                $resp = Invoke-WebRequest -UseBasicParsing -Uri $candidate -TimeoutSec 3
                if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                    return $true
                }
            } catch {
                Start-Sleep -Milliseconds 250
            }
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Import-UserEnvForChild {
    $names = @(
        "CYBERAGENT_FAST_MODEL",
        "CYBERAGENT_POWER_MODEL",
        "CYBERAGENT_MISTRAL_MODEL",
        "CYBERAGENT_FAST_KEEP_ALIVE",
        "CYBERAGENT_POWER_KEEP_ALIVE",
        "MISTRAL_API_KEY",
        "MISTRAL_STUDIO_API_KEY",
        "MISTRAL_BASE_URL"
    )

    foreach ($name in $names) {
        $value = [Environment]::GetEnvironmentVariable($name, "User")
        if ($null -ne $value -and $value -ne "") {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

if (-not (Test-Path $Python)) {
    throw "Python venv no encontrado: $Python"
}
if (-not $ApiOnly -and -not (Test-Path $Pythonw)) {
    throw "pythonw venv no encontrado: $Pythonw"
}

$targets = @(Get-AgentProcessTargets)
if ($targets.Count -gt 0) {
    Write-Host "Stopping CyberAgent project processes:" -ForegroundColor Yellow
    $targets | Format-Table ProcessId, ParentProcessId, Name, CommandLine -AutoSize
}

if (-not $DryRun) {
    foreach ($p in $targets) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

if ($DryRun) {
    Write-Host "DryRun: no processes stopped or started." -ForegroundColor Cyan
    exit 0
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null
Import-UserEnvForChild

if ($env:CYBERAGENT_FAST_MODEL) {
    Write-Host "Child env: CYBERAGENT_FAST_MODEL=$env:CYBERAGENT_FAST_MODEL" -ForegroundColor DarkGray
}
if ($env:CYBERAGENT_POWER_MODEL) {
    Write-Host "Child env: CYBERAGENT_POWER_MODEL=$env:CYBERAGENT_POWER_MODEL" -ForegroundColor DarkGray
}
if ($env:CYBERAGENT_MISTRAL_MODEL) {
    Write-Host "Child env: CYBERAGENT_MISTRAL_MODEL=$env:CYBERAGENT_MISTRAL_MODEL" -ForegroundColor DarkGray
}

if ($ApiOnly) {
    Write-Host "Starting standalone local API..." -ForegroundColor Cyan
    Start-Process -FilePath $Python `
        -ArgumentList @("scripts\start_local_api.py") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput (Join-Path $Root "logs\local-api.out.log") `
        -RedirectStandardError (Join-Path $Root "logs\local-api.err.log") `
        -WindowStyle Hidden | Out-Null
} else {
    Write-Host "Starting CyberAgent desktop instance..." -ForegroundColor Cyan
    Start-Process -FilePath $Pythonw `
        -ArgumentList "main.py" `
        -WorkingDirectory $Root `
        -WindowStyle Hidden | Out-Null
}

$apiOk = Wait-HttpOk @("http://127.0.0.1:8765/api/status", "http://localhost:8765/api/status") 35
if ($apiOk) {
    Write-Host "Local API ready: http://127.0.0.1:8765/api/status" -ForegroundColor Green
} else {
    Write-Host "Local API did not become ready within timeout." -ForegroundColor Yellow
}

& (Join-Path $PSScriptRoot "ops_health.ps1")
