"""Reproject a real-Earth climatology onto the azimuthal-equidistant disc to
build the ``sphere-reference`` scenario (spec §4.4).

This is the high-stakes module: the whole falsification narrative leans on the
disc-vs-sphere comparison, so the projection must be correct (CLAUDE.md). The
projection is the **north-polar azimuthal-equidistant** mapping (the UN-logo
projection): the North Pole sits at the disc centre and distance from the pole
(colatitude) maps linearly to disc radius, so latitude circles become concentric
rings —

    colatitude = 180 deg * (r / R)
    latitude   = 90 deg - colatitude
    longitude  = atan2(y, x)

The CLIMATOLOGY fed through it here is a **synthetic, clearly-labelled Earth-like
stand-in** (a smooth zonal profile: warm equator, cold poles, midlatitude
westerlies, an equatorial rain band). Real ERA5 ingestion is a separate
data step (it needs CDS credentials and a sizeable download); swapping the real
field into :func:`synthetic_climatology` is all that changes — the projection is
already correct. The synthetic origin is recorded in the manifest
(``"source": "synthetic-earthlike-placeholder"``) so the site can say so plainly.

The point of the reference is the contrast: the sphere's *static latitudinal
bands* versus the disc's moving bull's-eye, rim anticyclone, and standing waves.
"""

from __future__ import annotations

import numpy as np

from solver.grid import DiscGrid

SOURCE = "synthetic-earthlike-placeholder"


def disc_to_latlon(grid: DiscGrid) -> tuple[np.ndarray, np.ndarray]:
    """Invert the north-polar azimuthal-equidistant projection: disc (x, y) ->
    (latitude, longitude) in degrees."""
    colatitude = 180.0 * (grid.R / grid.radius_m)
    latitude = 90.0 - colatitude
    longitude = np.degrees(np.arctan2(grid.Y, grid.X))
    return latitude, longitude


def synthetic_climatology(latitude: np.ndarray) -> dict[str, np.ndarray]:
    """A smooth, zonal (longitude-independent), Earth-like climatology.

    Placeholder for real ERA5 — physically sensible bands, not measured data.
    """
    phi = np.radians(latitude)
    return {
        # Warm equator (~288 K), cold poles (~243 K): the real latitudinal gradient.
        "temperature": 288.0 - 45.0 * np.sin(phi) ** 2,
        # Crude pressure bands (equatorial/​subpolar lows, subtropical/​polar highs).
        "pressure": 1013.0 + 10.0 * np.cos(np.radians(3.0 * latitude)),
        # Midlatitude westerlies / tropical easterlies (zonal wind, m/s).
        "zonal_wind": 20.0 * np.sin(2.0 * phi),
        # An equatorial rain band (ITCZ), mm/hr.
        "precipitation": 14.0 * np.exp(-((latitude / 12.0) ** 2)),
    }


def reproject_to_disc(grid: DiscGrid) -> dict[str, np.ndarray]:
    """Build the sphere-reference display fields on the disc grid.

    Returns the same keys as :func:`render.fields.derive_fields` so the reference
    renders through the identical path: temperature, pressure, wind (speed),
    precipitation, and the wind components ``wind_u``/``wind_v``.
    """
    latitude, _ = disc_to_latlon(grid)
    clim = synthetic_climatology(latitude)

    # Zonal wind -> disc components. The eastward unit vector at (x, y) is the
    # tangential direction (-y/r, x/r); undefined at the centre, so guard r = 0.
    r = np.where(grid.R > 0.0, grid.R, 1.0)
    east_x, east_y = -grid.Y / r, grid.X / r
    u = clim["zonal_wind"] * east_x
    v = clim["zonal_wind"] * east_y

    return {
        "temperature": clim["temperature"],
        "pressure": clim["pressure"],
        "wind": np.hypot(u, v),
        "precipitation": clim["precipitation"],
        "wind_u": u,
        "wind_v": v,
    }
