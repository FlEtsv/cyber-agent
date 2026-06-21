QSS = """
/* ══════════════════════════════════════════════════════
   BASE
══════════════════════════════════════════════════════ */
QMainWindow, QWidget#root {
    background-color: #080c0f;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
}

/* ══════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════ */
QWidget#sidebar {
    background-color: #0d1117;
    border-right: 1px solid #1e2d3d;
}
QLabel#logo {
    color: #00d9ff;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 16px 16px 4px;
}
QLabel#model_label {
    color: #4a5568;
    font-size: 11px;
    padding: 0 16px 12px;
}
QPushButton#btn_new_conv {
    background: transparent;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    color: #4a5568;
    padding: 8px 12px;
    text-align: left;
    margin: 4px 8px;
    font-size: 12px;
}
QPushButton#btn_new_conv:hover {
    border-color: #00d9ff;
    color: #00d9ff;
    background: rgba(0, 217, 255, 0.05);
}
QPushButton#trust_btn {
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: bold;
    margin: 4px 8px;
    text-align: left;
}
QPushButton#trust_btn[trusted="false"] {
    background: transparent;
    border: 1px solid #1e2d3d;
    color: #4a5568;
}
QPushButton#trust_btn[trusted="false"]:hover {
    border-color: #00ff88;
    color: #00ff88;
    background: rgba(0, 255, 136, 0.05);
}
QPushButton#trust_btn[trusted="true"] {
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid #00ff88;
    color: #00ff88;
}
QListWidget#conv_list {
    background: transparent;
    border: none;
    padding: 4px;
    outline: none;
}
QListWidget#conv_list::item {
    border-radius: 6px;
    padding: 8px 10px;
    margin: 1px 0;
    color: #4a5568;
    font-size: 12px;
}
QListWidget#conv_list::item:hover {
    background: rgba(30, 45, 61, 0.5);
    color: #c9d1d9;
}
QListWidget#conv_list::item:selected {
    background: rgba(0, 217, 255, 0.1);
    border: 1px solid rgba(0, 217, 255, 0.3);
    color: #00d9ff;
}
QFrame#sidebar_sep {
    color: #1e2d3d;
    margin: 4px 0;
}
QLabel#sidebar_section_hdr {
    color: #2a3a4a;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 6px 0 2px;
}
/* Permissions */
QWidget#perm_section {
    background: transparent;
}
QLabel#perm_tool_label {
    color: #4a5568;
    font-size: 11px;
    padding: 0;
}
QPushButton#perm_btn {
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 4px;
}
QPushButton#perm_btn[perm="ask"] {
    background: rgba(255, 68, 102, 0.08);
    border: 1px solid rgba(255, 68, 102, 0.3);
    color: #ff4466;
}
QPushButton#perm_btn[perm="auto"] {
    background: rgba(0, 255, 136, 0.08);
    border: 1px solid rgba(0, 255, 136, 0.3);
    color: #00ff88;
}
QPushButton#perm_btn[perm="block"] {
    background: rgba(74, 85, 104, 0.15);
    border: 1px solid #2a3a4a;
    color: #4a5568;
}
QPushButton#perm_btn:hover { opacity: 0.85; }
/* References button */
QPushButton#btn_refs {
    background: transparent;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    color: #4a5568;
    padding: 7px 12px;
    text-align: left;
    margin: 4px 8px;
    font-size: 12px;
}
QPushButton#btn_refs:hover {
    border-color: #ffd700;
    color: #ffd700;
    background: rgba(255, 215, 0, 0.05);
}
QLabel#status_bar {
    color: #1e2d3d;
    font-size: 10px;
    padding: 8px 16px;
    border-top: 1px solid #0d1117;
}

/* ══════════════════════════════════════════════════════
   TAB BAR
══════════════════════════════════════════════════════ */
QWidget#main_area { background: #080c0f; }
QWidget#tab_bar   { background: #0d1117; }
QFrame#tab_line   { color: #1e2d3d; }
QPushButton#tab_btn {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: #4a5568;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#tab_btn:hover  { color: #c9d1d9; }
QPushButton#tab_btn_active {
    background: transparent;
    border: none;
    border-bottom: 2px solid #00d9ff;
    border-radius: 0;
    color: #00d9ff;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}
QLabel#model_status {
    color: #00ff88;
    font-size: 11px;
    padding: 0 8px;
}

/* ══════════════════════════════════════════════════════
   CHAT AREA
══════════════════════════════════════════════════════ */
QWidget#chat_page  { background: #080c0f; }
QScrollArea#chat_scroll  { background: #080c0f; border: none; }
QWidget#chat_container   { background: #080c0f; }
QWidget#input_area {
    background: #0d1117;
    border-top: 1px solid #1e2d3d;
}
QTextEdit#input_box {
    background: #080c0f;
    border: 1px solid #1e2d3d;
    border-radius: 10px;
    color: #c9d1d9;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: rgba(0, 217, 255, 0.3);
}
QTextEdit#input_box:focus { border-color: rgba(0, 217, 255, 0.5); }
QPushButton#send_btn {
    background: rgba(0, 217, 255, 0.1);
    border: 1px solid rgba(0, 217, 255, 0.4);
    border-radius: 8px;
    color: #00d9ff;
    padding: 8px 16px;
    font-weight: bold;
    min-width: 70px;
}
QPushButton#send_btn:hover { background: rgba(0, 217, 255, 0.2); border-color: #00d9ff; }
QPushButton#stop_btn {
    background: rgba(255, 68, 102, 0.1);
    border: 1px solid rgba(255, 68, 102, 0.4);
    border-radius: 8px;
    color: #ff4466;
    padding: 8px 16px;
    font-weight: bold;
    min-width: 70px;
}
QPushButton#stop_btn:hover { background: rgba(255, 68, 102, 0.2); }
QLabel#tools_hint {
    color: #1e2d3d;
    font-size: 10px;
}

/* ══════════════════════════════════════════════════════
   MESSAGE BUBBLES
══════════════════════════════════════════════════════ */
QFrame#msg_user {
    background: rgba(0, 217, 255, 0.06);
    border: 1px solid rgba(0, 217, 255, 0.2);
    border-radius: 12px;
    padding: 2px;
}
QFrame#msg_assistant {
    background: #0d1117;
    border: 1px solid #1e2d3d;
    border-radius: 12px;
    padding: 2px;
}
QTextBrowser#msg_content {
    background: transparent;
    border: none;
    color: #c9d1d9;
    font-size: 13px;
    selection-background-color: rgba(0, 217, 255, 0.3);
}

/* ══════════════════════════════════════════════════════
   TOOL CARDS
══════════════════════════════════════════════════════ */
QFrame#tool_card_dangerous {
    background: #0d1117;
    border: 1px solid rgba(255, 68, 102, 0.4);
    border-radius: 8px;
    margin: 4px 0;
}
QFrame#tool_card_safe {
    background: #0d1117;
    border: 1px solid rgba(0, 217, 255, 0.3);
    border-radius: 8px;
    margin: 4px 0;
}
QFrame#tool_card_done {
    background: #0d1117;
    border: 1px solid rgba(0, 255, 136, 0.3);
    border-radius: 8px;
    margin: 4px 0;
}
QPushButton#btn_approve {
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid #00ff88;
    border-radius: 6px;
    color: #00ff88;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton#btn_approve:hover { background: rgba(0, 255, 136, 0.2); }
QPushButton#btn_reject {
    background: rgba(255, 68, 102, 0.1);
    border: 1px solid #ff4466;
    border-radius: 6px;
    color: #ff4466;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton#btn_reject:hover { background: rgba(255, 68, 102, 0.2); }
QPushButton#btn_always {
    background: transparent;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    color: #4a5568;
    padding: 6px 12px;
    font-size: 11px;
}
QPushButton#btn_always:hover { border-color: #00ff88; color: #00ff88; }

/* ══════════════════════════════════════════════════════
   TERMINAL
══════════════════════════════════════════════════════ */
QWidget#terminal_toolbar {
    background: #0d1117;
    border-bottom: 1px solid #1e2d3d;
}
QLabel#terminal_title {
    color: #00d9ff;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel#terminal_cwd {
    color: #4a5568;
    font-size: 11px;
}
QPushButton#shell_btn {
    background: transparent;
    border: 1px solid #1e2d3d;
    border-radius: 5px;
    color: #4a5568;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#shell_btn:hover   { color: #c9d1d9; border-color: #2a3a4a; }
QPushButton#shell_btn:checked {
    background: rgba(0, 217, 255, 0.1);
    border-color: rgba(0, 217, 255, 0.5);
    color: #00d9ff;
}
QPushButton#btn_terminal_action {
    background: transparent;
    border: 1px solid #1e2d3d;
    border-radius: 5px;
    color: #4a5568;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#btn_terminal_action:hover { color: #c9d1d9; border-color: #2a3a4a; }
QPushButton#btn_terminal_kill {
    background: transparent;
    border: 1px solid rgba(255, 68, 102, 0.3);
    border-radius: 5px;
    color: rgba(255, 68, 102, 0.5);
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#btn_terminal_kill:enabled {
    color: #ff4466;
    border-color: rgba(255, 68, 102, 0.6);
}
QPushButton#btn_terminal_kill:hover { background: rgba(255, 68, 102, 0.1); }
QPlainTextEdit#terminal_output {
    background: #050810;
    border: none;
    color: #c9d1d9;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    selection-background-color: rgba(0, 217, 255, 0.3);
    padding: 8px;
}
QWidget#terminal_input_bar {
    background: #0d1117;
    border-top: 1px solid #1e2d3d;
}
QLabel#terminal_prompt {
    color: #00ff88;
    font-size: 13px;
    font-weight: bold;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
QLineEdit#terminal_input_line {
    background: #080c0f;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    color: #c9d1d9;
    padding: 6px 10px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
    selection-background-color: rgba(0, 217, 255, 0.3);
}
QLineEdit#terminal_input_line:focus { border-color: rgba(0, 255, 136, 0.5); }
QPushButton#btn_terminal_run {
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid rgba(0, 255, 136, 0.4);
    border-radius: 6px;
    color: #00ff88;
    font-weight: bold;
}
QPushButton#btn_terminal_run:hover  { background: rgba(0, 255, 136, 0.2); }
QPushButton#btn_terminal_run:disabled { background: transparent; color: #1e2d3d; border-color: #1e2d3d; }

/* ══════════════════════════════════════════════════════
   REFERENCES DIALOG
══════════════════════════════════════════════════════ */
QDialog {
    background: #080c0f;
    color: #c9d1d9;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
QWidget#refs_header {
    background: #0d1117;
    border-bottom: 1px solid #1e2d3d;
}
QLabel#refs_title {
    color: #00d9ff;
    font-size: 14px;
    font-weight: bold;
}
QLineEdit#refs_search {
    background: #080c0f;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    color: #c9d1d9;
    padding: 6px 10px;
    font-size: 12px;
}
QLineEdit#refs_search:focus { border-color: rgba(0, 217, 255, 0.5); }
QTabWidget#refs_tabs::pane {
    border: none;
    background: #0d1117;
}
QTabWidget#refs_tabs > QTabBar::tab {
    background: transparent;
    color: #4a5568;
    padding: 8px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}
QTabWidget#refs_tabs > QTabBar::tab:selected {
    color: #00d9ff;
    border-bottom: 2px solid #00d9ff;
}
QTabWidget#refs_tabs > QTabBar::tab:hover { color: #c9d1d9; }
QListWidget#refs_list {
    background: #0d1117;
    border: none;
    outline: none;
    padding: 4px;
}
QListWidget#refs_list::item {
    color: #c9d1d9;
    padding: 7px 10px;
    border-radius: 5px;
    font-size: 12px;
}
QListWidget#refs_list::item:hover    { background: rgba(0, 217, 255, 0.07); }
QListWidget#refs_list::item:selected { background: rgba(0, 217, 255, 0.12); color: #00d9ff; }
QLabel#refs_detail_title {
    color: #00d9ff;
    font-size: 13px;
    font-weight: bold;
    background: #0d1117;
    border-bottom: 1px solid #1e2d3d;
    padding-bottom: 6px;
}
QLabel#refs_detail_desc {
    color: #4a5568;
    font-size: 12px;
    background: #0d1117;
}
QTextEdit#refs_detail_code {
    background: #050810;
    border: none;
    color: #00ff88;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: rgba(0, 217, 255, 0.3);
}
QWidget#refs_btn_row { background: #0d1117; border-top: 1px solid #1e2d3d; }
QPushButton#refs_btn_chat {
    background: rgba(0, 217, 255, 0.1);
    border: 1px solid rgba(0, 217, 255, 0.4);
    border-radius: 6px;
    color: #00d9ff;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#refs_btn_chat:hover { background: rgba(0, 217, 255, 0.2); }
QPushButton#refs_btn_terminal {
    background: rgba(0, 255, 136, 0.1);
    border: 1px solid rgba(0, 255, 136, 0.4);
    border-radius: 6px;
    color: #00ff88;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#refs_btn_terminal:hover { background: rgba(0, 255, 136, 0.2); }
QPushButton#refs_btn_copy {
    background: transparent;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    color: #4a5568;
    padding: 7px 14px;
    font-size: 12px;
}
QPushButton#refs_btn_copy:hover { border-color: #ffd700; color: #ffd700; }

/* ══════════════════════════════════════════════════════
   SCROLLBARS
══════════════════════════════════════════════════════ */
QScrollBar:vertical {
    background: #0d1117;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #1e2d3d;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: rgba(0, 217, 255, 0.3); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    background: #0d1117;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #1e2d3d;
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: rgba(0, 217, 255, 0.3); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""
