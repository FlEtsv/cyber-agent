"""
Auto-conciencia de CyberAgent: permite al agente conocer, leer y modificar su propio código.
Proporciona herramientas para auto-reparación, mejora y reinicio limpio.
"""
import os, sys, subprocess

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Mapa de archivos clave para que el agente sepa dónde buscar
KEY_FILES = {
    "entry_point":      "main.py",
    "core_agent":       "app/ollama_client.py",
    "tools":            "app/tools.py",
    "main_window":      "app/widgets/main_window.py",
    "chat_panel":       "app/widgets/chat_panel.py",
    "server":           "app/api/server.py",
    "agent_runner":     "app/api/agent_runner.py",
    "relay":            "app/api/relay_connector.py",
    "database":         "app/database.py",
    "system_context":   "app/consciousness/system_context.py",
    "self_awareness":   "app/consciousness/self_awareness.py",
    "threat_detector":  "app/consciousness/threat_detector.py",
    "decision_log":     "app/consciousness/decision_log.py",
    "styles":           "app/styles.py",
    "mobile_tools":     "app/mobile_tools.py",
}

_ARCHITECTURE_BLOCK = f"""── AUTOCONCIENCIA ──
Proyecto: {PROJECT_ROOT}
Archivos clave: main.py · app/ollama_client.py · app/tools.py · app/widgets/main_window.py · app/api/server.py · app/database.py · app/consciousness/self_awareness.py · app/styles.py
Auto-modificación: read_file → write_file → syntax_check(path) → restart_self()
Nueva herramienta: añadir en tools.py (función + schema en TOOLS_SCHEMA + dispatch en execute_tool + permisos en DEFAULT_PERMISSIONS).
──────────────────────────────────────────"""


def get_architecture_block() -> str:
    return _ARCHITECTURE_BLOCK


def _list_self_files() -> dict:
    """Lista todos los archivos del proyecto con tamaño y fecha."""
    files = []
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        # Ignorar dirs de artefactos
        dirnames[:] = [d for d in dirnames
                       if d not in {".venv", "__pycache__", ".git", "node_modules",
                                    ".mypy_cache", "dist", "build", ".pytest_cache"}]
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            try:
                stat = os.stat(fpath)
                rel  = os.path.relpath(fpath, PROJECT_ROOT).replace("\\", "/")
                files.append({
                    "path":     rel,
                    "size_kb":  round(stat.st_size / 1024, 1),
                    "modified": __import__("datetime").datetime.fromtimestamp(
                                    stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
            except OSError:
                pass
    return {"project_root": PROJECT_ROOT, "file_count": len(files), "files": files}


def _syntax_check(path: str) -> dict:
    """Compila un archivo .py y reporta errores de sintaxis."""
    import py_compile, traceback
    abs_path = path if os.path.isabs(path) else os.path.join(PROJECT_ROOT, path)
    if not os.path.isfile(abs_path):
        return {"error": f"Archivo no encontrado: {abs_path}"}
    try:
        py_compile.compile(abs_path, doraise=True)
        return {"ok": True, "path": abs_path, "message": "Sin errores de sintaxis"}
    except py_compile.PyCompileError as e:
        return {"ok": False, "path": abs_path, "error": str(e)}
    except Exception as e:
        return {"ok": False, "path": abs_path, "error": traceback.format_exc()}


def _restart_self() -> dict:
    """
    Reinicia CyberAgent sin interpolación de shell:
    1. Lanza nueva instancia directamente con Popen (sin PowerShell)
    2. Señaliza a Qt para que cierre limpiamente
    """
    python  = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pythonw.exe")
    main_py = os.path.join(PROJECT_ROOT, "main.py")

    if not os.path.isfile(python):
        python = sys.executable

    try:
        subprocess.Popen(
            [python, main_py],
            cwd=PROJECT_ROOT,
            creationflags=(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) |
                getattr(subprocess, "DETACHED_PROCESS", 0)
            ),
            close_fds=True,
        )
    except Exception as e:
        return {"error": f"No se pudo lanzar nueva instancia: {e}"}

    # Señalizar a Qt (thread-safe desde QThread)
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QMetaObject, Qt as _Qt
        app = QApplication.instance()
        if app:
            QMetaObject.invokeMethod(app, "quit", _Qt.QueuedConnection)
    except Exception as e:
        return {"error": f"Nueva instancia lanzada pero error al cerrar Qt: {e}"}

    return {
        "success":  True,
        "message":  "CyberAgent se reiniciará con los cambios aplicados.",
        "new_proc": f"{python} main.py",
    }
