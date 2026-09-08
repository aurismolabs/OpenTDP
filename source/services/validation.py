# services/validation.py
"""
Criticality is derived from the Quality tab's Risk Classification:

    Technical Performance    Safety Criticality       → Criticality level
    ─────────────────────    ──────────────────
    Negligible  +  Minimal                            → Non-critical
    Any other combination where at least one is
    above the lowest option                           → Low
    Moderate or higher in either field                → Medium
    High or Critical in either field                  → High
    Critical in either field                          → Very High

Lifecycle status affects WHEN requirements become active:

    Draft       : Item ID, Name, Contact and Licensing required.
                  All other requirements (geometry, risks, approval,
                  overview, process steps) are waived.
    In Review   : Geometry file required (≥1 STL or 3MF).
                  Identified Risks required when criticality ≥ Low.
    Approved    : Full criticality-based requirements apply. Revision
                  stamp required. Approval fields (Approver, Status ≠
                  Pending, Conditions, Evidence Refs) required.
    Released    : Same as Approved.
    Deprecated  : Package is treated as read-only. Validation passes
                  unconditionally; saving is allowed but a deprecation
                  warning is shown.

Validation rules (cumulative — each lifecycle adds to the previous):

    All states  : Item ID and Name required.
    Draft       : No further requirements.
    In Review+  : ≥1 geometry file (STL or 3MF).
                  Identified Risks (when criticality ≥ Low).
    Approved+   : Revision stamp (Revision Timestamp field).
                  Approval fields: Approver, Status ≠ Pending,
                    Conditions, Evidence Refs.
                  Overview Method and Material (when Medium+).
                  ≥1 Process Option + ≥1 Step (when High+).
                  ≥1 Inspection Method in any step (when Very High+).
    Released    : Same requirements as Approved.
"""
from typing import List
from models.tdp_package import TDPPackage
from models.quality import QualityData


# ---------------------------------------------------------------------------
# Ordinal rankings
# ---------------------------------------------------------------------------

_TECH_RANK = {
    "Negligible Technical Impact": 0,
    "Low Technical Impact":        1,
    "Moderate Technical Impact":   2,
    "High Technical Impact":       3,
    "Critical Technical Impact":   4,
}

_SAFETY_RANK = {
    "Minimal Safety Concern":   0,
    "Low Safety Concern":       1,
    "Moderate Safety Concern":  2,
    "High Safety Concern":      3,
    "Critical Safety Hazard":   4,
}

_LEVEL_ORDER = ["Non-critical", "Low", "Medium", "High", "Very High"]

# Lifecycle stages ordered from least to most complete.
# Draft is index 0 (fewest requirements); Deprecated sits after Released
# but is treated specially (read-only / unconditional pass).
_LIFECYCLE_ORDER = ["Draft", "In Review", "Approved", "Released", "Deprecated"]


def derive_criticality(quality: QualityData) -> str:
    """Return the criticality label derived from the two risk combo-boxes."""
    tech   = _TECH_RANK.get(quality.risks.technical_performance, 0)
    safety = _SAFETY_RANK.get(quality.risks.safety_criticality, 0)
    worst  = max(tech, safety)

    if worst == 0:
        return "Non-critical"
    elif worst == 1:
        return "Low"
    elif worst == 2:
        return "Medium"
    elif worst == 3:
        return "High"
    else:
        return "Very High"


def _at_least_criticality(level: str, required: str) -> bool:
    try:
        return _LEVEL_ORDER.index(level) >= _LEVEL_ORDER.index(required)
    except ValueError:
        return False


def _at_least_lifecycle(status: str, required: str) -> bool:
    try:
        return _LIFECYCLE_ORDER.index(status) >= _LIFECYCLE_ORDER.index(required)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

_ACCEPTED_GEOMETRY_FORMATS = {"STL", "3MF"}


