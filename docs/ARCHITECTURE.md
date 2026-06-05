# planeoldweather.com — Canonical Architecture & Build Specification

> **Status:** Canonical and prescriptive — Claude Code can execute from it without further design decisions, while noting where alternatives are acceptable.

**Purpose:** A free, educational website that builds a physically-grounded "flat earth weather model" as a teaching tool. The site uses the model to demonstrate, rigorously, *what breaks* when you replace spherical geometry with a flat disc — turning a fringe claim into a genuine geophysics lesson.

**Audience:** Curious general public, students, educators. Tone: playful but scientifically honest. The flat-earth framing is the hook; the payload is real atmospheric science (projections, thermodynamics, geostrophic balance, boundary conditions, falsification).

**Standing disclaimer (hero + footer + methods):** *"The Earth is not flat. This is a physics thought experiment exploring what weather would look like if it were — and why that model fails."*

---

## 1. Guiding principles

1. **The model is fixed, not live.** The simulation is deterministic and educational. It is computed *offline* and its output shipped as static assets. There is no application server, no database, no per-request compute. This is the single most important architectural decision — it makes the site nearly free to host and trivial to operate.
2. **Static-first, interactive where it counts.** The site is ~90% content. Heavy JavaScript is confined to a small number of interactive "islands" (the 3D hero, the model viewer). Everything else ships as pre-rendered HTML/CSS.
3. **Premium feel, honest physics.** Scroll-based animation, smooth momentum scroll, and 3D parallax carry the narrative. Every visual claim maps to a defensible piece of atmospheric science, and the site is explicit that the Earth is an oblate spheroid.
4. **Graceful degradation.** WebGL-free fallbacks, `prefers-reduced-motion` support, and progressive asset loading are requirements, not afterthoughts.
5. **Source-available and reproducible.** The source is public to read, fork, and run locally; public deployment is reserved to Bow Echo LLC and requires prior written permission (the code is under a custom source-available license; written content and figures are CC-BY-NC-4.0 — see `LICENSE`). The full-resolution model output is downloadable; every cited concept is accurate enough for an instructor to use without correction.

---

## 2. Two subsystems

### 2.1 The model pipeline (offline / batch)
A Python program that solves a simplified 2D atmospheric model on a grid representing the flat disc, applies the "spotlight sun" forcing, enforces the ice-wall and dome boundary conditions, and renders the output to web-ready static assets. It **never runs in response to a user request** — a developer or CI job runs it to (re)generate the asset bundle, which is then committed/deployed with the site.

### 2.2 The web experience (the site)
An **Astro** static site delivering the educational narrative via scrollytelling, a Three.js 3D disc hero, and a WebGL interactive viewer that scrubs through the pre-computed model output. Builds to static files served by Cloudflare Pages.

---

## 3. The data: format and shape

**Decision:** pre-computed timeseries, served as static assets, displayed through an interactive viewer. Not live computation. Not flat static images. A hybrid that feels interactive but costs nothing to serve.

### 3.1 Canonical scenarios (six)
Each scenario is a full timeseries (suggested ~200 timesteps over one diurnal cycle of the spotlight sun).

| Scenario ID | Description | Teaching point |
|---|---|---|
| `summer-orbit` | Spotlight sun on a tight inner orbit | Warm zone is a small ring near the pole |
| `winter-orbit` | Spotlight sun on a wide outer orbit | Warm ring expands toward the rim |
| `no-coriolis` | Pure gradient flow, f = 0 | Cyclones converge but do not rotate |
| `f-plane-dome` | Rotating-dome f-plane, uniform f | Cyclones rotate at the same rate everywhere |
| `dome-absorbing` | Closed/absorbing dome; cooling sink suppressed near the ceiling | Runaway heating + inversion cap; no stratosphere analogue |
| `sphere-reference` | Equivalent real-Earth fields (ERA5 climatology, reprojected) | The control case for side-by-side comparison |

`sphere-reference` powers the "disc vs sphere" compare mode and is the backbone of the falsification narrative. `dome-absorbing` is the thermodynamic-catastrophe teaching case.

### 3.2 Per-frame output (two representations)
For every (scenario, variable, timestep):

