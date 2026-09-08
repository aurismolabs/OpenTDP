# ui/field_state.py
"""
Centralised field-state styling for all TDP tabs.

Two states:
  REQUIRED_EMPTY  — field is mandatory right now but has no value:
                    red border + very light red background.
  REQUIRED_FILLED — field is mandatory right now and has a value:
                    green border + very light green background.

Widgets that are optional receive no extra styling (clear() resets them).

Usage
-----
    from ui.field_state import apply_state, clear_state, REQUIRED_EMPTY, REQUIRED_FILLED

    # Mark a single widget:
    apply_state(self.tdp_id, REQUIRED_EMPTY)
    apply_state(self.name,   REQUIRED_FILLED)
    clear_state(self.description)   # optional field — no colour

    # Convenience: update a whole mapping in one call:
    update_states({
        self.tdp_id:    bool(self.tdp_id.text().strip()),
        self.name:      bool(self.name.text().strip()),
    })
    # True  → REQUIRED_FILLED (green)
    # False → REQUIRED_EMPTY  (red)
"""
from PyQt6.QtWidgets import QWidget

# ── Stylesheet fragments ──────────────────────────────────────────────────────
_BASE = "border-radius: 4px;"

REQUIRED_EMPTY = (
    "border: 1.5px solid #f87171;"          # red-400
    "background-color: #fff5f5;"            # very light red
) + _BASE

REQUIRED_FILLED = (
    "border: 1.5px solid #4ade80;"          # green-400
    "background-color: #f0fdf4;"            # very light green
) + _BASE

_CLEAR = ""   # reset to default Qt styling


# ── Public API ────────────────────────────────────────────────────────────────

def apply_state(widget: QWidget, style: str) -> None:
    """Apply REQUIRED_EMPTY or REQUIRED_FILLED stylesheet to *widget*."""
    widget.setStyleSheet(style)


def clear_state(widget: QWidget) -> None:
    """Remove any field-state styling (optional field)."""
    widget.setStyleSheet(_CLEAR)


def update_states(mapping: dict[QWidget, bool]) -> None:
    """
    Bulk-update a dict of {widget: is_filled}.
    True  → REQUIRED_FILLED (green)
    False → REQUIRED_EMPTY  (red)
    """
    for widget, filled in mapping.items():
        apply_state(widget, REQUIRED_FILLED if filled else REQUIRED_EMPTY)
