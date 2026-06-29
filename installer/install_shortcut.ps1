# install_shortcut.ps1 - Instala CyberAgent como app nativa de Windows.
# Crea accesos directos (Escritorio + Menu Inicio) que lanzan la app sin consola.
# Uso:   .\installer\install_shortcut.ps1            (instala accesos directos)
#        .\installer\install_shortcut.ps1 -Autostart (ademas arranca con Windows)
#        .\installer\install_shortcut.ps1 -Uninstall  (quita accesos directos)
param(
    [switch]$Autostart,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$Root      = Split-Path -Parent $PSScriptRoot
$MainPy    = Join-Path $Root "main.py"
$IconPath  = Join-Path $Root "assets\cyberagent.ico"
$Desktop   = [Environment]::GetFolderPath("Desktop")
$Programs  = [Environment]::GetFolderPath("Programs")
$StartupDir = [Environment]::GetFolderPath("Startup")
$DesktopLnk = Join-Path $Desktop "CyberAgent.lnk"
$StartMenu  = Join-Path $Programs "CyberAgent.lnk"
$StartupLnk = Join-Path $StartupDir "CyberAgent.lnk"

function Make-Shortcut($Path, $Target, $Arguments, $WorkDir, $Icon) {
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($Path)
    $sc.TargetPath = $Target
    $sc.Arguments = $Arguments
    $sc.WorkingDirectory = $WorkDir
    if (Test-Path $Icon) { $sc.IconLocation = $Icon }
    $sc.Description = "CyberAgent - agente IA local"
    $sc.WindowStyle = 7
    $sc.Save()
}

if ($Uninstall) {
    foreach ($p in @($DesktopLnk, $StartMenu, $StartupLnk)) {
        if (Test-Path $p) { Remove-Item $p -Force; Write-Host ("  quitado: " + $p) -ForegroundColor Yellow }
    }
    Write-Host "CyberAgent desinstalado (accesos directos eliminados)." -ForegroundColor Green
    return
}

# 1) pythonw del venv (sin ventana de consola)
$Pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Pythonw)) { $Pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source }
if (-not $Pythonw) { Write-Host "No se encontro pythonw.exe." -ForegroundColor Red; exit 1 }
Write-Host ("[1/3] Lanzador: " + $Pythonw) -ForegroundColor Cyan

# 2) Genera el icono .ico si no existe
if (-not (Test-Path $IconPath)) {
    Write-Host "[2/3] Generando icono..." -ForegroundColor Cyan
    $Py = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $Py)) { $Py = "python" }
    & $Py (Join-Path $PSScriptRoot "make_icon.py") $IconPath
} else {
    Write-Host "[2/3] Icono ya existe." -ForegroundColor Cyan
}

# 3) Crea los accesos directos
Write-Host "[3/3] Creando accesos directos..." -ForegroundColor Cyan
Make-Shortcut $DesktopLnk $Pythonw ('"' + $MainPy + '"') $Root $IconPath
Write-Host ("  OK Escritorio:  " + $DesktopLnk) -ForegroundColor Green
Make-Shortcut $StartMenu $Pythonw ('"' + $MainPy + '"') $Root $IconPath
Write-Host ("  OK Menu Inicio: " + $StartMenu) -ForegroundColor Green

if ($Autostart) {
    Make-Shortcut $StartupLnk $Pythonw ('"' + $MainPy + '"') $Root $IconPath
    Write-Host "  OK Autoarranque con Windows activado" -ForegroundColor Green
}

Write-Host "`nListo. CyberAgent instalado como app nativa." -ForegroundColor Green
Write-Host "Abrelo desde el icono del Escritorio o el Menu Inicio." -ForegroundColor Cyan
Write-Host "Controles en bandeja: Abrir / Reiniciar / Salir." -ForegroundColor Cyan
