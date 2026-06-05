"""Phase 3 verification — the end-to-end asset bundle (ARCHITECTURE.md §3, §8).

Definition of done: the full asset bundle is produced and the manifest
validates. This emits a tiny real bundle (a solved scenario + the reference) and
checks structure, the manifest, PNG dimensions, probe-blob byte sizes, and the
NetCDF archive.
"""

from __future__ import annotations

import json

from PIL import Image

import scenarios as scen
from render import emit_scenario, validate_manifest, write_manifest

GRID_N, FRAMES, DISPLAY, PROBE = 48, 3, 128, 32


def test_full_bundle_produced_and_manifest_validates(tmp_path):
    entries = [
        emit_scenario(
            scen.get(sid),
            tmp_path,
            grid_n=GRID_N,
            frames=FRAMES,
            display_size=DISPLAY,
            probe_size=PROBE,
            spinup_steps=10,
            heating_amplitude=0.02,
        )
        for sid in ("summer-orbit", "sphere-reference")
    ]
    manifest_path = tmp_path / "manifest.json"
    write_manifest(entries, manifest_path, disc_radius_km=scen.DISC_RADIUS_KM, display_size=DISPLAY)

    manifest = json.loads(manifest_path.read_text())
    assert validate_manifest(manifest, tmp_path) == []  # the headline check

    solved = manifest["scenarios"][0]
    assert solved["id"] == "summer-orbit"
    assert solved["timesteps"] == FRAMES
    assert set(solved["variables"]) == {"temperature", "pressure", "wind", "precipitation"}
    assert solved["variables"]["wind"]["components"].keys() == {"u", "v"}

    # Display PNGs render at the requested size with an alpha channel.
    img = Image.open(tmp_path / "summer-orbit" / "temperature" / "frame_0000.png")
    assert img.size == (DISPLAY, DISPLAY)
    assert img.mode == "RGBA"

    # Probe blob holds exactly frames x probe x probe float32 values.
    blob = tmp_path / "summer-orbit" / "temperature" / "grid.bin"
    assert blob.stat().st_size == FRAMES * PROBE * PROBE * 4

    # The reference is a single static, clearly-labelled climatology frame.
    reference = manifest["scenarios"][1]
    assert reference["timesteps"] == 1
    assert reference["source"] == "synthetic-earthlike-placeholder"

    # Archival NetCDF exists for the raw-data download.
    assert (tmp_path / "summer-orbit" / "archive.nc").exists()
