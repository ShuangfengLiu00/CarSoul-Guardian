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
  up: 'var(--soul-400)',
  down: 'var(--danger-400)',
  stable: 'var(--text-300)',
};

/**
 * StatCard - 精密克制统计卡片（CS-UI-DS §6.2）
 * 实色 ink-850 卡 + 发丝边框 + 大数 --font-display，无任何霓虹发光。
 */
export function StatCard({
  label,
  value,
  unit,
  sub,
  color = 'var(--accent)',
  icon,
  trend,
  trendValue,
}: StatCardProps) {
  const fill =
    typeof value === 'number' ? Math.max(0, Math.min(100, value)) : 75;

  return (
    <div
      className="holo-glass holo-glass-hover holo-anim-fade-scale"
      style={{ position: 'relative', padding: 'var(--space-5)' }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          position: 'relative',
          zIndex: 2,
        }}
      >
        <span className="holo-stat__label" style={{ color: 'var(--text-300)', fontSize: 13 }}>
          {label}
        </span>
        {icon && (
          <span style={{ color, fontSize: 18, lineHeight: 1 }}>{icon}</span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, position: 'relative', zIndex: 2, marginTop: 6 }}>
        <span
          className="holo-stat__value"
          style={{ color, fontFamily: 'var(--font-display)', fontSize: 30, fontWeight: 700, lineHeight: 1 }}
        >
          {value}
        </span>
        {unit && (
          <span className="holo-text-dim" style={{ fontSize: 14 }}>
            {unit}
          </span>
        )}
      </div>

      {sub && <span className="holo-stat__sub" style={{ color: 'var(--text-300)', fontSize: 12, display: 'block', marginTop: 4 }}>{sub}</span>}

      {trend && trendValue && (
        <div
          style={{
            fontSize: 12,
            color: TREND_COLOR[trend],
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            marginTop: 2,
          }}
        >
          <span>{TREND_ICON[trend]}</span>
          <span>{trendValue}</span>
        </div>
      )}

      <div className="holo-energy-bar" style={{ marginTop: 10 }}>
        <div
          className="holo-energy-bar__fill"
          style={{ width: `${fill}%`, background: color }}
        />
      </div>
    </div>
  );
}
