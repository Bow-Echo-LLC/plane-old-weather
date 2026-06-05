import { lazy, Suspense } from "react";
import {
  useLightweightDevice,
  useReducedMotion,
  useScrollProgressRef,
  useWebGLAvailable,
} from "../../lib/hooks";
import HeroFallback from "./HeroFallback";

// Lazy so the heavy three.js / react-three-fiber scene chunk is fetched only
// when we actually render it — phones, data-saver, reduced-motion, and no-WebGL
// visitors never download it; they get the static SVG chart instead.
const DiscScene = lazy(() => import("./DiscScene"));

/**
 * The 3D flat-disc hero island (disc + dome + orbiting spotlight sun + starfield)
 * on one persistent canvas, with a scroll-coupled camera.
 *
 * Graceful degradation (CLAUDE.md cardinal rule): the static chart fallback
 * renders unless WebGL is available AND the user hasn't asked for reduced motion
 * AND the device isn't a phone / on data-saver. While probing (initial state)
 * the fallback also shows, so the hero is never blank and the SSR'd HTML works
 * with no JS.
 */
export default function DiscHero3D() {
  const webglAvailable = useWebGLAvailable();
  const reducedMotion = useReducedMotion();
  const lightweight = useLightweightDevice();
  const scrollRef = useScrollProgressRef();

  const use3D = webglAvailable === true && !reducedMotion && !lightweight;
  if (!use3D) return <HeroFallback />;

  // The static chart stays underneath; the WebGL scene loads (Suspense) and then
  // fades in over it, so the 2D→3D hand-off is a smooth resolve, not a flash.
  return (
    <>
      <HeroFallback />
      <Suspense fallback={null}>
        <DiscScene reducedMotion={reducedMotion} scrollRef={scrollRef} />
      </Suspense>
    </>
  );
}
