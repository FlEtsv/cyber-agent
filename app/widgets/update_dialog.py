from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QApplication,
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
        self.setMinimumWidth(540)
        self.setStyleSheet(
            "QDialog { background: #080c0f; color: #c9d1d9; font-family: monospace; }"
        )
        self._worker  = None
        self._zip     = None
        self._build(local, remote_info)

    def _build(self, local: str, remote_info: str):
        from app.updater import is_frozen
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
        self.log.setMinimumHeight(140)
        self.log.setStyleSheet(
            "background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
            " color: #00ff88; font-family: monospace; font-size: 11px; padding: 6px;"
        )
        lay.addWidget(self.log)

        btn_row = QHBoxLayout()

        lbl = "⬇  Descargar e instalar" if is_frozen() else "⬇  Actualizar ahora"
        self.update_btn = QPushButton(lbl)
        self.update_btn.setStyleSheet(_BTN.format(bg="#0d1a2d", border="#00d9ff"))
        self.update_btn.clicked.connect(self._do_update)
        btn_row.addWidget(self.update_btn)

        self.apply_btn = QPushButton("🔁  Aplicar y reiniciar")
        self.apply_btn.setStyleSheet(_BTN.format(bg="#0d1a1a", border="#00ff88"))
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_and_restart)
        btn_row.addWidget(self.apply_btn)

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
        from app.updater import is_frozen, Updater, ReleaseUpdater
        self.update_btn.setEnabled(False)
        self.log.clear()

        # Clean up previous worker before starting a new one
        if self._worker is not None:
            try:
                self._worker.progress.disconnect()
                self._worker.done.disconnect() if hasattr(self._worker, 'done') else None
                self._worker.ready.disconnect() if hasattr(self._worker, 'ready') else None
                self._worker.failed.disconnect()
            except RuntimeError:
                pass
            self._worker.quit()
            self._worker.wait(2000)
            self._worker.deleteLater()
            self._worker = None

        if is_frozen():
            self._worker = ReleaseUpdater()
            self._worker.progress.connect(self._on_progress)
            self._worker.ready.connect(self._on_zip_ready)
            self._worker.failed.connect(self._on_failed)
        else:
            self._worker = Updater()
            self._worker.progress.connect(self._on_progress)
            self._worker.done.connect(self._on_source_done)
            self._worker.failed.connect(self._on_failed)

        self._worker.start()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
            self._worker.deleteLater()
        super().closeEvent(event)

    def _on_progress(self, msg: str):
        self.log.append(msg)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _on_zip_ready(self, zip_path: str):
        self._zip = zip_path
        self.log.append("\n✓ Descarga completada. Pulsa 'Aplicar y reiniciar' para instalar.")
        self.apply_btn.setEnabled(True)

    def _on_source_done(self, new_ver: str):
        self.log.append(f"\n✓ Versión actualizada: {new_ver}")
        self.apply_btn.setText("🔁  Reiniciar")
        self.apply_btn.setEnabled(True)
        self._zip = None

    def _on_failed(self, err: str):
        self.log.append(f"\n[ERROR]\n{err}")
        self.update_btn.setEnabled(True)

    def _apply_and_restart(self):
        from app.updater import is_frozen, apply_frozen_update, restart
        self.apply_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        if is_frozen() and self._zip:
            self.log.append("\nAplicando actualización y reiniciando...")
            # Process events before blocking file operation, but prevent close
            self.setWindowFlag(Qt.WindowCloseButtonHint, False)
            self.show()
            QApplication.processEvents()
            apply_frozen_update(self._zip)
            QApplication.quit()
        else:
            restart()
