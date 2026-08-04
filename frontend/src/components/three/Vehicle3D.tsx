/**
 * Vehicle3D
 *
 * A stylized 3D car built entirely from primitive Three.js geometry (no GLB
 * asset required). The vehicle is composed of:
 *   - A dark-metallic lower body and cabin
 *   - Dark transparent "glass" window regions
 *   - A cyan wireframe edge overlay for the holographic glow
 *   - Four cylindrical wheels that spin on their axles
 *   - A flattened emissive cyan energy disc underneath
 *
 * The whole model auto-rotates around Y by default (toggle via `autoRotate`).
 * Sub-parts report clicks through `onPartClick`. A `highlightPart` prop can
 * emphasize the geometry that best matches a given component key.
 */

import { useRef } from 'react';
import { useFrame, type ThreeEvent } from '@react-three/fiber';
import * as THREE from 'three';

interface Vehicle3DProps {
  /** Slowly rotate the model around its Y axis. Defaults to true. */
  autoRotate?: boolean;
  /** Rotation speed in radians per second. Defaults to 0.4. */
  rotationSpeed?: number;
  /** Uniform scale applied to the whole model. Defaults to 1. */
  scale?: number;
  /**
   * Name of the sub-part to highlight. Accepts the car's own part names
   * ("body", "window", "wheel") as well as the digital-twin component keys
   * ("battery", "motor", "brake", "tire", "chassis"), which are mapped onto
   * the closest matching geometry.
   */
  highlightPart?: string;
  /** Called with the name of the clicked sub-part. */
  onPartClick?: (part: string) => void;
}

const BODY_COLOR = '#0a1a2a';
const EDGE_COLOR = '#00f0ff';

const WHEEL_POSITIONS: [number, number, number][] = [
  [1.05, 0.2, 1.35], // front-left
  [-1.05, 0.2, 1.35], // front-right
  [1.05, 0.2, -1.35], // rear-left
  [-1.05, 0.2, -1.35], // rear-right
];

