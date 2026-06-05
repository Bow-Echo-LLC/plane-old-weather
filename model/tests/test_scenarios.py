"""Guards on the canonical scenario set (no heavy deps; runs on the scaffold).

These assert the invariants CLAUDE.md calls non-negotiable: the exact six
scenarios, and the Coriolis rule (f = 0 baseline; constant f only for the
f-plane; never spherical).
"""

from __future__ import annotations

import scenarios as scen

CANONICAL_IDS = {
    "summer-orbit",
    "winter-orbit",
    "no-coriolis",
    "f-plane-dome",
    "dome-absorbing",
    "sphere-reference",
}


def test_exactly_the_six_canonical_scenarios():
    assert set(scen.SCENARIO_IDS) == CANONICAL_IDS
    assert len(scen.SCENARIO_IDS) == 6


def test_coriolis_rule():
    # Baseline geometry and the no-coriolis scenario are f = 0.
    assert scen.get("no-coriolis").coriolis_f == 0.0
    assert scen.get("summer-orbit").coriolis_f == 0.0
    # Only the f-plane uses a non-zero, constant f (= 2*Omega).
    assert scen.get("f-plane-dome").coriolis_f == scen.F_PLANE
    assert scen.F_PLANE > 0.0


def test_reference_scenario_is_not_solved():
    assert scen.get("sphere-reference").kind == "reference"
    solved = [s for s in scen.SCENARIOS.values() if s.kind == "solved"]
    assert len(solved) == 5


def test_seasons_differ_by_sun_orbit_radius():
    # Tight orbit = summer (warm ring near pole); wide orbit = winter (near rim).
    assert (
        scen.get("summer-orbit").sun_orbit_radius_km < scen.get("winter-orbit").sun_orbit_radius_km
    )


def test_absorbing_dome_flagged():
    assert scen.get("dome-absorbing").dome == "absorbing"


def test_unknown_scenario_raises():
    import pytest

    with pytest.raises(KeyError):
        scen.get("flat-mars")
