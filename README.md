# ChimeraX Vina Grid Box (VinaGridBox)

**Release:** 2.0.0  
**Author and maintainer:** Ayan Bhowmik  
**Contact:** ayan.bhowmik.bd@gmail.com  
**Target tested by maintainer:** UCSF ChimeraX 1.12 / Python 3.11  
**ChimeraX command:** `vinabox`  
**License for v2.x:** GNU Lesser General Public License, version 2.1 only (LGPL-2.1-only)

VinaGridBox is a ChimeraX bundle for defining, visualizing and checking AutoDock Vina search spaces directly on molecular structures. The first public v2.x release consolidates development after the previous public release, v1.9.1. Intermediate v2.x development builds were not separate public releases.

## Features

- Visualize Vina's `center_x`, `center_y`, `center_z`, `size_x`, `size_y`, and `size_z` as a 3D box.
- Edit center and size numerically in a responsive, vertically scrollable GUI.
- Generate a box from the current selection using either selection bounds plus padding (recommended for receptor pockets) or Vina's ligand-centroid convention (for ligand-oriented comparison).
- Inspect exact minimum/maximum coordinates and check whether selected atoms fall inside the box.
- View Vina's rounded internal map span as a separate reference outline.
- Change box color and choose between normal scene-depth occlusion and drawing the box on top of the molecular scene.
- Move the box by left-dragging and resize a face by right-dragging when mouse interaction is enabled.
- Undo/redo box creation, edits, selection-derived calculations, completed mouse gestures, color/display changes and clearing.
- Open PDBQT files inside ChimeraX using native AutoDock PDBQT reader for normal `.pdbqt` opening, including ViewDock for multi-pose docking results. VinaGridBox does not register a duplicate PDBQT reader.
- Copy Vina-ready configuration values and use the compact `vinabox` command-line interface.

VinaGridBox is a search-space visualization and editing tool. It does not run docking or prepare receptor/ligand PDBQT files.

## Installation

### From the ChimeraX Toolshed

Install VinaGridBox through ChimeraX's in-application Toolshed. The listing and bundle metadata describe the current published release.

### From a downloaded wheel

If the wheel was downloaded using a web browser, open ChimeraX and run `toolshed install` with the full path to the downloaded file. Example for the 2.0.0 release on Windows:

    toolshed install "C:/Users/YourName/Downloads/ChimeraX_VinaGridBox-2.0.0-py3-none-any.whl"

Use the exact filename produced by the build; capitalization can vary. Restart ChimeraX if the release notes or installation process instruct you to do so.

### From source during development

Extract the source repository. In ChimeraX's command line, use the directory that contains `bundle_info.xml` and `src/`:

    devel clean H:/path/to/ChimeraX-VinaGridBox
    devel install H:/path/to/ChimeraX-VinaGridBox

To build a wheel for distribution, use `devel build` instead of `devel install`:

    devel clean H:/path/to/ChimeraX-VinaGridBox
    devel build H:/path/to/ChimeraX-VinaGridBox

See [BUILDING_FOR_TOOLSHED.md](BUILDING_FOR_TOOLSHED.md) for the release checklist, [TOOLSHED_DETAILS.md](TOOLSHED_DETAILS.md) for the listing text, and [GITHUB_RELEASE_NOTES.md](GITHUB_RELEASE_NOTES.md) / [TOOLSHED_RELEASE_NOTES.txt](TOOLSHED_RELEASE_NOTES.txt) for release announcements. Do not manually edit generated wheel metadata. Keep `LICENSE.txt` and `THIRD_PARTY_NOTICES.md` in the source repository and distribution.

## Open the GUI

Open **Tools → Binding Analysis → Vina Grid Box**, or enter:

    vinabox showgui

Hide the panel without removing the box:

    vinabox hidegui

The GUI reflows numeric fields at narrow widths and scrolls vertically.

## Manual Vina box entry

The six numeric fields are the Vina center and dimensions, in Angstroms (Å):

- **Center X / Y / Z** correspond to `center_x`, `center_y`, and `center_z`.
- **Size X / Y / Z** correspond to `size_x`, `size_y`, and `size_z`.

Use **New box** to create or update the box from the current values. Each axis's bounds are calculated as:

    minimum = center - size / 2
    maximum = center + size / 2

The **Exact box bounds** section displays those bounds so they can be checked independently of the six input fields. The visible geometry uses the requested Vina center/size values directly.

## Create a box from the current selection

Select the atoms in ChimeraX, choose a calculation method, set **Padding per side**, and click **Create box from selection**. The methods operate on the current atomic selection; they do not accept a residue list directly.

### Selection bounds + padding (recommended)

CLI:

    vinabox bounds padding 4

For each axis, the method finds the selected atoms' minimum and maximum coordinates and expands each side by the padding `p`:

    minimum = min(q_i) - p
    maximum = max(q_i) + p
    center = (minimum + maximum) / 2
    size = maximum - minimum

This forms an axis-aligned bounding box containing every selected atom with the requested padding on all six faces. Dimensions are not rounded to whole Angstroms or aligned to grid spacing. This method is recommended for receptor-pocket residues and arbitrary selected atom groups.

### Vina ligand-centroid method

CLI:

    vinabox centroid padding 4

This method follows Vina's ligand-derived box convention. It calculates the arithmetic mean of selected coordinates, finds the largest absolute excursion from that center on each axis, adds the padding and rounds each dimension upward to an integer Angstrom:

    center = mean(atom coordinates)
    size_axis = ceil(2 * (max(abs(q_i - center_axis)) + padding))

This method is intended for ligand atom selections and comparison with Vina's ligand-derived convention. It is not recommended for receptor-pocket selections, where a bounds-centered padded box more directly expresses the goal of enclosing the selected atoms with fixed padding.

