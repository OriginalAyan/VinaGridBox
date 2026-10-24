# Changelog

This changelog lists published releases. Intermediate development/test builds between v1.9.1 and v2.0.0 were not separate public releases; their changes are consolidated in the v2.0.0 entry below.

## 2.0.0 — first public v2.x release after v1.9.1

### Added
- Interactive box movement and face resizing when Mouse interaction is enabled: left-drag moves the box; right-drag resizes the selected face while keeping the opposite face fixed.
- A display toggle that switches between normal scene-depth occlusion and drawing box geometry on top of the molecular scene.
- ChimeraX undo/redo support for box creation/removal, numeric geometry edits, CLI updates, selection-derived box generation, padding/method changes, completed mouse gestures, color changes and display options. GUI show/hide is intentionally not undoable.
- A recommended selection-bounds-plus-padding method for receptor-pocket selections, alongside a ligand-centroid method for comparison with Vina's ligand-derived box convention.
- More complete command support for `vinabox nativepdbqt`, which restores the preferred native `.pdbqt` reader when needed.

### Changed
- PDBQT opening uses ChimeraX's built-in AutoDock PDBQT reader. VinaGridBox does not register a custom PDBQT provider or add a separate PDBQT file chooser. Multi-pose docking results can use the built-in ViewDock workflow.
- Improved the native `.pdbqt` format preference initialization to handle ordinary file opening, Explorer-open and drag-and-drop.
- Improved the responsive GUI, exact-bound reporting, selection containment checks, configuration copying and grid-span reference display.

### Licensing and third-party notices
- The v2.x release is licensed under LGPL-2.1-only because the mouse interaction implementation includes adapted code from an LGPL-licensed ChimeraX bundle. See `LICENSE.txt` and `THIRD_PARTY_NOTICES.md`.
- Previous public releases through v1.9.1 remain under their original MIT license; this release does not retroactively change their terms.

## 1.9.1 — GUI startup command fix

- Fixed `vinabox showgui` and commands that need to create the GUI before first use.
- Used ChimeraX's supported `tools.get_singleton()` API rather than a nonexistent UI method.
- Routed Tools-menu and CLI startup through the same singleton instance to avoid duplicate windows.
- No changes to box geometry or the two selection calculation methods.

## 1.9 — shorter CLI actions

- Added `vinabox bounds padding 4` and `vinabox centroid padding 4`.
- Added `vinabox showgui` and `vinabox hidegui`, with `guishow` and `guihide` synonyms.
- Retained previous selection and GUI action names as compatibility aliases.
- Updated user documentation and CLI examples.

## 1.8

- Fixed GUI layout ownership for the manual center/size field group.
- Restored Center X/Y/Z and Size X/Y/Z controls.
- Fixed Qt widget-lifetime errors during startup and selection-derived box updates.

## 1.7 — selection methods and Toolshed preparation

- Added selection bounds plus padding for receptor pockets and arbitrary selected atom groups.
- Added Vina ligand-centroid calculation as a second option for ligand-oriented comparison.
- Documented both methods, padding behavior, and their distinct purposes.
- Used Binding Analysis as the tool category following ChimeraX developer feedback.

## 1.6 — stable release metadata and documentation

- Expanded user documentation and Toolshed metadata.
- Added maintainer contact details, citation guidance, and development acknowledgement.
- Documented exact box bounds, padding, selection checks, and rounded map extent.

