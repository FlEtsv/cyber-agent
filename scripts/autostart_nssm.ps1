# autostart_nssm.ps1 — Instala CyberAgent como servicio Windows con NSSM
# Requiere NSSM (https://nssm.cc) o: winget install NSSM.NSSM
# Ejecutar como Administrador

$ServiceName = "CyberAgent"
$AppDir      = "C:\Users\steve\cyber-llm\agent-native"
$Python      = "$AppDir\.venv\Scripts\python.exe"
$Script      = "$AppDir\main.py"
$LogDir      = "$AppDir\logs"

# Verificar NSSM
$Nssm = (Get-Command nssm -ErrorAction SilentlyContinue)
if (-not $Nssm) {
    Write-Host "[ERROR] NSSM no encontrado." -ForegroundColor Red
    Write-Host "        Instala con: winget install NSSM.NSSM" -ForegroundColor Yellow
    exit 1
}
$NssmExe = $Nssm.Source

Write-Host "Configurando servicio '$ServiceName'..." -ForegroundColor Cyan

# Detener y eliminar servicio existente
& $NssmExe stop $ServiceName 2>$null
& $NssmExe remove $ServiceName confirm 2>$null
Start-Sleep -Seconds 1

# Crear directorio de logs
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Instalar servicio
& $NssmExe install $ServiceName $Python $Script
& $NssmExe set $ServiceName AppDirectory $AppDir
& $NssmExe set $ServiceName Description  "CyberAgent — Agente IA local con Ollama"
& $NssmExe set $ServiceName Start        SERVICE_AUTO_START
& $NssmExe set $ServiceName AppStdout    "$LogDir\stdout.log"
& $NssmExe set $ServiceName AppStderr    "$LogDir\stderr.log"
& $NssmExe set $ServiceName AppRotateFiles     1
& $NssmExe set $ServiceName AppRotateBytes     10485760
& $NssmExe set $ServiceName AppRestartDelay    5000
& $NssmExe set $ServiceName AppThrottle        30000

# Iniciar
& $NssmExe start $ServiceName
$status = & $NssmExe status $ServiceName
Write-Host "Estado: $status" -ForegroundColor Green
Write-Host ""
Write-Host "Comandos utiles:"
Write-Host "  nssm status  $ServiceName"
Write-Host "  nssm restart $ServiceName"
Write-Host "  nssm stop    $ServiceName"
Write-Host "  nssm edit    $ServiceName   (GUI)"
