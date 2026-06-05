"""Field -> azimuthal-disc display PNG with a transparent background (spec §3.2).

One colour-mapped PNG per (scenario, variable, timestep), fixed dimensions,
colormap baked in. Cells outside the disc mask are fully transparent. These
images need alt text on the site (CLAUDE.md, accessibility rule).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from solver.grid import DiscGrid

from .colormaps import apply_colormap


def render_disc_png(
    field: np.ndarray,
    grid: DiscGrid,
    out_path: Path,
    *,
    colormap: str,
    value_range: tuple[float, float],
    size: int = 1024,
) -> None:
    """Render ``field`` to a transparent-background display PNG at ``size``x``size``."""
    vmin, vmax = value_range
    norm = (field - vmin) / (vmax - vmin)
    rgba = apply_colormap(norm, colormap)
    rgba[~grid.mask] = 0  # off-disc pixels fully transparent (incl. alpha)

    # Image row 0 is the top; +y is physically up, so flip rows so north is up.
    img = Image.fromarray(np.flipud(rgba), mode="RGBA")
    if img.size != (size, size):
        # Bilinear gives a smooth disc edge (alpha feathered at the rim).
        img = img.resize((size, size), Image.BILINEAR)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, optimize=True)
