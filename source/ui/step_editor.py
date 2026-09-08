# ui/step_editor.py
import os
import uuid

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QFileDialog,
    QLabel, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QObject, QEvent

from models.manufacturing import ProcessStep, Attachment
from models.geometry import Geometry
from models.amdata import BuildFile
from services.checksum_service import file_checksum


_INSPECTION_CATALOG = {
    "Visual and Dimensional": [
        "Visual inspection — surfaces, colors, damage",
        "Dimensional inspection — caliper, micrometer, CMM",
        "Surface roughness measurement — Ra, Rz",
        "Weight check — mass verification",
    ],
    "Functional & Mechanical": [
        "Functional testing — opening, closing, durability",
        "Hardness testing — Shore, Rockwell, Brinell",
        "Tensile / compression testing",
        "Torque testing — caps, closures",
    ],
    "Integrity & Leakage": [
        "Leak testing — pressure, vacuum, water bath",
        "Seal integrity testing — heat-seal strength, burst test",
    ],
    "Material & Chemical": [
        "Material identification — FTIR, XRF, DSC",
        "Chemical migration testing — food contact materials",
    ],
    "Advanced NDT": [
        "Ultrasonic inspection",
        "X-ray inspection",
        "CT scanning — 3D structure analysis",
        "Thermal imaging — temperature anomalies",
    ],
    "Environmental & Packaging": [
        "Drop testing — impact resistance",
        "Vibration testing — transport simulation",
        "Environmental chamber testing — temperature & humidity stress",
        "Microbiological inspection",
    ],
}


