"""Cartesian-grid-with-disc-mask geometry (spec §4.1).

A regular Cartesian grid whose cells outside ``x^2 + y^2 > R^2`` are inactive.
This deliberately avoids the ``r = 0`` coordinate singularity of a true polar
``(r, theta)`` mesh and is the chosen starting point (CLAUDE.md, "Known
gotchas"); a pole-averaging polar stencil is a later refinement, not a first
pass.

Fields are stored collocated at cell centres in 2-D arrays indexed ``[j, i]``
(row ``j`` = y, column ``i`` = x). The grid precomputes, for each cell, whether
its east/west/north/south face is *open* (both adjacent cells active). A closed
face is the ice wall: no flux crosses it. Those boolean face arrays are what
make the finite-volume operators (operators.py) conserve mass exactly and apply
the no-penetration / Neumann wall conditions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(eq=False)
class DiscGrid:
    """A square Cartesian grid masked to a disc of radius ``radius_m``.

    The physical domain is ``[-radius_m, radius_m]`` on each axis, so the disc
    is inscribed in the grid and touches the domain edges only on the axes.
    """

    n: int
    radius_m: float
    dx: float
    x: np.ndarray  # (n,) cell-centre x coordinates [m]
    y: np.ndarray  # (n,) cell-centre y coordinates [m]
    X: np.ndarray  # (n, n) meshgrid X[j, i] = x[i]
    Y: np.ndarray  # (n, n) meshgrid Y[j, i] = y[j]
    R: np.ndarray  # (n, n) radial distance from centre [m]
    mask: np.ndarray  # (n, n) bool: True where the cell is active (inside disc)
    # Per-cell booleans: is the face toward this neighbour open (both active)?
    has_E: np.ndarray
    has_W: np.ndarray
    has_N: np.ndarray
    has_S: np.ndarray

    @property
    def active_count(self) -> int:
        return int(self.mask.sum())

    @property
    def cell_area(self) -> float:
        return self.dx * self.dx


def build_disc_grid(n: int, radius_km: float) -> DiscGrid:
    """Build the masked Cartesian grid for an ``n x n`` domain of half-width R.

    ``n`` is the number of cells per side; ``radius_km`` is the disc radius R
    (which equals the domain half-width). Returns a fully-populated
    :class:`DiscGrid`.
    """
    radius_m = radius_km * 1_000.0
    # Cell-centred coordinates spanning [-R, R]: width 2R split into n cells.
    dx = 2.0 * radius_m / n
    x = -radius_m + (np.arange(n) + 0.5) * dx
    y = x.copy()
    X, Y = np.meshgrid(x, y)  # 'xy' indexing: X[j, i] = x[i], Y[j, i] = y[j]
    R = np.hypot(X, Y)
    mask = R <= radius_m

    # An east face (between cell i and i+1) is open iff both cells are active.
    # Build by shifting the mask and disabling wrap-around at the domain edge.
    maskE = np.roll(mask, -1, axis=1)
    maskE[:, -1] = False
    maskW = np.roll(mask, 1, axis=1)
    maskW[:, 0] = False
    maskN = np.roll(mask, -1, axis=0)
    maskN[-1, :] = False
    maskS = np.roll(mask, 1, axis=0)
    maskS[0, :] = False

    return DiscGrid(
        n=n,
        radius_m=radius_m,
        dx=dx,
        x=x,
        y=y,
        X=X,
        Y=Y,
        R=R,
        mask=mask,
        has_E=mask & maskE,
        has_W=mask & maskW,
        has_N=mask & maskN,
        has_S=mask & maskS,
    )
