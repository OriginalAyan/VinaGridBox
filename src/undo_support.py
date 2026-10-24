"""Undo/redo support for VinaGridBox.

This module uses ChimeraX's per-session UndoAction API. GUI visibility is
intentionally not captured: showing or hiding the tool window is a UI action,
not an edit to the docking box.
"""

import time
import weakref

from chimerax.core.undo import UndoAction


MERGE_WINDOW_SECONDS = 1.25


def _is_live(model):
    if model is None:
        return False
    try:
        return not bool(model.deleted)
    except (AttributeError, RuntimeError):
        return False


def find_box_model(session, tool=None):
    """Return the tool's live box, or the first live VinaBoxModel in the scene."""
    if tool is not None:
        box = getattr(tool, "box", None)
        if _is_live(box):
            return box
    try:
        from .box import VinaBoxModel
    except ImportError:
        return None
    for model in session.models.list():
        if isinstance(model, VinaBoxModel) and _is_live(model):
            return model
    return None


def find_tool(session):
    """Return the running VinaGridBox tool, if it exists."""
    try:
        for tool in session.tools.list():
            if tool.__class__.__name__ == "VinaGridBoxTool":
                return tool
    except (AttributeError, RuntimeError):
        pass
    return None


def _coords_tuple(coords):
    if coords is None:
        return None
    return tuple(tuple(float(v) for v in row) for row in coords)


def capture_state(session, tool=None, overrides=None):
    """Capture serializable box and relevant GUI state before/after an edit."""
    if tool is None:
        tool = find_tool(session)
    box = find_box_model(session, tool)
    if box is None:
        box_state = None
    else:
        box_state = {
            "center": tuple(float(v) for v in box.center),
            "size": tuple(float(v) for v in box.size),
            "rgb": tuple(int(v) for v in box._visual_rgb),
            "internal_visible": bool(box._internal_visible),
            "draw_on_top": bool(box.draw_on_top),
        }

    tool_state = None
    if tool is not None:
        fields = {}
        for key, widget in getattr(tool, "fields", {}).items():
            try:
                fields[key] = float(widget.value())
            except (RuntimeError, AttributeError):
                pass
        try:
            padding = float(tool.padding.value())
        except (RuntimeError, AttributeError):
            padding = 4.0
        try:
            spacing = float(tool.spacing.value())
        except (RuntimeError, AttributeError):
            spacing = 0.375
        try:
            show_internal = bool(tool.show_internal.isChecked())
        except (RuntimeError, AttributeError):
            show_internal = bool(box_state and box_state["internal_visible"])
        try:
            draw_on_top = bool(tool.draw_on_top_cb.isChecked())
        except (RuntimeError, AttributeError):
            draw_on_top = bool(box_state and box_state["draw_on_top"])
        tool_state = {
            "box_source": getattr(tool, "_box_source", "manual"),
            "selection_coords": _coords_tuple(getattr(tool, "_selection_coords", None)),
            "selection_method": getattr(tool, "_selection_method", "bounds"),
            "padding": padding,
            "spacing": spacing,
            "field_values": fields,
            "show_internal": show_internal,
            "draw_on_top": draw_on_top,
        }
        if overrides:
            tool_state.update(overrides)

    return {"box": box_state, "tool": tool_state}


def _snapshot_equal(a, b):
    # Snapshots contain only dictionaries, numbers, strings, booleans and tuples.
    return a == b


class VinaBoxUndoAction(UndoAction):
    """Reversible snapshot action for a Vina box and its relevant controls."""

    def __init__(self, session, name, before, after, merge_key=None):
        super().__init__(name)
        self._session_ref = weakref.ref(session)
        self.before = before
        self.after = after
        self.merge_key = merge_key
        self.timestamp = time.monotonic()

    def undo(self):
        session = self._session_ref()
        if session is not None:
            restore_state(session, self.before)

    def redo(self):
        session = self._session_ref()
        if session is not None:
            restore_state(session, self.after)


