# ui/widgets/three_d_viewer.py
"""
Software-rendered 3-D model preview.

Rendering approach:
  - Back-face culling eliminates rearward triangles.
  - Painter's algorithm (back-to-front Z sort) for ordering.
  - Each triangle is inflated by ~0.5 px before drawing to
    close sub-pixel gaps between adjacent faces, which is the
    true cause of horizontal-line artefacts in QPainter rendering.
  - Supersampling 2x for edge quality.
  - Hard limit: 60 000 triangles; larger models show a text notice.
"""
from __future__ import annotations

import struct, math, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui  import QPainter, QColor, QPen, QPolygonF, QBrush, QImage
from PyQt6.QtCore import Qt, QPointF, QSize


# ── geometry ─────────────────────────────────────────────────────────────────
def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _sub(a, b):  return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _dot(a, b):  return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _norm(v):
    m = math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    return (v[0]/m, v[1]/m, v[2]/m) if m > 1e-12 else (0., 0., 1.)
def _rot_y(v, ca, sa):
    x, y, z = v
    return (x*ca + z*sa, y, -x*sa + z*ca)


# ── loaders ───────────────────────────────────────────────────────────────────
def _load_stl(path: str) -> list:
    with open(path, "rb") as f:
        hdr = f.read(80); cnt = f.read(4); data = f.read()
    if len(hdr) < 80 or len(cnt) < 4:
        return []
    n = struct.unpack("<I", cnt)[0]
    try:
        is_ascii = (hdr.decode("utf-8", errors="replace").strip().lower()
                    .startswith("solid") and b"endsolid" in data)
    except Exception:
        is_ascii = False
    if is_ascii:
        tris, buf = [], []
        with open(path, "r", errors="replace") as f:
            for line in f:
                ls = line.strip()
                if ls.startswith("vertex"):
                    p = ls.split()
                    try:
                        buf.append((float(p[1]), float(p[2]), float(p[3])))
                    except (IndexError, ValueError):
                        pass
                if len(buf) == 3:
                    tris.append((buf[0], buf[1], buf[2]))
                    buf = []
        return tris
    tris = []
    for i in range(min(n, len(data) // 50)):
        v = struct.unpack_from("<9f", data, i * 50 + 12)
        tris.append((v[0:3], v[3:6], v[6:9]))
    return tris


def _load_3mf(path: str) -> list:
    try:
        with zipfile.ZipFile(path) as zf:
            name = next((n for n in zf.namelist() if n.endswith(".model")), None)
            if not name:
                return []
            root = ET.fromstring(zf.read(name))
    except Exception:
        return []
    NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    tris = []
    for mesh in root.iter(f"{{{NS}}}mesh"):
        vel = mesh.find(f"{{{NS}}}vertices")
        tel = mesh.find(f"{{{NS}}}triangles")
        if vel is None or tel is None:
            continue
        verts = []
        for v in vel.findall(f"{{{NS}}}vertex"):
            try:
                verts.append((float(v.get("x", 0)),
                               float(v.get("y", 0)),
                               float(v.get("z", 0))))
            except ValueError:
                verts.append((0., 0., 0.))
        for t in tel.findall(f"{{{NS}}}triangle"):
            try:
                i0 = int(t.get("v1", 0))
                i1 = int(t.get("v2", 0))
                i2 = int(t.get("v3", 0))
                if max(i0, i1, i2) < len(verts):
                    tris.append((verts[i0], verts[i1], verts[i2]))
            except (ValueError, IndexError):
                pass
    return tris


# ── projection ────────────────────────────────────────────────────────────────
_CE = math.cos(math.radians(30))
_SE = math.sin(math.radians(30))

def _proj(v, scale, cx, cy):
    x, y, z = v
    return (cx + (x - z) * _CE * scale,
            cy + ((x + z) * _SE * 0.5 - y) * scale)


# ── polygon inflation — closes sub-pixel gaps between adjacent triangles ──────
def _inflate(pts, amount=0.6):
    """
    Move each vertex outward from the centroid by *amount* pixels.
    This fills the hairline gaps that QPainter leaves between adjacent
    polygons, which appear as horizontal lines at certain view angles.
    """
    cx = (pts[0][0] + pts[1][0] + pts[2][0]) / 3.0
    cy = (pts[0][1] + pts[1][1] + pts[2][1]) / 3.0
    result = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            f = (dist + amount) / dist
            result.append((cx + dx * f, cy + dy * f))
        else:
            result.append((x, y))
    return result


# ── viewer ────────────────────────────────────────────────────────────────────
class ThreeDViewer(QWidget):
    _TRIS_LIMIT = 60_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._centred:   list  = []
        self._span:      float = 1.0
        self._loaded:    bool  = False
        self._too_large: bool  = False
        self._rot:       float = 225.0

        self.setMinimumSize(260, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background:#1e2433; border-radius:6px;")

    # ── public ───────────────────────────────────────────────────────────────
    def load_model(self, path: str) -> None:
        ext = Path(path).suffix.lower()
        try:
            tris = (_load_stl(path) if ext == ".stl" else
                    _load_3mf(path) if ext == ".3mf" else [])
        except Exception:
            tris = []

        if not tris:
            self._loaded = False
            self._too_large = False
            self._centred = []
            self.update()
            return

        if len(tris) > self._TRIS_LIMIT:
            self._loaded = False
            self._too_large = True
            self._centred = []
            self.update()
            return

        self._too_large = False
        xs = [v[0] for t in tris for v in t]
        ys = [v[1] for t in tris for v in t]
        zs = [v[2] for t in tris for v in t]
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        cz = (max(zs) + min(zs)) / 2
        self._span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)) or 1.0
        self._centred = [
            ((t[0][0]-cx, t[0][1]-cy, t[0][2]-cz),
             (t[1][0]-cx, t[1][1]-cy, t[1][2]-cz),
             (t[2][0]-cx, t[2][1]-cy, t[2][2]-cz))
            for t in tris
        ]
        self._loaded = True
        self.update()

    def clear(self) -> None:
        self._loaded = False
        self._too_large = False
        self._centred = []
        self.update()

    def rotate(self, delta: float) -> None:
        self._rot = (self._rot + delta) % 360
        self.update()

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        w, h = self.width(), self.height()
        SS = 2
        ow, oh = w * SS, h * SS

        img = QImage(ow, oh, QImage.Format.Format_RGB32)
        img.fill(QColor("#1e2433"))

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._loaded and self._centred:
            self._render(p, ow, oh)
        else:
            p.setPen(QColor("#7788aa"))
            if self._too_large:
                msg = (f"Model exceeds {self._TRIS_LIMIT:,} triangles\n"
                       "and cannot be shown in preview.")
            else:
                msg = "No preview"
            p.drawText(0, 0, ow, oh, Qt.AlignmentFlag.AlignCenter, msg)

        p.end()

        sp = QPainter(self)
        sp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled = img.scaled(w, h,
                            Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        sp.drawImage(0, 0, scaled)
        sp.end()

    def _render(self, p: QPainter, W: int, H: int):
        scale = min(W, H) * 0.66 / self._span
        cx, cy = W / 2.0, H / 2.0

        ca = math.cos(math.radians(self._rot))
        sa = math.sin(math.radians(self._rot))

        L_KEY  = _norm(( 0.6,  1.0,  0.8))
        L_FILL = _norm((-0.8,  0.3, -0.4))
        L_RIM  = _norm(( 0.0, -0.8,  0.6))

        visible = []
        for tri in self._centred:
            r0 = _rot_y(tri[0], ca, sa)
            r1 = _rot_y(tri[1], ca, sa)
            r2 = _rot_y(tri[2], ca, sa)

            sx0, sy0 = _proj(r0, scale, cx, cy)
            sx1, sy1 = _proj(r1, scale, cx, cy)
            sx2, sy2 = _proj(r2, scale, cx, cy)

            # Back-face cull: screen-space signed area
            cross_z = (sx1-sx0)*(sy2-sy0) - (sy1-sy0)*(sx2-sx0)
            if cross_z >= 0:
                continue

            n = _norm(_cross(_sub(r1, r0), _sub(r2, r0)))
            shade = (max(0., _dot(n, L_KEY))
                     + max(0., _dot(n, L_FILL)) * 0.30
                     + max(0., _dot(n, L_RIM))  * 0.15
                     + 0.06)
            shade = min(shade, 1.0)

            depth = (r0[2] + r1[2] + r2[2]) / 3.0
            screen_pts = [(sx0, sy0), (sx1, sy1), (sx2, sy2)]
            visible.append((depth, shade, screen_pts))

        # Back-to-front
        visible.sort(key=lambda t: t[0])

        no_pen = QPen(Qt.PenStyle.NoPen)
        p.setPen(no_pen)

        for depth, shade, pts in visible:
            lum = shade
            r = int(80  + lum * 140)
            g = int(85  + lum * 140)
            b = int(100 + lum * 135)

            # Inflate polygon to close hairline gaps
            inflated = _inflate(pts, amount=0.7)

            poly = QPolygonF([QPointF(x, y) for x, y in inflated])
            p.setBrush(QBrush(QColor(r, g, b)))
            p.drawPolygon(poly)

    def sizeHint(self) -> QSize:
        return QSize(320, 280)
