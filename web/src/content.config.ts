import { glob } from "astro/loaders";
import { defineCollection } from "astro:content";
import { z } from "astro:schema";

/**
 * The fixed narrative arc (ARCHITECTURE.md §5.3). Each MDX file is one scroll
 * chapter: frontmatter carries the heading + which visual to mount, the body is
 * the prose. The arc order is fixed — discuss before reordering (CLAUDE.md).
 */
const narrative = defineCollection({
  loader: glob({ pattern: "*.mdx", base: "./src/content/narrative" }),
  schema: z.object({
    order: z.number(),
    eyebrow: z.string(),
    title: z.string(),
    visual: z
      .enum([
        "structure",
        "projection",
        "bullseye",
        "cyclones",
        "waves",
        "chart",
        "none",
      ])
      .default("none"),
    // How prominently the persistent 3D scene shows behind this chapter.
    backdrop: z.enum(["scene", "dim", "solid"]).default("dim"),
  }),
});

export const collections = { narrative };
