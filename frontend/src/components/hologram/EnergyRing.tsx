import { useId } from 'react';

interface EnergyRingProps {
  /** 0-100 进度值 */
  value: number;
  size?: number;
  strokeWidth?: number;
  /** 颜色，支持 CSS 变量或十六进制 */
  color?: string;
  label?: string;
  /** 副标签（规范命名） */
  sublabel?: string;
  /** 副标签（驼峰别名，兼容消费端） */
  subLabel?: string;
  animate?: boolean;
}

/**
 * EnergyRing - 圆形能量进度环
 * 使用 SVG stroke-dasharray 绘制进度，带发光滤镜与旋转装饰外环。
 */
export function EnergyRing({
  value,
  size = 120,
  strokeWidth = 8,
  color = 'var(--holo-cyan)',
  label,
  sublabel,
  subLabel,
  animate = true,
}: EnergyRingProps) {
  const rawId = useId();
  const uid = rawId.replace(/[:]/g, '');
  const glowId = `er-glow-${uid}`;
  const subText = subLabel ?? sublabel;

  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const center = size / 2;

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ display: 'block', transform: 'rotate(-90deg)' }}
      >
        <defs>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* 装饰性旋转虚线外环 */}
        <circle
          cx={center}
          cy={center}
          r={radius + strokeWidth / 2 + 6}
          fill="none"
          strokeWidth={1}
          strokeDasharray="4 8"
          className="holo-anim-rotate"
          style={{
            stroke: color,
            strokeOpacity: 0.25,
            transformOrigin: 'center',
            transformBox: 'fill-box',
          }}
        />

        {/* 轨道 */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          style={{ stroke: 'rgba(255,255,255,0.08)' }}
        />

        {/* 进度 */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          filter={`url(#${glowId})`}
          style={{
            stroke: color,
            transition: animate ? 'stroke-dashoffset 1s ease' : 'none',
          }}
        />
      </svg>

      {/* 中心文字 */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          pointerEvents: 'none',
        }}
      >
        <span
          className="holo-text-bright"
          style={{ fontSize: size * 0.26, fontWeight: 800, lineHeight: 1, textShadow: '0 0 12px currentColor', color }}
        >
          {Math.round(clamped)}
        </span>
        {label && (
          <span className="holo-text-cyan" style={{ fontSize: 12, marginTop: 4 }}>
            {label}
          </span>
        )}
        {subText && (
          <span className="holo-text-dim" style={{ fontSize: 11, marginTop: 2 }}>
            {subText}
          </span>
        )}
      </div>
    </div>
  );
}
