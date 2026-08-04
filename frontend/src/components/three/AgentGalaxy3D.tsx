/**
 * AgentGalaxy3D
 *
 * Visualizes the CarSoul Guardian multi-agent system as an orbiting galaxy:
 *   - A central, larger, pulsing "Manager Agent" sphere (purple)
 *   - The remaining agents orbit the manager on circular paths at varying
 *     radii/speeds derived from the `AgentInfo` data
 *   - Faint rings trace each orbit
 *   - Gradient connection lines link the manager to every orbiting agent and
 *     pulse over time (toggle via `showConnections`)
 *   - The agent whose id matches `selectedAgent` is highlighted with a ring
 *
 * Data is sourced from `@/services/holoData` by default but can be overridden
 * via the `agents` prop.
 */

import { useMemo, useRef } from 'react';
import { useFrame, type ThreeEvent } from '@react-three/fiber';
import * as THREE from 'three';
import { agents as defaultAgents, type AgentInfo } from '@/services/holoData';

interface AgentGalaxy3DProps {
  /** Agents to render. Defaults to the holoData `agents` array. */
  agents?: AgentInfo[];
  /** Called with the agent id when an agent sphere is clicked. */
  onAgentClick?: (id: string) => void;
  /** Id of the currently selected agent (highlighted in the scene). */
  selectedAgent?: string;
  /** Whether to render the manager<->agent connection lines. Defaults to true. */
  showConnections?: boolean;
}

interface Orbit {
  agent: AgentInfo;
  startAngle: number;
  radius: number;
}

