"""Colormaps for the display PNGs (spec §3.2).

The colormap is baked into the display PNG at render time. Each variable has a
fixed colormap and a fixed *global* value range (render/fields.py) so colours are
comparable across all timesteps and scenarios (spec §3.2, §4.4). We only use
Matplotlib here for its colormap lookup tables — no figures — so it stays fast.
"""

from __future__ import annotations

import matplotlib
import numpy as np

# Variable -> colormap name, kept here so the renderer and manifest agree.
DEFAULT_COLORMAPS: dict[str, str] = {
    "temperature": "inferno",
    "pressure": "RdBu_r",
    "wind": "cividis",
    "precipitation": "Blues",
}


def apply_colormap(normalized: np.ndarray, name: str) -> np.ndarray:
    """Map a ``[0, 1]``-normalised field to an ``(H, W, 4)`` uint8 RGBA array.

    Values are clipped to ``[0, 1]``; the caller is responsible for masking
    off-disc pixels (set their alpha to 0) after colouring.
    """
    cmap = matplotlib.colormaps[name]
    return cmap(np.clip(normalized, 0.0, 1.0), bytes=True)
