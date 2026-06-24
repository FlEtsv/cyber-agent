import json
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit)
from PySide6.QtCore import Signal, Qt

TOOL_ICONS = {
    "shell": "⚡", "run_python": "⬡", "write_file": "✎",
    "read_file": "▤", "list_directory": "▥", "web_fetch": "◎",
    "list_processes": "◈", "screenshot": "⊡",
    "install_package": "⬇", "uninstall_package": "⬆", "system_info": "◉",
}


class ToolActivityRow(QFrame):
    """Trace card displayed inside the collapsible actions section."""

    def __init__(self, tool_id: str, name: str, args: dict, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self._status = None
        self._args_box = None
        self._result_box = None
        self._build(name, args)

    @staticmethod
    def _format_payload(payload, limit: int = 6000) -> str:
        try:
            text = json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            text = str(payload)
        if len(text) > limit:
            return text[:limit] + "\n... [salida recortada en UI]"
        return text

    def _build(self, name: str, args: dict):
        self.setObjectName("tool_activity_row")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 7, 8, 7)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        icon = TOOL_ICONS.get(name, "tool")
        name_lbl = QLabel(f"{icon}  {name}")
        name_lbl.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: 600;")
        header.addWidget(name_lbl)
        header.addStretch()

        self._status = QLabel("working")
        self._status.setStyleSheet("color: #e3b341; font-size: 11px;")
        header.addWidget(self._status)
        root.addLayout(header)

        self._args_box = QTextEdit()
        self._args_box.setPlainText(self._format_payload(args, limit=4000))
        self._args_box.setReadOnly(True)
        self._args_box.setMaximumHeight(120)
        self._args_box.setObjectName("tool_trace_box")
        root.addWidget(self._args_box)

        self._result_box = QTextEdit()
        self._result_box.setReadOnly(True)
        self._result_box.setMaximumHeight(160)
        self._result_box.setObjectName("tool_trace_box")
        self._result_box.hide()
        root.addWidget(self._result_box)

    def set_done(self, result=None):
        self._status.setText("done")
        self._status.setStyleSheet("color: #3fb950; font-size: 11px;")
        if result is not None and self._result_box:
            self._result_box.setPlainText(self._format_payload(result))
            self._result_box.show()

    def set_cancelled(self):
        self._status.setText("cancelled")
        self._status.setStyleSheet("color: #f85149; font-size: 11px;")

class ToolApprovalCard(QFrame):
    """Large approval card shown inline below the AI response."""
    approved = Signal(str, str, bool)
    rejected = Signal(str)

    def __init__(self, tool_id: str, name: str, args: dict, dangerous: bool, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.tool_name = name
        self._build(name, args, dangerous)

    def _build(self, name: str, args: dict, dangerous: bool):
        self.setObjectName("approval_card_dangerous" if dangerous else "approval_card_safe")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        icon = TOOL_ICONS.get(name, "○")
        color = "#f85149" if dangerous else "#58a6ff"
        suffix = ("  <span style='color:#e3b341; font-size:11px'>— requiere confirmación</span>"
                  if dangerous else "")
        hdr = QLabel(
            f"<span style='color:{color}; font-weight:600; font-size:13px'>"
            f"{icon}  {name}</span>{suffix}"
        )
        hdr.setTextFormat(Qt.RichText)
        lay.addWidget(hdr)

        args_box = QTextEdit()
        args_box.setPlainText(json.dumps(args, indent=2, ensure_ascii=False))
        args_box.setReadOnly(True)
        args_box.setMaximumHeight(90)
        args_box.setObjectName("approval_args_box")
        lay.addWidget(args_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_approve = QPushButton("Ejecutar")
        self.btn_approve.setObjectName("btn_approve")
        self.btn_approve.setMinimumHeight(34)
        self.btn_approve.clicked.connect(
            lambda: self.approved.emit(self.tool_id, self.tool_name, False)
        )
        self.btn_always = QPushButton("Permitir siempre")
        self.btn_always.setObjectName("btn_always")
        self.btn_always.setMinimumHeight(34)
        self.btn_always.clicked.connect(
            lambda: self.approved.emit(self.tool_id, self.tool_name, True)
        )
        self.btn_reject = QPushButton("Rechazar")
        self.btn_reject.setObjectName("btn_reject")
        self.btn_reject.setMinimumHeight(34)
        self.btn_reject.clicked.connect(lambda: self.rejected.emit(self.tool_id))

        btn_row.addWidget(self.btn_approve)
        btn_row.addWidget(self.btn_always)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_reject)
        lay.addLayout(btn_row)
