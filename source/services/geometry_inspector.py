# services/geometry_inspector.py


def get_dimensions(path: str) -> str:
    """Return 'W: x mm, D: y mm, H: z mm' string, or empty string on failure."""
    try:
        import trimesh
        mesh = trimesh.load(path, force="mesh")
        w, d, h = mesh.extents
        return f"W: {w:.3f} mm, D: {d:.3f} mm, H: {h:.3f} mm"
    except Exception:
        return ""
