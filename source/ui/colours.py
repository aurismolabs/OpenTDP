# ui/colours.py
"""
Centralised colour definitions for lifecycle and criticality levels.
Import from here — do not redefine these in individual tab files.
"""

# Lifecycle colours: (text_fg, light_bg)
LC_COLOURS = {
    "Draft":      ("#64748b", "#f1f5f9"),
    "In Review":  ("#0369a1", "#e0f2fe"),
    "Approved":   ("#3d7a00", "#ecfccb"),
    "Released":   ("#065F46", "#a7f3d0"),
    "Deprecated": ("#6b7280", "#f3f4f6"),
}

# Criticality colours: (light_text, dark_bg) — for badges and labels
CRIT_COLOURS = {
    "Non-critical": ("#e2e8f0", "#475569"),
    "Low":          ("#fef9c3", "#854d0e"),
    "Medium":       ("#ffedd5", "#c2410c"),
    "High":         ("#fecaca", "#b91c1c"),
    "Very High":    ("#ede9fe", "#4c1d95"),
}
