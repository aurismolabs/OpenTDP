# services/xml_serializer.py
"""
Converts a TDPPackage to an XML string and back.
All data passes through the model's to_xml_dict / from_xml_dict methods,
so the XML schema and the models are always in sync.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional

from models.tdp_package import TDPPackage
from models.metadata import Metadata
from models.version import VersionInfo, ChangeEntry
from models.geometry import Geometry
from models.manufacturing import ManufacturingOverview, ProcessOption, ProcessStep, Attachment
from models.amdata import BuildFile, PrinterInfo, MaterialInfo, CertificationInfo
from models.optional import OptionalData, AdditionalCADModel, ReferenceImage
from models.quality import QualityData, TraceabilityData, RiskData, ApprovalData
from models.packing import PackingAndSafety


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sub(parent: ET.Element, tag: str, text: str = "",
         field_id: str = "") -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text or ""
    if field_id:
        el.set("fieldId", field_id)
    return el



def _text(element: Optional[ET.Element], default: str = "") -> str:
    if element is None:
        return default
    return (element.text or "").strip()


def _find_text(parent: ET.Element, tag: str, default: str = "") -> str:
    el = parent.find(tag)
    return _text(el, default)


# ---------------------------------------------------------------------------
# SERIALISE: TDPPackage → XML string
# ---------------------------------------------------------------------------

def to_xml_string(package: TDPPackage) -> str:
    root = ET.Element("TDP")
    _write_metadata(root, package.metadata)
    _write_version(root, package.version)
    _write_geometry(root, package.geometry)
    _write_overview(root, package.overview)
    _write_process_options(root, package.process_options)
    _write_build_files(root, package.build_files)
    _write_optional(root, package.optional)
    _write_quality(root, package.quality)
    _write_packing(root, package.packing)
    rough = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(rough).toprettyxml(indent="  ")


def _write_metadata(root: ET.Element, md: Metadata) -> None:
    m = ET.SubElement(root, "Metadata")
    d = md.to_xml_dict()
    _IDS = {'TDP_ID': '10010', 'AdditionalIDs': '10020', 'Name': '10030', 'Description': '10040', 'Version': '10050', 'CreatedDate': '10060', 'ModifiedDate': '10070', 'LifecycleStatus': '10080', 'Author': '10090', 'Organization': '10100', 'Contact': '10110', 'Licensing': '10120', 'InformationClassification': '10130', 'ConfidentialityLevel': '10140', 'CriticalityLevel': '10150'}
    for key, val in d.items():
        _sub(m, key, str(val), _IDS.get(key, ""))


def _write_version(root: ET.Element, v: VersionInfo) -> None:
    ve = ET.SubElement(root, "Version")
    d = v.to_xml_dict()
    _IDS = {'UniqueID': '11010', 'AssemblyID': '11020', 'Revision': '11030', 'Checksum': '11040', 'Signature': '11050', 'EncryptionEnabled': '11060', 'EncryptionAlgorithm': '11070'}
    _CE_IDS = {'ChangeID': '11100', 'Timestamp': '11110', 'Author': '11120', 'Description': '11130'}
    for key, val in d.items():
        if key == "ChangeHistory":
            ch = ET.SubElement(ve, "ChangeHistory")
            for entry in val:
                ce = ET.SubElement(ch, "ChangeEntry")
                for ek, ev in entry.items():
                    _sub(ce, ek, str(ev), _CE_IDS.get(ek, ""))
        else:
            _sub(ve, key, str(val), _IDS.get(key, ""))


def _write_geometry(root: ET.Element, geometries: list) -> None:
    g_root = ET.SubElement(root, "Geometry")
    _IDS = {'id': '12010', 'FileName': '12020', 'FileFormat': '12030', 'FileSize': '12040', 'Checksum': '12050', 'Dimensions': '12060', 'Preview': '12070', 'SourcePath': ''}
    for g in geometries:
        ge = ET.SubElement(g_root, "GeometryFile")
        d = g.to_xml_dict()
        for key, val in d.items():
            _sub(ge, key, str(val), _IDS.get(key, ""))


def _write_overview(root: ET.Element, ov: ManufacturingOverview) -> None:
    o = ET.SubElement(root, "ManufacturingOverview")
    d = ov.to_xml_dict()
    _IDS = {'Description': '13010', 'ManufacturingMethod': '13020', 'Material': '13030'}
    for key, val in d.items():
        if key == "Standards":
            std_root = ET.SubElement(o, "Standards")
            for s in val:
                _sub(std_root, "Standard", s)
        else:
            _sub(o, key, str(val), _IDS.get(key, ""))


def _write_process_options(root: ET.Element, options: list) -> None:
    po_root = ET.SubElement(root, "ProcessOptions")
    for opt in options:
        po = ET.SubElement(po_root, "ProcessOption")
        d = opt.to_xml_dict()
        _IDS = {'OptionName': '14010', 'Description': '14020', 'Maturity': '14030', 'Revision': '14040'}
        for key, val in d.items():
            if key == "Steps":
                steps_el = ET.SubElement(po, "Steps")
                for step_dict in val:
                    _write_step_element(steps_el, step_dict)
            else:
                _sub(po, key, str(val), _IDS.get(key, ""))


def _write_step_element(parent: ET.Element, sd: dict) -> None:
    s = ET.SubElement(parent, "Step")
    _IDS = {'id': '15010', 'sequence': '15020', 'name': '15030', 'description': '15040', 'manufacturing_method': '15050', 'orientation': '15060', 'operator_count': '15115', 'material': '15200', 'material_batch': '15210', 'material_pretreatment': '15220', 'material_quantity': '15230', 'material_shelf_life': '15240', 'env_temp_min': '15300', 'env_temp_max': '15310', 'env_humidity_min': '15320', 'env_humidity_max': '15330', 'airflow': '15340', 'env_cleanroom_class': '15350', 'machine': '15400', 'tools': '15410', 'software': '15420', 'power_kw': '15430', 'compressed_air_bar': '15440', 'vacuum': '15450', 'cooling': '15460', 'floorarea': '15470', 'eqpheight': '15480', 'weight': '15490', 'other_equipment': '15500', 'inspection_points': '15610', 'sampling_plan': '15620', 'tolerances': '15630', 'surface_quality': '15640', 'acceptance_criteria': '15650', 'nonacceptance_handling': '15660', 'required_docs': '15670', 'required_training': '15680', 'requirement_source': '15690', 'ppe': '15700', 'chemical_risks': '15710', 'thermal_risks': '15720', 'mechanical_risks': '15730', 'esd_risks': '15740', 'other_safety': '15750', 'post_processing': '15800', 'notes': '15810'}
    _ATT_IDS = {'FileName': '15950', 'SourcePath': '15960', 'FileFormat': '15970', 'FileSize': '15980', 'Checksum': '15990'}
    for key, val in sd.items():
        if key == "attachments":
            att_root = ET.SubElement(s, "Attachments")
            for att in val:
                a = ET.SubElement(att_root, "Attachment")
                for ak, av in att.items():
                    _sub(a, ak, str(av), _ATT_IDS.get(ak, ""))
        elif key == "inputs":
            inp = ET.SubElement(s, "Inputs")
            for v in val:
                _sub(inp, "Input", v)
        elif key == "outputs":
            out = ET.SubElement(s, "Outputs")
            for v in val:
                _sub(out, "Output", v)
        elif key == "build_files":
            bf_el = ET.SubElement(s, "BuildFileRefs")
            for v in val:
                _sub(bf_el, "Ref", v)
        elif key == "duration":
            dur = ET.SubElement(s, "Duration")
            _sub(dur, "Hours", str(val.get("hours", 0)))
            _sub(dur, "Minutes", str(val.get("minutes", 0)))
        elif key == "inspection_methods":
            im = ET.SubElement(s, "InspectionMethods")
            im.set("fieldId", "15600")
            for m in val:
                _sub(im, "Method", m)
        elif key == "parameters":
            pm = ET.SubElement(s, "Parameters")
            for pk, pv in val.items():
                p = ET.SubElement(pm, "Parameter")
                p.set("name", pk)
                p.set("fieldId", "15900")
                p.text = str(pv)
        else:
            _sub(s, key, str(val), _IDS.get(key, ""))


def _write_build_files(root: ET.Element, build_files: list) -> None:
    bf_root = ET.SubElement(root, "BuildFiles")
    for bf in build_files:
        b = ET.SubElement(bf_root, "BuildFile")
        d = bf.to_xml_dict()
        _IDS = {'id': '16010', 'FileName': '16020', 'FileFormat': '16030', 'FileSize': '16040', 'FileType': '16050', 'Checksum': '16060'}
        _PR  = {'Manufacturer': '16100', 'Model': '16110', 'SerialNumber': '16120'}
        _MT  = {'Name': '16200', 'Grade': '16210', 'BatchNumber': '16220'}
        _CT  = {'Certified': '16300', 'CertificationBody': '16310', 'CertificateID': '16320', 'IssueDate': '16330', 'ExpiryDate': '16340'}
        _SUB_IDS = {"Printer": _PR, "Material": _MT, "Certification": _CT}
        for key, val in d.items():
            if key in ("Printer", "Material", "Certification"):
                sub = ET.SubElement(b, key)
                for sk, sv in val.items():
                    _sub(sub, sk, str(sv), _SUB_IDS[key].get(sk, ""))
            else:
                _sub(b, key, str(val), _IDS.get(key, ""))


def _write_optional(root: ET.Element, opt: OptionalData) -> None:
    o = ET.SubElement(root, "OptionalData")
    cad_root = ET.SubElement(o, "AdditionalCAD")
    _CAD = {'FileName': '17010', 'FileFormat': '17020', 'FileSize': '17030', 'Checksum': '17040', 'Description': '17050', 'SourcePath': '17060'}
    _IMG = {'FileName': '17100', 'FileFormat': '17110', 'FileSize': '17120', 'Checksum': '17130', 'Description': '17140', 'SourcePath': '17150'}
    for cad in opt.additional_cad:
        c = ET.SubElement(cad_root, "CADFile")
        for k, v in cad.to_xml_dict().items():
            _sub(c, k, str(v), _CAD.get(k, ""))
    img_root = ET.SubElement(o, "Images")
    for img in opt.images:
        i = ET.SubElement(img_root, "Image")
        for k, v in img.to_xml_dict().items():
            _sub(i, k, str(v), _IMG.get(k, ""))


def _write_quality(root: ET.Element, q: QualityData) -> None:
    qe = ET.SubElement(root, "Quality")
    _TR = {'SerialNumberFormat': '18010', 'BatchIDFormat': '18020', 'MaterialLotFormat': '18030', 'LabelingRequirements': '18040', 'TraceabilityLevel': '18050'}
    _RI = {'TechnicalPerformance': '18100', 'SafetyCriticality': '18110', 'IdentifiedRisks': '18120'}
    _AP = {'Approver': '18300', 'Status': '18310', 'Timestamp': '18320', 'Conditions': '18330', 'EvidenceRefs': '18340'}
    # Traceability
    tr = ET.SubElement(qe, "Traceability")
    for k, v in q.traceability.to_xml_dict().items():
        _sub(tr, k, str(v), _TR.get(k, ""))
    # Risks
    ri = ET.SubElement(qe, "Risks")
    for k, v in q.risks.to_xml_dict().items():
        _sub(ri, k, str(v), _RI.get(k, ""))
    _sub(qe, "ProcessQualityNotes", q.process_quality_notes, "18200")
    # Approval
    ap = ET.SubElement(qe, "Approval")
    for k, v in q.approval.to_xml_dict().items():
        _sub(ap, k, str(v), _AP.get(k, ""))


def _write_packing(root: ET.Element, p: PackingAndSafety) -> None:
    pe = ET.SubElement(root, "PackingAndSafety")
    d = p.to_xml_dict()
    _IDS = {'PackingMaterial': '19010', 'Cushioning': '19020', 'MoistureProtection': '19030', 'SurfaceProtection': '19040', 'LabelFragile': '19050', 'LabelThisSideUp': '19060', 'LabelDoNotStack': '19070', 'LabelESD': '19080', 'OtherLabels': '19090', 'AllowedLifting': '19100', 'ForbiddenLifting': '19110', 'COGDescription': '19120', 'HandlingForces': '19130', 'ESDRequirements': '19140', 'TransportOrientation': '19200', 'SecuringMethod': '19210', 'SpecialTransport': '19220', 'TempMin': '19240', 'TempMax': '19250', 'HumidityMin': '19260', 'HumidityMax': '19270', 'Stackable': '19280', 'MaxStackLayers': '19290', 'PPE': '19300', 'EdgeRisks': '19310', 'Weight': '19320', 'ManualLiftLimit': '19330', 'ChemicalRisks': '19340', 'ThermalRisks': '19350', 'OtherSafety': '19360'}
    for key, val in d.items():
        if key == "HazmatClasses":
            haz = ET.SubElement(pe, "HazmatClasses")
            haz.set("fieldId", "19230")
            for cls in val:
                _sub(haz, "Class", cls)
        else:
            _sub(pe, key, str(val), _IDS.get(key, ""))


# ---------------------------------------------------------------------------
# DESERIALISE: XML string → TDPPackage
# ---------------------------------------------------------------------------

def from_xml_string(xml_str: str) -> TDPPackage:
    root = ET.fromstring(xml_str)
    return TDPPackage(
        metadata=_read_metadata(root),
        version=_read_version(root),
        geometry=_read_geometry(root),
        overview=_read_overview(root),
        process_options=_read_process_options(root),
        build_files=_read_build_files(root),
        optional=_read_optional(root),
        quality=_read_quality(root),
        packing=_read_packing(root),
    )


def _read_metadata(root: ET.Element) -> Metadata:
    m = root.find("Metadata")
    if m is None:
        return Metadata()
    d = {child.tag: (child.text or "").strip() for child in m}
    return Metadata.from_xml_dict(d)


def _read_version(root: ET.Element) -> VersionInfo:
    v = root.find("Version")
    if v is None:
        return VersionInfo()
    d = {}
    history = []
    for child in v:
        if child.tag == "ChangeHistory":
            for ce in child.findall("ChangeEntry"):
                entry = {c.tag: (c.text or "").strip() for c in ce}
                history.append(entry)
        else:
            d[child.tag] = (child.text or "").strip()
    d["ChangeHistory"] = history
    return VersionInfo.from_xml_dict(d)


def _read_geometry(root: ET.Element) -> list:
    g_root = root.find("Geometry")
    if g_root is None:
        return []
    result = []
    for ge in g_root.findall("GeometryFile"):
        d = {child.tag: (child.text or "").strip() for child in ge}
        result.append(Geometry.from_xml_dict(d))
    return result


def _read_overview(root: ET.Element) -> ManufacturingOverview:
    o = root.find("ManufacturingOverview")
    if o is None:
        return ManufacturingOverview()
    d = {}
    standards = []
    for child in o:
        if child.tag == "Standards":
            standards = [(s.text or "").strip() for s in child.findall("Standard")]
        else:
            d[child.tag] = (child.text or "").strip()
    d["Standards"] = standards
    return ManufacturingOverview.from_xml_dict(d)


def _read_process_options(root: ET.Element) -> list:
    po_root = root.find("ProcessOptions")
    if po_root is None:
        return []
    result = []
    for po in po_root.findall("ProcessOption"):
        d = {}
        steps = []
        for child in po:
            if child.tag == "Steps":
                steps = [_read_step_element(s) for s in child.findall("Step")]
            else:
                d[child.tag] = (child.text or "").strip()
        d["Steps"] = steps
        result.append(ProcessOption.from_xml_dict(d))
    return result


def _read_step_element(s: ET.Element) -> dict:
    d = {}
    for child in s:
        tag = child.tag
        if tag == "Attachments":
            atts = []
            for a in child.findall("Attachment"):
                atts.append({c.tag: (c.text or "").strip() for c in a})
            d["attachments"] = atts
        elif tag == "Inputs":
            d["inputs"] = [(c.text or "").strip() for c in child.findall("Input")]
        elif tag == "Outputs":
            d["outputs"] = [(c.text or "").strip() for c in child.findall("Output")]
        elif tag == "BuildFileRefs":
            d["build_files"] = [(c.text or "").strip() for c in child.findall("Ref")]
        elif tag == "Duration":
            d["duration"] = {
                "hours": int((child.findtext("Hours") or "0").strip()),
                "minutes": int((child.findtext("Minutes") or "0").strip()),
            }
        elif tag == "InspectionMethods":
            d["inspection_methods"] = [(c.text or "").strip() for c in child.findall("Method")]
        elif tag == "Parameters":
            params = {}
            for p in child.findall("Parameter"):
                params[p.get("name", "")] = (p.text or "").strip()
            d["parameters"] = params
        else:
            d[tag] = (child.text or "").strip()
    return d


def _read_build_files(root: ET.Element) -> list:
    bf_root = root.find("BuildFiles")
    if bf_root is None:
        return []
    result = []
    for b in bf_root.findall("BuildFile"):
        d = {}
        for child in b:
            if child.tag in ("Printer", "Material", "Certification"):
                d[child.tag] = {c.tag: (c.text or "").strip() for c in child}
            else:
                d[child.tag] = (child.text or "").strip()
        result.append(BuildFile.from_xml_dict(d))
    return result


def _read_optional(root: ET.Element) -> OptionalData:
    o = root.find("OptionalData")
    if o is None:
        return OptionalData()
    cad_list = []
    img_list = []
    cad_root = o.find("AdditionalCAD")
    if cad_root is not None:
        for c in cad_root.findall("CADFile"):
            d = {child.tag: (child.text or "").strip() for child in c}
            cad_list.append(AdditionalCADModel.from_xml_dict(d))
    img_root = o.find("Images")
    if img_root is not None:
        for i in img_root.findall("Image"):
            d = {child.tag: (child.text or "").strip() for child in i}
            img_list.append(ReferenceImage.from_xml_dict(d))
    return OptionalData(additional_cad=cad_list, images=img_list)


def _read_quality(root: ET.Element) -> QualityData:
    qe = root.find("Quality")
    if qe is None:
        return QualityData()
    tr_el = qe.find("Traceability")
    ri_el = qe.find("Risks")
    ap_el = qe.find("Approval")
    return QualityData(
        traceability=TraceabilityData.from_xml_dict(
            {c.tag: (c.text or "").strip() for c in tr_el} if tr_el is not None else {}
        ),
        risks=RiskData.from_xml_dict(
            {c.tag: (c.text or "").strip() for c in ri_el} if ri_el is not None else {}
        ),
        process_quality_notes=_find_text(qe, "ProcessQualityNotes"),
        approval=ApprovalData.from_xml_dict(
            {c.tag: (c.text or "").strip() for c in ap_el} if ap_el is not None else {}
        ),
    )


def _read_packing(root: ET.Element) -> PackingAndSafety:
    pe = root.find("PackingAndSafety")
    if pe is None:
        return PackingAndSafety()
    d = {}
    for child in pe:
        if child.tag == "HazmatClasses":
            d["HazmatClasses"] = [(c.text or "").strip() for c in child.findall("Class")]
        else:
            d[child.tag] = (child.text or "").strip()
    return PackingAndSafety.from_xml_dict(d)
