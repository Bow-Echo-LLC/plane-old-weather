"""Field -> downsampled Float32 probe grid, packed per (scenario, variable) (spec §3.2).

The probe grid holds the raw field values for hover-readouts and GPU wind-particle
advection. All timesteps for a given (scenario, variable) are packed into ONE
little-endian Float32 ``.bin`` blob, C-order ``(timestep, row, col)``, so the
client makes a single request and slices frame ``i`` at byte offset
``i * grid_w * grid_h * 4``. Off-disc cells are stored as NaN so the client knows
where there is no readout.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import zoom

from solver.grid import DiscGrid


def downsample(field: np.ndarray, grid: DiscGrid, probe_size: int) -> np.ndarray:
    """Bilinearly downsample ``field`` to ``(probe_size, probe_size)`` Float32,
    with off-disc cells set to NaN."""
    factor = probe_size / grid.n
    coarse = zoom(field, factor, order=1)
    coarse_mask = zoom(grid.mask.astype(np.float64), factor, order=1) > 0.5
    return np.where(coarse_mask, coarse, np.nan).astype("<f4")


def pack_blob(frames: list[np.ndarray], out_path: Path) -> tuple[int, int, int]:
    """Concatenate per-timestep probe grids into one little-endian Float32 blob.

    Returns ``(timesteps, height, width)``. Each frame must already be
    ``(probe_size, probe_size)`` Float32.
    """
    stack = np.stack(frames).astype("<f4")  # (T, H, W), C-order
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(stack.tobytes(order="C"))
    return stack.shape
