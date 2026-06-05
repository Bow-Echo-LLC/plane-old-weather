"""The spotlight sun: a small, close source whose sub-solar point orbits the
disc centre over the diurnal cycle (spec §4.2).

    Q(x, y, t) = S0 / (1 + (d/h)^2) * cos(alpha)

where ``d`` is the horizontal distance to the sub-solar point, ``h`` is the sun's
altitude (~5000 km), and ``alpha`` is the local incidence angle. For a point sun
at height ``h`` above the sub-solar point, ``cos(alpha) = h / sqrt(h^2 + d^2)``,
so the two factors combine to ``Q = S0 * h^3 / (h^2 + d^2)^{3/2}`` — the moving
"thermal bull's-eye" that is the core thermodynamic difference from a sphere.

Heating enters the shallow-water system as a *mass source* (heating -> expansion
-> local height rise; spec §3.3): the returned field is added to ``d(eta)/dt``.
Net heating is balanced by the dome cooling sink (boundary/dome.py) so runs reach
equilibrium; :class:`SpotlightForcing` combines the two into the ``Q`` the solver
consumes.
"""

from __future__ import annotations

import math

import numpy as np

from boundary.dome import cooling_sink
from solver.grid import DiscGrid
from solver.state import State

DAY_SECONDS: float = 86_400.0  # one diurnal cycle of the spotlight sun


def subsolar_point(
    t: float, orbit_radius_m: float, period_s: float = DAY_SECONDS
) -> tuple[float, float]:
    """Position of the sub-solar point at time ``t``, tracing a ring of radius
    ``orbit_radius_m`` about the disc centre once per ``period_s``."""
    omega = 2.0 * math.pi / period_s
    return orbit_radius_m * math.cos(omega * t), orbit_radius_m * math.sin(omega * t)


def insolation(
    grid: DiscGrid,
    t: float,
    *,
    orbit_radius_m: float,
    altitude_m: float,
    amplitude: float,
    period_s: float = DAY_SECONDS,
) -> np.ndarray:
    """Heating field ``Q_in(x, y, t) >= 0`` over the disc at time ``t`` (spec §4.2)."""
    sx, sy = subsolar_point(t, orbit_radius_m, period_s)
    d2 = (grid.X - sx) ** 2 + (grid.Y - sy) ** 2
    h2 = altitude_m * altitude_m
    # S0/(1+(d/h)^2) * cos(alpha) = S0 * h^3 / (h^2 + d^2)^{3/2}
    q_in = amplitude * altitude_m * h2 / np.power(h2 + d2, 1.5)
    return q_in * grid.mask


class SpotlightForcing:
    """Callable forcing ``Q_net = heating - cooling`` for the solver.

    Holds the per-scenario knobs (orbit radius -> season, dome mode) and, when
    called with the current state, returns the net thermal mass source. The
    cooling sink balances the heating so total mass is conserved and the run
    reaches a moving equilibrium (spec §4.2-4.3).
    """

    def __init__(
        self,
        *,
        orbit_radius_m: float,
        altitude_m: float,
        amplitude: float,
        period_s: float = DAY_SECONDS,
        dome_mode: str = "closed",
    ) -> None:
        self.orbit_radius_m = orbit_radius_m
        self.altitude_m = altitude_m
        self.amplitude = amplitude
        self.period_s = period_s
        self.dome_mode = dome_mode

    def heating(self, grid: DiscGrid, t: float) -> np.ndarray:
        return insolation(
            grid,
            t,
            orbit_radius_m=self.orbit_radius_m,
            altitude_m=self.altitude_m,
            amplitude=self.amplitude,
            period_s=self.period_s,
        )

    def __call__(self, state: State, grid: DiscGrid, t: float) -> np.ndarray:
        q_in = self.heating(grid, t)
        cooling = cooling_sink(q_in, state.eta, grid, mode=self.dome_mode)
        return q_in - cooling
