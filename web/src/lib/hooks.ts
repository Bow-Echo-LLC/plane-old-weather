import { useEffect, useRef, useState } from "react";

/** True when the user asks for reduced motion. Defaults to true until known, so
 * we never start motion on the first paint. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

/** Synchronous WebGL capability probe. */
export function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return (
      !!window.WebGLRenderingContext &&
      (!!canvas.getContext("webgl2") || !!canvas.getContext("webgl"))
    );
  } catch {
    return false;
  }
}

/** null while probing, then whether WebGL is available. */
export function useWebGLAvailable(): boolean | null {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => setOk(detectWebGL()), []);
  return ok;
}

/** A ref holding page scroll progress in [0, 1], updated outside React render so
 * the 3D loop can read it every frame without re-rendering. */
export function useScrollProgressRef() {
  const progress = useRef(0);
  useEffect(() => {
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      progress.current =
        max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);
  return progress;
}

/** True on phones, data-saver, or very-low-memory devices, where we serve the
 * lightweight static hero instead of the WebGL scene (the reduced-3D path,
 * ARCHITECTURE.md §5.5). */
export function useLightweightDevice(): boolean {
  const [light, setLight] = useState(false);
  useEffect(() => {
    const nav = navigator as Navigator & {
      connection?: { saveData?: boolean };
      deviceMemory?: number;
    };
    const mq = window.matchMedia("(max-width: 700px)");
    const compute = () => {
      const saveData = nav.connection?.saveData === true;
      const lowMemory =
        typeof nav.deviceMemory === "number" && nav.deviceMemory <= 2;
      setLight(mq.matches || saveData || lowMemory);
    };
    compute();
    mq.addEventListener("change", compute);
    return () => mq.removeEventListener("change", compute);
  }, []);
  return light;
}
