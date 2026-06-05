import { Billboard, Stars } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { type RefObject, useMemo, useRef } from "react";
import * as THREE from "three";

const DISC_R = 10;

/** A canvas texture of the azimuthal graticule (concentric rings + radial
 * spokes) painted onto the disc face — the polar-chart motif. */
function useGraticuleTexture(): THREE.CanvasTexture {
  return useMemo(() => {
    const size = 1024;
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const c = size / 2;
    ctx.strokeStyle = "rgba(150,180,220,0.7)";
    for (let i = 1; i <= 10; i++) {
      ctx.lineWidth = i % 5 === 0 ? 3 : 1.2;
      ctx.beginPath();
      ctx.arc(c, c, (size / 2) * (i / 10.4), 0, Math.PI * 2);
      ctx.stroke();
    }
    for (let a = 0; a < 24; a++) {
      const ang = (a / 24) * Math.PI * 2;
      ctx.lineWidth = a % 6 === 0 ? 2.4 : 0.8;
      ctx.beginPath();
      ctx.moveTo(c, c);
      ctx.lineTo(c + Math.cos(ang) * c, c + Math.sin(ang) * c);
      ctx.stroke();
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.anisotropy = 4;
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, []);
}

/** A soft radial-gradient sprite texture for the sun's glow halo. */
function useGlowTexture(): THREE.CanvasTexture {
  return useMemo(() => {
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const g = ctx.createRadialGradient(
      size / 2,
      size / 2,
      0,
      size / 2,
      size / 2,
      size / 2,
    );
    g.addColorStop(0, "rgba(255,240,212,1)");
    g.addColorStop(0.25, "rgba(240,169,76,0.55)");
    g.addColorStop(1, "rgba(240,169,76,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, []);
}

function Disc() {
  const graticule = useGraticuleTexture();
  return (
    <mesh rotation={[0, 0, 0]} position={[0, 0, 0]} receiveShadow>
      <cylinderGeometry args={[DISC_R, DISC_R, 0.6, 128, 1, false]} />
      {/* side = ice wall, top = graticule face, bottom = dark underside */}
      <meshStandardMaterial
        attach="material-0"
        color="#88a8cc"
        roughness={0.4}
        metalness={0.1}
        emissive="#21405e"
        emissiveIntensity={0.5}
      />
      <meshStandardMaterial
        attach="material-1"
        color="#0a0e20"
        roughness={0.85}
        metalness={0}
        emissive="#587bb2"
        emissiveMap={graticule}
        emissiveIntensity={0.7}
      />
      <meshStandardMaterial attach="material-2" color="#05060c" roughness={1} />
    </mesh>
  );
}

function Dome() {
  return (
    <mesh position={[0, 0.3, 0]}>
      <sphereGeometry
        args={[DISC_R + 0.6, 64, 32, 0, Math.PI * 2, 0, Math.PI / 2]}
      />
      <meshStandardMaterial
        color="#9bb8d6"
        emissive="#1a2c48"
        emissiveIntensity={0.5}
        transparent
        opacity={0.07}
        side={THREE.DoubleSide}
        depthWrite={false}
        metalness={0}
        roughness={0.1}
      />
    </mesh>
  );
}

function SpotlightSun({ reducedMotion }: { reducedMotion: boolean }) {
  const group = useRef<THREE.Group>(null);
  const glow = useGlowTexture();
  const orbitR = 5.4;
  const height = 4.6;

  useFrame((state) => {
    if (!group.current) return;
    const a = reducedMotion ? 0.85 : state.clock.elapsedTime * 0.22;
    group.current.position.set(
      Math.cos(a) * orbitR,
      height + Math.sin(a) * orbitR * 0.18,
      Math.sin(a) * orbitR,
    );
  });

  return (
    <group ref={group}>
      <pointLight color="#ffdca8" intensity={48} distance={130} decay={1.5} />
      <mesh>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshBasicMaterial color="#fff1d6" toneMapped={false} />
      </mesh>
      <Billboard>
        <mesh>
          <planeGeometry args={[7, 7]} />
          <meshBasicMaterial
            map={glow}
            transparent
            blending={THREE.AdditiveBlending}
            depthWrite={false}
            toneMapped={false}
            opacity={0.95}
          />
        </mesh>
      </Billboard>
    </group>
  );
}

// Camera "shots", one per narrative beat (hero → premise → projection →
// thermodynamics → dynamics → boundaries → falsification). Scroll progress
// interpolates between them; az = orbit angle, el = height, rad = distance.
type Shot = { az: number; el: number; rad: number; lookY: number };
const SHOTS: Shot[] = [
  { az: -0.45, el: 9.5, rad: 25, lookY: 1.0 },
  { az: 0.25, el: 7.0, rad: 22, lookY: 1.6 },
  { az: 0.7, el: 13.5, rad: 20, lookY: 0.6 },
  { az: 1.15, el: 5.5, rad: 19, lookY: 2.2 },
  { az: 1.85, el: 7.5, rad: 21, lookY: 1.4 },
  { az: 2.5, el: 3.4, rad: 23, lookY: 1.8 },
  { az: 3.1, el: 10.5, rad: 26, lookY: 1.0 },
];

function sampleShot(p: number): Shot {
  const n = SHOTS.length - 1;
  const f = Math.min(0.9999, Math.max(0, p)) * n;
  const i = Math.floor(f);
  const raw = f - i;
  const t = raw * raw * (3 - 2 * raw); // smoothstep
  const a = SHOTS[i];
  const b = SHOTS[i + 1] ?? a;
  const mix = (x: number, y: number) => x + (y - x) * t;
  return {
    az: mix(a.az, b.az),
    el: mix(a.el, b.el),
    rad: mix(a.rad, b.rad),
    lookY: mix(a.lookY, b.lookY),
  };
}

/** Camera: interpolates between the narrative shots by scroll progress, with a
 * slow idle orbit on top. Frozen on the opening shot when motion is reduced. */
function CameraRig({
  reducedMotion,
  scrollRef,
}: {
  reducedMotion: boolean;
  scrollRef: RefObject<number>;
}) {
  const { camera } = useThree();
  useFrame((state, dt) => {
    const shot = sampleShot(reducedMotion ? 0 : scrollRef.current);
    const az = shot.az + (reducedMotion ? 0 : state.clock.elapsedTime * 0.02);
    const target = new THREE.Vector3(
      Math.sin(az) * shot.rad,
      shot.el,
      Math.cos(az) * shot.rad,
    );
    if (reducedMotion) {
      camera.position.copy(target);
    } else {
      camera.position.lerp(target, Math.min(1, dt * 2));
    }
    camera.lookAt(0, shot.lookY, 0);
  });
  return null;
}

export default function DiscScene({
  reducedMotion,
  scrollRef,
}: {
  reducedMotion: boolean;
  scrollRef: RefObject<number>;
}) {
  return (
    <Canvas
      className="disc-canvas"
      style={{ position: "absolute", inset: 0 }}
      dpr={[1, 2]}
      frameloop={reducedMotion ? "demand" : "always"}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      }}
      camera={{ position: [0, 9, 25], fov: 38, near: 0.1, far: 220 }}
    >
      <color attach="background" args={["#070912"]} />
      <fog attach="fog" args={["#070912", 34, 105]} />

      <ambientLight intensity={0.22} color="#3a4a6a" />
      <hemisphereLight args={["#26344f", "#05060c", 0.3]} />

      <Stars
        radius={95}
        depth={55}
        count={2200}
        factor={3.2}
        saturation={0}
        fade
        speed={reducedMotion ? 0 : 0.3}
      />

      <Disc />
      <Dome />
      <SpotlightSun reducedMotion={reducedMotion} />

      <CameraRig reducedMotion={reducedMotion} scrollRef={scrollRef} />
    </Canvas>
  );
}
