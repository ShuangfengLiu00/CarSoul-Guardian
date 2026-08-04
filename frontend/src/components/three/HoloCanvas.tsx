/**
 * HoloCanvas
 *
 * Wrapper around the react-three-fiber <Canvas> that pre-configures the camera,
 * fog, lights and the deep-space background for the holographic cockpit.
 *
 * Usage:
 *   <HoloCanvas>
 *     <Vehicle3D />
 *     <AgentGalaxy3D />
 *   </HoloCanvas>
 */

import type { ReactNode } from 'react';
import { Canvas } from '@react-three/fiber';
import { SpaceBackground } from './SpaceBackground';

interface HoloCanvasProps {
  /** Canvas children rendered inside the 3D scene. */
  children?: ReactNode;
  /** Camera position. Defaults to [0, 2, 8]. */
  cameraPosition?: [number, number, number];
  /** Toggle the built-in SpaceBackground. Defaults to true. */
  enableBackground?: boolean;
  /** Optional className forwarded to the canvas element. */
  className?: string;
}

export function HoloCanvas({
  children,
  cameraPosition = [0, 2, 8],
  enableBackground = true,
  className,
}: HoloCanvasProps) {
  return (
    <Canvas
      className={className}
      camera={{ position: cameraPosition, fov: 50, near: 0.1, far: 2000 }}
      gl={{ antialias: true, alpha: false }}
      dpr={[1, 2]}
    >
      <color attach="background" args={['#03000a']} />
      <fogExp2 attach="fog" args={['#03000a', 0.015]} />

      {/* Lighting rig — subdued for cleaner background */}
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.8} color="#00f0ff" />
      <pointLight position={[-10, -5, -10]} intensity={0.4} color="#a855f7" />

      {enableBackground && <SpaceBackground />}
      {children}
    </Canvas>
  );
}

export default HoloCanvas;
