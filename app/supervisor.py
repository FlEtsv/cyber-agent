"""
Supervisor in-process: tres servicios guardianes, cada uno vigila y AUTO-CURA
su parte y solo la suya. Corren como hilos daemon independientes, así que si uno
falla no tumba a los demás.

  1. PersistenceService  → conversación/datos (SQLite: chats, mensajes, historial,
                           contexto, carpetas, archivos). Verifica, checkpoint WAL
                           y backup periódico.
  2. OllamaService       → Ollama + modelos. Si la API no responde, reinicia
                           Ollama; mantiene las env de optimización.
  3. ConnectionService   → red↔PC. Mantiene el servidor local :8765 enlazado y el
                           conector del relay vivo/conectado.

El estado agregado se expone en /api/health (lo consume el watchdog externo, que
reinicia la app entera solo si TODO se cuelga).
"""
from __future__ import annotations

import os
import socket
import subprocess
import threading
import time

try:
    from app.agent_log import log
except Exception:  # pragma: no cover
    def log(*a, **k):
        pass


# ── utilidades ────────────────────────────────────────────────────────────────
def _port_listening(port: int, host: str = "127.0.0.1", timeout: float = 3.0) -> bool:
    # Reintenta antes de declarar caído: durante una inferencia larga el server
    # puede tardar en aceptar y daba FALSOS positivos → rebinds innecesarios.
    for _ in range(3):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            time.sleep(0.6)
    return False


def _no_window():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ── servicio base ─────────────────────────────────────────────────────────────
class _Service:
    name = "service"
    interval = 15.0          # segundos entre comprobaciones
    heal_after = 1           # fallos CONSECUTIVOS antes de intentar curar

    def __init__(self):
        self._stop = False
        self._fail = 0
        self._last = {"ok": None, "detail": "iniciando", "ts": 0.0,
                      "heals": 0, "fail_streak": 0}

    # a implementar por cada servicio
    def check(self) -> tuple[bool, str]:
        raise NotImplementedError

    def heal(self) -> None:
        pass

    def _loop(self):
        # arranque escalonado para no martillear todo a la vez
        time.sleep(2.0)
        while not self._stop:
            try:
                ok, detail = self.check()
            except Exception as e:
                ok, detail = False, f"check error: {type(e).__name__}: {e}"
            self._fail = 0 if ok else self._fail + 1
            self._last.update(ok=ok, detail=detail, ts=time.time(),
                              fail_streak=self._fail)
            if not ok and self._fail >= self.heal_after:
                log("WARN", "supervisor", f"{self.name}: no sano, curando",
                    {"detail": detail, "fail_streak": self._fail})
                try:
                    self.heal()
                    self._last["heals"] += 1
                except Exception as e:
                    log("ERROR", "supervisor", f"{self.name}: heal falló: {e}")
                self._fail = 0   # tras curar, damos margen a que se recupere
            time.sleep(self.interval)

    def start(self):
        threading.Thread(target=self._loop, daemon=True,
                         name=f"svc-{self.name}").start()

    def stop(self):
        self._stop = True

    def status(self) -> dict:
        return {"service": self.name, **self._last}


# ── 1) Persistencia (conversación / datos) ────────────────────────────────────
class PersistenceService(_Service):
    name = "persistence"
    interval = 300.0         # 5 min: la capa de datos es estable; sobre todo cuida+respalda
    heal_after = 1

    def __init__(self):
        super().__init__()
        self._last_backup = 0.0

    def check(self) -> tuple[bool, str]:
        from app.database import get_conn
        conn = get_conn()
        # sanity: las tablas clave de la conversación responden
        n = conn.execute("SELECT count(*) FROM conversations").fetchone()[0]
        # checkpoint WAL para que el historial no crezca sin límite
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        # backup diario (la función ya conserva 7 y no duplica el del día)
        if time.time() - self._last_backup > 3600:
            try:
                from app.database import backup_db
                backup_db()
                self._last_backup = time.time()
            except Exception:
                pass
        return True, f"{n} conversaciones · WAL checkpoint · backup ok"

    def heal(self) -> None:
        # Si el SELECT falla, la conexión threadlocal puede estar rota: la cerramos
        # para que get_conn() abra una nueva en la siguiente comprobación.
        try:
            from app.database import _local
            c = getattr(_local, "conn", None)
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
                _local.conn = None
        except Exception:
            pass


