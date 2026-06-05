"""Mask-aware finite-difference / finite-volume operators on the disc grid.

Everything here is vectorised NumPy. Neighbour values are fetched with
``np.roll`` and then corrected at closed faces using the grid's ``has_*`` face
booleans, which encode the ice wall (a closed face = no neighbour). The two
properties that matter for Phase 1:

* :func:`divergence_flux` is in finite-volume *flux form* with zero flux through
  closed faces, so summing the continuity tendency over the disc telescopes to
  zero — **total mass is conserved to round-off**.
* :func:`gradient`, :func:`laplacian`, and :func:`advect_upwind` all treat a
  closed face as a zero-normal-gradient (Neumann) wall, so nothing is advected,
  diffused, or pressure-forced *through* the ice wall.
"""

from __future__ import annotations

import numpy as np

from .grid import DiscGrid


def _neighbor(a: np.ndarray, has: np.ndarray, shift: int, axis: int) -> np.ndarray:
    """Neighbour values along ``axis``, falling back to the cell's own value at a
    closed face (Neumann: ghost = self). ``shift`` follows ``np.roll`` (``-1``
    pulls the +index neighbour into place)."""
    rolled = np.roll(a, shift, axis=axis)
    return np.where(has, rolled, a)


def gradient(field: np.ndarray, g: DiscGrid) -> tuple[np.ndarray, np.ndarray]:
    """Centred gradient (d/dx, d/dy) with a zero-normal-gradient wall.

    Used for the pressure-gradient force ``-g grad(eta)``; the Neumann fallback
    gives ``d(eta)/dn = 0`` at the ice wall (spec §4.3).
    """
    east = _neighbor(field, g.has_E, -1, 1)
    west = _neighbor(field, g.has_W, 1, 1)
    north = _neighbor(field, g.has_N, -1, 0)
    south = _neighbor(field, g.has_S, 1, 0)
    dfdx = (east - west) / (2.0 * g.dx)
    dfdy = (north - south) / (2.0 * g.dx)
    return dfdx * g.mask, dfdy * g.mask


def divergence_flux(Fx: np.ndarray, Fy: np.ndarray, g: DiscGrid) -> np.ndarray:
    """Divergence of a flux field in conservative finite-volume form.

    Face fluxes are the average of the two adjacent cell-centre fluxes, and are
    forced to zero on closed faces (the ice wall). Because each interior face is
    shared with opposite sign by its two cells, the disc-wide sum of the result
    is exactly zero — the basis of discrete mass conservation.
    """
    # East/north face fluxes (zero where the face is closed).
    flux_E = np.where(g.has_E, 0.5 * (Fx + np.roll(Fx, -1, axis=1)), 0.0)
    flux_N = np.where(g.has_N, 0.5 * (Fy + np.roll(Fy, -1, axis=0)), 0.0)
    # A cell's west/south face flux is its neighbour's east/north face flux.
    flux_W = np.roll(flux_E, 1, axis=1)
    flux_W[:, 0] = 0.0
    flux_S = np.roll(flux_N, 1, axis=0)
    flux_S[0, :] = 0.0
    div = (flux_E - flux_W) / g.dx + (flux_N - flux_S) / g.dx
    return div * g.mask


def laplacian(field: np.ndarray, g: DiscGrid) -> np.ndarray:
    """Five-point Laplacian summing diffusive flux over open faces only.

    Closed faces contribute nothing (zero diffusive flux through the wall), so —
    like :func:`divergence_flux` — the disc-wide sum is exactly zero. That makes
    a ``nu * laplacian(eta)`` smoothing term mass-conserving.
    """
    east = np.roll(field, -1, axis=1)
    west = np.roll(field, 1, axis=1)
    north = np.roll(field, -1, axis=0)
    south = np.roll(field, 1, axis=0)
    lap = (
        g.has_E * (east - field)
        + g.has_W * (west - field)
        + g.has_N * (north - field)
        + g.has_S * (south - field)
    ) / (g.dx * g.dx)
    return lap * g.mask


def advect_upwind(q: np.ndarray, u: np.ndarray, v: np.ndarray, g: DiscGrid) -> np.ndarray:
    """First-order upwind advection ``u . grad(q)``.

    Upwind differencing is robust and adds a little scale-selective numerical
    diffusion that helps keep the collocated solver stable. The Neumann wall
    (neighbour = self at a closed face) means nothing is advected through the
    ice wall.
    """
    east = _neighbor(q, g.has_E, -1, 1)
    west = _neighbor(q, g.has_W, 1, 1)
    north = _neighbor(q, g.has_N, -1, 0)
    south = _neighbor(q, g.has_S, 1, 0)
    dqdx = np.where(u > 0.0, (q - west) / g.dx, (east - q) / g.dx)
    dqdy = np.where(v > 0.0, (q - south) / g.dx, (north - q) / g.dx)
    return (u * dqdx + v * dqdy) * g.mask
