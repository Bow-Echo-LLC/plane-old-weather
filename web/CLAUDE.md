# web/ — Astro static site

Subsystem notes for working in `web/`. The root `CLAUDE.md` and
`docs/ARCHITECTURE.md` (§5) are authoritative; this only adds local detail.

## Invariants

- **Static output only.** `output: "static"` in `astro.config.mjs`. Never switch
  to a server adapter — the build is served as static files; nothing else runs.
- **Islands, hydrated narrowly.** Only `DiscHero3D` and `ModelViewer` are React
  (so they can use react-three-fiber). Prefer `client:visible` over
  `client:load`. Keep JS off the critical render path.
- **One persistent canvas.** The 3D scene is a single WebGL/three.js canvas
  behind the content; sections animate the camera and toggle visibility. Never
  mount a new canvas per section.
- **Manifest-driven viewer.** Read `assets/model/manifest.json` (types in
  `src/lib/manifest.ts`). Never hard-code asset paths, frame counts, or value
  ranges.
- **Graceful degradation is required.** Every island honors
  `prefers-reduced-motion` (static fallback) and survives missing WebGL (static
  image / Canvas2D fallback). Field images need alt text; viewer controls must
  be keyboard-operable. The Phase 0 islands already implement these checks —
  keep them when adding real rendering.
- **Sentence case** in UI copy and headings. Don't hand-format what
  prettier/eslint own.
- **Read the `frontend-design` skill before any UI/styling work** (Phases 4-6).
  `src/styles/global.css` is a neutral placeholder until then.

## Layout

`src/pages/` (entry) · `src/layouts/` · `src/content/` (MDX, Phase 5) ·
`src/components/{DiscHero3D,ModelViewer,scrollytelling}/` · `src/lib/`
(manifest loader, scroll/webgl helpers) · `src/styles/`.
`public/assets/model/` holds the committed asset bundle.

## Commands

```
npm install
npm run dev        # astro dev
npm run build      # static build -> web/dist/
npm run preview
npm run lint && npm run typecheck   # quality gates
npm run format     # prettier --write
```
