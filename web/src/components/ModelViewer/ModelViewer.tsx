import {
  type MouseEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useReducedMotion } from "../../lib/hooks";
import {
  frameAssetUrl,
  loadManifest,
  loadProbeBlob,
  sliceFrame,
  type Manifest,
} from "../../lib/manifest";
import WindParticles from "./WindParticles";

// Approximate CSS gradients for the baked colormaps (for the legend bar only).
const COLORMAP_CSS: Record<string, string> = {
  inferno:
    "linear-gradient(90deg,#000004,#420a68,#932667,#dd513a,#fca50a,#fcffa4)",
  RdBu_r: "linear-gradient(90deg,#053061,#4393c3,#f7f7f7,#d6604d,#67001f)",
  cividis: "linear-gradient(90deg,#00204d,#31446b,#666970,#a69d75,#ffe945)",
  Blues: "linear-gradient(90deg,#deebf7,#9ecae1,#4292c6,#08519c,#08306b)",
};

interface StageProps {
  src: string;
  alt: string;
  label: string;
  onMove?: (e: MouseEvent<HTMLDivElement>) => void;
  onLeave?: () => void;
  wind?: ReactNode;
}

function Stage({ src, alt, label, onMove, onLeave, wind }: StageProps) {
  return (
    <div className="viewer__stage" onMouseMove={onMove} onMouseLeave={onLeave}>
      <img className="viewer__field" src={src} alt={alt} decoding="async" />
      {wind}
      <span className="viewer__stage-label mono">{label}</span>
    </div>
  );
}

/**
 * The interactive model viewer (ARCHITECTURE.md §5.4). Reads manifest.json and
 * drives everything from it (cardinal rule #3): scenario + variable toggles, a
 * time scrubber and play, hover readouts sampled from the probe `.bin` grids,
 * Canvas2D wind-particle advection, and a disc-vs-sphere compare. Keyboard-
 * operable; degrades to a static frame (no autoplay, no particles) under reduced
 * motion, and to a notice if the bundle is missing.
 */
