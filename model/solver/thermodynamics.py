"""Continuity (free-surface height) tendency and the closed-dome assumption
(spec §4.2-4.3).

    d(eta)/dt = -div[(H + eta) u] + nu_h lap(eta) + Q

The first term is the shallow-water mass divergence in conservative flux form,
so total mass is conserved to round-off. ``nu_h lap(eta)`` is a scale-selective
smoother that suppresses collocated-grid checkerboard noise; because the masked
Laplacian sums to zero over the disc, it does **not** change total mass. ``Q``
is the thermal source (heating -> expansion -> local height rise); in Phase 1 it
is absent. The ``dome-absorbing`` cooling-sink variant arrives with the forcing
in Phase 2.
"""

from __future__ import annotations

import numpy as np

from .grid import DiscGrid
from .operators import divergence_flux, laplacian
from .state import Params, State


def continuity_tendency(
    state: State, grid: DiscGrid, p: Params, Q: np.ndarray | None = None
) -> np.ndarray:
    """Compute ``d(eta)/dt`` from mass divergence, height smoothing, and (later)
    the thermal source ``Q``."""
    total_depth = p.H + state.eta
    flux_x = total_depth * state.u
    flux_y = total_depth * state.v

    deta = -divergence_flux(flux_x, flux_y, grid) + p.nu_h * laplacian(state.eta, grid)
    if Q is not None:
        deta = deta + Q
    return deta * grid.mask
