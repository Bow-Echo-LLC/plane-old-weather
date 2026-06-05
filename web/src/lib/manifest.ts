/**
 * Types and loaders for the model asset bundle (spec §3.2-3.4).
 *
 * The viewer is manifest-driven: it reads scenarios, variables, paths, value
 * ranges, grid sizes, and colormaps from here and NEVER hard-codes them
 * (CLAUDE.md cardinal rule #3). The bundle is produced by model/run.py (Phase 3)
 * and lives under /assets/model/.
 */

export interface VariableManifest {
  /** Frame path template, e.g. "summer-orbit/temperature/frame_{i:04d}.png". */
  frames: string;
  /** Packed Float32 probe blob (the scalar field), one per (scenario, variable). */
  probe_blob: string;
  /** Probe grid dimensions [w, h]. */
  grid_size: [number, number];
  /** Fixed value range [min, max] used for the baked colormap. */
  value_range: [number, number];
  units: string;
  colormap: string;
  /** Wind only: packed Float32 u/v component blobs for particle advection. */
  components?: { u: string; v: string };
}

export interface ScenarioManifest {
  id: string;
  label: string;
  kind?: "solved" | "reference";
  source?: string;
  timesteps: number;
  time_labels?: string[];
  variables: Record<string, VariableManifest>;
  archive?: string | null;
}

export interface DiscManifest {
  radius_km: number;
  center: string;
}

export interface Manifest {
  scenarios: ScenarioManifest[];
  disc: DiscManifest;
  display_size?: number;
}

export const ASSET_BASE = "/assets/model/";
export const DEFAULT_MANIFEST_URL = ASSET_BASE + "manifest.json";

/** Resolve a manifest-relative path to a URL under the asset base. */
export function assetUrl(rel: string): string {
  return ASSET_BASE + rel;
}

/** Fetch and parse the manifest. Throws if it is missing or malformed. */
export async function loadManifest(
  url: string = DEFAULT_MANIFEST_URL,
): Promise<Manifest> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`failed to load manifest (${res.status}) from ${url}`);
  }
  return (await res.json()) as Manifest;
}

/** Expand a frame template for timestep `i` ("{i}" / zero-padded "{i:0Nd}"). */
export function frameUrl(template: string, i: number): string {
  return template.replace(/\{i(?::0(\d+)d)?\}/g, (_full, width?: string) =>
    width ? String(i).padStart(Number(width), "0") : String(i),
  );
}

/** Full URL of a display PNG for (variable template, timestep). */
export function frameAssetUrl(template: string, i: number): string {
  return assetUrl(frameUrl(template, i));
}

// One in-flight/parsed promise per probe blob path, so each is fetched once.
const probeCache = new Map<string, Promise<Float32Array>>();

/** Fetch a packed Float32 probe blob (cached across the session). */
export function loadProbeBlob(rel: string): Promise<Float32Array> {
  let pending = probeCache.get(rel);
  if (!pending) {
    pending = fetch(assetUrl(rel)).then(async (res) => {
      if (!res.ok) throw new Error(`probe ${rel}: ${res.status}`);
      return new Float32Array(await res.arrayBuffer());
    });
    probeCache.set(rel, pending);
  }
  return pending;
}

/** A view onto timestep `i` of a packed probe blob (length w*h, C-order). */
export function sliceFrame(
  blob: Float32Array,
  i: number,
  w: number,
  h: number,
): Float32Array {
  const n = w * h;
  return blob.subarray(i * n, (i + 1) * n);
}
