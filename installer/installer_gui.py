"""
CyberAgent Installer — GUI profesional sin terminal.
Modos:
  - Dev: copia desde ../dist/CyberAgent/ (build local)
  - Standalone: descarga la última release de GitHub
"""
import sys, os, subprocess, shutil, winreg, ctypes, zipfile, tempfile
from pathlib import Path
import httpx
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QCheckBox, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

# ── Paths ─────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    _SELF_DIR = Path(sys.executable).parent
else:
    _SELF_DIR = Path(__file__).parent

INSTALL_SRC  = _SELF_DIR.parent / "dist" / "CyberAgent"   # solo existe en dev
INSTALL_DST  = Path(os.environ["LOCALAPPDATA"]) / "CyberAgent"
DESKTOP      = Path(os.environ["USERPROFILE"]) / "Desktop"
REPO         = "FlEtsv/cyber-agent"
_API_RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"

# ── Herramientas de seguridad opcionales ──────────────────────────────────────
SECURITY_TOOLS = [
    {
        "id":      "ollama",
        "name":    "Ollama",
        "desc":    "Motor de IA local (REQUERIDO para el agente)",
        "cmd":     ["winget", "install", "Ollama.Ollama", "--accept-package-agreements",
                    "--accept-source-agreements", "--silent", "-e"],
        "check":   "ollama",
        "default": True,
    },
    {
        "id":      "git",
        "name":    "Git",
        "desc":    "Control de versiones",
        "cmd":     ["winget", "install", "Git.Git", "--accept-package-agreements",
                    "--accept-source-agreements", "--silent", "-e"],
        "check":   "git",
        "default": True,
    },
    {
        "id":      "nmap",
        "name":    "Nmap",
        "desc":    "Escáner de redes y detección de servicios",
        "cmd":     ["winget", "install", "Insecure.Nmap", "--accept-package-agreements",
                    "--accept-source-agreements", "--silent", "-e"],
        "check":   "nmap",
        "default": True,
    },
    {
        "id":      "wireshark",
        "name":    "Wireshark",
        "desc":    "Análisis de tráfico de red",
        "cmd":     ["winget", "install", "WiresharkFoundation.Wireshark", "--accept-package-agreements",
                    "--accept-source-agreements", "--silent", "-e"],
        "check":   None,
        "default": False,
    },
    {
        "id":      "vscode",
        "name":    "Visual Studio Code",
        "desc":    "Editor de código (el agente puede abrirlo)",
        "cmd":     ["winget", "install", "Microsoft.VisualStudioCode", "--accept-package-agreements",
                    "--accept-source-agreements", "--silent", "-e"],
        "check":   "code",
        "default": False,
    },
]

QSS = """
* { font-family: 'Segoe UI', 'Consolas', sans-serif; }
QWidget { background: #0a0e14; color: #c9d1d9; }
QLabel#title  { color: #00d9ff; font-size: 22px; font-weight: bold; }
QLabel#sub    { color: #4a5568; font-size: 12px; }
QLabel#step   { color: #c9d1d9; font-size: 13px; padding: 2px 0; }
QLabel#done   { color: #00ff88; font-size: 13px; padding: 2px 0; }
QLabel#err    { color: #ff4466; font-size: 12px; padding: 2px 0; }
QLabel#section{ color: #00d9ff; font-size: 12px; font-weight: bold; padding: 8px 0 4px; }
QLabel#dl_lbl { color: #ffd700; font-size: 12px; padding: 4px 0; }
QProgressBar  {
    background: #1e2d3d; border: none; border-radius: 4px;
    height: 8px; text-align: center;
}
QProgressBar::chunk { background: #00d9ff; border-radius: 4px; }
QProgressBar#dl_bar::chunk { background: #ffd700; border-radius: 4px; }
QPushButton#install_btn {
    background: rgba(0,217,255,0.12); border: 1px solid rgba(0,217,255,0.5);
    border-radius: 8px; color: #00d9ff; font-size: 14px; font-weight: bold;
    padding: 12px 32px;
}
QPushButton#install_btn:hover    { background: rgba(0,217,255,0.22); }
QPushButton#install_btn:disabled { background: transparent; color: #1e2d3d; border-color: #1e2d3d; }
QPushButton#close_btn {
    background: rgba(0,255,136,0.12); border: 1px solid rgba(0,255,136,0.5);
    border-radius: 8px; color: #00ff88; font-size: 14px; font-weight: bold;
    padding: 12px 32px;
}
QPushButton#close_btn:hover { background: rgba(0,255,136,0.22); }
QCheckBox { color: #c9d1d9; font-size: 12px; padding: 2px; }
QCheckBox::indicator { width:14px; height:14px; border:1px solid #1e2d3d; border-radius:3px; background:#0d1117; }
QCheckBox::indicator:checked { background:rgba(0,217,255,0.3); border-color:#00d9ff; }
QFrame#sep    { color: #1e2d3d; }
QScrollArea   { border: none; background: transparent; }
"""


