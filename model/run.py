#!/usr/bin/env python3
"""Orchestrator for the offline flat-disc model pipeline.

    solve  ->  render (display PNG + Float32 probe .bin)  ->  emit (manifest.json)

This program is **offline and batch only**. It is never invoked in response to a
user request; a developer or CI job runs it to (re)generate the static asset
bundle that the website ships (CLAUDE.md, cardinal rule #1). Output lands in
``model/output/`` and is then copied into ``web/public/assets/model/`` for the
build.

Usage:
    python run.py                          # all six scenarios -> model/output/
    python run.py --scenario summer-orbit  # a single scenario
    python run.py --list                   # list scenarios and exit
    python run.py --frames 48              # more timesteps (bigger bundle)
    python run.py --output-dir /tmp/out    # override the output directory

The ``--list`` path imports only the standard library plus ``scenarios``; the
heavy pipeline (NumPy, the solver, the renderer) is imported lazily so the CLI
stays usable without the scientific stack.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import scenarios as scen

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Effective height-source rate of the spotlight sun [m/s]. Tuned so the warm
# anomaly builds to a few hundred metres and winds reach tens of m/s — the
# regime where the rim pile-up and (with Coriolis) the rim anticyclone show up.
HEATING_AMPLITUDE = 0.02


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Generate the planeoldweather static asset bundle (offline pipeline).",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        metavar="ID",
        help=(
            "scenario id to run (repeatable). Default: all six. "
            f"Valid ids: {', '.join(scen.SCENARIO_IDS)}"
        ),
    )
    parser.add_argument("--list", action="store_true", help="list the scenarios and exit")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="where to write the asset bundle (default: model/output/)",
    )
    parser.add_argument(
        "--grid-n", type=int, default=160, help="solver cells per side (default 160)"
    )
    parser.add_argument(
        "--frames", type=int, default=24, help="timesteps per scenario (default 24)"
    )
    parser.add_argument(
        "--display-size", type=int, default=512, help="display PNG size (default 512)"
    )
    parser.add_argument("--probe-size", type=int, default=96, help="probe grid size (default 96)")
    parser.add_argument(
        "--spinup-steps",
        type=int,
        default=300,
        help="solver spin-up steps before recording (default 300)",
    )
    parser.add_argument("--no-archive", action="store_true", help="skip the NetCDF archival files")
    return parser.parse_args(argv)


def print_scenario_list() -> None:
    print("Canonical scenarios (ARCHITECTURE.md §3.1):\n")
    width = max(len(s.id) for s in scen.SCENARIOS.values())
    for s in scen.SCENARIOS.values():
        kind = "" if s.kind == "solved" else f"  [{s.kind}]"
        print(f"  {s.id:<{width}}  {s.label}{kind}")
        print(f"  {'':<{width}}    {s.teaching_point}")
    print()


def resolve_scenarios(requested: list[str] | None) -> list[scen.Scenario]:
    if not requested:
        return list(scen.SCENARIOS.values())
    # Validate every id up front so a typo fails fast with a helpful message.
    return [scen.get(sid) for sid in requested]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.list:
        print_scenario_list()
        return 0

    try:
        selected = resolve_scenarios(args.scenarios)
    except KeyError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    # Lazy: keep the --list/--help paths free of the scientific stack.
    from render import emit_scenario, validate_manifest, write_manifest

    out = args.output_dir
    print(f"planeoldweather model pipeline -> {out}")
    print(f"scenarios: {', '.join(s.id for s in selected)}")
    print(
        f"grid_n={args.grid_n} frames={args.frames} display={args.display_size} probe={args.probe_size}\n"
    )

    entries = []
    for s in selected:
        entry = emit_scenario(
            s,
            out,
            grid_n=args.grid_n,
            frames=args.frames,
            display_size=args.display_size,
            probe_size=args.probe_size,
            spinup_steps=args.spinup_steps,
            heating_amplitude=HEATING_AMPLITUDE,
            archive=not args.no_archive,
        )
        tag = f"  [{s.id}] {entry['timesteps']} frames x {len(entry['variables'])} vars"
        tag += f"  ({entry['source']})" if "source" in entry else ""
        print(tag)

        entries.append(entry)

    manifest_path = out / "manifest.json"
    write_manifest(
        entries, manifest_path, disc_radius_km=scen.DISC_RADIUS_KM, display_size=args.display_size
    )

    import json

    issues = validate_manifest(json.loads(manifest_path.read_text()), out)
    print(f"\nmanifest: {manifest_path}")
    if issues:
        print(f"VALIDATION FAILED ({len(issues)} issue(s)):")
        for issue in issues[:10]:
            print(f"  - {issue}")
        return 1
    print(f"manifest valid: {len(entries)} scenario(s), bundle in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
