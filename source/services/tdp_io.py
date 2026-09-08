# services/tdp_io.py
"""
Handles all disk I/O for TDP packages.

A .tdp file is a ZIP archive containing:
  TDP.xml          — the main XML document
  Geometry/        — geometry files (STL, 3MF only; open triangle-mesh formats)
  BuildFiles/      — AM build files (gcode, 3mf, …)
  Optional/CAD/    — additional CAD models
  Optional/Images/ — reference images
  Attachments/     — step attachments (flat, prefixed by step id)
"""
import os
import shutil
import zipfile
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple

from models.tdp_package import TDPPackage
from models.version import ChangeEntry
from services import xml_serializer
from services import checksum_service


class TDPSaveError(Exception):
    pass


class TDPLoadError(Exception):
    pass


# ---------------------------------------------------------------------------
# SAVE
# ---------------------------------------------------------------------------

def save_tdp(output_path: str, package: TDPPackage, author: str = "") -> None:
    """
    Refresh all checksums, record a ChangeEntry, serialise to XML,
    copy all referenced files, and write a .tdp ZIP archive.
    """
    output_path = str(output_path)
    if not output_path.endswith(".tdp"):
        output_path += ".tdp"

    # 1. Refresh all file checksums
    checksum_service.refresh_geometry_checksums(package.geometry)
    checksum_service.refresh_buildfile_checksums(package.build_files)
    checksum_service.refresh_optional_checksums(package.optional)
    checksum_service.refresh_attachment_checksums(package.process_options)

    # 2. Add automatic ChangeEntry
    _record_change_entry(package, author)

    # 3. Compute package checksum (over XML without version checksum field)
    package.version.checksum = _compute_package_checksum(package)

    # 4. Generate XML
    xml_str = xml_serializer.to_xml_string(package)

    # 5. Write ZIP
    tmp_path = output_path + ".tmp"
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("TDP.xml", xml_str.encode("utf-8"))
            _pack_geometries(zf, package)
            _pack_build_files(zf, package)
            _pack_optional(zf, package)
            _pack_attachments(zf, package)
        # Atomic replace
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(tmp_path, output_path)
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise TDPSaveError(f"Failed to write TDP: {exc}") from exc


def _record_change_entry(package: TDPPackage, author: str) -> None:
    entry = ChangeEntry(
        change_id=f"CH-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        author=author or package.metadata.author or "Unknown",
        description="Package saved",
    )
    package.version.change_history.append(entry)


def _compute_package_checksum(package: TDPPackage) -> str:
    """SHA-256 of a canonical JSON snapshot (excluding version.checksum)."""
    snapshot = xml_serializer.to_xml_string(package)
    return hashlib.sha256(snapshot.encode("utf-8")).hexdigest()


def _pack_geometries(zf: zipfile.ZipFile, package: TDPPackage) -> None:
    for g in package.geometry:
        if g.source_path and os.path.exists(g.source_path):
            zf.write(g.source_path, f"Geometry/{g.file_name}")


def _pack_build_files(zf: zipfile.ZipFile, package: TDPPackage) -> None:
    for bf in package.build_files:
        if bf.source_path and os.path.exists(bf.source_path):
            zf.write(bf.source_path, f"BuildFiles/{bf.file_name}")


def _pack_optional(zf: zipfile.ZipFile, package: TDPPackage) -> None:
    for cad in package.optional.additional_cad:
        if cad.source_path and os.path.exists(cad.source_path):
            zf.write(cad.source_path, f"Optional/CAD/{cad.file_name}")
    for img in package.optional.images:
        if img.source_path and os.path.exists(img.source_path):
            zf.write(img.source_path, f"Optional/Images/{img.file_name}")


def _pack_attachments(zf: zipfile.ZipFile, package: TDPPackage) -> None:
    for opt in package.process_options:
        for step in opt.steps:
            for att in step.attachments:
                if att.source_path and os.path.exists(att.source_path):
                    arcname = f"Attachments/{step.id}/{att.file_name}"
                    zf.write(att.source_path, arcname)


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------

def load_tdp(tdp_path: str) -> Tuple[TDPPackage, str]:
    """
    Extract a .tdp archive to a temp directory, parse the XML,
    and fix all SourcePath references to point at the extracted files.
    Returns (package, extracted_dir) — caller is responsible for cleanup.
    """
    tdp_path = str(tdp_path)
    if not os.path.exists(tdp_path):
        raise TDPLoadError(f"File not found: {tdp_path}")

    extract_dir = tdp_path + "_extracted"
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)

    try:
        with zipfile.ZipFile(tdp_path, "r") as zf:
            zf.extractall(extract_dir)
    except Exception as exc:
        raise TDPLoadError(f"Failed to extract TDP: {exc}") from exc

    xml_path = os.path.join(extract_dir, "TDP.xml")
    if not os.path.exists(xml_path):
        raise TDPLoadError("TDP.xml missing from archive")

    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_str = f.read()
        package = xml_serializer.from_xml_string(xml_str)
    except Exception as exc:
        raise TDPLoadError(f"Failed to parse TDP.xml: {exc}") from exc

    # Repoint SourcePaths to extracted location
    _repoint_paths(package, extract_dir)

    return package, extract_dir


def _repoint_paths(package: TDPPackage, base: str) -> None:
    for g in package.geometry:
        candidate = os.path.join(base, "Geometry", g.file_name)
        if os.path.exists(candidate):
            g.source_path = candidate

    for bf in package.build_files:
        candidate = os.path.join(base, "BuildFiles", bf.file_name)
        if os.path.exists(candidate):
            bf.source_path = candidate

    for cad in package.optional.additional_cad:
        candidate = os.path.join(base, "Optional", "CAD", cad.file_name)
        if os.path.exists(candidate):
            cad.source_path = candidate

    for img in package.optional.images:
        candidate = os.path.join(base, "Optional", "Images", img.file_name)
        if os.path.exists(candidate):
            img.source_path = candidate

    for opt in package.process_options:
        for step in opt.steps:
            for att in step.attachments:
                candidate = os.path.join(base, "Attachments", step.id, att.file_name)
                if os.path.exists(candidate):
                    att.source_path = candidate