The maintainer has not found a clear published explanation in the Vina source/documentation reviewed for why Vina's ligand-centroid convention was preferred over a minimum/maximum-centred padded box. The recommendation above is specific to receptor-pocket selection, not a claim that the bounds method is universally superior for all workflows.

Padding defaults to 4 Å when omitted. Both methods create or update the box and synchronize the GUI fields. Changing padding or switching methods recalculates a selection-derived box from saved selected coordinates. Editing center/size manually detaches the box from the saved selection so later padding changes do not overwrite manual values.

Examples:

    vinabox bounds
    vinabox centroid padding 3.5

## Check selection

**Check selection** is a sanity check and does not modify the box. It reports how many currently selected atoms are inside and outside the box, and the maximum Cartesian overhang in Å if any are outside. If no box exists, the tool asks you to create one first. This is useful for confirming that a ligand is contained by the proposed search space before docking.

## Vina rounded map extent

Vina discretizes requested dimensions into a grid. With a spacing of 0.375 Å, a reference calculation is conceptually:

    n = ceil(size / spacing)
    grid_span = n * spacing

For example, a requested size of 24.390 Å gives `ceil(24.390 / 0.375) = 66`, corresponding to a 24.750 Å grid span. The **Show Vina rounded map extent** option displays that span as a separate reference outline. It does not change the `size_*` values exported to Vina. The GUI's spacing field is a visualization/reference setting, not a separate Vina configuration parameter.

## Mouse interaction and display

Enable **Mouse interaction** to use:

- **Left-drag:** move the whole box.
- **Right-drag:** resize the box face under the cursor while keeping the opposite face fixed.

While this mode is enabled, it temporarily takes over the normal left/right mouse bindings. Uncheck it to restore the previous bindings. The completed move/resize gesture is one undoable action.

By default, the box uses normal scene-depth occlusion: opaque molecular geometry hides box edges behind it. Enable **Draw box on top (show edges through structure)** to draw the box over the scene so all edges remain visible. This only changes visualization.

**Box color…** changes the visualization color, not Vina calculations. **View box** frames the current box. **Clear** removes the 3D box without modifying receptor or ligand coordinates.

## Native PDBQT opening

ChimeraX already includes the native **AutoDock PDBQT** reader used by the built-in ViewDock workflow. VinaGridBox does not register a separate PDBQT reader or provide a separate PDBQT file chooser. Its initialization makes ChimeraX's native PDBQT format the preferred default for `.pdbqt` files and clears a competing legacy default for that suffix. Consequently, normal ChimeraX file opening—including opening from Windows Explorer and drag-and-drop—can use the native reader. Multi-pose docking results normally open in ViewDock; a single receptor/ligand PDBQT can open as a molecular model.

If the saved format preference needs to be repaired manually, run:

    vinabox nativepdbqt

To open one file explicitly through ChimeraX's built-in reader, the normal ChimeraX command is:

    open "D:/docking/results.pdbqt" format pdbqt

This is a native ChimeraX operation; there is no VinaGridBox-specific PDBQT-opening button.

## Command-line reference

Create or update a box:

    vinabox set center 0,0,0 size 20,20,20

Create a box from the current selection:

    vinabox bounds padding 4
    vinabox centroid padding 4

Repair the preferred native PDBQT format for `.pdbqt`:

    vinabox nativepdbqt

Show/hide the GUI, report values, or remove the box:

    vinabox showgui
    vinabox hidegui
    vinabox report
    vinabox clear

For `set`, each 3D coordinate/dimension must be one comma-separated triple (for example, `center 0,0,0`), not three space-separated numbers. `showgui` and `hidegui` affect only the interface and do not enter the undo history. `clear` removes the 3D box but leaves the GUI open.

## Undo and redo

VinaGridBox integrates box changes with ChimeraX's undo/redo system. Undo/redo covers numeric center/size editing, `vinabox set`, selection-derived box creation, padding/method changes, each completed mouse move/resize gesture, box color changes (including color changes via the Models panel), display toggles, box creation, and clearing. Rapid numerical edits are coalesced where possible. GUI show/hide is intentionally not undoable.

## Coordinate-frame limitations

Selection-derived calculations use ChimeraX atom scene coordinates. Ensure that these match the coordinates in the receptor/ligand files supplied to Vina. If a structure has been translated or transformed in the ChimeraX scene without changing its saved atomic coordinates, verify the coordinate frame before exporting the search space.

VinaGridBox does not run AutoDock Vina, prepare receptor/ligand PDBQT files, choose a scoring function, or perform docking. It is a search-space definition, visualization, and pre-docking sanity-check tool.

## Source, license and acknowledgements

- Source repository: https://github.com/OriginalAyan/VinaGridBox
- Public Toolshed listing: https://cxtoolshed.rbvi.ucsf.edu/apps/chimeraxvinagridbox
- AutoDock Vina documentation/source: https://github.com/ccsb-scripps/AutoDock-Vina

VinaGridBox v2.x is distributed under LGPL-2.1-only because its mouse interaction implementation includes adapted code from another LGPL-licensed ChimeraX bundle. The source distribution includes `LICENSE.txt` and `THIRD_PARTY_NOTICES.md` with the required attribution. VinaGridBox releases through v1.9.1 remain under their previously published MIT terms; those older releases are not relicensed by this release.

Suggested citation: 
Bhowmik, A. (2026). *ChimeraX Vina Grid Box* (Version 2.0.0) [Computer software]. ChimeraX Toolshed. https://cxtoolshed.rbvi.ucsf.edu/apps/chimeraxvinagridbox

The bundle was developed and debugged with coding assistance from ChatGPT (OpenAI). The author is responsible for final review, testing, and release decisions.