export function AgentGalaxy3D({
  agents = defaultAgents,
  onAgentClick,
  selectedAgent,
  showConnections = true,
}: AgentGalaxy3DProps) {
  const managerRef = useRef<THREE.Mesh>(null!);
  const segmentsRef = useRef<THREE.LineSegments>(null!);
  const orbiterRefs = useRef<(THREE.Group | null)[]>([]);

  // Split into the central manager and the orbiting agents.
  const manager = useMemo<AgentInfo | undefined>(() => {
    return agents.find((a) => a.orbitRadius === 0 || a.id === 'manager') ?? agents[0];
  }, [agents]);

  const orbiters = useMemo<AgentInfo[]>(
    () => agents.filter((a) => a !== manager),
    [agents, manager],
  );

  const orbits = useMemo<Orbit[]>(() => {
    return orbiters.map((agent, i) => {
      const base = agent.orbitRadius > 0 ? agent.orbitRadius : 3;
      // Layer the agents across a few orbital radii for a richer galaxy.
      const radius = base + ((i % 3) - 1) * 0.6;
      const startAngle = (i / Math.max(orbiters.length, 1)) * Math.PI * 2;
      return { agent, startAngle, radius };
    });
  }, [orbiters]);

  const distinctRadii = useMemo(() => {
    return Array.from(new Set(orbits.map((o) => o.radius)));
  }, [orbits]);

  // Segment geometry: one line per orbit (manager -> agent).
  const segPositions = useMemo(
    () => new Float32Array(orbits.length * 6),
    [orbits],
  );

  const segColors = useMemo(() => {
    const arr = new Float32Array(orbits.length * 6);
    const managerColor = new THREE.Color(manager?.color ?? '#a855f7');
    orbits.forEach((o, i) => {
      const ac = new THREE.Color(o.agent.color);
      // vertex 0 (manager end)
      arr[i * 6 + 0] = managerColor.r;
      arr[i * 6 + 1] = managerColor.g;
      arr[i * 6 + 2] = managerColor.b;
      // vertex 1 (agent end)
      arr[i * 6 + 3] = ac.r;
      arr[i * 6 + 4] = ac.g;
      arr[i * 6 + 5] = ac.b;
    });
    return arr;
  }, [orbits, manager]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;

    // Manager pulse
    if (managerRef.current) {
      const s = 1 + Math.sin(t * 2) * 0.06;
      managerRef.current.scale.setScalar(s);
    }

    // Advance orbiters and refresh connection endpoints
    orbits.forEach((o, i) => {
      const angle = o.startAngle + t * o.agent.orbitSpeed;
      const x = Math.cos(angle) * o.radius;
      const z = Math.sin(angle) * o.radius;
      const g = orbiterRefs.current[i];
      if (g) g.position.set(x, 0, z);
      segPositions[i * 6 + 3] = x;
      segPositions[i * 6 + 4] = 0;
      segPositions[i * 6 + 5] = z;
    });

    if (segmentsRef.current) {
      const attr = segmentsRef.current.geometry.getAttribute('position') as THREE.BufferAttribute;
      attr.needsUpdate = true;
      const mat = segmentsRef.current.material as THREE.LineBasicMaterial;
      mat.opacity = 0.25 + Math.sin(t * 3) * 0.15;
    }
  });

  const handle = (id: string) => (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onAgentClick?.(id);
  };

  const managerColor = manager?.color ?? '#a855f7';
  const managerSelected = !!manager && manager.id === selectedAgent;

  return (
    <group rotation={[0.25, 0, 0]}>
      {/* ===== Orbit rings ===== */}
      {distinctRadii.map((radius, i) => (
        <mesh key={`ring-${i}`} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
          <ringGeometry args={[radius - 0.03, radius + 0.03, 96]} />
          <meshBasicMaterial color="#3b82f6" transparent opacity={0.12} side={THREE.DoubleSide} />
        </mesh>
      ))}

      {/* ===== Connection lines (manager <-> each agent) ===== */}
      {showConnections && (
        <lineSegments ref={segmentsRef}>
          <bufferGeometry>
            <bufferAttribute args={[segPositions, 3]} attach="attributes-position" />
            <bufferAttribute args={[segColors, 3]} attach="attributes-color" />
          </bufferGeometry>
          <lineBasicMaterial vertexColors transparent opacity={0.3} depthWrite={false} />
        </lineSegments>
      )}

      {/* ===== Central manager ===== */}
      {manager && (
        <>
          <mesh ref={managerRef} position={[0, 0, 0]} onClick={handle(manager.id)}>
            <sphereGeometry args={[0.55, 32, 32]} />
            <meshStandardMaterial
              color={managerColor}
              emissive={managerColor}
              emissiveIntensity={managerSelected ? 1.0 : 0.6}
              metalness={0.4}
              roughness={0.3}
            />
          </mesh>
          {/* Manager halo */}
          <mesh position={[0, 0, 0]}>
            <sphereGeometry args={[0.85, 32, 32]} />
            <meshBasicMaterial
              color={managerColor}
              transparent
              opacity={managerSelected ? 0.2 : 0.12}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
          {managerSelected && (
            <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
              <torusGeometry args={[0.95, 0.02, 8, 64]} />
              <meshBasicMaterial color={managerColor} transparent opacity={0.8} />
            </mesh>
          )}
        </>
      )}

      {/* ===== Orbiting agents ===== */}
      {orbits.map((o, i) => {
        const isSelected = o.agent.id === selectedAgent;
        return (
          <group
            key={`agent-${o.agent.id}`}
            ref={(el) => {
              orbiterRefs.current[i] = el;
            }}
          >
            <mesh onClick={handle(o.agent.id)} scale={isSelected ? 1.35 : 1}>
              <sphereGeometry args={[0.28, 24, 24]} />
              <meshStandardMaterial
                color={o.agent.color}
                emissive={o.agent.color}
                emissiveIntensity={isSelected ? 1.1 : 0.5}
                metalness={0.3}
                roughness={0.4}
              />
            </mesh>
            {/* Agent glow halo */}
            <mesh scale={isSelected ? 1.3 : 1}>
              <sphereGeometry args={[0.44, 16, 16]} />
              <meshBasicMaterial
                color={o.agent.color}
                transparent
                opacity={isSelected ? 0.2 : 0.1}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
              />
            </mesh>
            {/* Selection ring */}
            {isSelected && (
              <mesh rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[0.5, 0.015, 8, 64]} />
                <meshBasicMaterial color={o.agent.color} transparent opacity={0.8} />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}

export default AgentGalaxy3D;
