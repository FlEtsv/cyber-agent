param(
    [switch]$Json,
    [switch]$Detailed
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv\Scripts\python.exe"

function Get-HttpStatus {
    param([string[]]$Url, [int]$TimeoutSec = 4, [int]$Attempts = 2)
    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in $Url) {
        for ($i = 0; $i -lt $Attempts; $i++) {
            try {
                $resp = Invoke-WebRequest -UseBasicParsing -Uri $candidate -TimeoutSec $TimeoutSec
                return [pscustomobject]@{
                    ok = $true
                    url = $candidate
                    status = $resp.StatusCode
                    body = $resp.Content
                }
            } catch {
                $errors.Add("$candidate -> $($_.Exception.Message)")
                Start-Sleep -Milliseconds 300
            }
        }
    }
    return [pscustomobject]@{
        ok = $false
        url = ($Url -join ",")
        status = $null
        body = ($errors -join " | ")
    }
}

function Get-AgentProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -like "python*" -and
            $_.CommandLine -and
            $_.CommandLine -match [regex]::Escape([string]$Root)
        } |
        Select-Object ProcessId, ParentProcessId, Name, CommandLine
}

function Get-LogicalInstanceCount {
    param([object[]]$ProcessGroup)
    if (-not $ProcessGroup -or $ProcessGroup.Count -eq 0) {
        return 0
    }
    $ids = @{}
    foreach ($p in $ProcessGroup) {
        $ids[[int]$p.ProcessId] = $true
    }
    $roots = @($ProcessGroup | Where-Object { -not $ids.ContainsKey([int]$_.ParentProcessId) })
    return $roots.Count
}

$processes = @(Get-AgentProcesses)
$mainProcesses = @($processes | Where-Object { $_.CommandLine -match "main\.py" })
$apiProcesses = @($processes | Where-Object { $_.CommandLine -match "uvicorn app\.api\.server|scripts[\\/]start_local_api\.py" })
$listenerProcesses = @($processes | Where-Object { $_.CommandLine -match "scripts[\\/]taskboard_listener\.py" })
$mainLogical = Get-LogicalInstanceCount $mainProcesses
$apiLogical = Get-LogicalInstanceCount $apiProcesses
$listenerLogical = Get-LogicalInstanceCount $listenerProcesses
$port8765 = @(Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, State, OwningProcess)

$api = Get-HttpStatus @("http://127.0.0.1:8765/api/status", "http://localhost:8765/api/status") 5 3
$ollama = Get-HttpStatus @("http://127.0.0.1:11434/api/tags", "http://localhost:11434/api/tags") 5 3

$fastModel = [Environment]::GetEnvironmentVariable("CYBERAGENT_FAST_MODEL", "User")
if (-not $fastModel) { $fastModel = $env:CYBERAGENT_FAST_MODEL }
$powerModel = [Environment]::GetEnvironmentVariable("CYBERAGENT_POWER_MODEL", "User")
if (-not $powerModel) { $powerModel = $env:CYBERAGENT_POWER_MODEL }
$mistralModel = [Environment]::GetEnvironmentVariable("CYBERAGENT_MISTRAL_MODEL", "User")
if (-not $mistralModel) { $mistralModel = $env:CYBERAGENT_MISTRAL_MODEL }

$warnings = New-Object System.Collections.Generic.List[string]
if ($mainLogical -gt 1) {
    $warnings.Add("Hay mas de una instancia logica de main.py.")
}
if ($apiLogical -gt 1) {
    $warnings.Add("Hay mas de una instancia logica API standalone/uvicorn.")
}
if ($listenerLogical -gt 1) {
    $warnings.Add("Hay mas de una instancia logica de taskboard_listener.py.")
}
if (-not $api.ok) {
    $warnings.Add("La API local no responde en 127.0.0.1:8765.")
}
if (-not $ollama.ok) {
    $warnings.Add("Ollama no responde en 127.0.0.1:11434.")
}
if (-not (Test-Path $Python)) {
    $warnings.Add("No existe el Python del venv: $Python")
}

$result = [ordered]@{
    root = [string]$Root
    python = $Python
    fast_model = $fastModel
    power_model = $powerModel
    mistral_model = $mistralModel
    api = [ordered]@{
        ok = $api.ok
        url = $api.url
        status = $api.status
        body = $api.body
    }
    ollama = [ordered]@{
        ok = $ollama.ok
        url = $ollama.url
        status = $ollama.status
    }
    port_8765 = $port8765
    counts = [ordered]@{
        agent_python = $processes.Count
        main_raw = $mainProcesses.Count
        main_logical = $mainLogical
        api_raw = $apiProcesses.Count
        api_logical = $apiLogical
        taskboard_listener_raw = $listenerProcesses.Count
        taskboard_listener_logical = $listenerLogical
    }
    warnings = @($warnings)
}

if ($Detailed) {
    $result.processes = $processes
}

if ($Json) {
    $result | ConvertTo-Json -Depth 6
    exit 0
}

[pscustomobject]$result | Format-List
if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host " - $warning" -ForegroundColor Yellow
    }
}
