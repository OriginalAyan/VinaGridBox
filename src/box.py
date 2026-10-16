from math import sqrt

from chimerax.core.models import Model, Surface, MODEL_COLOR_CHANGED
from chimerax.surface.shapes import cylinder_geometry
from chimerax.atomic import Atom

from .math_utils import (
    DEFAULT_SPACING,
    bounds_from_center_size,
    center_size_from_bounds,
    vina_config_text,
    vina_map_info,
)

DEFAULT_RGB = (40, 175, 245)
EDGE_RGBA = (255, 220, 70, 255)
INTERNAL_RGBA = (245, 145, 45, 165)
MIN_SIZE = 0.1


def _rgba(rgb, alpha):
    return (*tuple(int(v) for v in rgb), int(alpha))


def _cylinder_between(a, b, radius, n=10):
    va = b - a
    length = float(sqrt(float(va[0] ** 2 + va[1] ** 2 + va[2] ** 2)))
    if length <= 1e-8:
        return None
    import numpy as np
    axis = np.asarray(va, dtype=float) / length
    # Pick a reference vector not parallel to axis and construct an
    # orthonormal basis (u, v, axis).  Do not use ChimeraX vector helpers
    # here because the coordinates passed to this function are NumPy arrays.
    if abs(float(axis[0])) < 0.9:
        tmp = np.array([1.0, 0.0, 0.0], dtype=float)
    else:
        tmp = np.array([0.0, 1.0, 0.0], dtype=float)
    u = np.cross(axis, tmp)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    verts, norms, tris = cylinder_geometry(radius=radius, height=length, nz=2, nc=n, caps=True)
    # cylinder_geometry is aligned with +Z. Rotate the generated points so
    # +Z maps to the requested axis, then translate to the midpoint.
    rmat = np.column_stack((u, v, axis))
    verts = np.asarray(verts, dtype=float) @ rmat.T
    verts += (a + b) * 0.5
    norms = np.asarray(norms, dtype=float) @ rmat.T
    return verts, norms, tris


class VinaBoxModel(Model):
    def __init__(self, session, center, size, name="Vina Search Box"):
        super().__init__(name, session)
        self._center = None
        self._size = None
        self._visual_rgb = tuple(DEFAULT_RGB)
        self._surface = None
        self._internal = None
        self._tool = None
        self._internal_visible = False
        self._color_sync_pending = False
        self._color_handler = session.triggers.add_handler(MODEL_COLOR_CHANGED, self._on_model_color_changed)
        self.color = _rgba(self._visual_rgb, 255)
        self._set_initial(center, size)

    def set_tool(self, tool):
        self._tool = tool

    @property
    def center(self):
        return tuple(self._center)

    @property
    def size(self):
        return tuple(self._size)

    @property
    def min_corner(self):
        return bounds_from_center_size(self._center, self._size)[0]

    @property
    def max_corner(self):
        return bounds_from_center_size(self._center, self._size)[1]

    def box_bounds(self):
        return bounds_from_center_size(self._center, self._size)

    def _set_initial(self, center, size):
        self.set_box(center, size)

    def set_box(self, center, size):
        c, s = tuple(float(v) for v in center), tuple(float(v) for v in size)
        if any(v <= 0.0 for v in s):
            raise ValueError("All Vina box dimensions must be > 0 Å")
        self._center = c
        self._size = s
        self._rebuild()

    def set_face(self, axis, side, coordinate):
        lo, hi = self.box_bounds()
        lo = list(lo)
        hi = list(hi)
        eps = MIN_SIZE * 0.5
        if side == -1:
            lo[axis] = min(float(coordinate), hi[axis] - eps)
        else:
            hi[axis] = max(float(coordinate), lo[axis] + eps)
        self._center, self._size = center_size_from_bounds(lo, hi)
        self._rebuild()

    def set_internal_visible(self, visible):
        self._internal_visible = bool(visible)
        self._rebuild()

    def delete(self):
        if self._color_handler is not None:
            self.session.triggers.remove_handler(self._color_handler)
            self._color_handler = None
        super().delete()

    def _on_model_color_changed(self, trigger_name, data):
        source = data
        if source is self:
            color = getattr(source, "color", None)
        else:
            color = getattr(source, "color", None) if getattr(source, "parent", None) is self else None
        if color is None or getattr(source, "name", "").startswith("Vina_"):
            return
        self._visual_rgb = tuple(int(v) for v in color[:3])
        if not self._color_sync_pending:
            self._color_sync_pending = True
            from Qt.QtCore import QTimer
            QTimer.singleShot(0, self._apply_visual_color)

    def _apply_visual_color(self):
        self._color_sync_pending = False
        if not self.deleted:
            self._rebuild()

    def _destroy_children(self):
        for child in list(self.child_models()):
            child.delete()
        self._surface = None
        self._internal = None

    def _rebuild(self):
        if self.deleted:
            return
        self._destroy_children()
        lo, hi = self.box_bounds()
        import numpy as np
        corners = np.array([
            [lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]],
            [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
            [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]],
            [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]],
        ], dtype=float)
        faces = np.array([
            [0, 1, 2, 3], [4, 7, 6, 5],
            [0, 4, 5, 1], [1, 5, 6, 2],
            [2, 6, 7, 3], [4, 0, 3, 7],
        ], dtype=int)
        verts = corners
        tris = np.array([[f[0], f[1], f[2], f[0], f[2], f[3]] for f in faces], dtype=int).reshape(-1, 3)
        surf = Surface("Vina box", self.session)
        surf.set_geometry(verts, None, tris)
        surf.color = _rgba(self._visual_rgb, 32)
        surf.pickable = False
        surf.on_top = True
        self.add([surf])
        self._surface = surf

        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        radius = max(0.06, min(self._size) * 0.006)
        for a, b in edges:
            data = _cylinder_between(corners[a], corners[b], radius, n=12)
            if data is None:
                continue
            ev, en, et = data
            edge = Surface("Vina box edge", self.session)
            edge.set_geometry(ev, en, et)
            edge.color = EDGE_RGBA
            edge.pickable = False
            edge.on_top = True
            self.add([edge])

        if self._internal_visible:
            _, real_span = vina_map_info(self._size, DEFAULT_SPACING, False)
            center = np.asarray(self._center)
            half = np.asarray(real_span) * 0.5
            ilo, ihi = center-half, center+half
            ic = np.array([
                [ilo[0],ilo[1],ilo[2]], [ihi[0],ilo[1],ilo[2]],
                [ihi[0],ihi[1],ilo[2]], [ilo[0],ihi[1],ilo[2]],
                [ilo[0],ilo[1],ihi[2]], [ihi[0],ilo[1],ihi[2]],
                [ihi[0],ihi[1],ihi[2]], [ilo[0],ihi[1],ihi[2]],
            ], dtype=float)
            iedges = []
            for a,b in edges:
                data = _cylinder_between(ic[a], ic[b], max(0.03, radius*0.5), n=8)
                if data:
                    iedges.append(data)
            if iedges:
                verts2=[]; norms2=[]; tris2=[]; offset=0
                for ev,en,et in iedges:
                    verts2.append(ev); norms2.append(en); tris2.append(np.asarray(et)+offset); offset += len(ev)
                iv=np.vstack(verts2); inn=np.vstack(norms2); it=np.vstack(tris2)
                inner = Surface("Vina rounded map extent", self.session)
                inner.set_geometry(iv, inn, it)
                inner.color = INTERNAL_RGBA
                inner.pickable = False
                inner.on_top = True
                self.add([inner])
                self._internal = inner
