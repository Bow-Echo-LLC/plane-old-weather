"""Canonical scenario definitions for the planeoldweather flat-disc model.

This is the single source of truth for *which* runs exist and the high-level
physical knobs that distinguish them (spec §3.1). It is intentionally pure
standard library — no NumPy — so that ``run.py`` can list and orchestrate
scenarios without importing the heavy scientific stack. The solver (Phase 1+)
consumes these configs; it does not redefine them.

The six scenarios are fixed (CLAUDE.md, "Decisions already settled"):

    summer-orbit, winter-orbit, no-coriolis, f-plane-dome,
    dome-absorbing, sphere-reference

``sphere-reference`` is not solved by our PDE — it is ERA5 climatology
reprojected onto the azimuthal-equidistant disc (see reference/era5_reproject.py)
and powers the disc-vs-sphere comparison and the falsification narrative.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Disc geometry shared by every scenario (spec §4.1) -----------------------
DISC_RADIUS_KM: float = 20_000.0
"""Physical radius of the flat disc; the ice wall sits at r = R."""

SUN_ALTITUDE_KM: float = 5_000.0
"""Height of the 'spotlight' sun above the disc; the ``h`` in the 1/(1+(d/h)^2)
insolation falloff (spec §4.2)."""

# Coriolis: f = 0 is the baseline disc geometry AND the no-coriolis scenario.
# f = 2*Omega (constant) is used ONLY for the rotating-dome f-plane. The
# spherical f = 2*Omega*sin(phi) is deliberately never used — that geometry does
# not exist on the disc (CLAUDE.md, "Known gotchas").
EARTH_OMEGA: float = 7.292_1e-5  # rad/s
F_PLANE: float = 2.0 * EARTH_OMEGA  # ~1.4584e-4 s^-1, constant everywhere on the disc


@dataclass(frozen=True)
class Scenario:
    """A single canonical run configuration.

    Attributes are seeds for the solver/forcing/boundary stages; Phase 0 only
    needs ``id``/``label``/``teaching_point`` for listing and orchestration.
    """

    id: str
    label: str
    teaching_point: str
    # "solved"   -> integrated by our shallow-water solver
    # "reference"-> external reanalysis reprojected onto the disc (sphere-reference)
    kind: str = "solved"
    # Coriolis parameter f (1/s). 0.0 for the disc baseline; F_PLANE for f-plane-dome.
    coriolis_f: float = 0.0
    # Radius (km) of the circle the sub-solar point traces over a diurnal cycle:
    # tight = summer (warm ring near the pole), wide = winter (warm ring near rim).
    sun_orbit_radius_km: float = 7_000.0
    # Dome thermodynamics: "closed" (balanced cooling sink) or "absorbing"
    # (cooling sink suppressed near the ceiling -> runaway heating / inversion cap).
    dome: str = "closed"
    # Number of timesteps to export over one diurnal cycle (~spec suggests ~200).
    timesteps: int = 200


# Ordered so listings read in a teaching-friendly sequence.
SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in (
        Scenario(
            id="summer-orbit",
            label="Summer sun orbit",
            teaching_point="Spotlight sun on a tight inner orbit; the warm zone is a small ring near the pole.",
            sun_orbit_radius_km=3_000.0,
        ),
        Scenario(
            id="winter-orbit",
            label="Winter sun orbit",
            teaching_point="Spotlight sun on a wide outer orbit; the warm ring expands toward the rim.",
            sun_orbit_radius_km=12_000.0,
        ),
        Scenario(
            id="no-coriolis",
            label="No Coriolis (f = 0)",
            teaching_point="Pure gradient flow: cyclones converge but do not rotate. The cleanest 'this is wrong'.",
            coriolis_f=0.0,
        ),
        Scenario(
            id="f-plane-dome",
            label="Rotating-dome f-plane (uniform f)",
            teaching_point="Constant f everywhere: cyclones rotate, but at the same rate at every latitude — the key falsifier.",
            coriolis_f=F_PLANE,
        ),
        Scenario(
            id="dome-absorbing",
            label="Absorbing dome",
            teaching_point="Cooling sink suppressed near the ceiling: runaway heating and an inversion cap, with no stratosphere analogue.",
            dome="absorbing",
        ),
        Scenario(
            id="sphere-reference",
            label="Sphere reference (idealized)",
            teaching_point="The real-Earth control: an idealized climatology reprojected onto the disc (a stand-in for ERA5), for side-by-side comparison.",
            kind="reference",
        ),
    )
}

# Canonical ordering / membership guard used by run.py and the tests.
SCENARIO_IDS: tuple[str, ...] = tuple(SCENARIOS.keys())


def get(scenario_id: str) -> Scenario:
    """Return the scenario by id, or raise a helpful error listing valid ids."""
    try:
        return SCENARIOS[scenario_id]
    except KeyError:
        valid = ", ".join(SCENARIO_IDS)
        raise KeyError(f"unknown scenario {scenario_id!r}; valid ids: {valid}") from None
