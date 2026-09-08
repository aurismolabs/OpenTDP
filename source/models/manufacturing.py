# models/manufacturing.py
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Attachment:
    file_name: str = ""
    source_path: str = ""
    file_format: str = ""
    file_size: str = ""
    checksum: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "FileName": self.file_name,
            "SourcePath": self.source_path,
            "FileFormat": self.file_format,
            "FileSize": self.file_size,
            "Checksum": self.checksum,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "Attachment":
        return Attachment(
            file_name=d.get("FileName", ""),
            source_path=d.get("SourcePath", ""),
            file_format=d.get("FileFormat", ""),
            file_size=d.get("FileSize", ""),
            checksum=d.get("Checksum", ""),
        )


@dataclass
class ProcessStep:
    id: str = ""
    sequence: int = 0
    name: str = ""
    description: str = ""
    manufacturing_method: str = ""
    orientation: str = ""

    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    build_files: List[str] = field(default_factory=list)
    duration: Dict[str, int] = field(default_factory=lambda: {"hours": 0, "minutes": 0})
    operator_count: int = 1     # Number of operators required to perform this step
    attachments: List[Attachment] = field(default_factory=list)

    # Materials
    material: str = ""
    material_batch: str = ""
    material_pretreatment: str = ""
    material_quantity: str = ""     # Amount consumed, e.g. "200 g" or "2 blanks"
    material_shelf_life: str = ""   # Expiry / shelf-life requirement, e.g. "2025-12-31" or "12 months"

    # Environment
    env_temp_min: int = 5
    env_temp_max: int = 35
    env_humidity_min: int = 30
    env_humidity_max: int = 70
    airflow: str = ""
    env_cleanroom_class: str = ""   # ISO 14644 class or equivalent, e.g. "ISO 7" or "Class 10000"

    # Equipment
    machine: str = ""
    tools: str = ""
    software: str = ""
    power_kw: float = 0.0
    compressed_air_bar: float = 0.0
    vacuum: str = ""
    cooling: str = ""
    floorarea: str = ""
    eqpheight: str = ""
    weight: float = 0.0
    other_equipment: str = ""

    # Quality
    inspection_methods: List[str] = field(default_factory=list)
    inspection_points: str = ""
    sampling_plan: str = ""
    tolerances: str = ""
    surface_quality: str = ""
    acceptance_criteria: str = ""
    nonacceptance_handling: str = ""
    required_docs: str = ""
    required_training: str = ""
    requirement_source: str = ""  # Origin of quality requirements, e.g. standard, drawing, customer spec

    # Safety
    ppe: str = ""
    chemical_risks: str = ""
    thermal_risks: str = ""
    mechanical_risks: str = ""
    esd_risks: str = ""
    other_safety: str = ""

    # Post-processing
    post_processing: str = ""
    notes: str = ""

    # Parameters (key-value)
    parameters: Dict[str, str] = field(default_factory=dict)

    def to_xml_dict(self) -> dict:
        return {
            "id": self.id,
            "sequence": self.sequence,
            "name": self.name,
            "description": self.description,
            "manufacturing_method": self.manufacturing_method,
            "orientation": self.orientation,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "build_files": self.build_files,
            "duration": self.duration,
            "operator_count": self.operator_count,
            "attachments": [a.to_xml_dict() for a in self.attachments],
            "material": self.material,
            "material_batch": self.material_batch,
            "material_pretreatment": self.material_pretreatment,
            "material_quantity": self.material_quantity,
            "material_shelf_life": self.material_shelf_life,
            "env_temp_min": self.env_temp_min,
            "env_temp_max": self.env_temp_max,
            "env_humidity_min": self.env_humidity_min,
            "env_humidity_max": self.env_humidity_max,
            "airflow": self.airflow,
            "env_cleanroom_class": self.env_cleanroom_class,
            "machine": self.machine,
            "tools": self.tools,
            "software": self.software,
            "power_kw": self.power_kw,
            "compressed_air_bar": self.compressed_air_bar,
            "vacuum": self.vacuum,
            "cooling": self.cooling,
            "floorarea": self.floorarea,
            "eqpheight": self.eqpheight,
            "weight": self.weight,
            "other_equipment": self.other_equipment,
            "inspection_methods": self.inspection_methods,
            "inspection_points": self.inspection_points,
            "sampling_plan": self.sampling_plan,
            "tolerances": self.tolerances,
            "surface_quality": self.surface_quality,
            "acceptance_criteria": self.acceptance_criteria,
            "nonacceptance_handling": self.nonacceptance_handling,
            "required_docs": self.required_docs,
            "required_training": self.required_training,
            "requirement_source": self.requirement_source,
            "ppe": self.ppe,
            "chemical_risks": self.chemical_risks,
            "thermal_risks": self.thermal_risks,
            "mechanical_risks": self.mechanical_risks,
            "esd_risks": self.esd_risks,
            "other_safety": self.other_safety,
            "post_processing": self.post_processing,
            "notes": self.notes,
            "parameters": self.parameters,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "ProcessStep":
        return ProcessStep(
            id=d.get("id", ""),
            sequence=int(d.get("sequence", 0)),
            name=d.get("name", ""),
            description=d.get("description", ""),
            manufacturing_method=d.get("manufacturing_method", ""),
            orientation=d.get("orientation", ""),
            inputs=d.get("inputs", []),
            outputs=d.get("outputs", []),
            build_files=d.get("build_files", []),
            duration=d.get("duration", {"hours": 0, "minutes": 0}),
            operator_count=int(d.get("operator_count", 1)),
            attachments=[Attachment.from_xml_dict(a) for a in d.get("attachments", [])],
            material=d.get("material", ""),
            material_batch=d.get("material_batch", ""),
            material_pretreatment=d.get("material_pretreatment", ""),
            material_quantity=d.get("material_quantity", ""),
            material_shelf_life=d.get("material_shelf_life", ""),
            env_temp_min=int(d.get("env_temp_min", 5)),
            env_temp_max=int(d.get("env_temp_max", 35)),
            env_humidity_min=int(d.get("env_humidity_min", 30)),
            env_humidity_max=int(d.get("env_humidity_max", 70)),
            airflow=d.get("airflow", ""),
            env_cleanroom_class=d.get("env_cleanroom_class", ""),
            machine=d.get("machine", ""),
            tools=d.get("tools", ""),
            software=d.get("software", ""),
            power_kw=float(d.get("power_kw", 0.0)),
            compressed_air_bar=float(d.get("compressed_air_bar", 0.0)),
            vacuum=d.get("vacuum", ""),
            cooling=d.get("cooling", ""),
            floorarea=d.get("floorarea", ""),
            eqpheight=d.get("eqpheight", ""),
            weight=float(d.get("weight", 0.0)),
            other_equipment=d.get("other_equipment", ""),
            inspection_methods=d.get("inspection_methods", []),
            inspection_points=d.get("inspection_points", ""),
            sampling_plan=d.get("sampling_plan", ""),
            tolerances=d.get("tolerances", ""),
            surface_quality=d.get("surface_quality", ""),
            acceptance_criteria=d.get("acceptance_criteria", ""),
            nonacceptance_handling=d.get("nonacceptance_handling", ""),
            required_docs=d.get("required_docs", ""),
            required_training=d.get("required_training", ""),
            requirement_source=d.get("requirement_source", ""),
            ppe=d.get("ppe", ""),
            chemical_risks=d.get("chemical_risks", ""),
            thermal_risks=d.get("thermal_risks", ""),
            mechanical_risks=d.get("mechanical_risks", ""),
            esd_risks=d.get("esd_risks", ""),
            other_safety=d.get("other_safety", ""),
            post_processing=d.get("post_processing", ""),
            notes=d.get("notes", ""),
            parameters=d.get("parameters", {}),
        )


@dataclass
class ProcessOption:
    option_name: str = ""
    description: str = ""
    maturity: str = ""
    revision: str = ""          # Option-level revision / change identifier
    steps: List[ProcessStep] = field(default_factory=list)

    def to_xml_dict(self) -> dict:
        return {
            "OptionName": self.option_name,
            "Description": self.description,
            "Maturity": self.maturity,
            "Revision": self.revision,
            "Steps": [s.to_xml_dict() for s in self.steps],
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "ProcessOption":
        return ProcessOption(
            option_name=d.get("OptionName", ""),
            description=d.get("Description", ""),
            maturity=d.get("Maturity", ""),
            revision=d.get("Revision", ""),
            steps=[ProcessStep.from_xml_dict(s) for s in d.get("Steps", [])],
        )


@dataclass
class ManufacturingOverview:
    description: str = ""
    manufacturing_method: str = ""
    material: str = ""
    standards: List[str] = field(default_factory=list)

    def to_xml_dict(self) -> dict:
        return {
            "Description": self.description,
            "ManufacturingMethod": self.manufacturing_method,
            "Material": self.material,
            "Standards": self.standards,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "ManufacturingOverview":
        return ManufacturingOverview(
            description=d.get("Description", ""),
            manufacturing_method=d.get("ManufacturingMethod", ""),
            material=d.get("Material", ""),
            standards=d.get("Standards", []),
        )
