# models/version.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChangeEntry:
    change_id: str = ""
    timestamp: str = ""
    author: str = ""
    description: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "ChangeID": self.change_id,
            "Timestamp": self.timestamp,
            "Author": self.author,
            "Description": self.description,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "ChangeEntry":
        return ChangeEntry(
            change_id=d.get("ChangeID", ""),
            timestamp=d.get("Timestamp", ""),
            author=d.get("Author", ""),
            description=d.get("Description", ""),
        )


@dataclass
class VersionInfo:
    unique_id: str = ""
    assembly_id: str = ""
    revision: str = ""
    checksum: str = ""
    signature: str = ""
    encryption_enabled: bool = False
    encryption_algorithm: str = ""
    change_history: List[ChangeEntry] = field(default_factory=list)

    def to_xml_dict(self) -> dict:
        return {
            "UniqueID": self.unique_id,
            "AssemblyID": self.assembly_id,
            "Revision": self.revision,
            "Checksum": self.checksum,
            "Signature": self.signature,
            "EncryptionEnabled": "true" if self.encryption_enabled else "false",
            "EncryptionAlgorithm": self.encryption_algorithm,
            "ChangeHistory": [e.to_xml_dict() for e in self.change_history],
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "VersionInfo":
        return VersionInfo(
            unique_id=d.get("UniqueID", ""),
            assembly_id=d.get("AssemblyID", ""),
            revision=d.get("Revision", ""),
            checksum=d.get("Checksum", ""),
            signature=d.get("Signature", ""),
            encryption_enabled=d.get("EncryptionEnabled", "false") == "true",
            encryption_algorithm=d.get("EncryptionAlgorithm", ""),
            change_history=[
                ChangeEntry.from_xml_dict(e) for e in d.get("ChangeHistory", [])
            ],
        )
