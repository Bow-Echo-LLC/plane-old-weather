"""Render stage: field -> display PNG + downsampled Float32 probe .bin, plus the
manifest the viewer reads (spec §3.2-3.4, §4.4).

Baseline format (CLAUDE.md, settled decision): a color-mapped display PNG per
(scenario, variable, timestep) plus one packed Float32 ``.bin`` per
(scenario, variable) that the client slices. The RG16-packed-PNG + colormap
shader is a sanctioned *future* enhancement only — not the baseline.
"""

from __future__ import annotations

from .fields import DISPLAY_VARIABLES, VARIABLE_SPECS, derive_fields
from .manifest import validate_manifest, write_manifest
from .pipeline import emit_scenario
from .to_grid import downsample, pack_blob
from .to_png import render_disc_png

__all__ = [
    "DISPLAY_VARIABLES",
    "VARIABLE_SPECS",
    "derive_fields",
    "emit_scenario",
    "render_disc_png",
    "downsample",
    "pack_blob",
    "write_manifest",
    "validate_manifest",
]
