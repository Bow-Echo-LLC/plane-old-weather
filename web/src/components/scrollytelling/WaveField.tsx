import { useEffect, useRef } from "react";
import { useReducedMotion } from "../../lib/hooks";

/**
 * A cross-section of the bounded disc: gravity waves run out to the ice wall,
 * reflect, and interfere into standing modes; mass heaps against the rim into a
 * persistent high (ARCHITECTURE.md §5.3, §4.3). The surface oscillates in fixed
 * modal shapes; static under reduced motion.
 */
const MODES = [
  { k: 1, amp: 1.0, omega: 0.7 },
  { k: 2, amp: 0.5, omega: 1.0 },
  { k: 3, amp: 0.34, omega: 1.28 },
];

export default function WaveField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let w = 0;
    let h = 0;
    let raf = 0;

    const render = (t: number) => {
      ctx.fillStyle = "#080a14";
      ctx.fillRect(0, 0, w, h);
      const m = w * 0.1;
      const x0 = m;
      const x1 = w - m;
      const L = x1 - x0;
      const base = h * 0.66;
      const amp = Math.min(h * 0.13, 64);

      // firmament dome
      ctx.beginPath();
      ctx.moveTo(x0 - 6, base);
      ctx.quadraticCurveTo(w / 2, base - h * 0.62, x1 + 6, base);
      ctx.strokeStyle = "rgba(132,169,204,0.4)";
      ctx.lineWidth = 1;
      ctx.stroke();

      const eta = (x: number) => {
        const s = (x - x0) / L;
        let y = 0;
        for (const md of MODES)
          y += md.amp * Math.sin(md.k * Math.PI * s) * Math.cos(md.omega * t);
        return y;
      };

      // atmosphere column under the surface
      ctx.beginPath();
      ctx.moveTo(x0, base);
      for (let x = x0; x <= x1; x += 3) ctx.lineTo(x, base - amp * eta(x));
      ctx.lineTo(x1, base + h * 0.16);
      ctx.lineTo(x0, base + h * 0.16);
      ctx.closePath();
      const g = ctx.createLinearGradient(0, base - amp, 0, base + h * 0.16);
      g.addColorStop(0, "rgba(132,169,204,0.22)");
      g.addColorStop(1, "rgba(132,169,204,0.02)");
      ctx.fillStyle = g;
      ctx.fill();

      // surface line
      ctx.beginPath();
      for (let x = x0; x <= x1; x += 2) {
        const y = base - amp * eta(x);
        if (x === x0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(236,227,208,0.8)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // ice walls
      ctx.strokeStyle = "rgba(132,169,204,0.85)";
      ctx.lineWidth = 3;
      for (const x of [x0, x1]) {
        ctx.beginPath();
        ctx.moveTo(x, base - amp * 1.5);
        ctx.lineTo(x, base + h * 0.16);
        ctx.stroke();
      }

      // rim high marker
      ctx.fillStyle = "#f0a94c";
      ctx.beginPath();
      ctx.arc(x1 - 14, base - amp * eta(x1 - 14) - 10, 3, 0, Math.PI * 2);
      ctx.fill();
    };

    const frame = (now: number) => {
      render(now * 0.001);
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
      if (reduced) render(0.9);
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
        <span className="fig-tag mono" style={{ top: "12%", left: "10%" }}>
          ice wall
        </span>
        <span className="fig-tag mono" style={{ top: "12%", left: "90%" }}>
          ice wall
        </span>
        <span className="fig-tag mono" style={{ top: "12%", left: "50%" }}>
          standing waves
        </span>
        <span
          className="fig-tag fig-tag--amber mono"
          style={{ top: "40%", left: "84%" }}
        >
          rim high
        </span>
      </div>
      <figcaption className="fig-cap mono">
        Fig. 5 — waves with nowhere to go.
        <span className="sr-only">
          In cross-section, gravity waves reflect off the ice walls at both rims
          and interfere into standing waves, while mass heaps against the rim
          into a persistent high-pressure anticyclone.
        </span>
      </figcaption>
    </figure>
  );
}
