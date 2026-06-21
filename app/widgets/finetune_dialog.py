import os, sys, subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QFileDialog,
    QComboBox, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, QProcess

_FT_DEPS = ["unsloth", "trl", "peft", "accelerate", "datasets", "bitsandbytes"]
_FT_PIP  = ["unsloth[colab-new]", "trl", "peft", "accelerate", "datasets", "bitsandbytes"]


def _ft_deps_installed() -> bool:
    for pkg in _FT_DEPS:
        try:
            __import__(pkg)
        except ImportError:
            return False
    return True


class DepsInstallWorker(QThread):
    log    = Signal(str)
    done   = Signal()
    failed = Signal(str)

    def run(self):
        cmd = [sys.executable, "-m", "pip", "install"] + _FT_PIP + ["--quiet", "--progress-bar", "off"]
        self.log.emit(f"Instalando: {' '.join(_FT_PIP)}\n\n")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for line in proc.stdout:
                self.log.emit(line)
            proc.wait()
            if proc.returncode == 0:
                self.done.emit()
            else:
                self.failed.emit(f"pip salió con código {proc.returncode}")
        except Exception as e:
            self.failed.emit(str(e))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data")

MODELS = [
    "unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
    "unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
    "unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
    "unsloth/Qwen2.5-Coder-3B-Instruct-bnb-4bit",
]

_STYLE_INPUT = (
    "background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
    " color: #c9d1d9; padding: 5px 8px; font-size: 12px;"
)
_STYLE_BTN = (
    "QPushButton { background: #0d1a2d; border: 1px solid #00d9ff; border-radius: 5px;"
    " color: #00d9ff; padding: 6px 14px; font-size: 12px; }"
    "QPushButton:hover { background: rgba(0,217,255,0.1); }"
    "QPushButton:disabled { color: #2a3a4a; border-color: #1e2d3d; background: transparent; }"
)
_STYLE_LOG = (
    "background: #080c0f; border: 1px solid #1e2d3d; border-radius: 5px;"
    " color: #00ff88; font-family: monospace; font-size: 11px; padding: 4px;"
)


def _lbl(text):
    l = QLabel(text)
    l.setStyleSheet("color: #4a5568; font-size: 11px;")
    return l


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color: #1e2d3d; background: #1e2d3d; max-height: 1px; margin: 4px 0;")
    return f


class TrainWorker(QThread):
    log    = Signal(str)
    done   = Signal(str)   # output path
    failed = Signal(str)

    def __init__(self, jsonl, output, model, epochs, batch, lr):
        super().__init__()
        self.jsonl  = jsonl
        self.output = output
        self.model  = model
        self.epochs = epochs
        self.batch  = batch
        self.lr     = lr

    def run(self):
        train_script = os.path.join(os.path.dirname(__file__), "..", "finetune", "train.py")
        cmd = [
            sys.executable, train_script,
            "--jsonl",      self.jsonl,
            "--output",     self.output,
            "--model",      self.model,
            "--epochs",     str(self.epochs),
            "--batch-size", str(self.batch),
            "--lr",         str(self.lr),
        ]
        proc = QProcess()
        proc.setProcessChannelMode(QProcess.MergedChannels)

        all_out = []

        def on_data():
            data = proc.readAll().data().decode("utf-8", errors="replace")
            all_out.append(data)
            self.log.emit(data)

        proc.readyRead.connect(on_data)
        proc.start(cmd[0], cmd[1:])
        proc.waitForFinished(-1)

        exit_code = proc.exitCode()
        full_out  = "".join(all_out)
        if exit_code == 0:
            self.done.emit(full_out)
        else:
            self.failed.emit(full_out)


class FineTuneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎓 Fine-tuning QLoRA")
        self.setMinimumSize(640, 640)
        self.setStyleSheet(
            "QDialog { background: #080c0f; color: #c9d1d9; font-family: monospace; }"
        )
        self._worker     = None
        self._deps_worker = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("🎓 Fine-tuning QLoRA — CyberAgent")
        title.setStyleSheet("color: #00d9ff; font-size: 14px; font-weight: bold; padding-bottom: 4px;")
        lay.addWidget(title)

        # ── Dependencias ───────────────────────────────────────────────
        self._deps_banner = QFrame()
        self._deps_banner.setStyleSheet(
            "QFrame { background: #1a0f00; border: 1px solid #ffd700;"
            " border-radius: 6px; padding: 4px; }"
        )
        deps_lay = QHBoxLayout(self._deps_banner)
        deps_lay.setContentsMargins(10, 6, 10, 6)

        self._deps_lbl = QLabel(
            "⚠️  Dependencias de entrenamiento no instaladas  "
            "(unsloth, trl, peft, accelerate, datasets, bitsandbytes)\n"
            "    GPU VRAM necesaria: ~10 GB para modelos 7B · Tiempo estimado de instalación: 5-15 min"
        )
        self._deps_lbl.setStyleSheet("color: #ffd700; font-size: 11px;")
        self._deps_lbl.setWordWrap(True)
        deps_lay.addWidget(self._deps_lbl, 1)

        self._install_btn = QPushButton("📦 Instalar ahora")
        self._install_btn.setStyleSheet(
            "QPushButton { background: #2a1a00; border: 1px solid #ffd700; border-radius: 5px;"
            " color: #ffd700; padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,215,0,0.12); }"
            "QPushButton:disabled { color: #4a3a00; border-color: #2a1a00; }"
        )
        self._install_btn.clicked.connect(self._install_deps)
        deps_lay.addWidget(self._install_btn)

        lay.addWidget(self._deps_banner)
        self._deps_banner.setVisible(not _ft_deps_installed())

        lay.addWidget(_sep())

        # JSONL path
        lay.addWidget(_lbl("Archivo JSONL de entrenamiento:"))
        jsonl_row = QHBoxLayout()
        self.jsonl_input = QLineEdit()
        self.jsonl_input.setPlaceholderText("data/finetune_xxx.jsonl")
        self.jsonl_input.setStyleSheet(_STYLE_INPUT)
        jsonl_row.addWidget(self.jsonl_input)
        browse_btn = QPushButton("📂")
        browse_btn.setFixedWidth(36)
        browse_btn.setStyleSheet(_STYLE_BTN)
        browse_btn.clicked.connect(self._browse_jsonl)
        jsonl_row.addWidget(browse_btn)
        lay.addLayout(jsonl_row)

        # Auto-fill last export
        last = self._find_last_jsonl()
        if last:
            self.jsonl_input.setText(last)

        # Output dir
        lay.addWidget(_lbl("Directorio de salida:"))
        self.output_input = QLineEdit(os.path.join(DATA_DIR, "ft_out"))
        self.output_input.setStyleSheet(_STYLE_INPUT)
        lay.addWidget(self.output_input)

        # Model
        lay.addWidget(_lbl("Modelo base (HuggingFace):"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.model_combo.setEditable(True)
        self.model_combo.setStyleSheet(
            "QComboBox { background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
            " color: #c9d1d9; padding: 5px 8px; font-size: 12px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #0d1117; color: #c9d1d9;"
            " border: 1px solid #1e2d3d; selection-background-color: #1e2d3d; }"
        )
        lay.addWidget(self.model_combo)

        # Hyperparams
        lay.addWidget(_lbl("Hiperparámetros:"))
        hp_row = QHBoxLayout()
        hp_row.setSpacing(12)

        hp_row.addWidget(QLabel("Épocas:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 20)
        self.epochs_spin.setValue(1)
        self.epochs_spin.setStyleSheet(_STYLE_INPUT + " max-width: 60px;")
        hp_row.addWidget(self.epochs_spin)

        hp_row.addWidget(QLabel("Batch:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 16)
        self.batch_spin.setValue(2)
        self.batch_spin.setStyleSheet(_STYLE_INPUT + " max-width: 60px;")
        hp_row.addWidget(self.batch_spin)

        hp_row.addWidget(QLabel("LR:"))
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(1e-6, 1e-2)
        self.lr_spin.setValue(2e-4)
        self.lr_spin.setDecimals(6)
        self.lr_spin.setSingleStep(1e-5)
        self.lr_spin.setStyleSheet(_STYLE_INPUT + " max-width: 90px;")
        hp_row.addWidget(self.lr_spin)
        hp_row.addStretch()
        lay.addLayout(hp_row)

        lay.addWidget(_sep())

        # Log output
        lay.addWidget(_lbl("Log de entrenamiento:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(_STYLE_LOG)
        self.log_box.setMinimumHeight(180)
        lay.addWidget(self.log_box)

        # Buttons
        btn_row = QHBoxLayout()
        self.train_btn = QPushButton("🚀 Iniciar entrenamiento")
        self.train_btn.setStyleSheet(_STYLE_BTN)
        self.train_btn.clicked.connect(self._start_train)
        btn_row.addWidget(self.train_btn)

        self.stop_btn = QPushButton("■ Detener")
        self.stop_btn.setStyleSheet(
            "QPushButton { background: #1a0d0d; border: 1px solid #ff4466; border-radius: 5px;"
            " color: #ff4466; padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,68,102,0.1); }"
        )
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_train)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #1e2d3d; border-radius: 5px;"
            " color: #4a5568; padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { border-color: #4a5568; color: #c9d1d9; }"
        )
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        lay.addLayout(btn_row)

    def _browse_jsonl(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar JSONL", DATA_DIR, "JSONL Files (*.jsonl);;All Files (*)"
        )
        if path:
            self.jsonl_input.setText(path)

    def _find_last_jsonl(self) -> str:
        if not os.path.isdir(DATA_DIR):
            return ""
        files = sorted(
            (f for f in os.listdir(DATA_DIR) if f.startswith("finetune_") and f.endswith(".jsonl")),
            reverse=True,
        )
        return os.path.join(DATA_DIR, files[0]) if files else ""

    def _start_train(self):
        jsonl  = self.jsonl_input.text().strip()
        output = self.output_input.text().strip()
        if not jsonl or not os.path.isfile(jsonl):
            self.log_box.append("[ERROR] Archivo JSONL no encontrado")
            return

        self.log_box.clear()
        self.log_box.append(f"[start] {jsonl}")
        self.train_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self._worker = TrainWorker(
            jsonl   = jsonl,
            output  = output,
            model   = self.model_combo.currentText(),
            epochs  = self.epochs_spin.value(),
            batch   = self.batch_spin.value(),
            lr      = self.lr_spin.value(),
        )
        self._worker.log.connect(self._on_log)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _stop_train(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self.log_box.append("\n[DETENIDO por el usuario]")
        self._reset_btns()

    def _on_log(self, text: str):
        self.log_box.insertPlainText(text)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    def _on_done(self, out: str):
        self.log_box.append("\n✓ Entrenamiento completado.")
        self.log_box.append("Importa a Ollama con el comando mostrado arriba.")
        self._reset_btns()

    def _on_failed(self, out: str):
        self.log_box.append("\n[ERROR] El entrenamiento falló.")
        self._reset_btns()

    def _reset_btns(self):
        self.train_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ── Instalación de dependencias ────────────────────────────────────────
    def _install_deps(self):
        self._install_btn.setEnabled(False)
        self._install_btn.setText("⏳ Instalando...")
        self._deps_lbl.setText("Instalando dependencias de entrenamiento — esto puede tardar varios minutos...")
        self.log_box.clear()
        self.log_box.append("📦 Instalando: unsloth trl peft accelerate datasets bitsandbytes\n")
        self._deps_worker = DepsInstallWorker()
        self._deps_worker.log.connect(self._on_log)
        self._deps_worker.done.connect(self._on_deps_done)
        self._deps_worker.failed.connect(self._on_deps_failed)
        self._deps_worker.start()

    def _on_deps_done(self):
        self.log_box.append("\n✓ Dependencias instaladas correctamente.")
        self._deps_banner.setVisible(False)

    def _on_deps_failed(self, err: str):
        self.log_box.append(f"\n[ERROR] {err}")
        self._deps_lbl.setText("⚠️  La instalación falló — revisa el log")
        self._install_btn.setEnabled(True)
        self._install_btn.setText("📦 Reintentar")
