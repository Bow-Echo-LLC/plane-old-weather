"""Phase 3 verification — render primitives: display PNGs and packed Float32
probe blobs (ARCHITECTURE.md §3.2)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

import scenarios as scen
from render.colormaps import apply_colormap
from render.to_grid import downsample, pack_blob
from render.to_png import render_disc_png
from solver import build_disc_grid


@pytest.fixture(scope="module")
def grid():
    return build_disc_grid(48, scen.DISC_RADIUS_KM)


def test_apply_colormap_returns_rgba_uint8():
    norm = np.linspace(0.0, 1.0, 16).reshape(4, 4)
    rgba = apply_colormap(norm, "inferno")
    assert rgba.shape == (4, 4, 4)
    assert rgba.dtype == np.uint8


def test_downsample_shape_and_offdisc_nan(grid):
    probe = downsample(grid.X, grid, 24)
    assert probe.shape == (24, 24)
    assert probe.dtype == np.float32
    assert np.isnan(probe[0, 0])  # corner is outside the disc
    assert np.isfinite(probe[12, 12])  # centre is inside


def test_pack_blob_roundtrip(grid, tmp_path):
    frames = [downsample(grid.X, grid, 16), downsample(grid.Y, grid, 16)]
    shape = pack_blob(frames, tmp_path / "g.bin")
    assert shape == (2, 16, 16)
    buf = np.fromfile(tmp_path / "g.bin", dtype="<f4")
    assert buf.size == 2 * 16 * 16
    # Slice frame 1 by offset, as the client will (NaNs compare equal here).
    frame1 = buf[16 * 16 : 2 * 16 * 16].reshape(16, 16)
    np.testing.assert_array_equal(frame1, frames[1])


def test_render_disc_png_dims_and_transparency(grid, tmp_path):
    out = tmp_path / "f.png"
    render_disc_png(
        grid.X,
        grid,
        out,
        colormap="viridis",
        value_range=(float(grid.X.min()), float(grid.X.max())),
        size=64,
    )
    img = Image.open(out)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"
    alpha = np.array(img)[:, :, 3]
    assert alpha[0, 0] == 0  # corner (off-disc) fully transparent
    assert alpha[32, 32] > 0  # centre opaque
