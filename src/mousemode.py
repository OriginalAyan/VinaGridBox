# Mouse interaction adapted from ChimeraX-Vinardock.
# Upstream project: https://github.com/rquiroga7/ChimeraX-Vinardock
# Original interaction implementation by Rodrigo Quiroga, distributed under
# the GNU Lesser General Public License, version 2.1 (LGPL-2.1).
#
# Modified by Ayan Bhowmik on 2026-10-16 for VinaGridBox.
# The adapted modes move the VinaBoxModel using left-drag and resize the
# intersected box face using right-drag (or Shift+left-drag in move mode).
# See LICENSE.txt and THIRD_PARTY_NOTICES.md.

import numpy as np
from chimerax.mouse_modes import MouseMode

MOVE_MODE = "vinabox box move"
RESIZE_MODE = "vinabox box resize"


def _find_box(session):
    from .box import VinaBoxModel
    for model in session.models.list():
        if isinstance(model, VinaBoxModel):
            return model
    return None


def register_mousemodes(session):
    """Register the two VinaGridBox mouse modes if they are not registered."""
    if not session.ui.is_gui:
        return
    mm = session.ui.mouse_modes
    if mm.named_mode(MOVE_MODE) is None:
        mm.add_mode(VinaBoxMouseMode(session, resize=False))
    if mm.named_mode(RESIZE_MODE) is None:
        mm.add_mode(VinaBoxMouseMode(session, resize=True))


def _notify_tool(box):
    tool = getattr(box, "_tool", None)
    if tool is not None:
        try:
            tool.mark_manual_edit()
            tool.sync_from_model()
        except (RuntimeError, AttributeError):
            # The GUI may have been closed while an interaction event is pending.
            pass


class VinaBoxMouseMode(MouseMode):
    """Left-drag moves the box; right-drag resizes the ray-hit face."""

    name = MOVE_MODE

    def __init__(self, session, resize=False):
        super().__init__(session)
        self._resize_only = bool(resize)
        if resize:
            self.name = RESIZE_MODE
        self._box = None
        self._action = None
        self._resize = None
        self._last = None
        self._pixel_size = 1.0
        self._undo_before = None
        self._undo_name = None
        self._moved = False

    def mouse_down(self, event):
        super().mouse_down(event)
        self._undo_before = None
        self._undo_name = None
        self._moved = False
        self._last = event.position()
        self._box = _find_box(self.session)
        self._action = None
        self._resize = None
        if self._box is None:
            return
        view = self.session.main_view
        line = view.clip_plane_points(*self._last)
        if line[0] is None or line[1] is None:
            return
        self._pixel_size = view.pixel_size(self._box.center)
        if self._resize_only or event.shift_down():
            self._resize = self._pick_face(line)
            self._action = 'resize' if self._resize is not None else None
        else:
            # When the interaction checkbox is enabled, left dragging moves
            # the whole box. This temporarily replaces normal left-button use.
            self._action = 'move'
        if self._action is not None:
            from .undo_support import capture_state
            self._undo_before = capture_state(self.session, tool=getattr(self._box, "_tool", None))
            self._undo_name = "Resize Vina box" if self._action == "resize" else "Move Vina box"
            self._moved = False

    def mouse_drag(self, event):
        if self._box is None or self._last is None or self._action is None:
            return
        x0, y0 = self._last
        x, y = event.position()
        dx, dy = x - x0, y - y0
        if dx == 0 and dy == 0:
            return
        self._last = (x, y)
        if self._action == 'resize':
            self._resize_box(dx, dy)
        else:
            self._move_box(dx, dy)
        self._moved = True
        _notify_tool(self._box)

    def mouse_up(self, event):
        if self._undo_before is not None and self._moved:
            from .undo_support import capture_state, record_state_change
            tool = getattr(self._box, "_tool", None)
            after = capture_state(self.session, tool=tool)
            record_state_change(self.session, self._undo_before, after, self._undo_name)
        self._box = None
        self._action = None
        self._resize = None
        self._last = None
        self._undo_before = None
        self._undo_name = None
        self._moved = False
        super().mouse_up(event)

    def _move_box(self, dx, dy):
        view = self.session.main_view
        step = view.camera.position.transform_vector(
            (dx * self._pixel_size, -dy * self._pixel_size, 0.0))
        center = np.asarray(self._box.center, dtype=np.float64) + np.asarray(step, dtype=np.float64)
        self._box.set_box(center, self._box.size)

    def _resize_box(self, dx, dy):
        axis, side = self._resize
        normal = np.zeros(3, dtype=np.float64)
        normal[axis] = 1.0 if side else -1.0
        view = self.session.main_view
        camera_normal = view.camera.position.inverse().transform_vector(normal)
        growth = (camera_normal[0] * dx - camera_normal[1] * dy) * self._pixel_size
        size = np.array(self._box.size, dtype=np.float64)
        center = np.array(self._box.center, dtype=np.float64)
        new_size = max(0.5, float(size[axis] + growth))
        actual = new_size - size[axis]
        size[axis] = new_size
        # Move the dragged face; keep the opposite face fixed.
        center[axis] += 0.5 * actual if side else -0.5 * actual
        self._box.set_box(center, size)

    def _pick_face(self, line):
        """Return (axis, side) for the first box face intersected by the view ray."""
        p0 = np.asarray(line[0], dtype=np.float64)
        direction = np.asarray(line[1], dtype=np.float64) - p0
        lo = np.asarray(self._box.min_corner, dtype=np.float64)
        hi = np.asarray(self._box.max_corner, dtype=np.float64)
        best = None
        best_t = None
        for axis in range(3):
            for side, value in ((1, hi[axis]), (0, lo[axis])):
                if abs(direction[axis]) < 1e-9:
                    continue
                t = (value - p0[axis]) / direction[axis]
                if t <= 0.0:
                    continue
                point = p0 + t * direction
                inside = True
                for other in range(3):
                    if other == axis:
                        continue
                    if point[other] < lo[other] - 1e-6 or point[other] > hi[other] + 1e-6:
                        inside = False
                        break
                if inside and (best_t is None or t < best_t):
                    best_t = t
                    best = (axis, side)
        return best
