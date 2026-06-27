from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSizePolicy, QStackedWidget,
    QFrame, QComboBox, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from .chat_panel import ChatPanel
from .terminal_panel import TerminalPanel
from .references_panel import ReferencesDialog
from .agent_panel import AgentPanel
from .tools_panel import ToolsPanel
from .finetune_dialog import FineTuneDialog
from .update_dialog import UpdateDialog
from .mobile_dialog import MobileSubscribeDialog
from app.ollama_client import AgentWorker, OLLAMA_MODEL, SYSTEM_PROMPT
from app.consciousness.system_context import build_system_prompt, get_personality_labels
from app.consciousness import decision_log
from app.finetune import collector
from app.api import alert_sender
from app.api.approval_poller import ApprovalPoller
from app import database as db
from app import autostart

# ── Default permission levels per tool ────────────────────────────────────
DEFAULT_PERMISSIONS = {
    # — Core (siempre auto) —
    "shell":                "auto",
    "write_file":           "auto",
    "run_python":           "auto",
    "read_file":            "auto",
    "list_directory":       "auto",
    "web_fetch":            "auto",
    "http_request":         "auto",
    "search_files":         "auto",
    "grep_files":           "auto",
    # — Sistema (read-only, auto) —
    "list_processes":       "auto",
    "system_info":          "auto",
    "memory_info":          "auto",
    "gpu_info":             "auto",
    "network_info":         "auto",
    "env_vars":             "auto",
    "process_tree":         "auto",
    "process_info":         "auto",
    "arp_cache":            "auto",
    # — Herramientas de análisis (auto) —
    "hash_file":            "auto",
    "diff_files":           "auto",
    "encode_decode":        "auto",
    "strings_extract":      "auto",
    "hex_dump":             "auto",
    "file_entropy":         "auto",
    "pe_info":              "auto",
    "file_metadata":        "auto",
    # — Auditoría web/red (auto) —
    "web_search":           "auto",
    "ssl_info":             "auto",
    "http_headers_check":   "auto",
    "web_crawl":            "auto",
    "dns_lookup":           "auto",
    "whois_lookup":         "auto",
    "traceroute":           "auto",
    "banner_grab":          "auto",
    "ping_sweep":           "auto",
    "port_scan":            "auto",
    # — RAG / aprendizaje —
    "rag_search":           "auto",
    "rag_add":              "auto",
    # — Auditoría Windows (auto, read-only) —
    "registry_query":       "auto",
    "list_services":        "auto",
    "check_persistence":    "auto",
    "network_connections":  "auto",
    "dir_bruteforce":       "auto",
    # — Requieren confirmación —
    "install_package":      "ask",
    "uninstall_package":    "ask",
    "kill_process":         "ask",
    "clipboard_write":      "ask",
    "windows_notify":       "ask",
    # — Siempre auto (misc) —
    "screenshot_pc":        "auto",
    "clipboard_read":       "auto",
    "open_browser":         "auto",
    # — Auto-conciencia y auto-modificación —
    "list_self_files":      "auto",
    "syntax_check":         "auto",
    "restart_self":         "ask",   # reiniciar pide confirmación por seguridad
    "mistral_consult":      "ask",   # envia contexto a nube; siempre supervisado
}

PERM_LABELS = {"ask": "🔴 Pedir", "auto": "🟢 Auto", "block": "⛔ Bloquear"}
PERM_CYCLE  = ["ask", "auto", "block"]

TOOL_ICONS = {
    "shell":             "⚡",
    "write_file":        "✏️",
    "run_python":        "🐍",
    "install_package":   "📦",
    "uninstall_package": "🗑️",
    "read_file":         "📄",
    "list_directory":    "📁",
    "web_fetch":         "🌐",
    "list_processes":    "⚙️",
    "system_info":       "💻",
    "mistral_consult":   "AI",
}


