/**
 * DataParticles
 *
 * Flowing "data stream" particle field rendered with Three.js Points and a
 * custom ShaderMaterial. Each particle drifts upward and resets to the bottom
 * once it passes the top, producing a continuous upward data-rain effect.
 *
 * Colors cycle through cyan, purple and green (the `color` prop seeds the
 * first slot of the palette so callers can tint the stream).
 */

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface DataParticlesProps {
  /** Number of particles in the stream. */
  count?: number;
  /** Base color (first palette slot). Defaults to cyan. */
  color?: string;
}

const TOP_Y = 4;
const BOTTOM_Y = -4;
const SPREAD = 6;

const vertexShader = /* glsl */ `
  attribute float aSize;
  attribute vec3 aColor;

  varying vec3 vColor;

  uniform float uTime;

  void main() {
    vColor = aColor;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    // Gentle size shimmer tied to height so the stream feels alive.
    float shimmer = 0.7 + 0.3 * sin(uTime * 3.0 + position.y * 2.0);
    gl_PointSize = aSize * shimmer * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = /* glsl */ `
  varying vec3 vColor;

  void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);
    float alpha = smoothstep(0.5, 0.0, dist);
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(vColor, alpha);
  }
`;

export function DataParticles({ count = 100, color = '#00f0ff' }: DataParticlesProps) {
  const pointsRef = useRef<THREE.Points>(null!);
  const matRef = useRef<THREE.ShaderMaterial>(null!);

  const { positions, sizes, colors, velocities } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const colors = new Float32Array(count * 3);
    const velocities = new Float32Array(count);

    const palette = [
      new THREE.Color(color),
      new THREE.Color('#a855f7'), // purple
    ];

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * SPREAD;
      positions[i * 3 + 1] = Math.random() * (TOP_Y - BOTTOM_Y) + BOTTOM_Y;
      positions[i * 3 + 2] = (Math.random() - 0.5) * SPREAD;

      sizes[i] = 2 + Math.random() * 4;
      velocities[i] = 0.5 + Math.random() * 1.5;

      const c = palette[i % palette.length];
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }

    return { positions, sizes, colors, velocities };
  }, [count, color]);

  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), []);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1); // clamp to avoid jumps on tab refocus
    if (pointsRef.current) {
      const attr = pointsRef.current.geometry.getAttribute('position') as THREE.BufferAttribute;
      const arr = attr.array as Float32Array;
      for (let i = 0; i < count; i++) {
        arr[i * 3 + 1] += velocities[i] * dt;
        if (arr[i * 3 + 1] > TOP_Y) {
          // Reset to bottom with a new horizontal position
          arr[i * 3 + 1] = BOTTOM_Y;
          arr[i * 3] = (Math.random() - 0.5) * SPREAD;
          arr[i * 3 + 2] = (Math.random() - 0.5) * SPREAD;
        }
      }
      attr.needsUpdate = true;
    }
    if (matRef.current) matRef.current.uniforms.uTime.value = state.clock.elapsedTime;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute args={[positions, 3]} attach="attributes-position" />
        <bufferAttribute args={[sizes, 1]} attach="attributes-aSize" />
        <bufferAttribute args={[colors, 3]} attach="attributes-aColor" />
      </bufferGeometry>
      <shaderMaterial
        ref={matRef}
        uniforms={uniforms}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export default DataParticles;
