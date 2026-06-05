"""Phase 2 verification — spotlight-sun forcing and the dome cooling sink
(ARCHITECTURE.md §4.2-4.3, §8).

The forcing is a moving "thermal bull's-eye" that enters the shallow-water system
as a mass source; a dome cooling sink balances it so runs reach equilibrium and
mass is conserved. The absorbing-dome variant suppresses cooling where the column
is tall, producing a hotter, capped core (the thermodynamic catastrophe).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import scenarios as scen
from boundary.dome import cooling_sink
from forcing import DAY_SECONDS, SpotlightForcing, insolation, subsolar_point
from solver import Params, build_disc_grid, integrate, rest_state

ORBIT_M = 3_000.0 * 1_000.0
ALTITUDE_M = scen.SUN_ALTITUDE_KM * 1_000.0
AMPLITUDE = 0.02


@pytest.fixture(scope="module")
def grid():
    return build_disc_grid(64, scen.DISC_RADIUS_KM)


def _forcing(dome="closed"):
    return SpotlightForcing(
        orbit_radius_m=ORBIT_M,
        altitude_m=ALTITUDE_M,
        amplitude=AMPLITUDE,
        period_s=DAY_SECONDS,
        dome_mode=dome,
    )


# --- the moving sub-solar point -----------------------------------------------


def test_subsolar_orbits_at_fixed_radius():
    r = ORBIT_M
    x0, y0 = subsolar_point(0.0, r)
    assert math.isclose(x0, r, rel_tol=1e-9) and abs(y0) < 1e-6
    # A quarter day later it is 90 degrees around the ring.
    xq, yq = subsolar_point(DAY_SECONDS / 4, r)
    assert abs(xq) < 1e-6 and math.isclose(yq, r, rel_tol=1e-9)
    # The orbit radius is constant over the cycle.
    for t in np.linspace(0, DAY_SECONDS, 9):
        sx, sy = subsolar_point(t, r)
        assert math.isclose(math.hypot(sx, sy), r, rel_tol=1e-9)


# --- insolation shape ---------------------------------------------------------


def test_insolation_peaks_under_the_sun(grid):
    t = 0.123 * DAY_SECONDS
    q = insolation(grid, t, orbit_radius_m=ORBIT_M, altitude_m=ALTITUDE_M, amplitude=AMPLITUDE)
    # Heating is confined to the disc and strictly positive inside.
    assert np.all(q[~grid.mask] == 0.0)
    assert q[grid.mask].min() > 0.0
    # The hottest cell is the active cell nearest the sub-solar point (Q falls
    # off monotonically with distance).
    sx, sy = subsolar_point(t, ORBIT_M)
    d2 = (grid.X - sx) ** 2 + (grid.Y - sy) ** 2
    d2_masked = np.where(grid.mask, d2, np.inf)
    assert np.argmax(q) == np.argmin(d2_masked)


# --- dome cooling sink --------------------------------------------------------


def test_closed_cooling_is_uniform_and_mass_neutral(grid):
    heating = insolation(
        grid, 0.0, orbit_radius_m=ORBIT_M, altitude_m=ALTITUDE_M, amplitude=AMPLITUDE
    )
    eta = np.zeros((grid.n, grid.n))
    cooling = cooling_sink(heating, eta, grid, mode="closed")
    # Uniform over the disc...
    assert np.ptp(cooling[grid.mask]) < 1e-12
    # ...and balances the heating, so the net source is mass-neutral.
    net = (heating - cooling) * grid.mask
    assert abs(net.sum()) < 1e-9 * heating.sum()


def test_absorbing_cooling_spares_tall_columns_but_balances(grid):
    heating = insolation(
        grid, 0.0, orbit_radius_m=ORBIT_M, altitude_m=ALTITUDE_M, amplitude=AMPLITUDE
    )
    # A tall column at the centre, a short one off to the side.
    eta = 400.0 * np.exp(-(grid.R**2) / (2 * (2.0e6) ** 2)) * grid.mask
    cooling = cooling_sink(heating, eta, grid, mode="absorbing")
    # Still balances the heating (mass-neutral).
    net = (heating - cooling) * grid.mask
    assert abs(net.sum()) < 1e-9 * heating.sum()
    # Cooling is suppressed where the column is tall relative to where it is short.
    tall = np.unravel_index(np.argmax(eta), eta.shape)
    short = np.unravel_index(np.argmin(np.where(grid.mask, eta, np.inf)), eta.shape)
    assert cooling[tall] < cooling[short]


# --- forced integration -------------------------------------------------------


def test_forced_run_conserves_mass(grid):
    result = integrate(rest_state(grid), grid, Params(f=0.0), steps=300, forcing=_forcing())
    eta = result.state.eta
    # The balanced sink keeps the net source mass-neutral, so total mass stays at
    # its initial value (zero) to round-off, relative to the field magnitude.
    relative = abs(eta.sum()) / np.abs(eta).sum()
    assert relative < 1e-9


def test_forcing_builds_physical_structure(grid):
    result = integrate(rest_state(grid), grid, Params(f=0.0), steps=300, forcing=_forcing())
    # Starting from rest, the forcing does work and builds a substantial anomaly...
    assert np.abs(result.state.eta).max() > 50.0
    # ...while staying physical.
    assert result.final["min_depth"] > 0.0
    assert result.final["max_speed"] < 200.0
