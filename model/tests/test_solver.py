"""Phase 1 verification: the solver core runs stably, conserves mass, and
produces physical fields (ARCHITECTURE.md §8).

These are deliberately physics-level assertions, not unit trivia: they are the
definition of done for the solver. All runs are unforced (Q = 0) — the
spotlight-sun forcing arrives in Phase 2.
"""

from __future__ import annotations

import numpy as np
import pytest

import scenarios as scen
from solver import (
    Params,
    build_disc_grid,
    diagnostics,
    gaussian_bump,
    integrate,
    rest_state,
)
from solver.operators import divergence_flux, laplacian

RADIUS_KM = scen.DISC_RADIUS_KM


@pytest.fixture(scope="module")
def grid():
    return build_disc_grid(64, RADIUS_KM)


# --- geometry -----------------------------------------------------------------


def test_disc_mask_geometry(grid):
    # Centre is inside the disc; the corners are outside.
    c = grid.n // 2
    assert grid.mask[c, c]
    assert not grid.mask[0, 0]
    assert not grid.mask[-1, -1]
    # Active-cell count approximates the disc area pi*R^2 / dx^2 = (pi/4) n^2.
    expected = np.pi / 4 * grid.n**2
    assert abs(grid.active_count - expected) / expected < 0.05


def test_face_flags_consistent(grid):
    # A face can only be open if its own cell is active.
    assert not (grid.has_E & ~grid.mask).any()
    assert not (grid.has_N & ~grid.mask).any()
    # An open east face implies the eastern neighbour is active.
    assert np.array_equal(grid.has_E[:, :-1], grid.mask[:, :-1] & grid.mask[:, 1:])


# --- operator conservation properties -----------------------------------------


def test_operators_sum_to_zero_over_disc(grid):
    rng = np.random.default_rng(0)
    field = rng.standard_normal((grid.n, grid.n)) * grid.mask
    fx = rng.standard_normal((grid.n, grid.n)) * grid.mask
    fy = rng.standard_normal((grid.n, grid.n)) * grid.mask
    # Both the Laplacian and the flux divergence telescope to the (closed)
    # boundary, so their disc-wide sums vanish to round-off.
    assert abs(laplacian(field, grid).sum()) < 1e-9
    assert abs(divergence_flux(fx, fy, grid).sum()) < 1e-9


# --- integration: stability, conservation, physicality ------------------------


def test_rest_stays_at_rest(grid):
    result = integrate(rest_state(grid), grid, Params(), steps=50)
    assert np.max(np.abs(result.state.eta)) < 1e-12
    assert np.max(np.abs(result.state.u)) < 1e-12
    assert np.max(np.abs(result.state.v)) < 1e-12


def test_mass_conserved_unforced(grid):
    result = integrate(gaussian_bump(grid), grid, Params(f=0.0), steps=300)
    # Flux-form continuity with closed rim faces => mass conserved to round-off.
    assert result.mass_drift < 1e-9


def test_fields_stay_physical(grid):
    result = integrate(gaussian_bump(grid), grid, Params(f=0.0), steps=300)
    # Reaching here means the run stayed finite (integrate raises otherwise).
    assert result.final["min_depth"] > 0.0  # no dry-out: H + eta > 0 everywhere
    assert result.final["max_speed"] < 500.0  # winds stay in a sane range
    # Fields are confined to the disc; nothing leaks outside the mask.
    assert np.all(result.state.eta[~grid.mask] == 0.0)
    assert np.all(result.state.u[~grid.mask] == 0.0)


def test_energy_does_not_grow(grid):
    # Every term (drag, viscosity, upwind, height smoothing) is dissipative and
    # there is no forcing, so total energy must be non-increasing.
    result = integrate(gaussian_bump(grid), grid, Params(), steps=300, record_every=25)
    e0 = result.initial["energy"]
    assert result.final["energy"] < e0  # some energy is dissipated
    assert all(h["energy"] <= e0 * (1 + 1e-6) for h in result.history)


def test_fplane_run_is_stable(grid):
    # The f-plane scenario uses a constant, non-zero Coriolis parameter.
    result = integrate(gaussian_bump(grid), grid, Params(f=scen.F_PLANE), steps=300)
    assert result.mass_drift < 1e-9
    assert result.final["max_speed"] < 500.0


def test_coriolis_deflects_flow(grid):
    # With f = 0 the collapsing bump radiates radial outflow that disperses with
    # no preferred rotation; with f != 0 geostrophic adjustment leaves a
    # balanced, coherently rotating vortex with a definite sign. This is the
    # qualitative no-coriolis vs f-plane distinction the scenarios exist to show.
    no_f = integrate(gaussian_bump(grid), grid, Params(f=0.0), steps=200)
    with_f = integrate(gaussian_bump(grid), grid, Params(f=scen.F_PLANE), steps=200)

    r = np.where(grid.R > 0.0, grid.R, 1.0)

    def net_rotation(state):
        # Signed azimuthal wind about the centre, averaged over the disc. Radial
        # outflow and (chirality-free) grid noise cancel in the mean; coherent
        # rotation does not.
        tang = (-grid.Y * state.u + grid.X * state.v) / r
        return float(np.mean(tang * grid.mask))

    assert abs(net_rotation(with_f.state)) > 10.0 * abs(net_rotation(no_f.state))


def test_cfl_timestep_respects_gravity_wave_speed(grid):
    from solver import cfl_timestep

    p = Params()
    dt = cfl_timestep(grid, p)
    assert 0.0 < dt < grid.dx / p.gravity_wave_speed


def test_diagnostics_keys(grid):
    d = diagnostics(gaussian_bump(grid), grid, Params())
    assert set(d) == {"mass", "energy", "max_speed", "min_depth"}