class MainWindow(QMainWindow):
    notification_pending = Signal(bool)  # True = hay aprobación pendiente

    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ CyberAgent")
        self.setMinimumSize(1100, 700)
        self.resize(1340, 820)

        self.active_conv  = None
        self.worker: AgentWorker | None = None
        self.trusted_tools: set[str]    = set()
        self.session_trust              = False
        self._streaming                 = False
        self._response_bubble           = None
        self._current_response          = ""

        self.tool_permissions: dict[str, str] = dict(DEFAULT_PERMISSIONS)
        self._perm_btns: dict[str, QPushButton] = {}

        self._refs_dialog: ReferencesDialog | None = None
        self._ft_dialog: FineTuneDialog | None = None
        self._update_dialog: UpdateDialog | None = None
        self._mobile_dialog: MobileSubscribeDialog | None = None
        self._pending_tools: dict[str, dict] = {}  # tool_id -> {name, args}
        self._update_local: str = ""
        self._update_remote: str = ""
        self._approval_pollers: dict[str, ApprovalPoller] = {}
        self._threat_detectors: list = []
        self.selected_model: str = OLLAMA_MODEL
        self.agent_persona: str = "general"

        self._build_ui()
        self._load_conversations()

    # ════════════════════════════════════════════════════════════════════
    # UI BUILDING
    # ════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root_lay = QHBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        root_lay.addWidget(self._build_sidebar())
        root_lay.addWidget(self._build_main_area(), 1)

    def _on_model_changed(self, index: int):
        self.selected_model = self._model_ids[index]
        if hasattr(self, "model_status"):
            self.model_status.setText(f"● {self.selected_model} listo")

    # ── Sidebar ───────────────────────────────────────────────────────

    def _on_persona_changed(self, index: int):
        self.agent_persona = self._persona_ids[index]
        if hasattr(self, "workspace_state"):
            self.workspace_state.setText(f"Perfil: {self.persona_combo.currentText()}")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(258)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Logo
        logo = QLabel("⚡ CYBER AGENT")
        logo.setObjectName("logo")
        lay.addWidget(logo)

        self._model_ids = [OLLAMA_MODEL]
        self.model_badge = QLabel(f"  Modelo activo\n  {OLLAMA_MODEL}")
        self.model_badge.setObjectName("model_badge")
        lay.addWidget(self.model_badge)

        persona_lbl = QLabel("  PERFIL")
        persona_lbl.setObjectName("sidebar_section_hdr")
        lay.addWidget(persona_lbl)

        self._persona_ids = []
        self.persona_combo = QComboBox()
        self.persona_combo.setObjectName("persona_combo")
        for profile_id, label in get_personality_labels():
            self._persona_ids.append(profile_id)
            self.persona_combo.addItem(label)
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        lay.addWidget(self.persona_combo)

        # Trust toggle
        self.trust_btn = QPushButton("🛡  Supervisado")
        self.trust_btn.setObjectName("trust_btn")
        self.trust_btn.setProperty("trusted", "false")
        self.trust_btn.setCheckable(True)
        self.trust_btn.clicked.connect(self._toggle_trust)
        lay.addWidget(self.trust_btn)

        # New conversation
        new_btn = QPushButton("＋  Nueva conversación")
        new_btn.setObjectName("btn_new_conv")
        new_btn.clicked.connect(self._new_conversation)
        lay.addWidget(new_btn)

        # Conversation list
        self.conv_list = QListWidget()
        self.conv_list.setObjectName("conv_list")
        self.conv_list.currentRowChanged.connect(self._on_conv_selected)
        lay.addWidget(self.conv_list, 1)

        # ── Permissions section ────────────────────────────────────────
        sep1 = self._separator()
        lay.addWidget(sep1)

        perm_hdr = QLabel("  PERMISOS")
        perm_hdr.setObjectName("sidebar_section_hdr")
        lay.addWidget(perm_hdr)

        perm_widget = QWidget()
        perm_widget.setObjectName("perm_section")
        perm_lay = QVBoxLayout(perm_widget)
        perm_lay.setContentsMargins(8, 4, 8, 4)
        perm_lay.setSpacing(3)

        for tool_name, default_perm in DEFAULT_PERMISSIONS.items():
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(2, 0, 2, 0)
            row_lay.setSpacing(4)

            icon = TOOL_ICONS.get(tool_name, "🔧")
            lbl  = QLabel(f"{icon} {tool_name}")
            lbl.setObjectName("perm_tool_label")
            lbl.setToolTip(tool_name)
            row_lay.addWidget(lbl, 1)

            btn = QPushButton(PERM_LABELS[default_perm])
            btn.setObjectName("perm_btn")
            btn.setProperty("perm", default_perm)
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda _, t=tool_name: self._cycle_permission(t))
            self._perm_btns[tool_name] = btn
            row_lay.addWidget(btn)

            perm_lay.addWidget(row)

        perm_scroll = QScrollArea()
        perm_scroll.setObjectName("perm_scroll")
        perm_scroll.setWidget(perm_widget)
        perm_scroll.setWidgetResizable(True)
        perm_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        perm_scroll.setFrameShape(QFrame.NoFrame)
        lay.addWidget(perm_scroll, 1)

        # ── Bottom buttons ─────────────────────────────────────────────
        sep2 = self._separator()
        lay.addWidget(sep2)

        refs_btn = QPushButton("📚  Referencias")
        refs_btn.setObjectName("btn_refs")
        refs_btn.clicked.connect(self._open_references)
        lay.addWidget(refs_btn)

        export_btn = QPushButton("📤  Exportar dataset")
        export_btn.setObjectName("btn_refs")
        export_btn.clicked.connect(self._export_finetune)
        lay.addWidget(export_btn)

        ft_btn = QPushButton("🎓  Fine-tuning QLoRA")
        ft_btn.setObjectName("btn_refs")
        ft_btn.clicked.connect(self._open_finetune)
        lay.addWidget(ft_btn)

        lay.addWidget(self._separator())

        # ── Automatización ────────────────────────────────────────────
        mobile_btn = QPushButton("📱  Activar móvil (QR)")
        mobile_btn.setObjectName("btn_refs")
        mobile_btn.clicked.connect(self._open_mobile_dialog)
        lay.addWidget(mobile_btn)

        self.autostart_btn = QPushButton()
        self.autostart_btn.setObjectName("btn_refs")
        self._refresh_autostart_btn()
        self.autostart_btn.clicked.connect(self._toggle_autostart)
        lay.addWidget(self.autostart_btn)

        nssm_btn = QPushButton("⚙️  Instalar servicio Win")
        nssm_btn.setObjectName("btn_refs")
        nssm_btn.setToolTip("Instala CyberAgent como servicio Windows via NSSM (requiere Admin)")
        nssm_btn.clicked.connect(self._install_nssm_service)
        lay.addWidget(nssm_btn)

        vram_btn = QPushButton("🎮  Liberar VRAM")
        vram_btn.setObjectName("btn_free_vram")
        vram_btn.setToolTip("Descarga el modelo de VRAM para liberar GPU (úsalo antes de jugar)")
        vram_btn.clicked.connect(self._free_vram)
        lay.addWidget(vram_btn)

        self.status_lbl = QLabel("● daemon activo · localhost:11434")
        self.status_lbl.setObjectName("status_bar")
        self.status_lbl.setCursor(Qt.PointingHandCursor)
        self.status_lbl.mousePressEvent = self._on_status_click
        lay.addWidget(self.status_lbl)

        return sidebar

    # ── Main area (Chat + Terminal tabs) ──────────────────────────────

    def _build_main_area(self) -> QWidget:
        container = QWidget()
        container.setObjectName("main_area")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QWidget()
        header.setObjectName("workspace_header")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(18, 14, 18, 12)
        hlay.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)

        self.workspace_title = QLabel("CyberAgent Console")
        self.workspace_title.setObjectName("workspace_title")
        self.workspace_subtitle = QLabel("Chat, terminal y memoria operativa en una sola vista")
        self.workspace_subtitle.setObjectName("workspace_subtitle")
        title_box.addWidget(self.workspace_title)
        title_box.addWidget(self.workspace_subtitle)

        hlay.addLayout(title_box, 1)

        self.workspace_route = QLabel("Vista: Chat")
        self.workspace_route.setObjectName("workspace_pill")
        hlay.addWidget(self.workspace_route)

        self.workspace_state = QLabel("Sistema listo")
        self.workspace_state.setObjectName("workspace_pill_accent")
        hlay.addWidget(self.workspace_state)

        lay.addWidget(header)

        # Tab bar
        tab_bar = QWidget()
        tab_bar.setObjectName("tab_bar")
        tlay = QHBoxLayout(tab_bar)
        tlay.setContentsMargins(18, 0, 18, 0)
        tlay.setSpacing(8)

        self.tab_chat = QPushButton("💬  Chat")
        self.tab_chat.setObjectName("tab_btn_active")
        self.tab_chat.setCheckable(True)
        self.tab_chat.setChecked(True)
        self.tab_chat.clicked.connect(lambda: self._switch_tab(0))

        self.tab_terminal = QPushButton("⚡  Terminal")
        self.tab_terminal.setObjectName("tab_btn")
        self.tab_terminal.setCheckable(True)
        self.tab_terminal.setChecked(False)
        self.tab_terminal.clicked.connect(lambda: self._switch_tab(1))

        self.tab_agent = QPushButton("🧠  Agente")
        self.tab_agent.setObjectName("tab_btn")
        self.tab_agent.setCheckable(True)
        self.tab_agent.setChecked(False)
        self.tab_agent.clicked.connect(lambda: self._switch_tab(2))

        self.tab_tools = QPushButton("Herramientas")
        self.tab_tools.setObjectName("tab_btn")
        self.tab_tools.setCheckable(True)
        self.tab_tools.setChecked(False)
        self.tab_tools.clicked.connect(lambda: self._switch_tab(3))

        tlay.addWidget(self.tab_chat)
        tlay.addWidget(self.tab_terminal)
        tlay.addWidget(self.tab_agent)
        tlay.addWidget(self.tab_tools)
        tlay.addStretch()

        self.model_status = QLabel("● modelo listo")
        self.model_status.setObjectName("model_status")
        tlay.addWidget(self.model_status)

        lay.addWidget(tab_bar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("tab_line")
        lay.addWidget(line)

        # Stacked pages
        self.stack = QStackedWidget()

        # Page 0: Chat
        self.stack.addWidget(self._build_chat_page())

        # Page 1: Terminal
        self.terminal = TerminalPanel()
        self.stack.addWidget(self.terminal)

        # Page 2: Agent panel (RAG + Decision Log)
        self.agent_panel = AgentPanel()
        self.stack.addWidget(self.agent_panel)

        # Page 3: Tools catalog
        self.tools_panel = ToolsPanel()
        self.stack.addWidget(self.tools_panel)

        lay.addWidget(self.stack, 1)
        return container

    def _build_chat_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("chat_page")
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.chat = ChatPanel()
        self.chat.tool_approved.connect(self._on_tool_approved)
        self.chat.tool_rejected.connect(self._on_tool_rejected)
        self.chat.message_rated.connect(self._on_message_rated)
        lay.addWidget(self.chat, 1)

        # Input bar
        input_area = QWidget()
        input_area.setObjectName("input_area")
        ilay = QVBoxLayout(input_area)
        ilay.setContentsMargins(16, 12, 16, 12)
        ilay.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.input_box = QTextEdit()
        self.input_box.setObjectName("input_box")
        self.input_box.setPlaceholderText(
            "Mensaje al agente... (Enter envía · Shift+Enter nueva línea)"
        )
        self.input_box.setMinimumHeight(44)
        self.input_box.setMaximumHeight(160)
        self.input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.input_box.installEventFilter(self)

        self.send_btn = QPushButton("Enviar →")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedHeight(44)
        self.send_btn.clicked.connect(self._send)

        self.stop_btn = QPushButton("■ Parar")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedHeight(44)
        self.stop_btn.hide()
        self.stop_btn.clicked.connect(self._stop)

        row.addWidget(self.input_box)
        row.addWidget(self.send_btn)
        row.addWidget(self.stop_btn)
        ilay.addLayout(row)

        self.tools_hint = QLabel(
            "shell · write · python · install · web · read · processes · system_info"
        )
        self.tools_hint.setObjectName("tools_hint")
        ilay.addWidget(self.tools_hint)

        lay.addWidget(input_area)
        return page

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("sidebar_sep")
        return sep

    # ════════════════════════════════════════════════════════════════════
    # TAB SWITCHING
    # ════════════════════════════════════════════════════════════════════

    def _switch_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.tab_chat.setChecked(idx == 0)
        self.tab_terminal.setChecked(idx == 1)
        self.tab_agent.setChecked(idx == 2)
        self.tab_tools.setChecked(idx == 3)
        tabs = [self.tab_chat, self.tab_terminal, self.tab_agent, self.tab_tools]
        for i, btn in enumerate(tabs):
            btn.setObjectName("tab_btn_active" if i == idx else "tab_btn")
            btn.setStyle(btn.style())
        if idx == 2:
            self.agent_panel.refresh_log()
        if hasattr(self, "workspace_route"):
            routes = ["Vista: Chat", "Vista: Terminal", "Vista: Agente", "Vista: Herramientas"]
            self.workspace_route.setText(routes[idx])

    # ════════════════════════════════════════════════════════════════════
    # PERMISSIONS
    # ════════════════════════════════════════════════════════════════════

    def _cycle_permission(self, tool_name: str):
        current = self.tool_permissions.get(tool_name, "ask")
        idx     = PERM_CYCLE.index(current)
        new_perm = PERM_CYCLE[(idx + 1) % len(PERM_CYCLE)]
        self.tool_permissions[tool_name] = new_perm
        btn = self._perm_btns.get(tool_name)
        if btn:
            btn.setText(PERM_LABELS[new_perm])
            btn.setProperty("perm", new_perm)
            btn.setStyle(btn.style())

    # ════════════════════════════════════════════════════════════════════
    # REFERENCES
    # ════════════════════════════════════════════════════════════════════

    def _open_references(self):
        if self._refs_dialog is None:
            self._refs_dialog = ReferencesDialog(self)
            self._refs_dialog.insert_to_chat.connect(self._insert_to_chat)
            self._refs_dialog.insert_to_terminal.connect(self._insert_to_terminal)
        self._refs_dialog.show()
        self._refs_dialog.raise_()
        self._refs_dialog.activateWindow()

    def _insert_to_chat(self, text: str):
        self._switch_tab(0)
        self.input_box.setPlainText(text)
        self.input_box.setFocus()

    def _insert_to_terminal(self, text: str):
        self._switch_tab(1)
        self.terminal.prefill(text)

    # ════════════════════════════════════════════════════════════════════
    # CONVERSATIONS
    # ════════════════════════════════════════════════════════════════════

    def _load_conversations(self):
        self.conv_list.blockSignals(True)
        self.conv_list.clear()
        self._convs = db.get_conversations()
        for c in self._convs:
            item = QListWidgetItem(f"  {c['title']}")
            item.setData(Qt.UserRole, c["id"])
            self.conv_list.addItem(item)
        self.conv_list.blockSignals(False)

    def _on_conv_selected(self, row: int):
        if row < 0 or row >= len(self._convs):
            return
        self.active_conv = self._convs[row]["id"]
        msgs = db.get_messages(self.active_conv)
        self.chat.load_messages(msgs, conv_id=self.active_conv)

    def _new_conversation(self):
        conv_id = db.create_conversation()
        self._load_conversations()
        for i in range(self.conv_list.count()):
            if self.conv_list.item(i).data(Qt.UserRole) == conv_id:
                self.conv_list.setCurrentRow(i)
                break
        self.chat.clear()
        self.active_conv = conv_id
        self._switch_tab(0)
        self.input_box.setFocus()

    # ════════════════════════════════════════════════════════════════════
    # SEND / STOP
    # ════════════════════════════════════════════════════════════════════

    def eventFilter(self, obj, event):
        if obj is self.input_box and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self._send()
                return True
        return super().eventFilter(obj, event)

    def _send(self):
        from app.agent_log import log, separator
        text = self.input_box.toPlainText().strip()
        if not text or self._streaming:
            return
        if not self.active_conv:
            self._new_conversation()
        separator(f"SEND → {text[:60]}")
        log("INFO", "main_window._send", "Usuario envía mensaje",
            {"msg": text[:200], "model": self.selected_model,
             "session_trust": self.session_trust, "persona": self.agent_persona})

        self.input_box.clear()
        self._streaming      = True
        self._response_bubble = None
        self._current_response = ""
        self.send_btn.hide()
        self.stop_btn.show()
        self.input_box.setReadOnly(True)
        self.model_status.setText("● generando...")
        if hasattr(self, "workspace_state"):
            self.workspace_state.setText("Generando respuesta")

        db.save_message(self.active_conv, "user", text)
        db.update_title(self.active_conv, text)
        self.chat.add_message("user", text)

        msgs = db.get_messages(self.active_conv)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in msgs
            if m["role"] in ("user", "assistant")
        ]

        self.worker = AgentWorker(
            messages         = history,
            model            = self.selected_model,
            trusted_tools    = self.trusted_tools,
            session_trust    = self.session_trust,
            tool_permissions = self.tool_permissions,
            system_prompt    = build_system_prompt(SYSTEM_PROMPT, personality=self.agent_persona),
            conversation_id  = self.active_conv,
        )
        _conv_id = self.active_conv  # snapshot — user may switch conversations mid-stream
        self.worker.token.connect(self._on_token)
        self.worker.tool_call.connect(self._on_tool_call)
        self.worker.tool_result.connect(self._on_tool_result)
        self.worker.need_approval.connect(self._on_need_approval)
        self.worker.finished.connect(lambda full: self._on_finished(full, _conv_id))
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _stop(self):
        worker = self.worker  # atomic snapshot — _end_streaming may set self.worker = None concurrently
        if worker:
            worker.stop()

    # ════════════════════════════════════════════════════════════════════
    # AGENT SIGNALS
    # ════════════════════════════════════════════════════════════════════

    def _on_token(self, token: str):
        if self._response_bubble is None:
            # Reuse bubble created by tool activity (if any), otherwise create fresh
            self._response_bubble = self.chat.get_or_create_assistant_bubble()
            from app.agent_log import log
            log("INFO", "main_window", "Primer token recibido — bubble creado")
        self._current_response += token
        self.chat.append_token(token)

    def _on_tool_call(self, event: dict):
        self._pending_tools[event["id"]] = {"name": event["name"], "args": event["args"]}
        self.chat.add_tool_activity(
            event["id"], event["name"], event["args"], event["dangerous"]
        )

    _SKIP_THREAT = {"read_file", "list_directory", "list_processes", "system_info",
                    "memory_info", "gpu_info", "network_info", "env_vars", "arp_cache"}
    _MAX_DETECTORS = 3

    def _check_threat(self, result: dict, tool_name: str):
        if tool_name in self._SKIP_THREAT:
            return
        if len(self._threat_detectors) >= self._MAX_DETECTORS:
            return
        from app.consciousness.threat_detector import ThreatDetector
        detector = ThreatDetector(tool_name, result, parent=self)
        detector.threat_found.connect(self._on_threat_found)
        def _remove_detector(d=detector):
            if d in self._threat_detectors:
                self._threat_detectors.remove(d)
        detector.finished.connect(_remove_detector)
        # Safety: force-remove after 60s if thread hangs and never emits finished
        from PySide6.QtCore import QTimer as _QT
        _QT.singleShot(60_000, _remove_detector)
        self._threat_detectors.append(detector)
        detector.start()

    def _on_threat_found(self, title: str, body: str, severity: str):
        if alert_sender.cloud_configured():
            alert_sender.send_threat_alert(title=title, body=body)

    def _on_tool_result(self, event: dict):
        self.chat.set_tool_result(event["id"], event["result"])
        pending = self._pending_tools.pop(event["id"], None)
        if pending and self.active_conv:
            decision_log.log_decision(
                self.active_conv, pending["name"], pending["args"],
                event["result"], approved=True,
            )
            self._check_threat(event["result"], pending["name"])

    def _on_need_approval(self, event: dict):
        self.notification_pending.emit(True)
        self.chat.show_approval(event["id"], event["name"], event["args"], event["dangerous"])
        if alert_sender.cloud_configured():
            token = alert_sender.request_approval(
                event["id"], event["name"], event["args"]
            )
            if token:
                poller = ApprovalPoller(event["id"], token)
                poller.decided.connect(self._on_cloud_approval)
                self._approval_pollers[event["id"]] = poller
                poller.start()

    def _on_cloud_approval(self, tool_id: str, approved: bool):
        """Respuesta de aprobación que llegó desde el móvil vía Cloud Run."""
        self._approval_pollers.pop(tool_id, None)
        if approved:
            self._on_tool_approved(tool_id, "", False)
        else:
            self._on_tool_rejected(tool_id)

    def _on_tool_approved(self, tool_id: str, tool_name: str, always: bool):
        self.chat.hide_approval(tool_id)
        poller = self._approval_pollers.pop(tool_id, None)
        if poller:
            poller.stop()
        if not self._approval_pollers:
            self.notification_pending.emit(False)
        if always and tool_name != "mistral_consult":
            self.trusted_tools.add(tool_name)
        if self.worker:
            self.worker.approve(True)

    def _on_tool_rejected(self, tool_id: str):
        poller = self._approval_pollers.pop(tool_id, None)
        if poller:
            poller.stop()
        if not self._approval_pollers:
            self.notification_pending.emit(False)
        self.chat.set_tool_cancelled(tool_id)
        pending = self._pending_tools.pop(tool_id, None)
        if pending and self.active_conv:
            decision_log.log_decision(
                self.active_conv, pending["name"], pending["args"],
                {}, approved=False,
            )
        if self.worker:
            self.worker.approve(False)

    def _on_finished(self, full: str, conv_id: int = None):
        from app.agent_log import log
        log("INFO", "main_window._on_finished", "Respuesta completada",
            {"full_len": len(full), "preview": full[:200] if full else ""})
        msg_id = None
        save_conv = conv_id or self.active_conv
        if full and save_conv:
            msg_id = db.save_message(save_conv, "assistant", full)
            try:
                from app.memory import refresh_conversation_memory
                refresh_conversation_memory(save_conv)
            except Exception:
                pass
        if not self.isVisible():
            self._end_streaming()
            return
        self.chat.finish_streaming(msg_id=msg_id, conv_id=save_conv)
        self._response_bubble = None
        self._end_streaming()
        self._load_conversations()
        self.model_status.setText("● modelo listo")
        if hasattr(self, "workspace_state"):
            self.workspace_state.setText("Sistema listo")

    def _on_error(self, msg: str):
        if not self.isVisible():
            return
        from app.agent_log import log
        log("ERROR", "main_window._on_error", "Error del agente", {"error": msg[:500]})
        lower = msg.lower()
        is_connection = any(
            marker in lower
            for marker in ("connecterror", "connecttimeout", "no se puede arrancar ollama", "ollama no responde")
        )
        title = "Error de conexion" if is_connection else "Error del agente"
        hint = (
            "\n\nVerifica que Ollama esta corriendo: `ollama serve`"
            if is_connection
            else "\n\nEl agente encontro un fallo interno. Revisa el bloque anterior y `agent.log`."
        )
        self.chat.add_message(
            "assistant",
            f"**{title}:**\n\n```\n{msg}\n```{hint}",
        )
        self._end_streaming()
        self.model_status.setText("error de conexion" if is_connection else "error del agente")
        if hasattr(self, "workspace_state"):
            self.workspace_state.setText("Revisar error")

    def _end_streaming(self):
        self._streaming = False
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        self.stop_btn.hide()
        self.send_btn.show()
        self.input_box.setReadOnly(False)
        self.input_box.setFocus()
        if hasattr(self, "workspace_state") and self.model_status.text() != "error de conexion":
            self.workspace_state.setText("Sistema listo")

    # ════════════════════════════════════════════════════════════════════
    # TRUST
    # ════════════════════════════════════════════════════════════════════

    def _toggle_trust(self, checked: bool):
        self.session_trust = checked
        self.trust_btn.setProperty("trusted", "true" if checked else "false")
        self.trust_btn.setStyle(self.trust_btn.style())
        if checked:
            self.trust_btn.setText("⚡  Confianza total")
        else:
            self.trust_btn.setText("🛡  Supervisado")
            self.trusted_tools.clear()

    # ════════════════════════════════════════════════════════════════════
    # RATING & FINE-TUNE
    # ════════════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════════════
    # AUTO-UPDATE
    # ════════════════════════════════════════════════════════════════════

    def notify_update_available(self, local: str, remote_info: str):
        self._update_local  = local
        self._update_remote = remote_info
        self.status_lbl.setText("🔄  Actualización disponible — click para instalar")
        self.status_lbl.setStyleSheet(
            "color: #00d9ff; font-size: 11px; padding: 8px 12px; cursor: pointer;"
        )

    def notify_up_to_date(self, sha: str):
        self.status_lbl.setText(f"● daemon activo · {sha}")
        self.status_lbl.setStyleSheet("")

    def _on_status_click(self, _event=None):
        if not self._update_local:
            return
        if self._update_dialog is None:
            self._update_dialog = UpdateDialog(self._update_local, self._update_remote, self)
        self._update_dialog.show()
        self._update_dialog.raise_()
        self._update_dialog.activateWindow()

    def _on_message_rated(self, message_id: int, conv_id: int, rating: int):
        try:
            collector.rate_message(message_id, conv_id, rating)
            stats = collector.get_stats()
            self.status_lbl.setText(
                f"● daemon activo · 👍{stats['positivos']} 👎{stats['negativos']}"
            )
        except Exception as e:
            print(f"[rating] Error: {e}")

    def _open_finetune(self):
        if self._ft_dialog is None:
            self._ft_dialog = FineTuneDialog(self)
        self._ft_dialog.show()
        self._ft_dialog.raise_()
        self._ft_dialog.activateWindow()

    def _export_finetune(self):
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        stats = collector.get_stats()
        if stats["positivos"] == 0:
            QMessageBox.information(
                self, "Sin datos",
                "No hay respuestas con 👍 para exportar.\n"
                "Dale thumbs up a las respuestas que quieras incluir.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar dataset JSONL", "finetune.jsonl",
            "JSONL Files (*.jsonl);;All Files (*)",
        )
        if not path:
            return
        try:
            out, count = collector.export_jsonl(path)
            QMessageBox.information(
                self, "Exportado",
                f"Dataset exportado: {count} pares conversacionales\n{out}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ════════════════════════════════════════════════════════════════════
    # AUTOMATIZACIÓN
    # ════════════════════════════════════════════════════════════════════

    def _open_mobile_dialog(self):
        if self._mobile_dialog is None:
            self._mobile_dialog = MobileSubscribeDialog(self)
        self._mobile_dialog.show()
        self._mobile_dialog.raise_()
        self._mobile_dialog.activateWindow()

    def _refresh_autostart_btn(self):
        enabled = autostart.is_enabled()
        self.autostart_btn.setText(
            "🟢  Inicio automático ON" if enabled else "⚪  Inicio automático OFF"
        )

    def _toggle_autostart(self):
        from PySide6.QtWidgets import QMessageBox
        try:
            now_on = autostart.toggle()
            self._refresh_autostart_btn()
            msg = (
                "✓ CyberAgent arrancará automáticamente con Windows."
                if now_on else
                "✓ Inicio automático desactivado."
            )
            self.status_lbl.setText(msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar el registro:\n{e}")

    def _free_vram(self):
        import subprocess
        subprocess.run(
            ["powershell", "-NonInteractive", "-Command",
             "Stop-Process -Name llama-server -Force -ErrorAction SilentlyContinue"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.status_lbl.setText("● VRAM liberada — recarga al chatear")
        if hasattr(self, "model_status"):
            self.model_status.setText("● modelo descargado")

    def _install_nssm_service(self):
        import os, ctypes
        ps1 = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "autostart_nssm.ps1")
        )
        if not os.path.isfile(ps1):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No encontrado", f"Script no encontrado:\n{ps1}")
            return
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell",
            f'-ExecutionPolicy Bypass -NoExit -File "{ps1}"',
            None, 1,
        )

    def closeEvent(self, event):
        """X oculta la ventana en bandeja — no cierra la app."""
        event.ignore()
        self.hide()
