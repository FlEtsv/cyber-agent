from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.tools import get_tool_catalog


CATEGORY_LABELS = {
    "core": "Core",
    "web": "Web",
    "files": "Archivos",
    "system": "Sistema",
    "desktop": "Desktop",
    "network": "Red",
    "forensics": "Forense",
    "encode": "Encode",
    "rag": "RAG",
    "self": "Agente",
    "mobile": "Movil",
    "other": "Otros",
}


class ToolsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tools_catalog_page")
        self._catalog = sorted(
            get_tool_catalog(),
            key=lambda row: (row.get("category", "other"), row.get("name", "")),
        )
        self._filtered: list[dict] = []
        self._build()
        self._populate_filters()
        self._apply_filter()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)

        header = QWidget()
        header.setObjectName("tools_catalog_header")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(0, 0, 0, 0)
        header_lay.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title = QLabel("Catalogo de herramientas")
        title.setObjectName("tools_catalog_title")
        subtitle = QLabel("Categorias, riesgo, permiso por defecto y uso operativo")
        subtitle.setObjectName("tools_catalog_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_lay.addLayout(title_box, 1)

        self.manual_btn = QPushButton("Abrir manual")
        self.manual_btn.setObjectName("tools_manual_btn")
        self.manual_btn.clicked.connect(self._open_manual)
        header_lay.addWidget(self.manual_btn)
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("tools_catalog_controls")
        controls_lay = QHBoxLayout(controls)
        controls_lay.setContentsMargins(0, 0, 0, 0)
        controls_lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setObjectName("tools_search")
        self.search.setPlaceholderText("Filtrar por nombre, categoria o descripcion...")
        self.search.textChanged.connect(self._apply_filter)
        controls_lay.addWidget(self.search, 1)

        self.category = QComboBox()
        self.category.setObjectName("tools_filter_combo")
        self.category.currentIndexChanged.connect(self._apply_filter)
        controls_lay.addWidget(self.category)

        self.risk = QComboBox()
        self.risk.setObjectName("tools_filter_combo")
        self.risk.addItem("Todos los riesgos", "")
        self.risk.addItem("Riesgo alto", "high")
        self.risk.addItem("Riesgo bajo", "low")
        self.risk.currentIndexChanged.connect(self._apply_filter)
        controls_lay.addWidget(self.risk)
        root.addWidget(controls)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        self.list = QListWidget()
        self.list.setObjectName("tools_list")
        self.list.currentItemChanged.connect(self._show_detail)
        body.addWidget(self.list, 2)

        detail = QFrame()
        detail.setObjectName("tools_detail")
        detail_lay = QVBoxLayout(detail)
        detail_lay.setContentsMargins(14, 14, 14, 14)
        detail_lay.setSpacing(10)

        self.detail_name = QLabel("Selecciona una herramienta")
        self.detail_name.setObjectName("tools_detail_name")
        self.detail_name.setWordWrap(True)
        detail_lay.addWidget(self.detail_name)

        self.badges = QLabel("")
        self.badges.setObjectName("tools_detail_badges")
        self.badges.setTextFormat(Qt.RichText)
        self.badges.setWordWrap(True)
        detail_lay.addWidget(self.badges)

        self.detail_guide = QLabel("")
        self.detail_guide.setObjectName("tools_detail_guide")
        self.detail_guide.setWordWrap(True)
        detail_lay.addWidget(self.detail_guide)

        self.detail_desc = QTextEdit()
        self.detail_desc.setObjectName("tools_detail_desc")
        self.detail_desc.setReadOnly(True)
        detail_lay.addWidget(self.detail_desc, 1)

        body.addWidget(detail, 3)
        root.addLayout(body, 1)

        self.summary = QLabel("")
        self.summary.setObjectName("tools_catalog_summary")
        root.addWidget(self.summary)

    def _populate_filters(self):
        self.category.addItem("Todas las categorias", "")
        categories = sorted({row.get("category", "other") for row in self._catalog})
        for category in categories:
            self.category.addItem(CATEGORY_LABELS.get(category, category.title()), category)

    def _apply_filter(self):
        text = self.search.text().strip().lower()
        category = self.category.currentData()
        risk = self.risk.currentData()

        self.list.clear()
        self._filtered = []
        for row in self._catalog:
            haystack = " ".join(
                str(row.get(key, ""))
                for key in ("name", "category", "risk", "guide", "description")
            ).lower()
            if text and text not in haystack:
                continue
            if category and row.get("category") != category:
                continue
            if risk and row.get("risk") != risk:
                continue
            self._filtered.append(row)
            self._add_item(row)

        total = len(self._catalog)
        high = sum(1 for row in self._filtered if row.get("risk") == "high")
        self.summary.setText(
            f"{len(self._filtered)} de {total} herramientas visibles | {high} riesgo alto"
        )
        if self.list.count():
            self.list.setCurrentRow(0)
        else:
            self._clear_detail()

    def _add_item(self, row: dict):
        category = CATEGORY_LABELS.get(row.get("category"), row.get("category", "other"))
        risk = "ALTO" if row.get("risk") == "high" else "BAJO"
        item = QListWidgetItem(f"{row['name']}   [{category} | {risk}]")
        item.setData(Qt.UserRole, row)
        self.list.addItem(item)

    def _show_detail(self, current: QListWidgetItem, _previous: QListWidgetItem):
        if not current:
            self._clear_detail()
            return
        row = current.data(Qt.UserRole)
        category = CATEGORY_LABELS.get(row.get("category"), row.get("category", "other"))
        risk = "ALTO" if row.get("risk") == "high" else "BAJO"
        permission = row.get("default_permission", "ask")

        self.detail_name.setText(row.get("name", ""))
        risk_color = "#f85149" if row.get("risk") == "high" else "#3fb950"
        self.badges.setText(
            f"<span style='color:#8ce8f1'>{category}</span>"
            f"  <span style='color:{risk_color}'>{risk}</span>"
            f"  <span style='color:#8f9aa8'>permiso: {permission}</span>"
        )
        self.detail_guide.setText(row.get("guide", ""))
        self.detail_desc.setPlainText(row.get("description", ""))

    def _clear_detail(self):
        self.detail_name.setText("Sin resultados")
        self.badges.setText("")
        self.detail_guide.setText("Ajusta los filtros para ver herramientas.")
        self.detail_desc.clear()

    def _open_manual(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        preferred = os.path.join(root, "docs", "TOOLS_MANUAL.md")
        fallback = os.path.join(root, "docs", "TOOLS.md")
        target = preferred if os.path.exists(preferred) else fallback
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))
