# models/quality.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class TraceabilityData:
    serial_number_format: str = ""
    batch_id_format: str = ""
    material_lot_format: str = ""
    labeling_requirements: str = ""
    traceability_level: str = ""   # Required granularity: Batch | Lot | Unit | Component

    def to_xml_dict(self) -> dict:
        return {
            "SerialNumberFormat": self.serial_number_format,
            "BatchIDFormat": self.batch_id_format,
            "MaterialLotFormat": self.material_lot_format,
            "LabelingRequirements": self.labeling_requirements,
            "TraceabilityLevel": self.traceability_level,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "TraceabilityData":
        return TraceabilityData(
            serial_number_format=d.get("SerialNumberFormat", ""),
            batch_id_format=d.get("BatchIDFormat", ""),
            material_lot_format=d.get("MaterialLotFormat", ""),
            labeling_requirements=d.get("LabelingRequirements", ""),
            traceability_level=d.get("TraceabilityLevel", ""),
        )


@dataclass
class RiskData:
    technical_performance: str = "Negligible Technical Impact"
    safety_criticality: str = "Minimal Safety Concern"
    identified_risks: str = ""

    def to_xml_dict(self) -> dict:
        return {
            "TechnicalPerformance": self.technical_performance,
            "SafetyCriticality": self.safety_criticality,
            "IdentifiedRisks": self.identified_risks,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "RiskData":
        return RiskData(
            technical_performance=d.get("TechnicalPerformance", "Negligible Technical Impact"),
            safety_criticality=d.get("SafetyCriticality", "Minimal Safety Concern"),
            identified_risks=d.get("IdentifiedRisks", ""),
        )


@dataclass
class ApprovalData:
    approver: str = ""
    status: str = "Pending"
    timestamp: str = ""
    conditions: str = ""      # What must be demonstrated/submitted before approval
    evidence_refs: str = ""   # References to submitted evidence documents

    def to_xml_dict(self) -> dict:
        return {
            "Approver": self.approver,
            "Status": self.status,
            "Timestamp": self.timestamp,
            "Conditions": self.conditions,
            "EvidenceRefs": self.evidence_refs,
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "ApprovalData":
        return ApprovalData(
            approver=d.get("Approver", ""),
            status=d.get("Status", "Pending"),
            timestamp=d.get("Timestamp", ""),
            conditions=d.get("Conditions", ""),
            evidence_refs=d.get("EvidenceRefs", ""),
        )


@dataclass
class QualityData:
    traceability: TraceabilityData = field(default_factory=TraceabilityData)
    risks: RiskData = field(default_factory=RiskData)
    process_quality_notes: str = ""
    approval: ApprovalData = field(default_factory=ApprovalData)

    def to_xml_dict(self) -> dict:
        return {
            "Traceability": self.traceability.to_xml_dict(),
            "Risks": self.risks.to_xml_dict(),
            "ProcessQualityNotes": self.process_quality_notes,
            "Approval": self.approval.to_xml_dict(),
        }

    @staticmethod
    def from_xml_dict(d: dict) -> "QualityData":
        return QualityData(
            traceability=TraceabilityData.from_xml_dict(d.get("Traceability", {})),
            risks=RiskData.from_xml_dict(d.get("Risks", {})),
            process_quality_notes=d.get("ProcessQualityNotes", ""),
            approval=ApprovalData.from_xml_dict(d.get("Approval", {})),
        )
