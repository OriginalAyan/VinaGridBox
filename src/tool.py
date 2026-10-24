import numpy as np

from Qt.QtCore import Qt, QRect, QPoint, QSize
from Qt.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QLayout
)
from chimerax.core.tools import ToolInstance
from chimerax.core.commands import run
from chimerax.core.models import MODEL_COLOR_CHANGED
from chimerax.atomic import selected_atoms

from .box import VinaBoxModel, DEFAULT_SPACING, DEFAULT_RGB
from .math_utils import (
    vina_config_text, selection_bounds_box, vina_ligand_box, vina_map_info
)


class FlowLayout(QLayout):
    """A small wrapping Qt layout: fields reflow as the panel width changes."""
    def __init__(self, parent=None, margin=0, hspacing=6, vspacing=6):
        super().__init__(parent)
        self._items = []
        self._hspace = hspacing
        self._vspace = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, max(1, width), 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        right = rect.right() - margins.right()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width()
            if next_x > right and line_height > 0:
                x = rect.x() + margins.left()
                y += line_height + self._vspace
                next_x = x + hint.width()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x + self._hspace
            line_height = max(line_height, hint.height())
        return y + line_height + margins.bottom() - rect.y()


class VinaGridBoxTool(ToolInstance):
    SESSION_ENDURING = False
    help = "help:user/tools/vinagridbox.html"

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        self.display_name = "Vina Grid Box"
        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)
        self.box = None
        self._updating = False
        self._box_source = "manual"
        self._selection_coords = None
        self._selection_method = "bounds"
        self._previous_mouse_modes = None
        self._mouse_interaction_active = False
        self._last_padding_value = 4.0
        self._last_selection_method = "bounds"
        self._build_ui()
        # Reuse an existing scene box if the user closes and reopens the tool.
        # GUI startup/show/hide is not itself an undoable box edit.
        from .undo_support import find_box_model
        existing_box = find_box_model(session)
        if existing_box is not None:
            self.box = existing_box
            existing_box.set_tool(self)
            self._box_source = "manual"
            self.sync_from_model()
        else:
            self.create_box(record_undo=False)
        self._last_padding_value = float(self.padding.value())
        self._last_selection_method = self._selection_method

    def _build_ui(self):
        parent = self.tool_window.ui_area
        parent.setMinimumWidth(250)
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        title = QLabel("AutoDock Vina Search Space")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        outer.addWidget(title)
        note = QLabel("Native Vina center_* / size_* values in Å. Numeric fields wrap automatically.")
        note.setWordWrap(True)
        outer.addWidget(note)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_content = QWidget()
        self._scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll.setWidget(self._scroll_content)
        outer.addWidget(scroll, 1)

        content_layout = QVBoxLayout(self._scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(7)

        grid_group = QGroupBox("Vina box")
        grid_layout = QVBoxLayout(grid_group)
        grid_layout.setContentsMargins(7, 7, 7, 7)
        field_flow = FlowLayout(hspacing=6, vspacing=6)
        grid_layout.addLayout(field_flow)

        self.fields = {}
        for name, label in (("cx", "Center X"), ("cy", "Center Y"), ("cz", "Center Z"),
                            ("sx", "Size X"), ("sy", "Size Y"), ("sz", "Size Z")):
            card = QWidget()
            card.setFixedWidth(146)
            lay = QVBoxLayout(card)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)
            lab = QLabel(label)
            spin = QDoubleSpinBox()
            spin.setDecimals(4)
            spin.setRange(-100000.0, 100000.0)
            spin.setSingleStep(0.1)
            spin.setMinimumWidth(108)
            spin.setMaximumWidth(120)
            spin.valueChanged.connect(self._field_changed)
            lay.addWidget(lab)
            lay.addWidget(spin)
            field_flow.addWidget(card)
            self.fields[name] = spin

        # IMPORTANT: parent the Vina box group into the scroll area's layout.
        # Without this, Qt owns neither the group nor the field widgets after this
        # method returns, so the QDoubleSpinBox C++ objects can be deleted while
        # self.fields still holds Python wrappers to them. That caused the
        # "wrapped C/C++ object ... has been deleted" errors and hid the manual
        # center/size panel in v1.7.
        content_layout.addWidget(grid_group)

        selection_group = QGroupBox("From selection")
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(7, 7, 7, 7)
        selection_layout.setSpacing(5)

        selection_layout.addWidget(QLabel("Box calculation method"))
        self.selection_method_combo = QComboBox()
        self.selection_method_combo.addItem("Selection bounds + padding (recommended)", "bounds")
        self.selection_method_combo.addItem("Vina ligand-centroid method (ligands only)", "vina")
        self.selection_method_combo.setToolTip(
            "Recommended: use the selected atoms' minimum and maximum coordinates, "
            "then add padding to every side. The Vina ligand-centroid method is for "
            "reproducing Vina's ligand-derived box convention and is not recommended "
            "for selecting receptor pocket residues."
        )
        self.selection_method_combo.currentIndexChanged.connect(self._selection_method_changed)
        selection_layout.addWidget(self.selection_method_combo)

        self.selection_method_note = QLabel("")
        self.selection_method_note.setWordWrap(True)
        selection_layout.addWidget(self.selection_method_note)

        self.padding = QDoubleSpinBox()
        self.padding.setDecimals(2)
        self.padding.setRange(0.0, 50.0)
        self.padding.setSingleStep(0.25)
        self.padding.setValue(4.0)
        self.padding.setMinimumWidth(105)
        self.padding.valueChanged.connect(self._padding_changed)
        padding_row = QHBoxLayout()
        padding_row.addWidget(QLabel("Padding per side (Å)"))
        padding_row.addWidget(self.padding)
        padding_row.addStretch(1)
        selection_layout.addLayout(padding_row)

        selection_button = QPushButton("Create box from selection")
        selection_button.clicked.connect(self.from_selection)
        selection_layout.addWidget(selection_button)
        content_layout.addWidget(selection_group)
        self._update_selection_method_note()

        mouse_group = QGroupBox("Mouse interaction")
        mouse_layout = QVBoxLayout(mouse_group)
        mouse_layout.setContentsMargins(7, 7, 7, 7)
        self.mouse_interaction_cb = QCheckBox("Enable mouse move / resize")
        self.mouse_interaction_cb.setToolTip(
            "When enabled, left-drag moves the box and right-drag resizes the face "
            "intersected by the cursor. Normal left/right mouse bindings are temporarily "
            "replaced until this option is unchecked. Uncheck it to restore your previous modes."
        )
        self.mouse_interaction_cb.toggled.connect(self._mouse_interaction_toggled)
        mouse_layout.addWidget(self.mouse_interaction_cb)
        mouse_note = QLabel("Left-drag: move box. Right-drag: resize the face under the cursor. "
                            "Mouse interaction temporarily takes over those two buttons.")
        mouse_note.setWordWrap(True)
        mouse_layout.addWidget(mouse_note)
        content_layout.addWidget(mouse_group)

        options = QGroupBox("Display options")
        opt_layout = QVBoxLayout(options)
        opt_layout.setContentsMargins(7, 7, 7, 7)
        opt_flow = FlowLayout(hspacing=6, vspacing=4)
        opt_layout.addLayout(opt_flow)
        self.spacing = QDoubleSpinBox()
        self.spacing.setDecimals(4)
        self.spacing.setRange(0.001, 10.0)
        self.spacing.setSingleStep(0.025)
        self.spacing.setValue(DEFAULT_SPACING)
        self.spacing.setMinimumWidth(105)
        self.spacing.valueChanged.connect(self._option_changed)
        s_card = QWidget(); s_card.setFixedWidth(146)
        sl = QVBoxLayout(s_card); sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(QLabel("Map spacing")); sl.addWidget(self.spacing)
        opt_flow.addWidget(s_card)

        self.show_internal = QCheckBox("Show Vina rounded map extent")
        self.show_internal.setToolTip("Reference-only outline showing size rounded to Vina's map spacing. It does not change size_* exported to Vina.")
        self.show_internal.toggled.connect(self._internal_toggled)
        opt_flow.addWidget(self.show_internal)

        self.draw_on_top_cb = QCheckBox("Draw box on top (show edges through structure)")
        self.draw_on_top_cb.setToolTip(
            "Off: the receptor and other opaque scene objects occlude box faces/edges normally. "
            "On: box geometry is drawn on top, so hidden edges remain visible through the structure."
        )
        self.draw_on_top_cb.setChecked(False)
        self.draw_on_top_cb.toggled.connect(self._draw_on_top_toggled)
        opt_flow.addWidget(self.draw_on_top_cb)

        color_button = QPushButton("Box color…")
        color_button.clicked.connect(self.choose_color)
        opt_flow.addWidget(color_button)

        content_layout.addWidget(options)

        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        action_layout.setContentsMargins(7, 7, 7, 7)
        action_flow = FlowLayout(hspacing=6, vspacing=6)
        action_layout.addLayout(action_flow)
        buttons = [
            ("New box", self.create_box),
            ("View box", self.view_box),
            ("Copy Vina config", self.copy_config),
            ("Check selection", self.check_selection),
            ("Clear", self.clear_box),
        ]
        for text, fn in buttons:
            b = QPushButton(text)
            b.setMinimumWidth(120)
            b.clicked.connect(fn)
            action_flow.addWidget(b)
        content_layout.addWidget(action_group)

        bounds_group = QGroupBox("Exact box bounds")
        bounds_layout = QFormLayout(bounds_group)
        self.bounds_labels = {}
        for axis in "XYZ":
            lab = QLabel("—")
            self.bounds_labels[axis] = lab
            bounds_layout.addRow(f"{axis} min / max", lab)
        content_layout.addWidget(bounds_group)

        self.info = QLabel("")
        self.info.setWordWrap(True)
        content_layout.addWidget(self.info)
        content_layout.addStretch(1)
        self.tool_window.manage(placement="side")

    def display(self, shown=True):
        self.tool_window.shown = shown

    def create_box(self, *args, record_undo=True):
        from .undo_support import capture_state, record_state_change
        before = capture_state(self.session, tool=self) if record_undo else None
        center = (self.fields["cx"].value(), self.fields["cy"].value(), self.fields["cz"].value())
        size = (max(0.1, self.fields["sx"].value()), max(0.1, self.fields["sy"].value()), max(0.1, self.fields["sz"].value()))
        self._box_source = "manual"
        self._selection_coords = None
        if self.box is None or getattr(self.box, "deleted", False):
            self.box = VinaBoxModel(self.session, center, size)
            self.box.set_tool(self)
            self.box.set_draw_on_top(self.draw_on_top_cb.isChecked())
            self.session.models.add([self.box])
        else:
            self.box.set_box(center, size)
        self.sync_from_model()
        if record_undo:
            after = capture_state(self.session, tool=self)
            record_state_change(self.session, before, after, "Set Vina box")

    def set_box_from_cli(self, center, size, spacing):
        from .undo_support import capture_state, record_state_change
        before = capture_state(self.session, tool=self)
        self.spacing.setValue(spacing)
        self._box_source = "manual"
        self._selection_coords = None
        if self.box is None or getattr(self.box, "deleted", False):
            self.box = VinaBoxModel(self.session, center, size)
            self.box.set_tool(self)
            self.box.set_draw_on_top(self.draw_on_top_cb.isChecked())
            self.session.models.add([self.box])
        else:
            self.box.set_box(center, size)
        self.sync_from_model()
        after = capture_state(self.session, tool=self)
        record_state_change(self.session, before, after, "Set Vina box")

    def _field_changed(self, *args):
        if self._updating or self.box is None:
            return
        from .undo_support import capture_state, record_state_change
        before = capture_state(self.session, tool=self)
        self._box_source = "manual"
        self._selection_coords = None
        center = (self.fields["cx"].value(), self.fields["cy"].value(), self.fields["cz"].value())
        size = (max(0.1, self.fields["sx"].value()), max(0.1, self.fields["sy"].value()), max(0.1, self.fields["sz"].value()))
        self.box.set_box(center, size)
        self.sync_from_model()
        after = capture_state(self.session, tool=self)
        record_state_change(self.session, before, after, "Edit Vina box", merge_key="manual-box-edit")

    def _option_changed(self, *args):
        if self.box:
            self.update_status()

    def _padding_changed(self, *args):
        if self._updating:
            return
        current_padding = float(self.padding.value())
        if (self._selection_coords is None or self.box is None
                or self._box_source not in ("selection_bounds", "selection_vina")):
            self._last_padding_value = current_padding
            self.update_status()
            return
        from .undo_support import capture_state
        before = capture_state(self.session, tool=self, overrides={"padding": self._last_padding_value})
        self._apply_selection_box(
            self._selection_coords, self._selection_method, current_padding,
            before_state=before, undo_name="Adjust selection box padding",
            merge_key="selection-box-edit")
        self._last_padding_value = current_padding

    def _selection_method_changed(self, *args):
        if self._updating or not hasattr(self, "selection_method_combo"):
            return
        method = self.selection_method_combo.currentData()
        if method not in ("bounds", "vina"):
            return
        previous_method = self._selection_method
        if method == previous_method:
            self._last_selection_method = method
            return
        from .undo_support import capture_state
        before = capture_state(self.session, tool=self, overrides={"selection_method": previous_method})
        self._selection_method = method
        self._update_selection_method_note()
        if (self._selection_coords is not None and self.box is not None
                and self._box_source in ("selection_bounds", "selection_vina")):
            self._apply_selection_box(
                self._selection_coords, method, self.padding.value(),
                before_state=before, undo_name="Change selection-box method",
                merge_key="selection-box-edit")
        elif self.box is not None:
            self.update_status()
        self._last_selection_method = method

    def _update_selection_method_note(self):
        if not hasattr(self, "selection_method_note"):
            return
        method = self.selection_method_combo.currentData()
        if method == "bounds":
            self.selection_method_note.setText(
                "Recommended for receptor pockets and arbitrary selections: find the "
                "minimum/maximum coordinates on each axis, then add padding to both sides. "
                "The result directly encloses the selected atoms plus the requested margin."
            )
        else:
            self.selection_method_note.setText(
                "Vina ligand-style calculation: center on the selected atoms' coordinate "
                "mean, size from the furthest excursion on each axis, and round dimensions "
                "up to whole Å. Use for ligand-style compatibility checks; not recommended "
                "for defining a receptor-residue pocket box."
            )

    @staticmethod
    def _selection_box_values(coords, method, padding):
        if method == "bounds":
            return selection_bounds_box(coords, padding)
        if method == "vina":
            return vina_ligand_box(coords, padding)
        raise ValueError(f"Unknown selection box method: {method}")

    def _apply_selection_box(self, coords, method, padding, before_state=None,
                             undo_name="Create box from selection", merge_key=None):
        from .undo_support import capture_state, record_state_change
        if before_state is None:
            before_state = capture_state(self.session, tool=self)
        center, size = self._selection_box_values(coords, method, padding)
        self._selection_coords = np.asarray(coords, dtype=float).copy()
        self._selection_method = method
        self._box_source = "selection_bounds" if method == "bounds" else "selection_vina"
        if self.box is None or getattr(self.box, "deleted", False):
            self.box = VinaBoxModel(self.session, center, size)
            self.box.set_tool(self)
            self.box.set_draw_on_top(self.draw_on_top_cb.isChecked())
            self.session.models.add([self.box])
        else:
            self.box.set_box(center, size)
        self._last_selection_method = method
        self._last_padding_value = float(padding)
        self.sync_from_model()
        after_state = capture_state(self.session, tool=self)
        record_state_change(self.session, before_state, after_state, undo_name, merge_key=merge_key)

    def from_selection(self, *args, method=None, padding=None):
        atoms = selected_atoms(self.session)
        if len(atoms) == 0:
            message = "No atoms selected. Select the ligand or pocket atoms first."
            self.info.setText(message)
            return message

        if method is None:
            method = self.selection_method_combo.currentData()
        if method not in ("bounds", "vina"):
            raise ValueError("Selection method must be 'bounds' or 'vina'")

        before_state = None
        from .undo_support import capture_state
        before_state = capture_state(self.session, tool=self)
        if padding is not None:
            padding = float(padding)
            if not 0.0 <= padding <= 50.0:
                raise ValueError("Padding must be between 0 and 50 Å")
            self.padding.blockSignals(True)
            self.padding.setValue(padding)
            self.padding.blockSignals(False)
        padding = self.padding.value()

        coords = np.asarray(atoms.scene_coords, dtype=float).copy()
        self._selection_method = method
        index = self.selection_method_combo.findData(method)
        self.selection_method_combo.blockSignals(True)
        if index >= 0:
            self.selection_method_combo.setCurrentIndex(index)
        self.selection_method_combo.blockSignals(False)
        self._update_selection_method_note()

        self._apply_selection_box(coords, method, padding, before_state=before_state,
                                  undo_name="Create box from selection")
        self._last_padding_value = float(padding)
        self._last_selection_method = method
        method_label = (
            "selection bounds + padding (recommended)"
            if method == "bounds" else "Vina ligand-centroid method (ligand-style)"
        )
        message = f"Selection box created using {method_label}: {len(atoms)} atoms, {padding:.2f} Å padding per side."
        self.info.setText(message + "\n" + self.info.text())
        return message

    def _draw_on_top_toggled(self, checked):
        if self._updating or self.box is None:
            return
        from .undo_support import capture_state, record_state_change
        before = capture_state(self.session, tool=self, overrides={"draw_on_top": self.box.draw_on_top})
        self.box.set_draw_on_top(checked)
        after = capture_state(self.session, tool=self)
        record_state_change(self.session, before, after, "Toggle box edge visibility")
        self.update_status()

    def _mouse_interaction_toggled(self, checked):
        """Temporarily bind left/right mouse buttons to box move/resize modes."""
        if not self.session.ui.is_gui:
            return
        mm = self.session.ui.mouse_modes
        if checked:
            if self._mouse_interaction_active:
                return
            from .mousemode import register_mousemodes, MOVE_MODE, RESIZE_MODE
            register_mousemodes(self.session)
            move_mode = mm.named_mode(MOVE_MODE)
            resize_mode = mm.named_mode(RESIZE_MODE)
            if move_mode is None or resize_mode is None:
                self.mouse_interaction_cb.blockSignals(True)
                self.mouse_interaction_cb.setChecked(False)
                self.mouse_interaction_cb.blockSignals(False)
                self.session.logger.warning("VinaGridBox could not register mouse interaction modes.")
                return
            self._previous_mouse_modes = (mm.mode("left", []), mm.mode("right", []))
            mm.bind_mouse_mode(mouse_button="left", mode=move_mode)
            mm.bind_mouse_mode(mouse_button="right", mode=resize_mode)
            self._mouse_interaction_active = True
            self.info.setText("Mouse interaction enabled: left-drag moves the box; right-drag resizes a face. "
                              "Normal left/right mouse actions are temporarily replaced.")
        else:
            previous = self._previous_mouse_modes
            self._previous_mouse_modes = None
            self._mouse_interaction_active = False
            if previous is not None:
                try:
                    if previous[0] is not None:
                        mm.bind_mouse_mode(mouse_button="left", mode=previous[0])
                    if previous[1] is not None:
                        mm.bind_mouse_mode(mouse_button="right", mode=previous[1])
                except Exception as e:
                    self.session.logger.warning("Could not fully restore previous mouse bindings: %s" % e)
            if self.box is not None:
                self.update_status()

    def _internal_toggled(self, checked):
        if self._updating or self.box is None:
            return
        from .undo_support import capture_state, record_state_change
        before = capture_state(self.session, tool=self, overrides={"show_internal": self.box._internal_visible})
        self.box.set_internal_visible(checked)
        after = capture_state(self.session, tool=self)
        record_state_change(self.session, before, after, "Toggle rounded map extent")
        self.sync_from_model()

    def mark_manual_edit(self):
        self._box_source = "manual"
        self._selection_coords = None

    def sync_from_model(self):
        if not self.box:
            return
        self._updating = True
        c = self.box.center; s = self.box.size
        for key, val in (("cx", c[0]), ("cy", c[1]), ("cz", c[2]), ("sx", s[0]), ("sy", s[1]), ("sz", s[2])):
            self.fields[key].setValue(float(val))
        self._updating = False
        self.update_status()

    def update_status(self):
        if not self.box:
            return
        lo, hi = self.box.box_bounds()
        for axis, idx in zip("XYZ", range(3)):
            self.bounds_labels[axis].setText(f"{lo[idx]:.4f}  →  {hi[idx]:.4f} Å")
        vox, span = vina_map_info(self.box.size, self.spacing.value(), False)
        internal = "ON" if self.show_internal.isChecked() else "OFF"
        if self._box_source == "selection_bounds":
            source = "selection bounds + padding (recommended)"
        elif self._box_source == "selection_vina":
            source = "Vina ligand-centroid method (ligand-style; not recommended for receptor residues)"
        else:
            source = "manual / edited"
        self.info.setText(
            f"Vina box: {self.box.size[0]:.4f} × {self.box.size[1]:.4f} × {self.box.size[2]:.4f} Å\n"
            f"Rounded map extent (spacing {self.spacing.value():.4f} Å): {span[0]:.4f} × {span[1]:.4f} × {span[2]:.4f} Å; voxels {vox[0]} × {vox[1]} × {vox[2]}\n"
            f"Map extent display: {internal}. Draw on top: {self.box.draw_on_top}. Box source: {source}."
        )

    def report(self):
        if not self.box:
            return
        self.session.logger.info(vina_config_text(self.box.center, self.box.size, self.spacing.value(), False))

    def view_box(self):
        if self.box is None:
            return
        run(self.session, f"view #{self.box.id[0]}")

    def clear_box(self):
        if self.box is None:
            self.info.setText("No Vina box.")
            return
        from .undo_support import capture_state, record_state_change
        before = capture_state(self.session, tool=self)
        old_box = self.box
        self.box = None
        self._selection_coords = None
        self._box_source = "manual"
        old_box.set_tool(None)
        old_box.delete()
        after = capture_state(self.session, tool=self)
        record_state_change(self.session, before, after, "Clear Vina box")
        for label in self.bounds_labels.values():
            label.setText("—")
        self.info.setText("No Vina box.")

    def copy_config(self):
        if self.box is None:
            return
        text = vina_config_text(self.box.center, self.box.size, self.spacing.value(), False)
        self.session.ui.clipboard().setText(text)
        self.info.setText("Vina configuration copied to the system clipboard.")

    def check_selection(self):
        atoms = selected_atoms(self.session)
        if len(atoms) == 0:
            self.info.setText("No atoms selected.")
            return
        if self.box is None:
            self.info.setText("Selection check: no Vina box exists. Create a box first.")
            return
        lo, hi = self.box.box_bounds()
        xyz = np.asarray(atoms.scene_coords, dtype=float)
        lo_arr = np.asarray(lo, dtype=float)
        hi_arr = np.asarray(hi, dtype=float)
        inside = np.all((xyz >= lo_arr) & (xyz <= hi_arr), axis=1)
        outside = int((~inside).sum())
        if outside == 0:
            self.info.setText(f"Selection check: all {len(atoms)} selected atoms are inside the Vina box.")
        else:
            delta = np.maximum(np.maximum(lo_arr - xyz, xyz - hi_arr), 0.0)
            max_overhang = float(delta.max())
            self.info.setText(f"Selection check: {inside.sum()}/{len(atoms)} atoms inside; {outside} outside; maximum overhang {max_overhang:.2f} Å.")

    def choose_color(self):
        if self.box is None:
            return
        from Qt.QtGui import QColor
        from .undo_support import capture_state, record_state_change
        rgb = tuple(self.box._visual_rgb) if self.box else DEFAULT_RGB
        initial = QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]))
        chosen = QColorDialog.getColor(initial, self.tool_window.ui_area, "Vina box color")
        if not chosen.isValid() or self.box is None:
            return
        before = capture_state(self.session, tool=self)
        self.box.set_visual_rgb((chosen.red(), chosen.green(), chosen.blue()))
        after = capture_state(self.session, tool=self)
        record_state_change(self.session, before, after, "Change Vina box color")
        self.update_status()
    def delete(self):
        # Restore the user's prior mouse bindings when closing the tool.
        if getattr(self, "mouse_interaction_cb", None) is not None and self.mouse_interaction_cb.isChecked():
            self.mouse_interaction_cb.setChecked(False)
        # The 3D model can remain in the scene while the GUI is closed. Do not
        # leave it holding a reference to a dead tool instance.
        if self.box is not None and getattr(self.box, "_tool", None) is self:
            self.box.set_tool(None)
        super().delete()

    def take_snapshot(self, session, flags):
        return {}

    @classmethod
    def restore_snapshot(cls, session, data):
        return cls(session, "Vina Grid Box")
