from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QLineEdit, QComboBox, QFrame, QSplitter, QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor


# ── RAG re-index worker ───────────────────────────────────────────────────
class ReindexWorker(QThread):
    done  = Signal(int)   # doc count
    error = Signal(str)

    def run(self):
        try:
            from app.rag.vectorstore import reset_index, _get_collection
            reset_index()
            col = _get_collection()
            self.done.emit(col.count() if col else 0)
        except Exception as e:
            self.error.emit(str(e))


class AddDocWorker(QThread):
    done  = Signal()
    error = Signal(str)

    def __init__(self, doc_id, title, content, platform):
        super().__init__()
        self.doc_id   = doc_id
        self.title    = title
        self.content  = content
        self.platform = platform

    def run(self):
        try:
            from app.rag.vectorstore import add_document
            add_document(self.doc_id, self.title, self.content, self.platform)
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))


# ── Helpers ───────────────────────────────────────────────────────────────
def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #1e2d3d; background: #1e2d3d; max-height: 1px;")
    return line


def _hdr(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #00d9ff; font-size: 12px; font-weight: bold; padding: 6px 0 2px;")
    return lbl


def _stat(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #4a5568; font-size: 11px; padding-bottom: 4px;")
    return lbl


# ══════════════════════════════════════════════════════════════════════════
# RAG PANEL
# ══════════════════════════════════════════════════════════════════════════
class RagPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build()
        self._refresh_stats()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        lay.addWidget(_hdr("🧠 RAG — Knowledge Base"))

        self.stat_lbl = _stat("Cargando...")
        lay.addWidget(self.stat_lbl)

        btn_row = QHBoxLayout()
        self.reindex_btn = QPushButton("🔄 Re-indexar base")
        self.reindex_btn.setStyleSheet(self._btn_style("#1e2d3d", "#00d9ff"))
        self.reindex_btn.clicked.connect(self._reindex)
        btn_row.addWidget(self.reindex_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addWidget(_sep())
        lay.addWidget(_hdr("➕ Añadir documento personalizado"))

        form_grid = QVBoxLayout()
        form_grid.setSpacing(4)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Título del documento")
        self.title_input.setStyleSheet(self._input_style())
        form_grid.addWidget(self.title_input)

        plat_row = QHBoxLayout()
        plat_lbl = QLabel("Plataforma:")
        plat_lbl.setStyleSheet("color: #4a5568; font-size: 11px;")
        self.plat_combo = QComboBox()
        self.plat_combo.addItems(["windows", "linux", "macos", "all"])
        self.plat_combo.setStyleSheet(self._combo_style())
        plat_row.addWidget(plat_lbl)
        plat_row.addWidget(self.plat_combo)
        plat_row.addStretch()
        form_grid.addLayout(plat_row)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Contenido del documento (comandos, notas técnicas, etc.)")
        self.content_input.setMaximumHeight(100)
        self.content_input.setStyleSheet(self._input_style())
        form_grid.addWidget(self.content_input)

        lay.addLayout(form_grid)

        add_btn = QPushButton("➕ Añadir al índice")
        add_btn.setStyleSheet(self._btn_style("#0d2a1a", "#00ff88"))
        add_btn.clicked.connect(self._add_doc)
        lay.addWidget(add_btn)

        self.msg_lbl = QLabel("")
        self.msg_lbl.setStyleSheet("color: #00ff88; font-size: 11px; padding: 2px 0;")
        lay.addWidget(self.msg_lbl)
        lay.addStretch()

    def _refresh_stats(self):
        try:
            from app.rag.vectorstore import _get_collection
            col = _get_collection()
            if col:
                n = col.count()
                self.stat_lbl.setText(f"{n} documentos indexados en ChromaDB")
            else:
                self.stat_lbl.setText("ChromaDB no disponible — instala: pip install chromadb sentence-transformers")
        except Exception as e:
            self.stat_lbl.setText(f"Error: {e}")

    def _reindex(self):
        self.reindex_btn.setEnabled(False)
        self.reindex_btn.setText("⏳ Indexando...")
        self.stat_lbl.setText("Re-indexando documentos...")
        self._worker = ReindexWorker()
        self._worker.done.connect(self._on_reindex_done)
        self._worker.error.connect(self._on_reindex_error)
        self._worker.start()

    def _on_reindex_done(self, count: int):
        self.reindex_btn.setEnabled(True)
        self.reindex_btn.setText("🔄 Re-indexar base")
        self.stat_lbl.setText(f"{count} documentos indexados en ChromaDB")
        self.msg_lbl.setText("✓ Re-índice completado")

    def _on_reindex_error(self, err: str):
        self.reindex_btn.setEnabled(True)
        self.reindex_btn.setText("🔄 Re-indexar base")
        self.msg_lbl.setStyleSheet("color: #ff4466; font-size: 11px;")
        self.msg_lbl.setText(f"Error: {err}")

    def _add_doc(self):
        title   = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        if not title or not content:
            self.msg_lbl.setStyleSheet("color: #ff4466; font-size: 11px;")
            self.msg_lbl.setText("Título y contenido son obligatorios")
            return
        platform = self.plat_combo.currentText()
        import hashlib, time
        doc_id = "custom_" + hashlib.md5(f"{title}{time.time()}".encode()).hexdigest()[:8]
        self._add_worker = AddDocWorker(doc_id, title, content, platform)
        self._add_worker.done.connect(self._on_add_done)
        self._add_worker.error.connect(lambda e: self.msg_lbl.setText(f"Error: {e}"))
        self._add_worker.start()

    def _on_add_done(self):
        self.title_input.clear()
        self.content_input.clear()
        self.msg_lbl.setStyleSheet("color: #00ff88; font-size: 11px;")
        self.msg_lbl.setText("✓ Documento añadido al índice")
        self._refresh_stats()

    @staticmethod
    def _btn_style(bg, border):
        return (
            f"QPushButton {{ background: {bg}; border: 1px solid {border}; border-radius: 5px;"
            f" color: {border}; padding: 5px 10px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(0,217,255,0.1); }}"
            f"QPushButton:disabled {{ color: #2a3a4a; border-color: #1e2d3d; background: transparent; }}"
        )

    @staticmethod
    def _input_style():
        return (
            "background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
            " color: #c9d1d9; padding: 5px 8px; font-size: 12px;"
        )

    @staticmethod
    def _combo_style():
        return (
            "QComboBox { background: #0d1117; border: 1px solid #1e2d3d; border-radius: 5px;"
            " color: #c9d1d9; padding: 4px 8px; font-size: 12px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #0d1117; color: #c9d1d9; "
            " border: 1px solid #1e2d3d; selection-background-color: #1e2d3d; }"
        )


# ══════════════════════════════════════════════════════════════════════════
# DECISION LOG PANEL
# ══════════════════════════════════════════════════════════════════════════
class DecisionLogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        hdr_row = QHBoxLayout()
        hdr_row.addWidget(_hdr("📊 Decision Log — herramientas usadas"))
        hdr_row.addStretch()

        _btn_style = (
            "QPushButton { background: transparent; border: 1px solid #1e2d3d;"
            " border-radius: 4px; color: #4a5568; font-size: 11px; padding: 0 6px; }"
            "QPushButton:hover { border-color: #00d9ff; color: #00d9ff; }"
        )

        csv_btn = QPushButton("📥 CSV")
        csv_btn.setFixedHeight(24)
        csv_btn.setToolTip("Exportar a CSV")
        csv_btn.setStyleSheet(_btn_style)
        csv_btn.clicked.connect(self._export_csv)
        hdr_row.addWidget(csv_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(28, 24)
        refresh_btn.setToolTip("Actualizar")
        refresh_btn.setStyleSheet(_btn_style)
        refresh_btn.clicked.connect(self.refresh)
        hdr_row.addWidget(refresh_btn)
        lay.addLayout(hdr_row)

        self.stat_lbl = _stat("")
        lay.addWidget(self.stat_lbl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Herramienta", "Args", "Resultado", "Estado", "Fecha"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0d1117; border: 1px solid #1e2d3d;
                border-radius: 6px; gridline-color: #1e2d3d;
                color: #c9d1d9; font-size: 11px;
            }
            QTableWidget::item { padding: 4px 6px; border: none; }
            QTableWidget::item:selected { background: #1e2d3d; }
            QHeaderView::section {
                background: #080c0f; color: #00d9ff;
                border: none; border-bottom: 1px solid #1e2d3d;
                padding: 4px 6px; font-size: 11px;
            }
        """)
        lay.addWidget(self.table)

    def refresh(self):
        try:
            from app.consciousness.decision_log import get_recent_decisions, get_stats
            import json as _json

            stats = get_stats()
            total     = stats.get("total", 0) or 0
            approved  = int(stats.get("approved") or 0)
            rejected  = int(stats.get("rejected") or 0)
            self.stat_lbl.setText(
                f"Total: {total}  |  ✓ Aprobadas: {approved}  |  ✗ Rechazadas: {rejected}"
            )

            rows = get_recent_decisions(limit=100)
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # Tool name
                self.table.setItem(i, 0, QTableWidgetItem(row.get("tool_name", "")))

                # Args preview
                try:
                    args = _json.loads(row.get("args_json") or "{}")
                    args_str = ", ".join(f"{k}={str(v)[:30]}" for k, v in args.items())
                except Exception:
                    args_str = str(row.get("args_json", ""))[:60]
                self.table.setItem(i, 1, QTableWidgetItem(args_str))

                # Result preview
                try:
                    res = _json.loads(row.get("result_json") or "{}")
                    if isinstance(res, dict):
                        out = res.get("stdout", res.get("output", str(res)))
                    else:
                        out = str(res)
                    res_str = str(out)[:80].replace("\n", " ")
                except Exception:
                    res_str = str(row.get("result_json", ""))[:80]
                self.table.setItem(i, 2, QTableWidgetItem(res_str))

                # Status
                approved_flag = row.get("approved", 0)
                status_item = QTableWidgetItem("✓" if approved_flag else "✗")
                status_item.setForeground(
                    QColor("#00ff88") if approved_flag else QColor("#ff4466")
                )
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, status_item)

                # Date
                ts = (row.get("created_at") or "")[:16]
                self.table.setItem(i, 4, QTableWidgetItem(ts))

            self.table.scrollToBottom()
        except Exception as e:
            self.stat_lbl.setText(f"Error cargando log: {e}")

    def _export_csv(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import csv, json as _json

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Decision Log", "decision_log.csv",
            "CSV (*.csv);;Todos (*)",
        )
        if not path:
            return
        try:
            from app.consciousness.decision_log import get_recent_decisions
            rows = get_recent_decisions(limit=10000)
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "tool_name", "args", "result", "approved", "created_at"])
                for r in rows:
                    try:
                        args = _json.loads(r.get("args_json") or "{}")
                        args_str = _json.dumps(args, ensure_ascii=False)
                    except Exception:
                        args_str = r.get("args_json", "")
                    try:
                        res = _json.loads(r.get("result_json") or "{}")
                        res_str = _json.dumps(res, ensure_ascii=False)
                    except Exception:
                        res_str = r.get("result_json", "")
                    w.writerow([
                        r.get("id"), r.get("tool_name"), args_str,
                        res_str, r.get("approved", 0), r.get("created_at", ""),
                    ])
            QMessageBox.information(self, "Exportado", f"{len(rows)} entradas → {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ══════════════════════════════════════════════════════════════════════════
# AGENT PANEL (contenedor principal — pestaña "Agente")
# ══════════════════════════════════════════════════════════════════════════
class AgentPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: #1e2d3d; height: 2px; }")

        self.rag_panel = RagPanel()
        self.log_panel = DecisionLogPanel()

        splitter.addWidget(self.rag_panel)
        splitter.addWidget(self.log_panel)
        splitter.setSizes([320, 500])

        lay.addWidget(splitter)

    def refresh_log(self):
        self.log_panel.refresh()
