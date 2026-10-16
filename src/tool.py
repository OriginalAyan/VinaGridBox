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
        self._build_ui()
        self.create_box()

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

    def create_box(self):
        center = (self.fields["cx"].value(), self.fields["cy"].value(), self.fields["cz"].value())
        size = (max(0.1, self.fields["sx"].value()), max(0.1, self.fields["sy"].value()), max(0.1, self.fields["sz"].value()))
        self._box_source = "manual"
        self._selection_coords = None
        if self.box is None:
            self.box = VinaBoxModel(self.session, center, size)
            self.box.set_tool(self)
            self.session.models.add([self.box])
        else:
            self.box.set_box(center, size)
        self.sync_from_model()

    def set_box_from_cli(self, center, size, spacing):
        self.spacing.setValue(spacing)
        self._box_source = "manual"
        self._selection_coords = None
        if self.box is None:
            self.box = VinaBoxModel(self.session, center, size)
            self.box.set_tool(self)
            self.session.models.add([self.box])
        else:
            self.box.set_box(center, size)
        self.sync_from_model()

    def _field_changed(self, *args):
        if self._updating or self.box is None:
            return
        self._box_source = "manual"
        self._selection_coords = None
        center = (self.fields["cx"].value(), self.fields["cy"].value(), self.fields["cz"].value())
        size = (max(0.1, self.fields["sx"].value()), max(0.1, self.fields["sy"].value()), max(0.1, self.fields["sz"].value()))
        self.box.set_box(center, size)
        self.sync_from_model()

    def _option_changed(self, *args):
        if self.box:
            self.update_status()

    def _padding_changed(self, *args):
        if (self._selection_coords is None or self.box is None
                or self._box_source not in ("selection_bounds", "selection_vina")):
            self.update_status()
            return
        self._apply_selection_box(self._selection_coords, self._selection_method, self.padding.value())

    def _selection_method_changed(self, *args):
        if not hasattr(self, "selection_method_combo"):
            return
        method = self.selection_method_combo.currentData()
        if method not in ("bounds", "vina"):
            return
        self._selection_method = method
        self._update_selection_method_note()
        if (self._selection_coords is not None and self.box is not None
                and self._box_source in ("selection_bounds", "selection_vina")):
            self._apply_selection_box(self._selection_coords, method, self.padding.value())
        elif self.box is not None:
            self.update_status()

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

    def _apply_selection_box(self, coords, method, padding):
        center, size = self._selection_box_values(coords, method, padding)
        self._selection_method = method
        self._box_source = "selection_bounds" if method == "bounds" else "selection_vina"
        if self.box is None:
            self.box = VinaBoxModel(self.session, center, size)
            self.box.set_tool(self)
            self.session.models.add([self.box])
        else:
            self.box.set_box(center, size)
        self.sync_from_model()

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

        if padding is not None:
            padding = float(padding)
            if not 0.0 <= padding <= 50.0:
                raise ValueError("Padding must be between 0 and 50 Å")
            self.padding.blockSignals(True)
            self.padding.setValue(padding)
            self.padding.blockSignals(False)
        padding = self.padding.value()

        coords = np.asarray(atoms.scene_coords, dtype=float).copy()
        self._selection_coords = coords
        self._selection_method = method
        index = self.selection_method_combo.findData(method)
        self.selection_method_combo.blockSignals(True)
        if index >= 0:
            self.selection_method_combo.setCurrentIndex(index)
        self.selection_method_combo.blockSignals(False)
        self._update_selection_method_note()

        self._apply_selection_box(coords, method, padding)
        method_label = (
            "selection bounds + padding (recommended)"
            if method == "bounds" else "Vina ligand-centroid method (ligand-style)"
        )
        message = f"Selection box created using {method_label}: {len(atoms)} atoms, {padding:.2f} Å padding per side."
        self.info.setText(message + "\n" + self.info.text())
        return message

    def _internal_toggled(self, checked):
        if self.box:
            self.box.set_internal_visible(checked)
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
            f"Map extent display: {internal}. Box source: {source}."
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
        if self.box is not None:
            self.box.delete()
            self.box = None
        self._selection_coords = None
        self._box_source = "manual"
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
        from Qt.QtGui import QColor
        c = getattr(self.box, "overall_color", None) if self.box else None
        if c is None or c is False:
            c = (*DEFAULT_RGB, 255)
        initial = QColor(int(c[0]), int(c[1]), int(c[2]))
        chosen = QColorDialog.getColor(initial, self.tool_window.ui_area, "Vina box color")
        if not chosen.isValid() or self.box is None:
            return
        self.box._visual_rgb = (chosen.red(), chosen.green(), chosen.blue())
        self.box._rebuild()
    def take_snapshot(self, session, flags):
        return {}

    @classmethod
    def restore_snapshot(cls, session, data):
        return cls(session, "Vina Grid Box")
