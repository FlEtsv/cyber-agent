# build_all.ps1 — Compila CyberAgent.exe + CyberAgentInstaller.exe (onefile)
# Ejecutar desde PowerShell en el directorio agent-native/
param(
    [switch]$InstallerOnly,
    [switch]$AgentOnly
)

$Root   = $PSScriptRoot
$PyInst = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")

function Banner($t) {
    Write-Host "`n══════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $t" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
}
function OK($t)  { Write-Host "  ✓ $t" -ForegroundColor Green }
function ERR($t) { Write-Host "  ✗ $t" -ForegroundColor Red; exit 1 }

Banner "CyberAgent Build System"

if (-not (Test-Path $PyInst)) {
    ERR "PyInstaller no encontrado. Ejecuta: .venv\Scripts\pip install pyinstaller"
}

# ── Compilar agente principal (onedir) ────────────────────────────────────────
if (-not $InstallerOnly) {
    Banner "Compilando CyberAgent.exe"
    Push-Location $Root
    & $PyInst "CyberAgent.spec" --noconfirm 2>&1 | ForEach-Object {
        if ($_ -match "^(ERROR|CRITICAL)") { Write-Host "  $_" -ForegroundColor Red }
    }
    if (Test-Path "dist\CyberAgent\CyberAgent.exe") { OK "dist\CyberAgent\CyberAgent.exe" }
    else { ERR "Falló la compilación del agente" }
    Pop-Location
}

# ── Compilar instalador (onefile) ─────────────────────────────────────────────
if (-not $AgentOnly) {
    Banner "Compilando CyberAgentInstaller.exe  (onefile)"
    Push-Location (Join-Path $Root "installer")
    & $PyInst "CyberAgentInstaller.spec" --noconfirm 2>&1 | ForEach-Object {
        if ($_ -match "^(ERROR|CRITICAL)") { Write-Host "  $_" -ForegroundColor Red }
    }
    # onefile genera dist\CyberAgentInstaller.exe (no subcarpeta)
    $InstallerExe = "dist\CyberAgentInstaller.exe"
    if (-not (Test-Path $InstallerExe)) { ERR "Falló la compilación del instalador" }
    OK "installer\$InstallerExe generado ($([math]::Round((Get-Item $InstallerExe).Length/1MB,1)) MB)"
    Pop-Location
}

# ── Copiar instalador único al escritorio ─────────────────────────────────────
Banner "Copiando al escritorio"

$src = Join-Path $Root "installer\dist\CyberAgentInstaller.exe"
$dst = Join-Path $Desktop "CyberAgentInstaller.exe"

if (Test-Path $src) {
    # Eliminar versión vieja (carpeta o exe)
    $oldDir = Join-Path $Desktop "CyberAgentInstaller"
    if (Test-Path $oldDir) { Remove-Item $oldDir -Recurse -Force }
    if (Test-Path $dst)    { Remove-Item $dst -Force }
    # Eliminar acceso directo viejo
    $oldLnk = Join-Path $Desktop "Instalar CyberAgent.lnk"
    if (Test-Path $oldLnk) { Remove-Item $oldLnk -Force }

    Copy-Item $src $dst
    OK "CyberAgentInstaller.exe copiado al escritorio"
} else {
    Write-Host "  (instalador no compilado — omitiendo copia)" -ForegroundColor Yellow
}

Banner "BUILD COMPLETADO"
Write-Host "  • dist\CyberAgent\CyberAgent.exe        (agente)" -ForegroundColor Gray
Write-Host "  • Desktop\CyberAgentInstaller.exe        (instalador — un solo archivo)" -ForegroundColor Gray
