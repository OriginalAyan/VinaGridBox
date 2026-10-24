## Source structure

The bundle root contains `bundle_info.xml` and `src/`. Use UCSF ChimeraX's own bundle-builder commands from ChimeraX 1.12 or another supported ChimeraX development installation.

## Local development test

1. Extract or clone the repository to a short, stable path.
2. Run a clean build and install the source bundle:

       devel clean H:/path/to/ChimeraX-VinaGridBox
       devel install H:/path/to/ChimeraX-VinaGridBox

3. Restart ChimeraX and test the GUI at Tools → Binding Analysis → Vina Grid Box.
4. Test manual numeric entry, `vinabox set`, `vinabox bounds`, `vinabox centroid`, `vinabox report`, `vinabox clear`, GUI show/hide, box color/display toggles, undo/redo, and mouse move/resize. Confirm GUI show/hide is not undoable.
5. Test normal `.pdbqt` opening using ChimeraX's native AutoDock PDBQT reader, including a multi-pose docking output (ViewDock), a single receptor PDBQT, drag-and-drop, and opening a file from Windows Explorer. VinaGridBox intentionally does not register a separate PDBQT provider or expose a separate PDBQT-opening GUI action. If the native reader preference needs resetting, test `vinabox nativepdbqt`.
6. Verify that box coordinates use the same coordinate frame as files supplied to Vina.
7. Run the standalone tests from a Python environment that can import pytest:

       python -m pytest -q tests

## Build the distributable wheel

Run inside ChimeraX:

       devel clean H:/path/to/ChimeraX-VinaGridBox
       devel build H:/path/to/ChimeraX-VinaGridBox

Use the newly generated wheel under `dist/`. Do not manually edit the wheel's `METADATA`.

Install-test the exact wheel using:

       toolshed install H:/path/to/dist/ChimeraX_VinaGridBox-2.0.0-py3-none-any.whl

Use the exact filename emitted by the build. Check version/category/license metadata, GUI launch, commands, undo/redo, native `.pdbqt` opening, and format preference behavior.

