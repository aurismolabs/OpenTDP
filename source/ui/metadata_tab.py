# ui/metadata_tab.py
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QHBoxLayout, QVBoxLayout, QFrame,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QLabel, QSizePolicy
)
from PyQt6.QtCore import QDate, Qt

from models.metadata import Metadata
from ui.widgets.three_d_viewer import ThreeDViewer
from ui.field_state import update_states, clear_state
from ui.colours import LC_COLOURS


class MetadataTab(QWidget):
    data_changed = pyqtSignal()
    def __init__(self):
        super().__init__()

        # Top-level form layout
        layout = QFormLayout(self)

        # ── Basic identity fields ──────────────────────────────────────
        self.tdp_id = QLineEdit()
        self.tdp_id.setPlaceholderText("Primary permanent identifier (e.g. part number)")

        self.additional_ids = QLineEdit()
        self.additional_ids.setPlaceholderText("Other identifiers e.g. NSN (optional)")

        self.name = QLineEdit()

        # ── Description + 3-D viewer side-by-side ─────────────────────
        self.description = QTextEdit()
        self.description.setMinimumHeight(120)

        self._no_preview_label = QLabel("No geometry\nselected for preview")
        self._no_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_preview_label.setStyleSheet(
            "color: #888; font-size: 12px; background: #1e2433; border-radius: 6px;"
        )
        self._no_preview_label.setMinimumSize(260, 220)

        self.viewer = ThreeDViewer(self)
        self.viewer.hide()

        # Rotation buttons
        _btn_style = (
            "QPushButton { background:#2d3448; color:#aab; border:1px solid #445;"
            " border-radius:4px; padding:2px 8px; font-size:14px; }"
            "QPushButton:hover { background:#3d4560; }"
            "QPushButton:pressed { background:#1e2433; }"
        )
        from PyQt6.QtWidgets import QPushButton
        btn_ccw = QPushButton("↺ 45°")
        btn_cw  = QPushButton("45° ↻")
        for btn in (btn_ccw, btn_cw):
            btn.setStyleSheet(_btn_style)
            btn.setFixedHeight(26)
        btn_ccw.clicked.connect(lambda: self.viewer.rotate(-45))
        btn_cw.clicked.connect(lambda:  self.viewer.rotate(+45))
        btn_ccw.setToolTip("Rotate 45° counter-clockwise")
        btn_cw.setToolTip("Rotate 45° clockwise")

        rot_row = QHBoxLayout()
        rot_row.addWidget(btn_ccw)
        rot_row.addStretch()
        rot_row.addWidget(btn_cw)

        viewer_col = QVBoxLayout()
        viewer_col.addWidget(self._no_preview_label)
        viewer_col.addWidget(self.viewer)
        viewer_col.addLayout(rot_row)
        viewer_col.setContentsMargins(6, 0, 0, 0)

        desc_and_viewer = QHBoxLayout()
        desc_and_viewer.addWidget(self.description, stretch=1)
        desc_and_viewer.addLayout(viewer_col, stretch=1)

        # ── Date / status fields ───────────────────────────────────────
        self.version = QLineEdit()

        self.created_date = QDateEdit(QDate.currentDate())
        self.created_date.setCalendarPopup(True)

        self.modified_date = QDateEdit(QDate.currentDate())
        self.modified_date.setCalendarPopup(True)
        self.modified_date.setReadOnly(True)

        self.lifecycle_status = QComboBox()
        self.lifecycle_status.addItems(
            ["Draft", "In Review", "Approved", "Released", "Deprecated"]
        )

        self.information_classification = QComboBox()
        self.information_classification.addItems(
            ["Internal", "Public", "Unclassified", "Restricted",
             "Confidential", "Secret", "Top Secret"]
        )

        # ── Contact / ownership fields ─────────────────────────────────
        self.author = QLineEdit()
        self.organization = QLineEdit()
        self.contact = QLineEdit()
        self.licensing = QLineEdit()
        self.confidentiality_level = QLineEdit()

        # Auto-update Modified Date whenever any field changes
        for w in [self.tdp_id, self.additional_ids, self.name, self.version,
                  self.author, self.organization, self.contact,
                  self.licensing, self.confidentiality_level]:
            w.textChanged.connect(self._touch_modified)
        self.description.textChanged.connect(self._touch_modified)
        self.lifecycle_status.currentIndexChanged.connect(self._touch_modified)

        # Live field-state highlighting
        self.tdp_id.textChanged.connect(self._refresh_states)
        self.name.textChanged.connect(self._refresh_states)
        self.contact.textChanged.connect(self._refresh_states)
        self.licensing.textChanged.connect(self._refresh_states)
        self.lifecycle_status.currentIndexChanged.connect(self._refresh_states)
        self._refresh_states()
        self._connect_change_signals()   # show state immediately on startup

        # ── Two-column block (dates+status left | contacts right) ──────
        left = QFormLayout()
        right = QFormLayout()

        vsep = QFrame()
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setFrameShadow(QFrame.Shadow.Sunken)

        left.addRow("Lifecycle Status:", self.lifecycle_status)
        left.addRow("Revision:", self.version)
        left.addRow("Created Date:", self.created_date)
        left.addRow("Modified Date:", self.modified_date)
        left.addRow("Information Classification:", self.information_classification)

        right.addRow("Author:", self.author)
        right.addRow("Organization:", self.organization)
        right.addRow("Contact *:", self.contact)
        right.addRow("Licensing *:", self.licensing)
        right.addRow("Confidentiality Marking:", self.confidentiality_level)

        two_col = QHBoxLayout()
        two_col.addLayout(left)
        two_col.addWidget(vsep)
        two_col.addLayout(right)

        # ── Assemble form ──────────────────────────────────────────────
        layout.addRow("Item ID *:", self.tdp_id)
        layout.addRow("Additional IDs:", self.additional_ids)
        layout.addRow("Item Name *:", self.name)
        layout.addRow("Description / 3-D Preview:", desc_and_viewer)
        layout.addRow(two_col)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _touch_modified(self):
        self.modified_date.setDate(QDate.currentDate())

    # ------------------------------------------------------------------
    # 3-D preview
    # ------------------------------------------------------------------
    def load_geometry_preview(self, model_path: str):
        """Called by MainWindow when the user selects a geometry preview."""
        if model_path and Path(model_path).is_file():
            self._no_preview_label.hide()
            self.viewer.show()
            self.viewer.load_model(model_path)
        else:
            self._clear_preview()

    def _clear_preview(self):
        self.viewer.clear()
        self.viewer.hide()
        self._no_preview_label.show()

    # ------------------------------------------------------------------
    # Field-state highlighting
    # ------------------------------------------------------------------

    def set_non_critical_lifecycle(self, non_critical: bool) -> None:
        """Called by MainWindow when criticality = Non-critical.
        Non-critical packages skip In Review — Draft goes straight to
        Approved, Released or Deprecated.
        """
        current = self.lifecycle_status.currentText()
        self.lifecycle_status.blockSignals(True)
        self.lifecycle_status.clear()
        if non_critical:
            options = ["Draft", "Approved", "Released", "Deprecated"]
        else:
            options = ["Draft", "In Review", "Approved", "Released", "Deprecated"]
        self.lifecycle_status.addItems(options)
        # Restore selection — if current value no longer in list, default to Draft
        if current in options:
            self.lifecycle_status.setCurrentText(current)
        else:
            # 'In Review' removed for non-critical: fall back to Draft
            self.lifecycle_status.setCurrentText("Draft")
        self.lifecycle_status.blockSignals(False)
        self._refresh_states()

    def has_errors(self) -> bool:
        """True if any always-required field is empty."""
        return not all([
            self.tdp_id.text().strip(),
            self.name.text().strip(),
            self.contact.text().strip(),
            self.licensing.text().strip(),
        ])

    def _refresh_states(self):
        update_states({
            self.tdp_id:    bool(self.tdp_id.text().strip()),
            self.name:      bool(self.name.text().strip()),
            self.contact:   bool(self.contact.text().strip()),
            self.licensing: bool(self.licensing.text().strip()),
        })
        lc = self.lifecycle_status.currentText()
        fg, bg = LC_COLOURS.get(lc, ('#000000', '#ffffff'))
        self.lifecycle_status.setStyleSheet(
            f'QComboBox {{ background-color: {bg}; color: {fg};'
            f' border: 1.5px solid {fg}; border-radius: 4px;'
            f' font-weight: bold; padding: 2px 6px; }}'
            f'QComboBox::drop-down {{ border: none; }}'
        )

    # ------------------------------------------------------------------
    # Data I/O  (no criticality_level — derived from Quality tab)
    # ------------------------------------------------------------------
    def get_data(self) -> Metadata:
        return Metadata(
            tdp_id=self.tdp_id.text().strip(),
            additional_ids=self.additional_ids.text().strip(),
            name=self.name.text().strip(),
            description=self.description.toPlainText().strip(),
            version=self.version.text().strip(),
            created_date=self.created_date.date().toString("yyyy-MM-dd"),
            modified_date=self.modified_date.date().toString("yyyy-MM-dd"),
            lifecycle_status=self.lifecycle_status.currentText(),
            criticality_level="",   # derived — set by collect_package()
            author=self.author.text().strip(),
            organization=self.organization.text().strip(),
            contact=self.contact.text().strip(),
            licensing=self.licensing.text().strip(),
            information_classification=self.information_classification.currentText(),
            confidentiality_level=self.confidentiality_level.text().strip(),
        )

    def load_data(self, md: Metadata):
        self.tdp_id.setText(md.tdp_id)
        self.additional_ids.setText(md.additional_ids)
        self.name.setText(md.name)
        self.description.setPlainText(md.description)
        self.version.setText(md.version)
        for date_edit, date_str in [
            (self.created_date, md.created_date),
            (self.modified_date, md.modified_date),
        ]:
            d = QDate.fromString(date_str, "yyyy-MM-dd")
            if d.isValid():
                date_edit.setDate(d)
        self.lifecycle_status.setCurrentText(md.lifecycle_status)
        self.information_classification.setCurrentText(md.information_classification)
        self.author.setText(md.author)
        self.organization.setText(md.organization)
        self.contact.setText(md.contact)
        self.licensing.setText(md.licensing)
        self.confidentiality_level.setText(md.confidentiality_level)
        self._refresh_states()
        # Reset preview on load — geometry_tab will fire preview_changed if needed
        self._clear_preview()


    def _connect_change_signals(self):
        for sig in [
            self.tdp_id.textChanged, self.name.textChanged,
            self.contact.textChanged, self.licensing.textChanged,
            self.lifecycle_status.currentIndexChanged,
        ]:
            sig.connect(self.data_changed)