# ── 2) Ollama + modelos ───────────────────────────────────────────────────────
class OllamaService(_Service):
    name = "ollama"
    interval = 20.0
    heal_after = 5           # ~100s: tolera cargas legítimas de modelo desde disco

    def check(self) -> tuple[bool, str]:
        import httpx
        r = httpx.get("http://localhost:11434/api/version", timeout=5.0)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        return True, f"v{r.json().get('version', '?')}"

    def heal(self) -> None:
        # Ollama colgado o caído → reinícialo (las env de optimización ya están
        # fijadas a nivel de usuario; el proceso nuevo las recoge).
        _restart_ollama()
        # tras reiniciar, intenta precalentar el modelo por defecto
        time.sleep(8)
        try:
            from app.ollama_client import warm_fast_model
            warm_fast_model()
        except Exception:
            pass


def _restart_ollama() -> None:
    # mata server + app de Ollama y relanza la app (que rearranca el server)
    for name in ("ollama.exe", "ollama app.exe"):
        try:
            subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True,
                           creationflags=_no_window(), timeout=15)
        except Exception:
            pass
    time.sleep(2)
    app_exe = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                           "Programs", "Ollama", "ollama app.exe")
    try:
        if os.path.isfile(app_exe):
            subprocess.Popen([app_exe], creationflags=_no_window(),
                             close_fds=True)
        else:
            subprocess.Popen(["ollama", "serve"], creationflags=_no_window(),
                             close_fds=True)
        log("INFO", "supervisor", "Ollama reiniciado por el supervisor")
    except Exception as e:
        log("ERROR", "supervisor", f"No se pudo reiniciar Ollama: {e}")


# ── 3) Conexión red↔PC (servidor local + relay) ───────────────────────────────
class ConnectionService(_Service):
    name = "connection"
    interval = 15.0
    heal_after = 1   # acciones idempotentes/seguras; actuamos rápido

    def __init__(self):
        super().__init__()
        self._xcheck = 0
        self._stale_streak = 0

    def check(self) -> tuple[bool, str]:
        api_up = _port_listening(8765)
        from app.api.relay_connector import relay_status, relay_remote_sees_us
        rs = relay_status()
        if not rs["configured"]:
            return api_up, f"api:8765={'up' if api_up else 'DOWN'} · relay=sin-config"
        # ¿El conector cree estar conectado pero la revisión ACTIVA del relay no
        # nos ve? (fijado a revisión muerta). Lo comprobamos por HTTP cada ~45s y
        # exigimos 2 detecciones SEGUIDAS antes de forzar (evita falsos por lag).
        stale = False
        if rs["connected"]:
            self._xcheck += 1
            if self._xcheck % 3 == 0:
                if relay_remote_sees_us() is False:
                    self._stale_streak += 1
                else:
                    self._stale_streak = 0
                if self._stale_streak >= 2:
                    stale = True
        else:
            self._stale_streak = 0
        relay_ok = rs["connected"] and not stale
        ok = api_up and relay_ok
        txt = ("conectado" if relay_ok
               else "FIJADO-A-REV-MUERTA" if stale else "DESCONECTADO")
        return ok, f"api:8765={'up' if api_up else 'DOWN'} · relay={txt}"

    def heal(self) -> None:
        # a) servidor local caído → reenlázalo
        if not _port_listening(8765):
            try:
                from app.api.server import start_server
                start_server(port=8765)
                log("INFO", "supervisor", "Servidor local :8765 reenlazado")
            except Exception as e:
                log("ERROR", "supervisor", f"No se pudo reenlazar :8765: {e}")
        from app.api import relay_connector as rc
        rs = rc.relay_status()
        if not rs["configured"]:
            return
        if not rs["thread_alive"]:
            # b1) hilo del conector muerto → relánzalo
            try:
                rc.start_relay_connector()
                log("INFO", "supervisor", "Conector del relay relanzado")
            except Exception as e:
                log("ERROR", "supervisor", f"No se pudo relanzar el conector: {e}")
        elif rs["connected"] and rc.relay_remote_sees_us() is False:
            # b2) fijado a revisión muerta → fuerza reconexión (thread-safe)
            if rc.force_relay_reconnect():
                log("INFO", "supervisor", "Relay fijado a revisión muerta → reconexión forzada")
        # si está desconectado pero el hilo vive, su bucle ya reconecta solo


