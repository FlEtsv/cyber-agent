import markdown, re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QFrame, QTextBrowser, QScrollArea, QSizePolicy, QSpacerItem)
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
    def __init__(self, role, content="", parent=None):
        super().__init__(parent)
        self.role = role
        self._content = content
        self._build()

    def _build(self):
        self.setObjectName("msg_user" if self.role == "user" else "msg_assistant")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

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
            lay.addStretch()
            lay.addWidget(self.content_widget)
            lay.addWidget(avatar)
        else:
            lay.addWidget(avatar)
            lay.addWidget(self.content_widget)

        if self._content:
            self.set_content(self._content)

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_cards: dict[str, ToolCard] = {}
        self._current_bubble: MessageBubble | None = None
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

    def load_messages(self, messages):
        self.clear()
        for m in messages:
            if m["role"] in ("user", "assistant"):
                self.add_message(m["role"], m["content"], streaming=False)

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

    def finish_streaming(self):
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
