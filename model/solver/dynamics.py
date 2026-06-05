"""Shallow-water momentum tendencies: advection, pressure gradient, a
configurable Coriolis term, Rayleigh drag, and eddy viscosity (spec §4.1).

    du/dt = -(u.grad)u + f v - g d(eta)/dx - r u + nu lap(u)
    dv/dt = -(u.grad)v - f u - g d(eta)/dy - r v + nu lap(v)

``f`` is a scenario knob: 0.0 for the disc baseline and the ``no-coriolis``
scenario; the constant ``F_PLANE = 2*Omega`` for ``f-plane-dome``. The spherical
``f = 2*Omega*sin(phi)`` is never used here — that geometry does not exist on
the disc (CLAUDE.md, "Known gotchas").
"""

from __future__ import annotations

import numpy as np

from .grid import DiscGrid
from .operators import advect_upwind, gradient, laplacian
from .state import Params, State


def momentum_tendency(state: State, grid: DiscGrid, p: Params) -> tuple[np.ndarray, np.ndarray]:
    """Compute ``(du/dt, dv/dt)`` for the shallow-water momentum equations."""
    detadx, detady = gradient(state.eta, grid)

    du = (
        -advect_upwind(state.u, state.u, state.v, grid)
        + p.f * state.v
        - p.g * detadx
        - p.r * state.u
        + p.nu * laplacian(state.u, grid)
    )
    dv = (
        -advect_upwind(state.v, state.u, state.v, grid)
        - p.f * state.u
        - p.g * detady
        - p.r * state.v
        + p.nu * laplacian(state.v, grid)
    )
    return du * grid.mask, dv * grid.mask
