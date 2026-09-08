# ui/amdata_tab.py
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QHeaderView, QLabel,
    QDialog, QFormLayout, QLineEdit, QDateEdit
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from models.amdata import BuildFile, PrinterInfo, MaterialInfo, CertificationInfo
from services.checksum_service import file_checksum


# Visible columns in the main table (source_path is stored in the model, not shown)
_HEADERS = [
    "ID", "File Name", "Format", "Size (bytes)", "File Type",
    "Machine Mfg", "Machine Model",
    "Material", "Grade",
    "Certified", "Cert Body", "Issue Date", "Expiry Date",
    "Checksum",
]


class AMDataTab(QWidget):
    files_changed = pyqtSignal()
    data_changed = pyqtSignal()   # emitted after any add / remove / edit

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Build files for prepared processes (G-code, AMF, 3MF, …)"))

        self._status_banner = QLabel()
        self._status_banner.setContentsMargins(8, 4, 8, 4)
        self._status_banner.setWordWrap(True)
        layout.addWidget(self._status_banner)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Build File")
        btn_add.clicked.connect(self._add)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, len(_HEADERS))
        self.table.setHorizontalHeaderLabels(_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._edit)
        layout.addWidget(self.table)

        self._files: list[BuildFile] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_build_required(self, required: bool) -> None:
        """Called by MainWindow when criticality >= High."""
        self._build_required = required
        self._update_banner()

    def has_errors(self) -> bool:
        """True when any build file has an expired certification."""
        return self._has_expired()

    def _has_expired(self) -> bool:
        today = QDate.currentDate()
        for bf in self._files:
            exp = QDate.fromString(bf.certification.expiry_date, "yyyy-MM-dd")
            if exp.isValid() and exp < today:
                return True
        return False

    def _update_banner(self) -> None:
        req  = getattr(self, '_build_required', False)
        n    = len(self._files)
        exp  = self._has_expired()

        if exp:
            self._status_banner.setText(
                "  ⚠  One or more build files have an expired certification. "
                "Please update or remove the affected files."
            )
            self._status_banner.setStyleSheet(
                "background:#fee2e2; color:#991b1b; border:1px solid #f87171;"
                "border-radius:4px; font-weight:bold;"
            )
        elif req and n == 0:
            self._status_banner.setText(
                "  ℹ  No build files added. At least one build file is "
                "recommended for High and Very High criticality packages."
            )
            self._status_banner.setStyleSheet(
                "background:#fef9c3; color:#854d0e; border:1px solid #fde047;"
                "border-radius:4px;"
            )
        else:
            self._status_banner.setText("")
            self._status_banner.setStyleSheet("")
        self.files_changed.emit()
        self.data_changed.emit()

    def get_data(self) -> list[BuildFile]:
        return list(self._files)

    def load_data(self, build_files: list[BuildFile]):
        self.table.setRowCount(0)
        self._files = []
        for bf in build_files:
            self._append_row(bf)
        self._update_banner()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _add(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Build File(s)", "", "Build Files (*.gcode *.amf *.3mf *.mbf *.cls)"
        )
        for path in paths:
            fname = os.path.basename(path)
            fmt = os.path.splitext(fname)[1].lstrip(".").upper()
            bf = BuildFile(
                id=f"BF-{len(self._files) + 1:03d}",
                file_name=fname,
                source_path=path,
                file_format=fmt,
                file_size=str(os.path.getsize(path)),
                checksum=file_checksum(path),
                file_type="AM Build File",
            )
            dlg = BuildFileDialog(bf, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                bf = dlg.get_data()
            self._append_row(bf)
        self._update_banner()

    def _remove(self):
        rows = sorted(
            {idx.row() for idx in self.table.selectionModel().selectedRows()},
            reverse=True,
        )
        if not rows:
            QMessageBox.information(self, "Remove", "Select at least one row first.")
            return
        for row in rows:
            self.table.removeRow(row)
            self._files.pop(row)
        self._renumber()
        self._update_banner()

    def _edit(self, item):
        row = item.row()
        dlg = BuildFileDialog(self._files[row], self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._files[row] = dlg.get_data()
            self._refresh_row(row)
            self._update_banner()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _append_row(self, bf: BuildFile):
        self._files.append(bf)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._refresh_row(row)

    def _refresh_row(self, row: int):
        bf = self._files[row]
        values = [
            bf.id, bf.file_name, bf.file_format, bf.file_size, bf.file_type,
            bf.printer.manufacturer, bf.printer.model,
            bf.material.name, bf.material.grade,
            bf.certification.certified, bf.certification.certification_body,
            bf.certification.issue_date, bf.certification.expiry_date,
            bf.checksum,
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)
        self._color_row(row)

    def _renumber(self):
        for i, bf in enumerate(self._files):
            bf.id = f"BF-{i + 1:03d}"
            item = self.table.item(i, 0)
            if item:
                item.setText(bf.id)

    def _color_row(self, row: int):
        bf = self._files[row]
        try:
            size_ok = int(bf.file_size) > 100
        except ValueError:
            size_ok = False

        machine_ok = bool(bf.printer.manufacturer and bf.printer.model)
        material_ok = bool(bf.material.name)

        cert = bf.certification
        cert_full = all([cert.certified, cert.certification_body, cert.certificate_id,
                         cert.issue_date, cert.expiry_date])
        cert_partial = any([cert.certified, cert.certification_body, cert.certificate_id])

        # Check expiry
        expired = False
        if cert.expiry_date:
            exp = QDate.fromString(cert.expiry_date, "yyyy-MM-dd")
            if exp.isValid() and exp < QDate.currentDate():
                expired = True

        if not size_ok or not machine_ok or not material_ok:
            color = QColor("#cccccc")       # grey — incomplete basics
        elif expired and cert_full:
            color = QColor("#ffcccc")       # red — certification expired
        elif cert_full:
            color = QColor("#ccffcc")       # green — fully certified
        elif cert_partial:
            color = QColor("#ffffcc")       # yellow — partially certified
        else:
            color = QColor("#ffffff")       # white — no cert, otherwise OK

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(color)


# ---------------------------------------------------------------------------
# Build File editor dialog
# ---------------------------------------------------------------------------
class BuildFileDialog(QDialog):
    def __init__(self, bf: BuildFile, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Build File")
        self.setMinimumWidth(480)
        self._original = bf

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.f_id = QLineEdit(bf.id)
        self.f_name = QLineEdit(bf.file_name)
        self.f_path = QLineEdit(bf.source_path)
        self.f_fmt = QLineEdit(bf.file_format)
        self.f_size = QLineEdit(bf.file_size)
        self.f_type = QLineEdit(bf.file_type)
        self.f_checksum = QLineEdit(bf.checksum)
        self.f_checksum.setReadOnly(True)

        form.addRow("ID:", self.f_id)
        form.addRow("File Name:", self.f_name)
        form.addRow("Source Path:", self.f_path)
        form.addRow("Format:", self.f_fmt)
        form.addRow("File Size:", self.f_size)
        form.addRow("File Type:", self.f_type)
        form.addRow("Checksum:", self.f_checksum)

        # Printer
        form.addRow(QLabel("— Machine Information —"))
        self.pr_mfg = QLineEdit(bf.printer.manufacturer)
        self.pr_model = QLineEdit(bf.printer.model)
        self.pr_sn = QLineEdit(bf.printer.serial_number)
        form.addRow("Manufacturer:", self.pr_mfg)
        form.addRow("Model:", self.pr_model)
        form.addRow("Serial Number:", self.pr_sn)

        # Material
        form.addRow(QLabel("— Material Information —"))
        self.mat_name = QLineEdit(bf.material.name)
        self.mat_grade = QLineEdit(bf.material.grade)
        self.mat_batch = QLineEdit(bf.material.batch_number)
        form.addRow("Material Name:", self.mat_name)
        form.addRow("Grade:", self.mat_grade)
        form.addRow("Batch Number:", self.mat_batch)

        # Certification
        form.addRow(QLabel("— Certification —"))
        self.cert_name = QLineEdit(bf.certification.certified)
        self.cert_body = QLineEdit(bf.certification.certification_body)
        self.cert_id = QLineEdit(bf.certification.certificate_id)

        def _make_date(val):
            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            d = QDate.fromString(val, "yyyy-MM-dd")
            de.setDate(d if d.isValid() else QDate.currentDate())
            return de

        self.cert_issue = _make_date(bf.certification.issue_date)
        self.cert_exp = _make_date(bf.certification.expiry_date)

        form.addRow("Certification Name:", self.cert_name)
        form.addRow("Certification Body:", self.cert_body)
        form.addRow("Certificate ID:", self.cert_id)
        form.addRow("Issue Date:", self.cert_issue)
        form.addRow("Expiry Date:", self.cert_exp)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def get_data(self) -> BuildFile:
        return BuildFile(
            id=self.f_id.text(),
            file_name=self.f_name.text(),
            source_path=self.f_path.text(),
            file_format=self.f_fmt.text(),
            file_size=self.f_size.text(),
            checksum=self.f_checksum.text(),
            file_type=self.f_type.text(),
            printer=PrinterInfo(
                manufacturer=self.pr_mfg.text(),
                model=self.pr_model.text(),
                serial_number=self.pr_sn.text(),
            ),
            material=MaterialInfo(
                name=self.mat_name.text(),
                grade=self.mat_grade.text(),
                batch_number=self.mat_batch.text(),
            ),
            certification=CertificationInfo(
                certified=self.cert_name.text(),
                certification_body=self.cert_body.text(),
                certificate_id=self.cert_id.text(),
                issue_date=self.cert_issue.date().toString("yyyy-MM-dd"),
                expiry_date=self.cert_exp.date().toString("yyyy-MM-dd"),
            ),
        )
