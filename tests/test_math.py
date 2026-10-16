import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))

from math_utils import (
    bounds_from_center_size, center_size_from_bounds, vina_map_info,
    vina_ligand_box, selection_bounds_box
)


def test_bounds_round_trip():
    c=(28.297,24.706,-8.419); s=(24.39,30.682,20.616)
    lo,hi=bounds_from_center_size(c,s)
    c2,s2=center_size_from_bounds(lo,hi)
    assert all(abs(a-b) < 1e-9 for a,b in zip(c2,c))
    assert all(abs(a-b) < 1e-9 for a,b in zip(s2,s))


def test_map_info():
    vox,span=vina_map_info((24.39,30.682,20.616),.375)
    assert vox==(66,82,55)
    assert span==(24.75,30.75,20.625)


def test_vina_ligand_box():
    coords=[[0,0,0],[2,4,6],[-2,2,1]]
    c,s=vina_ligand_box(coords,4)
    assert c==(0.0,2.0,7/3)
    assert s==(12.0,12.0,16.0)


def test_selection_bounds_box_uses_extrema_and_padding():
    coords = [[0, 0, 0], [2, 4, 6], [-2, 2, 1]]
    center, size = selection_bounds_box(coords, padding=4)
    assert center == (0.0, 2.0, 3.0)
    assert size == (12.0, 12.0, 14.0)


def test_selection_bounds_box_asymmetric_points_differ_from_vina_centroid_method():
    coords = [[0, 0, 0], [2, 0, 0], [10, 0, 0]]
    bounds_center, bounds_size = selection_bounds_box(coords, padding=2)
    vina_center, vina_size = vina_ligand_box(coords, padding=2)
    assert bounds_center == (5.0, 0.0, 0.0)
    assert bounds_size == (14.0, 4.0, 4.0)
    assert vina_center == (4.0, 0.0, 0.0)
    assert vina_size == (16.0, 4.0, 4.0)


def test_selection_bounds_box_rejects_invalid_input():
    import pytest
    with pytest.raises(ValueError):
        selection_bounds_box([], padding=4)
    with pytest.raises(ValueError):
        selection_bounds_box([[0, 0, 0]], padding=-1)