# ── 4) Seguridad (Telegram notifier + módulo de seguridad) ───────────────────
class SecurityService(_Service):
    """Vigila que el notificador de Telegram esté accesible.
    No envía mensajes de prueba; solo verifica que el vault devuelve credenciales.
    """
    name = "security"
    interval = 120.0
    heal_after = 3

    def check(self) -> tuple[bool, str]:
        try:
            from app.security.notify import available, _cfg
            if not available():
                return True, "telegram=sin-config (ok)"
            token, chat = _cfg()
            # Verificación liviana: endpoint getMe de Telegram (no envía mensajes)
            import httpx
            r = httpx.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=8.0,
            )
            if r.status_code == 200 and r.json().get("ok"):
                return True, f"telegram=ok (@{r.json()['result'].get('username', '?')})"
            return False, f"telegram=HTTP {r.status_code}"
        except Exception as e:
            return False, f"telegram=error: {e}"

    def heal(self) -> None:
        log("WARN", "supervisor", "SecurityService: Telegram no responde — nada que curar automáticamente")


# ── 5) Docker HA health-check (J-03, gateado por SECURITY_ENABLED) ───────────
_HA_CONTAINER_NAMES = ("homeassistant", "home-assistant", "apicomunicaciones", "centralita")


class DockerHAService(_Service):
    """Verifica que el contenedor HA/comunicaciones esté corriendo.
    Solo actúa si CYBERAGENT_SECURITY_ENABLED=1. En heal, intenta start."""
    name = "docker_ha"
    interval = 60.0
    heal_after = 2

    def check(self) -> tuple[bool, str]:
        if os.environ.get("CYBERAGENT_SECURITY_ENABLED", "0") != "1":
            return True, "ha_docker=skipped (SECURITY_ENABLED=0)"
        try:
            from app.docker_tools import available, run
            if not available():
                return True, "ha_docker=skipped (docker no instalado)"
            result = run("ps_all")
            for c in result.get("containers", []):
                cname = (c.get("name") or "").lower()
                if any(n in cname for n in _HA_CONTAINER_NAMES):
                    state = (c.get("state") or "").lower()
                    return state == "running", f"ha_docker={state} ({c['name']})"
            return True, "ha_docker=no encontrado (no configurado)"
        except Exception as e:
            return False, f"ha_docker=error: {e}"

    def heal(self) -> None:
        if os.environ.get("CYBERAGENT_SECURITY_ENABLED", "0") != "1":
            return
        try:
            from app.docker_tools import available, run
            if not available():
                return
            for c in run("ps_all").get("containers", []):
                cname = (c.get("name") or "").lower()
                if any(n in cname for n in _HA_CONTAINER_NAMES):
                    log("INFO", "supervisor", f"DockerHAService heal: arrancando {c['name']}")
                    run("start", c["name"])
                    return
        except Exception as e:
            log("WARN", "supervisor", f"DockerHAService heal falló: {e}")


# ── 6) Watchdog (supervisión mutua) ───────────────────────────────────────────
def _startup_bat() -> str:
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                        "Start Menu", "Programs", "Startup", "CyberAgentWatchdog.bat")


def _watchdog_running() -> bool:
    try:
        import psutil
    except Exception:
        return True   # sin psutil no podemos saber; no molestamos
    for p in psutil.process_iter(["cmdline"]):
        try:
            if "watchdog.py" in " ".join(p.info.get("cmdline") or []).lower():
                return True
        except Exception:
            pass
    return False


