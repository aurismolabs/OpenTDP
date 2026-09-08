# ui/quality_tab.py
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QLabel
)
from PyQt6.QtCore import QDateTime

from models.quality import QualityData, TraceabilityData, RiskData, ApprovalData
from ui.field_state import update_states, clear_state, apply_state, REQUIRED_EMPTY, REQUIRED_FILLED
from ui.colours import CRIT_COLOURS


class QualityTab(QWidget):
    data_changed = pyqtSignal()
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(self._traceability_group())
        layout.addWidget(self._risk_group())
        layout.addWidget(self._process_quality_group())
        layout.addWidget(self._approval_group())
        layout.addStretch()

        # Live field-state highlighting
        self.approver.textChanged.connect(self._refresh_states)
        self.approval_status.currentIndexChanged.connect(self._refresh_states)
        self.approval_conditions.textChanged.connect(self._refresh_states)
        self.evidence_refs.textChanged.connect(self._refresh_states)
        self.identified_risks.textChanged.connect(self._refresh_states)
        self._refresh_states()   # show state immediately on startup
        self._connect_change_signals()

    def _traceability_group(self):
        g = QGroupBox("Traceability and Identification Rules")
        form = QFormLayout()
        self.serial_format = QLineEdit()
        self.serial_format.setPlaceholderText("e.g. XX-YYYY-ZZZZZZ or GS1")
        self.batch_format = QLineEdit()
        self.material_lot_format = QLineEdit()
        self.labeling = QLineEdit()
        self.traceability_level = QComboBox()
        self.traceability_level.addItems([
            "", "Batch", "Lot", "Unit", "Component"
        ])
        self.traceability_level.wheelEvent = lambda e: e.ignore()
        form.addRow("Serial Number Format:", self.serial_format)
        form.addRow("Batch ID Format:", self.batch_format)
        form.addRow("Material Lot Format:", self.material_lot_format)
        form.addRow("Labeling Requirements:", self.labeling)
        form.addRow("Traceability Level:", self.traceability_level)
        g.setLayout(form)
        return g

    def _risk_group(self):
        g = QGroupBox("Risk Classification  →  determines Criticality Level")
        form = QFormLayout()
        self.technical_perf = QComboBox()
        self.technical_perf.addItems([
            "Negligible Technical Impact", "Low Technical Impact",
            "Moderate Technical Impact", "High Technical Impact", "Critical Technical Impact"
        ])
        self.technical_perf.wheelEvent = lambda e: e.ignore()
        self.safety_crit = QComboBox()
        self.safety_crit.addItems([
            "Minimal Safety Concern", "Low Safety Concern",
            "Moderate Safety Concern", "High Safety Concern", "Critical Safety Hazard"
        ])
        self.safety_crit.wheelEvent = lambda e: e.ignore()
        self.identified_risks = QTextEdit()
        self.identified_risks.setFixedHeight(70)

        # Live criticality indicator
        self._criticality_label = QLabel()
        self.technical_perf.currentIndexChanged.connect(self._update_criticality_label)
        self.safety_crit.currentIndexChanged.connect(self._update_criticality_label)
        self._update_criticality_label()   # apply correct colour on startup

        form.addRow("Technical Performance:", self.technical_perf)
        form.addRow("Safety Criticality:", self.safety_crit)
        form.addRow("Identified Risks:", self.identified_risks)
        form.addRow("→ Derived Criticality:", self._criticality_label)
        g.setLayout(form)
        return g

    def _update_criticality_label(self):
        from services.validation import derive_criticality
        from models.quality import QualityData, RiskData
        mock = QualityData(risks=RiskData(
            technical_performance=self.technical_perf.currentText(),
            safety_criticality=self.safety_crit.currentText(),
        ))
        level = derive_criticality(mock)
        # CRIT_COLOURS: (light_text, dark_bg) — swap for label (dark bg, light text)
        fg, bg = CRIT_COLOURS.get(level, ("#f3f4f6", "#374151"))
        self._criticality_label.setText(f"Criticality: {level}")
        self._criticality_label.setStyleSheet(
            f"font-weight: bold; padding: 4px 8px; border-radius: 4px;"
            f"background: {bg}; color: {fg};"
        )

    def _process_quality_group(self):
        g = QGroupBox("Process Quality Notes")
        form = QFormLayout()
        self.process_quality_notes = QTextEdit()
        self.process_quality_notes.setFixedHeight(80)
        self.process_quality_notes.setPlaceholderText(
            "General quality considerations. Detailed requirements belong in Manufacturing Steps."
        )
        form.addRow("General Considerations:", self.process_quality_notes)
        g.setLayout(form)
        return g

    def _approval_group(self):
        g = QGroupBox("Approval and Audit Trail")
        form = QFormLayout()
        self.approver = QLineEdit()
        self.approval_status = QComboBox()
        self.approval_status.addItems(["Pending", "Approved", "Rejected"])
        self.approval_status.wheelEvent = lambda e: e.ignore()
        self.approval_timestamp = QDateTimeEdit(QDateTime.currentDateTime())
        self.approval_timestamp.setCalendarPopup(True)
        self.approval_timestamp.wheelEvent = lambda e: e.ignore()
        self.approval_conditions = QTextEdit()
        self.approval_conditions.setFixedHeight(70)
        self.approval_conditions.setPlaceholderText(
            "List what must be submitted/demonstrated for approval, e.g.:\n  - First Article Inspection report\n  - Material certificates\n  - Dimensional report"
        )
        self.evidence_refs = QLineEdit()
        self.evidence_refs.setPlaceholderText(
            "References to submitted evidence, e.g. FAI-2024-001, MatCert-batch-42"
        )
        form.addRow("Approver:", self.approver)
        form.addRow("Status:", self.approval_status)
        form.addRow("Timestamp:", self.approval_timestamp)
        form.addRow("Approval Conditions:", self.approval_conditions)
        form.addRow("Evidence References:", self.evidence_refs)
        g.setLayout(form)
        return g

    def has_errors(self) -> bool:
        """True if any required quality field is empty."""
        # Identified risks: In Review+ and Low+
        if getattr(self, '_risks_required', False):
            if not self.identified_risks.toPlainText().strip():
                return True
        # Approval status: Approved+ (only status required; audit fields
        # are optional for Non-critical packages)
        if getattr(self, '_approval_required', False):
            if self.approval_status.currentText() in ('', 'Pending'):
                return True
        return False

    def set_lifecycle(self, lifecycle: str) -> None:
        """Called by MainWindow when lifecycle changes."""
        self._lifecycle = lifecycle
        self._enforce_approval_status_constraint()
        self._refresh_states()

    def set_identified_risks_required(self, required: bool) -> None:
        """Called by MainWindow when In Review+ and criticality >= Low."""
        self._risks_required = required
        self._refresh_states()

    def set_non_critical(self, non_critical: bool) -> None:
        """Called by MainWindow when criticality = Non-critical.
        Auto-sets Status to Approved and makes audit fields optional.
        """
        self._non_critical = non_critical
        if non_critical:
            self.approval_status.setCurrentText('Approved')
        self._refresh_states()

    def set_approval_required(self, required: bool) -> None:
        """Called by MainWindow when lifecycle >= Approved."""
        self._approval_required = required
        self._refresh_states()

    def _enforce_approval_status_constraint(self) -> None:
        """Disable Approved option when lifecycle is Draft/In Review/Deprecated.
        Non-critical packages are exempt — their status is auto-Approved.
        """
        from PyQt6.QtCore import Qt
        lc = getattr(self, '_lifecycle', 'Draft')
        non_critical = getattr(self, '_non_critical', False)
        # In Review blocks Approved only for Low+ packages
        blocked = {'Draft', 'In Review', 'Deprecated'} if not non_critical else {'Deprecated'}
        if lc in blocked and self.approval_status.currentText() == 'Approved':
            self.approval_status.setCurrentText('Pending')
        model = self.approval_status.model()
        for i in range(self.approval_status.count()):
            text = self.approval_status.itemText(i)
            item = model.item(i)
            if text == 'Approved' and lc in blocked:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)

    def _refresh_states(self):
        lc = getattr(self, '_lifecycle', 'Draft')
        draft = (lc == 'Draft')

        # Identified Risks: required when criticality >= Low
        risks_req = getattr(self, '_risks_required', False)
        if risks_req:
            update_states({
                self.identified_risks:
                    bool(self.identified_risks.toPlainText().strip())
            })
        else:
            clear_state(self.identified_risks)

        # Approval fields: Approved+ required; Non-critical only status highlighted
        approval_req  = getattr(self, '_approval_required', False)
        non_critical  = getattr(self, '_non_critical', False)
        if approval_req:
            status_ok = self.approval_status.currentText() not in ('', 'Pending')
            # Status always highlighted
            apply_state(self.approval_status,
                        REQUIRED_FILLED if status_ok else REQUIRED_EMPTY)
            if non_critical:
                # Audit fields are informational only for Non-critical
                for w in (self.approver, self.approval_conditions,
                          self.evidence_refs):
                    clear_state(w)
            else:
                update_states({
                    self.approver:
                        bool(self.approver.text().strip()),
                    self.approval_conditions:
                        bool(self.approval_conditions.toPlainText().strip()),
                    self.evidence_refs:
                        bool(self.evidence_refs.text().strip()),
                })
        else:
            for w in (self.approver, self.approval_status,
                      self.approval_conditions, self.evidence_refs):
                clear_state(w)

    def get_data(self) -> QualityData:
        return QualityData(
            traceability=TraceabilityData(
                serial_number_format=self.serial_format.text(),
                batch_id_format=self.batch_format.text(),
                material_lot_format=self.material_lot_format.text(),
                labeling_requirements=self.labeling.text(),
                traceability_level=self.traceability_level.currentText(),
            ),
            risks=RiskData(
                technical_performance=self.technical_perf.currentText(),
                safety_criticality=self.safety_crit.currentText(),
                identified_risks=self.identified_risks.toPlainText(),
            ),
            process_quality_notes=self.process_quality_notes.toPlainText(),
            approval=ApprovalData(
                approver=self.approver.text(),
                status=self.approval_status.currentText(),
                timestamp=self.approval_timestamp.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                conditions=self.approval_conditions.toPlainText(),
                evidence_refs=self.evidence_refs.text(),
            ),
        )

    def load_data(self, q: QualityData):
        self.serial_format.setText(q.traceability.serial_number_format)
        self.batch_format.setText(q.traceability.batch_id_format)
        self.material_lot_format.setText(q.traceability.material_lot_format)
        self.labeling.setText(q.traceability.labeling_requirements)
        self.traceability_level.setCurrentText(q.traceability.traceability_level)

        self.technical_perf.setCurrentText(q.risks.technical_performance)
        self.safety_crit.setCurrentText(q.risks.safety_criticality)
        self.identified_risks.setPlainText(q.risks.identified_risks)
        self._update_criticality_label()

        self.process_quality_notes.setPlainText(q.process_quality_notes)

        self.approver.setText(q.approval.approver)
        self.approval_status.setCurrentText(q.approval.status)
        self.approval_conditions.setPlainText(q.approval.conditions)
        self.evidence_refs.setText(q.approval.evidence_refs)
        self._refresh_states()
        if q.approval.timestamp:
            dt = QDateTime.fromString(q.approval.timestamp, "yyyy-MM-dd HH:mm:ss")
            if dt.isValid():
                self.approval_timestamp.setDateTime(dt)


    def _connect_change_signals(self):
        for sig in [
            self.technical_perf.currentIndexChanged,
            self.safety_crit.currentIndexChanged,
            self.identified_risks.textChanged,
            self.approver.textChanged,
            self.approval_status.currentIndexChanged,
            self.approval_conditions.textChanged,
            self.evidence_refs.textChanged,
        ]:
            sig.connect(self.data_changed)
