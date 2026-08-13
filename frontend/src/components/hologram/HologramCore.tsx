import { useId } from 'react';

interface HologramCoreProps {
  size?: number;
  color?: string;
  label?: string;
  active?: boolean;
}

/**
 * HologramCore - 引擎状态可视化（CS-UI-DS 精密克制版）
 * 静态同心环 + 中心实色圆点，无霓虹发光 / 无呼吸粒子 / 无旋转。
 * 仅作"引擎在线"状态指示，不喧宾夺主。
 */
export function HologramCore({
  size = 200,
  color = 'var(--accent)',
  label,
  active = true,
}: HologramCoreProps) {
  const rawId = useId();
  const uid = rawId.replace(/[:]/g, '');
  const center = size / 2;

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
        aria-hidden="true"
      >
        {/* 外环（静态、低透明） */}
        <circle
          cx={center}
          cy={center}
          r={size * 0.46}
          fill="none"
          strokeWidth={1}
          strokeDasharray="6 10"
          style={{ stroke: color, strokeOpacity: 0.3, transformOrigin: 'center', transformBox: 'fill-box' }}
        />
        {/* 内环（静态、更低透明） */}
        <circle
          cx={center}
          cy={center}
          r={size * 0.38}
          fill="none"
          strokeWidth={1}
          strokeDasharray="2 6"
          style={{ stroke: color, strokeOpacity: 0.18, transformOrigin: 'center', transformBox: 'fill-box' }}
        />
      </svg>

      {/* 静态同心环 */}
      <div
        style={{
          position: 'absolute',
          width: size * 0.72,
          height: size * 0.72,
          borderRadius: '50%',
          border: `1px solid ${color}`,
          opacity: 0.28,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: size * 0.52,
          height: size * 0.52,
          borderRadius: '50%',
          border: `1px solid ${color}`,
          opacity: 0.45,
        }}
      />

      {/* 中心实色圆点（无发光） */}
      <div
        style={{
          width: size * 0.3,
          height: size * 0.3,
          borderRadius: '50%',
          background: color,
          position: 'relative',
          zIndex: 2,
        }}
      />

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
            color: 'var(--text-200)',
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
}