1. **Display PNG** — the field color-mapped onto the azimuthal-equidistant disc, transparent background, fixed dimensions (suggested 1024×1024). Fast to display, looks good, no client-side math. The colormap is baked in.
2. **Probe grid** — a downsampled `Float32` array (suggested 128×128 or 256×256) of the raw field values, for hover-readouts and, for the wind field, GPU particle advection. Pack all timesteps for a given (scenario, variable) into a **single binary blob** (`.bin`) to minimize request count; the client slices it by offset.

Variables to export: `temperature`, `pressure`, `wind_u`, `wind_v` (magnitude/direction derived client-side), and optionally `precipitation`.

> **Optional enhancement (not baseline):** if client-side colormap switching is desired later, additionally encode the scalar field as a 16-bit value packed across the R+G channels of a PNG (RG16) and decode + colormap it in a fragment shader. This trades engineering effort for runtime flexibility. Ship the display-PNG + probe-grid model first; add this only if the feature is wanted.

### 3.3 Archival output + raw-data download
Keep full-resolution model output as NetCDF (`.nc`) for reproducibility and a public **"download the raw data"** link, satisfying the open/educational promise. This is not loaded by the viewer.

### 3.4 Manifest
A single `manifest.json` at the asset root describes everything the viewer needs; the viewer reads it and never hard-codes paths.

```json
{
  "scenarios": [
    {
      "id": "summer-orbit",
      "label": "Summer sun orbit",
      "timesteps": 200,
      "time_labels": ["00:00", "..."],
      "variables": {
        "temperature": {
          "frames": "summer-orbit/temperature/frame_{i:04d}.png",
          "probe_blob": "summer-orbit/temperature/grid.bin",
          "grid_size": [128, 128],
          "value_range": [220.0, 320.0],
          "units": "K",
          "colormap": "inferno"
        }
      }
    }
  ],
  "disc": { "radius_km": 20000, "center": "north_pole" }
}
```

---

## 4. The model pipeline — design

A custom finite-difference solver is appropriate here (over a heavyweight framework): the domain is simple, the educational value comes from transparency of the code, and the geometry is non-standard.

### 4.1 Governing equations
A 2D shallow-water / barotropic-style model. Momentum equation with a configurable Coriolis term so scenarios can toggle it:

```
∂u/∂t + (u·∇)u + f·(k̂ × u) = -(1/ρ)∇p + F
```

- `f = 0` for the non-rotating disc (`no-coriolis`, and the baseline geometry).
- `f = 2Ω` (constant) for the rotating-dome f-plane (`f-plane-dome`). Never use the spherical `f = 2Ω sinφ` — that geometry doesn't exist here.
- Pressure-gradient and advection terms are standard; `F` is friction/diffusion for numerical stability.

Solve on a **Cartesian grid masked to the disc** (cells with `x² + y² > R²` are inactive). This avoids the `r=0` coordinate singularity of a true polar mesh and is simpler to get right; recommended. Suggested `R ≈ 20,000 km`. Integrator: RK3 (preferred) or leapfrog with a Robert–Asselin filter; respect CFL (`dt < dx / √(gH)`).

### 4.2 Solar forcing — the spotlight sun
Insolation at each grid point is a function of distance from the sub-solar point, which moves in a circle over the diurnal cycle:

```
Q(x, y, t) = S0 / (1 + (d(x, y, t)/h)^2) · cos(α)
```

where `d` is horizontal distance from the sub-solar point, `h ≈ 5000 km` is the sun's altitude, and `α` is the local incidence angle. The sub-solar point traces a ring whose radius is set per scenario (tight = summer, wide = winter). This produces the "moving thermal bull's-eye" — the core thermodynamic difference from a sphere. Balance net heating with a uniform cooling sink so runs reach equilibrium (the `dome-absorbing` scenario deliberately suppresses this sink near the ceiling — see 4.3).

### 4.3 Boundary conditions
- **Ice wall (lateral, `r = R`):** no-penetration, `u·n̂ = 0`. Implement with a ghost-cell method — mirror the normal velocity component, leave the tangential component free. Pressure gets a zero-normal-gradient (Neumann) condition, `∂p/∂n = 0`.
- **Dome (top):** for the 2D model the dome is a closed-energy assumption (no radiative escape) folded into the thermodynamics. The `dome-absorbing` scenario models the absorbing case (reduced cooling near the ceiling → runaway heating / inversion cap). If a vertical dimension is added later, add Rayleigh damping near the ceiling to absorb spurious wave reflection in place of the usual sponge layer.

