# ui/version_tab.py
import uuid
import json
import hashlib

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QListWidget, QListWidgetItem,
    QHBoxLayout, QTextEdit, QDateTimeEdit, QLabel
)
from PyQt6.QtCore import QDateTime

from models.version import VersionInfo, ChangeEntry
from ui.field_state import apply_state, clear_state, REQUIRED_EMPTY, REQUIRED_FILLED


class VersionTab(QWidget):
    data_changed = pyqtSignal()
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow

        layout = QVBoxLayout(self)
        layout.addWidget(self._version_group())
        layout.addWidget(self._encryption_group())
        layout.addWidget(self._history_group())
        layout.addStretch()
        self.setLayout(layout)
        self._refresh_states()
        self._connect_change_signals()   # show state immediately on startup

    # ------------------------------------------------------------------
    # UI GROUPS
    # ------------------------------------------------------------------
    def _version_group(self):
        group = QGroupBox("Version Control")
        form = QFormLayout()

        self.unique_id = QLineEdit(str(uuid.uuid4()))
        btn_uid = QPushButton("Generate New")
        btn_uid.clicked.connect(lambda: self.unique_id.setText(str(uuid.uuid4())))
        uid_row = QHBoxLayout()
        uid_row.addWidget(btn_uid)
        uid_row.addWidget(self.unique_id)

        self.assembly_id = QLineEdit()

        self.revision = QLineEdit()
        btn_rev = QPushButton("Stamp Now")
        btn_rev.clicked.connect(
            lambda: self.revision.setText(QDateTime.currentDateTime().toString("yyyyMMddHHmmss"))
        )
        rev_row = QHBoxLayout()
        rev_row.addWidget(btn_rev)
        rev_row.addWidget(self.revision)

        self.checksum = QLineEdit()
        self.checksum.setReadOnly(True)
        self.checksum.setPlaceholderText("Computed automatically on save")
        btn_cs = QPushButton("Preview")
        btn_cs.clicked.connect(self._preview_checksum)
        cs_row = QHBoxLayout()
        cs_row.addWidget(btn_cs)
        cs_row.addWidget(self.checksum)

        self.signature = QLineEdit()
        self.revision.textChanged.connect(self._refresh_states)
        self.unique_id.textChanged.connect(self._refresh_states)

        form.addRow("Unique ID:", uid_row)
        form.addRow("Assembly ID:", self.assembly_id)
        form.addRow("Revision Timestamp:", rev_row)
        form.addRow("Package Checksum:", cs_row)
        form.addRow("Signature (RSA2048):", self.signature)
        group.setLayout(form)
        return group

    def _encryption_group(self):
        group = QGroupBox("Encryption")
        form = QFormLayout()
        self.encryption_enabled = QCheckBox("Enable Encryption")
        self.encryption_algorithm = QComboBox()
        self.encryption_algorithm.addItems(["", "AES-256", "Fernet", "RSA2048"])
        self.encryption_algorithm.wheelEvent = lambda e: e.ignore()
        form.addRow(self.encryption_enabled)
        form.addRow("Algorithm:", self.encryption_algorithm)
        group.setLayout(form)
        return group

    def _history_group(self):
        group = QGroupBox("Change History (automatic on save — manual entries also allowed)")
        layout = QVBoxLayout()

        self.change_list = QListWidget()
        layout.addWidget(self.change_list)

        btn_add = QPushButton("Add Manual Entry")
        btn_add.clicked.connect(self._open_manual_entry)
        btn_del = QPushButton("Remove Selected")
        btn_del.clicked.connect(self._remove_entry)
        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)

        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _preview_checksum(self):
        try:
            package = self.mainwindow.collect_package()
            package.version.checksum = ""
            xml_str = __import__("services.xml_serializer", fromlist=["to_xml_string"]).to_xml_string(package)
            sha = hashlib.sha256(xml_str.encode("utf-8")).hexdigest()
            self.checksum.setText(sha)
        except Exception as exc:
            self.checksum.setText(f"Error: {exc}")

    def _open_manual_entry(self):
        editor = _ChangeEntryEditor(self)
        editor.show()

    def _remove_entry(self):
        row = self.change_list.currentRow()
        if row >= 0:
            self.change_list.takeItem(row)

    def add_change_entry_to_list(self, entry: ChangeEntry):
        text = (
            f"[{entry.timestamp}]  {entry.change_id}\n"
            f"Author: {entry.author}\n"
            f"{entry.description}"
        )
        self.change_list.addItem(QListWidgetItem(text))

    # ------------------------------------------------------------------
    # DATA I/O
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Field-state highlighting
    # ------------------------------------------------------------------
    def has_errors(self) -> bool:
        """True if Unique ID is empty, or revision required (Approved+) but empty."""
        if not self.unique_id.text().strip():
            return True
        if getattr(self, '_revision_required', False):
            return not self.revision.text().strip()
        return False

    def set_revision_required(self, required: bool) -> None:
        """Called by MainWindow when lifecycle = Released."""
        self._revision_required = required
        self._refresh_states()

    def _refresh_states(self):
        # Unique ID: always required in all cases
        uid_ok = bool(self.unique_id.text().strip())
        apply_state(self.unique_id, REQUIRED_FILLED if uid_ok else REQUIRED_EMPTY)

        # Revision Timestamp: required when lifecycle >= Approved
        rev_req = getattr(self, '_revision_required', False)
        if rev_req:
            rev_ok = bool(self.revision.text().strip())
            apply_state(self.revision, REQUIRED_FILLED if rev_ok else REQUIRED_EMPTY)
        else:
            clear_state(self.revision)  # no colour — not required

    def get_data(self) -> VersionInfo:
        history = []
        for i in range(self.change_list.count()):
            lines = self.change_list.item(i).text().splitlines()
            # Parse back the stored text
            header = lines[0] if len(lines) > 0 else ""
            author_line = lines[1] if len(lines) > 1 else ""
            desc = lines[2] if len(lines) > 2 else ""
            # Extract ID and timestamp from header "[timestamp]  change_id"
            import re
            m = re.match(r"\[(.+?)\]\s+(.+)", header)
            ts = m.group(1) if m else ""
            ch_id = m.group(2) if m else ""
            author = author_line.replace("Author: ", "")
            history.append(ChangeEntry(change_id=ch_id, timestamp=ts, author=author, description=desc))

        return VersionInfo(
            unique_id=self.unique_id.text(),
            assembly_id=self.assembly_id.text(),
            revision=self.revision.text(),
            checksum=self.checksum.text(),
            signature=self.signature.text(),
            encryption_enabled=self.encryption_enabled.isChecked(),
            encryption_algorithm=self.encryption_algorithm.currentText(),
            change_history=history,
        )

    def load_data(self, v: VersionInfo):
        self.unique_id.setText(v.unique_id)
        self.assembly_id.setText(v.assembly_id)
        self.revision.setText(v.revision)
        self.checksum.setText(v.checksum)
        self.signature.setText(v.signature)
        self.encryption_enabled.setChecked(v.encryption_enabled)
        self.encryption_algorithm.setCurrentText(v.encryption_algorithm)
        self.change_list.clear()
        for entry in v.change_history:
            self.add_change_entry_to_list(entry)
        self._refresh_states()

    def _connect_change_signals(self):
        for sig in [
            self.unique_id.textChanged,
            self.revision.textChanged,
        ]:
            sig.connect(self.data_changed)


# -------------------------------------------------------------------------
# Manual change entry editor
# -------------------------------------------------------------------------
class _ChangeEntryEditor(QWidget):
    def __init__(self, parent_tab: VersionTab):
        super().__init__()
        self.parent_tab = parent_tab
        self.setWindowTitle("Add Change Entry")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        self.change_id = QLineEdit(f"CH-{uuid.uuid4().hex[:6].upper()}")
        self.timestamp = QDateTimeEdit(QDateTime.currentDateTime())
        self.timestamp.setCalendarPopup(True)
        self.author = QLineEdit()
        self.description = QTextEdit()

        btn = QPushButton("Add")
        btn.clicked.connect(self._save)

        layout.addRow("Change ID:", self.change_id)
        layout.addRow("Timestamp:", self.timestamp)
        layout.addRow("Author:", self.author)
        layout.addRow("Description:", self.description)
        layout.addRow(btn)

    def _save(self):
        entry = ChangeEntry(
            change_id=self.change_id.text(),
            timestamp=self.timestamp.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            author=self.author.text(),
            description=self.description.toPlainText(),
        )
        self.parent_tab.add_change_entry_to_list(entry)
        self.close()
