# ui/analytics_window.py
"""
Analytics window — summarises key metrics derived from the current TDP package.

Scope (kept deliberately simple for v1):
  • Package identity + criticality card
  • Process Options comparison table (duration, steps, operators, inspections)
  • Aggregate totals card
  • Risk & complexity heat indicators
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QGridLayout, QFrame, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from models.tdp_package import TDPPackage
from services.validation import validate
from models.manufacturing import ProcessOption


# ── palette ──────────────────────────────────────────────────────────────────
_PURPLE   = "#4c1d95"; _PURPLE_L = "#ede9fe"
_TEAL     = "#0f6e56"; _TEAL_L   = "#d1fae5"
_AMBER    = "#854d0e"; _AMBER_L  = "#fef9c3"
_RED      = "#991b1b"; _RED_L    = "#fee2e2"
_SLATE    = "#1e3a5f"; _SLATE_L  = "#e8f0fb"
_GRAY     = "#374151"; _GRAY_L   = "#f3f4f6"

_MATURITY_SCORE = {
    "Very Low — Ad hoc / Initial":          1,
    "Low — Repeatable":                     2,
    "Moderate — Defined / Standardized":    3,
    "High — Measured and Controlled":       4,
    "Very High — Optimized":                5,
}

_CRIT_COLOUR = {
    "Non-critical": ("#065f46", "#d1fae5"),
    "Low":          ("#854d0e", "#fef9c3"),
    "Medium":       ("#b45309", "#ffedd5"),
    "High":         ("#991b1b", "#fee2e2"),
    "Very High":    ("#4c1d95", "#ede9fe"),
}


def _opt_duration_min(opt: ProcessOption) -> int:
    """Total duration of all steps in minutes."""
    total = 0
    for s in opt.steps:
        total += s.duration.get("hours", 0) * 60 + s.duration.get("minutes", 0)
    return total


def _fmt_dur(minutes: int) -> str:
    if minutes == 0:
        return "—"
    h, m = divmod(minutes, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def _opt_max_operators(opt: ProcessOption) -> int:
    if not opt.steps:
        return 0
    return max(s.operator_count for s in opt.steps)


def _opt_total_operators_minutes(opt: ProcessOption) -> int:
    """operator-minutes = sum(op_count × step_duration_min)."""
    total = 0
    for s in opt.steps:
        dur = s.duration.get("hours", 0) * 60 + s.duration.get("minutes", 0)
        total += s.operator_count * dur
    return total


def _opt_inspection_count(opt: ProcessOption) -> int:
    return sum(len(s.inspection_methods) for s in opt.steps)


def _opt_safety_flags(opt: ProcessOption) -> int:
    """Count steps that have any safety risk filled."""
    count = 0
    for s in opt.steps:
        if any([s.ppe, s.chemical_risks, s.thermal_risks,
                s.mechanical_risks, s.esd_risks, s.other_safety]):
            count += 1
    return count


def _complexity_score(opt: ProcessOption) -> float:
    """Simple composite 0–10 score:
       steps(×2) + maturity(×1) + inspections(×0.5) + safety_steps(×0.5)
       capped at 10.
    """
    n_steps  = len(opt.steps)
    maturity = _MATURITY_SCORE.get(opt.maturity, 0)
    insp     = _opt_inspection_count(opt)
    safety   = _opt_safety_flags(opt)
    raw = n_steps * 2 + maturity + insp * 0.5 + safety * 0.5
    return round(min(raw, 10.0), 1)


def _score_bar(score: float, max_val: float = 10.0,
               low_col="#4ade80", high_col="#f87171") -> QWidget:
    """Horizontal progress-bar style widget."""
    ratio = min(score / max_val, 1.0)
    container = QWidget()
    container.setFixedHeight(16)
    container.setMinimumWidth(80)
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    bar = QFrame(container)
    # Colour interpolated from green → red
    r = int(0x4a + (0xf8 - 0x4a) * ratio)
    g = int(0xde + (0x87 - 0xde) * ratio)
    b = int(0x80 + (0x71 - 0x80) * ratio)
    colour = f"#{r:02x}{g:02x}{b:02x}"
    bar.setStyleSheet(f"background:{colour}; border-radius:4px;")
    bar.setGeometry(0, 2, max(4, int(container.minimumWidth() * ratio)), 12)

    def _resize(event):
        bar.setGeometry(0, 2, max(4, int(container.width() * ratio)), 12)
    container.resizeEvent = _resize
    return container


# ── Card helpers ──────────────────────────────────────────────────────────────

def _card(title: str, fg: str, bg: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background:{bg}; border:1px solid {fg}40;"
        f"border-radius:8px; padding:4px; }}"
    )
    layout = QVBoxLayout(frame)
    layout.setSpacing(4)
    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"color:{fg}; font-weight:bold; font-size:12px; background:transparent; border:none;"
    )
    layout.addWidget(lbl)
    return frame, layout


def _kv(key: str, value: str, fg: str = _GRAY) -> QLabel:
    lbl = QLabel(f"<b>{key}:</b> {value}")
    lbl.setStyleSheet(f"color:{fg}; background:transparent; border:none; font-size:12px;")
    lbl.setWordWrap(True)
    return lbl


# ═════════════════════════════════════════════════════════════════════════════
class AnalyticsWindow(QDialog):
    def __init__(self, package: TDPPackage, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TDP Analytics")
        self.setMinimumSize(760, 580)
        self.resize(900, 660)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(12, 12, 12, 12)
        scroll_area.setWidget(content)
        root.addWidget(scroll_area)

        opts = package.process_options

        self._build_validation_card(layout, package)
        self._build_identity_card(layout, package)
        if opts:
            self._build_totals_card(layout, opts)
            self._build_options_table(layout, opts)
            self._build_complexity_card(layout, opts)
        else:
            placeholder = QLabel("No Process Options defined yet.")
            placeholder.setStyleSheet("color:#888; font-size:13px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)

        layout.addStretch()

    # ── Identity card ─────────────────────────────────────────────────────────
    def _build_validation_card(self, layout: QVBoxLayout, pkg: TDPPackage):
        """Show validation errors as a summary card, or a green OK card."""
        errors = validate(pkg)
        if not errors:
            card, cl = _card("Validation — All requirements met ✓", _TEAL, _TEAL_L)
            cl.addWidget(_kv("", "No missing required fields.", _TEAL))
        else:
            card, cl = _card(
                f"Validation — {len(errors)} requirement(s) not met",
                _RED, _RED_L
            )
            for i, err in enumerate(errors, 1):
                lbl = QLabel(f"{i}. {err}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"color:{_RED}; font-size:12px;"
                    " background:transparent; border:none;"
                )
                cl.addWidget(lbl)
        layout.addWidget(card)

    def _build_identity_card(self, layout: QVBoxLayout, pkg: TDPPackage):
        crit = pkg.metadata.criticality_level or "Non-critical"
        fg, bg = _CRIT_COLOUR.get(crit, (_GRAY, _GRAY_L))
        card, cl = _card("Package identity", _SLATE, _SLATE_L)
        row = QHBoxLayout()
        row.setSpacing(16)

        left = QVBoxLayout()
        left.addWidget(_kv("Item ID", pkg.metadata.tdp_id or "—", _SLATE))
        left.addWidget(_kv("Name", pkg.metadata.name or "—", _SLATE))
        left.addWidget(_kv("Lifecycle", pkg.metadata.lifecycle_status, _SLATE))
        row.addLayout(left, 2)

        right = QVBoxLayout()
        crit_lbl = QLabel(f"Criticality: {crit}")
        crit_lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:6px;"
            f"font-weight:bold; font-size:13px; padding:6px 14px; border:none;"
        )
        crit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(crit_lbl)
        tech = pkg.quality.risks.technical_performance.replace(" Impact", "")
        safety = pkg.quality.risks.safety_criticality.replace(" Concern", "").replace(" Hazard", "")
        right.addWidget(_kv("Tech risk", tech))
        right.addWidget(_kv("Safety risk", safety))
        row.addLayout(right, 1)

        cl.addLayout(row)
        layout.addWidget(card)

    # ── Aggregate totals card ─────────────────────────────────────────────────
    def _build_totals_card(self, layout: QVBoxLayout, opts: list):
        card, cl = _card("Aggregate totals across all options", _TEAL, _TEAL_L)
        grid = QGridLayout()
        grid.setSpacing(8)

        total_steps   = sum(len(o.steps) for o in opts)
        total_dur     = sum(_opt_duration_min(o) for o in opts)
        total_insp    = sum(_opt_inspection_count(o) for o in opts)
        total_safety  = sum(_opt_safety_flags(o) for o in opts)
        avg_ops       = (
            sum(_opt_max_operators(o) for o in opts) / len(opts)
            if opts else 0
        )

        metrics = [
            ("Process Options",    str(len(opts))),
            ("Total Steps",        str(total_steps)),
            ("Avg Option Duration", _fmt_dur(total_dur // len(opts)) if opts else "—"),
            ("Inspection Methods", str(total_insp)),
            ("Steps with Safety",  str(total_safety)),
            ("Avg Max Operators",  f"{avg_ops:.1f}"),
        ]
        for i, (k, v) in enumerate(metrics):
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet("color:#085041; font-size:11px; background:transparent; border:none;")
            lbl_v = QLabel(v)
            lbl_v.setStyleSheet("color:#0f6e56; font-weight:bold; font-size:14px; background:transparent; border:none;")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row, col = divmod(i, 3)
            grid.addWidget(lbl_k, row * 2,     col * 2)
            grid.addWidget(lbl_v, row * 2 + 1, col * 2)

        cl.addLayout(grid)
        layout.addWidget(card)

    # ── Options comparison table ──────────────────────────────────────────────
    def _build_options_table(self, layout: QVBoxLayout, opts: list):
        card, cl = _card("Process Options comparison", _SLATE, _SLATE_L)

        cols = ["Option", "Maturity", "Steps", "Duration",
                "Max ops", "Op·min", "Insp.", "Safety", "Score"]
        tbl = QTableWidget(len(opts), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        hdr = tbl.horizontalHeader()
        hdr.setMinimumHeight(36)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(2, len(cols)):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            tbl.setColumnWidth(c, 62)
        tbl.horizontalHeader().setMinimumSectionSize(52)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)

        # Find max values for relative colouring
        durations    = [_opt_duration_min(o)            for o in opts]
        op_mins      = [_opt_total_operators_minutes(o) for o in opts]
        complexities = [_complexity_score(o)            for o in opts]
        max_dur    = max(durations)    if durations    else 1
        max_opmin  = max(op_mins)      if op_mins      else 1
        max_compl  = max(complexities) if complexities else 1

        _MATURITY_SHORT = {
            "Very Low — Ad hoc / Initial":          "1 — Ad hoc",
            "Low — Repeatable":                     "2 — Repeatable",
            "Moderate — Defined / Standardized":    "3 — Defined",
            "High — Measured and Controlled":       "4 — Controlled",
            "Very High — Optimized":                "5 — Optimized",
        }

        for r, opt in enumerate(opts):
            dur   = _opt_duration_min(opt)
            opmin = _opt_total_operators_minutes(opt)
            compl = _complexity_score(opt)
            mat_s = _MATURITY_SHORT.get(opt.maturity, opt.maturity or "—")
            insp  = _opt_inspection_count(opt)
            safe  = _opt_safety_flags(opt)
            maxop = _opt_max_operators(opt)

            values = [
                opt.option_name or f"Option {r+1}",
                mat_s,
                str(len(opt.steps)),
                _fmt_dur(dur),
                str(maxop),
                f"{opmin:,}",
                str(insp),
                str(safe),
                str(compl),
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    if c == 0 else
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                # Heat-colour duration, op·min, complexity columns
                if c == 3 and max_dur > 0:
                    ratio = dur / max_dur
                    item.setBackground(QColor(
                        int(0xff - ratio * 0x60),
                        int(0xff - ratio * 0x50),
                        0xff
                    ))
                elif c == 5 and max_opmin > 0:
                    ratio = opmin / max_opmin
                    item.setBackground(QColor(
                        0xff,
                        int(0xff - ratio * 0x70),
                        int(0xff - ratio * 0x70)
                    ))
                elif c == 8 and max_compl > 0:
                    ratio = compl / max_compl
                    r_ch = int(0x4a + (0xf8 - 0x4a) * ratio)
                    g_ch = int(0xde + (0x87 - 0xde) * ratio)
                    b_ch = int(0x80 + (0x71 - 0x80) * ratio)
                    item.setBackground(QColor(r_ch, g_ch, b_ch))
                    item.setForeground(QColor("#ffffff" if ratio > 0.5 else "#222222"))
                tbl.setItem(r, c, item)

        tbl.resizeRowsToContents()
        cl.addWidget(tbl)

        # Legend
        leg = QLabel(
            "Duration (blue) · Op·min = operator-minutes (red) · Score = complexity (green→red)  "
            "— darker shade = higher relative value within this package"
        )
        leg.setStyleSheet("color:#64748b; font-size:11px; background:transparent; border:none;")
        cl.addWidget(leg)
        layout.addWidget(card)

    # ── Complexity breakdown card ─────────────────────────────────────────────
    def _build_complexity_card(self, layout: QVBoxLayout, opts: list):
        card, cl = _card("Complexity score breakdown (0 – 10)", _AMBER, _AMBER_L)

        note = QLabel(
            "Score = steps×2 + maturity + inspections×0.5 + safety steps×0.5 (capped at 10)"
        )
        note.setStyleSheet("color:#854d0e; font-size:11px; background:transparent; border:none;")
        cl.addWidget(note)

        # Use absolute max (10.0) so single-option bar shows true score,
        # not always 100%. For multiple options use relative max for comparison.
        if len(opts) == 1:
            max_score = 10.0
        else:
            max_score = max((_complexity_score(o) for o in opts), default=1.0) or 1.0

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)

        for i, opt in enumerate(opts):
            score = _complexity_score(opt)
            name_lbl = QLabel(opt.option_name or f"Option {i+1}")
            name_lbl.setStyleSheet(
                "color:#412402; font-size:12px; background:transparent; border:none;"
            )
            name_lbl.setFixedWidth(160)
            bar = _score_bar(score, max_score)
            score_lbl = QLabel(str(score))
            score_lbl.setStyleSheet(
                "color:#412402; font-weight:bold; font-size:12px;"
                "background:transparent; border:none;"
            )
            score_lbl.setFixedWidth(36)
            grid.addWidget(name_lbl, i, 0)
            grid.addWidget(bar,      i, 1)
            grid.addWidget(score_lbl,i, 2)

        cl.addLayout(grid)
        layout.addWidget(card)
