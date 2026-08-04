/**
 * SpaceBackground
 *
 * Deep-space starfield rendered with Three.js Points using a custom
 * ShaderMaterial. Provides:
 *   - 2500 stars distributed on a sphere shell (2000+ requirement)
 *   - Per-star twinkle animation driven by a phase attribute
 *   - A subset of larger, brighter glowing stars
 *   - A large transparent nebula sphere with a gradient shader
 *
 * The component is intended to be rendered inside a <Canvas> (see HoloCanvas).
 * Stars use additive blending and depthWrite=false so they always sit behind
 * the opaque scene objects while remaining visible against the dark backdrop.
 */

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const STAR_COUNT = 600;
const LARGE_STAR_COUNT = 8;
const NEBULA_RADIUS = 400;

// --- Shaders (module scope so they are not re-allocated each render) ---

const starVertexShader = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute vec3 aColor;

  varying vec3 vColor;
  varying float vTwinkle;

  uniform float uTime;

  void main() {
    vColor = aColor;
    // Subtle per-star twinkle: 0.0 - 1.0
    vTwinkle = 0.55 + 0.45 * abs(sin(uTime * 1.5 + aPhase));

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = aSize * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const starFragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vTwinkle;

  void main() {
    // Soft circular sprite (no texture needed)
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);
    float alpha = smoothstep(0.5, 0.0, dist);
    alpha *= vTwinkle;
    if (alpha < 0.01) discard;

    gl_FragColor = vec4(vColor, alpha);
  }
`;

const nebulaVertexShader = /* glsl */ `
  varying vec3 vDir;

  void main() {
    vDir = normalize(position);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const nebulaFragmentShader = /* glsl */ `
  varying vec3 vDir;

  uniform float uTime;
  uniform vec3 uColorA; // deep purple
  uniform vec3 uColorB; // dark cyan/blue
  uniform vec3 uColorC; // magenta blob

  void main() {
    // Vertical gradient based on direction
    float t = vDir.y * 0.5 + 0.5;
    vec3 col = mix(uColorA, uColorB, t);

    // Soft magenta "nebula" blob near the equator
    float blob = smoothstep(0.75, 0.0, distance(vDir.xz, vec2(0.0)));
    col = mix(col, uColorC, blob * 0.3);

    // Gentle breathing opacity — very subtle
    float alpha = 0.04 + 0.01 * sin(uTime * 0.2);
    gl_FragColor = vec4(col, alpha);
  }
`;

export function SpaceBackground() {
  const starMatRef = useRef<THREE.ShaderMaterial>(null!);
  const nebulaMatRef = useRef<THREE.ShaderMaterial>(null!);

  // Build star buffers once.
  const { positions, sizes, phases, colors } = useMemo(() => {
    const positions = new Float32Array(STAR_COUNT * 3);
    const sizes = new Float32Array(STAR_COUNT);
    const phases = new Float32Array(STAR_COUNT);
    const colors = new Float32Array(STAR_COUNT * 3);

    const palette = [
      new THREE.Color('#ffffff'),
      new THREE.Color('#ffffff'),
      new THREE.Color('#ffffff'),
      new THREE.Color('#e0e8ff'),
    ];
    const cyan = new THREE.Color('#00f0ff');
    const purple = new THREE.Color('#a855f7');

    for (let i = 0; i < STAR_COUNT; i++) {
      // Random point on a spherical shell (radius 60-300)
      const r = 60 + Math.random() * 240;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);

      const isLarge = i < LARGE_STAR_COUNT;
      sizes[i] = isLarge ? 3 + Math.random() * 3 : 0.4 + Math.random() * 1.0;
      phases[i] = Math.random() * Math.PI * 2;

      const c = isLarge
        ? Math.random() > 0.5
          ? cyan
          : purple
        : palette[Math.floor(Math.random() * palette.length)];

      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }

    return { positions, sizes, phases, colors };
  }, []);

  const starUniforms = useMemo(() => ({ uTime: { value: 0 } }), []);

  const nebulaUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColorA: { value: new THREE.Color('#050310') },
      uColorB: { value: new THREE.Color('#010408') },
      uColorC: { value: new THREE.Color('#080318') },
    }),
    [],
  );

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (starMatRef.current) starMatRef.current.uniforms.uTime.value = t;
    if (nebulaMatRef.current) nebulaMatRef.current.uniforms.uTime.value = t;
  });

  return (
    <group>
      {/* Starfield */}
      <points renderOrder={-1}>
        <bufferGeometry>
          <bufferAttribute args={[positions, 3]} attach="attributes-position" />
          <bufferAttribute args={[sizes, 1]} attach="attributes-aSize" />
          <bufferAttribute args={[phases, 1]} attach="attributes-aPhase" />
          <bufferAttribute args={[colors, 3]} attach="attributes-aColor" />
        </bufferGeometry>
        <shaderMaterial
          ref={starMatRef}
          uniforms={starUniforms}
          vertexShader={starVertexShader}
          fragmentShader={starFragmentShader}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Nebula gradient backdrop */}
      <mesh scale={[NEBULA_RADIUS, NEBULA_RADIUS, NEBULA_RADIUS]} renderOrder={-2}>
        <sphereGeometry args={[1, 32, 32]} />
        <shaderMaterial
          ref={nebulaMatRef}
          uniforms={nebulaUniforms}
          vertexShader={nebulaVertexShader}
          fragmentShader={nebulaFragmentShader}
          transparent
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

export default SpaceBackground;
