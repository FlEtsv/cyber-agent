import sys, os, ctypes
sys.path.insert(0, os.path.dirname(__file__))

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
    vram_action    = menu.addAction("🎮  Liberar VRAM (para jugar)")
    menu.addSeparator()
    restart_action = menu.addAction("↻  Reiniciar CyberAgent")
    quit_action    = menu.addAction("✕  Salir")
    tray.setContextMenu(menu)

    def _restart_app():
        """Relanza una instancia nueva y cierra la actual (control de instancia)."""
        import subprocess
        try:
            tray_notify("CyberAgent", "Reiniciando…", QSystemTrayIcon.Information, 1500)
        except Exception:
            pass
        # Libera el mutex de instancia única para que la nueva instancia arranque
        try:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
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
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(sys.argv[0])) or None,
                             creationflags=flags, close_fds=True)
        except Exception as e:
            print(f"[restart] {e}")
        QTimer.singleShot(400, app.quit)

    def _toggle_window():
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    def _free_vram_tray():
        import subprocess
        subprocess.run(
            ["powershell", "-NonInteractive", "-Command",
             "Stop-Process -Name llama-server -Force -ErrorAction SilentlyContinue"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        tray_notify("CyberAgent", "VRAM liberada — GPU lista para jugar",
                    QSystemTrayIcon.Information, 3000)

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
    except Exception as e:
        print(f"[api] No se pudo iniciar servidor: {e}")

    # ── Relay connector (si RELAY_URL está configurado en .env) ───────────────
    try:
        from app.api.relay_connector import start_relay_connector
        start_relay_connector()
    except Exception as e:
        print(f"[relay] No se pudo iniciar conector: {e}")

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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