class WatchdogService(_Service):
    """La app vigila al watchdog externo (que a su vez vigila a la app): si el
    watchdog se cae, lo relanzamos. Solo actúa si está instalado en autostart."""
    name = "watchdog"
    interval = 60.0
    heal_after = 1

    def check(self) -> tuple[bool, str]:
        if not os.path.isfile(_startup_bat()):
            return True, "no instalado"
        alive = _watchdog_running()
        return alive, ("vivo" if alive else "CAÍDO — relanzando")

    def heal(self) -> None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pyw = os.path.join(base, ".venv", "Scripts", "pythonw.exe")
        wd = os.path.join(base, "watchdog.py")
        try:
            subprocess.Popen([pyw, wd], cwd=base,
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
                             close_fds=True)
            log("INFO", "supervisor", "Watchdog relanzado")
        except Exception as e:
            log("ERROR", "supervisor", f"No se pudo relanzar el watchdog: {e}")


# ── 7) Bot Telegram polling (B-01, gateado por SECURITY_ENABLED) ─────────────
class TelegramBotService(_Service):
    """Arranca el bot de long-polling si SECURITY_ENABLED=1."""
    name = "telegram_bot"
    interval = 30.0
    heal_after = 2

    def check(self) -> tuple[bool, str]:
        if os.environ.get("SECURITY_ENABLED", "0") != "1":
            return True, "bot=skipped (SECURITY_ENABLED=0)"
        try:
            from app.security.telegram.bot import status
            s = status()
            if s.get("running") and s.get("thread_alive"):
                return True, f"bot=running offset={s.get('offset', 0)}"
            return False, "bot=stopped"
        except Exception as e:
            return False, f"bot=error: {e}"

    def heal(self) -> None:
        if os.environ.get("SECURITY_ENABLED", "0") != "1":
            return
        try:
            from app.security.telegram.bot import start, stop
            stop()
            time.sleep(1)
            start()
            log("INFO", "supervisor", "TelegramBot relanzado")
        except Exception as e:
            log("WARN", "supervisor", f"TelegramBotService heal falló: {e}")


# ── 8) Tareas programadas de seguridad (D-09) ─────────────────────────────────
class SecurityScheduleService(_Service):
    """Ejecuta las tareas periódicas de seguridad (retention, backup, digest)."""
    name = "security_schedule"
    interval = 60.0
    heal_after = 5

    def check(self) -> tuple[bool, str]:
        if os.environ.get("SECURITY_ENABLED", "0") != "1":
            return True, "schedule=skipped"
        try:
            from app.security.schedule import run_due, default_tasks
            default_tasks()
            ran = run_due()
            return True, f"schedule=ok tasks_ran={len(ran)}"
        except Exception as e:
            return False, f"schedule=error: {e}"


# ── Supervisor ────────────────────────────────────────────────────────────────
class Supervisor:
    def __init__(self):
        self.services: list[_Service] = [
            PersistenceService(),
            OllamaService(),
            ConnectionService(),
            SecurityService(),
            DockerHAService(),
            WatchdogService(),
            TelegramBotService(),
            SecurityScheduleService(),
        ]

    def start(self):
        for s in self.services:
            s.start()
        log("INFO", "supervisor", "Supervisor iniciado",
            {"services": [s.name for s in self.services]})

    def stop(self):
        for s in self.services:
            s.stop()

    def status(self) -> dict:
        svcs = [s.status() for s in self.services]
        healthy = all(s.get("ok") is not False for s in svcs)
        return {"healthy": healthy, "services": svcs, "ts": time.time()}


_SUPERVISOR: Supervisor | None = None


def start_supervisor() -> Supervisor:
    global _SUPERVISOR
    if _SUPERVISOR is None:
        _SUPERVISOR = Supervisor()
        _SUPERVISOR.start()
    return _SUPERVISOR


def supervisor_status() -> dict:
    if _SUPERVISOR is None:
        return {"healthy": None, "services": [], "ts": time.time()}
    return _SUPERVISOR.status()
