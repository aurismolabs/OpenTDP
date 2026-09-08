# ui/packing_tab.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QCheckBox, QDoubleSpinBox,
    QSpinBox, QLabel, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QFrame, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from models.packing import PackingAndSafety


# ── Collapsible section ───────────────────────────────────────────────────────

class CollapsibleSection(QWidget):
    """Titled collapsible container — collapsed by default."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._collapsed = True

        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 6)

        # Header
        header = QWidget()
        header.setStyleSheet(
            "QWidget { background:#e8e8e8; border:1px solid #c8c8c8;"
            " border-radius:4px; }"
        )
        header.setFixedHeight(30)
        header.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Fixed)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.mousePressEvent = lambda _: self.toggle()

        hl = QHBoxLayout(header)
        hl.setContentsMargins(6, 0, 6, 0)
        hl.setSpacing(4)

        self._arrow = QToolButton()
        self._arrow.setArrowType(Qt.ArrowType.RightArrow)
        self._arrow.setStyleSheet("QToolButton{border:none;background:transparent;}")
        self._arrow.clicked.connect(self.toggle)

        lbl = QLabel(title)
        f = QFont(); f.setBold(True)
        lbl.setFont(f)
        lbl.setStyleSheet("color:#333333; background:transparent;")

        hl.addWidget(self._arrow)
        hl.addWidget(lbl)
        hl.addStretch()
        outer.addWidget(header)

        # Content wrapper — holds the original group widget unchanged
        self._content = QWidget()
        self._content.setVisible(False)
        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        outer.addWidget(self._content)

        self._content_layout = cl

    def set_widget(self, widget: QWidget):
        """Place an existing widget (e.g. QGroupBox) inside the section."""
        self._content_layout.addWidget(widget)

    def toggle(self):
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        self._arrow.setArrowType(
            Qt.ArrowType.DownArrow if not self._collapsed
            else Qt.ArrowType.RightArrow
        )

    def expand(self):
        if self._collapsed:
            self.toggle()


# ── Tab ───────────────────────────────────────────────────────────────────────

class PackingAndSafetyTab(QWidget):
    data_changed = pyqtSignal()
    def __init__(self):
        super().__init__()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(4)
        lay.setContentsMargins(8, 8, 8, 8)

        # Build original group boxes exactly as before
        self._grp_packing   = self._packing_group()
        self._grp_handling  = self._handling_group()
        self._grp_transport = self._transport_group()
        self._grp_safety    = self._safety_group()

        # Wrap each in a collapsible section
        self._sec_packing   = CollapsibleSection("Packing Requirements")
        self._sec_handling  = CollapsibleSection("Handling Instructions")
        self._sec_transport = CollapsibleSection("Transport Requirements")
        self._sec_safety    = CollapsibleSection("Safety Information")

        self._sec_packing.set_widget(self._grp_packing)
        self._sec_handling.set_widget(self._grp_handling)
        self._sec_transport.set_widget(self._grp_transport)
        self._sec_safety.set_widget(self._grp_safety)

        for sec in (self._sec_packing, self._sec_handling,
                    self._sec_transport, self._sec_safety):
            lay.addWidget(sec)

        lay.addStretch()
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ── Original group builders (unchanged from previous version) ─────────────

    def _packing_group(self):
        from PyQt6.QtWidgets import QGroupBox
        g = QGroupBox("Packing Requirements")
        grid = QGridLayout()
        r = 0

        self.packing_material = QComboBox()
        self.packing_material.addItems([
            "", "Paper and cardboard", "Plastics", "Metals", "Glass",
            "Wood and wood-based materials", "Ceramics",
            "Textiles and fiber materials", "Elastomers and rubber",
            "Composite and multilayer materials",
            "Active and intelligent packaging materials",
        ])
        self.packing_material.wheelEvent = lambda e: e.ignore()

        self.cushioning         = QLineEdit()
        self.moisture           = QLineEdit()
        self.surface_protection = QLineEdit()
        self.other_labels       = QLineEdit()

        self.chk_fragile  = QCheckBox("Fragile")
        self.chk_side_up  = QCheckBox("This Side Up")
        self.chk_no_stack = QCheckBox("Do Not Stack")
        self.chk_esd      = QCheckBox("ESD Sensitive")

        for label, widget in [
            ("Packing Material:", self.packing_material),
            ("Cushioning:",       self.cushioning),
            ("Moisture Protection:", self.moisture),
            ("Surface Protection:", self.surface_protection),
            ("Other Labels:",     self.other_labels),
        ]:
            grid.addWidget(QLabel(label), r, 0)
            grid.addWidget(widget, r, 1)
            r += 1

        chk_row = QHBoxLayout()
        for chk in (self.chk_fragile, self.chk_side_up,
                    self.chk_no_stack, self.chk_esd):
            chk_row.addWidget(chk)
        chk_row.addStretch()
        grid.addWidget(QLabel("Warning Labels:"), r, 0)
        grid.addLayout(chk_row, r, 1)

        g.setLayout(grid)
        return g

    def _handling_group(self):
        from PyQt6.QtWidgets import QGroupBox
        g = QGroupBox("Handling Instructions")
        form = QFormLayout()

        self.allowed_lifting   = QTextEdit(); self.allowed_lifting.setFixedHeight(55)
        self.forbidden_lifting = QTextEdit(); self.forbidden_lifting.setFixedHeight(55)
        self.cog_description   = QLineEdit()
        self.handling_forces   = QLineEdit()
        self.esd_requirements  = QLineEdit()

        form.addRow("Allowed Lifting Methods:",   self.allowed_lifting)
        form.addRow("Forbidden Lifting Methods:", self.forbidden_lifting)
        form.addRow("Centre of Gravity:",         self.cog_description)
        form.addRow("Max Handling Forces:",       self.handling_forces)
        form.addRow("ESD Requirements:",          self.esd_requirements)
        g.setLayout(form)
        return g

    def _transport_group(self):
        from PyQt6.QtWidgets import QGroupBox
        g = QGroupBox("Transport Requirements")
        form = QFormLayout()

        self.transport_orientation = QLineEdit()
        self.securing_method       = QLineEdit()
        self.special_transport     = QLineEdit()
        self.chk_stackable         = QCheckBox("Stackable")
        self.max_stack_layers      = QSpinBox()
        self.max_stack_layers.setRange(0, 100)
        self.max_stack_layers.wheelEvent = lambda e: e.ignore()

        def _dspin(lo, hi, val):
            w = QDoubleSpinBox()
            w.setRange(lo, hi); w.setValue(val)
            w.wheelEvent = lambda e: e.ignore()
            return w

        self.temp_min = _dspin(-100, 9999, -20)
        self.temp_max = _dspin(-100, 9999,  60)
        self.hum_min  = _dspin(0, 100, 10)
        self.hum_max  = _dspin(0, 100, 90)

        temp_row = QHBoxLayout()
        temp_row.addWidget(self.temp_min)
        temp_row.addWidget(QLabel("to"))
        temp_row.addWidget(self.temp_max)
        temp_row.addWidget(QLabel("°C"))

        hum_row = QHBoxLayout()
        hum_row.addWidget(self.hum_min)
        hum_row.addWidget(QLabel("to"))
        hum_row.addWidget(self.hum_max)
        hum_row.addWidget(QLabel("% RH"))

        self.hazmat_list = QListWidget()
        self.hazmat_list.setFixedHeight(80)
        hazmat_input = QLineEdit()
        hazmat_input.setPlaceholderText("Enter UN hazmat class and press Add")
        btn_add = QPushButton("Add")
        btn_rem = QPushButton("Remove")
        btn_add.clicked.connect(lambda: self._add_hazmat(hazmat_input))
        btn_rem.clicked.connect(self._remove_hazmat)
        haz_btns = QHBoxLayout()
        haz_btns.addWidget(hazmat_input)
        haz_btns.addWidget(btn_add)
        haz_btns.addWidget(btn_rem)

        form.addRow("Transport Orientation:", self.transport_orientation)
        form.addRow("Securing Method:",       self.securing_method)
        form.addRow("Temperature Range:",     temp_row)
        form.addRow("Humidity Range:",        hum_row)
        form.addRow("Stackable:",             self.chk_stackable)
        form.addRow("Max Stack Layers:",      self.max_stack_layers)
        form.addRow("Special Transport:",     self.special_transport)
        form.addRow("Hazmat Classes:",        self.hazmat_list)
        form.addRow("",                       haz_btns)
        g.setLayout(form)
        return g

    def _safety_group(self):
        from PyQt6.QtWidgets import QGroupBox
        g = QGroupBox("Safety Information")
        form = QFormLayout()

        self.ppe               = QLineEdit()
        self.edge_risks        = QLineEdit()
        self.item_weight       = QDoubleSpinBox()
        self.item_weight.setRange(0, 999999)
        self.item_weight.wheelEvent = lambda e: e.ignore()
        self.manual_lift_limit = QDoubleSpinBox()
        self.manual_lift_limit.setRange(0, 9999)
        self.manual_lift_limit.wheelEvent = lambda e: e.ignore()
        self.chemical_risks    = QTextEdit(); self.chemical_risks.setFixedHeight(55)
        self.thermal_risks     = QTextEdit(); self.thermal_risks.setFixedHeight(55)
        self.other_safety      = QTextEdit(); self.other_safety.setFixedHeight(55)

        form.addRow("PPE Requirements:",       self.ppe)
        form.addRow("Edge / Sharp Risks:",     self.edge_risks)
        form.addRow("Item Weight (kg):",       self.item_weight)
        form.addRow("Manual Lift Limit (kg):", self.manual_lift_limit)
        form.addRow("Chemical Risks:",         self.chemical_risks)
        form.addRow("Thermal Risks:",          self.thermal_risks)
        form.addRow("Other Safety Notes:",     self.other_safety)
        g.setLayout(form)
        return g

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _add_hazmat(self, line: QLineEdit):
        text = line.text().strip()
        if text:
            self.hazmat_list.addItem(QListWidgetItem(text))
            line.clear()

    def _remove_hazmat(self):
        row = self.hazmat_list.currentRow()
        if row >= 0:
            self.hazmat_list.takeItem(row)

    # ── Standard API ─────────────────────────────────────────────────────────

    def has_errors(self) -> bool:
        return False

    def get_data(self) -> PackingAndSafety:
        hazmat = [self.hazmat_list.item(i).text()
                  for i in range(self.hazmat_list.count())]
        return PackingAndSafety(
            packing_material=self.packing_material.currentText(),
            cushioning=self.cushioning.text(),
            moisture_protection=self.moisture.text(),
            surface_protection=self.surface_protection.text(),
            label_fragile=self.chk_fragile.isChecked(),
            label_this_side_up=self.chk_side_up.isChecked(),
            label_do_not_stack=self.chk_no_stack.isChecked(),
            label_esd=self.chk_esd.isChecked(),
            other_labels=self.other_labels.text(),
            allowed_lifting=self.allowed_lifting.toPlainText(),
            forbidden_lifting=self.forbidden_lifting.toPlainText(),
            cog_description=self.cog_description.text(),
            handling_forces=self.handling_forces.text(),
            esd_requirements=self.esd_requirements.text(),
            transport_orientation=self.transport_orientation.text(),
            hazmat_classes=hazmat,
            securing_method=self.securing_method.text(),
            temp_min=self.temp_min.value(),
            temp_max=self.temp_max.value(),
            humidity_min=self.hum_min.value(),
            humidity_max=self.hum_max.value(),
            stackable=self.chk_stackable.isChecked(),
            max_stack_layers=self.max_stack_layers.value(),
            special_transport=self.special_transport.text(),
            ppe=self.ppe.text(),
            edge_risks=self.edge_risks.text(),
            weight=self.item_weight.value(),
            manual_lift_limit=self.manual_lift_limit.value(),
            chemical_risks=self.chemical_risks.toPlainText(),
            thermal_risks=self.thermal_risks.toPlainText(),
            other_safety=self.other_safety.toPlainText(),
        )

    def load_data(self, p: PackingAndSafety):
        self.packing_material.setCurrentText(p.packing_material)
        self.cushioning.setText(p.cushioning)
        self.moisture.setText(p.moisture_protection)
        self.surface_protection.setText(p.surface_protection)
        self.chk_fragile.setChecked(p.label_fragile)
        self.chk_side_up.setChecked(p.label_this_side_up)
        self.chk_no_stack.setChecked(p.label_do_not_stack)
        self.chk_esd.setChecked(p.label_esd)
        self.other_labels.setText(p.other_labels)
        self.allowed_lifting.setPlainText(p.allowed_lifting)
        self.forbidden_lifting.setPlainText(p.forbidden_lifting)
        self.cog_description.setText(p.cog_description)
        self.handling_forces.setText(p.handling_forces)
        self.esd_requirements.setText(p.esd_requirements)
        self.transport_orientation.setText(p.transport_orientation)
        self.securing_method.setText(p.securing_method)
        self.temp_min.setValue(p.temp_min)
        self.temp_max.setValue(p.temp_max)
        self.hum_min.setValue(p.humidity_min)
        self.hum_max.setValue(p.humidity_max)
        self.chk_stackable.setChecked(p.stackable)
        self.max_stack_layers.setValue(p.max_stack_layers)
        self.special_transport.setText(p.special_transport)
        self.hazmat_list.clear()
        for cls in p.hazmat_classes:
            self.hazmat_list.addItem(QListWidgetItem(cls))
        self.ppe.setText(p.ppe)
        self.edge_risks.setText(p.edge_risks)
        self.item_weight.setValue(p.weight)
        self.manual_lift_limit.setValue(p.manual_lift_limit)
        self.chemical_risks.setPlainText(p.chemical_risks)
        self.thermal_risks.setPlainText(p.thermal_risks)
        self.other_safety.setPlainText(p.other_safety)

        # Auto-expand sections that contain data
        if any([p.packing_material, p.cushioning, p.moisture_protection,
                p.surface_protection, p.other_labels, p.label_fragile,
                p.label_this_side_up, p.label_do_not_stack, p.label_esd]):
            self._sec_packing.expand()
        if any([p.allowed_lifting, p.forbidden_lifting, p.cog_description,
                p.handling_forces, p.esd_requirements]):
            self._sec_handling.expand()
        if any([p.transport_orientation, p.securing_method, p.special_transport,
                p.hazmat_classes, p.stackable, p.temp_min != -20, p.temp_max != 60]):
            self._sec_transport.expand()
        if any([p.ppe, p.edge_risks, p.weight, p.manual_lift_limit,
                p.chemical_risks, p.thermal_risks, p.other_safety]):
            self._sec_safety.expand()
