# Changelog

## 1.9.1 — GUI startup command fix

- Fix `vinabox showgui` and commands that need to create the GUI before first use.
- Use ChimeraX's supported `tools.get_singleton()` API instead of the nonexistent `session.ui.display_tool_window()` method.
- Route the Tools menu and CLI through the same singleton tool instance to avoid duplicate windows.
- No changes to box geometry or the two selection calculation methods.


## 1.9 — shorter CLI actions

- Added short selection actions: `vinabox bounds padding 4` and `vinabox centroid padding 4`.
- Added explicit GUI actions: `vinabox showgui` and `vinabox hidegui`.
- Added accepted synonyms `vinabox guishow` and `vinabox guihide`.
- Kept the previous long selection actions (`from-selection-bounds`, `from-selection-vina`) and GUI actions (`show`, `hide`) as backwards-compatible aliases.
- Updated the README and ChimeraX HTML help so new examples use the shorter, clearer command forms.
- No changes to box mathematics or GUI controls.

## 1.8

- Fixed a missing layout insertion for the manual Vina box field group.
- Restored the Center X/Y/Z and Size X/Y/Z controls in the GUI.
- Fixed the Qt widget lifetime issue that caused deleted QDoubleSpinBox errors during tool startup and selection-derived box updates.
- No box mathematics or CLI semantics changed from v1.7.

## 1.7 — selection methods and Toolshed preparation

- Added **Selection bounds + padding (recommended)** for selected receptor residues and arbitrary atom groups.
- Added **Vina ligand-centroid method** as an explicit second option for ligand-oriented compatibility checks.
- Added CLI actions `vinabox from-selection-bounds padding 4` and `vinabox from-selection-vina padding 4`.
- Padding changes and method changes recalculate an active selection-derived box.
- Updated GUI help, README, bundle description, and CLI reference to explain both calculations and their intended uses.
- Documented that the maintainer has not found a clear published rationale in the Vina source/documentation reviewed for choosing its centroid-based ligand box over a bounds-centered box; bounds is recommended here for receptor-pocket selection, not claimed universally superior.
- Kept the bundle under **Tools → Binding Analysis** as advised by ChimeraX developer Eric Pettersen.
- No docking execution or drag-resize was added.

## 1.6 pre-submission metadata adjustment

- Changed the bundle and tool menu category from General to Binding Analysis following ChimeraX developer feedback.
- Updated GUI navigation instructions. No box geometry or CLI implementation changes.

## 1.6 — stable release metadata/documentation refresh

- Expanded bundle description and user documentation for ChimeraX Toolshed publication.
- Added author and maintainer metadata for Ayan Bhowmik.
- Added MIT license metadata and license file.
- Added detailed GUI and CLI documentation.
- Added explicit explanation of selection padding, Check selection, and Vina rounded map extent.
- Added citation guidance and development acknowledgement.
- Documented the stable release limitation that experimental mouse drag-resize is excluded.
- No changes to the tested core box mathematics or `vinabox` CLI behavior.
