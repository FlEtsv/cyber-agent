from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSizePolicy, QStackedWidget,
    QFrame, QComboBox, QScrollArea, QMenu, QInputDialog, QDialog, QLineEdit,
    QFormLayout, QDialogButtonBox, QColorDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QColor

from .chat_panel import ChatPanel
from .terminal_panel import TerminalPanel
from .references_panel import ReferencesDialog
from .agent_panel import AgentPanel
from .tools_panel import ToolsPanel
from .security_panel import SecurityPanel
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
    "edit_file":            "auto",
    "multi_edit":           "auto",
    "todo_write":           "auto",
    "lint_code":            "auto",
    "run_tests":            "auto",
    "apply_patch":          "auto",
    "code_symbols":         "auto",
    "cve_lookup":           "auto",
    "threat_intel":         "auto",
    "yara_scan":            "auto",
    "sql_query":            "auto",
    "gmail_search":         "auto",
    "gmail_read":           "auto",
    "gdrive_search":        "auto",
    "gdrive_read":          "auto",
    "gcalendar_events":     "auto",
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
    cost_updated = Signal()              # se emite tras cada llamada real a Mistral

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

        # Contador de consumo de Mistral: EVENT-DRIVEN — se refresca aprovechando
        # cada llamada real a Mistral (no por polling). Fallback lento por si
        # cambia el día con la app abierta.
        from app import mistral_usage
        self.cost_updated.connect(self._update_cost_lbl)
        mistral_usage.add_listener(lambda _s: self.cost_updated.emit())
        from PySide6.QtCore import QTimer
        self._cost_timer = QTimer(self)
        self._cost_timer.timeout.connect(self._update_cost_lbl)
        self._cost_timer.start(60000)   # fallback lento (rollover de día)
        self._update_cost_lbl()

    def _update_cost_lbl(self):
        try:
            from app import mistral_usage
            s = mistral_usage.get_summary("today")
            if s.get("calls"):
                ktok = (s["input_tokens"] + s["output_tokens"]) // 1000
                self.cost_lbl.setText(
                    f"💸 Mistral hoy: ${s['cost_usd']:.4f} · {s['calls']} llam · {ktok}k tok"
                )
            else:
                self.cost_lbl.setText("💸 Mistral hoy: $0.0000")
        except Exception:
            pass

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

        model_lbl = QLabel("  MODELO / CEREBRO")
        model_lbl.setObjectName("sidebar_section_hdr")
        lay.addWidget(model_lbl)

        # Construye la lista de cerebros disponibles
        self._model_ids = [OLLAMA_MODEL, "auto"]
        model_labels = [f"🖥️ Local ({OLLAMA_MODEL})", "🔀 Auto (decide solo)"]
        try:
            from app.brain import mistral_available
            if mistral_available():
                self._model_ids += ["fused", "codestral-latest",
                                    "mistral-large-latest", "mistral-medium-latest"]
                model_labels += ["🤝 Fusionado (Mistral Medium 3 + local)",
                                 "💻 Codestral (código)",
                                 "🧠 Mistral Large", "🧠 Mistral Medium 3"]
        except Exception:
            pass

        self.model_combo = QComboBox()
        self.model_combo.setObjectName("persona_combo")
        for lbl in model_labels:
            self.model_combo.addItem(lbl)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        lay.addWidget(self.model_combo)

        # Por defecto: LOCAL (gratis). Mistral/fused/Small quedan seleccionables a mano.
        self.model_combo.setCurrentIndex(0)
        self.selected_model = self._model_ids[0]

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

        # New conversation + nueva carpeta (A2 workspace)
        new_row = QHBoxLayout()
        new_btn = QPushButton("＋  Chat")
        new_btn.setObjectName("btn_new_conv")
        new_btn.clicked.connect(lambda: self._new_conversation(ask_folder=True))
        folder_btn = QPushButton("📁  Carpeta")
        folder_btn.setObjectName("btn_new_conv")
        folder_btn.clicked.connect(self._create_folder_dialog)
        new_row.addWidget(new_btn, 1)
        new_row.addWidget(folder_btn, 1)
        lay.addLayout(new_row)

        # Conversation list (agrupada por carpetas)
        self.conv_list = QListWidget()
        self.conv_list.setObjectName("conv_list")
        self.conv_list.currentRowChanged.connect(self._on_conv_selected)
        self.conv_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.conv_list.customContextMenuRequested.connect(self._conv_context_menu)
        self.conv_list.itemClicked.connect(self._on_conv_item_clicked)
        self._collapsed = set()
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

        # Contador de consumo de Mistral (siempre visible)
        self.cost_lbl = QLabel("💸 Mistral hoy: —")
        self.cost_lbl.setObjectName("status_bar")
        self.cost_lbl.setToolTip("Consumo de Mistral de hoy (tokens y coste en USD). Se actualiza en vivo.")
        lay.addWidget(self.cost_lbl)

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

        self.tab_security = QPushButton("🛡️  Seguridad")
        self.tab_security.setObjectName("tab_btn")
        self.tab_security.setCheckable(True)
        self.tab_security.setChecked(False)
        self.tab_security.clicked.connect(lambda: self._switch_tab(4))

        tlay.addWidget(self.tab_chat)
        tlay.addWidget(self.tab_terminal)
        tlay.addWidget(self.tab_agent)
        tlay.addWidget(self.tab_tools)
        tlay.addWidget(self.tab_security)
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

        # Page 4: Seguridad (SEC-003)
        self.security_panel = SecurityPanel()
        self.stack.addWidget(self.security_panel)

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
        self.tab_security.setChecked(idx == 4)
        tabs = [self.tab_chat, self.tab_terminal, self.tab_agent,
                self.tab_tools, self.tab_security]
        for i, btn in enumerate(tabs):
            btn.setObjectName("tab_btn_active" if i == idx else "tab_btn")
            btn.setStyle(btn.style())
        if idx == 2:
            self.agent_panel.refresh_log()
        if hasattr(self, "workspace_route"):
            routes = ["Vista: Chat", "Vista: Terminal", "Vista: Agente",
                      "Vista: Herramientas", "Vista: Seguridad"]
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

    _ROLE_FOLDER = Qt.UserRole + 1   # ("folder", id) en cabeceras

    def _load_conversations(self):
        self.conv_list.blockSignals(True)
        self.conv_list.clear()
        self._convs = db.get_conversations()
        self._folders = db.get_folders()
        groups = {}
        for c in self._convs:
            groups.setdefault(c.get("folder_id"), []).append(c)

        def add_header(f, depth):
            collapsed = f["id"] in self._collapsed
            caret = "▸" if collapsed else "▾"
            it = QListWidgetItem(("    " * depth) + f"{caret} 📁 {f['name']}")
            it.setData(Qt.UserRole, None)
            it.setData(self._ROLE_FOLDER, f["id"])
            it.setFlags(Qt.ItemIsEnabled)
            fnt = it.font(); fnt.setBold(True); it.setFont(fnt)
            if f.get("color"):
                it.setForeground(QColor(f["color"]))
            self.conv_list.addItem(it)
            return not collapsed

        def add_conv(c, depth=0):
            dot = "● " if c.get("color") else ""
            it = QListWidgetItem(("    " * depth) + f"   {dot}{c['title']}")
            it.setData(Qt.UserRole, c["id"])
            if c.get("color"):
                it.setForeground(QColor(c["color"]))
            self.conv_list.addItem(it)

        def render_folder(f, depth=0):
            opened = add_header(f, depth)
            if opened:
                for c in groups.get(f["id"], []):
                    add_conv(c, depth + 1)
            for sub in self._folders:
                if sub.get("parent_id") == f["id"]:
                    render_folder(sub, depth + 1)

        for f in self._folders:
            if not f.get("parent_id"):
                render_folder(f)
        loose = groups.get(None, [])
        if loose and self._folders:
            h = QListWidgetItem("Sin carpeta")
            h.setData(Qt.UserRole, None); h.setFlags(Qt.ItemIsEnabled)
            h.setForeground(QColor("#616d7d"))
            self.conv_list.addItem(h)
        for c in loose:
            add_conv(c)
        self.conv_list.blockSignals(False)

    def _on_conv_selected(self, row: int):
        item = self.conv_list.item(row)
        if not item:
            return
        cid = item.data(Qt.UserRole)
        if cid is None:
            return                       # cabecera de carpeta
        self.active_conv = cid
        msgs = db.get_messages(cid)
        self.chat.load_messages(msgs, conv_id=cid)

    def _on_conv_item_clicked(self, item):
        fid = item.data(self._ROLE_FOLDER)
        if fid is not None:
            self._collapsed.discard(fid) if fid in self._collapsed else self._collapsed.add(fid)
            self._load_conversations()

    def _select_conv_item(self, conv_id):
        for i in range(self.conv_list.count()):
            if self.conv_list.item(i).data(Qt.UserRole) == conv_id:
                self.conv_list.setCurrentRow(i)
                break

    def _new_conversation(self, ask_folder=True):
        folder_id = None
        if ask_folder:
            folder_id = self._pick_folder_dialog()
            if folder_id == "__cancel__":
                return
        conv_id = db.create_conversation(folder_id=folder_id)
        self._load_conversations()
        self._select_conv_item(conv_id)
        self.chat.clear()
        self.active_conv = conv_id
        self._switch_tab(0)
        self.input_box.setFocus()

    # ── A2: carpetas / workspace (escritorio) ───────────────────────────────
    def _pick_folder_dialog(self, title="¿Para quién es este chat?"):
        folders = db.get_folders()
        labels = ["(Sin carpeta)"] + [f["name"] for f in folders] + ["＋ Nueva categoría…"]
        choice, ok = QInputDialog.getItem(self, "Carpeta", title, labels, 0, False)
        if not ok:
            return "__cancel__"
        if choice == labels[0]:
            return None
        if choice == labels[-1]:
            return self._create_folder_dialog()
        for f in folders:
            if f["name"] == choice:
                return f["id"]
        return None

    def _folder_dialog(self, folder=None):
        """Diálogo crear/editar carpeta. Devuelve dict o None."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar categoría" if folder else "Nueva categoría")
        form = QFormLayout(dlg)
        name = QLineEdit(folder["name"] if folder else "")
        context = QTextEdit((folder or {}).get("context", "") or "")
        context.setMaximumHeight(80)
        color = QLineEdit((folder or {}).get("color", "") or "#54c7d8")
        model = QComboBox(); model.setEditable(True)
        model.addItem("")
        for m_ in ("cyberagent-24b", "codestral-latest", "mistral-medium-latest", "mistral-large-latest"):
            model.addItem(m_)
        if folder and folder.get("default_model"):
            model.setEditText(folder["default_model"])
        form.addRow("Nombre", name)
        form.addRow("Contexto", context)
        form.addRow("Color (hex)", color)
        form.addRow("Modelo por defecto", model)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.Accepted or not name.text().strip():
            return None
        return {"name": name.text().strip(), "context": context.toPlainText().strip(),
                "color": color.text().strip() or None, "default_model": model.currentText().strip() or None}

    def _create_folder_dialog(self):
        data = self._folder_dialog()
        if not data:
            return None
        fid = db.create_folder(data["name"], color=data["color"],
                               context=data["context"], default_model=data["default_model"])
        self._load_conversations()
        return fid

    def _conv_context_menu(self, pos):
        item = self.conv_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        fid = item.data(self._ROLE_FOLDER)
        cid = item.data(Qt.UserRole)
        if fid is not None:                         # cabecera de carpeta
            act_edit = menu.addAction("✏️  Editar carpeta")
            act_del = menu.addAction("🗑  Borrar carpeta")
            chosen = menu.exec(self.conv_list.mapToGlobal(pos))
            f = db.get_folder(fid)
            if chosen == act_edit and f:
                data = self._folder_dialog(f)
                if data:
                    db.update_folder(fid, **data)
                    self._load_conversations()
            elif chosen == act_del:
                db.delete_folder(fid)
                self._load_conversations()
        elif cid is not None:                       # conversación
            move = menu.addMenu("📁  Mover a")
            folders = db.get_folders()
            act_none = move.addAction("(Sin carpeta)")
            fmap = {}
            for f in folders:
                a = move.addAction(f["name"]); fmap[a] = f["id"]
            act_color = menu.addAction("🎨  Color…")
            act_del = menu.addAction("🗑  Borrar")
            chosen = menu.exec(self.conv_list.mapToGlobal(pos))
            if chosen == act_none:
                db.move_conversation(cid, None); self._load_conversations()
            elif chosen in fmap:
                db.move_conversation(cid, fmap[chosen]); self._load_conversations()
            elif chosen == act_color:
                col = QColorDialog.getColor(parent=self)
                if col.isValid():
                    db.set_conversation_color(cid, col.name()); self._load_conversations()
            elif chosen == act_del:
                db.delete_conversation(cid)
                if self.active_conv == cid:
                    self.active_conv = None; self.chat.clear()
                self._load_conversations()

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
            self._new_conversation(ask_folder=False)
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
        self.worker.reasoning.connect(self._on_reasoning)
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

    def _on_reasoning(self, text: str):
        # Proceso/razonamiento: indicador atenuado, NO contamina la respuesta final
        try:
            one = " ".join((text or "").split())
            if hasattr(self, "model_status"):
                self.model_status.setText("💭 " + one[:80])
            if hasattr(self.chat, "add_reasoning_step"):
                self.chat.add_reasoning_step(text)
        except Exception:
            pass

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
