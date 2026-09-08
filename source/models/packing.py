# models/packing.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class PackingAndSafety:
    # Packing
    packing_material: str = ""
    cushioning: str = ""
    moisture_protection: str = ""
    surface_protection: str = ""
    label_fragile: bool = False
    label_this_side_up: bool = False
    label_do_not_stack: bool = False
    label_esd: bool = False
    other_labels: str = ""

    # Handling
    allowed_lifting: str = ""
    forbidden_lifting: str = ""
    cog_description: str = ""
    handling_forces: str = ""
    esd_requirements: str = ""

    # Transport
    transport_orientation: str = ""
    hazmat_classes: List[str] = field(default_factory=list)
    securing_method: str = ""
    temp_min: float = 0.0
    temp_max: float = 0.0
    humidity_min: float = 0.0
    humidity_max: float = 0.0
    stackable: bool = False
    max_stack_layers: int = 0
    special_transport: str = ""

    # Safety
    ppe: str = ""
    edge_risks: str = ""
    weight: float = 0.0
    manual_lift_limit: float = 0.0
    chemical_risks: str = ""
    thermal_risks: str = ""
    other_safety: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "PackingMaterial": self.packing_material,
            "Cushioning": self.cushioning,
            "MoistureProtection": self.moisture_protection,
            "SurfaceProtection": self.surface_protection,
            "LabelFragile": "true" if self.label_fragile else "false",
            "LabelThisSideUp": "true" if self.label_this_side_up else "false",
            "LabelDoNotStack": "true" if self.label_do_not_stack else "false",
            "LabelESD": "true" if self.label_esd else "false",
            "OtherLabels": self.other_labels,
            "AllowedLifting": self.allowed_lifting,
            "ForbiddenLifting": self.forbidden_lifting,
            "COGDescription": self.cog_description,
            "HandlingForces": self.handling_forces,
            "ESDRequirements": self.esd_requirements,
            "TransportOrientation": self.transport_orientation,
            "HazmatClasses": self.hazmat_classes,
            "SecuringMethod": self.securing_method,
            "TempMin": str(self.temp_min),
            "TempMax": str(self.temp_max),
            "HumidityMin": str(self.humidity_min),
            "HumidityMax": str(self.humidity_max),
            "Stackable": "true" if self.stackable else "false",
            "MaxStackLayers": str(self.max_stack_layers),
            "SpecialTransport": self.special_transport,
            "PPE": self.ppe,
            "EdgeRisks": self.edge_risks,
            "Weight": str(self.weight),
            "ManualLiftLimit": str(self.manual_lift_limit),
            "ChemicalRisks": self.chemical_risks,
            "ThermalRisks": self.thermal_risks,
            "OtherSafety": self.other_safety,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "PackingAndSafety":
        def _bool(v): return v == "true"
        def _float(v, default=0.0):
            try: return float(v)
            except (ValueError, TypeError): return default
        def _int(v, default=0):
            try: return int(v)
            except (ValueError, TypeError): return default

        return PackingAndSafety(
            packing_material=d.get("PackingMaterial", ""),
            cushioning=d.get("Cushioning", ""),
            moisture_protection=d.get("MoistureProtection", ""),
            surface_protection=d.get("SurfaceProtection", ""),
            label_fragile=_bool(d.get("LabelFragile", "false")),
            label_this_side_up=_bool(d.get("LabelThisSideUp", "false")),
            label_do_not_stack=_bool(d.get("LabelDoNotStack", "false")),
            label_esd=_bool(d.get("LabelESD", "false")),
            other_labels=d.get("OtherLabels", ""),
            allowed_lifting=d.get("AllowedLifting", ""),
            forbidden_lifting=d.get("ForbiddenLifting", ""),
            cog_description=d.get("COGDescription", ""),
            handling_forces=d.get("HandlingForces", ""),
            esd_requirements=d.get("ESDRequirements", ""),
            transport_orientation=d.get("TransportOrientation", ""),
            hazmat_classes=d.get("HazmatClasses", []),
            securing_method=d.get("SecuringMethod", ""),
            temp_min=_float(d.get("TempMin", "0")),
            temp_max=_float(d.get("TempMax", "0")),
            humidity_min=_float(d.get("HumidityMin", "0")),
            humidity_max=_float(d.get("HumidityMax", "0")),
            stackable=_bool(d.get("Stackable", "false")),
            max_stack_layers=_int(d.get("MaxStackLayers", "0")),
            special_transport=d.get("SpecialTransport", ""),
            ppe=d.get("PPE", ""),
            edge_risks=d.get("EdgeRisks", ""),
            weight=_float(d.get("Weight", "0")),
            manual_lift_limit=_float(d.get("ManualLiftLimit", "0")),
            chemical_risks=d.get("ChemicalRisks", ""),
            thermal_risks=d.get("ThermalRisks", ""),
            other_safety=d.get("OtherSafety", ""),
        )
