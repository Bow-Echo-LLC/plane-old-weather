# model/ — offline simulation pipeline

Subsystem notes for working in `model/`. The root `CLAUDE.md` and
`docs/ARCHITECTURE.md` (§4) are authoritative; this only adds local detail.

## Invariants
- **Offline & deterministic.** Nothing here runs in production. `run.py`
  (re)generates the static asset bundle; a developer or CI runs it occasionally.
- **`run.py`'s no-op/list path imports only the standard library** (plus
  `scenarios`, also stdlib-only). Keep it that way so the CLI works before the
  scientific stack is installed. Heavy imports (NumPy, etc.) belong inside the
  solve/render functions, imported lazily.
- **Masked Cartesian grid, not a polar mesh** (spec §4.1). A regular grid with
  `x²+y² > R²` cells inactive avoids the `r=0` singularity. Polar is a later
  refinement.
- **Coriolis:** `f = 0` baseline and for `no-coriolis`; constant `F_PLANE = 2Ω`
  only for `f-plane-dome`. Never the spherical `f = 2Ω·sinφ` (see
  `scenarios.py`).
- **Stability:** respect CFL (`dt < dx/√(gH)`) and include enough
  diffusion/friction. Get one scenario integrating to completion before adding
  more.
- **Expected outputs, not bugs:** the rim anticyclone, standing-wave resonance,
  and corner turbulence are the falsification — do not "fix" them away.
- `reference/era5_reproject.py` is high-stakes: the disc-vs-sphere comparison
  depends on a correct azimuthal-equidistant reprojection.

## Layout
`solver/` (grid, dynamics, thermodynamics, integrate) · `forcing/`
(spotlight_sun) · `boundary/` (ice_wall, dome) · `reference/` (era5_reproject) ·
`render/` (colormaps, to_png, to_grid, manifest) · `scenarios.py` · `run.py`.
Output: `model/output/` (intermediate, git-ignored) → copied to
`web/public/assets/model/` (the committed bundle).

## Commands
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # add -optional.txt for Numba
python run.py --list                   # scenarios
python run.py                          # all six (Phase 0: no-op)
ruff check . && pytest                 # quality gates
```
