"""Write and validate the asset-bundle ``manifest.json`` (spec §3.4).

A single manifest at the asset root describes every scenario, variable, frame
path template, probe-blob path, grid size, value range, units, and colormap,
plus the disc geometry. The viewer reads ONLY the manifest and never hard-codes
paths, frame counts, or value ranges (CLAUDE.md, cardinal rule #3).

Frame templates use the ``{i:04d}`` form, e.g.
``"summer-orbit/temperature/frame_{i:04d}.png"``.
"""

from __future__ import annotations

import json
from pathlib import Path

_FLOAT32_BYTES = 4


def write_manifest(
    scenarios: list[dict],
    out_path: Path,
    *,
    disc_radius_km: float,
    display_size: int,
) -> None:
    """Write ``manifest.json`` describing the produced asset bundle."""
    manifest = {
        "scenarios": scenarios,
        "disc": {"radius_km": disc_radius_km, "center": "north_pole"},
        "display_size": display_size,
        "format": "display-png + float32-probe-bin (ARCHITECTURE.md §3.2)",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n")


def _check_blob(
    base_dir: Path, rel: str, timesteps: int, w: int, h: int, issues: list[str]
) -> None:
    blob = base_dir / rel
    if not blob.exists():
        issues.append(f"missing probe blob: {rel}")
        return
    expected = timesteps * w * h * _FLOAT32_BYTES
    actual = blob.stat().st_size
    if actual != expected:
        issues.append(f"{rel}: size {actual} != expected {expected} ({timesteps}x{w}x{h} f32)")


def validate_manifest(manifest: dict, base_dir: Path) -> list[str]:
    """Return a list of problems with the bundle under ``base_dir`` (empty = valid).

    Checks that every frame PNG exists and every probe blob has exactly
    ``timesteps * w * h * 4`` bytes (and likewise for wind component blobs).
    """
    issues: list[str] = []
    if "disc" not in manifest or "scenarios" not in manifest:
        issues.append("manifest missing 'disc' or 'scenarios'")
        return issues

    for sc in manifest["scenarios"]:
        steps = sc["timesteps"]
        for var, meta in sc["variables"].items():
            w, h = meta["grid_size"]
            for i in range(steps):
                frame = base_dir / meta["frames"].format(i=i)
                if not frame.exists():
                    issues.append(f"{sc['id']}/{var}: missing frame {frame.name}")
                    break  # one report per variable is enough
            _check_blob(base_dir, meta["probe_blob"], steps, w, h, issues)
            for comp_rel in meta.get("components", {}).values():
                _check_blob(base_dir, comp_rel, steps, w, h, issues)
    return issues