export default function ModelViewer() {
  const reduced = useReducedMotion();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scenarioId, setScenarioId] = useState("");
  const [variable, setVariable] = useState("temperature");
  const [timestep, setTimestep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [compare, setCompare] = useState(false);
  const [hover, setHover] = useState<number | null>(null);

  const [scalarBlob, setScalarBlob] = useState<Float32Array | null>(null);
  const [windU, setWindU] = useState<Float32Array | null>(null);
  const [windV, setWindV] = useState<Float32Array | null>(null);

  // Load the manifest once and pick sensible initial selections.
  useEffect(() => {
    loadManifest()
      .then((m) => {
        setManifest(m);
        // Open on no-coriolis: the cleanest, most instructive entry point (a
        // cyclone that converges but never spins). Fall back gracefully if the
        // manifest ever omits it, keeping selection manifest-driven (rule #3).
        const solved = m.scenarios.filter((s) => s.kind !== "reference");
        const initial =
          solved.find((s) => s.id === "no-coriolis") ??
          solved[0] ??
          m.scenarios[0];
        setScenarioId(initial.id);
        const vars = Object.keys(initial.variables);
        setVariable(vars.includes("temperature") ? "temperature" : vars[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario = manifest?.scenarios.find((s) => s.id === scenarioId);
  const varMeta = scenario?.variables[variable];
  const reference = manifest?.scenarios.find((s) => s.kind === "reference");
  const refMeta = reference?.variables[variable];
  const canCompare = !!refMeta && scenario?.kind !== "reference";

  // Keep the timestep within the active scenario.
  useEffect(() => {
    if (scenario) setTimestep((t) => Math.min(t, scenario.timesteps - 1));
  }, [scenarioId, scenario]);

  // Load probe blobs for the active (scenario, variable).
  useEffect(() => {
    if (!varMeta) return;
    let cancelled = false;
    setScalarBlob(null);
    setWindU(null);
    setWindV(null);
    loadProbeBlob(varMeta.probe_blob).then(
      (b) => !cancelled && setScalarBlob(b),
    );
    if (varMeta.components) {
      loadProbeBlob(varMeta.components.u).then(
        (b) => !cancelled && setWindU(b),
      );
      loadProbeBlob(varMeta.components.v).then(
        (b) => !cancelled && setWindV(b),
      );
    }
    return () => {
      cancelled = true;
    };
  }, [scenarioId, variable, varMeta]);

  // Prefetch neighboring frames so scrubbing/play stays smooth.
  useEffect(() => {
    if (!varMeta || !scenario) return;
    for (const d of [1, -1]) {
      const k = (timestep + d + scenario.timesteps) % scenario.timesteps;
      new Image().src = frameAssetUrl(varMeta.frames, k);
    }
  }, [timestep, varMeta, scenario]);

  // Play loop (disabled under reduced motion).
  useEffect(() => {
    if (!playing || reduced || !scenario) return;
    const id = window.setInterval(
      () => setTimestep((t) => (t + 1) % scenario.timesteps),
      130,
    );
    return () => window.clearInterval(id);
  }, [playing, reduced, scenario]);

  const [gw, gh] = varMeta?.grid_size ?? [0, 0];
  const lastMove = useRef(0);

  const onMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!scalarBlob || !varMeta) return;
    const now = performance.now();
    if (now - lastMove.current < 30) return; // throttle
    lastMove.current = now;
    const rect = e.currentTarget.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width;
    const ny = (e.clientY - rect.top) / rect.height;
    const col = Math.round(nx * (gw - 1));
    const row = Math.round((1 - ny) * (gh - 1)); // probe row 0 = south
    if (col < 0 || col >= gw || row < 0 || row >= gh) return setHover(null);
    const value = sliceFrame(scalarBlob, timestep, gw, gh)[row * gw + col];
    setHover(Number.isNaN(value) ? null : value);
  };

  const windNode = useMemo(() => {
    if (variable !== "wind" || !windU || !windV || reduced || !gw) return null;
    return (
      <WindParticles
        u={sliceFrame(windU, timestep, gw, gh)}
        v={sliceFrame(windV, timestep, gw, gh)}
        width={gw}
        height={gh}
        reducedMotion={reduced}
      />
    );
  }, [variable, windU, windV, reduced, gw, gh, timestep]);

  if (error) {
    return (
      <div className="viewer viewer--notice">
        <p className="mono">Model bundle unavailable.</p>
        <p>
          The viewer reads <code>/assets/model/manifest.json</code>, produced by{" "}
          <code>model/run.py</code>. Generate it into{" "}
          <code>web/public/assets/model/</code> to explore the simulation here.
        </p>
      </div>
    );
  }
  if (!manifest || !scenario || !varMeta) {
    return (
      <div className="viewer viewer--loading" role="status" aria-live="polite">
        <span className="viewer__spinner" aria-hidden="true"></span>
        <span className="viewer__loading-text mono">Loading model</span>
      </div>
    );
  }

  const timeLabel = scenario.time_labels?.[timestep] ?? `frame ${timestep}`;
  const isStatic = scenario.kind === "reference" || scenario.timesteps <= 1;
  const stateText = scenario.kind === "reference" ? "climatology" : timeLabel;
  const alt = `${variable} field for ${scenario.label}${isStatic ? "" : ` at ${timeLabel}`}`;
  const [vmin, vmax] = varMeta.value_range;

  return (
    <figure className="viewer">
      <div
        className={`viewer__stages${compare && canCompare ? " viewer__stages--split" : ""}`}
      >
        <Stage
          src={frameAssetUrl(varMeta.frames, timestep)}
          alt={alt}
          label={`${scenario.label} · ${stateText}`}
          onMove={onMove}
          onLeave={() => setHover(null)}
          wind={windNode}
        />
        {compare && canCompare && refMeta && reference && (
          <Stage
            src={frameAssetUrl(refMeta.frames, 0)}
            alt={`${variable} field for ${reference.label} (idealized real-Earth reference)`}
            label={`${reference.label} · reference`}
          />
        )}
      </div>

      <div className="viewer__readout mono" aria-live="polite">
        {hover !== null
          ? `${hover.toFixed(variable === "pressure" ? 1 : 0)} ${varMeta.units}`
          : `${variable} · ${vmin}–${vmax} ${varMeta.units}`}
      </div>

      <div className="viewer__controls">
        <label className="viewer__ctl">
          <span className="viewer__ctl-label mono">scenario</span>
          <select
            className="viewer__select"
            value={scenarioId}
            onChange={(e) => setScenarioId(e.target.value)}
          >
            {manifest.scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>

        <div className="viewer__ctl" role="group" aria-label="Variable">
          <span className="viewer__ctl-label mono">variable</span>
          <div className="viewer__chips">
            {Object.keys(scenario.variables).map((v) => (
              <button
                key={v}
                type="button"
                className="viewer__chip mono"
                aria-pressed={v === variable}
                onClick={() => setVariable(v)}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        <div className="viewer__ctl viewer__ctl--time">
          <span className="viewer__ctl-label mono">
            time <span className="viewer__time">{stateText}</span>
          </span>
          <div className="viewer__scrub">
            <button
              type="button"
              className="viewer__play mono"
              aria-pressed={playing}
              aria-label={playing ? "Pause" : "Play"}
              disabled={isStatic || reduced}
              onClick={() => setPlaying((p) => !p)}
            >
              {playing ? "❚❚" : "▶"}
            </button>
            <input
              className="viewer__range"
              type="range"
              min={0}
              max={Math.max(0, scenario.timesteps - 1)}
              value={timestep}
              disabled={isStatic}
              aria-label="Timestep"
              onChange={(e) => setTimestep(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="viewer__ctl viewer__ctl--view">
          <span className="viewer__ctl-label mono">view</span>
          <button
            type="button"
            className="viewer__viewtoggle mono"
            aria-pressed={compare}
            disabled={!canCompare}
            onClick={() => setCompare((c) => !c)}
          >
            <span className="viewer__viewtoggle-dot" aria-hidden="true"></span>
            compare sphere
          </button>
        </div>

        <div className="viewer__ctl viewer__ctl--legend">
          <span
            className="viewer__legend"
            style={{
              backgroundImage: COLORMAP_CSS[varMeta.colormap] ?? "none",
            }}
            aria-hidden="true"
          ></span>
          <span className="viewer__legend-range mono">
            {vmin}–{vmax} {varMeta.units}
          </span>
        </div>
      </div>

      <figcaption className="viewer__caption">
        The pre-computed simulation, scrubbed by time and scenario. Hover the
        disc for a real value; toggle <strong>wind</strong> for particle flow,
        or <strong>compare sphere</strong> to set it beside an idealized real
        Earth.
        <span className="sr-only">
          An interactive viewer of the flat-disc weather model, showing
          temperature, pressure, wind and precipitation for each scenario across
          a diurnal cycle, with an idealized real-Earth reference for
          comparison.
        </span>
      </figcaption>
    </figure>
  );
}