# ── Download worker ───────────────────────────────────────────────────────────
class DownloadWorker(QThread):
    progress = Signal(int, str)   # pct, message
    done     = Signal(str)        # extracted_dir
    failed   = Signal(str)

    def run(self):
        try:
            self.progress.emit(0, "Consultando GitHub Releases...")
            with httpx.Client(timeout=15, follow_redirects=True) as c:
                resp = c.get(_API_RELEASE, headers={"Accept": "application/vnd.github.v3+json"})
                resp.raise_for_status()
                data = resp.json()

            tag = data.get("tag_name", "?")
            asset = next(
                (a for a in data.get("assets", [])
                 if "CyberAgent-" in a["name"]
                 and "windows" in a["name"].lower()
                 and "Installer" not in a["name"]),
                None,
            )
            if not asset:
                self.failed.emit("No se encontró el asset Windows en el release.")
                return

            url  = asset["browser_download_url"]
            size = asset.get("size", 0)
            name = asset["name"]
            self.progress.emit(5, f"Descargando {name}  ({size // 1048576} MB)...")

            zip_path   = os.path.join(tempfile.gettempdir(), name)
            downloaded = 0
            with httpx.Client(timeout=600, follow_redirects=True) as c:
                with c.stream("GET", url) as r:
                    r.raise_for_status()
                    with open(zip_path, "wb") as f:
                        for chunk in r.iter_bytes(chunk_size=524288):
                            f.write(chunk)
                            downloaded += len(chunk)
                            pct = int(5 + (downloaded / size) * 80) if size else 50
                            self.progress.emit(pct, f"Descargando {downloaded // 1048576}/{size // 1048576} MB")

            self.progress.emit(87, "Extrayendo archivos...")
            extract = os.path.join(tempfile.gettempdir(), "cyberagent_install_tmp")
            if os.path.exists(extract):
                shutil.rmtree(extract)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract)
            os.remove(zip_path)

            # El zip contiene CyberAgent/ dentro
            inner = next(
                (os.path.join(extract, d) for d in os.listdir(extract)
                 if os.path.isdir(os.path.join(extract, d))),
                extract,
            )
            self.progress.emit(95, f"✓ Listo — versión {tag}")
            self.done.emit(inner)

        except Exception as e:
            self.failed.emit(str(e))


