from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
)
from PySide6.QtCore import Qt

_BTN = (
    "QPushButton {{ background: {bg}; border: 1px solid {border}; border-radius: 5px;"
    " color: {border}; padding: 6px 16px; font-size: 12px; }}"
    "QPushButton:hover {{ background: rgba(0,217,255,0.08); }}"
    "QPushButton:disabled {{ color: #2a3a4a; border-color: #1e2d3d; background: transparent; }}"
)


class UpdateDialog(QDialog):
    def __init__(self, local: str, remote_info: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 Actualización disponible")
        self.setMinimumWidth(520)
        self.setStyleSheet(
            "QDialog { background: #080c0f; color: #c9d1d9; font-family: monospace; }"
        )
        self._worker = None
        self._build(local, remote_info)

    def _build(self, local: str, remote_info: str):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 16)

        title = QLabel("🔄  Nueva actualización disponible")
        title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        lay.addWidget(title)

        info = QLabel(
            f"<b>Local:</b>  {local}<br>"
            f"<b>Remoto:</b> {remote_info}"
        )
        info.setStyleSheet("color: #c9d1d9; font-size: 12px; padding: 4px 0;")
        info.setTextFormat(Qt.RichText)
        lay.addWidget(info)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)
        self.log.setStyleSheet(
            "background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
            " color: #00ff88; font-family: monospace; font-size: 11px; padding: 6px;"
        )
        lay.addWidget(self.log)

        btn_row = QHBoxLayout()

        self.update_btn = QPushButton("⬇  Actualizar ahora")
        self.update_btn.setStyleSheet(_BTN.format(bg="#0d1a2d", border="#00d9ff"))
        self.update_btn.clicked.connect(self._do_update)
        btn_row.addWidget(self.update_btn)

        self.restart_btn = QPushButton("🔁  Reiniciar")
        self.restart_btn.setStyleSheet(_BTN.format(bg="#0d1a1a", border="#00ff88"))
        self.restart_btn.setEnabled(False)
        self.restart_btn.clicked.connect(self._restart)
        btn_row.addWidget(self.restart_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Después")
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #1e2d3d;"
            " border-radius: 5px; color: #4a5568; padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { border-color: #4a5568; color: #c9d1d9; }"
        )
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        lay.addLayout(btn_row)

    def _do_update(self):
        from app.updater import Updater
        self.update_btn.setEnabled(False)
        self.log.clear()
        self.log.append("Actualizando desde GitHub...")
        self._worker = Updater()
        self._worker.progress.connect(self.log.append)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, new_sha: str):
        self.log.append(f"\n✓ Versión actualizada a: {new_sha}")
        self.restart_btn.setEnabled(True)

    def _on_failed(self, err: str):
        self.log.append(f"\n[ERROR]\n{err}")
        self.log.append("\nIntenta manualmente: git pull origin master")
        self.update_btn.setEnabled(True)

    def _restart(self):
        from app.updater import restart
        restart()
