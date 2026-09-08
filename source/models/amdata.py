# models/amdata.py
from dataclasses import dataclass, field


@dataclass
class PrinterInfo:
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""

    def to_xml_dict(self) -> dict:
        return {"Manufacturer": self.manufacturer, "Model": self.model, "SerialNumber": self.serial_number}

    @staticmethod
    def from_xml_dict(d: dict) -> "PrinterInfo":
        return PrinterInfo(
            manufacturer=d.get("Manufacturer", ""),
            model=d.get("Model", ""),
            serial_number=d.get("SerialNumber", ""),
        )


@dataclass
class MaterialInfo:
    name: str = ""
    grade: str = ""
    batch_number: str = ""

    def to_xml_dict(self) -> dict:
        return {"Name": self.name, "Grade": self.grade, "BatchNumber": self.batch_number}

    @staticmethod
    def from_xml_dict(d: dict) -> "MaterialInfo":
        return MaterialInfo(
            name=d.get("Name", ""),
            grade=d.get("Grade", ""),
            batch_number=d.get("BatchNumber", ""),
        )


@dataclass
class CertificationInfo:
    certified: str = ""
    certification_body: str = ""
    certificate_id: str = ""
    issue_date: str = ""
    expiry_date: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "Certified": self.certified,
            "CertificationBody": self.certification_body,
            "CertificateID": self.certificate_id,
            "IssueDate": self.issue_date,
            "ExpiryDate": self.expiry_date,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "CertificationInfo":
        return CertificationInfo(
            certified=d.get("Certified", ""),
            certification_body=d.get("CertificationBody", ""),
            certificate_id=d.get("CertificateID", ""),
            issue_date=d.get("IssueDate", ""),
            expiry_date=d.get("ExpiryDate", ""),
        )


@dataclass
class BuildFile:
    id: str = ""
    file_name: str = ""
    source_path: str = ""
    file_format: str = ""
    file_size: str = ""
    checksum: str = ""
    file_type: str = ""
    printer: PrinterInfo = field(default_factory=PrinterInfo)
    material: MaterialInfo = field(default_factory=MaterialInfo)
    certification: CertificationInfo = field(default_factory=CertificationInfo)

    def to_xml_dict(self) -> dict:
        return {
            "id": self.id,
            "FileName": self.file_name,
            "SourcePath": self.source_path,
            "FileFormat": self.file_format,
            "FileSize": self.file_size,
            "Checksum": self.checksum,
            "FileType": self.file_type,
            "Printer": self.printer.to_xml_dict(),
            "Material": self.material.to_xml_dict(),
            "Certification": self.certification.to_xml_dict(),
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "BuildFile":
        return BuildFile(
            id=d.get("id", ""),
            file_name=d.get("FileName", ""),
            source_path=d.get("SourcePath", ""),
            file_format=d.get("FileFormat", ""),
            file_size=d.get("FileSize", ""),
            checksum=d.get("Checksum", ""),
            file_type=d.get("FileType", ""),
            printer=PrinterInfo.from_xml_dict(d.get("Printer", {})),
            material=MaterialInfo.from_xml_dict(d.get("Material", {})),
            certification=CertificationInfo.from_xml_dict(d.get("Certification", {})),
        )
