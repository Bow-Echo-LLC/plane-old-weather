"""Solver core: the masked-Cartesian disc grid, shallow-water dynamics with a
configurable Coriolis term, the continuity (height) equation, and the SSP-RK3
time integrator.

See docs/ARCHITECTURE.md §4.1 and the Phase 1 definition of done (§8). Public
API:

    grid    = build_disc_grid(n, radius_km)
    state   = gaussian_bump(grid)            # or rest_state(grid)
    params  = Params(f=...)                  # f from the scenario
    result  = integrate(state, grid, params, steps)
    result.mass_drift, result.final["energy"], ...
"""

from __future__ import annotations

from .dynamics import momentum_tendency
from .grid import DiscGrid, build_disc_grid
from .integrate import (
    IntegrationResult,
    cfl_timestep,
    diagnostics,
    integrate,
    rk3_step,
)
from .state import Params, State, gaussian_bump, rest_state
from .thermodynamics import continuity_tendency

__all__ = [
    "DiscGrid",
    "build_disc_grid",
    "State",
    "Params",
    "rest_state",
    "gaussian_bump",
    "momentum_tendency",
    "continuity_tendency",
    "integrate",
    "rk3_step",
    "cfl_timestep",
    "diagnostics",
    "IntegrationResult",
]