export function Vehicle3D({
  autoRotate = true,
  rotationSpeed = 0.4,
  scale = 1,
  highlightPart,
  onPartClick,
}: Vehicle3DProps) {
  const groupRef = useRef<THREE.Group>(null!);
  const wheelGroupRefs = useRef<(THREE.Group | null)[]>([]);
  const energyRef = useRef<THREE.Mesh>(null!);

  // Map digital-twin component keys onto the stylized car geometry.
  const highlightBody =
    highlightPart === 'body' || highlightPart === 'motor' || highlightPart === 'chassis';
  const highlightWindow = highlightPart === 'window';
  const highlightWheel = highlightPart === 'wheel' || highlightPart === 'tire' || highlightPart === 'brake';
  const highlightBattery = highlightPart === 'battery';

  useFrame((state, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * rotationSpeed;
    }
    // Spin the wheels on their axles.
    wheelGroupRefs.current.forEach((w) => {
      if (w) w.rotation.x += delta * 3.0;
    });
    // Pulse the underglow energy disc.
    if (energyRef.current) {
      const t = state.clock.elapsedTime;
      const s = 1 + Math.sin(t * 2) * 0.08;
      energyRef.current.scale.set(s, 1, s);
      const mat = energyRef.current.material as THREE.MeshBasicMaterial;
      const base = highlightBattery ? 0.75 : 0.45;
      mat.opacity = base + Math.sin(t * 2) * 0.15;
    }
  });

  const handle = (part: string) => (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onPartClick?.(part);
  };

  return (
    <group ref={groupRef} rotation={[0, 0, 0]} scale={scale}>
      {/* ===== Lower body ===== */}
      <mesh position={[0, 0.35, 0]} onClick={handle('body')}>
        <boxGeometry args={[2.2, 0.5, 4.2]} />
        <meshStandardMaterial
          color={BODY_COLOR}
          metalness={0.9}
          roughness={0.25}
          emissive={EDGE_COLOR}
          emissiveIntensity={highlightBody ? 0.3 : 0.04}
        />
      </mesh>

      {/* Cyan edge glow around the body (wireframe overlay) */}
      <mesh position={[0, 0.35, 0]}>
        <boxGeometry args={[2.24, 0.54, 4.24]} />
        <meshBasicMaterial
          color={EDGE_COLOR}
          wireframe
          transparent
          opacity={highlightBody ? 0.6 : 0.28}
        />
      </mesh>

      {/* ===== Cabin / greenhouse (glass) ===== */}
      <mesh position={[0, 0.85, -0.2]} onClick={handle('window')}>
        <boxGeometry args={[1.85, 0.55, 2.2]} />
        <meshStandardMaterial
          color="#051018"
          metalness={0.4}
          roughness={0.08}
          transparent
          opacity={0.65}
          emissive={EDGE_COLOR}
          emissiveIntensity={highlightWindow ? 0.35 : 0.06}
        />
      </mesh>

      {/* Roof cap */}
      <mesh position={[0, 1.14, -0.2]}>
        <boxGeometry args={[1.7, 0.06, 1.9]} />
        <meshStandardMaterial color={BODY_COLOR} metalness={0.9} roughness={0.25} />
      </mesh>

      {/* Cyan edge glow around the cabin */}
      <mesh position={[0, 0.85, -0.2]}>
        <boxGeometry args={[1.89, 0.59, 2.24]} />
        <meshBasicMaterial
          color={EDGE_COLOR}
          wireframe
          transparent
          opacity={highlightWindow ? 0.55 : 0.22}
        />
      </mesh>

      {/* ===== Wheels ===== */}
      {WHEEL_POSITIONS.map((pos, i) => (
        <group
          key={`wheel-${i}`}
          position={pos}
          ref={(el) => {
            wheelGroupRefs.current[i] = el;
          }}
        >
          <mesh rotation={[0, 0, Math.PI / 2]} onClick={handle('wheel')}>
            <cylinderGeometry args={[0.4, 0.4, 0.3, 24]} />
            <meshStandardMaterial
              color="#0a0a0a"
              metalness={0.6}
              roughness={0.4}
              emissive={EDGE_COLOR}
              emissiveIntensity={highlightWheel ? 0.45 : 0.12}
            />
          </mesh>
          {/* Hubcap accent */}
          <mesh position={[0.16, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.16, 0.16, 0.02, 16]} />
            <meshStandardMaterial color={EDGE_COLOR} emissive={EDGE_COLOR} emissiveIntensity={0.5} />
          </mesh>
        </group>
      ))}

      {/* ===== Headlights ===== */}
      <mesh position={[0.7, 0.4, 2.1]}>
        <boxGeometry args={[0.35, 0.12, 0.05]} />
        <meshStandardMaterial color={EDGE_COLOR} emissive={EDGE_COLOR} emissiveIntensity={0.9} />
      </mesh>
      <mesh position={[-0.7, 0.4, 2.1]}>
        <boxGeometry args={[0.35, 0.12, 0.05]} />
        <meshStandardMaterial color={EDGE_COLOR} emissive={EDGE_COLOR} emissiveIntensity={0.9} />
      </mesh>

      {/* ===== Taillights ===== */}
      <mesh position={[0.7, 0.4, -2.1]}>
        <boxGeometry args={[0.35, 0.12, 0.05]} />
        <meshStandardMaterial color="#ff3860" emissive="#ff3860" emissiveIntensity={0.8} />
      </mesh>
      <mesh position={[-0.7, 0.4, -2.1]}>
        <boxGeometry args={[0.35, 0.12, 0.05]} />
        <meshStandardMaterial color="#ff3860" emissive="#ff3860" emissiveIntensity={0.8} />
      </mesh>

      {/* ===== Energy underglow ===== */}
      <mesh ref={energyRef} position={[0, -0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.7, 48]} />
        <meshBasicMaterial
          color={EDGE_COLOR}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

export default Vehicle3D;
