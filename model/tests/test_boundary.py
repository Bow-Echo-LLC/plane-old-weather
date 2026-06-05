"""Phase 2 verification — ice-wall boundary and the phenomena it produces
(ARCHITECTURE.md §4.3, §8).

Definition of done: with the spotlight-sun forcing and the reflective ice wall,
non-rotating inflow (f = 0) and a rotating rim anticyclone (f-plane) emerge
qualitatively. These are *expected* outputs, not bugs (CLAUDE.md).
"""

from __future__ import annotations

import numpy as np
import pytest

import scenarios as scen
from boundary.ice_wall import apply_no_penetration
from forcing import DAY_SECONDS, SpotlightForcing
from solver import Params, State, build_disc_grid, integrate, rest_state

ORBIT_M = 3_000.0 * 1_000.0
ALTITUDE_M = scen.SUN_ALTITUDE_KM * 1_000.0
AMPLITUDE = 0.02
STEPS = 300


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


def _run(grid, f, dome="closed"):
    return integrate(rest_state(grid), grid, Params(f=f), steps=STEPS, forcing=_forcing(dome))


@pytest.fixture(scope="module")
def run_closed(grid):
    return _run(grid, 0.0, "closed")


@pytest.fixture(scope="module")
def run_fplane(grid):
    return _run(grid, scen.F_PLANE, "closed")


@pytest.fixture(scope="module")
def run_absorbing(grid):
    return _run(grid, 0.0, "absorbing")


def _net_rotation(state, grid, region):
    """Signed azimuthal wind averaged over ``region`` (negative = anticyclonic)."""
    r = np.where(grid.R > 0.0, grid.R, 1.0)
    return float(np.mean((-grid.Y * state.u + grid.X * state.v) / r * region))


# --- the ice-wall condition itself --------------------------------------------


def test_no_penetration_zeros_normal_velocity_at_rim(grid):
    ones = np.ones((grid.n, grid.n))
    state = apply_no_penetration(State(np.zeros_like(ones), ones.copy(), ones.copy()), grid)
    wall_x = grid.mask & (~grid.has_E | ~grid.has_W)
    wall_y = grid.mask & (~grid.has_N | ~grid.has_S)
    # Normal component zeroed at the wall, tangential left free.
    assert np.all(state.u[wall_x] == 0.0)
    assert np.all(state.v[wall_y] == 0.0)
    # Nothing lives outside the disc.
    assert np.all(state.u[~grid.mask] == 0.0)
    # A deep-interior cell (no wall on any side) is untouched.
    interior = grid.mask & grid.has_E & grid.has_W & grid.has_N & grid.has_S
    assert np.all(state.u[interior] == 1.0)
    assert np.all(state.v[interior] == 1.0)


def test_no_flow_through_wall_after_forced_run(grid, run_closed):
    # The integrator enforces no-penetration every substage, so even a fully
    # spun-up flow has zero velocity normal to the ice wall.
    wall_x = grid.mask & (~grid.has_E | ~grid.has_W)
    wall_y = grid.mask & (~grid.has_N | ~grid.has_S)
    assert np.abs(run_closed.state.u[wall_x]).max() < 1e-12
    assert np.abs(run_closed.state.v[wall_y]).max() < 1e-12


# --- emergent phenomena -------------------------------------------------------


def test_inflow_does_not_rotate_without_coriolis(grid, run_closed, run_fplane):
    # The cleanest "this is wrong" visual: with f = 0 the forced flow runs
    # straight down-gradient (no net rotation); a constant f spins up a strong,
    # coherent circulation.
    rot_no_f = _net_rotation(run_closed.state, grid, grid.mask)
    rot_fplane = _net_rotation(run_fplane.state, grid, grid.mask)
    assert abs(rot_fplane) > 100.0 * abs(rot_no_f)


def test_rim_anticyclone_on_fplane(grid, run_closed, run_fplane):
    # Near the ice wall the f-plane develops a persistent *anticyclonic* (negative
    # signed rotation) circulation — the rim anticyclone — absent at f = 0.
    outer = grid.mask & (grid.R / grid.radius_m >= 0.7)
    rim_rot_no_f = _net_rotation(run_closed.state, grid, outer)
    rim_rot_fplane = _net_rotation(run_fplane.state, grid, outer)
    assert rim_rot_fplane < 0.0  # anticyclonic
    assert abs(rim_rot_fplane) > 100.0 * abs(rim_rot_no_f)


def test_absorbing_dome_runs_hotter(grid, run_closed, run_absorbing):
    # Suppressing cooling where the column is tall concentrates heat into a
    # hotter, capped core: the dome-absorbing thermodynamic catastrophe.
    assert run_absorbing.state.eta.max() > 1.15 * run_closed.state.eta.max()
    # Both remain mass-neutral (the sink is redistributed, not removed).
    for run in (run_closed, run_absorbing):
        assert abs(run.state.eta.sum()) / np.abs(run.state.eta).sum() < 1e-9
