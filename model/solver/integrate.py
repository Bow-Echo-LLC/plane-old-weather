"""Time integration with stability controls (spec §4.1).

A strong-stability-preserving RK3 (Shu-Osher) stepper. The timestep respects the
gravity-wave CFL condition ``dt < dx / sqrt(g H)``; upwind advection, eddy
viscosity, and the height smoother keep the run from blowing up (CLAUDE.md,
"Known gotchas: numerical stability"). Get one scenario integrating to
completion before adding scenarios.

The driver also tracks conservation diagnostics — total mass, total energy,
peak wind, minimum layer depth — which Phase 1's verification leans on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from boundary.ice_wall import apply_no_penetration

from .dynamics import momentum_tendency
from .grid import DiscGrid
from .state import Params, State
from .thermodynamics import continuity_tendency

# A forcing supplies the thermal source given the current state, grid, and time:
# Q(state, grid, t). None means no forcing.
Forcing = Callable[[State, DiscGrid, float], np.ndarray]


def cfl_timestep(grid: DiscGrid, p: Params, safety: float = 0.4) -> float:
    """A CFL-respecting timestep set by the gravity-wave speed (the fastest
    signal in the system). ``safety`` < 1 keeps a margin."""
    return safety * grid.dx / p.gravity_wave_speed


def _tendencies(
    state: State, grid: DiscGrid, p: Params, forcing: Forcing | None, t: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    Q = forcing(state, grid, t) if forcing is not None else None
    du, dv = momentum_tendency(state, grid, p)
    deta = continuity_tendency(state, grid, p, Q)
    return deta, du, dv


def _euler(state: State, d: tuple[np.ndarray, np.ndarray, np.ndarray], dt: float) -> State:
    """Forward-Euler substep ``state + dt * d`` (the building block of SSP-RK3)."""
    deta, du, dv = d
    return State(state.eta + dt * deta, state.u + dt * du, state.v + dt * dv)


def _combine(a: State, b: State, wa: float, wb: float) -> State:
    """Convex combination ``wa * a + wb * b`` of two states."""
    return State(
        wa * a.eta + wb * b.eta,
        wa * a.u + wb * b.u,
        wa * a.v + wb * b.v,
    )


def rk3_step(
    state: State,
    grid: DiscGrid,
    p: Params,
    dt: float,
    t: float = 0.0,
    forcing: Forcing | None = None,
) -> State:
    """One SSP-RK3 (Shu-Osher) step, applying the ice-wall no-penetration
    condition after each substage.

    The forcing is evaluated per substage at the Shu-Osher stage times
    (t, t+dt, t+dt/2) using each stage's state, so the state-dependent
    absorbing-dome cooling stays consistent within the step."""
    d0 = _tendencies(state, grid, p, forcing, t)
    s1 = apply_no_penetration(_euler(state, d0, dt), grid)
    d1 = _tendencies(s1, grid, p, forcing, t + dt)
    s2 = apply_no_penetration(_combine(state, _euler(s1, d1, dt), 0.75, 0.25), grid)
    d2 = _tendencies(s2, grid, p, forcing, t + 0.5 * dt)
    s3 = _combine(state, _euler(s2, d2, dt), 1.0 / 3.0, 2.0 / 3.0)
    return apply_no_penetration(s3, grid)


def diagnostics(state: State, grid: DiscGrid, p: Params) -> dict[str, float]:
    """Conservation/physical diagnostics over the active disc."""
    dA = grid.cell_area
    total_depth = p.H + state.eta
    kinetic = 0.5 * np.sum(total_depth * (state.u**2 + state.v**2)) * dA
    potential = 0.5 * p.g * np.sum(state.eta**2) * dA
    speed = np.sqrt(state.u**2 + state.v**2)
    depth_in_disc = np.where(grid.mask, total_depth, p.H)
    return {
        "mass": float(np.sum(state.eta) * dA),  # H-part is constant; track the anomaly
        "energy": float(kinetic + potential),
        "max_speed": float(speed.max()),
        "min_depth": float(depth_in_disc.min()),
    }


@dataclass
class IntegrationResult:
    """Final state plus the diagnostics needed to judge a run."""

    state: State
    dt: float
    steps: int
    initial: dict[str, float]
    final: dict[str, float]
    history: list[dict[str, float]] = field(default_factory=list)

    @property
    def mass_drift(self) -> float:
        """Relative change in total mass anomaly (should be ~round-off)."""
        m0 = self.initial["mass"]
        denom = abs(m0) if abs(m0) > 0 else 1.0
        return abs(self.final["mass"] - m0) / denom


def integrate(
    state: State,
    grid: DiscGrid,
    p: Params,
    steps: int,
    dt: float | None = None,
    forcing: Forcing | None = None,
    record_every: int = 0,
) -> IntegrationResult:
    """Advance ``state`` for ``steps`` SSP-RK3 steps and return the result.

    Raises :class:`FloatingPointError` if the solution stops being finite, so an
    unstable configuration fails loudly instead of returning garbage.
    """
    if dt is None:
        dt = cfl_timestep(grid, p)

    state = apply_no_penetration(state.copy(), grid)
    initial = diagnostics(state, grid, p)
    history: list[dict[str, float]] = []

    for step in range(steps):
        state = rk3_step(state, grid, p, dt, t=step * dt, forcing=forcing)
        if not np.isfinite(state.eta).all():
            raise FloatingPointError(
                f"solution went non-finite at step {step}; reduce dt or raise diffusion"
            )
        if record_every and step % record_every == 0:
            history.append(diagnostics(state, grid, p))

    return IntegrationResult(
        state=state,
        dt=dt,
        steps=steps,
        initial=initial,
        final=diagnostics(state, grid, p),
        history=history,
    )
