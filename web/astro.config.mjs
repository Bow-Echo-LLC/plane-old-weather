// @ts-check
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import mdx from "@astrojs/mdx";

// Static output only. The build is served as static files; nothing else runs
// in production (CLAUDE.md, cardinal rules #1-2). Never switch to `output: 'server'`.
//
// Astro ships zero JS by default; only the React islands (DiscHero3D,
// ModelViewer) are hydrated, and narrowly (client:visible over client:load).
export default defineConfig({
  site: "https://planeoldweather.com",
  output: "static",
  integrations: [react(), mdx()],
});
