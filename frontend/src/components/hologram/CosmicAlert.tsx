import { motion } from 'framer-motion';

type AlertLevel = 'info' | 'warning' | 'critical';

interface CosmicAlertProps {
  level: AlertLevel;
  title: string;
  detail?: string;
  source?: string;
  time?: string;
  onClose?: () => void;
}

interface LevelConfig {
  chipClass: string;
  label: string;
  color: string;
  border: string;
  bg: string;
  icon: string;
}

const LEVEL_CONFIG: Record<AlertLevel, LevelConfig> = {
  info: {
    chipClass: 'holo-chip',
    label: '信息',
    color: 'var(--info-400)',
    border: 'var(--info-400)',
    bg: 'var(--info-soft)',
    icon: 'i',
  },
  warning: {
    chipClass: 'holo-chip-amber',
    label: '警告',
    color: 'var(--warn-400)',
    border: 'var(--warn-400)',
    bg: 'var(--warn-soft)',
    icon: '!',
  },
  critical: {
    chipClass: 'holo-chip-red',
    label: '紧急',
    color: 'var(--danger-400)',
    border: 'var(--danger-400)',
    bg: 'var(--danger-soft)',
    icon: '!',
  },
};

/**
 * CosmicAlert - 精密克制告警横幅（CS-UI-DS §6.3 / §6.4）
 * 实色软底 + 左侧角色色边框，无脉冲 / 无扫描线 / 无霓虹发光。
 */
export function CosmicAlert({ level, title, detail, source, time, onClose }: CosmicAlertProps) {
  const cfg = LEVEL_CONFIG[level];

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: 'easeOut' }}
      className="holo-glass"
      style={{
        position: 'relative',
        padding: '16px 20px',
        borderLeft: `3px solid ${cfg.border}`,
        borderRadius: 'var(--r-md)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, position: 'relative', zIndex: 2 }}>
        {/* 图标（实色圆，无发光） */}
        <div
          style={{
            width: 38,
            height: 38,
            flexShrink: 0,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: cfg.bg,
            border: `1px solid ${cfg.border}`,
            color: cfg.color,
            fontWeight: 800,
            fontSize: 16,
          }}
        >
          {cfg.icon}
        </div>

        {/* 内容 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            <span className={cfg.chipClass}>{cfg.label}</span>
            <span className="holo-text-bright" style={{ fontSize: 15, fontWeight: 700 }}>
              {title}
            </span>
          </div>
          {detail && (
            <p className="holo-text-dim" style={{ margin: 0, fontSize: 13, lineHeight: 1.6 }}>
              {detail}
            </p>
          )}
          {(source || time) && (
            <div
              className="holo-text-dim"
              style={{ display: 'flex', gap: 14, marginTop: 8, fontSize: 11, flexWrap: 'wrap' }}
            >
              {source && <span>来源: {source}</span>}
              {time && <span>{time}</span>}
            </div>
          )}
        </div>

        {/* 关闭按钮 */}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="holo-btn-ghost"
            style={{ flexShrink: 0, padding: '4px 12px', fontSize: 12, borderRadius: 8 }}
          >
            关闭
          </button>
        )}
      </div>
    </motion.div>
  );
}
