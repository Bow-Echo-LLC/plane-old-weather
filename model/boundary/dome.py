"""Dome (top) boundary / energy budget (spec §4.3).

For the 2-D model the dome is a closed-energy assumption (no radiative escape)
folded into the thermodynamics: a cooling sink balances the spotlight-sun
heating so a run reaches equilibrium instead of warming forever.

* **closed** — a spatially *uniform* sink equal to the mean heating. The net
  source then has zero spatial mean, so total mass is conserved exactly and the
  field settles into a moving dynamical equilibrium.
* **absorbing** — the cooling is *suppressed where the column is tall* (high
  ``eta`` ~ reaching the dome ceiling, where radiative escape is blocked). The
  sink is redistributed (not removed) toward the short/cool columns so it still
  balances the total heating — mass stays conserved — but the warm core runs
  away to a hotter, capped state (an inversion). This is the thermodynamic
  catastrophe the ``dome-absorbing`` scenario exists to show; it is an expected
  output, not a bug (CLAUDE.md).

If a vertical dimension is added later, Rayleigh damping near the ceiling would
absorb spurious wave reflection in place of the usual sponge layer.
"""

from __future__ import annotations

import numpy as np

from solver.grid import DiscGrid


def cooling_sink(
    heating: np.ndarray,
    eta: np.ndarray,
    grid: DiscGrid,
    *,
    mode: str = "closed",
    suppression: float = 0.7,
    eta_scale: float = 150.0,
) -> np.ndarray:
    """Cooling field that balances ``heating`` over the disc (so the net source
    is mass-neutral). ``mode`` selects the closed (uniform) or absorbing
    (tall-column-suppressed) dome."""
    total_heating = float(heating.sum())

    if mode == "closed":
        # Uniform sink = mean heating; net source has zero spatial mean.
        mean_heating = total_heating / grid.active_count
        return mean_heating * grid.mask

    if mode == "absorbing":
        # Weight < 1 where eta is high (tall column near the ceiling -> blocked
        # escape -> less cooling). Renormalise so the total cooling still equals
        # the total heating, keeping the net source mass-neutral.
        weight = (1.0 - suppression * np.tanh(np.maximum(eta, 0.0) / eta_scale)) * grid.mask
        weight_sum = float(weight.sum())
        if weight_sum <= 0.0:
            return cooling_sink(heating, eta, grid, mode="closed")
        return (total_heating / weight_sum) * weight

    raise ValueError(f"unknown dome mode {mode!r}; expected 'closed' or 'absorbing'")
