"""Boundary conditions: the ice wall (lateral rim) and the dome (top) (spec §4.3)."""

from __future__ import annotations

from .dome import cooling_sink
from .ice_wall import apply_no_penetration

__all__ = ["apply_no_penetration", "cooling_sink"]
