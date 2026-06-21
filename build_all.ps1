# build_all.ps1 — Compila CyberAgent.exe + CyberAgentInstaller.exe
# Ejecutar desde PowerShell como Administrador en el directorio agent-native/
param(
    [switch]$InstallerOnly,
    [switch]$AgentOnly
)

$Root = $PSScriptRoot
$Venv = Join-Path $Root ".venv\Scripts\python.exe"
$PyInst = Join-Path $Root ".venv\Scripts\pyinstaller.exe"

function Banner($text) {
    Write-Host ""
    Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
}

function Step($text) { Write-Host "  ► $text" -ForegroundColor White }
function OK($text)   { Write-Host "  ✓ $text" -ForegroundColor Green }
function ERR($text)  { Write-Host "  ✗ $text" -ForegroundColor Red }

Banner "CyberAgent Build System"

# ── Verificar entorno ──────────────────────────────────────────────────────
if (-not (Test-Path $PyInst)) {
    ERR "PyInstaller no encontrado en .venv. Ejecuta primero:"
    Write-Host "    .venv\Scripts\pip install pyinstaller" -ForegroundColor Yellow
    exit 1
}

# ── Compilar agente principal ──────────────────────────────────────────────
if (-not $InstallerOnly) {
    Banner "Compilando CyberAgent.exe"
    Step "PyInstaller con manifest UAC + sin consola..."
    Push-Location $Root
    & $PyInst "CyberAgent.spec" --noconfirm 2>&1 | ForEach-Object {
        if ($_ -match "ERROR|error") { Write-Host "    $_" -ForegroundColor Red }
        elseif ($_ -match "WARNING|warning") { Write-Host "    $_" -ForegroundColor Yellow }
    }
    if (Test-Path "dist\CyberAgent\CyberAgent.exe") {
        OK "dist\CyberAgent\CyberAgent.exe generado"
    } else {
        ERR "Falló la compilación del agente"
        exit 1
    }
    Pop-Location
}

# ── Compilar instalador ────────────────────────────────────────────────────
if (-not $AgentOnly) {
    Banner "Compilando CyberAgentInstaller.exe"
    Step "PyInstaller para el instalador GUI..."
    Push-Location (Join-Path $Root "installer")
    & $PyInst "CyberAgentInstaller.spec" --noconfirm 2>&1 | ForEach-Object {
        if ($_ -match "ERROR|error") { Write-Host "    $_" -ForegroundColor Red }
        elseif ($_ -match "WARNING|warning") { Write-Host "    $_" -ForegroundColor Yellow }
    }
    if (Test-Path "dist\CyberAgentInstaller\CyberAgentInstaller.exe") {
        OK "installer\dist\CyberAgentInstaller\CyberAgentInstaller.exe generado"
    } else {
        ERR "Falló la compilación del instalador"
        Pop-Location
        exit 1
    }
    Pop-Location
}

# ── Copiar instalador al escritorio ───────────────────────────────────────
Banner "Copiando al escritorio"
$InstallerExe = Join-Path $Root "installer\dist\CyberAgentInstaller\CyberAgentInstaller.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")
$DesktopInstaller = Join-Path $Desktop "CyberAgentInstaller.exe"

if (Test-Path $InstallerExe) {
    # Copiar el directorio completo del instalador (lleva las DLLs de Qt)
    $InstallerDir = Join-Path $Root "installer\dist\CyberAgentInstaller"
    $DesktopDir   = Join-Path $Desktop "CyberAgentInstaller"
    if (Test-Path $DesktopDir) { Remove-Item $DesktopDir -Recurse -Force }
    Copy-Item $InstallerDir $DesktopDir -Recurse
    OK "Instalador copiado a: $DesktopDir\CyberAgentInstaller.exe"

    # Crear acceso directo al instalador en el escritorio
    $WS = New-Object -ComObject WScript.Shell
    $SC = $WS.CreateShortcut("$Desktop\Instalar CyberAgent.lnk")
    $SC.TargetPath       = "$DesktopDir\CyberAgentInstaller.exe"
    $SC.WorkingDirectory = $DesktopDir
    $SC.Description      = "CyberAgent — Instalador GUI"
    $SC.Save()
    OK "Acceso directo 'Instalar CyberAgent.lnk' creado en el escritorio"
} else {
    ERR "Instalador no encontrado, no se puede copiar al escritorio"
}

Banner "BUILD COMPLETADO"
Write-Host ""
Write-Host "  Archivos generados:" -ForegroundColor White
Write-Host "    • dist\CyberAgent\CyberAgent.exe          (agente principal)" -ForegroundColor Gray
Write-Host "    • installer\dist\CyberAgentInstaller\     (instalador GUI)" -ForegroundColor Gray
Write-Host "    • Desktop\Instalar CyberAgent.lnk          (acceso directo)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Próximo paso: haz doble clic en 'Instalar CyberAgent' del escritorio" -ForegroundColor Cyan
Write-Host ""