These boundaries are *why* the model produces a persistent rim anticyclone, standing-wave resonance, and corner turbulence — all absent from real observations, and therefore the heart of the falsification story.

### 4.4 Pipeline modules
```
model/
├── solver/
│   ├── grid.py            # Cartesian-with-disc-mask grid; polar helpers
│   ├── dynamics.py        # advection + pressure gradient + configurable Coriolis
│   ├── thermodynamics.py  # energy balance, closed-dome assumption
│   └── integrate.py       # timestepping (RK3 or leapfrog) + stability/diffusion
├── forcing/
│   └── spotlight_sun.py   # Q(x,y,t), moving sub-solar point per scenario
├── boundary/
│   ├── ice_wall.py        # ghost-cell no-penetration + Neumann pressure
│   └── dome.py            # closed-energy; absorbing variant; optional Rayleigh damping
├── scenarios.py           # the 6 canonical scenario configs
├── reference/
│   └── era5_reproject.py  # reproject ERA5 climatology → azimuthal disc (sphere-reference)
├── render/
│   ├── colormaps.py
│   ├── to_png.py          # field → azimuthal-disc display PNG (transparent bg)
│   ├── to_grid.py         # field → downsampled Float32, packed .bin per (scenario,var)
│   └── manifest.py        # writes manifest.json
└── run.py                 # orchestrates: solve → render → emit asset bundle
```

Output target `model/output/` mirrors the manifest structure, then is copied into `web/public/assets/model/` for the build.

**Stack:** Python 3.11+, NumPy, SciPy, optionally Numba for the inner loop, Matplotlib/Pillow for PNG rendering, `xarray` + `netCDF4` for archival output and ERA5 ingestion.

---

## 5. The web experience — design

### 5.1 Framework: Astro + React islands
**Astro.** The site is content-dominant with a few interactive islands. Astro ships zero JS by default and hydrates only the islands you mark, yielding excellent Lighthouse scores and minimal hosting cost — directly serving the "free, educational" goal. Content is authored in MDX.

The interactive islands (the 3D hero and the model viewer) are **React islands** (`@astrojs/react`) so they can use `@react-three/fiber` + `@react-three/drei` for the 3D scene graph. Everything else stays static Astro/MDX.

*Acceptable alternative:* Next.js with static export if a strong React-ecosystem preference emerges — but it's heavier for this use case; Astro is the better fit. Do not pick a framework that requires a running Node server in production.

### 5.2 Interaction libraries
- **Lenis** — smooth/momentum scroll (the buttery feel). Initialized in a client script; framework-agnostic.
- **GSAP + ScrollTrigger** — scroll-driven timelines, section pinning, scrubbed animations. The workhorse for the parallax narrative.
- **Three.js via react-three-fiber + drei** — the 3D flat-disc hero (disc + dome + orbiting spotlight sun + starfield), with depth layers parallaxing as the camera orbits on scroll. Use **one persistent canvas** behind the content; animate the camera and swap visibility per section rather than mounting a new WebGL context per section.
- **Model-viewer rendering** — plain WebGL or `regl` for the field display and GPU particle advection of the wind field (earth.nullschool.net–style streamlines). Canvas2D is an acceptable fallback for the static field. Avoid heavyweight geo libraries (deck.gl) unless a clear need emerges.

### 5.3 Scrollytelling narrative (section by section)
A persistent Three.js canvas sits behind the content and transforms (camera orbit, tilt, zoom; depth-layer parallax) as the reader scrolls:

