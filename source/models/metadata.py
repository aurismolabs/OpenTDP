# models/metadata.py
from dataclasses import dataclass


@dataclass
class Metadata:
    tdp_id: str = ""
    additional_ids: str = ""
    name: str = ""
    description: str = ""
    version: str = ""
    created_date: str = ""
    modified_date: str = ""
    lifecycle_status: str = "Draft"
    author: str = ""
    organization: str = ""
    contact: str = ""
    licensing: str = ""
    information_classification: str = "Internal"
    confidentiality_level: str = ""
    criticality_level: str = ""   # computed from Quality risk scores, not user-editable

    def to_xml_dict(self) -> dict:
        return {
            "TDP_ID": self.tdp_id,
            "AdditionalIDs": self.additional_ids,
            "Name": self.name,
            "Description": self.description,
            "Version": self.version,
            "CreatedDate": self.created_date,
            "ModifiedDate": self.modified_date,
            "LifecycleStatus": self.lifecycle_status,
            "Author": self.author,
            "Organization": self.organization,
            "Contact": self.contact,
            "Licensing": self.licensing,
            "InformationClassification": self.information_classification,
            "ConfidentialityLevel": self.confidentiality_level,
            "CriticalityLevel": self.criticality_level,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "Metadata":
        return Metadata(
            tdp_id=d.get("TDP_ID", ""),
            additional_ids=d.get("AdditionalIDs", ""),
            name=d.get("Name", ""),
            description=d.get("Description", ""),
            version=d.get("Version", ""),
            created_date=d.get("CreatedDate", ""),
            modified_date=d.get("ModifiedDate", ""),
            lifecycle_status=d.get("LifecycleStatus", "Draft"),
            author=d.get("Author", ""),
            organization=d.get("Organization", ""),
            contact=d.get("Contact", ""),
            licensing=d.get("Licensing", ""),
            information_classification=d.get("InformationClassification", "Internal"),
            confidentiality_level=d.get("ConfidentialityLevel", ""),
            criticality_level=d.get("CriticalityLevel", "Low"),
        )
