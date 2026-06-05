"""Asset-bundle emission: solve -> derive variables -> render -> pack -> archive
(spec §3, §4.4). Orchestrated per scenario; ``run.py`` drives all six and writes
the top-level manifest.

For a solved scenario the solver is spun up from rest, then ``frames`` snapshots
are recorded over one diurnal cycle and each is diagnosed into the display
variables (render/fields.py). The sphere-reference instead reprojects an
Earth-like climatology (reference/era5_reproject.py) into a single static frame.
Both then go through the identical render path: a display PNG and a downsampled
Float32 probe grid per (variable, frame), packed into one ``.bin`` per variable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

import scenarios as scen
from forcing import DAY_SECONDS, SpotlightForcing
from reference.era5_reproject import SOURCE, reproject_to_disc
from solver import (
    DiscGrid,
    Params,
    build_disc_grid,
    cfl_timestep,
    rest_state,
    rk3_step,
)

from .fields import DISPLAY_VARIABLES, VARIABLE_SPECS, derive_fields
from .to_grid import downsample, pack_blob
from .to_png import render_disc_png


def simulate_frames(
    grid: DiscGrid,
    params: Params,
    forcing: SpotlightForcing,
    *,
    spinup_steps: int,
    frames: int,
    steps_per_frame: int,
) -> tuple[list[float], list]:
    """Spin up from rest, then record ``frames`` (time, State) snapshots."""
    from solver.state import State  # local import keeps the public surface small

    dt = cfl_timestep(grid, params)
    state: State = rest_state(grid)
    t = 0.0
    for _ in range(spinup_steps):
        state = rk3_step(state, grid, params, dt, t=t, forcing=forcing)
        t += dt

    times: list[float] = []
    snapshots: list[State] = []
    for _ in range(frames):
        times.append(t)
        snapshots.append(state.copy())
        for _ in range(steps_per_frame):
            state = rk3_step(state, grid, params, dt, t=t, forcing=forcing)
            t += dt
    return times, snapshots


def _hhmm(i: int, frames: int) -> str:
    frac_hours = 24.0 * i / frames
    return f"{int(frac_hours) % 24:02d}:{int(frac_hours % 1 * 60):02d}"


def _write_netcdf(path: Path, grid: DiscGrid, times: list[float], frame_fields: list[dict]) -> None:
    """Archival full-field NetCDF for the 'download the raw data' link (spec §3.3)."""
    names = [*DISPLAY_VARIABLES, "wind_u", "wind_v"]
    data = {
        name: (("time", "y", "x"), np.stack([ff[name] for ff in frame_fields]).astype("f4"))
        for name in names
    }
    ds = xr.Dataset(
        data,
        coords={"time": np.asarray(times, dtype="f8"), "x": grid.x / 1000.0, "y": grid.y / 1000.0},
    )
    ds["mask"] = (("y", "x"), grid.mask)
    ds.x.attrs.update(units="km", long_name="disc x")
    ds.y.attrs.update(units="km", long_name="disc y")
    for var in DISPLAY_VARIABLES:
        ds[var].attrs["units"] = VARIABLE_SPECS[var]["units"]
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = {name: {"zlib": True, "complevel": 4} for name in ds.data_vars}
    ds.to_netcdf(path, encoding=encoding)


def emit_scenario(
    scenario: scen.Scenario,
    output_dir: Path,
    *,
    grid_n: int,
    frames: int,
    display_size: int,
    probe_size: int,
    spinup_steps: int,
    heating_amplitude: float,
    archive: bool = True,
) -> dict:
    """Produce one scenario's bundle and return its manifest entry."""
    grid = build_disc_grid(grid_n, scen.DISC_RADIUS_KM)

    if scenario.kind == "reference":
        frame_fields = [reproject_to_disc(grid)]
        times = [0.0]
        time_labels = ["climatology"]
    else:
        forcing = SpotlightForcing(
            orbit_radius_m=scenario.sun_orbit_radius_km * 1_000.0,
            altitude_m=scen.SUN_ALTITUDE_KM * 1_000.0,
            amplitude=heating_amplitude,
            period_s=DAY_SECONDS,
            dome_mode=scenario.dome,
        )
        params = Params(f=scenario.coriolis_f)
        dt = cfl_timestep(grid, params)
        steps_per_frame = max(1, round(DAY_SECONDS / dt / frames))
        times, snapshots = simulate_frames(
            grid,
            params,
            forcing,
            spinup_steps=spinup_steps,
            frames=frames,
            steps_per_frame=steps_per_frame,
        )
        frame_fields = [
            derive_fields(s, grid, t, forcing) for t, s in zip(times, snapshots, strict=True)
        ]
        time_labels = [_hhmm(i, frames) for i in range(frames)]

    sid = scenario.id
    n_frames = len(frame_fields)
    probe_acc: dict[str, list[np.ndarray]] = {
        name: [] for name in (*DISPLAY_VARIABLES, "wind_u", "wind_v")
    }

    for i, ff in enumerate(frame_fields):
        for var in DISPLAY_VARIABLES:
            spec = VARIABLE_SPECS[var]
            render_disc_png(
                ff[var],
                grid,
                output_dir / sid / var / f"frame_{i:04d}.png",
                colormap=spec["colormap"],
                value_range=spec["value_range"],
                size=display_size,
            )
        for name in (*DISPLAY_VARIABLES, "wind_u", "wind_v"):
            probe_acc[name].append(downsample(ff[name], grid, probe_size))

    for var in DISPLAY_VARIABLES:
        pack_blob(probe_acc[var], output_dir / sid / var / "grid.bin")
    pack_blob(probe_acc["wind_u"], output_dir / sid / "wind" / "u.bin")
    pack_blob(probe_acc["wind_v"], output_dir / sid / "wind" / "v.bin")

    if archive:
        _write_netcdf(output_dir / sid / "archive.nc", grid, times, frame_fields)

    variables: dict[str, dict] = {}
    for var in DISPLAY_VARIABLES:
        spec = VARIABLE_SPECS[var]
        entry = {
            "frames": f"{sid}/{var}/frame_{{i:04d}}.png",
            "probe_blob": f"{sid}/{var}/grid.bin",
            "grid_size": [probe_size, probe_size],
            "value_range": list(spec["value_range"]),
            "units": spec["units"],
            "colormap": spec["colormap"],
        }
        if var == "wind":
            entry["components"] = {"u": f"{sid}/wind/u.bin", "v": f"{sid}/wind/v.bin"}
        variables[var] = entry

    scenario_entry = {
        "id": sid,
        "label": scenario.label,
        "kind": scenario.kind,
        "timesteps": n_frames,
        "time_labels": time_labels,
        "variables": variables,
        "archive": f"{sid}/archive.nc" if archive else None,
    }
    if scenario.kind == "reference":
        scenario_entry["source"] = SOURCE
    return scenario_entry
