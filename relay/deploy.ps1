# deploy.ps1 â€” Despliega el relay en Google Cloud Run
# Uso: .\relay\deploy.ps1 -Project TU_PROJECT_ID
param(
    [Parameter(Mandatory=$true)]
    [string]$Project,
    [string]$Region = "us-central1",
    [string]$ServiceName = "cyberagent-relay",
    # 1 = una instancia siempre caliente (sin cold-starts ni cortes de conexión al
    # redesplegar; ~unos pocos $/mes). 0 = escala a cero (gratis en reposo pero con
    # cold-starts y reconexiones tras redeploy, mitigadas por el self-check del PC).
    [int]$MinInstances = 1
)

$ErrorActionPreference = "Stop"

Write-Host "`n[1/4] Verificando gcloud..." -ForegroundColor Cyan
gcloud auth list --filter=status:ACTIVE --format="value(account)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "No has iniciado sesiÃ³n. Ejecuta: gcloud auth login" -ForegroundColor Red
    exit 1
}

Write-Host "[2/4] Activando APIs necesarias..." -ForegroundColor Cyan
gcloud services enable run.googleapis.com cloudbuild.googleapis.com `
    --project=$Project --quiet

Write-Host "[3/4] Construyendo y subiendo imagen..." -ForegroundColor Cyan

# La web es un producto unico en apps/web. El relay solo la transporta, asi que
# sincronizamos apps/web -> relay/web (artefacto de build, no versionado) antes
# de empaquetar la imagen, ya que el contexto de Cloud Build es ./relay.
$webSrc = Join-Path $PSScriptRoot "..\apps\web"
$webDst = Join-Path $PSScriptRoot "web"
if (-not (Test-Path $webSrc)) {
    Write-Host "  ERROR: no existe apps\web (fuente de la web)" -ForegroundColor Red
    exit 1
}
if (Test-Path $webDst) { Remove-Item $webDst -Recurse -Force }
Copy-Item $webSrc $webDst -Recurse -Force
Write-Host "  Web sincronizada: apps\web -> relay\web" -ForegroundColor Green

$ImageUrl = "gcr.io/$Project/$ServiceName"
gcloud builds submit ./relay `
    --tag=$ImageUrl `
    --project=$Project

Write-Host "[4/4] Desplegando en Cloud Run..." -ForegroundColor Cyan

# Lee secrets del archivo .env si existen
$envFile = Join-Path $PSScriptRoot "..\data\relay_secrets.env"
$envVars = @()
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^[^#].*=") { $envVars += $_ }
    }
    Write-Host "  Usando variables de $envFile" -ForegroundColor Green
} else {
    Write-Host "  AVISO: no se encontrÃ³ data\relay_secrets.env" -ForegroundColor Yellow
    Write-Host "  Ejecuta primero: python relay\generate_secrets.py --email TU@EMAIL --password TUPASS" -ForegroundColor Yellow
}

$setEnv = if ($envVars) { "--set-env-vars=" + ($envVars -join ",") } else { "" }

$args = @(
    "run", "deploy", $ServiceName,
    "--image=$ImageUrl",
    "--region=$Region",
    "--platform=managed",
    "--allow-unauthenticated",
    "--min-instances=$MinInstances",
    "--max-instances=1",
    "--memory=256Mi",
    "--cpu=1",
    "--timeout=3600",
    "--project=$Project"
)
if ($setEnv) { $args += $setEnv }

& gcloud @args

$url = gcloud run services describe $ServiceName `
    --region=$Region --project=$Project `
    --format="value(status.url)"

Write-Host "`nRelay desplegado en: $url" -ForegroundColor Green
Write-Host "`nAnade esto a tu .env del PC:" -ForegroundColor Cyan
Write-Host "RELAY_URL=$url"
Write-Host "RELAY_HOST_SECRET=<el HOST_SECRET que generaste>"