"""Ice-wall lateral boundary at the disc rim, r = R (spec §4.3).

No-penetration ``u . n = 0`` with free slip. On the collocated masked grid the
ghost-cell mirror ("mirror the normal velocity component, leave the tangential
component free") is realised directly: at every active cell that touches the
wall along an axis, the velocity component *normal* to that wall is set to zero,
while the tangential component is left untouched. Pressure/height already carries
a zero-normal-gradient (Neumann) condition through the operators (a closed face
uses ghost = self), and mass cannot cross the rim because the flux-form
continuity uses closed faces there.

This reflective wall is *why* the model produces standing-wave resonance and a
persistent rim anticyclone — the heart of the falsification story, not artifacts
to remove (CLAUDE.md, "Expected outputs, not bugs").
"""

from __future__ import annotations

import numpy as np

from solver.grid import DiscGrid
from solver.state import State


def apply_no_penetration(state: State, grid: DiscGrid) -> State:
    """Enforce ``u . n = 0`` at the rim (free-slip) and keep inactive cells clean.

    A cell has an x-normal wall if its east or west neighbour is inactive; there
    the x-velocity (the normal component) is zeroed and the y-velocity (tangential)
    is left free. The y-normal walls are handled symmetrically. Corner cells (both
    a normal wall in x and in y) lose both components — the seed of the corner
    turbulence at the dome-wall junction.
    """
    active = grid.mask
    # For an active cell, a closed face (~has_*) means the neighbour is inactive,
    # i.e. the ice wall lies in that direction.
    wall_x = active & (~grid.has_E | ~grid.has_W)  # wall to the east or west
    wall_y = active & (~grid.has_N | ~grid.has_S)  # wall to the north or south

    state.u = np.where(wall_x, 0.0, state.u) * active
    state.v = np.where(wall_y, 0.0, state.v) * active
    state.eta = state.eta * active
    return state
