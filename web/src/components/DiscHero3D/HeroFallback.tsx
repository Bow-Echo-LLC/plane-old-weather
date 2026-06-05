/**
 * Static, WebGL-free hero — an antique-chart rendering of the flat-disc world
 * (disc + azimuthal graticule + ice wall + firmament dome + orbiting sun +
 * stars). Shown when WebGL is unavailable and while the 3D scene loads, so the
 * hero is never blank (CLAUDE.md: every island survives missing WebGL).
 */
const RINGS = [0.16, 0.32, 0.48, 0.64, 0.8, 0.97];
const SPOKES = Array.from({ length: 12 }, (_, i) => (i / 12) * Math.PI * 2);
const STARS = Array.from({ length: 70 }, (_, i) => ({
  x: (i * 97.13) % 800,
  y: (i * 53.7) % 360,
  r: 0.4 + ((i * 17) % 10) / 9,
  o: 0.25 + ((i * 13) % 10) / 16,
}));

const CX = 400;
const CY = 430;
const RX = 372;
const RY = 132;

export default function HeroFallback() {
  return (
    <svg
      className="hero-fallback"
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="A flat disc world ringed by an ice wall, capped by a firmament dome, with a small sun orbiting close overhead beneath a field of stars."
    >
      <defs>
        <radialGradient id="hf-sky" cx="46%" cy="32%" r="85%">
          <stop offset="0%" stopColor="#141a30" />
          <stop offset="60%" stopColor="#0a0d1c" />
          <stop offset="100%" stopColor="#060812" />
        </radialGradient>
        <radialGradient id="hf-sun" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff0d4" stopOpacity="0.95" />
          <stop offset="22%" stopColor="#f0a94c" stopOpacity="0.8" />
          <stop offset="55%" stopColor="#f0a94c" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#f0a94c" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="hf-spot" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f0a94c" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#f0a94c" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="hf-disc" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10162e" />
          <stop offset="100%" stopColor="#080b18" />
        </linearGradient>
      </defs>

      <rect width="800" height="600" fill="url(#hf-sky)" />

      {STARS.map((s, i) => (
        <circle
          key={i}
          cx={s.x}
          cy={s.y}
          r={s.r}
          fill="#ece3d0"
          opacity={s.o}
        />
      ))}

      {/* firmament dome */}
      <path
        d={`M ${CX - 392} ${CY} A 392 332 0 0 1 ${CX + 392} ${CY}`}
        fill="none"
        stroke="rgba(132,169,204,0.28)"
        strokeWidth="1"
      />
      <path
        d={`M ${CX - 300} ${CY} A 300 254 0 0 1 ${CX + 300} ${CY}`}
        fill="none"
        stroke="rgba(132,169,204,0.12)"
        strokeWidth="1"
      />

      {/* sun glow + core, orbiting close overhead */}
      <circle cx="556" cy="232" r="150" fill="url(#hf-sun)" />
      <circle cx="556" cy="232" r="13" fill="#fff1d6" />
      {/* its spotlight cast on the disc */}
      <ellipse cx="500" cy={CY - 8} rx="120" ry="44" fill="url(#hf-spot)" />

      {/* the disc face */}
      <ellipse cx={CX} cy={CY} rx={RX} ry={RY} fill="url(#hf-disc)" />
      {/* ice wall (a sliver of thickness at the rim) */}
      <path
        d={`M ${CX - RX} ${CY} A ${RX} ${RY} 0 0 0 ${CX + RX} ${CY} L ${CX + RX} ${CY + 16} A ${RX} ${RY} 0 0 1 ${CX - RX} ${CY + 16} Z`}
        fill="#1a2742"
        stroke="rgba(132,169,204,0.4)"
        strokeWidth="1"
      />

      {/* azimuthal graticule on the disc */}
      <g stroke="rgba(236,227,208,0.14)" strokeWidth="1" fill="none">
        {RINGS.map((r, i) => (
          <ellipse key={i} cx={CX} cy={CY} rx={RX * r} ry={RY * r} />
        ))}
        {SPOKES.map((a, i) => (
          <line
            key={i}
            x1={CX}
            y1={CY}
            x2={CX + RX * Math.cos(a)}
            y2={CY + RY * Math.sin(a)}
          />
        ))}
      </g>
      <ellipse
        cx={CX}
        cy={CY}
        rx={RX}
        ry={RY}
        fill="none"
        stroke="var(--line-amber, rgba(240,169,76,0.32))"
        strokeWidth="1.25"
      />
      {/* pole marker */}
      <circle cx={CX} cy={CY} r="2.5" fill="var(--amber, #f0a94c)" />
    </svg>
  );
}
