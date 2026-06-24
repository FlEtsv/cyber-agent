QSS = """
/* ══════════════════════════════════════════════════════
   BASE — GitHub dark palette, professional
══════════════════════════════════════════════════════ */
QMainWindow, QWidget#root {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

/* ══════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════ */
QWidget#sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}
QLabel#logo {
    color: #58a6ff;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 18px 16px 8px;
}
QLabel#model_badge {
    background: rgba(88, 166, 255, 0.08);
    border: 1px solid rgba(88, 166, 255, 0.22);
    border-radius: 6px;
    color: #c9d1d9;
    font-size: 11px;
    font-weight: 600;
    padding: 8px 10px;
    margin: 2px 8px 10px;
}
QComboBox#model_combo {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 5px;
    color: #8b949e;
    font-size: 11px;
    padding: 4px 8px;
    margin: 2px 8px 8px;
}
QComboBox#model_combo:hover {
    border-color: #58a6ff;
    color: #58a6ff;
}
QComboBox#model_combo::drop-down {
    border: none;
    width: 16px;
}
QComboBox QAbstractItemView {
    background: #161b22;
    border: 1px solid #30363d;
    color: #c9d1d9;
    selection-background-color: #21262d;
    selection-color: #58a6ff;
    font-size: 11px;
}
QPushButton#btn_new_conv {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #8b949e;
    padding: 8px 12px;
    text-align: left;
    margin: 4px 8px;
    font-size: 12px;
}
QPushButton#btn_new_conv:hover {
    border-color: #58a6ff;
    color: #58a6ff;
    background: rgba(88, 166, 255, 0.06);
}
QPushButton#trust_btn {
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 600;
    margin: 4px 8px;
    text-align: left;
}
QPushButton#trust_btn[trusted="false"] {
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
}
QPushButton#trust_btn[trusted="false"]:hover {
    border-color: #3fb950;
    color: #3fb950;
    background: rgba(63, 185, 80, 0.06);
}
QPushButton#trust_btn[trusted="true"] {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid #3fb950;
    color: #3fb950;
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
    color: #8b949e;
    font-size: 12px;
}
QListWidget#conv_list::item:hover {
    background: rgba(48, 54, 61, 0.5);
    color: #e6edf3;
}
QListWidget#conv_list::item:selected {
    background: rgba(88, 166, 255, 0.1);
    border: 1px solid rgba(88, 166, 255, 0.25);
    color: #58a6ff;
}
QFrame#sidebar_sep {
    color: #30363d;
    margin: 4px 0;
}
QLabel#sidebar_section_hdr {
    color: #484f58;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 6px 0 2px;
}
/* Permissions scroll */
QScrollArea#perm_scroll {
    background: transparent;
    border: none;
}
QScrollArea#perm_scroll > QWidget > QWidget { background: transparent; }
QScrollArea#perm_scroll QScrollBar:vertical {
    background: #0d1117;
    width: 4px;
    border-radius: 2px;
}
QScrollArea#perm_scroll QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 2px;
    min-height: 20px;
}
QScrollArea#perm_scroll QScrollBar::add-line:vertical,
QScrollArea#perm_scroll QScrollBar::sub-line:vertical { height: 0; }
/* Permissions */
QWidget#perm_section { background: transparent; }
QLabel#perm_tool_label {
    color: #8b949e;
    font-size: 11px;
    padding: 0;
}
QPushButton#perm_btn {
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 4px;
}
QPushButton#perm_btn[perm="ask"] {
    background: rgba(248, 81, 73, 0.08);
    border: 1px solid rgba(248, 81, 73, 0.3);
    color: #f85149;
}
QPushButton#perm_btn[perm="auto"] {
    background: rgba(63, 185, 80, 0.08);
    border: 1px solid rgba(63, 185, 80, 0.3);
    color: #3fb950;
}
QPushButton#perm_btn[perm="block"] {
    background: rgba(72, 79, 88, 0.15);
    border: 1px solid #30363d;
    color: #484f58;
}
/* Sidebar buttons */
QPushButton#btn_refs {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #8b949e;
    padding: 7px 12px;
    text-align: left;
    margin: 4px 8px;
    font-size: 12px;
}
QPushButton#btn_refs:hover {
    border-color: #e3b341;
    color: #e3b341;
    background: rgba(227, 179, 65, 0.06);
}
QPushButton#btn_free_vram {
    background: rgba(0, 217, 255, 0.07);
    border: 1px solid #00d9ff;
    border-radius: 6px;
    color: #00d9ff;
    padding: 5px 10px;
    text-align: left;
    margin: 4px 8px;
    font-size: 12px;
}
QPushButton#btn_free_vram:hover {
    background: rgba(0, 217, 255, 0.18);
}
QLabel#status_bar {
    color: #484f58;
    font-size: 10px;
    padding: 8px 16px;
    border-top: 1px solid #21262d;
}

/* ══════════════════════════════════════════════════════
   TAB BAR
══════════════════════════════════════════════════════ */
QWidget#main_area { background: #0d1117; }
QWidget#tab_bar   { background: #161b22; }
QFrame#tab_line   { color: #30363d; }
QPushButton#tab_btn {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: #8b949e;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#tab_btn:hover  { color: #e6edf3; }
QPushButton#tab_btn_active {
    background: transparent;
    border: none;
    border-bottom: 2px solid #58a6ff;
    border-radius: 0;
    color: #58a6ff;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}
QLabel#model_status {
    background: rgba(63, 185, 80, 0.08);
    border: 1px solid rgba(63, 185, 80, 0.18);
    border-radius: 10px;
    color: #7ee787;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
}

/* ══════════════════════════════════════════════════════
   CHAT AREA
══════════════════════════════════════════════════════ */
QWidget#chat_page       { background: #0d1117; }
QScrollArea#chat_scroll { background: #0d1117; border: none; }
QWidget#chat_container  { background: #0d1117; }
QWidget#input_area {
    background: #111820;
    border-top: 1px solid #30363d;
}
QTextEdit#input_box {
    background: #0b1118;
    border: 1px solid #3a424d;
    border-radius: 8px;
    color: #e6edf3;
    padding: 11px 14px;
    font-size: 13px;
    selection-background-color: rgba(88, 166, 255, 0.25);
}
QTextEdit#input_box:focus {
    border-color: #58a6ff;
    background: #0d1117;
}
QPushButton#send_btn {
    background: rgba(88, 166, 255, 0.14);
    border: 1px solid rgba(88, 166, 255, 0.45);
    border-radius: 6px;
    color: #58a6ff;
    padding: 8px 16px;
    font-weight: 600;
    min-width: 70px;
}
QPushButton#send_btn:hover {
    background: rgba(88, 166, 255, 0.22);
    border-color: #79c0ff;
    color: #79c0ff;
}
QPushButton#stop_btn {
    background: rgba(248, 81, 73, 0.1);
    border: 1px solid rgba(248, 81, 73, 0.4);
    border-radius: 6px;
    color: #f85149;
    padding: 8px 16px;
    font-weight: 600;
    min-width: 70px;
}
QPushButton#stop_btn:hover { background: rgba(248, 81, 73, 0.18); }
QLabel#tools_hint {
    color: #30363d;
    font-size: 10px;
}

/* ══════════════════════════════════════════════════════
   MESSAGE BUBBLES
══════════════════════════════════════════════════════ */
QFrame#msg_user {
    background: rgba(88, 166, 255, 0.05);
    border: 1px solid rgba(88, 166, 255, 0.15);
    border-radius: 10px;
    padding: 2px;
}
QFrame#msg_assistant {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 2px;
}
QTextBrowser#msg_content {
    background: transparent;
    border: none;
    color: #e6edf3;
    font-size: 13px;
    selection-background-color: rgba(88, 166, 255, 0.25);
}

/* ══════════════════════════════════════════════════════
   ACTIONS TOGGLE (collapsible)
══════════════════════════════════════════════════════ */
QPushButton#actions_toggle {
    background: transparent;
    border: none;
    color: #8b949e;
    font-size: 11px;
    text-align: left;
    padding: 2px 4px;
}
QPushButton#actions_toggle:hover { color: #e6edf3; }
QPushButton#actions_toggle:checked { color: #58a6ff; }

QFrame#tool_activity_row {
    background: rgba(13, 17, 23, 0.70);
    border: 1px solid #30363d;
    border-radius: 6px;
    margin: 3px 0;
}
QTextEdit#tool_trace_box {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 5px;
    color: #c9d1d9;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
    padding: 6px;
}

/* ══════════════════════════════════════════════════════
   APPROVAL CARDS
══════════════════════════════════════════════════════ */
QFrame#approval_card_safe {
    background: #161b22;
    border: 1px solid rgba(88, 166, 255, 0.4);
    border-radius: 8px;
    margin: 2px 0;
}
QFrame#approval_card_dangerous {
    background: #161b22;
    border: 1px solid rgba(248, 81, 73, 0.5);
    border-radius: 8px;
    margin: 2px 0;
}
QTextEdit#approval_args_box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 8px;
}

/* ══════════════════════════════════════════════════════
   APPROVAL BUTTONS
══════════════════════════════════════════════════════ */
QPushButton#btn_approve {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.5);
    border-radius: 6px;
    color: #3fb950;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton#btn_approve:hover { background: rgba(63, 185, 80, 0.2); }
QPushButton#btn_reject {
    background: rgba(248, 81, 73, 0.1);
    border: 1px solid rgba(248, 81, 73, 0.5);
    border-radius: 6px;
    color: #f85149;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton#btn_reject:hover { background: rgba(248, 81, 73, 0.2); }
QPushButton#btn_always {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #8b949e;
    padding: 6px 12px;
    font-size: 11px;
}
QPushButton#btn_always:hover { border-color: #58a6ff; color: #58a6ff; }

/* ══════════════════════════════════════════════════════
   TERMINAL
══════════════════════════════════════════════════════ */
QWidget#terminal_toolbar {
    background: #161b22;
    border-bottom: 1px solid #30363d;
}
QLabel#terminal_title {
    color: #58a6ff;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel#terminal_cwd { color: #8b949e; font-size: 11px; }
QPushButton#shell_btn {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 5px;
    color: #8b949e;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#shell_btn:hover   { color: #e6edf3; border-color: #484f58; }
QPushButton#shell_btn:checked {
    background: rgba(88, 166, 255, 0.1);
    border-color: rgba(88, 166, 255, 0.4);
    color: #58a6ff;
}
QPushButton#btn_terminal_action {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 5px;
    color: #8b949e;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#btn_terminal_action:hover { color: #e6edf3; border-color: #484f58; }
QPushButton#btn_terminal_kill {
    background: transparent;
    border: 1px solid rgba(248, 81, 73, 0.3);
    border-radius: 5px;
    color: rgba(248, 81, 73, 0.5);
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#btn_terminal_kill:enabled {
    color: #f85149;
    border-color: rgba(248, 81, 73, 0.6);
}
QPushButton#btn_terminal_kill:hover { background: rgba(248, 81, 73, 0.1); }
QPlainTextEdit#terminal_output {
    background: #0d1117;
    border: none;
    color: #e6edf3;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    selection-background-color: rgba(88, 166, 255, 0.25);
    padding: 8px;
}
QWidget#terminal_input_bar {
    background: #161b22;
    border-top: 1px solid #30363d;
}
QLabel#terminal_prompt {
    color: #3fb950;
    font-size: 13px;
    font-weight: bold;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
QLineEdit#terminal_input_line {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #e6edf3;
    padding: 6px 10px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
    selection-background-color: rgba(88, 166, 255, 0.25);
}
QLineEdit#terminal_input_line:focus { border-color: #3fb950; }
QPushButton#btn_terminal_run {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.4);
    border-radius: 6px;
    color: #3fb950;
    font-weight: 600;
}
QPushButton#btn_terminal_run:hover     { background: rgba(63, 185, 80, 0.2); }
QPushButton#btn_terminal_run:disabled  { background:transparent; color:#30363d; border-color:#30363d; }

/* ══════════════════════════════════════════════════════
   REFERENCES DIALOG
══════════════════════════════════════════════════════ */
QDialog {
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, sans-serif;
}
QWidget#refs_header {
    background: #161b22;
    border-bottom: 1px solid #30363d;
}
QLabel#refs_title { color: #58a6ff; font-size: 14px; font-weight: 600; }
QLineEdit#refs_search {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #e6edf3;
    padding: 6px 10px;
    font-size: 12px;
}
QLineEdit#refs_search:focus { border-color: rgba(88, 166, 255, 0.5); }
QTabWidget#refs_tabs::pane { border: none; background: #161b22; }
QTabWidget#refs_tabs > QTabBar::tab {
    background: transparent;
    color: #8b949e;
    padding: 8px 14px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}
QTabWidget#refs_tabs > QTabBar::tab:selected {
    color: #58a6ff;
    border-bottom: 2px solid #58a6ff;
}
QTabWidget#refs_tabs > QTabBar::tab:hover { color: #e6edf3; }
QListWidget#refs_list {
    background: #161b22;
    border: none;
    outline: none;
    padding: 4px;
}
QListWidget#refs_list::item {
    color: #e6edf3;
    padding: 7px 10px;
    border-radius: 5px;
    font-size: 12px;
}
QListWidget#refs_list::item:hover    { background: rgba(88, 166, 255, 0.06); }
QListWidget#refs_list::item:selected { background: rgba(88, 166, 255, 0.12); color: #58a6ff; }
QLabel#refs_detail_title {
    color: #58a6ff;
    font-size: 13px;
    font-weight: 600;
    background: #161b22;
    border-bottom: 1px solid #30363d;
    padding-bottom: 6px;
}
QLabel#refs_detail_desc { color: #8b949e; font-size: 12px; background: #161b22; }
QTextEdit#refs_detail_code {
    background: #0d1117;
    border: none;
    color: #3fb950;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: rgba(88, 166, 255, 0.25);
}
QWidget#refs_btn_row { background: #161b22; border-top: 1px solid #30363d; }
QPushButton#refs_btn_chat {
    background: rgba(88, 166, 255, 0.1);
    border: 1px solid rgba(88, 166, 255, 0.4);
    border-radius: 6px;
    color: #58a6ff;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#refs_btn_chat:hover { background: rgba(88, 166, 255, 0.2); }
QPushButton#refs_btn_terminal {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.4);
    border-radius: 6px;
    color: #3fb950;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#refs_btn_terminal:hover { background: rgba(63, 185, 80, 0.2); }
QPushButton#refs_btn_copy {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #8b949e;
    padding: 7px 14px;
    font-size: 12px;
}
QPushButton#refs_btn_copy:hover { border-color: #e3b341; color: #e3b341; }

/* ══════════════════════════════════════════════════════
   SCROLLBARS
══════════════════════════════════════════════════════ */
QScrollBar:vertical {
    background: #161b22;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: rgba(88, 166, 255, 0.4); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    background: #161b22;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: rgba(88, 166, 255, 0.4); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""