1. **Hero** — rotating 3D disc with dome and orbiting spotlight sun; title "Plane Old Weather"; one-line tagline; the standing disclaimer. Sets the premium 3D-parallax tone.
2. **The premise** — flat-earth structure: disc, North Pole at center, ice-wall rim, firmament dome, small close spotlight sun. Honest framing as a thought experiment.
3. **The projection** — azimuthal-equidistant mapping; parallax reveal of how real lat/lon data re-maps onto the disc; note this is a real cartographic projection (the UN-logo projection).
4. **Thermodynamics** — the moving thermal bull's-eye; scrubbed animation of the sun's heating ring sweeping and expanding/contracting with the season. Contrast with Earth's fixed latitudinal gradient.
5. **Dynamics** — no Coriolis; interactive cyclone comparison (radial inflow that *doesn't* spin vs. Earth's rotating spiral). The single cleanest "this is wrong" visual.
6. **Boundary conditions** — ice-wall cross-section; wave reflection / standing-wave resonance, the persistent rim anticyclone, and corner turbulence at the dome-wall junction.
7. **The interactive model viewer** — the centerpiece tool; full exploration of the pre-computed simulation (see 5.4).
8. **Falsification** — disc vs. sphere side-by-side; enumerate what the disc predicts that we never observe (rim anticyclone band, discrete wave spectrum, latitude-independent cyclone spin, impossible antipodal distances). Frame as: the spherical model is what makes the observations work.
9. **Methodology & open source** — how the model is built, links to source, the raw-data download, credits, and a clear restatement that Earth is a sphere.

### 5.4 The interactive model viewer (React island)
Controls:
- **Scenario selector** — the six canonical scenarios.
- **Variable toggle** — temperature / pressure / wind / precipitation.
- **Time scrubber + play/pause** — steps through the frame sequence.
- **Wind animation** — GPU particle advection driven by the `wind_u`/`wind_v` probe grids.
- **Hover readout** — samples the probe grid at the cursor, shows the real value + units.
- **Sphere-vs-disc compare** — split or toggle view against `sphere-reference`.

Loading strategy: read `manifest.json` first; lazy-load display-PNG frames on demand (prefetch neighbors of the current timestep); fetch the packed `.bin` probe blob once per (scenario, variable) and slice client-side.

### 5.5 Performance & accessibility (requirements)
- Honor `prefers-reduced-motion`: disable scroll-scrubbed motion and particle animation; provide static equivalents.
- WebGL capability check with a static hero-image fallback; reduced-3D path on low-power/small-viewport devices.
- Lazy-load model frames; never block first paint on assets.
- Semantic HTML, alt text on every rendered field image, keyboard-operable viewer controls, captions for each interactive, a text summary for each chart.
- Target strong Core Web Vitals; the static-first architecture makes this straightforward.

---

## 6. Project structure (monorepo)

```
planeoldweather/
├── model/                      # §4 — Python offline pipeline
│   ├── solver/  forcing/  boundary/  reference/  render/
│   ├── scenarios.py
│   ├── run.py
│   ├── output/                 # generated; copied into web/public
│   └── requirements.txt
├── web/                        # §5 — Astro site
│   ├── src/
│   │   ├── pages/index.astro
│   │   ├── content/            # MDX narrative sections
│   │   ├── components/
│   │   │   ├── scrollytelling/ # GSAP/Lenis-driven sections
│   │   │   ├── DiscHero3D/     # React + r3f island
│   │   │   └── ModelViewer/    # React + WebGL island
│   │   ├── lib/                # scroll setup, webgl helpers, manifest loader
│   │   └── styles/
│   ├── public/assets/model/    # the pre-computed asset bundle
│   ├── astro.config.mjs        # with @astrojs/react
│   └── package.json
├── deploy/                     # §7 — deploy runbook
│   └── cloudflare-pages.md     # Cloudflare Pages
├── .github/workflows/          # ci.yml + deploy.yml (Cloudflare Pages)
├── LICENSE                     # source-available (code) + CC-BY-NC-4.0 (content)
└── README.md
```

---

## 7. Hosting on Cloudflare Pages — deployment

The site is a static Astro build (`web/dist/`, including `public/assets/model/`), hosted on **Cloudflare Pages**: static files on a global CDN with automatic TLS and no origin server to provision or run. `planeoldweather.com` is already on Cloudflare, so attaching the custom domain is a dashboard step. The deploy runbook is `deploy/cloudflare-pages.md`.

### 7.1 Deploy
Either connect the GitHub repo to Cloudflare Pages (auto-build on push to `main`; pull requests get preview deployments), or push a build directly with `wrangler pages deploy`. Build settings: root directory `web`, build command `npm run build`, output `dist`, Node 22 (pinned by `web/.nvmrc`).

### 7.2 CI/CD
`.github/workflows/ci.yml` runs the quality gates on every push and PR. `.github/workflows/deploy.yml` is an optional manual (`workflow_dispatch`) Cloudflare Pages deploy; the primary path is Pages' own Git integration.

