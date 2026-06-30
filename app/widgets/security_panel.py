"""
SEC-003: Panel de Seguridad en la GUI de escritorio.

Estructura visible, funciones deshabilitadas (gateadas por SECURITY_ENABLED).
Telegram siempre activo (notif ya funciona). El resto muestra "próximamente".
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout,
)


class _TelegramTestWorker(QThread):
    done = Signal(bool, str)

    def run(self):
        try:
            from app.security.notify import notify, available
            if not available():
                self.done.emit(False, "No configurado (faltan token/chat_id en el vault)")
                return
            r = notify(title="CyberAgent PC — test de notificación",
                       body="Telegram funcionando correctamente desde la GUI.", emoji="🔔")
            self.done.emit(r.get("ok", False), r.get("error") or "")
        except Exception as e:
            self.done.emit(False, str(e))


class SecurityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("security_panel")
        self._worker: _TelegramTestWorker | None = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        # ── Cabecera ───────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("🛡️  Seguridad")
        title.setObjectName("sec_title")
        title.setStyleSheet("font-size: 20px; font-weight: 700; letter-spacing: -0.01em;")
        hdr.addWidget(title)
        hdr.addStretch()
        lay.addLayout(hdr)

        subtitle = QLabel("Control del hogar, cámaras, alertas y autonomía. "
                          "Telegram activo · resto próximamente.")
        subtitle.setObjectName("sec_subtitle")
        subtitle.setStyleSheet("color: #5a6478; font-size: 13px;")
        lay.addWidget(subtitle)

        lay.addWidget(self._separator())

        # ── Grid de cards ──────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        cards = [
            ("📱", "Telegram",  True,  "Activo",       self._card_telegram),
            ("📷", "Cámaras",   False, "Próximamente", None),
            ("🚨", "Alertas",   False, "Próximamente", None),
            ("🏠", "Eventos",   False, "Próximamente", None),
            ("🤖", "Autonomía", False, "Próximamente", None),
            ("🐳", "Docker",    False, "Próximamente", None),
        ]

        for i, (ico, name, active, badge, factory) in enumerate(cards):
            card = factory() if factory else self._card_disabled(ico, name)
            grid.addWidget(card, i // 2, i % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

    # ── Card: Telegram (activo) ────────────────────────────────────────
    def _card_telegram(self) -> QWidget:
        card = QFrame()
        card.setObjectName("sec_card_active")
        card.setStyleSheet(
            "#sec_card_active { background: #061a10; border: 1px solid #1a5c3a; "
            "border-radius: 10px; padding: 16px; }"
        )
        lay = QVBoxLayout(card)
        lay.setSpacing(8)

        row = QHBoxLayout()
        ico = QLabel("📱")
        ico.setStyleSheet("font-size: 26px;")
        row.addWidget(ico)
        row.addStretch()
        badge = QLabel("Activo")
        badge.setStyleSheet(
            "background: #0a3020; color: #3ecf8e; border: 1px solid #1a5c3a; "
            "border-radius: 100px; padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )
        row.addWidget(badge)
        lay.addLayout(row)

        name_lbl = QLabel("Telegram")
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #e8eaf0;")
        lay.addWidget(name_lbl)

        desc = QLabel("Notificaciones automáticas: tarea completada,\naprobación pendiente, alertas.")
        desc.setStyleSheet("font-size: 12px; color: #6b7a94;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self._tg_btn = QPushButton("Probar ahora")
        self._tg_btn.setObjectName("btn_refs")
        self._tg_btn.setStyleSheet(
            "QPushButton { background: #0d3a1f; color: #3ecf8e; border: 1px solid #1a5c3a; "
            "border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #144d29; }"
            "QPushButton:disabled { opacity: 0.4; }"
        )
        self._tg_btn.clicked.connect(self._test_telegram)
        lay.addWidget(self._tg_btn)

        self._tg_status = QLabel("")
        self._tg_status.setStyleSheet("font-size: 11px; color: #6b7a94;")
        lay.addWidget(self._tg_status)

        return card

    def _test_telegram(self):
        self._tg_btn.setEnabled(False)
        self._tg_btn.setText("Enviando…")
        self._tg_status.setText("")
        self._worker = _TelegramTestWorker()
        self._worker.done.connect(self._on_tg_done)
        self._worker.start()

    def _on_tg_done(self, ok: bool, err: str):
        if ok:
            self._tg_btn.setText("✅ Enviado")
            self._tg_status.setText("Mensaje de prueba enviado correctamente.")
            self._tg_status.setStyleSheet("font-size: 11px; color: #3ecf8e;")
        else:
            self._tg_btn.setText("❌ Error")
            self._tg_status.setText(err or "Error desconocido")
            self._tg_status.setStyleSheet("font-size: 11px; color: #e05252;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: (
            self._tg_btn.setEnabled(True),
            self._tg_btn.setText("Probar ahora"),
        ))

    # ── Card: deshabilitada ────────────────────────────────────────────
    def _card_disabled(self, ico: str, name: str) -> QWidget:
        card = QFrame()
        card.setObjectName("sec_card_disabled")
        card.setStyleSheet(
            "#sec_card_disabled { background: #0e1117; border: 1px solid #1e2330; "
            "border-radius: 10px; padding: 16px; opacity: 0.6; }"
        )
        lay = QVBoxLayout(card)
        lay.setSpacing(6)

        row = QHBoxLayout()
        ico_lbl = QLabel(ico)
        ico_lbl.setStyleSheet("font-size: 26px;")
        row.addWidget(ico_lbl)
        row.addStretch()
        badge = QLabel("Próximamente")
        badge.setStyleSheet(
            "background: #141820; color: #4a5568; border: 1px solid #1e2330; "
            "border-radius: 100px; padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )
        row.addWidget(badge)
        lay.addLayout(row)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #3d4558;")
        lay.addWidget(name_lbl)

        return card

    @staticmethod
    def _separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("tab_line")
        return sep