# ── Install worker ────────────────────────────────────────────────────────────
class InstallWorker(QThread):
    log      = Signal(str, str)   # message, level
    progress = Signal(int)
    done     = Signal(bool)

    def __init__(self, src_dir: str, tools: list[dict]):
        super().__init__()
        self.src_dir = src_dir
        self.tools   = tools

    def run(self):
        steps   = 3 + len(self.tools)
        current = 0

        def tick(msg, level="info"):
            nonlocal current
            current += 1
            self.log.emit(msg, level)
            self.progress.emit(int(current / steps * 100))

        try:
            # 1. Copiar archivos (preserva data/)
            self.log.emit("Instalando CyberAgent...", "info")
            src = Path(self.src_dir)
            if src.exists():
                if INSTALL_DST.exists():
                    for item in INSTALL_DST.iterdir():
                        if item.name != "data":
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                else:
                    INSTALL_DST.mkdir(parents=True)
                for item in src.iterdir():
                    dst_item = INSTALL_DST / item.name
                    if item.is_dir():
                        shutil.copytree(str(item), str(dst_item), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(item), str(dst_item))
                tick("Archivos instalados correctamente", "ok")
            else:
                tick("Directorio fuente no encontrado", "err")
                self.done.emit(False)
                return

            exe_path = INSTALL_DST / "CyberAgent.exe"
            if not exe_path.exists():
                tick("CyberAgent.exe no encontrado en destino", "err")
                self.done.emit(False)
                return

            # 2. Acceso directo escritorio
            _create_shortcut(
                target      = str(exe_path),
                shortcut    = str(DESKTOP / "CyberAgent.lnk"),
                workdir     = str(INSTALL_DST),
                description = "CyberAgent — Agente IA local de ciberseguridad",
            )
            tick("Acceso directo en el escritorio creado", "ok")

            # 3. Registro HKCU para inicio automático (lo gestiona la propia app)
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows\CurrentVersion\Run",
                                     0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "CyberAgent", 0, winreg.REG_SZ, str(exe_path))
                winreg.CloseKey(key)
                tick("Inicio automático con Windows configurado", "ok")
            except Exception as e:
                tick(f"Inicio automático: {e}", "info")

            # 4. Herramientas de seguridad
            for tool in self.tools:
                self.log.emit(f"Instalando {tool['name']}...", "info")
                if tool.get("check") and shutil.which(tool["check"]):
                    tick(f"{tool['name']} — ya instalado", "ok")
                    continue
                try:
                    r = subprocess.run(tool["cmd"], capture_output=True,
                                       timeout=300, text=True, encoding="utf-8", errors="replace")
                    if r.returncode == 0:
                        tick(f"{tool['name']} instalado", "ok")
                    else:
                        tick(f"{tool['name']} — {r.stderr[:80]}", "info")
                except subprocess.TimeoutExpired:
                    tick(f"{tool['name']} — timeout", "err")
                except FileNotFoundError:
                    tick(f"{tool['name']} — winget no encontrado", "err")
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


