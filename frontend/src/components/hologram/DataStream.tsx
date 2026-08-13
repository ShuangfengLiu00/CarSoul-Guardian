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
 * DataStream - 静态发丝分隔线（CS-UI-DS 精密克制版）
 * 原"动态霓虹数据流"违反 §一（Precision, not glow）。改为一条克制、无动画、
 * 尊重 prefers-reduced-motion 的虚线分隔，仅作区块呼吸留白。
 */
export function DataStream({
  direction = 'horizontal',
  color = 'var(--line-strong)',
  height = 36,
  segments,
  lines,
}: DataStreamProps) {
  const isHorizontal = direction === 'horizontal';
  const segCount = segments ?? lines ?? 5;
  const lineCount = 3;
  const nodes = Array.from({ length: segCount + 1 }, (_, i) => i);
  const VB_W = 1000;
  const VB_H = height;

  return (
    <div style={{ width: '100%', height, position: 'relative', overflow: 'hidden', opacity: 0.6 }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="none"
        style={{ display: 'block' }}
        aria-hidden="true"
      >
        {Array.from({ length: lineCount }, (_, i) => {
          const pos = (VB_H / (lineCount + 1)) * (i + 1);
          return (
            <line
              key={i}
              x1={isHorizontal ? 0 : pos}
              y1={isHorizontal ? pos : 0}
              x2={isHorizontal ? VB_W : pos}
              y2={isHorizontal ? pos : VB_H}
              strokeWidth={1}
              strokeDasharray="2 10"
              style={{ stroke: color, strokeOpacity: 0.5 - i * 0.12 }}
            />
          );
        })}

        {nodes.map((n) => {
          const t = n / segCount;
          if (isHorizontal) {
            const x = t * VB_W;
            const y = VB_H / 2;
            return <circle key={n} cx={x} cy={y} r={1.5} style={{ fill: color, fillOpacity: 0.5 }} />;
          }
          const y = t * VB_H;
          const x = VB_W / 2;
          return <circle key={n} cx={x} cy={y} r={1.5} style={{ fill: color, fillOpacity: 0.5 }} />;
        })}
      </svg>
    </div>
  );
}
