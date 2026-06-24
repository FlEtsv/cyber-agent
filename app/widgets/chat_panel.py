import markdown
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QFrame, QTextBrowser, QScrollArea, QSizePolicy,
                                QPushButton)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QTextCursor
from .tool_card import ToolActivityRow, ToolApprovalCard

MD_STYLE = """
<style>
body {
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    margin: 0;
    padding: 0;
    line-height: 1.6;
}
code {
    background: #161b22;
    color: #58a6ff;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 12px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
pre {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;
}
pre code { background: none; color: #e6edf3; padding: 0; }
h1, h2  { color: #58a6ff; margin: 8px 0 4px; }
h3      { color: #3fb950; margin: 6px 0 3px; }
strong  { color: #f0f6fc; }
a       { color: #58a6ff; }
li      { margin: 2px 0; }
table   { border-collapse: collapse; width: 100%; }
th, td  { border: 1px solid #30363d; padding: 4px 8px; }
th      { background: #161b22; color: #8b949e; }
blockquote {
    border-left: 3px solid #30363d;
    margin: 4px 0;
    padding-left: 10px;
    color: #8b949e;
}
</style>
"""


def md_to_html(text):
    html = markdown.markdown(text, extensions=["fenced_code", "tables", "nl2br"])
    return MD_STYLE + html


