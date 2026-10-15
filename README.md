# ChimeraX Vina Grid Box v1.9

**Author / maintainer:** Ayan Bhowmik  
**Contact:** ayan.bhowmik.bd@gmail.com  
**License:** MIT License  
**Target:** UCSF ChimeraX, developed and tested with ChimeraX 1.12 / Python 3.11  
**Command:** `vinabox`

## What this bundle is for

ChimeraX Vina Grid Box is a visualization and search-space editing tool for AutoDock Vina. It lets you place a Vina search box on a ChimeraX molecular scene using the same six values that Vina consumes:

```text
center_x center_y center_z
size_x   size_y   size_z
```

The purpose is to make the docking search space easy to inspect against the receptor and ligand before launching Vina. The extension does **not** perform docking and does not prepare PDBQT files.

The stable release uses numeric editing rather than interactive drag-resize. Experimental drag-resize controls were intentionally removed from the public release because the ChimeraX 1.12 mouse-mode behavior used during development was not reliable enough for a stable bundle.

## Vina box geometry

The displayed box is defined directly from the requested Vina center and size values. For each axis:

```text
minimum = center - size / 2
maximum = center + size / 2
```

For example:

```text
center_x = 10
size_x   = 20
```

means:

```text
x_min = 0
x_max = 20
```

The GUI shows these exact minimum/maximum coordinates in the **Exact box bounds** section so the rendered box can be checked independently from the six input fields.

Vina search-space dimensions are in Angstroms, not AutoDock4-style grid-point counts. The Vina source and documentation use the center and box size in Angstroms and derive internal voxel counts from the requested dimensions. See the Vina documentation/source: https://github.com/ccsb-scripps/AutoDock-Vina

## Installation

### From a published ChimeraX Toolshed release

After publication, install the bundle through ChimeraX's normal Toolshed interface. The Toolshed handles bundle dependencies and updates.

### From a wheel during testing

```text
toolshed install H:/path/to/ChimeraX_VinaGridBox-1.9-py3-none-any.whl
```

Use the exact filename produced by your ChimeraX build; capitalization may vary by packaging version.

### From source during development

With the bundle source directory containing `bundle_info.xml` and `src/`:

```text
devel install H:/path/to/ChimeraX-VinaGridBox
```

Do not manually edit `bundle_info.xml` unless you are intentionally developing the bundle metadata.

## Open the GUI

Open:

```text
Tools → Binding Analysis → Vina Grid Box
```

or use:

```text
vinabox showgui
```

The GUI is designed to remain usable at narrow widths. The center/size fields wrap across columns as the panel width changes, while the main content remains vertically scrollable.

## GUI: Vina box fields

The **Vina box** section contains six numeric inputs:

- **Center X / Y / Z** — Vina `center_x`, `center_y`, `center_z`, in Å.
- **Size X / Y / Z** — Vina `size_x`, `size_y`, `size_z`, in Å.

Use **New box** to create a box from the current values or to apply edited values to the current box.

Changing any center or size field directly updates the 3D box.

## GUI: From selection — two calculation methods

Select the atoms you want the box to cover, choose a method under **Box calculation method**, set **Padding per side**, and click **Create box from selection**. The same two methods are available through the CLI.

### Recommended: Selection bounds + padding

Use this for receptor-pocket residues and arbitrary selected atom groups. It finds the minimum and maximum coordinates of the selected atoms independently on X, Y, and Z, then expands both ends of every axis by the requested padding. The center is the midpoint of the expanded bounds; each size is the expanded maximum minus the expanded minimum.

For each axis, with coordinates `q_i` and padding `p`:

```text
minimum = min(q_i) - p
maximum = max(q_i) + p
center  = (minimum + maximum) / 2
size    = maximum - minimum
```

This method is recommended for selecting receptor residues because it directly encloses all selected atoms and provides the specified padding on every face. It does not round dimensions to whole Angstroms or align them to the grid spacing. Vina accepts the resulting center and size values and performs its own map discretization.

### Vina ligand-centroid method (ligands only; not recommended for receptor-pocket selections)

