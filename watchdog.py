"""
Watchdog externo de último recurso para CyberAgent.

Vigila /api/health desde FUERA del proceso de la app. Si la app está COLGADA
(su proceso existe pero deja de responder varias veces seguidas), la reinicia
entera. Si el proceso NO existe (salida intencional del usuario), no hace nada
—así no pelea con "Salir".

Pensado para autostart sin consola:  pythonw watchdog.py
Instalación en el arranque de Windows: pythonw watchdog.py --install
Desinstalar:                          pythonw watchdog.py --uninstall
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

BASE   = os.path.dirname(os.path.abspath(__file__))
PYW    = os.path.join(BASE, ".venv", "Scripts", "pythonw.exe")
MAIN   = os.path.join(BASE, "main.py")
HEALTH = "http://127.0.0.1:8765/api/health"
LOGFILE = os.path.join(BASE, "logs", "watchdog.log")

INTERVAL = 30     # s entre comprobaciones
FAIL_MAX = 4      # fallos consecutivos (~2 min) antes de reiniciar
COOLDOWN = 90     # s de gracia tras un reinicio


def _log(msg: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _no_window():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ── estado de la app ──────────────────────────────────────────────────────────
def app_pids() -> list[int]:
    """PIDs de la app (venv python(w) corriendo main.py). Excluye el watchdog y
    otros scripts del repo."""
    try:
        import psutil
    except Exception:
        return []
    pids = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            cl = " ".join(p.info.get("cmdline") or [])
            low = cl.lower()
            if ("main.py" in low and ".venv" in low
                    and "watchdog" not in low and "blitz" not in low):
                pids.append(p.pid)
        except Exception:
            pass
    return pids


def is_healthy() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=8) as r:
            if r.status != 200:
                return False
            d = json.loads(r.read().decode("utf-8"))
            # None (arrancando) cuenta como vivo; solo False persistente es malo.
            return d.get("healthy") is not False
    except Exception:
        return False


def _port_free(port: int = 8765) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return False
    except OSError:
        return True


def restart_app():
    _log("App colgada → reiniciando")
    try:
        import psutil
        for pid in app_pids():
            try:
                psutil.Process(pid).kill()
                _log(f"  matado PID {pid}")
            except Exception:
                pass
    except Exception:
        pass
    # espera a que se libere :8765
    for _ in range(15):
        if _port_free():
            break
        time.sleep(2)
    try:
        subprocess.Popen(
            [PYW, MAIN], cwd=BASE,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        _log("  relanzada la app")
    except Exception as e:
        _log(f"  ERROR relanzando: {e}")


# ── bucle principal ───────────────────────────────────────────────────────────
def run():
    _log("Watchdog iniciado")
    fails = 0
    while True:
        try:
            if not app_pids():
                fails = 0          # app no corriendo (salida intencional) → no tocar
            elif is_healthy():
                fails = 0
            else:
                fails += 1
                _log(f"health KO ({fails}/{FAIL_MAX})")
                if fails >= FAIL_MAX:
                    restart_app()
                    fails = 0
                    time.sleep(COOLDOWN)
        except Exception as e:
            _log(f"loop error: {e}")
        time.sleep(INTERVAL)


# ── instalación en autostart ──────────────────────────────────────────────────
def _startup_bat() -> str:
    appdata = os.environ.get("APPDATA", "")
    startup = os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                           "Programs", "Startup")
    return os.path.join(startup, "CyberAgentWatchdog.bat")


def install():
    bat = _startup_bat()
    os.makedirs(os.path.dirname(bat), exist_ok=True)
    with open(bat, "w", encoding="utf-8") as f:
        f.write(f'@echo off\r\nstart "" "{PYW}" "{os.path.join(BASE, "watchdog.py")}"\r\n')
    print(f"Watchdog instalado en autostart:\n  {bat}")
    # arráncalo ya
    subprocess.Popen([PYW, os.path.join(BASE, "watchdog.py")], cwd=BASE,
                     creationflags=subprocess.DETACHED_PROCESS, close_fds=True)
    print("Watchdog en marcha.")


def uninstall():
    bat = _startup_bat()
    try:
        if os.path.isfile(bat):
            os.remove(bat)
            print(f"Quitado de autostart: {bat}")
        else:
            print("No estaba instalado.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if "--install" in sys.argv:
        install()
    elif "--uninstall" in sys.argv:
        uninstall()
    else:
        run()