### 7.3 Model regeneration
The model bundle is **regenerated offline and committed** — never built in CI or computed per request. When it changes, run `model/run.py`, commit the regenerated bundle, then the normal deploy ships it.

### 7.4 Scaling path (when needed)
If model-asset bandwidth grows, move `/assets/model/` to **Cloudflare R2** (S3-compatible, same account) fronted by the CDN and point the manifest base URL there. Not needed at launch.

---

## 8. Build plan for Claude Code (sequenced)

Each phase is independently verifiable. Build the model pipeline first so the site has real assets to consume; the site shell can be built in parallel with placeholder assets if helpful. **Consult the `frontend-design` skill before any UI/styling work** (Phases 4–6) — it defines the design tokens and the non-generic aesthetic this build needs.

- **Phase 0 — Scaffold.** Monorepo, tooling, `requirements.txt`, Astro init with `@astrojs/react`, lint/format, README with the disclaimer. *Verify: `astro dev` and a no-op `model/run.py` both run.*
- **Phase 1 — Solver core.** Grid (Cartesian-with-disc-mask), dynamics with configurable `f`, thermodynamics, RK3 integrator with diffusion. *Verify: a single scenario runs stably to completion; mass conserved; fields physical.*
- **Phase 2 — Forcing & boundaries.** Spotlight-sun forcing; ice-wall ghost cells + Neumann pressure; closed-dome thermodynamics + the `dome-absorbing` variant. *Verify: the rim anticyclone and non-rotating inflow emerge qualitatively.*
- **Phase 3 — Scenarios, reference & render.** All six scenario configs; ERA5 reprojection for `sphere-reference`; display-PNG renderer, packed `.bin` probe grids, `manifest.json`, NetCDF archival + download artifact. *Verify: the full asset bundle is produced and the manifest validates.*
- **Phase 4 — 3D disc hero.** React + r3f island: disc + dome + orbiting sun + starfield; scroll-coupled camera on one persistent canvas; WebGL fallback image; reduced-motion path.
- **Phase 5 — Scrollytelling.** Lenis + GSAP; sections 2–6 and 8–9 from §5.3 with parallax/pinning/scrubbed animation; MDX content. *Verify: smooth scroll and correct trigger behavior across breakpoints.*
- **Phase 6 — Model viewer.** WebGL field display, time scrubber + play, variable/scenario toggles, hover readout from probe grids, wind particle advection, sphere-vs-disc compare. *Verify: against the Phase 3 manifest.*
- **Phase 7 — Deploy.** Deploy the static build to Cloudflare Pages (Git integration or `wrangler`); attach the `planeoldweather.com` custom domain with automatic TLS; first production deploy.
- **Phase 8 — Polish.** Accessibility pass, performance/Core Web Vitals, cross-browser/device checks, content proofread, final disclaimers, open-source/data-download links.

---

## 9. Scientific integrity notes

The site must be unambiguous that Earth is an oblate spheroid and that the flat model is a pedagogical device. The model's *value* is precisely that it fails in specific, quantifiable ways. Where the narrative states "this is absent from real observations," it should, where feasible, gesture at the magnitude of the discrepancy rather than asserting it qualitatively — that quantitative gap is the lesson. Cite real concepts accurately (azimuthal-equidistant projection, geostrophic balance, the f-plane approximation, no-penetration boundary conditions, Rayleigh damping) so an instructor could use the site without correction.

---

## Appendix — fork decisions on record

| Fork | Decision | Rationale |
|---|---|---|
| Framework | Astro + React islands | Content-dominant site; zero-JS default; lowest hosting cost; React only where the islands need r3f |
| Field data | Display PNG + Float32 probe `.bin` (baseline); RG16+shader (optional) | Simpler client, supports hover readout; flexibility deferred until wanted |
| Scenario set | Six, incl. both `sphere-reference` and `dome-absorbing` | Reference powers compare/falsification; absorbing-dome is a distinct teaching point |
| Object Storage (R2) | Scaling path, not baseline | Cloudflare Pages + CDN suffices at launch |
| Raw-data download | Included | Serves the open/reproducible promise |
| Hover readout | Included | Pedagogically valuable; cheap given the probe grid exists |
