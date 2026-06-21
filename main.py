import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer
from app.styles import QSS
from app.database import init_db
from app.widgets.main_window import MainWindow
from app.updater import UpdateChecker

def make_tray_icon():
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#00d9ff"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 24, 24)
    painter.setPen(QColor("#080c0f"))
    f = QFont("Arial", 14, QFont.Bold)
    painter.setFont(f)
    painter.drawText(pix.rect(), Qt.AlignCenter, "⚡")
    painter.end()
    return QIcon(pix)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CyberAgent")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(QSS)

    init_db()

    window = MainWindow()
    window.show()

    # System tray
    icon = make_tray_icon()
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("CyberAgent — activo")

    menu = QMenu()
    show_action   = menu.addAction("Mostrar / Ocultar")
    update_action = menu.addAction("🔄 Buscar actualización")
    menu.addSeparator()
    quit_action   = menu.addAction("Salir")
    tray.setContextMenu(menu)

    show_action.triggered.connect(lambda: window.hide() if window.isVisible() else window.show())
    quit_action.triggered.connect(app.quit)
    tray.activated.connect(lambda reason: (
        window.hide() if window.isVisible() else window.show()
    ) if reason == QSystemTrayIcon.Trigger else None)

    # ── Auto-updater ──────────────────────────────────────────────────
    _checker: list = []  # keep reference alive

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

    # Check on startup after 3 s, then every 30 min
    QTimer.singleShot(3000, _run_checker)
    periodic = QTimer()
    periodic.timeout.connect(_run_checker)
    periodic.start(30 * 60 * 1000)

    tray.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
