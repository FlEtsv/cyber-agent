import json
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit)
from PySide6.QtCore import Signal, Qt

TOOL_ICONS = {
    "shell": "⚡", "run_python": "⬡", "write_file": "✎",
    "read_file": "▤", "list_directory": "▥", "web_fetch": "◎",
    "list_processes": "◈", "screenshot": "⊡",
    "install_package": "⬇", "uninstall_package": "⬆", "system_info": "◉",
    "mistral_consult": "AI",
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

    @staticmethod
    def _diff_html(result: dict) -> str:
        import html as _html
        path = str(result.get("path") or "archivo").replace("\\", "/").split("/")[-1]
        reps = result.get("replacements", 1)
        if result.get("syntax_ok") is False:
            badge = " <span style='color:#f85149'>⚠ sintaxis rota</span>"
        elif result.get("syntax_ok") is True:
            badge = " <span style='color:#3fb950'>✓ compila</span>"
        else:
            badge = ""
        rows = [f"<div style='color:#c9d1d9;margin-bottom:4px'>✎ {_html.escape(path)} "
                f"<span style='color:#8b949e'>({reps} cambio{'s' if reps != 1 else ''})</span>{badge}</div>"]
        for line in (result.get("diff") or "").split("\n"):
            esc = _html.escape(line) or "&nbsp;"
            c = line[:1]
            if line.startswith(("+++", "---")):
                color, bg = "#8b949e", "transparent"
            elif line.startswith("@@"):
                color, bg = "#58a6ff", "transparent"
            elif c == "+":
                color, bg = "#7ee2a8", "rgba(63,185,80,0.13)"
            elif c == "-":
                color, bg = "#f9928c", "rgba(248,81,73,0.13)"
            else:
                color, bg = "#8b949e", "transparent"
            rows.append(f"<div style='color:{color};background:{bg};white-space:pre-wrap'>{esc}</div>")
        return "<div style='font-family:Consolas,monospace;font-size:11px'>" + "".join(rows) + "</div>"

    @staticmethod
    def _todos_html(todos: list) -> str:
        import html as _html
        done = sum(1 for t in todos if t.get("status") == "completed")
        rows = [f"<div style='color:#c9d1d9;font-weight:600;margin-bottom:4px'>"
                f"✓ Tareas ({done}/{len(todos)})</div>"]
        for t in todos:
            st = t.get("status")
            if st == "completed":
                icon, color, deco = "✓", "#3fb950", "line-through"
            elif st == "in_progress":
                icon, color, deco = "▶", "#e3b341", "none"
            else:
                icon, color, deco = "○", "#8b949e", "none"
            rows.append(f"<div style='color:{color};text-decoration:{deco}'>"
                        f"{icon}&nbsp;&nbsp;{_html.escape(str(t.get('content','')))}</div>")
        return "<div style='font-family:Consolas,monospace;font-size:12px'>" + "".join(rows) + "</div>"

    def set_done(self, result=None):
        self._status.setText("done")
        self._status.setStyleSheet("color: #3fb950; font-size: 11px;")
        if result is not None and self._result_box:
            if isinstance(result, dict) and isinstance(result.get("diff"), str) and result["diff"].strip():
                self._result_box.setHtml(self._diff_html(result))
                self._result_box.setMaximumHeight(320)
            elif isinstance(result, dict) and isinstance(result.get("todos"), list):
                self._result_box.setHtml(self._todos_html(result["todos"]))
                self._result_box.setMaximumHeight(260)
            else:
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
        always_ask = name == "mistral_consult"

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

        if always_ask:
            note = QLabel(
                "Consulta externa: esta accion siempre se aprueba por llamada "
                "y se redacta por defecto."
            )
            note.setWordWrap(True)
            note.setStyleSheet(
                "color:#e3b341; background:rgba(227,179,65,0.10);"
                "border:1px solid rgba(227,179,65,0.24);"
                "border-radius:6px; padding:7px 9px; font-size:12px;"
            )
            lay.addWidget(note)

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
        if always_ask:
            self.btn_always.hide()
        self.btn_reject = QPushButton("Rechazar")
        self.btn_reject.setObjectName("btn_reject")
        self.btn_reject.setMinimumHeight(34)
        self.btn_reject.clicked.connect(lambda: self.rejected.emit(self.tool_id))

        btn_row.addWidget(self.btn_approve)
        btn_row.addWidget(self.btn_always)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_reject)
        lay.addLayout(btn_row)
