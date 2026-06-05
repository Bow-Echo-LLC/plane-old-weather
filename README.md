# planeoldweather.com

A free, **educational** website that builds a physically-grounded "flat
earth weather model" to teach real atmospheric science — by demonstrating,
quantifiably, what breaks when spherical geometry is replaced with a flat disc.
The flat-earth framing is the hook; the payload is genuine geophysics.

> **The Earth is not flat.** This is a physics thought experiment exploring what
> weather would look like if it were — and why that model fails.

## What this is

A monorepo with two decoupled subsystems joined only by a static asset bundle:

- **`model/`** — an offline, deterministic Python simulation pipeline. It solves
  a 2D shallow-water atmosphere on a disc (Cartesian grid masked to a disc),
  applies the moving "spotlight sun" forcing, enforces the ice-wall and dome
  boundary conditions, and renders web-ready assets (display PNGs + Float32
  probe `.bin` grids + a `manifest.json`). **It never runs in production.**
- **`web/`** — an [Astro](https://astro.build) static site with a few React
  islands (a 3D disc hero and an interactive model viewer). It ships pre-rendered
  HTML/CSS plus the pre-computed asset bundle. **Static files only; nothing
  else runs.**

The architecture is static-only by design: no application server, no database,
no per-request compute. See `docs/ARCHITECTURE.md` for the authoritative
design, and `CLAUDE.md` for the working rules.

## Repository layout

```
model/      Python offline pipeline → emits the asset bundle
  solver/ forcing/ boundary/ reference/ render/  scenarios.py  run.py
web/        Astro site (static build → web/dist/)
  src/{pages,layouts,content,components,lib,styles}
  public/assets/model/   ← the pre-computed bundle the build ships
deploy/     Cloudflare Pages deploy runbook
docs/       ARCHITECTURE.md (design authority — stack, data format, build phases, deployment)
.github/    CI (quality gates) + Cloudflare Pages deploy
```

## Quick start

### Model pipeline (regenerate the asset bundle — occasional, not per-deploy)

```bash
cd model
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py                          # all six scenarios → model/output/
python run.py --scenario summer-orbit  # a single scenario
python run.py --list                   # list scenarios and exit
```

### Web (the day-to-day work)

```bash
cd web
npm install
npm run dev       # Astro dev server
npm run build     # static build → web/dist/ (includes the asset bundle)
npm run preview   # serve the production build locally
```

### Quality gates (run before committing)

```bash
cd model && ruff check . && pytest
cd web   && npm run lint && npm run typecheck
```

## Scientific integrity

The site states plainly that Earth is an oblate spheroid. The model's value is
that it fails in specific, defensible ways (a persistent rim anticyclone,
standing-wave resonance, latitude-independent cyclone spin). Those failures are
the lesson, not bugs. Concepts are cited accurately (azimuthal-equidistant
projection, geostrophic balance, the f-plane approximation, no-penetration
boundary conditions, Rayleigh damping).

## Raw data

The site ships a viewer-sized asset bundle (color-mapped display PNGs +
downsampled Float32 probe `.bin` grids + `manifest.json`) under
`web/public/assets/model/`. The **full-resolution NetCDF** archives (one per
scenario, `temperature`/`pressure`/`wind`/`precipitation` on the solver grid over
the diurnal cycle) are not committed — they are large and reproducible. Generate
both with the offline pipeline:

```bash
cd model && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py                  # writes model/output/<scenario>/archive.nc + the bundle
```

The model is deterministic, so a regeneration reproduces the shipped fields
exactly. `sphere-reference` is an idealized Earth-like climatology, not measured
reanalysis (real ERA5 ingestion is a planned data step).

## License

Copyright © 2026 **Bow Echo LLC**. **Source-available, not open source.** The
code is under a custom source-available license: you may read, fork, modify, and
run it locally for personal, educational, and evaluation use, but **public
deployment — hosting it on an external domain or network — requires prior written
permission from Bow Echo LLC.** Written content and figures are licensed
**CC-BY-NC-4.0** (non-commercial, with attribution). See [`LICENSE`](./LICENSE)
for the full terms and the permission contact.
