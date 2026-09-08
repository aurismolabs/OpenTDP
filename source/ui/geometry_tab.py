# ui/geometry_tab.py
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QHeaderView, QLabel,
    QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal

from models.geometry import Geometry
from services.checksum_service import file_checksum
from services.geometry_inspector import get_dimensions
from ui.field_state import REQUIRED_EMPTY, REQUIRED_FILLED

# Supported mesh formats — extend here as trimesh support grows
SUPPORTED_FORMATS = "Geometry Files — STL, 3MF (*.stl *.3mf)"

_FORMAT_NOTE = (
    "Geometry files — accepted formats: STL, 3MF  "
    "(open triangle-mesh models; STEP, IGES and OBJ are not accepted)  —  "
    "required when lifecycle status is In Review or later"
)


class GeometryTab(QWidget):
    # Emitted when the preview-selected geometry changes
    preview_changed = pyqtSignal(str)
    data_changed = pyqtSignal()   # source_path

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_FORMAT_NOTE))

        self._status_banner = QLabel()
        self._status_banner.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(self._status_banner)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Geometry")
        btn_add.clicked.connect(self._add)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Columns: ID | FileName | FileFormat | FileSize | Checksum | Dimensions | Preview
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "File Name", "Format", "Size (bytes)", "Checksum", "Dimensions", "Preview"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self._geometries: list[Geometry] = []
        self._preview_group = QButtonGroup(self)
        self._preview_group.setExclusive(True)

    # ------------------------------------------------------------------
    # Status banner
    # ------------------------------------------------------------------
    def has_errors(self) -> bool:
        """True if geometry is required but list is empty or has invalid formats."""
        if not getattr(self, '_geometry_required', False):
            return False
        return self.table.rowCount() == 0

    def refresh_banner(self, required: bool) -> None:
        """Update the geometry status banner. Called by MainWindow."""
        self._geometry_required = required
        self._update_banner()

    def _update_banner(self) -> None:
        req = getattr(self, '_geometry_required', False)
        count = self.table.rowCount()
        if not req:
            self._status_banner.setText("")
            self._status_banner.setStyleSheet("")
        elif count == 0:
            self._status_banner.setText(
                "  ⚠  At least one geometry file is required (STL or 3MF)")
            self._status_banner.setStyleSheet(REQUIRED_EMPTY +
                "color: #b91c1c; font-weight: bold;")
        else:
            self._status_banner.setText(
                f"  ✓  {count} geometry file{'s' if count > 1 else ''}")
            self._status_banner.setStyleSheet(REQUIRED_FILLED +
                "color: #166534; font-weight: bold;")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_data(self) -> list[Geometry]:
        result = []
        for row, g in enumerate(self._geometries):
            radio = self.table.cellWidget(row, 6)
            g.preview = radio.isChecked() if radio else False
            result.append(g)
        return result

    def load_data(self, geometries: list[Geometry]):
        self.table.setRowCount(0)
        self._geometries = []
        for btn in self._preview_group.buttons():
            self._preview_group.removeButton(btn)
        for g in geometries:
            self._append_row(g)
        self._update_banner()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _add(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Geometry File(s)", "", SUPPORTED_FORMATS
        )
        for path in paths:
            g = self._build_geometry(path, row_index=len(self._geometries))
            self._append_row(g)

    def _remove(self):
        rows = sorted(
            {idx.row() for idx in self.table.selectionModel().selectedRows()},
            reverse=True,
        )
        if not rows:
            QMessageBox.information(self, "Remove", "Select at least one row first.")
            return
        for row in rows:
            btn = self.table.cellWidget(row, 6)
            if btn:
                self._preview_group.removeButton(btn)
            self.table.removeRow(row)
            self._geometries.pop(row)
        self._renumber()
        self._update_banner()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_geometry(self, path: str, row_index: int) -> Geometry:
        fname = os.path.basename(path)
        fmt = os.path.splitext(fname)[1].lstrip(".").upper()
        size = str(os.path.getsize(path))
        checksum = file_checksum(path)
        dims = get_dimensions(path)
        return Geometry(
            id=f"G{row_index + 1:03d}",
            file_name=fname,
            source_path=path,
            file_format=fmt,
            file_size=size,
            checksum=checksum,
            dimensions=dims,
            preview=False,
        )

    def _append_row(self, g: Geometry):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._geometries.append(g)
        self._fill_row(row, g)
        self._color_row(row)
        self._update_banner()

    def _fill_row(self, row: int, g: Geometry):
        for col, value in enumerate([
            g.id, g.file_name, g.file_format, g.file_size, g.checksum, g.dimensions
        ]):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)

        radio = QRadioButton()
        radio.setChecked(g.preview)
        radio.toggled.connect(lambda checked, p=g.source_path: self._on_preview(checked, p))
        self._preview_group.addButton(radio)
        self.table.setCellWidget(row, 6, radio)

    def _on_preview(self, checked: bool, path: str):
        if checked:
            self.preview_changed.emit(path)

    def _renumber(self):
        for row, g in enumerate(self._geometries):
            g.id = f"G{row + 1:03d}"
            item = self.table.item(row, 0)
            if item:
                item.setText(g.id)

    def _color_row(self, row: int):
        g = self._geometries[row]
        try:
            size_ok = int(g.file_size) > 100
        except ValueError:
            size_ok = False
        dims_ok = bool(g.dimensions)

        if not size_ok:
            color = QColor("#cccccc")
        elif not dims_ok:
            color = QColor("#ffcccc")
        else:
            color = QColor("#ffffff")

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(color)
