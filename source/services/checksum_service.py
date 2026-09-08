# services/checksum_service.py
import hashlib
import os


def file_checksum(path: str, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    """Return hex digest of a file, or empty string if path is missing."""
    if not path or not os.path.exists(path):
        return ""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def refresh_geometry_checksums(geometries) -> None:
    for g in geometries:
        g.checksum = file_checksum(g.source_path)


def refresh_buildfile_checksums(build_files) -> None:
    for bf in build_files:
        bf.checksum = file_checksum(bf.source_path)


def refresh_optional_checksums(optional) -> None:
    for cad in optional.additional_cad:
        cad.checksum = file_checksum(cad.source_path)
    for img in optional.images:
        img.checksum = file_checksum(img.source_path)


def refresh_attachment_checksums(steps) -> None:
    for option in steps:
        for step in option.steps:
            for att in step.attachments:
                att.checksum = file_checksum(att.source_path)