This option reproduces the style of Vina's ligand-derived box calculation. It computes the arithmetic mean of the selected coordinates as the center, measures the largest absolute excursion from that center on each axis, adds padding to the half-dimension, doubles it, and rounds the size upward to an integer Angstrom value:

```text
center = mean(atom coordinates)
size_axis = ceil(2 * (max(abs(coordinate_axis - center_axis)) + padding))
```

This mode is provided for compatibility and comparison with Vina's ligand-derived convention. It is not the recommended way to define a box around a receptor pocket: centering on the mean rather than the midpoint of the extrema can make the box offset and larger than the tight padded bounding box.

**About the Vina convention:** the Vina source code describes the centroid-based calculation, but the maintainer has not found a clear published explanation in the documentation/source reviewed for why this centering convention was preferred over a minimum/maximum-centred padded bounding box. The bounds method is recommended here for receptor-pocket selection because it directly expresses the intended geometry; this is a use-case recommendation, not a claim that the bounds method is universally superior for every Vina workflow.

Changing the padding while a box derived from a selection is active recalculates that box using the active method. Switching the method also recalculates from the last selected coordinates. Editing center/size manually detaches the box from the saved selection coordinates, so later padding changes do not overwrite manual values.

## GUI: Selection padding

**Padding per side (Å)** is the extra distance added beyond each selected-coordinate extreme in the recommended bounds method. For the Vina ligand-centroid method, it is the buffer used by that calculation. The default is 4 Å. Changing padding affects a selection-derived box; it does not change a manually defined box.

## GUI: Check selection

**Check selection** is a sanity check. It does **not** change the box.

After selecting atoms, click **Check selection** and the tool tests whether every selected atom is inside the current Vina box. It reports:

- the number of selected atoms inside;
- the number outside; and
- if any atoms are outside, the maximum Cartesian overhang in Å.

If no Vina box exists, the tool reports that a box must be created first instead of raising an error.

This is useful for confirming that the ligand is completely contained by the proposed search space before docking.

## GUI: Show Vina rounded map extent

Vina discretizes the requested box dimensions into a grid. With the default 0.375 Å spacing, the number of voxels along each axis is derived from the requested size, conceptually:

```text
n = ceil(size / spacing)
real_span = n × spacing
```

Therefore the discrete map span can be slightly larger than the requested `size_*` value.

For example:

```text
size_x = 24.390 Å
spacing = 0.375 Å

ceil(24.390 / 0.375) = 66 voxels
66 × 0.375 = 24.750 Å internal span
```

The **Show Vina rounded map extent** option displays that rounded internal span as a reference. It does **not** replace or modify the Vina `size_*` values that the tool exports.

The spacing field is therefore a visualization/reference setting in this bundle, not a separate Vina input file parameter.

## GUI: View box

**View box** frames the current Vina box using ChimeraX's normal `view` command.

## GUI: Copy Vina config

**Copy Vina config** places a ready-to-paste configuration block on the system clipboard, e.g.:

```text
center_x = 26.1720
center_y = 23.1697
center_z = -9.0871
size_x = 20.0000
size_y = 20.0000
size_z = 20.0000
# spacing reference = 0.3750 Å
# force_even_voxels = False
```

The six `center_*` and `size_*` values are the important Vina configuration values. The final two lines are informational comments added by this tool.

## GUI: Box color

**Box color…** changes the visual color of the Vina box. This affects only the ChimeraX visualization; it has no effect on Vina calculations.

## GUI: Clear

**Clear** removes the 3D Vina box from the scene. It does not modify receptor or ligand models.

## Command-line interface

The command is deliberately short: **`vinabox`**.

### Set or update the box

Use `set` to create a new box or update the existing box:

```text
vinabox set center 0,0,0 size 20,20,20
```

Example:

```text
vinabox set center 26.1720,23.1697,-9.0871 size 20,20,20
```

ChimeraX's `Float3Arg` syntax requires each 3D value to be supplied as one comma-separated triple. Therefore this is correct:

```text
center 0,0,0
```

while this is not:

```text
center 0 0 0
```

### Create a box from the current selection

