"""Prognostic state, physical parameters, and initial conditions.

The model is the single-layer shallow-water system (spec §4.1):

    du/dt + (u.grad)u + f (k x u) = -g grad(eta) - r u + nu lap(u)
    d(eta)/dt + div[(H + eta) u]  = Q(x, y, t)

``eta`` is the free-surface height perturbation (the model's pressure stand-in),
``u, v`` the horizontal wind. In Phase 1 the thermal source ``Q`` is absent; the
moving spotlight-sun forcing arrives in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .grid import DiscGrid


@dataclass
class State:
    """Prognostic fields, collocated at cell centres, shape ``(n, n)``."""

    eta: np.ndarray  # free-surface height perturbation [m]
    u: np.ndarray  # x-velocity [m/s]
    v: np.ndarray  # y-velocity [m/s]

    def copy(self) -> State:
        return State(self.eta.copy(), self.u.copy(), self.v.copy())


@dataclass(frozen=True)
class Params:
    """Physical and numerical parameters.

    Defaults give a gravity-wave speed ``sqrt(g H) ~ 280 m/s`` on the
    20,000 km disc — fast enough to set the CFL timestep, slow enough that a
    diurnal cycle is a few hundred steps.
    """

    g: float = 9.81  # gravity [m/s^2]
    H: float = 8_000.0  # mean layer depth [m]
    f: float = 0.0  # Coriolis parameter [1/s]; 0 baseline, F_PLANE for f-plane
    r: float = 1.0e-6  # linear (Rayleigh) drag [1/s]
    nu: float = 2.0e4  # eddy viscosity on momentum [m^2/s]
    nu_h: float = 1.0e6  # scale-selective height smoothing [m^2/s], mass-conserving

    @property
    def gravity_wave_speed(self) -> float:
        return float(np.sqrt(self.g * self.H))


def rest_state(grid: DiscGrid) -> State:
    """A motionless state with a flat free surface."""
    zeros = np.zeros((grid.n, grid.n))
    return State(zeros.copy(), zeros.copy(), zeros.copy())


def gaussian_bump(
    grid: DiscGrid,
    amplitude_m: float = 200.0,
    sigma_km: float = 2_000.0,
    center_km: tuple[float, float] = (0.0, 0.0),
) -> State:
    """A motionless state with a Gaussian height anomaly.

    A standard shallow-water initial condition: the bump collapses and radiates
    gravity waves (geostrophic adjustment when ``f != 0``). Used in Phase 1 to
    exercise the solver before the spotlight-sun forcing exists.
    """
    cx, cy = center_km[0] * 1_000.0, center_km[1] * 1_000.0
    sigma = sigma_km * 1_000.0
    r2 = (grid.X - cx) ** 2 + (grid.Y - cy) ** 2
    eta = amplitude_m * np.exp(-r2 / (2.0 * sigma**2)) * grid.mask
    zeros = np.zeros((grid.n, grid.n))
    return State(eta, zeros.copy(), zeros.copy())
