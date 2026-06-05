"""Derive the viewer's display variables from the solver state (spec §3.2, §5.4).

The shallow-water solver carries ``eta`` (free-surface height) and the wind
``(u, v)``. The four variables the viewer toggles between — temperature,
pressure, wind, precipitation — are diagnosed from these plus the spotlight
forcing:

* **temperature** — the radiative-equilibrium temperature set by the spotlight
  insolation (the moving thermal bull's-eye). This is the thermal *forcing*
  pattern; the dynamical response shows up in the other fields. (The
  sphere-reference takes its temperature from the reprojected climatology
  instead.)
* **pressure** — a surface-pressure proxy linear in ``eta`` (tall column = high
  pressure). The dynamical highs/lows, rim band, and standing waves live here.
* **wind** — speed ``|u|`` for display; the raw ``u, v`` components are kept for
  the probe blobs that drive GPU particle advection.
* **precipitation** — diagnosed from low-level convergence ``max(0, -div(u))``:
  converging air rises and rains.

Value ranges are fixed and global so colours are comparable across every
timestep and scenario.
"""

from __future__ import annotations

import numpy as np

from solver.grid import DiscGrid
from solver.operators import gradient
from solver.state import State

# name -> manifest metadata. Order is the viewer's variable-toggle order.
VARIABLE_SPECS: dict[str, dict] = {
    "temperature": {"units": "K", "colormap": "inferno", "value_range": (240.0, 300.0)},
    "pressure": {"units": "hPa", "colormap": "RdBu_r", "value_range": (988.0, 1038.0)},
    "wind": {"units": "m/s", "colormap": "cividis", "value_range": (0.0, 40.0)},
    "precipitation": {"units": "mm/hr", "colormap": "Blues", "value_range": (0.0, 20.0)},
}
DISPLAY_VARIABLES: tuple[str, ...] = tuple(VARIABLE_SPECS)

# Diagnostic mappings from the shallow-water state to displayable units.
_TEMP_MIN, _TEMP_MAX = 240.0, 300.0  # K, spans the insolation falloff
_PRESSURE_REF = 1013.0  # hPa at eta = 0
_PRESSURE_PER_M = 0.035  # hPa per metre of eta
_PRECIP_SCALE = 3.0e5  # (mm/hr) per (1/s) of convergence


def _precipitation(u: np.ndarray, v: np.ndarray, grid: DiscGrid) -> np.ndarray:
    divergence = gradient(u, grid)[0] + gradient(v, grid)[1]
    return np.maximum(0.0, -divergence) * _PRECIP_SCALE


def derive_fields(state: State, grid: DiscGrid, t: float, forcing) -> dict[str, np.ndarray]:
    """Diagnose the display variables for a solved scenario at time ``t``.

    Returns the four display fields plus the raw wind components (``wind_u``,
    ``wind_v``) used for the wind probe blobs.
    """
    q_in = forcing.heating(grid, t)
    peak = forcing.amplitude if forcing.amplitude > 0 else 1.0
    temperature = _TEMP_MIN + (_TEMP_MAX - _TEMP_MIN) * np.clip(q_in / peak, 0.0, 1.0)

    return {
        "temperature": temperature,
        "pressure": _PRESSURE_REF + _PRESSURE_PER_M * state.eta,
        "wind": np.hypot(state.u, state.v),
        "precipitation": _precipitation(state.u, state.v, grid),
        "wind_u": state.u,
        "wind_v": state.v,
    }
