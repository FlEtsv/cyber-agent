import sys, os, ctypes
sys.path.insert(0, os.path.dirname(__file__))

# ── pythonw: sin consola, sys.stdout/stderr son None ──────────────────────────
# Bajo pythonw.exe (lanzador normal, sin ventana) stdout/stderr no existen y
# uvicorn —y cualquier lib que escriba a stderr al arrancar— peta EN SILENCIO,
# dejando el servidor local :8765 sin enlazar (la web del PC y el túnel caídos).
# Redirigir a devnull lo soluciona y deja :8765 operativo también sin consola.
if sys.stdout is None or sys.stderr is None:
    _devnull = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = _devnull
    if sys.stderr is None:
        sys.stderr = _devnull

# ── Instancia única: mutex con nombre ────────────────────────────────────────
_MUTEX_NAME = "Global\\CyberAgent_SingleInstance_v1"
_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
if ctypes.windll.kernel32.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
    # Traer la ventana existente al frente y salir
    hwnd = ctypes.windll.user32.FindWindowW(None, "⚡ CyberAgent")
    if hwnd:
        # No robar el foco si hay un juego a pantalla completa delante.
        try:
            from app.winfocus import foreground_is_fullscreen
            _busy = foreground_is_fullscreen()
        except Exception:
            _busy = False
        if not _busy:
            ctypes.windll.user32.ShowWindow(hwnd, 9)        # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    sys.exit(0)

# Carga .env
_env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_env_file):
    with open(_env_file, encoding="utf-8") as _fh:
        for _line in _fh:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip().lstrip("\ufeff"), _v.strip())

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer
from app.styles import QSS
from app.database import init_db
from app.widgets.main_window import MainWindow
from app.updater import UpdateChecker


def _make_icon(alert: bool = False) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    color = QColor("#ff4466") if alert else QColor("#00d9ff")
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, 24, 24)
    p.setPen(QColor("#080c0f"))
    f = QFont("Arial", 14, QFont.Bold)
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignCenter, "⚡")
    p.end()
    return QIcon(pix)


