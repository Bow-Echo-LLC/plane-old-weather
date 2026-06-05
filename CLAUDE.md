<!-- Read automatically by Claude Code at the start of each session. Provides project context, guardrails, and working conventions to the AI assistant. -->

# CLAUDE.md — planeoldweather.com

A free, **educational** website that builds a physically-grounded "flat earth weather model" to teach real atmospheric science by demonstrating, quantifiably, what breaks when spherical geometry is replaced with a flat disc. The flat-earth framing is the hook; the payload is genuine geophysics. The canonical design spec is `docs/ARCHITECTURE.md` — **read it before starting any build phase.** (It is the `planeoldweather-canonical-spec` artifact.)

Monorepo with two subsystems: `model/` (offline Python simulation pipeline) and `web/` (Astro static site with React islands). They are joined only by a static asset bundle the model produces and the site consumes.

## Cardinal rules — do not violate

1. **The model is offline and deterministic. Production is static files only.** Never introduce an application server, database, backend API, job queue, or any per-request compute into the deployed site. The simulation is computed ahead of time; the site serves pre-rendered assets. This is the architecture, not a temporary state.
2. **Static output only.** An Astro static build is the target; never pick a setup that needs a running Node server in production. Cloudflare Pages serves files; nothing else runs.
3. **The viewer is manifest-driven.** Read `assets/model/manifest.json` for scenarios, variables, paths, value ranges, and colormaps. Never hard-code asset paths or frame counts in the viewer.
4. **Accessibility and graceful degradation are requirements, not polish.** Every interactive island honors `prefers-reduced-motion` (static fallback) and survives missing WebGL (static hero image, Canvas2D field fallback). Field images need alt text; viewer controls must be keyboard-operable.
5. **Scientific integrity is non-negotiable.** The site states plainly that Earth is an oblate spheroid. The model's value is that it fails in specific, defensible ways. The standing disclaimer appears in the hero, footer, and methodology: *"The Earth is not flat. This is a physics thought experiment exploring what weather would look like if it were — and why that model fails."* Cite real concepts accurately (azimuthal-equidistant projection, geostrophic balance, f-plane approximation, no-penetration boundary conditions, Rayleigh damping).

## Decisions already settled — do not re-litigate

- **Frontend: Astro + React islands.** Not Next.js, not a plain React SPA. Astro ships zero JS by default; only the `DiscHero3D` and `ModelViewer` islands are React (so they can use react-three-fiber + drei) and hydrated.
- **Six scenarios:** `summer-orbit`, `winter-orbit`, `no-coriolis`, `f-plane-dome`, `dome-absorbing`, `sphere-reference`. `sphere-reference` powers the disc-vs-sphere compare and the falsification narrative; `dome-absorbing` is the thermodynamic-catastrophe case.
- **Field data: display PNG + Float32 probe `.bin` is the baseline.** The RG16-packed-PNG + colormap-shader approach is a sanctioned *future* enhancement only (for client-side colormap switching) — do not make it the baseline, and don't add any other format without reason.
- **Hosting: Cloudflare Pages** (static hosting on the existing Cloudflare account; `planeoldweather.com` is already on Cloudflare). Cloudflare R2 / Object Storage is the scaling path for the model bundle, not the launch setup.

## Repository layout

```
model/      Python offline pipeline → emits the asset bundle (see model/CLAUDE.md if present)
  solver/ forcing/ boundary/ reference/ render/ scenarios.py run.py
web/        Astro site (see web/CLAUDE.md if present)
  src/{pages,content,components,lib,styles}
  public/assets/model/   ← the pre-computed bundle the build ships
deploy/     Cloudflare Pages deploy runbook
docs/        ARCHITECTURE.md (the design authority)
```

## Commands

Model pipeline (regenerate the asset bundle — occasional, not per-deploy):
```
cd model && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python run.py                          # all six scenarios → model/output/
python run.py --scenario summer-orbit  # single scenario
```
Output is then synced into `web/public/assets/model/` (run.py writes there directly).

Web (the day-to-day work):
```
cd web && npm install
npm run dev       # Astro dev server
npm run build     # static build → web/dist/ (includes the asset bundle)
npm run preview   # serve the production build locally
```

Quality gates (run before committing):
```
cd model && ruff check . && pytest            # Python
cd web && npm run lint && npm run typecheck    # site
```

