"""Diálogo QR para suscribir el móvil a las notificaciones push."""
import os, io
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont

_BTN = (
    "QPushButton {{ background: {bg}; border: 1px solid {border}; border-radius: 5px;"
    " color: {border}; padding: 7px 18px; font-size: 12px; }}"
    "QPushButton:hover {{ background: rgba(0,217,255,0.1); }}"
)


def _make_qr_pixmap(url: str, size: int = 260) -> QPixmap | None:
    try:
        import qrcode
        from PIL import Image as PILImage
        qr = qrcode.QRCode(version=1, box_size=7, border=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#00d9ff", back_color="#080c0f")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pix = QPixmap()
        pix.loadFromData(buf.read())
        return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        return None


class MobileSubscribeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cloud_url = os.environ.get("CYBERAGENT_CLOUD_URL", "").rstrip("/")
        self.setWindowTitle("📱 Activar notificaciones en el móvil")
        self.setMinimumWidth(340)
        self.setStyleSheet(
            "QDialog { background: #080c0f; color: #c9d1d9; font-family: monospace; }"
        )
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        title = QLabel("📱 Suscribir móvil a notificaciones")
        title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        if not self.cloud_url:
            err = QLabel(
                "⚠️ CYBERAGENT_CLOUD_URL no configurada.\n"
                "Añade la URL al archivo .env"
            )
            err.setStyleSheet("color: #ff4466; font-size: 12px;")
            err.setAlignment(Qt.AlignCenter)
            lay.addWidget(err)
            lay.addWidget(self._close_btn())
            return

        instr = QLabel(
            "Abre este código QR con la cámara del móvil\n"
            "(o copia la URL y ábrela en Chrome)"
        )
        instr.setStyleSheet("color: #4a5568; font-size: 11px;")
        instr.setAlignment(Qt.AlignCenter)
        lay.addWidget(instr)

        # QR code
        qr_pix = _make_qr_pixmap(self.cloud_url)
        if qr_pix:
            qr_lbl = QLabel()
            qr_lbl.setPixmap(qr_pix)
            qr_lbl.setAlignment(Qt.AlignCenter)
            qr_lbl.setStyleSheet(
                "border: 2px solid #1e2d3d; border-radius: 8px; padding: 8px;"
                " background: #080c0f;"
            )
            lay.addWidget(qr_lbl)
        else:
            no_qr = QLabel(
                "⚠️ Instala el paquete qrcode para ver el código QR:\n"
                "pip install qrcode[pil]"
            )
            no_qr.setStyleSheet("color: #ffd700; font-size: 11px; text-align: center;")
            no_qr.setAlignment(Qt.AlignCenter)
            lay.addWidget(no_qr)

        # URL copiable
        url_lbl = QLabel(self.cloud_url)
        url_lbl.setStyleSheet(
            "color: #00ff88; font-size: 11px; padding: 6px 10px;"
            " background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
        )
        url_lbl.setAlignment(Qt.AlignCenter)
        url_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(url_lbl)

        steps = QLabel(
            "① Abre la URL  ②  Pulsa 'Activar notificaciones'  ③  Acepta el permiso"
        )
        steps.setStyleSheet("color: #c9d1d9; font-size: 11px;")
        steps.setAlignment(Qt.AlignCenter)
        lay.addWidget(steps)

        # Buttons
        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 Copiar URL")
        copy_btn.setStyleSheet(_BTN.format(bg="#0d1a2d", border="#00d9ff"))
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.cloud_url))
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(self._close_btn())
        lay.addLayout(btn_row)

    def _close_btn(self) -> QPushButton:
        btn = QPushButton("Cerrar")
        btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #1e2d3d;"
            " border-radius: 5px; color: #4a5568; padding: 7px 18px; font-size: 12px; }"
            "QPushButton:hover { border-color: #4a5568; color: #c9d1d9; }"
        )
        btn.clicked.connect(self.close)
        return btn
