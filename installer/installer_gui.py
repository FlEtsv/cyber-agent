"""
CyberAgent Installer — GUI profesional sin terminal
Corre con pythonw.exe o el exe compilado.
"""
import sys, os, subprocess, threading, shutil, winreg, ctypes
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QCheckBox, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon

# ── Paths ──────────────────────────────────────────────────────────────────
INSTALL_SRC   = Path(__file__).parent.parent / "dist" / "CyberAgent"
INSTALL_DST   = Path(os.environ["LOCALAPPDATA"]) / "CyberAgent"
STARTUP_DIR   = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
DESKTOP       = Path(os.environ["USERPROFILE"]) / "Desktop"

# ── Herramientas de seguridad opcionales ───────────────────────────────────
SECURITY_TOOLS = [
    {
        "id":   "nmap",
        "name": "Nmap",
        "desc": "Escáner de redes y detección de servicios",
        "cmd":  ["winget", "install", "Insecure.Nmap", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent", "-e"],
        "check": "nmap",
        "default": True,
    },
    {
        "id":   "git",
        "name": "Git",
        "desc": "Control de versiones (necesario para muchas herramientas)",
        "cmd":  ["winget", "install", "Git.Git", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent", "-e"],
        "check": "git",
        "default": True,
    },
    {
        "id":   "python_tools",
        "name": "Herramientas Python (pip)",
        "desc": "requests, scapy, impacket, pwntools, paramiko",
        "cmd":  ["pip", "install", "requests", "scapy", "paramiko", "cryptography", "pyyaml"],
        "check": None,
        "default": True,
    },
    {
        "id":   "wireshark",
        "name": "Wireshark",
        "desc": "Análisis de tráfico de red",
        "cmd":  ["winget", "install", "WiresharkFoundation.Wireshark", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent", "-e"],
        "check": None,
        "default": False,
    },
    {
        "id":   "vscode",
        "name": "Visual Studio Code",
        "desc": "Editor de código (el agente puede abrirlo)",
        "cmd":  ["winget", "install", "Microsoft.VisualStudioCode", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent", "-e"],
        "check": "code",
        "default": False,
    },
    {
        "id":   "ollama",
        "name": "Ollama",
        "desc": "Motor de IA local (REQUERIDO para el agente)",
        "cmd":  ["winget", "install", "Ollama.Ollama", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent", "-e"],
        "check": "ollama",
        "default": True,
    },
]

QSS = """
* { font-family: 'Segoe UI', 'Consolas', sans-serif; }
QWidget { background: #0a0e14; color: #c9d1d9; }
QLabel#title { color: #00d9ff; font-size: 22px; font-weight: bold; }
QLabel#sub   { color: #4a5568; font-size: 12px; }
QLabel#step  { color: #c9d1d9; font-size: 13px; padding: 2px 0; }
QLabel#done  { color: #00ff88; font-size: 13px; padding: 2px 0; }
QLabel#err   { color: #ff4466; font-size: 12px; padding: 2px 0; }
QLabel#section { color: #00d9ff; font-size: 12px; font-weight: bold; padding: 8px 0 4px; }
QProgressBar {
    background: #1e2d3d;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk { background: #00d9ff; border-radius: 4px; }
QPushButton#install_btn {
    background: rgba(0, 217, 255, 0.12);
    border: 1px solid rgba(0, 217, 255, 0.5);
    border-radius: 8px;
    color: #00d9ff;
    font-size: 14px;
    font-weight: bold;
    padding: 12px 32px;
}
QPushButton#install_btn:hover { background: rgba(0, 217, 255, 0.22); }
QPushButton#install_btn:disabled { background: transparent; color: #1e2d3d; border-color: #1e2d3d; }
QPushButton#close_btn {
    background: rgba(0, 255, 136, 0.12);
    border: 1px solid rgba(0, 255, 136, 0.5);
    border-radius: 8px;
    color: #00ff88;
    font-size: 14px;
    font-weight: bold;
    padding: 12px 32px;
}
QPushButton#close_btn:hover { background: rgba(0, 255, 136, 0.22); }
QCheckBox { color: #c9d1d9; font-size: 12px; padding: 2px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #1e2d3d; border-radius: 3px; background: #0d1117; }
QCheckBox::indicator:checked { background: rgba(0, 217, 255, 0.3); border-color: #00d9ff; }
QFrame#sep { color: #1e2d3d; }
QScrollArea { border: none; background: transparent; }
"""


class InstallWorker(QThread):
    log      = Signal(str, str)   # (message, level: "info"|"ok"|"err")
    progress = Signal(int)        # 0–100
    done     = Signal(bool)       # success

    def __init__(self, tools_to_install: list[dict]):
        super().__init__()
        self.tools = tools_to_install

    def run(self):
        steps = 3 + len(self.tools)
        current = 0

        def tick(msg, level="info"):
            nonlocal current
            current += 1
            self.log.emit(msg, level)
            self.progress.emit(int(current / steps * 100))

        try:
            # 1. Copiar archivos
            self.log.emit("Instalando CyberAgent...", "info")
            if INSTALL_SRC.exists():
                if INSTALL_DST.exists():
                    shutil.rmtree(INSTALL_DST)
                shutil.copytree(str(INSTALL_SRC), str(INSTALL_DST))
                tick("Archivos copiados correctamente", "ok")
            else:
                tick("Usando instalación de desarrollo", "info")
                INSTALL_DST.mkdir(parents=True, exist_ok=True)

            exe_path = INSTALL_DST / "CyberAgent.exe"
            if not exe_path.exists():
                # Fallback: usa pythonw del venv
                dev_path = Path(__file__).parent.parent
                exe_path = dev_path / ".venv" / "Scripts" / "pythonw.exe"

            # 2. Acceso directo escritorio
            _create_shortcut(
                target     = str(exe_path),
                shortcut   = str(DESKTOP / "CyberAgent.lnk"),
                workdir    = str(exe_path.parent),
                description= "CyberAgent — Agente IA local de ciberseguridad",
            )
            tick("Acceso directo en el escritorio creado", "ok")

            # 3. Inicio automático con Windows
            startup_bat = STARTUP_DIR / "cyber-agent.bat"
            startup_bat.write_text(
                f'@echo off\nstart "" "{exe_path}"\n', encoding="utf-8"
            )
            tick("Inicio automático configurado", "ok")

            # 4. Herramientas de seguridad
            for tool in self.tools:
                self.log.emit(f"Instalando {tool['name']}...", "info")
                already = tool.get("check") and shutil.which(tool["check"])
                if already:
                    tick(f"{tool['name']} — ya instalado", "ok")
                    continue
                try:
                    r = subprocess.run(
                        tool["cmd"], capture_output=True,
                        timeout=300, text=True, encoding="utf-8", errors="replace",
                    )
                    if r.returncode == 0:
                        tick(f"{tool['name']} instalado", "ok")
                    else:
                        tick(f"{tool['name']} — aviso: {r.stderr[:80]}", "info")
                except subprocess.TimeoutExpired:
                    tick(f"{tool['name']} — timeout", "err")
                except FileNotFoundError:
                    tick(f"{tool['name']} — gestor no encontrado (winget?)", "err")
                except Exception as e:
                    tick(f"{tool['name']} — {e}", "err")

            self.progress.emit(100)
            self.done.emit(True)

        except Exception as e:
            self.log.emit(f"Error fatal: {e}", "err")
            self.done.emit(False)


def _create_shortcut(target, shortcut, workdir, description):
    ps = (
        f"$WS = New-Object -ComObject WScript.Shell; "
        f"$SC = $WS.CreateShortcut('{shortcut}'); "
        f"$SC.TargetPath = '{target}'; "
        f"$SC.WorkingDirectory = '{workdir}'; "
        f"$SC.Description = '{description}'; "
        f"$SC.Save()"
    )
    subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                   capture_output=True, timeout=10)


class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CyberAgent — Instalador")
        self.setFixedSize(580, 720)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self._drag_pos = None
        self._worker = None
        self._tool_checks: dict[str, QCheckBox] = {}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(0)

        # Header
        title = QLabel("⚡ CYBER AGENT")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("Instalador v1.0 · Agente IA local de ciberseguridad")
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(20)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setObjectName("sep")
        lay.addWidget(sep1)
        lay.addSpacing(12)

        # Tools section
        tools_lbl = QLabel("HERRAMIENTAS A INSTALAR:")
        tools_lbl.setObjectName("section")
        lay.addWidget(tools_lbl)

        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFixedHeight(220)
        tools_widget = QWidget()
        tools_lay = QVBoxLayout(tools_widget)
        tools_lay.setContentsMargins(0, 0, 0, 0)
        tools_lay.setSpacing(6)

        for tool in SECURITY_TOOLS:
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(4, 0, 4, 0)
            row_lay.setSpacing(10)

            cb = QCheckBox(f"{tool['name']}")
            cb.setChecked(tool.get("default", False))
            self._tool_checks[tool["id"]] = cb
            row_lay.addWidget(cb)

            desc = QLabel(tool["desc"])
            desc.setObjectName("sub")
            desc.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row_lay.addWidget(desc, 1)

            tools_lay.addWidget(row)

        tools_scroll.setWidget(tools_widget)
        lay.addWidget(tools_scroll)

        lay.addSpacing(12)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("sep")
        lay.addWidget(sep2)
        lay.addSpacing(12)

        # Log section
        log_lbl = QLabel("PROGRESO:")
        log_lbl.setObjectName("section")
        lay.addWidget(log_lbl)

        log_scroll = QScrollArea()
        log_scroll.setWidgetResizable(True)
        log_scroll.setFixedHeight(200)
        self._log_widget = QWidget()
        self._log_lay = QVBoxLayout(self._log_widget)
        self._log_lay.setContentsMargins(4, 4, 4, 4)
        self._log_lay.setSpacing(2)
        self._log_lay.addStretch()
        log_scroll.setWidget(self._log_widget)
        self._log_scroll = log_scroll
        lay.addWidget(log_scroll)

        lay.addSpacing(12)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        lay.addWidget(self.progress_bar)

        lay.addSpacing(16)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.install_btn = QPushButton("⚡  Instalar CyberAgent")
        self.install_btn.setObjectName("install_btn")
        self.install_btn.clicked.connect(self._start_install)

        self.close_btn = QPushButton("Cancelar")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.hide()

        btn_row.addStretch()
        btn_row.addWidget(self.install_btn)
        btn_row.addWidget(self.close_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    # ── Draggable window ──────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Install ───────────────────────────────────────────────────────────

    def _start_install(self):
        selected = [
            t for t in SECURITY_TOOLS
            if self._tool_checks.get(t["id"], QCheckBox()).isChecked()
        ]
        self.install_btn.setEnabled(False)
        self.install_btn.setText("⏳  Instalando...")

        self._worker = InstallWorker(selected)
        self._worker.log.connect(self._on_log)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_log(self, msg: str, level: str):
        lbl = QLabel(f"  {'✓' if level=='ok' else '✗' if level=='err' else '·'}  {msg}")
        lbl.setObjectName("done" if level == "ok" else "err" if level == "err" else "step")
        self._log_lay.insertWidget(self._log_lay.count() - 1, lbl)
        QTimer.singleShot(50, lambda: self._log_scroll.verticalScrollBar().setValue(
            self._log_scroll.verticalScrollBar().maximum()
        ))

    def _on_done(self, success: bool):
        if success:
            self.install_btn.setText("✓  Instalación completada")
            self.install_btn.setStyleSheet("color: #00ff88; border-color: #00ff88;")
            self.close_btn.setText("✓  Lanzar CyberAgent")
            self.close_btn.disconnect()
            self.close_btn.clicked.connect(self._launch_and_close)
        else:
            self.install_btn.setText("✗  Error — ver log")
            self.install_btn.setStyleSheet("color: #ff4466; border-color: #ff4466;")
            self.close_btn.setText("Cerrar")
        self.close_btn.show()

    def _launch_and_close(self):
        exe = INSTALL_DST / "CyberAgent.exe"
        if exe.exists():
            subprocess.Popen([str(exe)], creationflags=0x00000008)  # DETACHED_PROCESS
        self.close()


def main():
    # Solicitar permisos de administrador si no los tiene
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