def record_state_change(session, before, after, name, merge_key=None):
    """Register a box state transition with ChimeraX undo/redo.

    Rapid repeated spin-box edits are merged into a single undo item. A mouse
    drag should call this once on release, not once per motion event.
    """
    if before is None or after is None or _snapshot_equal(before, after):
        return None
    undo_manager = getattr(session, "undo", None)
    if undo_manager is None or not hasattr(undo_manager, "register"):
        return None

    now = time.monotonic()
    if merge_key:
        stack = getattr(undo_manager, "undo_stack", ())
        if stack:
            previous = stack[-1]
            if (isinstance(previous, VinaBoxUndoAction)
                    and previous._session_ref() is session
                    and previous.merge_key == merge_key
                    and now - previous.timestamp <= MERGE_WINDOW_SECONDS):
                previous.after = after
                previous.timestamp = now
                previous.name = name
                return previous

    action = VinaBoxUndoAction(session, name, before, after, merge_key)
    undo_manager.register(action)
    return action


def _set_model_color_without_undo(box, rgb):
    box._visual_rgb = tuple(int(v) for v in rgb[:3])
    box._ignore_color_trigger = True
    try:
        box.color = (*box._visual_rgb, 255)
    finally:
        box._ignore_color_trigger = False


def restore_state(session, snapshot):
    """Restore a previously captured box state without adding another undo."""
    tool = find_tool(session)
    current = find_box_model(session, tool)
    box_state = snapshot.get("box")

    if box_state is None:
        if current is not None:
            current.set_tool(None)
            current.delete()
        box = None
    else:
        from .box import VinaBoxModel
        center = tuple(box_state["center"])
        size = tuple(box_state["size"])
        if current is None:
            box = VinaBoxModel(session, center, size)
            session.models.add([box])
        else:
            box = current
        box._center = center
        box._size = size
        box._internal_visible = bool(box_state["internal_visible"])
        box._draw_on_top = bool(box_state["draw_on_top"])
        _set_model_color_without_undo(box, box_state["rgb"])
        box._rebuild()
        if tool is not None:
            box.set_tool(tool)

    if tool is not None:
        tool.box = box
        tool_state = snapshot.get("tool") or {}
        tool._box_source = tool_state.get("box_source", "manual")
        selection_coords = tool_state.get("selection_coords")
        if selection_coords is None:
            tool._selection_coords = None
        else:
            import numpy as np
            tool._selection_coords = np.asarray(selection_coords, dtype=float)
        tool._selection_method = tool_state.get("selection_method", "bounds")

        # Restore GUI controls without firing their normal callbacks and adding
        # a second undo action. The tool window is not shown/hidden by undo.
        tool._updating = True
        widgets = []
        for attr in ("padding", "spacing", "show_internal", "draw_on_top_cb", "selection_method_combo"):
            widget = getattr(tool, attr, None)
            if widget is not None:
                try:
                    widgets.append((widget, widget.blockSignals(True)))
                except RuntimeError:
                    pass
        try:
            field_values = tool_state.get("field_values", {})
            if box is not None:
                c, s = box.center, box.size
                values = {"cx": c[0], "cy": c[1], "cz": c[2],
                          "sx": s[0], "sy": s[1], "sz": s[2]}
            else:
                values = field_values
            for key, value in values.items():
                widget = getattr(tool, "fields", {}).get(key)
                if widget is not None:
                    try:
                        widget.setValue(float(value))
                    except RuntimeError:
                        pass
            if hasattr(tool, "padding"):
                tool.padding.setValue(float(tool_state.get("padding", 4.0)))
            if hasattr(tool, "spacing"):
                tool.spacing.setValue(float(tool_state.get("spacing", 0.375)))
            if hasattr(tool, "show_internal"):
                internal_checked = (box_state["internal_visible"] if box_state is not None
                                    else tool_state.get("show_internal", False))
                tool.show_internal.setChecked(bool(internal_checked))
            if hasattr(tool, "draw_on_top_cb"):
                top_checked = (box_state["draw_on_top"] if box_state is not None
                               else tool_state.get("draw_on_top", False))
                tool.draw_on_top_cb.setChecked(bool(top_checked))
            combo = getattr(tool, "selection_method_combo", None)
            if combo is not None:
                idx = combo.findData(tool._selection_method)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            tool._last_padding_value = float(tool_state.get("padding", 4.0))
            tool._last_selection_method = tool._selection_method
        finally:
            for widget, previous in reversed(widgets):
                try:
                    widget.blockSignals(previous)
                except RuntimeError:
                    pass
            tool._updating = False

        if box is not None:
            tool.sync_from_model()
        else:
            for label in getattr(tool, "bounds_labels", {}).values():
                try:
                    label.setText("—")
                except RuntimeError:
                    pass
            try:
                tool.info.setText("No Vina box.")
            except (RuntimeError, AttributeError):
                pass
