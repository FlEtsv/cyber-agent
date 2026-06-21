import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Carga .env si existe (variables para Cloud Run notifications)
_env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_env_file):
    for _line in open(_env_file):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer
from app.styles import QSS
from app.database import init_db
from app.widgets.main_window import MainWindow
from app.updater import UpdateChecker


def _make_icon(alert: bool = False) -> QIcon:
    """Icono de tray — azul normal, rojo pulsante cuando hay aprobación pendiente."""
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
    app = QApplication(sys.argv)
    app.setApplicationName("CyberAgent")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(QSS)

    init_db()

    window = MainWindow()
    window.show()

    # ── Tray ──────────────────────────────────────────────────────────────
    _icon_normal = _make_icon(False)
    _icon_alert  = _make_icon(True)

    tray = QSystemTrayIcon(_icon_normal, app)
    tray.setToolTip("CyberAgent — activo")

    menu = QMenu()
    show_action   = menu.addAction("Mostrar / Ocultar")
    update_action = menu.addAction("🔄 Buscar actualización")
    menu.addSeparator()
    quit_action   = menu.addAction("Salir")
    tray.setContextMenu(menu)

    show_action.triggered.connect(
        lambda: window.hide() if window.isVisible() else window.show()
    )
    quit_action.triggered.connect(app.quit)
    tray.activated.connect(lambda reason: (
        window.hide() if window.isVisible() else window.show()
    ) if reason == QSystemTrayIcon.Trigger else None)

    # ── Icono dinámico ─────────────────────────────────────────────────────
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

    # ── Auto-updater ──────────────────────────────────────────────────────
    _checker: list = []

    def _run_checker():
        checker = UpdateChecker()
        checker.update_available.connect(
            lambda loc, rem: (
                window.notify_update_available(loc, rem),
                tray.showMessage(
                    "CyberAgent — Actualización",
                    f"Nueva versión disponible: {rem}",
                    QSystemTrayIcon.Information, 5000,
                ),
            )
        )
        checker.up_to_date.connect(window.notify_up_to_date)
        _checker.append(checker)
        checker.start()

    update_action.triggered.connect(_run_checker)
    QTimer.singleShot(3000, _run_checker)
    periodic = QTimer()
    periodic.timeout.connect(_run_checker)
    periodic.start(30 * 60 * 1000)

    # ── Servidor API local ────────────────────────────────────────────────
    try:
        from app.api.server import start_server
        start_server(port=8765)
        print("[api] Servidor local iniciado en localhost:8765")
    except Exception as e:
        print(f"[api] No se pudo iniciar servidor: {e}")

    # ── Cloudflare Tunnel — en hilo separado para no bloquear la UI ──────
    def _start_tunnel():
        import threading
        def _run():
            try:
                from app.api.tunnel import TunnelManager
                tm = TunnelManager(local_port=8765)
                url = tm.start(wait_secs=20)
                if url:
                    print(f"[tunnel] ✓ {url}")
                    tray.showMessage(
                        "CyberAgent — Túnel activo",
                        f"Acceso web: {url}",
                        QSystemTrayIcon.Information, 6000,
                    )
                else:
                    print("[tunnel] cloudflared no disponible — instala: winget install Cloudflare.cloudflared")
            except Exception as e:
                print(f"[tunnel] Error: {e}")
        threading.Thread(target=_run, daemon=True, name="tunnel-starter").start()

    QTimer.singleShot(5000, _start_tunnel)

    tray.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
