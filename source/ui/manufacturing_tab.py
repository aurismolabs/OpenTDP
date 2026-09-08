# ui/manufacturing_tab.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QListWidget, QListWidgetItem, QLabel
)

from models.manufacturing import ManufacturingOverview, ProcessOption, ProcessStep
from ui.step_editor import StepEditor
from ui.process_option_editor import ProcessOptionEditor
from ui.field_state import update_states, clear_state, REQUIRED_EMPTY, REQUIRED_FILLED


class ManufacturingTab(QWidget):
    data_changed = pyqtSignal()
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self._options: list[ProcessOption] = []
        self._current_option_idx: int | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(self._overview_group())
        layout.addWidget(self._options_group())
        layout.addStretch()

        self.steps_list.itemDoubleClicked.connect(self._edit_step)
        self.options_list.itemDoubleClicked.connect(self._edit_option)

        # Live field-state highlighting for overview fields
        self.description.textChanged.connect(self._refresh_states)
        self.mfg_method.textChanged.connect(self._refresh_states)
        self.material.textChanged.connect(self._refresh_states)

    # ------------------------------------------------------------------
    # UI groups
    # ------------------------------------------------------------------
    def _overview_group(self):
        group = QGroupBox("Process Overview  (required at criticality: Medium+)")
        form = QFormLayout()

        self.description = QTextEdit()
        self.description.setFixedHeight(70)
        self.description.setPlaceholderText("General manufacturing instructions and context")

        self.mfg_method = QLineEdit()
        self.mfg_method.setPlaceholderText("e.g. Fused Deposition Modelling (FDM)")

        self.material = QLineEdit()
        self.material.setPlaceholderText("e.g. PLA, AlSi10Mg")

        self.standards = QTextEdit()
        self.standards.setFixedHeight(70)
        self.standards.setPlaceholderText("One standard per line, e.g.\nAQAP-2110\nISO 9001")

        form.addRow("General Instructions:", self.description)
        form.addRow("Manufacturing Method:", self.mfg_method)
        form.addRow("Material:", self.material)
        form.addRow("Standards (one per line):", self.standards)
        group.setLayout(form)
        return group

    def _options_group(self):
        group = QGroupBox("Process Options and Steps  (required at criticality: High+)")
        layout = QHBoxLayout()

        # Left: options list
        left = QVBoxLayout()
        left.addWidget(QLabel("Options"))
        self._options_banner = QLabel()
        self._options_banner.setContentsMargins(4, 3, 4, 3)
        left.addWidget(self._options_banner)
        self.options_list = QListWidget()
        self.options_list.currentRowChanged.connect(self._select_option)
        left.addWidget(self.options_list)

        opt_btns = QHBoxLayout()
        btn_add_opt = QPushButton("Add Option")
        btn_add_opt.clicked.connect(self._add_option)
        btn_del_opt = QPushButton("Remove")
        btn_del_opt.clicked.connect(self._remove_option)
        opt_btns.addWidget(btn_add_opt)
        opt_btns.addWidget(btn_del_opt)
        left.addLayout(opt_btns)

        # Right: steps list
        right = QVBoxLayout()
        right.addWidget(QLabel("Steps  (double-click to edit)"))
        self._steps_banner = QLabel()
        self._steps_banner.setContentsMargins(4, 3, 4, 3)
        right.addWidget(self._steps_banner)
        self.steps_list = QListWidget()
        right.addWidget(self.steps_list)

        step_btns = QHBoxLayout()
        btn_add_step = QPushButton("Add Step")
        btn_add_step.clicked.connect(self._add_step)
        btn_del_step = QPushButton("Remove")
        btn_del_step.clicked.connect(self._remove_step)
        step_btns.addWidget(btn_add_step)
        step_btns.addWidget(btn_del_step)
        right.addLayout(step_btns)

        layout.addLayout(left)
        layout.addLayout(right)
        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------
    # Option handlers
    # ------------------------------------------------------------------
    def _add_option(self):
        dlg = ProcessOptionEditor(self)
        if dlg.exec():
            opt = ProcessOption.from_xml_dict(dlg.get_data())
            self._options.append(opt)
            rev = f" r{opt.revision}" if opt.revision else ""
            self.options_list.addItem(f"{opt.option_name}{rev}  [{opt.maturity}]")
            self._update_list_banners()

    def _edit_option(self):
        idx = self.options_list.currentRow()
        if idx < 0:
            return
        dlg = ProcessOptionEditor(self, existing=self._options[idx])
        if dlg.exec():
            data = dlg.get_data()
            # preserve existing steps
            data["Steps"] = [s.to_xml_dict() for s in self._options[idx].steps]
            updated = ProcessOption.from_xml_dict(data)
            self._options[idx] = updated
            rev = f" r{updated.revision}" if updated.revision else ""
            self.options_list.item(idx).setText(f"{updated.option_name}{rev}  [{updated.maturity}]")
            self._update_list_banners()

    def _remove_option(self):
        idx = self.options_list.currentRow()
        if idx >= 0:
            self._options.pop(idx)
            self.options_list.takeItem(idx)
            self.steps_list.clear()
            self._current_option_idx = None
            self._update_list_banners()

    def _select_option(self, idx: int):
        if idx < 0 or idx >= len(self._options):
            self._current_option_idx = None
            self.steps_list.clear()
            return
        self._current_option_idx = idx
        self._refresh_steps_list()

    def _refresh_steps_list(self):
        self.steps_list.clear()
        if self._current_option_idx is None:
            return
        # Sort by (sequence, id) — tie-break on Step ID when sequences are equal
        sorted_steps = sorted(
            self._options[self._current_option_idx].steps,
            key=lambda s: (s.sequence, s.id)
        )
        for s in sorted_steps:
            item = QListWidgetItem(f"{s.sequence:03d}  {s.name}  [{s.id}]")
            # Store the step ID in UserRole so selection always finds the right step
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self.steps_list.addItem(item)
        self._update_list_banners()

    def _step_id_from_row(self, row: int) -> str | None:
        """Return the step ID stored in the list item at *row*, or None."""
        item = self.steps_list.item(row)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _find_step_by_id(self, step_id: str):
        """Return (list_index, step) for the step with matching ID, or (None, None)."""
        steps = self._options[self._current_option_idx].steps
        for i, s in enumerate(steps):
            if s.id == step_id:
                return i, s
        return None, None

    # ------------------------------------------------------------------
    # Step handlers
    # ------------------------------------------------------------------
    def _add_step(self):
        if self._current_option_idx is None:
            return
        dlg = StepEditor(
            parent=self,
            geometry_list=self.mainwindow.geometry_tab.get_data(),
            build_files=self.mainwindow.amdata_tab.get_data(),
        )
        if dlg.exec():
            step = dlg.get_data()
            self._options[self._current_option_idx].steps.append(step)
            self._refresh_steps_list()

    def _edit_step(self):
        if self._current_option_idx is None:
            return
        row = self.steps_list.currentRow()
        if row < 0:
            return
        step_id = self._step_id_from_row(row)
        data_idx, existing = self._find_step_by_id(step_id)
        if existing is None:
            return
        dlg = StepEditor(
            parent=self,
            geometry_list=self.mainwindow.geometry_tab.get_data(),
            build_files=self.mainwindow.amdata_tab.get_data(),
            existing=existing,
        )
        if dlg.exec():
            self._options[self._current_option_idx].steps[data_idx] = dlg.get_data()
            self._refresh_steps_list()

    def _remove_step(self):
        if self._current_option_idx is None:
            return
        row = self.steps_list.currentRow()
        if row < 0:
            return
        step_id = self._step_id_from_row(row)
        data_idx, _ = self._find_step_by_id(step_id)
        if data_idx is not None:
            self._options[self._current_option_idx].steps.pop(data_idx)
            self._refresh_steps_list()

    # ------------------------------------------------------------------
    # Data I/O
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Field-state highlighting
    # ------------------------------------------------------------------
    def has_errors(self) -> bool:
        """True if any required manufacturing field is missing."""
        if getattr(self, '_desc_required', False):
            if not self.description.toPlainText().strip(): return True
        if getattr(self, '_detail_required', False):
            if not self.mfg_method.text().strip(): return True
            if not self.material.text().strip(): return True
        if getattr(self, '_process_required', False):
            if not self._options: return True
            if not any(opt.steps for opt in self._options): return True
        return False

    def set_overview_required(self, desc_req: bool, detail_req: bool) -> None:
        """Called by MainWindow.
        desc_req   — Description required (In Review+).
        detail_req — Method + Material required (Approved+/Medium+).
        """
        self._desc_required   = desc_req
        self._detail_required = detail_req
        self._refresh_states()
        for sig in [
            self.description.textChanged,
            self.mfg_method.textChanged,
            self.material.textChanged,
        ]:
            sig.connect(self._emit_changed)

    def set_process_required(self, required: bool) -> None:
        """Called by MainWindow when High+ criticality applies."""
        self._process_required = required
        self._update_list_banners()

    def _emit_changed(self):
        self.data_changed.emit()

    def _refresh_states(self):
        desc_req   = getattr(self, '_desc_required',   False)
        detail_req = getattr(self, '_detail_required', False)
        states = {}
        if desc_req:
            states[self.description] = bool(self.description.toPlainText().strip())
        else:
            clear_state(self.description)
        if detail_req:
            states[self.mfg_method] = bool(self.mfg_method.text().strip())
            states[self.material]   = bool(self.material.text().strip())
        else:
            clear_state(self.mfg_method)
            clear_state(self.material)
        if states:
            update_states(states)
        self._update_list_banners()

    def _update_list_banners(self) -> None:
        """Update option/step banners. Called whenever lists change."""
        options_req = getattr(self, '_overview_required', False)  # High+ also needs options
        # We show banners whenever overview is required (Medium+) as a minimum;
        # MainWindow sets _process_required separately for High+
        proc_req = getattr(self, '_process_required', False)

        # Options banner
        n_opts = self.options_list.count()
        if proc_req:
            if n_opts == 0:
                self._options_banner.setText("  ⚠  At least one Process Option is required")
                self._options_banner.setStyleSheet(REQUIRED_EMPTY + "color:#b91c1c;font-weight:bold;")
            else:
                self._options_banner.setText(f"  ✓  {n_opts} Process Option{'s' if n_opts > 1 else ''}")
                self._options_banner.setStyleSheet(REQUIRED_FILLED + "color:#166534;font-weight:bold;")
        else:
            self._options_banner.setText("")
            self._options_banner.setStyleSheet("")

        # Steps banner — based on currently selected option
        idx = self._current_option_idx
        if proc_req and idx is not None:
            n_steps = len(self._options[idx].steps)
            if n_steps == 0:
                self._steps_banner.setText("  ⚠  At least one Process Step is required")
                self._steps_banner.setStyleSheet(REQUIRED_EMPTY + "color:#b91c1c;font-weight:bold;")
            else:
                self._steps_banner.setText(f"  ✓  {n_steps} Process Step{'s' if n_steps > 1 else ''}")
                self._steps_banner.setStyleSheet(REQUIRED_FILLED + "color:#166534;font-weight:bold;")
        elif proc_req and n_opts > 0 and idx is None:
            self._steps_banner.setText("  ↑  Select an option to view its steps")
            self._steps_banner.setStyleSheet("color:#6b7280;")
        else:
            self._steps_banner.setText("")
            self._steps_banner.setStyleSheet("")

    def get_overview(self) -> ManufacturingOverview:
        return ManufacturingOverview(
            description=self.description.toPlainText().strip(),
            manufacturing_method=self.mfg_method.text().strip(),
            material=self.material.text().strip(),
            standards=[s.strip() for s in self.standards.toPlainText().splitlines() if s.strip()],
        )

    def get_options(self) -> list[ProcessOption]:
        return list(self._options)

    def load_overview(self, ov: ManufacturingOverview):
        self.description.setPlainText(ov.description)
        self.mfg_method.setText(ov.manufacturing_method)
        self.material.setText(ov.material)
        self.standards.setPlainText("\n".join(ov.standards))
        self._refresh_states()

    def load_options(self, options: list[ProcessOption]):
        self._options = list(options)
        self.options_list.clear()
        self.steps_list.clear()
        self._current_option_idx = None
        for opt in self._options:
            rev = f" r{opt.revision}" if opt.revision else ""
            self.options_list.addItem(f"{opt.option_name}{rev}  [{opt.maturity}]")
        if self._options:
            self.options_list.setCurrentRow(0)
        self._update_list_banners()
