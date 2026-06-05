import { useEffect, useRef } from "react";
import { useReducedMotion } from "../../lib/hooks";

const TWO_PI = Math.PI * 2;
const COOL = "rgba(132,169,204,0.55)";
const WARM = "rgba(240,169,76,0.6)";

/**
 * Two low-pressure centers, two worlds. On a non-rotating disc (f = 0) inflowing
 * air converges straight to the center and never turns; on a rotating Earth the
 * Coriolis force bends the identical inflow into a spiral. The single cleanest
 * "this is wrong" visual (ARCHITECTURE.md §5.3). Static under reduced motion.
 */
export default function CycloneCompare() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let w = 0;
    let h = 0;
    let raf = 0;
    let last = 0;

    type P = { panel: number; ang: number; r: number; px: number; py: number };
    let parts: P[] = [];

    const center = (panel: number) => ({
      cx: panel === 0 ? w * 0.27 : w * 0.73,
      cy: h * 0.52,
    });
    const maxR = () => Math.min(w * 0.19, h * 0.4);

    const place = (p: P) => {
      const { cx, cy } = center(p.panel);
      p.px = cx + p.r * Math.cos(p.ang);
      p.py = cy + p.r * Math.sin(p.ang);
    };
    const spawn = (panel: number): P => {
      const p = {
        panel,
        ang: Math.random() * TWO_PI,
        r: maxR() * (0.7 + Math.random() * 0.42),
        px: 0,
        py: 0,
      };
      place(p);
      return p;
    };

    const drawCenters = () => {
      for (const panel of [0, 1]) {
        const { cx, cy } = center(panel);
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, TWO_PI);
        ctx.fillStyle = "#f0a94c";
        ctx.fill();
      }
      ctx.strokeStyle = "rgba(236,227,208,0.1)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(w / 2, h * 0.12);
      ctx.lineTo(w / 2, h * 0.88);
      ctx.stroke();
    };

    const streamline = (panel: number, a0: number, spiral: boolean) => {
      const { cx, cy } = center(panel);
      const r0 = maxR();
      ctx.beginPath();
      let first = true;
      for (let r = r0; r > 5; r -= 2) {
        const t = 1 - r / r0;
        const ang = spiral ? a0 + t * 4.6 : a0;
        const x = cx + r * Math.cos(ang);
        const y = cy + r * Math.sin(ang);
        if (first) {
          ctx.moveTo(x, y);
          first = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.strokeStyle = panel === 0 ? COOL : WARM;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    };

    const drawStatic = () => {
      ctx.fillStyle = "#080a14";
      ctx.fillRect(0, 0, w, h);
      for (let k = 0; k < 14; k++) {
        const a0 = (k / 14) * TWO_PI;
        streamline(0, a0, false);
        streamline(1, a0, true);
      }
      drawCenters();
    };

    const frame = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000) || 0;
      last = now;
      ctx.fillStyle = "rgba(8,10,20,0.16)"; // fade -> trails
      ctx.fillRect(0, 0, w, h);
      const r0 = maxR();
      for (const p of parts) {
        const ox = p.px;
        const oy = p.py;
        p.r -= (26 + (1 - p.r / r0) * 42) * dt;
        if (p.panel === 1) p.ang += (0.8 + (1 - p.r / r0) * 3.2) * dt;
        if (p.r < 5) {
          Object.assign(p, spawn(p.panel));
          continue;
        }
        place(p);
        ctx.strokeStyle = p.panel === 0 ? COOL : WARM;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(ox, oy);
        ctx.lineTo(p.px, p.py);
        ctx.stroke();
      }
      drawCenters();
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
      parts = Array.from({ length: 200 }, (_, i) => spawn(i % 2));
      if (reduced) drawStatic();
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    if (!reduced) {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    }
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
          f = 0 — converges, never turns
        </span>
        <span className="fig-tag mono" style={{ top: "7%", left: "73%" }}>
          rotating — winds into a spiral
        </span>
      </div>
      <figcaption className="fig-cap mono">
        Fig. 4 — the same low, two worlds.
        <span className="sr-only">
          On a non-rotating disc, inflowing air converges straight to the
          low-pressure center and never rotates. On a rotating Earth, the
          Coriolis force bends the identical inflow into a spiral.
        </span>
      </figcaption>
    </figure>
  );
}
