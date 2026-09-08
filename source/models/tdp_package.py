# models/tdp_package.py
from dataclasses import dataclass, field
from typing import List

from models.metadata import Metadata
from models.version import VersionInfo
from models.geometry import Geometry
from models.manufacturing import ManufacturingOverview, ProcessOption
from models.amdata import BuildFile
from models.optional import OptionalData
from models.quality import QualityData
from models.packing import PackingAndSafety


@dataclass
class TDPPackage:
    metadata: Metadata = field(default_factory=Metadata)
    version: VersionInfo = field(default_factory=VersionInfo)
    geometry: List[Geometry] = field(default_factory=list)
    overview: ManufacturingOverview = field(default_factory=ManufacturingOverview)
    process_options: List[ProcessOption] = field(default_factory=list)
    build_files: List[BuildFile] = field(default_factory=list)
    optional: OptionalData = field(default_factory=OptionalData)
    quality: QualityData = field(default_factory=QualityData)
    packing: PackingAndSafety = field(default_factory=PackingAndSafety)
