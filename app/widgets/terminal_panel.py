import os, re, subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QLineEdit,
    QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QEvent
from PySide6.QtGui import QFont, QTextCursor, QTextOption

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CWD_MARKER = "__CYBERAGENT_CWD__:"

PROMPTS = {"powershell": "PS>", "cmd": "CMD>", "bash": "bash$"}

SHELL_WRAPPERS = {
    "powershell": lambda cmd, cwd: (
        f"Set-Location \"{cwd}\" -ErrorAction SilentlyContinue; "
        f"{cmd}; "
        f"Write-Host \"{CWD_MARKER}$((Get-Location).Path)\""
    ),
    "cmd": lambda cmd, cwd: f"cd /d \"{cwd}\" && {cmd} && echo {CWD_MARKER}%CD%",
    "bash": lambda cmd, cwd: f"cd \"{cwd}\" 2>/dev/null; {cmd}; echo \"{CWD_MARKER}$PWD\"",
}


class TerminalWorker(QThread):
    line_out = Signal(str)
    done = Signal(int)

    def __init__(self, command, shell_type, cwd):
        super().__init__()
        self.command = command
        self.shell_type = shell_type
        self.cwd = cwd
        self._proc = None
        self._killed = False

    def terminate_proc(self):
        self._killed = True
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def run(self):
        wrapper = SHELL_WRAPPERS.get(self.shell_type, SHELL_WRAPPERS["powershell"])
        wrapped = wrapper(self.command, self.cwd)

        if self.shell_type == "cmd":
            cmd = ["cmd.exe", "/c", wrapped]
        elif self.shell_type == "bash":
            cmd = ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c", wrapped]
        else:
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", wrapped]

        safe_cwd = self.cwd if os.path.isdir(self.cwd) else os.path.expanduser("~")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=safe_cwd,
            )
            for line in iter(self._proc.stdout.readline, ""):
                if self._killed:
                    break
                self.line_out.emit(line)
            self._proc.wait()
            rc = -1 if self._killed else (self._proc.returncode or 0)
            if self._killed:
                self.line_out.emit("\n[proceso terminado por el usuario]\n")
            self.done.emit(rc)
        except FileNotFoundError as e:
            self.line_out.emit(f"Error: herramienta no encontrada — {e}\n")
            self.done.emit(-1)
        except Exception as e:
            self.line_out.emit(f"Error: {e}\n")
            self.done.emit(-1)