class StepEditor(QDialog):
    def __init__(self, parent=None,
                 geometry_list: list[Geometry] = None,
                 build_files: list[BuildFile] = None,
                 existing: ProcessStep = None):
        super().__init__(parent)
        self.setWindowTitle("Process Step Editor")
        self.setMinimumSize(780, 680)

        self._geometries = geometry_list or []
        self._build_files = build_files or []
        self._existing = existing

        # Root scroll → container → tabs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        main_layout = QVBoxLayout(container)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Build each tab
        tabs.addTab(self._tab_basics(),       "Basics")
        tabs.addTab(self._tab_materials(),    "Materials")
        tabs.addTab(self._tab_environment(),  "Environment")
        tabs.addTab(self._tab_equipment(),    "Equipment")
        tabs.addTab(self._tab_quality(),      "Quality")
        tabs.addTab(self._tab_safety(),       "Safety")
        tabs.addTab(self._tab_post(),         "Post-processing")
        tabs.addTab(self._tab_parameters(),   "Parameters")
        tabs.addTab(self._tab_attachments(),  "Attachments")

        # Block wheel events on all spinboxes in this dialog
        self._install_wheel_block()

        save_btn = QPushButton("Save Step")
        save_btn.clicked.connect(self.accept)
        main_layout.addWidget(save_btn)

        if existing:
            self._populate(existing)

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Tab factory helper — uniform spacing for all form tabs
    # ------------------------------------------------------------------
    def _make_tab(self):
        """Return (QWidget, QFormLayout) with consistent compact spacing."""
        w = QWidget()
        form = QFormLayout(w)
        form.setVerticalSpacing(4)
        form.setHorizontalSpacing(8)
        form.setContentsMargins(8, 8, 8, 8)
        return w, form

    def _tab_basics(self):
        w, form = self._make_tab()

        self.step_id = QLineEdit(f"S-{uuid.uuid4().hex[:6]}")
        self.sequence = QSpinBox()
        self.sequence.setRange(0, 9999)
        self.name = QLineEdit()
        self.description = QTextEdit()
        self.description.setFixedHeight(48)
        self.mfg_method = QLineEdit()
        self.orientation = QLineEdit()

        geo_names = [g.file_name for g in self._geometries]
        self.input_combo = QComboBox()
        self.input_combo.addItem("")
        self.input_combo.addItems(geo_names)
        self.output_combo = QComboBox()
        self.output_combo.addItem("")
        self.output_combo.addItems(geo_names)

        self.operator_count = QSpinBox()
        self.operator_count.setRange(1, 99)
        self.operator_count.setValue(1)

        self.dur_hours = QSpinBox()
        self.dur_hours.setRange(0, 9999)
        self.dur_minutes = QSpinBox()
        self.dur_minutes.setRange(0, 59)
        dur_container = QWidget()
        dur_container.setFixedHeight(28)
        dur_row = QHBoxLayout(dur_container)
        dur_row.setContentsMargins(0, 0, 0, 0)
        dur_row.addWidget(self.dur_hours)
        dur_row.addWidget(QLabel("h"))
        dur_row.addWidget(self.dur_minutes)
        dur_row.addWidget(QLabel("min"))
        dur_row.addStretch()

        self.build_file_list = QListWidget()
        self.build_file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.build_file_list.setFixedHeight(80)
        for bf in self._build_files:
            self.build_file_list.addItem(QListWidgetItem(bf.file_name))

        form.addRow("Step ID:", self.step_id)
        form.addRow("Sequence:", self.sequence)
        form.addRow("Name:", self.name)
        form.addRow("Description:", self.description)
        form.addRow("Manufacturing Method:", self.mfg_method)
        form.addRow("Build Orientation:", self.orientation)
        form.addRow("Input Geometry:", self.input_combo)
        form.addRow("Output Geometry:", self.output_combo)
        form.addRow("Estimated Duration:", dur_container)
        form.addRow("Operators Required:", self.operator_count)
        form.addRow("Applicable Build Files:", self.build_file_list)
        return w

    def _tab_materials(self):
        w, form = self._make_tab()
        self.material = QLineEdit()
        self.material_batch = QLineEdit()
        self.material_pretreatment = QLineEdit()
        self.material_quantity = QLineEdit()
        self.material_quantity.setPlaceholderText("e.g. 200 g  /  2 blanks")
        self.material_shelf_life = QLineEdit()
        self.material_shelf_life.setPlaceholderText("e.g. 2025-12-31  /  12 months from opening")
        form.addRow("Material:", self.material)
        form.addRow("Batch:", self.material_batch)
        form.addRow("Pre-treatment:", self.material_pretreatment)
        form.addRow("Quantity / Consumption:", self.material_quantity)
        form.addRow("Shelf Life / Expiry:", self.material_shelf_life)
        return w

    def _tab_environment(self):
        w, form = self._make_tab()

        self.env_temp_min = QSpinBox()
        self.env_temp_min.setRange(-100, 500)
        self.env_temp_min.setValue(5)
        self.env_temp_max = QSpinBox()
        self.env_temp_max.setRange(-100, 500)
        self.env_temp_max.setValue(35)
        temp_container = QWidget(); temp_container.setFixedHeight(28)
        temp_row = QHBoxLayout(temp_container)
        temp_row.setContentsMargins(0, 0, 0, 0)
        temp_row.addWidget(self.env_temp_min)
        temp_row.addWidget(QLabel("to"))
        temp_row.addWidget(self.env_temp_max)
        temp_row.addWidget(QLabel("°C"))
        temp_row.addStretch()

        self.env_hum_min = QSpinBox()
        self.env_hum_min.setRange(0, 100)
        self.env_hum_min.setValue(30)
        self.env_hum_max = QSpinBox()
        self.env_hum_max.setRange(0, 100)
        self.env_hum_max.setValue(70)
        hum_container = QWidget(); hum_container.setFixedHeight(28)
        hum_row = QHBoxLayout(hum_container)
        hum_row.setContentsMargins(0, 0, 0, 0)
        hum_row.addWidget(self.env_hum_min)
        hum_row.addWidget(QLabel("to"))
        hum_row.addWidget(self.env_hum_max)
        hum_row.addWidget(QLabel("% RH"))
        hum_row.addStretch()

        self.airflow = QLineEdit()
        self.env_cleanroom_class = QLineEdit()
        self.env_cleanroom_class.setPlaceholderText("e.g. ISO 7  /  Class 10000  /  ISO 14644-1")

        form.addRow("Temperature:", temp_container)
        form.addRow("Humidity:", hum_container)
        form.addRow("Airflow:", self.airflow)
        form.addRow("Cleanroom Class:", self.env_cleanroom_class)
        return w

    def _tab_equipment(self):
        w, form = self._make_tab()

        self.machine = QLineEdit()
        self.tools = QLineEdit()
        self.software = QLineEdit()

        self.power_kw = QDoubleSpinBox()
        self.power_kw.setRange(0, 99999)
        self.compressed_air = QDoubleSpinBox()
        self.compressed_air.setRange(0, 99999)

        self.vacuum = QLineEdit()
        self.cooling = QLineEdit()
        self.floorarea = QLineEdit()
        self.eqpheight = QLineEdit()

        self.eqp_weight = QDoubleSpinBox()
        self.eqp_weight.setRange(0, 999999)

        self.other_equipment = QLineEdit()

        form.addRow("Machine:", self.machine)
        form.addRow("Tools:", self.tools)
        form.addRow("Software:", self.software)
        form.addRow("Power (kW):", self.power_kw)
        form.addRow("Compressed Air (bar):", self.compressed_air)
        form.addRow("Vacuum:", self.vacuum)
        form.addRow("Cooling:", self.cooling)
        form.addRow("Floor Area:", self.floorarea)
        form.addRow("Equipment Height:", self.eqpheight)
        form.addRow("Equipment Weight (kg):", self.eqp_weight)
        form.addRow("Other Needs:", self.other_equipment)
        return w

    def _tab_quality(self):
        w, form = self._make_tab()

        self.inspection_list = _InspectionSelector(_INSPECTION_CATALOG)
        self.inspection_list.setFixedHeight(160)
        self.inspection_points = QLineEdit()
        self.sampling_plan = QLineEdit()
        self.tolerances = QLineEdit()
        self.surface_quality = QLineEdit()
        self.acceptance_criteria = QTextEdit()
        self.acceptance_criteria.setFixedHeight(48)
        self.nonacceptance_handling = QLineEdit()
        self.required_docs = QLineEdit()
        self.required_training = QLineEdit()
        self.requirement_source = QLineEdit()
        self.requirement_source.setPlaceholderText(
            "e.g. Drawing rev. C  /  ISO 2768-m  /  Customer spec. CS-2024-017"
        )

        form.addRow("Verification Methods:", self.inspection_list)
        form.addRow("Characteristics to Verify:", self.inspection_points)
        form.addRow("Sampling Scheme:", self.sampling_plan)
        form.addRow("Dimensional Requirements:", self.tolerances)
        form.addRow("Surface Texture Requirements:", self.surface_quality)
        form.addRow("Conformity Criteria:", self.acceptance_criteria)
        form.addRow("Nonconformity Handling:", self.nonacceptance_handling)
        form.addRow("Required Documents:", self.required_docs)
        form.addRow("Competence Requirements:", self.required_training)
        form.addRow("Requirement Source:", self.requirement_source)
        return w

    def _tab_safety(self):
        w, form = self._make_tab()

        self.ppe = QLineEdit()
        self.chemical_risks = QLineEdit()
        self.thermal_risks = QLineEdit()
        self.mechanical_risks = QLineEdit()
        self.esd_risks = QLineEdit()
        self.other_safety = QLineEdit()

        form.addRow("PPE:", self.ppe)
        form.addRow("Chemical Risks:", self.chemical_risks)
        form.addRow("Thermal Risks:", self.thermal_risks)
        form.addRow("Mechanical Risks:", self.mechanical_risks)
        form.addRow("ESD Risks:", self.esd_risks)
        form.addRow("Other Safety:", self.other_safety)
        return w

    def _tab_post(self):
        w, form = self._make_tab()
        self.post_processing = QTextEdit()
        self.post_processing.setFixedHeight(60)
        self.notes = QTextEdit()
        self.notes.setFixedHeight(60)
        form.addRow("Post-processing:", self.post_processing)
        form.addRow("Notes:", self.notes)
        return w

    def _tab_parameters(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.param_table = QTableWidget(0, 2)
        self.param_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.param_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.param_table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Row")
        btn_add.clicked.connect(lambda: self.param_table.insertRow(self.param_table.rowCount()))
        btn_del = QPushButton("Remove Selected")
        btn_del.clicked.connect(self._remove_param_row)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)
        return w

    def _tab_attachments(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.att_list = QListWidget()
        layout.addWidget(self.att_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Attachment")
        btn_add.clicked.connect(self._add_attachment)
        btn_del = QPushButton("Remove Selected")
        btn_del.clicked.connect(self._remove_attachment)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)
        return w

    # ------------------------------------------------------------------
    # Populate from existing step
    # ------------------------------------------------------------------
    def _populate(self, s: ProcessStep):
        self.step_id.setText(s.id)
        self.sequence.setValue(s.sequence)
        self.name.setText(s.name)
        self.description.setPlainText(s.description)
        self.mfg_method.setText(s.manufacturing_method)
        self.orientation.setText(s.orientation)
        if s.inputs:
            self.input_combo.setCurrentText(s.inputs[0])
        if s.outputs:
            self.output_combo.setCurrentText(s.outputs[0])
        self.dur_hours.setValue(s.duration.get("hours", 0))
        self.dur_minutes.setValue(s.duration.get("minutes", 0))
        self.operator_count.setValue(s.operator_count)

        for i in range(self.build_file_list.count()):
            if self.build_file_list.item(i).text() in s.build_files:
                self.build_file_list.item(i).setSelected(True)

        # Materials
        self.material.setText(s.material)
        self.material_batch.setText(s.material_batch)
        self.material_pretreatment.setText(s.material_pretreatment)
        self.material_quantity.setText(s.material_quantity)
        self.material_shelf_life.setText(s.material_shelf_life)

        # Environment
        self.env_temp_min.setValue(s.env_temp_min)
        self.env_temp_max.setValue(s.env_temp_max)
        self.env_hum_min.setValue(s.env_humidity_min)
        self.env_hum_max.setValue(s.env_humidity_max)
        self.airflow.setText(s.airflow)
        self.env_cleanroom_class.setText(s.env_cleanroom_class)

        # Equipment
        self.machine.setText(s.machine)
        self.tools.setText(s.tools)
        self.software.setText(s.software)
        self.power_kw.setValue(s.power_kw)
        self.compressed_air.setValue(s.compressed_air_bar)
        self.vacuum.setText(s.vacuum)
        self.cooling.setText(s.cooling)
        self.floorarea.setText(s.floorarea)
        self.eqpheight.setText(s.eqpheight)
        self.eqp_weight.setValue(s.weight)
        self.other_equipment.setText(s.other_equipment)

        # Quality
        self.inspection_list.set_selected(s.inspection_methods)
        self.inspection_points.setText(s.inspection_points)
        self.sampling_plan.setText(s.sampling_plan)
        self.tolerances.setText(s.tolerances)
        self.surface_quality.setText(s.surface_quality)
        self.acceptance_criteria.setPlainText(s.acceptance_criteria)
        self.nonacceptance_handling.setText(s.nonacceptance_handling)
        self.required_docs.setText(s.required_docs)
        self.required_training.setText(s.required_training)
        self.requirement_source.setText(s.requirement_source)

        # Safety
        self.ppe.setText(s.ppe)
        self.chemical_risks.setText(s.chemical_risks)
        self.thermal_risks.setText(s.thermal_risks)
        self.mechanical_risks.setText(s.mechanical_risks)
        self.esd_risks.setText(s.esd_risks)
        self.other_safety.setText(s.other_safety)

        # Post
        self.post_processing.setPlainText(s.post_processing)
        self.notes.setPlainText(s.notes)

        # Parameters
        for key, val in s.parameters.items():
            row = self.param_table.rowCount()
            self.param_table.insertRow(row)
            self.param_table.setItem(row, 0, QTableWidgetItem(key))
            self.param_table.setItem(row, 1, QTableWidgetItem(val))

        # Attachments
        for att in s.attachments:
            item = QListWidgetItem(att.file_name)
            item.setData(Qt.ItemDataRole.UserRole, att)
            self.att_list.addItem(item)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _remove_param_row(self):
        row = self.param_table.currentRow()
        if row >= 0:
            self.param_table.removeRow(row)

    def _add_attachment(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Attachment")
        if not path:
            return
        att = Attachment(
            file_name=os.path.basename(path),
            source_path=path,
            file_format=os.path.splitext(path)[1].lstrip(".").upper(),
            file_size=str(os.path.getsize(path)),
            checksum=file_checksum(path),
        )
        item = QListWidgetItem(att.file_name)
        item.setData(Qt.ItemDataRole.UserRole, att)
        self.att_list.addItem(item)

    def _remove_attachment(self):
        row = self.att_list.currentRow()
        if row >= 0:
            self.att_list.takeItem(row)

    # ------------------------------------------------------------------
    # Data export
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Wheel block
    # ------------------------------------------------------------------
    def _install_wheel_block(self):
        class _WB(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == QEvent.Type.Wheel:
                    ev.ignore(); return True
                return super().eventFilter(obj, ev)
        self._wb = _WB(self)
        for child in self.findChildren((QSpinBox, QDoubleSpinBox, QComboBox)):
            child.installEventFilter(self._wb)

    def get_data(self) -> ProcessStep:
        # Build files
        selected_bf = [
            self.build_file_list.item(i).text()
            for i in range(self.build_file_list.count())
            if self.build_file_list.item(i).isSelected()
        ]

        # Parameters
        params = {}
        for row in range(self.param_table.rowCount()):
            k = self.param_table.item(row, 0)
            v = self.param_table.item(row, 1)
            if k and k.text().strip():
                params[k.text().strip()] = v.text().strip() if v else ""

        # Attachments
        attachments = [
            self.att_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.att_list.count())
        ]

        return ProcessStep(
            id=self.step_id.text(),
            sequence=self.sequence.value(),
            name=self.name.text(),
            description=self.description.toPlainText(),
            manufacturing_method=self.mfg_method.text(),
            orientation=self.orientation.text(),
            inputs=[self.input_combo.currentText()] if self.input_combo.currentText() else [],
            outputs=[self.output_combo.currentText()] if self.output_combo.currentText() else [],
            build_files=selected_bf,
            duration={"hours": self.dur_hours.value(), "minutes": self.dur_minutes.value()},
            operator_count=self.operator_count.value(),
            attachments=attachments,
            material=self.material.text(),
            material_batch=self.material_batch.text(),
            material_pretreatment=self.material_pretreatment.text(),
            material_quantity=self.material_quantity.text(),
            material_shelf_life=self.material_shelf_life.text(),
            env_temp_min=self.env_temp_min.value(),
            env_temp_max=self.env_temp_max.value(),
            env_humidity_min=self.env_hum_min.value(),
            env_humidity_max=self.env_hum_max.value(),
            airflow=self.airflow.text(),
            env_cleanroom_class=self.env_cleanroom_class.text(),
            machine=self.machine.text(),
            tools=self.tools.text(),
            software=self.software.text(),
            power_kw=self.power_kw.value(),
            compressed_air_bar=self.compressed_air.value(),
            vacuum=self.vacuum.text(),
            cooling=self.cooling.text(),
            floorarea=self.floorarea.text(),
            eqpheight=self.eqpheight.text(),
            weight=self.eqp_weight.value(),
            other_equipment=self.other_equipment.text(),
            inspection_methods=self.inspection_list.selected_items(),
            inspection_points=self.inspection_points.text(),
            sampling_plan=self.sampling_plan.text(),
            tolerances=self.tolerances.text(),
            surface_quality=self.surface_quality.text(),
            acceptance_criteria=self.acceptance_criteria.toPlainText(),
            nonacceptance_handling=self.nonacceptance_handling.text(),
            required_docs=self.required_docs.text(),
            required_training=self.required_training.text(),
            requirement_source=self.requirement_source.text(),
            ppe=self.ppe.text(),
            chemical_risks=self.chemical_risks.text(),
            thermal_risks=self.thermal_risks.text(),
            mechanical_risks=self.mechanical_risks.text(),
            esd_risks=self.esd_risks.text(),
            other_safety=self.other_safety.text(),
            post_processing=self.post_processing.toPlainText(),
            notes=self.notes.toPlainText(),
            parameters=params,
        )


# ---------------------------------------------------------------------------
# Inspection method checklist widget
# ---------------------------------------------------------------------------
class _InspectionSelector(QListWidget):
    def __init__(self, catalog: dict):
        super().__init__()
        for category, items in catalog.items():
            header = QListWidgetItem(category)
            header.setFlags(Qt.ItemFlag.ItemIsEnabled)
            header.setForeground(QColor("#0055aa"))
            self.addItem(header)
            for item_text in items:
                entry = QListWidgetItem("  " + item_text)
                entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                entry.setCheckState(Qt.CheckState.Unchecked)
                self.addItem(entry)

    def selected_items(self) -> list[str]:
        result = []
        for i in range(self.count()):
            item = self.item(i)
            if (item.flags() & Qt.ItemFlag.ItemIsUserCheckable and
                    item.checkState() == Qt.CheckState.Checked):
                result.append(item.text().strip())
        return result

    def set_selected(self, names: list[str]):
        for i in range(self.count()):
            item = self.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                state = Qt.CheckState.Checked if item.text().strip() in names else Qt.CheckState.Unchecked
                item.setCheckState(state)
