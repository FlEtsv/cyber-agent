param(
    [switch]$Pull,
    [switch]$PersistEnv
)

$ErrorActionPreference = "Stop"

$FastModel = "richardyoung/qwen3-14b-abliterated:Q5_K_M"
$PowerModel = "cyberagent-original"
$MistralModel = "mistral-large-latest"

Write-Host "CyberAgent model council setup" -ForegroundColor Cyan
Write-Host "Fast/private model:  $FastModel"
Write-Host "Power/private model: $PowerModel"
Write-Host "External reviewer:   $MistralModel"
Write-Host ""

if ($Pull) {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw "ollama no esta en PATH. Instala/arranca Ollama antes de usar -Pull."
    }
    Write-Host "Pulling $FastModel ..." -ForegroundColor Yellow
    ollama pull $FastModel
}

if ($PersistEnv) {
    [Environment]::SetEnvironmentVariable("CYBERAGENT_FAST_MODEL", $FastModel, "User")
    [Environment]::SetEnvironmentVariable("CYBERAGENT_POWER_MODEL", $PowerModel, "User")
    [Environment]::SetEnvironmentVariable("CYBERAGENT_MISTRAL_MODEL", $MistralModel, "User")
    Write-Host "Variables de modelo guardadas en el entorno de usuario." -ForegroundColor Green
}

Write-Host ""
Write-Host "Para esta sesion PowerShell:" -ForegroundColor Cyan
Write-Host "`$env:CYBERAGENT_FAST_MODEL='$FastModel'"
Write-Host "`$env:CYBERAGENT_POWER_MODEL='$PowerModel'"
Write-Host "`$env:CYBERAGENT_MISTRAL_MODEL='$MistralModel'"
Write-Host "`$env:MISTRAL_API_KEY='<tu clave local, no la guardes en git>'"
Write-Host ""
Write-Host "La clave de Mistral no se persiste desde este script."
