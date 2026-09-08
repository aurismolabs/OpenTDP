# models/optional.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class AdditionalCADModel:
    file_name: str = ""
    file_format: str = ""
    file_size: str = ""
    checksum: str = ""
    description: str = ""
    source_path: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "FileName": self.file_name,
            "FileFormat": self.file_format,
            "FileSize": self.file_size,
            "Checksum": self.checksum,
            "Description": self.description,
            "SourcePath": self.source_path,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "AdditionalCADModel":
        return AdditionalCADModel(
            file_name=d.get("FileName", ""),
            file_format=d.get("FileFormat", ""),
            file_size=d.get("FileSize", ""),
            checksum=d.get("Checksum", ""),
            description=d.get("Description", ""),
            source_path=d.get("SourcePath", ""),
        )


@dataclass
class ReferenceImage:
    file_name: str = ""
    file_format: str = ""
    file_size: str = ""
    checksum: str = ""
    description: str = ""
    source_path: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "FileName": self.file_name,
            "FileFormat": self.file_format,
            "FileSize": self.file_size,
            "Checksum": self.checksum,
            "Description": self.description,
            "SourcePath": self.source_path,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "ReferenceImage":
        return ReferenceImage(
            file_name=d.get("FileName", ""),
            file_format=d.get("FileFormat", ""),
            file_size=d.get("FileSize", ""),
            checksum=d.get("Checksum", ""),
            description=d.get("Description", ""),
            source_path=d.get("SourcePath", ""),
        )


@dataclass
class OptionalData:
    additional_cad: List[AdditionalCADModel] = field(default_factory=list)
    images: List[ReferenceImage] = field(default_factory=list)

    def to_xml_dict(self) -> dict:
        return {
            "AdditionalCAD": [c.to_xml_dict() for c in self.additional_cad],
            "Images": [i.to_xml_dict() for i in self.images],
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "OptionalData":
        return OptionalData(
            additional_cad=[AdditionalCADModel.from_xml_dict(c) for c in d.get("AdditionalCAD", [])],
            images=[ReferenceImage.from_xml_dict(i) for i in d.get("Images", [])],
        )
