import json
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QSizePolicy)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

TOOL_ICONS = {
    "shell": "⚡", "run_python": "🐍", "write_file": "✏️",
    "read_file": "📄", "list_directory": "📁",
    "web_fetch": "🌐", "list_processes": "⚙️", "screenshot": "📷",
}

class ToolCard(QFrame):
    approved = Signal(str, str, bool)  # tool_id, tool_name, always_allow
    rejected = Signal(str)

    def __init__(self, tool_id, name, args, dangerous, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.tool_name = name
        self.dangerous = dangerous
        self.is_done = False
        self._build(args)

    def _build(self, args):
        frame_id = "tool_card_dangerous" if self.dangerous else "tool_card_safe"
        self.setObjectName(frame_id)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        # Header
        header = QHBoxLayout()
        icon = TOOL_ICONS.get(self.tool_name, "🔧")
        badge_color = "#ff4466" if self.dangerous else "#00d9ff"
        label = QLabel(f"{icon} <span style='color:{badge_color};font-weight:bold'>{self.tool_name}</span>"
                       + (" <span style='color:#ff4466;font-size:10px'>● PELIGROSA</span>" if self.dangerous else ""))
        label.setTextFormat(Qt.RichText)
        header.addWidget(label)
        header.addStretch()
        self.status_label = QLabel("⏳ pendiente")
        self.status_label.setStyleSheet("color: #ffd700; font-size: 11px;")
        header.addWidget(self.status_label)
        lay.addLayout(header)

        # Args
        args_text = json.dumps(args, indent=2, ensure_ascii=False)
        args_box = QTextEdit()
        args_box.setPlainText(args_text)
        args_box.setReadOnly(True)
        args_box.setMaximumHeight(120)
        args_box.setStyleSheet("""
            QTextEdit {
                background: #080c0f;
                border: 1px solid #1e2d3d;
                border-radius: 6px;
                color: #c9d1d9;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 6px;
            }
        """)
        lay.addWidget(args_box)

        # Approval buttons
        self.btn_area = QFrame()
        btn_lay = QHBoxLayout(self.btn_area)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.setSpacing(8)

        self.btn_approve = QPushButton("✓  Ejecutar")
        self.btn_approve.setObjectName("btn_approve")
        self.btn_approve.clicked.connect(lambda: self.approved.emit(self.tool_id, self.tool_name, False))

        self.btn_always = QPushButton("Permitir siempre")
        self.btn_always.setObjectName("btn_always")
        self.btn_always.clicked.connect(lambda: self.approved.emit(self.tool_id, self.tool_name, True))

        self.btn_reject = QPushButton("✗  Rechazar")
        self.btn_reject.setObjectName("btn_reject")
        self.btn_reject.clicked.connect(lambda: self.rejected.emit(self.tool_id))

        btn_lay.addWidget(self.btn_approve)
        btn_lay.addWidget(self.btn_always)
        btn_lay.addStretch()
        btn_lay.addWidget(self.btn_reject)
        lay.addWidget(self.btn_area)

        # Result area (hidden initially)
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMaximumHeight(150)
        self.result_box.hide()
        self.result_box.setStyleSheet("""
            QTextEdit {
                background: #080c0f;
                border: 1px solid rgba(0, 255, 136, 0.2);
                border-radius: 6px;
                color: #00ff88;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)
        lay.addWidget(self.result_box)

    def set_result(self, result):
        self.is_done = True
        self.setObjectName("tool_card_done")
        self.setStyle(self.style())
        self.status_label.setText("✓ completada")
        self.status_label.setStyleSheet("color: #00ff88; font-size: 11px;")
        self.btn_area.hide()

        result_text = json.dumps(result, indent=2, ensure_ascii=False)
        self.result_box.setPlainText(result_text[:3000])
        self.result_box.show()

    def set_cancelled(self):
        self.status_label.setText("✗ cancelada")
        self.status_label.setStyleSheet("color: #ff4466; font-size: 11px;")
        self.btn_area.hide()
