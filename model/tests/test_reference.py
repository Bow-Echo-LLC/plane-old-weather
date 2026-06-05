"""Phase 3 verification — the azimuthal-equidistant reprojection for
sphere-reference (ARCHITECTURE.md §4.4).

The projection is the high-stakes piece (the falsification narrative leans on
the disc-vs-sphere comparison), so we check the mapping formula directly and
that the reprojected climatology forms latitudinal bands — the contrast to the
disc's moving bull's-eye.
"""

from __future__ import annotations

import numpy as np
import pytest

import scenarios as scen
from reference.era5_reproject import disc_to_latlon, reproject_to_disc
from render.fields import DISPLAY_VARIABLES, VARIABLE_SPECS
from solver import build_disc_grid


@pytest.fixture(scope="module")
def grid():
    return build_disc_grid(64, scen.DISC_RADIUS_KM)


def test_azimuthal_equidistant_formula(grid):
    lat, lon = disc_to_latlon(grid)
    # North-polar azimuthal equidistant: latitude is linear in radius.
    assert np.allclose(lat, 90.0 - 180.0 * grid.R / grid.radius_m)
    # Centre ~ North Pole, rim ~ South Pole.
    assert lat.max() > 84.0
    assert lat[grid.mask].min() < -84.0
    # Longitude increases counter-clockwise from +x.
    ne = grid.mask & (grid.X > 0) & (grid.Y > 0)
    nw = grid.mask & (grid.X < 0) & (grid.Y > 0)
    assert np.all((lon[ne] > 0.0) & (lon[ne] < 90.0))
    assert np.all((lon[nw] > 90.0) & (lon[nw] < 180.0))


def test_reproject_keys_and_ranges(grid):
    fields = reproject_to_disc(grid)
    assert {*DISPLAY_VARIABLES, "wind_u", "wind_v"} <= set(fields)
    m = grid.mask
    for var in DISPLAY_VARIABLES:
        lo, hi = VARIABLE_SPECS[var]["value_range"]
        assert lo <= float(fields[var][m].min())
        assert float(fields[var][m].max()) <= hi


def test_temperature_forms_latitudinal_bands(grid):
    temperature = reproject_to_disc(grid)["temperature"]
    rr = grid.R / grid.radius_m
    pole = grid.mask & (rr < 0.1)  # North Pole at the centre
    equator = grid.mask & (np.abs(rr - 0.5) < 0.05)  # equator at r = R/2
    rim = grid.mask & (rr > 0.9)  # South Pole at the rim
    # The equator ring is the warmest; both poles are cold — Earth's latitudinal
    # gradient, not the disc's bull's-eye.
    assert temperature[equator].mean() > temperature[pole].mean()
    assert temperature[equator].mean() > temperature[rim].mean()
