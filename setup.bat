@echo off
setlocal EnableDelayedExpansion
title CyberAgent — Instalador

echo.
echo  ══════════════════════════════════════════════════
echo    CYBERAGENT — INSTALADOR
echo    Agente IA local con acceso total al sistema
echo  ══════════════════════════════════════════════════
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+ desde python.org
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version') do set PY_VER=%%v
echo [OK] Python %PY_VER% detectado

:: Verificar que estamos en el directorio correcto
if not exist "main.py" (
    echo [ERROR] Ejecuta este script desde el directorio del proyecto
    pause & exit /b 1
)

echo.
echo [1/4] Creando entorno virtual...
if not exist ".venv" (
    python -m venv .venv
    echo      Entorno virtual creado en .venv\
) else (
    echo      Entorno virtual ya existe
)

echo.
echo [2/4] Instalando dependencias...
call .venv\Scripts\pip install --upgrade pip --quiet
call .venv\Scripts\pip install ^
    PySide6 ^
    httpx ^
    markdown ^
    psutil ^
    Pillow ^
    chromadb ^
    sentence-transformers ^
    --upgrade --quiet

if errorlevel 1 (
    echo [ERROR] Fallo al instalar dependencias
    pause & exit /b 1
)
echo      Dependencias instaladas correctamente

echo.
echo [3/4] Creando directorios de datos...
if not exist "data\knowledge" mkdir data\knowledge
if not exist "data\vectors"   mkdir data\vectors
if not exist "app\rag"        mkdir app\rag
if not exist "app\consciousness" mkdir app\consciousness
echo      Directorios creados

echo.
echo [4/4] Configurando inicio automático con Windows...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

(
echo @echo off
echo start "" /B "%SCRIPT_DIR%\.venv\Scripts\pythonw.exe" "%SCRIPT_DIR%\main.py"
) > "%STARTUP%\cyber-agent.bat"

echo      Acceso directo creado en Inicio Automático

echo.
echo  ══════════════════════════════════════════════════
echo    INSTALACIÓN COMPLETADA
echo.
echo    Para iniciar el agente:
echo      .venv\Scripts\pythonw.exe main.py
echo.
echo    O simplemente reinicia Windows (inicio automático).
echo.
echo    REQUISITO: Ollama debe estar corriendo.
echo      Descarga: https://ollama.com
echo      Iniciar:  ollama serve
echo      Modelo:   ollama pull cyber-coder:latest
echo  ══════════════════════════════════════════════════
echo.
pause