Recommended for a receptor pocket:

```text
vinabox bounds padding 4
```

This finds the selected atoms' minimum/maximum coordinates and expands each side by 4 Å. Use the current ChimeraX atom selection; the command does not take a residue list directly.

Vina ligand-centroid method (intended for ligand atom selections, not receptor pockets):

```text
vinabox centroid padding 4
```

Both commands create or update the box and set the GUI's padding field to the supplied value. `padding` is optional and defaults to 4 Å:

```text
vinabox bounds
vinabox centroid padding 3.5
```

### Show the GUI

```text
vinabox showgui
```

`showgui` controls the GUI window only. It does not create or modify the 3D box.

### Hide the GUI

```text
vinabox hidegui
```

`hidegui` hides the GUI window. It does not delete the 3D box.

### Report current Vina values

```text
vinabox report
```

Example output:

```text
center_x = 26.1720
center_y = 23.1697
center_z = -9.0871
size_x = 20.0000
size_y = 20.0000
size_z = 20.0000
# spacing reference = 0.3750 Å
# force_even_voxels = False
```

### Clear the 3D box

```text
vinabox clear
```

This removes the current Vina box. It does not close the GUI window.

### Command summary

| Command | Effect |
|---|---|
| `vinabox set center X,Y,Z size X,Y,Z` | Create or update the 3D Vina box |
| `vinabox bounds padding 4` | Recommended: selected-coordinate bounds plus padding |
| `vinabox centroid padding 4` | Vina ligand-centroid selection method; intended for ligands |
| `vinabox showgui` | Show the Vina Grid Box GUI |
| `vinabox hidegui` | Hide the Vina Grid Box GUI |
| `vinabox report` | Print the current center/size values |
| `vinabox clear` | Remove the current 3D box |

For backward compatibility, the previous action names `from-selection-bounds`, `from-selection-vina`, `show`, and `hide` are still accepted. Prefer the shorter `bounds`, `centroid`, `showgui`, and `hidegui` names in new scripts. The synonyms `guishow` and `guihide` are accepted as well.

## Coordinate-system note

The bundle is intended for structures whose ChimeraX coordinates correspond to the coordinates that will be supplied to Vina. The selection-derived workflow currently uses ChimeraX atom **scene coordinates**. If a structure has been translated or otherwise transformed at the model/scene level without changing its saved atomic coordinates, verify the coordinate frame before exporting a search space for Vina.

For the simplest one-to-one Vina workflow, use the box with the structure in its original coordinate frame, or otherwise ensure that the coordinates you visualize are the same coordinates present in the receptor/ligand files used for docking.

## What the bundle does not do

This bundle:

- does not run AutoDock Vina;
- does not prepare receptor or ligand PDBQT files;
- does not choose a docking scoring function;
- does not alter atomic coordinates merely by displaying the box;
- does not currently provide stable interactive drag-resizing in the public release.

It is a visualization, box-definition, and pre-docking sanity-check tool.

## Reference implementation and compatibility

The manually entered center/size geometry follows AutoDock Vina's center/size semantics and the map display is a reference calculation. The recommended selection-bounds method is a geometric bounding-box calculation, while the optional Vina ligand-centroid method follows Vina's ligand-derived convention. See the Vina source and documentation:

- AutoDock Vina repository: https://github.com/ccsb-scripps/AutoDock-Vina
- Vina Python API map calculation: https://github.com/ccsb-scripps/AutoDock-Vina/blob/develop/build/python/vina/vina.py

The bundle was developed and tested in UCSF ChimeraX 1.12. Compatibility with other ChimeraX versions depends on the availability of the standard APIs used by the bundle.

## Citation

A simple citation form for this bundle is:

> Bhowmik, A. (2026). *ChimeraX Vina Grid Box*, version 1.9. ChimeraX Toolshed.

When discussing docking results, also cite the AutoDock Vina publication appropriate to the Vina version used in the study.

## Development acknowledgement

The implementation, debugging, packaging, and documentation of this bundle were developed with coding assistance from **ChatGPT (OpenAI)**. The final source and release decisions remain the responsibility of the bundle author.