class MessageBubble(QFrame):
    rated         = Signal(int)
    tool_approved = Signal(str, str, bool)
    tool_rejected = Signal(str)

    def __init__(self, role, content="", parent=None):
        super().__init__(parent)
        self.role = role
        self._content = content
        self._message_id = None
        self._activity_rows: dict[str, ToolActivityRow] = {}
        self._activity_count = 0
        self._approval_card: ToolApprovalCard | None = None
        self._dirty = False
        self._render_timer = QTimer(self)
        self._render_timer.setInterval(80)
        self._render_timer.timeout.connect(self._flush_render)
        # Reasoning state — content_widget shows live steps until first real token
        self._tool_steps: dict[str, dict] = {}   # tool_id → {name, args_preview, status}
        self._tool_order: list[str] = []          # insertion order
        self._in_reasoning: bool = False
        self._build()

    def _build(self):
        self.setObjectName("msg_user" if self.role == "user" else "msg_assistant")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        avatar = QLabel("TÚ" if self.role == "user" else "AI")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        if self.role == "assistant":
            avatar.setStyleSheet(
                "background: rgba(88,166,255,0.12);"
                "border: 1px solid rgba(88,166,255,0.35);"
                "border-radius: 16px; color: #58a6ff;"
                "font-size: 10px; font-weight: bold;"
            )
        else:
            avatar.setStyleSheet(
                "background: rgba(63,185,80,0.12);"
                "border: 1px solid rgba(63,185,80,0.35);"
                "border-radius: 16px; color: #3fb950;"
                "font-size: 10px; font-weight: bold;"
            )

        # ── Avatar + content row ──────────────────────────────────────────
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.content_widget = QTextBrowser()
        self.content_widget.setObjectName("msg_content")
        self.content_widget.setOpenExternalLinks(True)
        self.content_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.content_widget.document().setDocumentMargin(8)

        if self.role == "user":
            row.addStretch()
            row.addWidget(self.content_widget)
            row.addWidget(avatar)
        else:
            row.addWidget(avatar)
            row.addWidget(self.content_widget)

        outer.addLayout(row)

        if self.role == "assistant":
            # ── Collapsible actions toggle ────────────────────────────────
            self._actions_toggle = QPushButton("▶  Acciones")
            self._actions_toggle.setObjectName("actions_toggle")
            self._actions_toggle.setCheckable(True)
            self._actions_toggle.hide()
            self._actions_toggle.clicked.connect(self._on_toggle_actions)

            toggle_wrap = QHBoxLayout()
            toggle_wrap.setContentsMargins(42, 0, 0, 0)
            toggle_wrap.addWidget(self._actions_toggle)
            toggle_wrap.addStretch()
            outer.addLayout(toggle_wrap)

            # ── Actions container ─────────────────────────────────────────
            self._actions_container = QWidget()
            self._actions_container.hide()
            self._actions_layout = QVBoxLayout(self._actions_container)
            self._actions_layout.setContentsMargins(42, 2, 0, 2)
            self._actions_layout.setSpacing(2)
            outer.addWidget(self._actions_container)

            # ── Approval card wrapper ─────────────────────────────────────
            self._approval_wrapper = QWidget()
            self._approval_wrapper.hide()
            self._approval_inner = QVBoxLayout(self._approval_wrapper)
            self._approval_inner.setContentsMargins(42, 4, 0, 4)
            self._approval_inner.setSpacing(0)
            outer.addWidget(self._approval_wrapper)

            # ── Rating bar ────────────────────────────────────────────────
            self._rating_row = QWidget()
            rlay = QHBoxLayout(self._rating_row)
            rlay.setContentsMargins(42, 0, 0, 0)
            rlay.setSpacing(4)

            self._btn_up   = QPushButton("👍")
            self._btn_down = QPushButton("👎")
            for btn in (self._btn_up, self._btn_down):
                btn.setFixedSize(28, 22)
                btn.setEnabled(False)
                btn.setStyleSheet(
                    "QPushButton { background:transparent; border:1px solid #30363d;"
                    " border-radius:4px; color:#484f58; font-size:11px; }"
                    "QPushButton:hover:enabled { border-color:#58a6ff; color:#e6edf3; }"
                    "QPushButton:disabled { color:#21262d; border-color:#21262d; }"
                )

            self._btn_up.clicked.connect(self._rate_up)
            self._btn_down.clicked.connect(self._rate_down)
            rlay.addWidget(self._btn_up)
            rlay.addWidget(self._btn_down)
            rlay.addStretch()
            outer.addWidget(self._rating_row)
        else:
            self._btn_up = self._btn_down = None

        if self._content:
            self.set_content(self._content)

    # ── Actions collapse ──────────────────────────────────────────────────

    def _on_toggle_actions(self, checked: bool):
        self._actions_container.setVisible(checked)
        self._update_toggle_text()

    def _update_toggle_text(self):
        n = self._activity_count
        checked = self._actions_toggle.isChecked()
        arrow = "▼" if checked else "▶"
        label = "acción" if n == 1 else "acciones"
        self._actions_toggle.setText(f"{arrow}  {n} {label}")

    # ── Tool activity ─────────────────────────────────────────────────────

    def add_tool_activity(self, tool_id: str, name: str, args: dict):
        if self.role != "assistant":
            return

        # Build args preview (HTML-safe)
        import html as _html, json as _json
        args_preview = ""
        if args:
            try:
                raw = _json.dumps(args, ensure_ascii=False)
                short = raw[:80] + "…" if len(raw) > 80 else raw
                args_preview = _html.escape(short)
            except Exception:
                pass

        self._tool_steps[tool_id] = {"name": name, "args_preview": args_preview, "status": "pending"}
        self._tool_order.append(tool_id)
        self._in_reasoning = True
        self._render_reasoning()

        # ── Tool card (collapsible below) ─────────────────────────────────
        row_widget = ToolActivityRow(tool_id, name, args)
        self._activity_rows[tool_id] = row_widget
        self._actions_layout.addWidget(row_widget)
        self._activity_count += 1
        self._update_toggle_text()
        self._actions_toggle.show()
        self._actions_toggle.setChecked(True)
        self._actions_container.show()

    def _render_reasoning(self):
        """Update content_widget with live tool-step progress (reasoning mode)."""
        import html as _html
        lines = []
        for tid in self._tool_order:
            step = self._tool_steps.get(tid, {})
            name = _html.escape(step.get("name", tid))
            preview = step.get("args_preview", "")
            status = step.get("status", "pending")
            if status == "done":
                lines.append(
                    f"<div style='margin:1px 0'>"
                    f"<span style='color:#3fb950'>&#10003;</span>&nbsp;"
                    f"<b style='color:#3fb950'>{name}</b>"
                    f"</div>"
                )
            elif status == "cancelled":
                lines.append(
                    f"<div style='margin:1px 0'>"
                    f"<span style='color:#f85149'>&#10007;</span>&nbsp;"
                    f"<b style='color:#f85149'>{name}</b>"
                    f"</div>"
                )
            else:
                lines.append(
                    f"<div style='margin:1px 0'>"
                    f"<span style='color:#e3b341'>&#9881;</span>&nbsp;"
                    f"<b style='color:#58a6ff'>{name}</b>"
                    + (f"&nbsp;<span style='color:#484f58;font-size:11px'>{preview}</span>" if preview else "")
                    + "</div>"
                )

        html = (
            "<div style='color:#8b949e;font-size:12px;"
            "font-family:Cascadia Code,Consolas,monospace;padding:4px 0'>"
            "<div style='color:#e3b341;font-size:12px;margin-bottom:6px'>"
            "<b>&#9881; Procesando...</b></div>"
            + "".join(lines)
            + "</div>"
        )
        self.content_widget.setHtml(MD_STYLE + html)
        self._adjust_height()

    def set_tool_done(self, tool_id: str, result=None):
        row_widget = self._activity_rows.get(tool_id)
        if row_widget:
            row_widget.set_done(result)
        if tool_id in self._tool_steps:
            self._tool_steps[tool_id]["status"] = "done"
            if self._in_reasoning:
                self._render_reasoning()

    def set_tool_cancelled(self, tool_id: str):
        row_widget = self._activity_rows.get(tool_id)
        if row_widget:
            row_widget.set_cancelled()
        if tool_id in self._tool_steps:
            self._tool_steps[tool_id]["status"] = "cancelled"
            if self._in_reasoning:
                self._render_reasoning()

    # ── Approval card ─────────────────────────────────────────────────────

    def show_approval(self, tool_id: str, name: str, args: dict, dangerous: bool):
        if self.role != "assistant":
            return
        self.hide_approval()
        card = ToolApprovalCard(tool_id, name, args, dangerous)
        card.approved.connect(self.tool_approved)
        card.rejected.connect(self.tool_rejected)
        self._approval_card = card
        self._approval_inner.addWidget(card)
        self._approval_wrapper.show()
        self._adjust_height()

    def hide_approval(self):
        if self._approval_card:
            self._approval_card.deleteLater()
            self._approval_card = None
        self._approval_wrapper.hide()
        self._adjust_height()

    # ── Rating ────────────────────────────────────────────────────────────

    def set_message_id(self, msg_id: int, existing_rating: int = None):
        self._message_id = msg_id
        if self._btn_up:
            self._btn_up.setEnabled(True)
            self._btn_down.setEnabled(True)
        if existing_rating == 1:
            self._apply_style(self._btn_up, True)
            self._apply_style(self._btn_down, False)
            self._btn_up.setEnabled(False)
            self._btn_down.setEnabled(False)
        elif existing_rating == -1:
            self._apply_style(self._btn_up, False)
            self._apply_style(self._btn_down, True)
            self._btn_up.setEnabled(False)
            self._btn_down.setEnabled(False)

    def _rate_up(self):   self._emit_rating(1)
    def _rate_down(self): self._emit_rating(-1)

    def _emit_rating(self, rating: int):
        self._btn_up.setEnabled(False)
        self._btn_down.setEnabled(False)
        self._apply_style(self._btn_up, rating == 1)
        self._apply_style(self._btn_down, rating == -1)
        self.rated.emit(rating)

    @staticmethod
    def _apply_style(btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet(
                "QPushButton { background:rgba(88,166,255,0.12); border:1px solid #58a6ff;"
                " border-radius:4px; color:#58a6ff; font-size:11px; }"
                "QPushButton:disabled { background:rgba(88,166,255,0.12); border:1px solid #58a6ff;"
                " border-radius:4px; color:#58a6ff; font-size:11px; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton:disabled { color:#21262d; border:1px solid #21262d;"
                " border-radius:4px; background:transparent; font-size:11px; }"
            )

    # ── Content ───────────────────────────────────────────────────────────

    def set_content(self, text):
        self._content = text
        if self.role == "user":
            self.content_widget.setPlainText(text)
        else:
            self.content_widget.setHtml(md_to_html(text))
        self._adjust_height()

    def append_token(self, token):
        if self._in_reasoning:
            # First real token — reasoning display disappears, real response begins
            self._in_reasoning = False
            self._content = ""
            self._render_timer.stop()
        self._content += token
        self._dirty = True
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _flush_render(self):
        try:
            if self._dirty:
                self._dirty = False
                self.content_widget.setHtml(md_to_html(self._content))
                cursor = self.content_widget.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.content_widget.setTextCursor(cursor)
                self._adjust_height()
            else:
                self._render_timer.stop()
        except RuntimeError:
            self._render_timer.stop()

    def finish_streaming_content(self):
        self._render_timer.stop()
        self._dirty = False
        self.content_widget.setHtml(md_to_html(self._content))
        self._adjust_height()

    def _adjust_height(self):
        doc = self.content_widget.document()
        doc.setTextWidth(self.content_widget.viewport().width() or 600)
        h = int(doc.size().height()) + 20
        self.content_widget.setMinimumHeight(min(h, 800))
        self.content_widget.setMaximumHeight(min(h, 800))


class ChatPanel(QWidget):
    tool_approved = Signal(str, str, bool)
    tool_rejected = Signal(str)
    message_rated = Signal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_to_bubble: dict[str, MessageBubble] = {}
        self._current_bubble: MessageBubble | None = None
        self._current_conv_id: int | None = None
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(50)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            )
        )
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("chat_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setObjectName("chat_container")
        self.inner = QVBoxLayout(self.container)
        self.inner.setContentsMargins(20, 20, 20, 20)
        self.inner.setSpacing(12)
        self.inner.addStretch()

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

    def clear(self):
        self._tool_to_bubble.clear()
        self._current_bubble = None
        while self.inner.count() > 1:
            item = self.inner.takeAt(0)
            w = item.widget() if item else None
            if w:
                if hasattr(w, "_render_timer"):
                    w._render_timer.stop()
                w.deleteLater()

    def load_messages(self, messages, conv_id: int = None):
        self.clear()
        self._current_conv_id = conv_id
        try:
            from app.finetune.collector import get_rating
            _get_rating = get_rating
        except Exception:
            _get_rating = lambda _: None
        for m in messages:
            if m["role"] in ("user", "assistant"):
                msg_id = m.get("id")
                existing = _get_rating(msg_id) if msg_id and m["role"] == "assistant" else None
                bubble = self.add_message(m["role"], m["content"], streaming=False)
                if msg_id and m["role"] == "assistant":
                    bubble.set_message_id(msg_id, existing)
                    bubble.rated.connect(
                        lambda r, mid=msg_id, cid=conv_id: self.message_rated.emit(mid, cid, r)
                    )

    def get_or_create_assistant_bubble(self) -> "MessageBubble":
        """Return existing streaming bubble (e.g. from tool activity) or create new one."""
        if self._current_bubble is not None:
            return self._current_bubble
        return self.add_message("assistant", streaming=True)

    def add_message(self, role, content="", streaming=False) -> MessageBubble:
        bubble = MessageBubble(role, content)
        if role == "assistant":
            bubble.tool_approved.connect(self.tool_approved)
            bubble.tool_rejected.connect(self.tool_rejected)
        self.inner.insertWidget(self.inner.count() - 1, bubble)
        if streaming and role == "assistant":
            self._current_bubble = bubble
        self._scroll_bottom()
        return bubble

    def append_token(self, token):
        if self._current_bubble:
            self._current_bubble.append_token(token)
            self._scroll_bottom()

    def finish_streaming(self, msg_id: int = None, conv_id: int = None):
        if self._current_bubble:
            self._current_bubble.finish_streaming_content()
            if msg_id:
                self._current_bubble.set_message_id(msg_id)
                self._current_bubble.rated.connect(
                    lambda r, mid=msg_id, cid=conv_id: self.message_rated.emit(mid, cid, r)
                )
        self._current_bubble = None

    # ── Tool activity (primary API) ───────────────────────────────────────

    def add_tool_activity(self, tool_id: str, name: str, args: dict, dangerous: bool):
        bubble = self._current_bubble
        if bubble is None:
            bubble = self.add_message("assistant", streaming=True)
        self._tool_to_bubble[tool_id] = bubble
        bubble.add_tool_activity(tool_id, name, args)
        self._scroll_bottom()

    def show_approval(self, tool_id: str, name: str, args: dict, dangerous: bool):
        bubble = self._tool_to_bubble.get(tool_id)
        if bubble:
            bubble.show_approval(tool_id, name, args, dangerous)
            self._scroll_bottom()

    def hide_approval(self, tool_id: str):
        bubble = self._tool_to_bubble.get(tool_id)
        if bubble:
            bubble.hide_approval()

    def set_tool_result(self, tool_id: str, result):
        bubble = self._tool_to_bubble.get(tool_id)
        if bubble:
            bubble.set_tool_done(tool_id, result)

    def set_tool_cancelled(self, tool_id: str):
        bubble = self._tool_to_bubble.get(tool_id)
        if bubble:
            bubble.hide_approval()
            bubble.set_tool_cancelled(tool_id)

    def _scroll_bottom(self):
        if not self._scroll_timer.isActive():
            self._scroll_timer.start()