def validate(package: TDPPackage) -> List[str]:
    """
    Derive criticality, stamp it onto package.metadata, then validate
    against both criticality level and lifecycle status.
    Returns a list of error/warning strings (empty = valid).
    """
    # 1. Derive and store criticality
    level  = derive_criticality(package.quality)
    package.metadata.criticality_level = level

    status = package.metadata.lifecycle_status  # e.g. "Draft", "In Review", …

    errors: List[str] = []

    # 2. Always required — any lifecycle, any criticality
    if not package.metadata.tdp_id.strip():
        errors.append("Item ID is required.")
    if not package.metadata.name.strip():
        errors.append("Item Name is required.")
    if not package.metadata.contact.strip():
        errors.append("Contact is required.")
    if not package.metadata.licensing.strip():
        errors.append("Licensing is required.")

    # Contact and Licensing are always required to establish IP ownership
    # and accountability from the earliest draft stage.

    # 3. Deprecated: unconditional pass — read-only state, no content
    #    requirements. Only ID + Name are checked (already done above).
    #    Contact and Licensing are waived for archived packages.
    if status == "Deprecated":
        return []

    # 4. Draft: waive all geometry and downstream requirements.
    if status == "Draft":
        return errors

    # --- From here: In Review, Approved, Released ---

    # 5b. In Review+: geometry file required regardless of criticality.
    #    Accepted formats: STL or 3MF (open triangle-mesh formats only).
    #    Both count and format are validated here so that files loaded from
    #    an older .tdp (which may contain STEP/IGES/OBJ entries) are also caught.
    if not package.geometry:
        errors.append(
            "At least one geometry file is required "
            f"when lifecycle status is '{status}'. "
            "Accepted formats: STL, 3MF."
        )
    else:
        for g in package.geometry:
            fmt = g.file_format.upper().strip()
            if fmt not in _ACCEPTED_GEOMETRY_FORMATS:
                errors.append(
                    f"Geometry file '{g.file_name}' uses format '{g.file_format}', "
                    "which is not accepted. Only STL and 3MF are allowed. "
                    "STEP, IGES and OBJ contain parametric or free-form curve "
                    "data and are not supported as geometry files."
                )

    # 5d. In Review+, Low+: identified risks required.
    if _at_least_criticality(level, "Low"):
        if not package.quality.risks.identified_risks.strip():
            errors.append(
                "Quality: Identified Risks is required "
                "(In Review+, Low criticality+)."
            )

    # 6. Approved / Released: revision stamp required.
    if _at_least_lifecycle(status, "Approved"):
        if not package.version.revision.strip():
            errors.append(
                "Revision Timestamp is required "
                "when lifecycle status is 'Approved' or 'Released'."
            )

    # 6b. Approved / Released: approval status required.
    # Non-critical: status is auto-set to Approved; other approval fields
    # are informational only (no mandatory audit trail at lowest risk level).
    # Low+: status must be explicitly confirmed.
    if _at_least_lifecycle(status, "Approved"):
        ap = package.quality.approval
        if ap.status in ("", "Pending"):
            errors.append(
                "Quality: Approval Status must be Approved or "
                "Rejected (Approved/Released)."
            )

    # 7. Approved / Released, Medium+: overview description, method and material.
    if _at_least_lifecycle(status, "Approved") and _at_least_criticality(level, "Medium"):
        ov = package.overview
        if not ov.description.strip():
            errors.append(
                "Process Overview: Description is required "
                "(Approved+, Medium criticality+)."
            )
        if not ov.manufacturing_method.strip():
            errors.append(
                "Process Overview: Manufacturing Method is required "
                "(Approved+, Medium criticality+)."
            )
        if not ov.material.strip():
            errors.append(
                "Process Overview: Material is required "
                "(Approved+, Medium criticality+)."
            )

    # 7. Approved / Released, High+: process options and steps
    if _at_least_lifecycle(status, "Approved") and _at_least_criticality(level, "High"):
        total_steps = sum(len(opt.steps) for opt in package.process_options)
        if not package.process_options:
            errors.append(
                "At least one Process Option is required "
                "(Approved+, High criticality+)."
            )
        elif total_steps == 0:
            errors.append(
                "At least one Process Step is required in a Process Option "
                "(Approved+, High criticality+)."
            )

    # 8. Approved / Released, Very High: inspection methods
    if _at_least_lifecycle(status, "Approved") and _at_least_criticality(level, "Very High"):
        has_inspection = any(
            step.inspection_methods
            for opt in package.process_options
            for step in opt.steps
        )
        if not has_inspection:
            errors.append(
                "At least one Inspection Method must be selected in a "
                "Process Step (Approved+, Very High criticality+)."
            )

    return errors


# ---------------------------------------------------------------------------
# Public helper kept for UI live-preview (Quality tab criticality label)
# ---------------------------------------------------------------------------

def validate_package(package: TDPPackage) -> List[str]:
    """Alias used by the web app views."""
    return validate(package)
