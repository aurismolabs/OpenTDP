# ui/optional_tab.py
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal

from models.optional import OptionalData, AdditionalCADModel, ReferenceImage
from services.checksum_service import file_checksum


class OptionalDataTab(QWidget):
    data_changed = pyqtSignal()
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Additional CAD / Project files"))
        layout.addLayout(self._btn_row("Add CAD File", self._add_cad, "Remove Selected", self._remove_cad))
        self.cad_table = self._make_table()
        layout.addWidget(self.cad_table)

        layout.addWidget(QLabel("Reference Images"))
        layout.addLayout(self._btn_row("Add Image", self._add_image, "Remove Selected", self._remove_image))
        self.img_table = self._make_table()
        layout.addWidget(self.img_table)

        self._cad_files: list[AdditionalCADModel] = []
        self._images: list[ReferenceImage] = []

    # ------------------------------------------------------------------
    def _make_table(self) -> QTableWidget:
        t = QTableWidget(0, 5)
        t.setHorizontalHeaderLabels(["File Name", "Format", "Size (bytes)", "Checksum", "Description"])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return t

    def _btn_row(self, add_label, add_slot, rem_label, rem_slot) -> QHBoxLayout:
        row = QHBoxLayout()
        btn_add = QPushButton(add_label)
        btn_add.clicked.connect(add_slot)
        btn_rem = QPushButton(rem_label)
        btn_rem.clicked.connect(rem_slot)
        row.addWidget(btn_add)
        row.addWidget(btn_rem)
        row.addStretch()
        return row

    def _set_row(self, table: QTableWidget, row: int, file_name, fmt, size, checksum, desc):
        for col, val in enumerate([file_name, fmt, size, checksum, desc]):
            item = QTableWidgetItem(str(val))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # CAD
    # ------------------------------------------------------------------
    def _add_cad(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select CAD File(s)", "", "CAD Files (*.stl *.step *.stp *.iges *.3mf)"
        )
        for path in paths:
            fname = os.path.basename(path)
            fmt = os.path.splitext(fname)[1].lstrip(".").upper()
            cad = AdditionalCADModel(
                file_name=fname, file_format=fmt,
                file_size=str(os.path.getsize(path)),
                checksum=file_checksum(path),
                description="", source_path=path,
            )
            self._cad_files.append(cad)
            row = self.cad_table.rowCount()
            self.cad_table.insertRow(row)
            self._set_row(self.cad_table, row, cad.file_name, cad.file_format,
                          cad.file_size, cad.checksum, cad.description)

    def _remove_cad(self):
        rows = sorted({i.row() for i in self.cad_table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.cad_table.removeRow(row)
            self._cad_files.pop(row)

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------
    def _add_image(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Image(s)", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        for path in paths:
            fname = os.path.basename(path)
            fmt = os.path.splitext(fname)[1].lstrip(".").upper()
            img = ReferenceImage(
                file_name=fname, file_format=fmt,
                file_size=str(os.path.getsize(path)),
                checksum=file_checksum(path),
                description="", source_path=path,
            )
            self._images.append(img)
            row = self.img_table.rowCount()
            self.img_table.insertRow(row)
            self._set_row(self.img_table, row, img.file_name, img.file_format,
                          img.file_size, img.checksum, img.description)

    def _remove_image(self):
        rows = sorted({i.row() for i in self.img_table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.img_table.removeRow(row)
            self._images.pop(row)

    # ------------------------------------------------------------------
    # Data I/O
    # ------------------------------------------------------------------
    def has_errors(self) -> bool:
        return False  # No required fields on this tab

    def get_data(self) -> OptionalData:
        return OptionalData(additional_cad=list(self._cad_files), images=list(self._images))

    def load_data(self, opt: OptionalData):
        self.cad_table.setRowCount(0)
        self._cad_files = []
        for cad in opt.additional_cad:
            self._cad_files.append(cad)
            row = self.cad_table.rowCount()
            self.cad_table.insertRow(row)
            self._set_row(self.cad_table, row, cad.file_name, cad.file_format,
                          cad.file_size, cad.checksum, cad.description)

        self.img_table.setRowCount(0)
        self._images = []
        for img in opt.images:
            self._images.append(img)
            row = self.img_table.rowCount()
            self.img_table.insertRow(row)
            self._set_row(self.img_table, row, img.file_name, img.file_format,
                          img.file_size, img.checksum, img.description)