class TerminalPanel(QWidget):
    """
    Terminal interactiva con PowerShell, CMD y WSL bash.
    Soporta streaming de salida en tiempo real, historial y seguimiento de CWD.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[str] = []
        self._hist_idx = -1
        self._cwd = os.path.expanduser("~")
        self._shell = "powershell"
        self._worker: TerminalWorker | None = None
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setObjectName("terminal_toolbar")
        tlay = QHBoxLayout(toolbar)
        tlay.setContentsMargins(12, 8, 12, 8)
        tlay.setSpacing(6)

        title = QLabel("⚡ TERMINAL")
        title.setObjectName("terminal_title")
        tlay.addWidget(title)

        self.cwd_label = QLabel(self._cwd)
        self.cwd_label.setObjectName("terminal_cwd")
        self.cwd_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.cwd_label.setAlignment(Qt.AlignCenter)
        tlay.addWidget(self.cwd_label, 1)

        self._shell_btns = {}
        for label, key in [("PowerShell", "powershell"), ("CMD", "cmd"), ("WSL bash", "bash")]:
            btn = QPushButton(label)
            btn.setObjectName("shell_btn")
            btn.setCheckable(True)
            btn.setChecked(key == "powershell")
            btn.clicked.connect(lambda _, k=key: self._set_shell(k))
            self._shell_btns[key] = btn
            tlay.addWidget(btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #1e2d3d;")
        tlay.addWidget(sep)

        self.clear_btn = QPushButton("Limpiar")
        self.clear_btn.setObjectName("btn_terminal_action")
        self.clear_btn.clicked.connect(self._clear)
        tlay.addWidget(self.clear_btn)

        self.kill_btn = QPushButton("⏹ Terminar")
        self.kill_btn.setObjectName("btn_terminal_kill")
        self.kill_btn.setEnabled(False)
        self.kill_btn.clicked.connect(self._kill_proc)
        tlay.addWidget(self.kill_btn)

        lay.addWidget(toolbar)

        # Output
        self.output = QPlainTextEdit()
        self.output.setObjectName("terminal_output")
        self.output.setReadOnly(True)
        self.output.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        font = QFont("Cascadia Code", 11)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        self.output.setFont(font)
        lay.addWidget(self.output, 1)

        # Input bar
        ibar = QWidget()
        ibar.setObjectName("terminal_input_bar")
        ilay = QHBoxLayout(ibar)
        ilay.setContentsMargins(12, 8, 12, 8)
        ilay.setSpacing(8)

        self.prompt_lbl = QLabel("PS>")
        self.prompt_lbl.setObjectName("terminal_prompt")
        self.prompt_lbl.setFixedWidth(52)
        ilay.addWidget(self.prompt_lbl)

        self.input_line = QLineEdit()
        self.input_line.setObjectName("terminal_input_line")
        self.input_line.setPlaceholderText("Escribe un comando... (↑↓ historial)")
        self.input_line.returnPressed.connect(self._run)
        self.input_line.installEventFilter(self)
        ilay.addWidget(self.input_line, 1)

        self.run_btn = QPushButton("▶")
        self.run_btn.setObjectName("btn_terminal_run")
        self.run_btn.setFixedWidth(40)
        self.run_btn.clicked.connect(self._run)
        ilay.addWidget(self.run_btn)

        lay.addWidget(ibar)

        self._write(
            "⚡ CyberAgent Terminal\n"
            "   Modos: PowerShell | CMD | WSL bash\n"
            f"   Directorio: {self._cwd}\n\n"
        )

    # ── Event filter (historial Up/Down) ──────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self.input_line and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key_Up:
                self._hist_prev()
                return True
            if event.key() == Qt.Key_Down:
                self._hist_next()
                return True
        return super().eventFilter(obj, event)

    # ── Shell switching ───────────────────────────────────────────────────

    def _set_shell(self, shell: str):
        self._shell = shell
        self.prompt_lbl.setText(PROMPTS.get(shell, ">"))
        for k, btn in self._shell_btns.items():
            btn.setChecked(k == shell)

    # ── History ───────────────────────────────────────────────────────────

    def _hist_prev(self):
        if not self._history:
            return
        self._hist_idx = (len(self._history) - 1) if self._hist_idx < 0 else max(0, self._hist_idx - 1)
        self.input_line.setText(self._history[self._hist_idx])

    def _hist_next(self):
        if not self._history or self._hist_idx < 0:
            return
        self._hist_idx += 1
        if self._hist_idx >= len(self._history):
            self._hist_idx = -1
            self.input_line.clear()
        else:
            self.input_line.setText(self._history[self._hist_idx])

    # ── Command execution ─────────────────────────────────────────────────

    def _run(self):
        cmd = self.input_line.text().strip()
        if not cmd or self._worker is not None:
            return

        self._history.append(cmd)
        self._hist_idx = -1
        self.input_line.clear()
        self._write(f"\n{self.prompt_lbl.text()} {cmd}\n")

        self._worker = TerminalWorker(cmd, self._shell, self._cwd)
        self._worker.line_out.connect(self._on_line)
        self._worker.done.connect(self._on_done)
        self.kill_btn.setEnabled(True)
        self.run_btn.setEnabled(False)
        self.input_line.setEnabled(False)
        self._worker.start()

    def _kill_proc(self):
        if self._worker:
            self._worker.terminate_proc()

    def _clear(self):
        self.output.clear()

    # ── Worker signals ────────────────────────────────────────────────────

    def _on_line(self, text: str):
        if CWD_MARKER in text:
            new_cwd = text.split(CWD_MARKER, 1)[1].strip()
            if os.path.isdir(new_cwd):
                self._cwd = new_cwd
                self.cwd_label.setText(self._cwd)
        else:
            self._write(text)

    def _on_done(self, rc: int):
        if rc not in (0, -1):
            self._write(f"[exit {rc}]\n")
        self._write(f"{self.prompt_lbl.text()} ")
        self._worker = None
        self.kill_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
        self.input_line.setEnabled(True)
        self.input_line.setFocus()

    def _write(self, text: str):
        text = ANSI_RE.sub("", text)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    # ── Public API ────────────────────────────────────────────────────────

    def prefill(self, command: str):
        """Pre-llena el input desde el panel de referencias."""
        self.input_line.setText(command)
        self.input_line.setFocus()
