import { useEffect, useRef } from "react";
import { useReducedMotion } from "../../lib/hooks";

const TWO_PI = Math.PI * 2;

/**
 * Thermodynamics, side by side: the flat disc heated by a spotlight bull's-eye
 * that orbits the center, versus the sphere's fixed latitudinal bands
 * (ARCHITECTURE.md §5.3). The flat panel animates; the sphere is static. Both
 * static under reduced motion.
 */
export default function BullseyeFigure() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let w = 0;
    let h = 0;
    let raf = 0;
    const discR = () => Math.min(w * 0.2, h * 0.42);
    const left = () => ({ cx: w * 0.27, cy: h * 0.52 });
    const right = () => ({ cx: w * 0.73, cy: h * 0.52 });

    const disc = (cx: number, cy: number, paint: () => void) => {
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, discR(), 0, TWO_PI);
      ctx.clip();
      paint();
      ctx.restore();
      ctx.beginPath();
      ctx.arc(cx, cy, discR(), 0, TWO_PI);
      ctx.strokeStyle = "rgba(236,227,208,0.22)";
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    const drawFlat = (ang: number) => {
      const { cx, cy } = left();
      const R = discR();
      disc(cx, cy, () => {
        ctx.fillStyle = "#0a0e1c";
        ctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);
        // diurnal-mean heating ring
        ctx.beginPath();
        ctx.arc(cx, cy, R * 0.42, 0, TWO_PI);
        ctx.strokeStyle = "rgba(240,169,76,0.14)";
        ctx.lineWidth = R * 0.32;
        ctx.stroke();
        // the bright moving spotlight
        const sx = cx + Math.cos(ang) * R * 0.42;
        const sy = cy + Math.sin(ang) * R * 0.42;
        const g = ctx.createRadialGradient(sx, sy, 0, sx, sy, R * 0.55);
        g.addColorStop(0, "rgba(255,240,212,0.95)");
        g.addColorStop(0.3, "rgba(240,169,76,0.75)");
        g.addColorStop(1, "rgba(240,169,76,0)");
        ctx.fillStyle = g;
        ctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);
      });
    };

    const drawSphere = () => {
      const { cx, cy } = right();
      const R = discR();
      disc(cx, cy, () => {
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
        g.addColorStop(0, "#241a4a"); // cold pole (center)
        g.addColorStop(0.34, "#7c3f6b");
        g.addColorStop(0.5, "#f0a94c"); // warm equator ring
        g.addColorStop(0.66, "#7c3f6b");
        g.addColorStop(1, "#241a4a"); // cold pole (rim)
        ctx.fillStyle = g;
        ctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);
      });
    };

    const render = (ang: number) => {
      ctx.fillStyle = "#080a14";
      ctx.fillRect(0, 0, w, h);
      drawFlat(ang);
      drawSphere();
    };

    const frame = (now: number) => {
      render(now * 0.0006);
      raf = requestAnimationFrame(frame);
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      w = rect.width;
      h = rect.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (reduced) render(0.7);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    if (!reduced) raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [reduced]);

  return (
    <figure className="fig">
      <div className="fig-stage">
        <canvas ref={canvasRef} aria-hidden="true"></canvas>
        <span className="fig-tag mono" style={{ top: "7%", left: "27%" }}>
          flat — a moving spotlight
        </span>
        <span className="fig-tag mono" style={{ top: "7%", left: "73%" }}>
          sphere — fixed bands
        </span>
      </div>
      <figcaption className="fig-cap mono">
        Fig. 3 — heat that sweeps, versus heat that stays.
        <span className="sr-only">
          On the flat disc a small close sun makes a bright bull's-eye of heat
          that orbits the center each day; on the sphere, latitude fixes a
          steady warm-equator, cold-pole gradient.
        </span>
      </figcaption>
    </figure>
  );
}
