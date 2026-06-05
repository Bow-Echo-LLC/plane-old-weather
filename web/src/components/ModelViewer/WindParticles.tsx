import { useEffect, useRef } from "react";

interface Props {
  /** Current-frame probe slices (row 0 = south), length width*height. */
  u: Float32Array;
  v: Float32Array;
  width: number;
  height: number;
  reducedMotion: boolean;
}

const COUNT = 1500;
const MAX_AGE = 1.6; // seconds
const SPEED = 0.02; // normalized units per (m/s · s)

/**
 * earth.nullschool-style wind advection over the disc, in Canvas2D: particles
 * follow the (u, v) probe field with fading trails. Reads the velocity via a
 * ref so timestep changes don't restart the loop. Off under reduced motion (the
 * baked wind-speed PNG already shows the field).
 */
export default function WindParticles({
  u,
  v,
  width,
  height,
  reducedMotion,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const field = useRef({ u, v, width, height });
  field.current = { u, v, width, height };

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || reducedMotion) return;

    let cw = 0;
    let ch = 0;
    let raf = 0;
    let last = 0;
    type Pt = { nx: number; ny: number; age: number };
    const reseed = (): Pt => ({
      nx: Math.random(),
      ny: Math.random(),
      age: Math.random() * MAX_AGE,
    });
    let parts: Pt[] = Array.from({ length: COUNT }, reseed);

    // Bilinear sample of (u, v) at normalized field coords; null if off-disc.
    const sample = (nx: number, ny: number): [number, number] | null => {
      const { u, v, width: W, height: H } = field.current;
      if (nx < 0 || nx > 1 || ny < 0 || ny > 1) return null;
      const fx = nx * (W - 1);
      const fy = (1 - ny) * (H - 1); // probe row 0 is south; screen y=0 is north
      const i0 = Math.floor(fx);
      const j0 = Math.floor(fy);
      const i1 = Math.min(W - 1, i0 + 1);
      const j1 = Math.min(H - 1, j0 + 1);
      const tx = fx - i0;
      const ty = fy - j0;
      const at = (arr: Float32Array, j: number, i: number) => arr[j * W + i];
      const lerp4 = (arr: Float32Array) =>
        (at(arr, j0, i0) * (1 - tx) + at(arr, j0, i1) * tx) * (1 - ty) +
        (at(arr, j1, i0) * (1 - tx) + at(arr, j1, i1) * tx) * ty;
      const uu = lerp4(u);
      const vv = lerp4(v);
      if (Number.isNaN(uu) || Number.isNaN(vv)) return null;
      return [uu, vv];
    };

    const step = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000) || 0;
      last = now;
      ctx.fillStyle = "rgba(8,10,20,0.13)"; // fade -> trails
      ctx.fillRect(0, 0, cw, ch);
      ctx.lineWidth = 1.1;
      for (const p of parts) {
        p.age += dt;
        const vel = sample(p.nx, p.ny);
        if (!vel || p.age > MAX_AGE) {
          Object.assign(p, reseed());
          p.age = 0;
          continue;
        }
        const ox = p.nx * cw;
        const oy = p.ny * ch;
        p.nx += vel[0] * SPEED * dt;
        p.ny -= vel[1] * SPEED * dt; // +v is north => up on screen
        const speed = Math.hypot(vel[0], vel[1]);
        const t = Math.min(1, speed / 28);
        ctx.strokeStyle = `rgba(${230 + t * 25}, ${200 - t * 30}, ${150 - t * 60}, ${0.25 + t * 0.55})`;
        ctx.beginPath();
        ctx.moveTo(ox, oy);
        ctx.lineTo(p.nx * cw, p.ny * ch);
        ctx.stroke();
      }
      raf = requestAnimationFrame(step);
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cw = rect.width;
      ch = rect.height;
      canvas.width = Math.round(cw * dpr);
      canvas.height = Math.round(ch * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      parts = Array.from({ length: COUNT }, reseed);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    last = performance.now();
    raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [reducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className="viewer__wind"
      aria-hidden="true"
    ></canvas>
  );
}
