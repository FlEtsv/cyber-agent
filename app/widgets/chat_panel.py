import markdown, re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QFrame, QTextBrowser, QScrollArea, QSizePolicy,
                                QSpacerItem, QPushButton)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from .tool_card import ToolCard

MD_STYLE = """
<style>
body { color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 13px; margin: 0; padding: 0; }
code { background: #080c0f; color: #00d9ff; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
pre  { background: #080c0f; border: 1px solid #1e2d3d; border-radius: 6px; padding: 10px; overflow-x: auto; margin: 6px 0; }
pre code { background: none; color: #00ff88; padding: 0; }
h1,h2 { color: #00d9ff; }
h3    { color: #00ff88; }
strong { color: #ffffff; }
a  { color: #00d9ff; }
li { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; }
th,td { border: 1px solid #1e2d3d; padding: 4px 8px; }
th { background: #0d1117; color: #00d9ff; }
blockquote { border-left: 3px solid #1e2d3d; margin: 4px 0; padding-left: 10px; color: #4a5568; }
</style>
"""

def md_to_html(text):
    html = markdown.markdown(text, extensions=["fenced_code", "tables", "nl2br"])
    return MD_STYLE + html

class MessageBubble(QFrame):
    rated = Signal(int)  # 1 = thumbs up, -1 = thumbs down

    def __init__(self, role, content="", parent=None):
        super().__init__(parent)
        self.role = role
        self._content = content
        self._message_id = None
        self._build()

    def _build(self):
        self.setObjectName("msg_user" if self.role == "user" else "msg_assistant")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        # Avatar
        avatar = QLabel("TÚ" if self.role == "user" else "AI")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background: rgba(0, 217, 255, 0.15);
            border: 1px solid rgba(0, 217, 255, 0.4);
            border-radius: 16px;
            color: #00d9ff;
            font-size: 10px;
            font-weight: bold;
        """ if self.role == "assistant" else """
            background: rgba(0, 255, 136, 0.15);
            border: 1px solid rgba(0, 255, 136, 0.4);
            border-radius: 16px;
            color: #00ff88;
            font-size: 10px;
            font-weight: bold;
        """)

        # Content
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

        # Rating bar (only for assistant)
        if self.role == "assistant":
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
                    "QPushButton { background: transparent; border: 1px solid #1e2d3d;"
                    " border-radius: 4px; color: #4a5568; font-size: 11px; }"
                    "QPushButton:hover:enabled { border-color: #00d9ff; color: #c9d1d9; }"
                    "QPushButton:disabled { color: #2a3a4a; border-color: #111; }"
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

    def _rate_up(self):
        self._emit_rating(1)

    def _rate_down(self):
        self._emit_rating(-1)

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
                "QPushButton { background: rgba(0,217,255,0.15); border: 1px solid #00d9ff;"
                " border-radius: 4px; color: #00d9ff; font-size: 11px; }"
                "QPushButton:disabled { background: rgba(0,217,255,0.15); border: 1px solid #00d9ff;"
                " border-radius: 4px; color: #00d9ff; font-size: 11px; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton:disabled { color: #2a3a4a; border: 1px solid #111;"
                " border-radius: 4px; background: transparent; font-size: 11px; }"
            )

    def set_content(self, text):
        self._content = text
        if self.role == "user":
            self.content_widget.setPlainText(text)
        else:
            self.content_widget.setHtml(md_to_html(text))
        self._adjust_height()

    def append_token(self, token):
        self._content += token
        self.content_widget.setHtml(md_to_html(self._content))
        cursor = self.content_widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.content_widget.setTextCursor(cursor)
        self._adjust_height()

    def _adjust_height(self):
        doc = self.content_widget.document()
        doc.setTextWidth(self.content_widget.viewport().width() or 600)
        h = int(doc.size().height()) + 20
        self.content_widget.setMinimumHeight(min(h, 800))
        self.content_widget.setMaximumHeight(min(h, 800))


class ChatPanel(QWidget):
    tool_approved = Signal(str, str, bool)  # tool_id, name, always
    tool_rejected = Signal(str)
    message_rated = Signal(int, int, int)   # message_id, conv_id, rating

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_cards: dict[str, ToolCard] = {}
        self._current_bubble: MessageBubble | None = None
        self._current_conv_id: int | None = None
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
        self._tool_cards.clear()
        self._current_bubble = None
        while self.inner.count() > 1:
            item = self.inner.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

    def add_message(self, role, content="", streaming=False):
        bubble = MessageBubble(role, content)
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
        if self._current_bubble and msg_id:
            self._current_bubble.set_message_id(msg_id)
            self._current_bubble.rated.connect(
                lambda r, mid=msg_id, cid=conv_id: self.message_rated.emit(mid, cid, r)
            )
        self._current_bubble = None

    def add_tool_card(self, tool_id, name, args, dangerous):
        card = ToolCard(tool_id, name, args, dangerous)
        card.approved.connect(lambda tid, tname, always: self.tool_approved.emit(tid, tname, always))
        card.rejected.connect(self.tool_rejected)
        self._tool_cards[tool_id] = card
        self.inner.insertWidget(self.inner.count() - 1, card)
        self._scroll_bottom()

    def set_tool_result(self, tool_id, result):
        if tool_id in self._tool_cards:
            self._tool_cards[tool_id].set_result(result)

    def set_tool_cancelled(self, tool_id):
        if tool_id in self._tool_cards:
            self._tool_cards[tool_id].set_cancelled()

    def _scroll_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))