def main():
    from app.agent_log import log, clear as log_clear, separator
    log_clear()
    separator("CYBERAGENT STARTUP")
    log("INFO", "main", "Iniciando CyberAgent", {"python": sys.version})

    app = QApplication(sys.argv)
    app.setApplicationName("CyberAgent")
    app.setQuitOnLastWindowClosed(False)   # X solo oculta, no cierra la app
    app.setStyleSheet(QSS)

    init_db()
    log("INFO", "main", "DB inicializada")

    window = MainWindow()
    # ── Arranca en bandeja, sin ventana visible ───────────────────────────────
    # window.show() — eliminado: solo abre desde el tray

    # ── Tray ──────────────────────────────────────────────────────────────────
    _icon_normal = _make_icon(False)
    _icon_alert  = _make_icon(True)

    tray = QSystemTrayIcon(_icon_normal, app)
    tray.setToolTip("CyberAgent — activo")

    def tray_notify(title, body, icon=QSystemTrayIcon.Information, msecs=4000):
        """Globo de notificación que se calla si hay un juego a pantalla
        completa delante (para no sacarte del fullscreen mientras juegas)."""
        try:
            from app.winfocus import foreground_is_fullscreen
            if foreground_is_fullscreen():
                return
        except Exception:
            pass
        tray.showMessage(title, body, icon, msecs)

    menu = QMenu()
    show_action    = menu.addAction("⚡  Abrir CyberAgent")
    update_action  = menu.addAction("🔄  Buscar actualización")
    health_action  = menu.addAction("🩺  Estado de servicios")
    vram_action    = menu.addAction("🎮  Liberar VRAM (para jugar)")
    menu.addSeparator()
    restart_action = menu.addAction("↻  Reiniciar CyberAgent")
    quit_action    = menu.addAction("✕  Salir")
    tray.setContextMenu(menu)

    # Mejora 2: salud del supervisor visible. Notificación al pulsar + tooltip vivo.
    def _service_summary():
        try:
            from app.supervisor import supervisor_status
            st = supervisor_status()
            emoji = {True: "✅", False: "❌", None: "⏳"}
            lines = [f"{emoji.get(s.get('ok'),'⏳')} {s['service']}: {s.get('detail','')[:60]}"
                     for s in st.get("services", [])]
            # H-02: estado del módulo de seguridad en el resumen del tray.
            try:
                from app.security import SECURITY_ENABLED
                from app.security import notify as _sec_notify
                from app.security import cameras_db as _cdb
                sec_on = "activo" if SECURITY_ENABLED else "desactivado"
                tg = "Telegram✓" if _sec_notify.available() else "Telegram✗"
                try:
                    ncam = _cdb.count()
                except Exception:
                    ncam = 0
                lines.append(f"🛡️ seguridad: {sec_on} · {tg} · {ncam} cámara(s)")
            except Exception:
                pass
            return st.get("healthy"), "\n".join(lines) or "(supervisor iniciando)"
        except Exception as e:
            return None, f"sin datos: {e}"

    def _show_health():
        healthy, body = _service_summary()
        title = "CyberAgent — servicios " + ("OK ✅" if healthy else "con avisos ⚠️" if healthy is False else "iniciando ⏳")
        tray_notify(title, body, QSystemTrayIcon.Information, 6000)

    health_action.triggered.connect(_show_health)

    def _refresh_health_tooltip():
        healthy, _ = _service_summary()
        mark = "✅" if healthy else "⚠️" if healthy is False else "⏳"
        tray.setToolTip(f"CyberAgent — servicios {mark}")
    _health_timer = QTimer()
    _health_timer.timeout.connect(_refresh_health_tooltip)
    _health_timer.start(20000)   # cada 20s

    def _restart_app():
        """Relanza una instancia nueva y cierra la actual (control de instancia).

        Usa un relanzador desacoplado que ESPERA a que este proceso muera (y
        suelte el mutex) antes de arrancar la nueva instancia, evitando que la
        nueva se cierre sola al ver el mutex todavía tomado.
        """
        try:
            tray_notify("CyberAgent", "Reiniciando…", QSystemTrayIcon.Information, 1500)
        except Exception:
            pass
        if getattr(sys, "frozen", False):
            cmd = [sys.executable] + sys.argv[1:]
        else:
            py = sys.executable
            pyw = py.replace("python.exe", "pythonw.exe")
            if os.path.isfile(pyw):
                py = pyw
            cmd = [py, os.path.abspath(sys.argv[0])] + sys.argv[1:]
        try:
            from app.updater import relaunch_detached
            relaunch_detached(cmd, cwd=os.path.dirname(os.path.abspath(sys.argv[0])) or None)
        except Exception as e:
            print(f"[restart] {e}")
        # Libera el mutex y cierra; el relanzador espera a que muramos.
        try:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        QTimer.singleShot(200, app.quit)

    def _toggle_window():
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    def _free_vram_tray():
        # Descarga los modelos vía la API de Ollama (keep_alive=0) — funciona en
        # Ollama actual; el viejo 'Stop-Process llama-server' ya no aplicaba.
        # En un hilo para no congelar la UI; Ollama sigue vivo (el supervisor no
        # lo reinicia), así la GPU queda libre para jugar.
        import threading as _th

        def _do():
            try:
                from app.ollama_client import free_vram
                n = free_vram()
                msg = (f"VRAM liberada ({n} modelo(s)) — GPU lista para jugar"
                       if n else "No había modelos cargados — GPU ya libre")
            except Exception as e:
                msg = f"No se pudo liberar VRAM: {e}"
            tray_notify("CyberAgent", msg, QSystemTrayIcon.Information, 3000)

        _th.Thread(target=_do, daemon=True, name="free-vram").start()

    show_action.triggered.connect(_toggle_window)
    vram_action.triggered.connect(_free_vram_tray)
    restart_action.triggered.connect(_restart_app)
    quit_action.triggered.connect(app.quit)

    # Clic izquierdo en tray → mostrar/ocultar
    tray.activated.connect(
        lambda reason: _toggle_window()
        if reason == QSystemTrayIcon.Trigger else None
    )

    # ── Icono dinámico (parpadeo rojo en aprobación pendiente) ─────────────
    _blink_timer = QTimer()
    _blink_state = [False]

    def _set_tray_alert(pending: bool):
        if pending:
            _blink_timer.start(700)
            tray.setToolTip("CyberAgent — ⚠️ Aprobación pendiente")
        else:
            _blink_timer.stop()
            tray.setIcon(_icon_normal)
            tray.setToolTip("CyberAgent — activo")

    def _blink():
        _blink_state[0] = not _blink_state[0]
        tray.setIcon(_icon_alert if _blink_state[0] else _icon_normal)

    _blink_timer.timeout.connect(_blink)
    window.notification_pending.connect(_set_tray_alert)

    # ── Auto-updater ──────────────────────────────────────────────────────────
    _checker: list = []

    def _run_checker():
        checker = UpdateChecker()
        checker.update_available.connect(
            lambda loc, rem: (
                window.notify_update_available(loc, rem),
                tray_notify(
                    "CyberAgent — Actualización disponible",
                    f"Nueva versión: {rem}",
                    QSystemTrayIcon.Information, 6000,
                ),
            )
        )
        checker.up_to_date.connect(window.notify_up_to_date)
        checker.finished.connect(
            lambda c=checker: _checker.remove(c) if c in _checker else None
        )
        _checker.append(checker)
        checker.start()

    update_action.triggered.connect(_run_checker)
    QTimer.singleShot(3000, _run_checker)
    periodic = QTimer()
    periodic.timeout.connect(_run_checker)
    periodic.start(30 * 60 * 1000)

    # ── Servidor API local ────────────────────────────────────────────────────
    try:
        from app.api.server import start_server
        start_server(port=8765)
        # Health-check: el server arranca en un hilo y puede fallar al enlazar en
        # silencio (p.ej. puerto ocupado). Verificamos a los pocos segundos y lo
        # dejamos REGISTRADO con un aviso claro en vez de quedar caído sin rastro.
        def _check_api_up():
            import socket
            for _ in range(10):
                try:
                    with socket.create_connection(("127.0.0.1", 8765), timeout=1):
                        return
                except OSError:
                    import time as _t; _t.sleep(1)
            try:
                from app.agent_log import log as _alog
                _alog("ERROR", "main", "El servidor local :8765 NO enlazó tras 10s "
                      "(web del PC y túnel no disponibles). Revisa puerto ocupado o stdout/stderr.")
            except Exception:
                pass
        import threading as _th
        _th.Thread(target=_check_api_up, daemon=True, name="api-healthcheck").start()
    except Exception as e:
        print(f"[api] No se pudo iniciar servidor: {e}")

    # ── Relay connector (si RELAY_URL está configurado en .env) ───────────────
    try:
        from app.api.relay_connector import start_relay_connector
        start_relay_connector()
    except Exception as e:
        print(f"[relay] No se pudo iniciar conector: {e}")

    # ── Supervisor: 3 servicios guardianes (datos · Ollama · conexión) ────────
    try:
        from app.supervisor import start_supervisor
        start_supervisor()
    except Exception as e:
        print(f"[supervisor] No se pudo iniciar: {e}")

    # ── Autoaprendizaje autónomo ──────────────────────────────────────────────
    try:
        from app.autonomous_learner import start_learner
        start_learner(interval_check=1800)   # verifica cada 30 min
    except Exception as e:
        print(f"[learner] No se pudo iniciar autoaprendizaje: {e}")


    # ── Cloudflare Tunnel ─────────────────────────────────────────────────────
    def _start_tunnel():
        import threading
        def _run():
            try:
                from app.api.tunnel import TunnelManager
                tm = TunnelManager(local_port=8765)
                url = tm.start(wait_secs=20)
                if url:
                    tray_notify(
                        "CyberAgent — Túnel activo",
                        f"Acceso web: {url}",
                        QSystemTrayIcon.Information, 6000,
                    )
            except Exception as e:
                print(f"[tunnel] Error: {e}")
        threading.Thread(target=_run, daemon=True, name="tunnel-starter").start()

    QTimer.singleShot(5000, _start_tunnel)

    # Reanuda tareas programadas persistidas (SCHED-001), sin bloquear el arranque
    def _resume_scheduler():
        try:
            from app.scheduler import start_if_pending
            start_if_pending()
        except Exception as e:
            print(f"[scheduler] {e}")
    QTimer.singleShot(6000, _resume_scheduler)

    tray.show()

    # Notificación de bienvenida
    tray_notify(
        "CyberAgent activo",
        "Clic en el icono para abrir · Clic derecho para opciones",
        QSystemTrayIcon.Information, 3000,
    )

    # Al salir: para apps desplegadas (procesos + túneles) y el supervisor, para
    # no dejar procesos/túneles Cloudflare huérfanos.
    def _cleanup_on_quit():
        try:
            from app.deployer import stop_all
            stop_all()
        except Exception:
            pass
        try:
            from app.supervisor import _SUPERVISOR
            if _SUPERVISOR:
                _SUPERVISOR.stop()
        except Exception:
            pass
    app.aboutToQuit.connect(_cleanup_on_quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
