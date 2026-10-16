import math

DEFAULT_SPACING = 0.375


def normalize_box(center, size):
    center = tuple(float(v) for v in center)
    size = tuple(float(v) for v in size)
    if any(v <= 0.0 for v in size):
        raise ValueError("All Vina box dimensions must be > 0 Å")
    return center, size


def bounds_from_center_size(center, size):
    center, size = normalize_box(center, size)
    half = tuple(v * 0.5 for v in size)
    lo = tuple(c - h for c, h in zip(center, half))
    hi = tuple(c + h for c, h in zip(center, half))
    return lo, hi


def center_size_from_bounds(lo, hi):
    lo = tuple(float(v) for v in lo)
    hi = tuple(float(v) for v in hi)
    center = tuple((a + b) * 0.5 for a, b in zip(lo, hi))
    size = tuple(b - a for a, b in zip(lo, hi))
    return normalize_box(center, size)


def vina_map_info(size, spacing=DEFAULT_SPACING, force_even_voxels=False):
    size = tuple(float(v) for v in size)
    spacing = float(spacing)
    if spacing <= 0:
        raise ValueError("Grid spacing must be > 0 Å")
    voxels = [math.ceil(v / spacing) for v in size]
    if force_even_voxels:
        voxels = [n if n % 2 == 0 else n + 1 for n in voxels]
    real_span = tuple(n * spacing for n in voxels)
    return tuple(voxels), real_span


def selection_bounds_box(coords, padding=4.0):
    """Create an axis-aligned box around selected atoms plus padding per side.

    The box is centered at the midpoint between each axis' coordinate extrema.
    No integer-Angstrom rounding or grid-spacing alignment is applied here.
    """
    import numpy as np

    xyz = np.asarray(coords, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.shape[0] == 0:
        raise ValueError("At least one 3D atom coordinate is required")
    if not np.isfinite(xyz).all():
        raise ValueError("Atom coordinates must all be finite numbers")
    padding = float(padding)
    if not math.isfinite(padding) or padding < 0:
        raise ValueError("Padding must be a finite value >= 0 Å")

    lo = xyz.min(axis=0) - padding
    hi = xyz.max(axis=0) + padding
    center = (lo + hi) * 0.5
    size = hi - lo
    # Vina box dimensions must be positive. A degenerate single-point selection
    # with zero padding receives a tiny positive size instead of a zero edge.
    size = [max(float(v), 0.001) for v in size]
    return tuple(float(v) for v in center), tuple(size)


def vina_ligand_box(coords, padding=4.0):
    """Vina-style ligand-derived center/size calculation.

    Vina's grid_dimensions_from_ligand() uses the arithmetic mean of the
    movable atom coordinates as center, finds the largest absolute excursion
    on each axis, then rounds the doubled buffered extent upward to integers.
    """
    import numpy as np

    xyz = np.asarray(coords, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.shape[0] == 0:
        raise ValueError("At least one 3D atom coordinate is required")
    padding = float(padding)
    if padding < 0:
        raise ValueError("Padding must be >= 0 Å")
    center = xyz.mean(axis=0)
    max_distance = np.max(np.abs(xyz - center), axis=0)
    size = np.ceil((max_distance + padding) * 2.0)
    size = np.maximum(size, 0.001)
    return tuple(float(v) for v in center), tuple(float(v) for v in size)


def vina_config_text(center, size, spacing=DEFAULT_SPACING, force_even_voxels=False):
    center, size = normalize_box(center, size)
    return (
        f"center_x = {center[0]:.4f}\n"
        f"center_y = {center[1]:.4f}\n"
        f"center_z = {center[2]:.4f}\n"
        f"size_x = {size[0]:.4f}\n"
        f"size_y = {size[1]:.4f}\n"
        f"size_z = {size[2]:.4f}\n"
        f"# spacing reference = {float(spacing):.4f} Å\n"
        f"# force_even_voxels = {bool(force_even_voxels)}\n"
    )
