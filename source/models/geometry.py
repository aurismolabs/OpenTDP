# models/geometry.py
from dataclasses import dataclass, field


@dataclass
class Geometry:
    id: str = ""
    file_name: str = ""
    source_path: str = ""
    file_format: str = ""
    file_size: str = ""
    checksum: str = ""
    dimensions: str = ""
    preview: bool = False

    def to_xml_dict(self) -> dict:
        return {
            "id": self.id,
            "FileName": self.file_name,
            "SourcePath": self.source_path,
            "FileFormat": self.file_format,
            "FileSize": self.file_size,
            "Checksum": self.checksum,
            "Dimensions": self.dimensions,
            "Preview": "true" if self.preview else "false",
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "Geometry":
        return Geometry(
            id=d.get("id", ""),
            file_name=d.get("FileName", ""),
            source_path=d.get("SourcePath", ""),
            file_format=d.get("FileFormat", ""),
            file_size=d.get("FileSize", ""),
            checksum=d.get("Checksum", ""),
            dimensions=d.get("Dimensions", ""),
            preview=d.get("Preview", "false") == "true",
        )