Deploy (Cloudflare Pages — see `deploy/cloudflare-pages.md`):
```
cd web && npm run build && npx wrangler pages deploy dist --project-name=plane-old-weather
```
(Or just push to `main` once the Pages Git integration is connected — it builds and deploys automatically.)

## Tech stack

- Model: Python 3.11+, NumPy, SciPy, Numba (inner loop), Pillow/Matplotlib (PNG render), xarray + netCDF4 (archival + ERA5 ingest).
- Site: Astro (islands architecture) + React for the islands, MDX for content. Lenis (smooth scroll), GSAP + ScrollTrigger (scroll animation), Three.js via react-three-fiber + drei (3D disc hero), plain WebGL or `regl` (model viewer field + wind particle advection).
- Ops: **Cloudflare Pages** (static hosting + global CDN + automatic SSL), Cloudflare (DNS), GitHub (CI quality gates via Actions; Pages Git integration for auto-deploy).

## Conventions

- **Static-first.** The site is ~90% content; JavaScript is confined to the interactive islands (`DiscHero3D`, `ModelViewer`). Hydrate narrowly (`client:visible` over `client:load` wherever possible). Never put JS on the critical render path.
- **One persistent canvas.** The 3D scene is a single WebGL/three.js canvas behind the content; sections animate the camera and toggle visibility. Never mount a new canvas per section — that is the classic perf-killer for this kind of site.
- **Asset bundle = two representations per frame.** Each (scenario, variable, timestep) is a display PNG (color-mapped on the disc) plus a downsampled Float32 probe grid; all timesteps for a (scenario, variable) are packed into one `.bin` the client slices.
- **Model code is pedagogical.** Transparency and readability are goals in themselves — the solver is part of the lesson. Keep it well-commented and free of clever obscurity.
- **Content in MDX** under `web/src/content/`. The narrative arc is fixed (spec §5.3) — discuss before reordering.
- **Sentence case** in UI copy and headings. Formatting is enforced by linters (ruff/prettier) — do not hand-format what they own.
- **Read the `frontend-design` skill before any UI/styling work** (build Phases 4–6). It defines the design tokens and the non-generic aesthetic this build needs.

## Known gotchas

- **Use the Cartesian-grid-with-disc-mask, not a polar mesh.** A regular `(r, θ)` mesh oversamples and breaks at `r=0`. The masked-Cartesian approach (spec §4.1) is the chosen starting point; a polar mesh with a pole-averaging stencil is a later refinement, not a first pass.
- **Coriolis:** `f = 0` is the baseline geometry and the `no-coriolis` scenario; `f = 2Ω` (constant) is used *only* for `f-plane-dome`. Never use the spherical `f = 2Ω·sinφ` — that geometry does not exist on the disc.
- **Numerical stability.** The solver needs adequate diffusion/friction and a CFL-respecting timestep (`dt < dx/√(gH)`), or runs blow up. Get one scenario integrating to completion before adding scenarios.
- **Expected outputs, not bugs.** The rim anticyclone, standing-wave resonance, and corner turbulence are the *point* — they are the falsification. Do not "fix" them away.
- **`reference/era5_reproject.py` is high-stakes.** The entire falsification narrative leans on the disc-vs-sphere comparison, so the ERA5-climatology reprojection onto the azimuthal disc must be correct.
- **Large binary assets.** PNG frame sequences and probe blobs are sizeable. Lazy-load frames in the viewer (prefetch neighbors of the current timestep), set long cache headers on hashed/bundle assets, and never block first paint on them.

## Workflow

- **Model regeneration is a separate, occasional step**, not part of normal deploys. The output rarely changes. When it does: run the pipeline, commit the regenerated bundle, then the standard deploy ships it. CI builds and deploys the *site*; it does not run the model.
- Build phase by phase (spec §8), **model subsystem first**. Each phase is independently verifiable — confirm the stated definition of done before moving on.
- If subsystem detail grows, put it in `model/CLAUDE.md` / `web/CLAUDE.md` (auto-loaded when working in those directories) rather than bloating this root file.
- Use `CLAUDE.local.md` (git-ignored) for personal/sprint-specific notes — never commit machine-specific or transient context here.

## Never do

- Add a backend service, database, or live model computation to the production site.
- Hard-code asset paths, frame counts, or value ranges in the viewer (read the manifest).
- Ship an interactive island without a reduced-motion and a no-WebGL fallback.
- Imply the Earth is actually flat, or drop the scientific disclaimers anywhere in the content.
- Commit large regenerated model output without a deliberate "model changed" reason in the commit.
