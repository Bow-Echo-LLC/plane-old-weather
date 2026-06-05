"""Solar forcing: the moving 'spotlight sun' thermal source (spec §4.2)."""

from __future__ import annotations

from .spotlight_sun import (
    DAY_SECONDS,
    SpotlightForcing,
    insolation,
    subsolar_point,
)

__all__ = ["DAY_SECONDS", "SpotlightForcing", "insolation", "subsolar_point"]