# ── Ventana principal ─────────────────────────────────────────────────────────
class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CyberAgent — Instalador")
        self.setFixedSize(600, 760)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self._drag_pos   = None
        self._worker     = None
        self._dl_worker  = None
        self._src_dir    = str(INSTALL_SRC)
        self._tool_checks: dict[str, QCheckBox] = {}
        self._build()

        # Si no hay dist local, auto-descargamos
        if not INSTALL_SRC.exists():
            QTimer.singleShot(400, self._start_download)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(0)

        # Header
        title = QLabel("⚡ CYBER AGENT")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        self._sub_lbl = QLabel("Instalador · Agente IA local de ciberseguridad")
        self._sub_lbl.setObjectName("sub")
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._sub_lbl)

        lay.addSpacing(16)

        # Barra de descarga (oculta en modo dev)
        self._dl_frame = QFrame()
        dl_lay = QVBoxLayout(self._dl_frame)
        dl_lay.setContentsMargins(0, 0, 0, 0)
        dl_lay.setSpacing(4)
        self._dl_lbl = QLabel("Descargando última versión de GitHub...")
        self._dl_lbl.setObjectName("dl_lbl")
        dl_lay.addWidget(self._dl_lbl)
        self._dl_bar = QProgressBar()
        self._dl_bar.setObjectName("dl_bar")
        self._dl_bar.setValue(0)
        dl_lay.addWidget(self._dl_bar)
        lay.addWidget(self._dl_frame)
        self._dl_frame.setVisible(not INSTALL_SRC.exists())

        lay.addSpacing(8)
        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine); sep1.setObjectName("sep")
        lay.addWidget(sep1)
        lay.addSpacing(10)

        # Tools
        tools_lbl = QLabel("HERRAMIENTAS A INSTALAR:")
        tools_lbl.setObjectName("section")
        lay.addWidget(tools_lbl)

        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFixedHeight(200)
        tools_widget = QWidget()
        tools_lay = QVBoxLayout(tools_widget)
        tools_lay.setContentsMargins(0, 0, 0, 0)
        tools_lay.setSpacing(6)

        for tool in SECURITY_TOOLS:
            row = QWidget()
            rl  = QHBoxLayout(row)
            rl.setContentsMargins(4, 0, 4, 0)
            rl.setSpacing(10)
            cb = QCheckBox(tool["name"])
            cb.setChecked(tool.get("default", False))
            self._tool_checks[tool["id"]] = cb
            rl.addWidget(cb)
            desc = QLabel(tool["desc"])
            desc.setObjectName("sub")
            rl.addWidget(desc, 1)
            tools_lay.addWidget(row)

        tools_scroll.setWidget(tools_widget)
        lay.addWidget(tools_scroll)

        lay.addSpacing(10)
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); sep2.setObjectName("sep")
        lay.addWidget(sep2)
        lay.addSpacing(10)

        # Log
        log_lbl = QLabel("PROGRESO:")
        log_lbl.setObjectName("section")
        lay.addWidget(log_lbl)

        log_scroll = QScrollArea()
        log_scroll.setWidgetResizable(True)
        log_scroll.setFixedHeight(200)
        self._log_widget = QWidget()
        self._log_lay    = QVBoxLayout(self._log_widget)
        self._log_lay.setContentsMargins(4, 4, 4, 4)
        self._log_lay.setSpacing(2)
        self._log_lay.addStretch()
        log_scroll.setWidget(self._log_widget)
        self._log_scroll = log_scroll
        lay.addWidget(log_scroll)

        lay.addSpacing(10)
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
        if not INSTALL_SRC.exists():
            self.install_btn.setEnabled(False)

        self.close_btn = QPushButton("Cancelar")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.hide()

        btn_row.addStretch()
        btn_row.addWidget(self.install_btn)
        btn_row.addWidget(self.close_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    # ── Download phase ─────────────────────────────────────────────────────────
    def _start_download(self):
        self._dl_lbl.setText("Descargando última versión de GitHub...")
        self._dl_bar.setValue(0)
        self._dl_worker = DownloadWorker()
        self._dl_worker.progress.connect(self._on_dl_progress)
        self._dl_worker.done.connect(self._on_dl_done)
        self._dl_worker.failed.connect(self._on_dl_failed)
        self._dl_worker.start()

    def _on_dl_progress(self, pct: int, msg: str):
        self._dl_bar.setValue(pct)
        self._dl_lbl.setText(msg)

    def _on_dl_done(self, extracted: str):
        self._src_dir = extracted
        self._dl_bar.setValue(100)
        self._dl_lbl.setText("✓ Descarga completa — listo para instalar")
        self._dl_lbl.setStyleSheet("color: #00ff88; font-size: 12px;")
        self.install_btn.setEnabled(True)

    def _on_dl_failed(self, err: str):
        self._dl_lbl.setText(f"✗ Error de descarga: {err}")
        self._dl_lbl.setStyleSheet("color: #ff4466; font-size: 12px;")
        self._dl_bar.setValue(0)
        self._add_log(f"Error: {err}", "err")

    # ── Install phase ──────────────────────────────────────────────────────────
    def _start_install(self):
        selected = [t for t in SECURITY_TOOLS
                    if self._tool_checks.get(t["id"], QCheckBox()).isChecked()]
        self.install_btn.setEnabled(False)
        self.install_btn.setText("⏳  Instalando...")
        self._worker = InstallWorker(self._src_dir, selected)
        self._worker.log.connect(lambda m, l: self._add_log(m, l))
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _add_log(self, msg: str, level: str):
        icon = "✓" if level == "ok" else "✗" if level == "err" else "·"
        lbl  = QLabel(f"  {icon}  {msg}")
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
            subprocess.Popen([str(exe)], creationflags=0x00000008)
        self.close()

    # ── Draggable ──────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


def main():
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
