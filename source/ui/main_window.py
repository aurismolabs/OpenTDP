# ui/main_window.py
import shutil

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QToolBar,
    QPushButton, QFileDialog, QMessageBox, QScrollArea, QInputDialog,
    QLineEdit, QComboBox, QAbstractSpinBox, QDateEdit, QDateTimeEdit,
    QLabel, QSizePolicy
)
from PyQt6.QtCore import QObject, QEvent

from models.tdp_package import TDPPackage

from ui.metadata_tab import MetadataTab
from ui.version_tab import VersionTab
from ui.geometry_tab import GeometryTab
from ui.manufacturing_tab import ManufacturingTab
from ui.amdata_tab import AMDataTab
from ui.analytics_window import AnalyticsWindow
from ui.quality_tab import QualityTab
from ui.packing_tab import PackingAndSafetyTab
from ui.optional_tab import OptionalDataTab

import os, subprocess, sys as _sys
from services import tdp_io, validation
from services.validation import derive_criticality, _at_least_lifecycle, _at_least_criticality
from ui.colours import LC_COLOURS, CRIT_COLOURS


class _WheelBlocker(QObject):
    """Event filter that ignores wheel events on input widgets."""
    _BLOCKED = (QComboBox, QAbstractSpinBox, QDateEdit, QDateTimeEdit)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.Wheel
                and isinstance(obj, self._BLOCKED)):
            event.ignore()
            return True
        return super().eventFilter(obj, event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TDP Package Builder")
        self.resize(1280, 860)

        self._current_path: str | None = None   # path of the open .tdp file
        self._extract_dir: str | None = None    # temp dir from last load (for cleanup)
        self._dirty: bool = False               # unsaved changes flag

        # ------------------------------------------------------------------
        # Tabs
        # ------------------------------------------------------------------
        self.tabs = QTabWidget()

        self.metadata_tab     = MetadataTab()
        self.version_tab      = VersionTab(self)
        self.geometry_tab     = GeometryTab()
        self.amdata_tab       = AMDataTab()
        self.manufacturing_tab = ManufacturingTab(self)
        self.quality_tab      = QualityTab()
        self.packing_tab      = PackingAndSafetyTab()
        self.optional_tab     = OptionalDataTab()

        # 3-D preview: geometry preview signal → metadata tab viewer
        self.geometry_tab.preview_changed.connect(self._on_preview_changed)

        for widget, label in [
            (self.metadata_tab,      "Metadata"),
            (self.version_tab,       "Version Control"),
            (self.quality_tab,       "Quality Assurance"),
            (self.geometry_tab,      "Geometry"),
            (self.amdata_tab,        "Build Data"),
            (self.manufacturing_tab, "Manufacturing"),
            (self.packing_tab,       "Logistics and Safety"),
            (self.optional_tab,      "Additional Data"),
        ]:
            self.tabs.addTab(self._scrollable(widget), label)

        central = QWidget()
        QVBoxLayout(central).addWidget(self.tabs)
        self.setCentralWidget(central)

        # Map tab index → (widget, original_label) for error highlighting
        self._tab_widgets = [
            (self.metadata_tab,      "Metadata"),
            (self.version_tab,       "Version Control"),
            (self.quality_tab,       "Quality Assurance"),
            (self.geometry_tab,      "Geometry"),
            (self.amdata_tab,        "Build Data"),
            (self.manufacturing_tab, "Manufacturing"),
            (self.packing_tab,       "Logistics and Safety"),
            (self.optional_tab,      "Additional Data"),
        ]

        # Propagate state changes to field highlighting
        self.metadata_tab.lifecycle_status.currentIndexChanged.connect(
            self._update_field_states)
        self.metadata_tab.tdp_id.textChanged.connect(self._mark_dirty)
        self.metadata_tab.name.textChanged.connect(self._mark_dirty)
        self.metadata_tab.lifecycle_status.currentIndexChanged.connect(self._mark_dirty)
        self.quality_tab.technical_perf.currentIndexChanged.connect(
            self._update_field_states)
        self.quality_tab.safety_crit.currentIndexChanged.connect(
            self._update_field_states)
        self.quality_tab.technical_perf.currentIndexChanged.connect(
            self._update_tab_colours)
        self.quality_tab.safety_crit.currentIndexChanged.connect(
            self._update_tab_colours)
        self.amdata_tab.files_changed.connect(self._update_tab_colours)

        # Re-colour tabs whenever any field on any tab changes
        for tab, _ in self._tab_widgets:
            if hasattr(tab, 'data_changed'):
                tab.data_changed.connect(self._update_tab_colours)
        self.amdata_tab.files_changed.connect(self._update_tab_colours)
        self.quality_tab.technical_perf.currentIndexChanged.connect(
            self._update_tab_colours)
        self.quality_tab.safety_crit.currentIndexChanged.connect(
            self._update_tab_colours)

        # ------------------------------------------------------------------
        # Toolbar  (must be built before _update_field_states is called)
        # ------------------------------------------------------------------
        toolbar = QToolBar("Actions")
        self.addToolBar(toolbar)

        for label, slot in [
            ("New",       self._new),
            ("Load TDP",  self._load),
            ("Save TDP",  self._save),
            ("Save As…",  self._save_as),
            ("Analytics",     self._open_analytics),
            ("Specification", self._open_specification),
            ("About",         self._open_info),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)

        # Spacer pushes the criticality badge to the right
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        from PyQt6.QtWidgets import QWidgetAction

        # Lifecycle badge — text colour only, no background
        self._lifecycle_badge = QLabel()
        self._lifecycle_badge.setContentsMargins(8, 4, 4, 4)
        self._lc_badge_action = QWidgetAction(toolbar)
        self._lc_badge_action.setDefaultWidget(self._lifecycle_badge)
        self._lc_badge_action.setVisible(False)
        toolbar.addAction(self._lc_badge_action)

        # Criticality badge — coloured background for all levels
        self._criticality_badge = QLabel()
        self._criticality_badge.setContentsMargins(10, 4, 10, 4)
        self._badge_action = QWidgetAction(toolbar)
        self._badge_action.setDefaultWidget(self._criticality_badge)
        self._badge_action.setVisible(False)
        toolbar.addAction(self._badge_action)

        self._update_field_states()  # show required states immediately on startup

        # Install wheel blocker on all input widgets in all tabs
        self._wheel_blocker = _WheelBlocker(self)
        self._install_wheel_blocker(self)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _install_wheel_blocker(self, parent):
        """Recursively install wheel blocker on all input widgets."""
        from PyQt6.QtWidgets import QComboBox, QAbstractSpinBox, QDateEdit, QDateTimeEdit
        for child in parent.findChildren(
                (QComboBox, QAbstractSpinBox, QDateEdit, QDateTimeEdit)):
            child.installEventFilter(self._wheel_blocker)

    def _update_tab_colours(self):
        """Colour tab buttons red/normal based on each tab's has_errors() result."""
        from PyQt6.QtGui import QColor, QPalette
        bar = self.tabs.tabBar()

        ERROR_BG   = QColor("#fee2e2")
        ERROR_FG   = QColor("#991b1b")
        NORMAL_FG  = QColor()          # invalid = reset to default

        for i, (tab, label) in enumerate(self._tab_widgets):
            has_err = tab.has_errors()

            # Text colour via tabBar API — works on all platforms
            bar.setTabTextColor(i, ERROR_FG if has_err else NORMAL_FG)

            # Background: set per-tab background via a small wrapper widget
            # stored as the tab's corner/button widget.  The most portable
            # Qt6 approach is to drive a stylesheet on the *tab bar itself*
            # using a fully-rebuilt stylesheet every call.
            # We tag each tab label with a zero-width prefix so Qt re-evaluates
            # the rule without any selector tricks.
            # Simplest reliable approach: rebuild full tabBar stylesheet.
        self._rebuild_tabbar_stylesheet()

    def _rebuild_tabbar_stylesheet(self):
        """Update tab text markers and colour stripes."""
        bar = self.tabs.tabBar()
        for i, (tab, label) in enumerate(self._tab_widgets):
            has_err = tab.has_errors()
            marker = "⚠ " if has_err else ""
            expected = marker + label
            if bar.tabText(i) != expected:
                bar.setTabText(i, expected)
        self._apply_tab_button_colours()

    def _apply_tab_button_colours(self):
        """
        Most reliable cross-platform tab colouring in Qt6:
        insert a small coloured QFrame as the LeftSide tab button.
        This draws a coloured stripe on the left edge of each tab.
        """
        from PyQt6.QtWidgets import QFrame
        from PyQt6.QtGui import QColor
        bar = self.tabs.tabBar()

        for i, (tab, label) in enumerate(self._tab_widgets):
            has_err = tab.has_errors()

            # Create or reuse a 4-px coloured stripe widget
            existing = bar.tabButton(i, bar.ButtonPosition.LeftSide)
            if has_err:
                stripe = QFrame()
                stripe.setFixedSize(4, 18)
                stripe.setStyleSheet(
                    "QFrame { background-color: #ef4444;"
                    " border-radius: 2px; margin: 2px 0px; }"
                )
                bar.setTabButton(i, bar.ButtonPosition.LeftSide, stripe)
            else:
                # Remove stripe
                bar.setTabButton(i, bar.ButtonPosition.LeftSide, None)

    def _update_field_states(self):
        """Recalculate which fields are required and update their styling."""
        status = self.metadata_tab.lifecycle_status.currentText()
        from models.quality import QualityData, RiskData
        mock_quality = QualityData(risks=RiskData(
            technical_performance=self.quality_tab.technical_perf.currentText(),
            safety_criticality=self.quality_tab.safety_crit.currentText(),
        ))
        level = derive_criticality(mock_quality)

        # Non-critical: skip In Review, auto-Approved approval status
        non_critical = (level == "Non-critical")
        self.metadata_tab.set_non_critical_lifecycle(non_critical)
        self.quality_tab.set_non_critical(non_critical)

        # In Review+: geometry
        in_review_plus = _at_least_lifecycle(status, "In Review")
        self.geometry_tab.refresh_banner(in_review_plus)

        # Overview: description + method + material all require Approved+/Medium+
        detail_req = (
            _at_least_lifecycle(status, "Approved") and
            _at_least_criticality(level, "Medium")
        )
        self.manufacturing_tab.set_overview_required(detail_req, detail_req)

        # Process options/steps: Approved+ and High+
        process_req = (
            _at_least_lifecycle(status, "Approved") and
            _at_least_criticality(level, "High")
        )
        self.manufacturing_tab.set_process_required(process_req)

        # Build files: recommended for High+ (any lifecycle)
        build_req = _at_least_criticality(level, "High")
        self.amdata_tab.set_build_required(build_req)

        # Revision stamp: Approved+
        self.version_tab.set_revision_required(
            _at_least_lifecycle(status, "Approved")
        )

        # Quality: risks In Review+/Low+; approval Approved+
        self.quality_tab.set_lifecycle(status)
        risks_req = (
            in_review_plus and _at_least_criticality(level, "Low")
        )
        self.quality_tab.set_identified_risks_required(risks_req)
        self.quality_tab.set_approval_required(
            _at_least_lifecycle(status, "Approved")
        )

        # Lifecycle badge — text colour from centralised LC_COLOURS
        lc_fg = LC_COLOURS.get(status, ('#374151', '#ffffff'))[0]
        lc_text = status
        self._lifecycle_badge.setText(lc_text)
        self._lifecycle_badge.setStyleSheet(
            f"QLabel {{"
            f"  color: {lc_fg};"
            f"  font-weight: bold;"
            f"  font-size: 14px;"
            f"  background: transparent;"
            f"}}"
        )
        self._lc_badge_action.setVisible(True)

        # Criticality badge — from centralised CRIT_COLOURS
        crit_fg, crit_bg = CRIT_COLOURS.get(level, ('#f3f4f6', '#374151'))
        self._criticality_badge.setText(f"  Criticality: {level}  ")
        self._criticality_badge.setStyleSheet(
            f"QLabel {{"
            f"  background-color: {crit_bg};"
            f"  color: {crit_fg};"
            f"  border-radius: 4px;"
            f"  font-weight: bold;"
            f"  font-size: 14px;"
            f"  letter-spacing: 0.3px;"
            f"}}"
        )
        self._badge_action.setVisible(True)

        # Update tab colours based on error state
        self._update_tab_colours()

    def _open_info(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt6.QtCore import Qt
        dlg = QDialog(self)
        dlg.setWindowTitle("About TDP Package Builder")
        dlg.setMinimumWidth(460)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 20)

        def _lbl(text, size=10, bold=False, colour='#1e3a5f', align=Qt.AlignmentFlag.AlignLeft):
            l = QLabel(text)
            l.setWordWrap(True)
            l.setAlignment(align)
            l.setStyleSheet(
                f'font-size:{size}px; font-weight:{"bold" if bold else "normal"};'
                f' color:{colour};')
            return l

        from PyQt6.QtWidgets import QFrame
        def _hr():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet('color:#cbd5e1;')
            return line

        layout.addWidget(_lbl('TDP Package Builder', size=18, bold=True,
                               align=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(_lbl('Version v20260909a  —  Alpha Release', size=11, colour='#374151',
                               align=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(_lbl(
            'This is an Alpha version of both the TDP Package Builder application '
            'and the OpenTDP "FIN TDP" specification.',
            size=9, colour='#854d0e', align=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(_hr())

        layout.addWidget(_lbl('Producer', size=9, bold=True, colour='#6b7280'))
        layout.addWidget(_lbl('V. Viljanen', size=11))
        layout.addWidget(_lbl('fintdp@outlook.com', size=10, colour='#0369a1'))
        layout.addWidget(_hr())

        layout.addWidget(_lbl('License', size=9, bold=True, colour='#6b7280'))
        layout.addWidget(_lbl('GNU General Public License v3 (GPLv3)', size=10))
        layout.addWidget(_hr())

        layout.addWidget(_lbl('Distribution', size=9, bold=True, colour='#6b7280'))
        layout.addWidget(_lbl('https://github.com/aurismo/OpenTDP', size=10, colour='#0369a1'))
        layout.addWidget(_hr())

        layout.addWidget(_lbl('Development', size=9, bold=True, colour='#6b7280'))
        layout.addWidget(_lbl(
            'Developed using manual programming, GitHub Copilot and Claude.ai.',
            size=10, colour='#374151'))
        layout.addWidget(_hr())

        layout.addWidget(_lbl('About the TDP Specification', size=9, bold=True, colour='#6b7280'))
        layout.addWidget(_lbl(
            'The Technical Data Package (TDP) specification — released as '
            'OpenTDP "FIN TDP" — is designed as an open language for distributed '
            'and advanced manufacturing. Its goal is to enable interoperability '
            'and provide a standardised way to exchange manufacturing information '
            'across organisations, tools and platforms — regardless of the '
            'underlying software or production technology.',
            size=10, colour='#374151'))

        from PyQt6.QtWidgets import QPushButton as _PB
        btn = _PB('Close')
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()

    def _open_specification(self):
        """Open the bundled TDP Specification PDF in the system default viewer."""
        pdf_name = "TDP_Specification_2026-09-06.pdf"
        # Look next to the executable / script first, then CWD
        base = os.path.dirname(os.path.abspath(
            _sys.argv[0] if getattr(_sys, 'frozen', False)
            else __file__))
        # __file__ is ui/main_window.py — go up one level
        candidate = os.path.join(os.path.dirname(base), pdf_name)
        if not os.path.isfile(candidate):
            candidate = os.path.join(base, pdf_name)
        if not os.path.isfile(candidate):
            candidate = os.path.join(os.getcwd(), pdf_name)
        if not os.path.isfile(candidate):
            QMessageBox.warning(self, "Specification",
                f"PDF not found:\n{pdf_name}\n\n"
                "Place the file in the same folder as main.py.")
            return
        try:
            if _sys.platform.startswith('win'):
                os.startfile(candidate)
            elif _sys.platform == 'darwin':
                subprocess.Popen(['open', candidate])
            else:
                subprocess.Popen(['xdg-open', candidate])
        except Exception as e:
            QMessageBox.warning(self, "Specification",
                f"Could not open PDF:\n{e}")

    def _open_analytics(self):
        pkg = self.collect_package()
        dlg = AnalyticsWindow(pkg, self)
        dlg.exec()

    @staticmethod
    def _scrollable(widget: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        return container

    def _on_preview_changed(self, path: str):
        # Forward to metadata tab if it has a 3-D viewer
        if hasattr(self.metadata_tab, "load_geometry_preview"):
            self.metadata_tab.load_geometry_preview(path)

    # ------------------------------------------------------------------
    # Collect all tab data into a TDPPackage
    # ------------------------------------------------------------------
    def collect_package(self) -> TDPPackage:
        pkg = TDPPackage(
            metadata=self.metadata_tab.get_data(),
            version=self.version_tab.get_data(),
            geometry=self.geometry_tab.get_data(),
            overview=self.manufacturing_tab.get_overview(),
            process_options=self.manufacturing_tab.get_options(),
            build_files=self.amdata_tab.get_data(),
            optional=self.optional_tab.get_data(),
            quality=self.quality_tab.get_data(),
            packing=self.packing_tab.get_data(),
        )
        # Derive criticality from risk scores and stamp onto metadata
        pkg.metadata.criticality_level = derive_criticality(pkg.quality)
        return pkg

    # ------------------------------------------------------------------
    # Populate all tabs from a TDPPackage
    # ------------------------------------------------------------------
    def _populate(self, pkg: TDPPackage):
        self.metadata_tab.load_data(pkg.metadata)
        self.version_tab.load_data(pkg.version)
        self.geometry_tab.load_data(pkg.geometry)
        self.amdata_tab.load_data(pkg.build_files)
        self.manufacturing_tab.load_overview(pkg.overview)
        self.manufacturing_tab.load_options(pkg.process_options)
        self.quality_tab.load_data(pkg.quality)
        self.packing_tab.load_data(pkg.packing)
        self.optional_tab.load_data(pkg.optional)
        self._update_field_states()

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------
    def _new(self):
        reply = QMessageBox.question(
            self, "New Package",
            "Discard current data and start a new empty package?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cleanup_extract_dir()
            self._current_path = None
            self._populate(TDPPackage())
            self._dirty = False
            self.setWindowTitle("TDP Package Builder — New Package")

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open TDP Package", "", "TDP Files (*.tdp)"
        )
        if not path:
            return
        try:
            pkg, extract_dir = tdp_io.load_tdp(path)
        except tdp_io.TDPLoadError as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return

        self._cleanup_extract_dir()
        self._extract_dir = extract_dir
        self._current_path = path
        self._populate(pkg)
        self._dirty = False
        self.setWindowTitle(f"TDP Package Builder — {path}")

    def _save(self):
        if not self._current_path:
            self._save_as()
            return
        self._do_save(self._current_path)

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save TDP Package As", "", "TDP Files (*.tdp)"
        )
        if not path:
            return
        if not path.endswith(".tdp"):
            path += ".tdp"
        self._current_path = path
        self._do_save(path)

    def _do_save(self, path: str):
        pkg = self.collect_package()

        # Validate (also stamps criticality_level onto pkg.metadata)
        errors = validation.validate(pkg)
        level = pkg.metadata.criticality_level

        if errors:
            reply = QMessageBox.warning(
                self, "Validation Warnings",
                f"Derived criticality level: <b>{level}</b><br><br>"
                "The following requirements are not met:<br><br>" +
                "<br>".join(f"• {e}" for e in errors) +
                "<br><br>Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Ask for author name for the automatic change entry
        author, ok = QInputDialog.getText(
            self, "Change Author",
            f"Your name for the change log entry:\n(Criticality: {level})",
            QLineEdit.EchoMode.Normal,
            pkg.metadata.author,
        )
        if not ok:
            author = pkg.metadata.author

        try:
            tdp_io.save_tdp(path, pkg, author=author)
        except tdp_io.TDPSaveError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return

        # Reload from saved file so ChangeHistory reflects what was written
        try:
            saved_pkg, _ = tdp_io.load_tdp(path)
            self.version_tab.load_data(saved_pkg.version)
        except Exception:
            self.version_tab.load_data(pkg.version)  # fallback
        self.setWindowTitle(f"TDP Package Builder — {path}")
        self._dirty = False
        QMessageBox.information(
            self, "Saved",
            f"TDP package saved to:\n{path}\n\nCriticality level: {level}"
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def _cleanup_extract_dir(self):
        if self._extract_dir:
            try:
                shutil.rmtree(self._extract_dir, ignore_errors=True)
            except Exception:
                pass
            self._extract_dir = None

    def _mark_dirty(self):
        self._dirty = True

    def closeEvent(self, event):
        if self._dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Close without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        self._cleanup_extract_dir()
        super().closeEvent(event)
