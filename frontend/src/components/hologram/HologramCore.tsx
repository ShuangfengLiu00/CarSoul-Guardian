import { useId } from 'react';
import { motion } from 'framer-motion';

interface HologramCoreProps {
  size?: number;
  color?: string;
  label?: string;
  active?: boolean;
}

/**
 * HologramCore - AI 核心可视化（脉动光球）
 * 多层同心圆呼吸动画 + 旋转虚线环 + 中心发光球体 + 向外扩散的数据粒子。
 */
export function HologramCore({
  size = 200,
  color = 'var(--holo-purple)',
  label,
  active = true,
}: HologramCoreProps) {
  const rawId = useId();
  const uid = rawId.replace(/[:]/g, '');
  const glowId = `hc-glow-${uid}`;
  const center = size / 2;
  const particles = Array.from({ length: 8 }, (_, i) => i);

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        <defs>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* 外层旋转虚线环 */}
        <circle
          cx={center}
          cy={center}
          r={size * 0.46}
          fill="none"
          strokeWidth={1}
          strokeDasharray="6 10"
          className="holo-anim-rotate"
          filter={`url(#${glowId})`}
          style={{ stroke: color, strokeOpacity: 0.3, transformOrigin: 'center', transformBox: 'fill-box' }}
        />
        {/* 内层快速旋转环 */}
        <circle
          cx={center}
          cy={center}
          r={size * 0.38}
          fill="none"
          strokeWidth={1}
          strokeDasharray="2 6"
          className="holo-anim-rotate-fast"
          filter={`url(#${glowId})`}
          style={{ stroke: color, strokeOpacity: 0.2, transformOrigin: 'center', transformBox: 'fill-box' }}
        />
      </svg>

      {/* 呼吸同心圆 */}
      <div
        className="holo-anim-breathe"
        style={{
          position: 'absolute',
          width: size * 0.72,
          height: size * 0.72,
          borderRadius: '50%',
          border: `1px solid ${color}`,
          opacity: 0.35,
        }}
      />
      <div
        className="holo-anim-breathe"
        style={{
          position: 'absolute',
          width: size * 0.52,
          height: size * 0.52,
          borderRadius: '50%',
          border: `1px solid ${color}`,
          opacity: 0.55,
          animationDelay: '0.5s',
        }}
      />

      {/* 中心发光球体 */}
      <div
        className={active ? 'holo-anim-breathe' : ''}
        style={{
          width: size * 0.34,
          height: size * 0.34,
          borderRadius: '50%',
          background: `radial-gradient(circle at 35% 35%, ${color} 0%, ${color} 30%, transparent 70%)`,
          boxShadow: `0 0 40px ${color}, 0 0 80px ${color}`,
          position: 'relative',
          zIndex: 2,
        }}
      />

      {/* 向外扩散的数据粒子 */}
      {active &&
        particles.map((i) => {
          const angle = (i / particles.length) * Math.PI * 2;
          const dist = size * 0.42;
          return (
            <motion.span
              key={i}
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: 4,
                height: 4,
                marginLeft: -2,
                marginTop: -2,
                borderRadius: '50%',
                background: color,
                boxShadow: `0 0 8px ${color}`,
                zIndex: 3,
              }}
              animate={{
                x: [0, Math.cos(angle) * dist, Math.cos(angle) * dist * 1.25],
                y: [0, Math.sin(angle) * dist, Math.sin(angle) * dist * 1.25],
                opacity: [0, 1, 0],
                scale: [0.5, 1, 0.3],
              }}
              transition={{
                duration: 2.5,
                repeat: Infinity,
                delay: i * 0.25,
                ease: 'easeOut',
              }}
            />
          );
        })}

      {label && (
        <div
          className="holo-text-bright"
          style={{
            position: 'absolute',
            bottom: -28,
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: '0.05em',
            whiteSpace: 'nowrap',
            textShadow: '0 0 10px var(--holo-purple-glow)',
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
}
