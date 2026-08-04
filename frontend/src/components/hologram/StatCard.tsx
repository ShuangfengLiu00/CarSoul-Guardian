import type { ReactNode } from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  /** 值的单位，显示在数值右侧 */
  unit?: string;
  /** 副标题/说明文字，显示在数值下方（对应 .holo-stat__sub） */
  sub?: string;
  color?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
}

const TREND_ICON: Record<'up' | 'down' | 'stable', string> = {
  up: '▲',
  down: '▼',
  stable: '—',
};

const TREND_COLOR: Record<'up' | 'down' | 'stable', string> = {
  up: 'var(--holo-green)',
  down: 'var(--holo-red)',
  stable: 'var(--holo-text-dim)',
};

/**
 * StatCard - 全息统计卡片
 * 基于 .holo-glass + .holo-stat，底部能量条按数值占比填充。
 */
export function StatCard({
  label,
  value,
  unit,
  sub,
  color = 'var(--holo-cyan)',
  icon,
  trend,
  trendValue,
}: StatCardProps) {
  const fill =
    typeof value === 'number' ? Math.max(0, Math.min(100, value)) : 75;

  return (
    <div
      className="holo-glass holo-glass-hover holo-corners holo-stat holo-anim-fade-scale"
      style={{ position: 'relative' }}
    >
      <div className="holo-scanline" />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          position: 'relative',
          zIndex: 2,
        }}
      >
        <span className="holo-stat__label">{label}</span>
        {icon && (
          <span style={{ color, fontSize: 18, lineHeight: 1, filter: `drop-shadow(0 0 6px ${color})` }}>
            {icon}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, position: 'relative', zIndex: 2 }}>
        <span className="holo-stat__value" style={{ color, textShadow: `0 0 12px ${color}` }}>
          {value}
        </span>
        {unit && (
          <span className="holo-text-dim" style={{ fontSize: 14 }}>
            {unit}
          </span>
        )}
      </div>

      {sub && <span className="holo-stat__sub">{sub}</span>}

      {trend && trendValue && (
        <div
          style={{
            fontSize: 12,
            color: TREND_COLOR[trend],
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            textShadow: `0 0 6px ${TREND_COLOR[trend]}`,
          }}
        >
          <span>{TREND_ICON[trend]}</span>
          <span>{trendValue}</span>
        </div>
      )}

      <div className="holo-energy-bar" style={{ marginTop: 4 }}>
        <div
          className="holo-energy-bar__fill"
          style={{ width: `${fill}%`, background: `linear-gradient(90deg, ${color}, transparent)` }}
        />
      </div>
    </div>
  );
}
