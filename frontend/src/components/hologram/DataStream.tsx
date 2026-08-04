import { useId } from 'react';

interface DataStreamProps {
  direction?: 'horizontal' | 'vertical';
  color?: string;
  height?: number;
  /** 数据段数（节点数 = segments + 1） */
  segments?: number;
  /** segments 的别名，兼容消费端命名 */
  lines?: number;
}

/**
 * DataStream - 动态数据流可视化
 * 多条平行 SVG 线段以不同速度流动，节点处发光闪烁。
 */
export function DataStream({
  direction = 'horizontal',
  color = 'var(--holo-cyan)',
  height = 60,
  segments,
  lines,
}: DataStreamProps) {
  const rawId = useId();
  const uid = rawId.replace(/[:]/g, '');
  const glowId = `ds-glow-${uid}`;

  const isHorizontal = direction === 'horizontal';
  const segCount = segments ?? lines ?? 5;
  const lineCount = 3;
  const nodes = Array.from({ length: segCount + 1 }, (_, i) => i);
  const VB_W = 1000;
  const VB_H = height;

  return (
    <div style={{ width: '100%', height, position: 'relative', overflow: 'hidden' }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="none"
        style={{ display: 'block' }}
      >
        <defs>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {Array.from({ length: lineCount }, (_, i) => {
          const pos = (VB_H / (lineCount + 1)) * (i + 1);
          return (
            <line
              key={i}
              x1={isHorizontal ? 0 : pos}
              y1={isHorizontal ? pos : 0}
              x2={isHorizontal ? VB_W : pos}
              y2={isHorizontal ? pos : VB_H}
              strokeWidth={1.5}
              strokeDasharray="12 8"
              filter={`url(#${glowId})`}
              style={{
                stroke: color,
                strokeOpacity: 0.5 - i * 0.1,
                animation: `holoRingDash ${10 + i * 4}s linear infinite`,
                animationDirection: i % 2 ? 'reverse' : 'normal',
              }}
            />
          );
        })}

        {nodes.map((n) => {
          const t = n / segCount;
          if (isHorizontal) {
            const x = t * VB_W;
            const y = VB_H / 2;
            return (
              <circle key={n} cx={x} cy={y} r={2.5} filter={`url(#${glowId})`} style={{ fill: color }}>
                <animate
                  attributeName="opacity"
                  values="0.2;1;0.2"
                  dur="2s"
                  begin={`${n * 0.3}s`}
                  repeatCount="indefinite"
                />
              </circle>
            );
          }
          const y = t * VB_H;
          const x = VB_W / 2;
          return (
            <circle key={n} cx={x} cy={y} r={2.5} filter={`url(#${glowId})`} style={{ fill: color }}>
              <animate
                attributeName="opacity"
                values="0.2;1;0.2"
                dur="2s"
                begin={`${n * 0.3}s`}
                repeatCount="indefinite"
              />
            </circle>
          );
        })}
      </svg>
    </div>
  );
}
