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
  glow: string;
  border: string;
  icon: string;
}

const LEVEL_CONFIG: Record<AlertLevel, LevelConfig> = {
  info: {
    chipClass: 'holo-chip',
    label: '信息',
    color: 'var(--holo-cyan)',
    glow: 'rgba(0, 240, 255, 0.25)',
    border: 'rgba(0, 240, 255, 0.4)',
    icon: 'i',
  },
  warning: {
    chipClass: 'holo-chip-amber',
    label: '警告',
    color: 'var(--holo-amber)',
    glow: 'rgba(255, 184, 0, 0.25)',
    border: 'rgba(255, 184, 0, 0.4)',
    icon: '!',
  },
  critical: {
    chipClass: 'holo-chip-red',
    label: '紧急',
    color: 'var(--holo-red)',
    glow: 'rgba(255, 56, 96, 0.35)',
    border: 'rgba(255, 56, 96, 0.55)',
    icon: '!',
  },
};

/**
 * CosmicAlert - 太空主题告警横幅
 * critical: 红色脉动边框 + 告警波 + 扫描线
 * warning: 琥珀色辉光
 * info: 青色辉光
 */
export function CosmicAlert({ level, title, detail, source, time, onClose }: CosmicAlertProps) {
  const cfg = LEVEL_CONFIG[level];
  const isCritical = level === 'critical';

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={`holo-glass ${isCritical ? 'holo-anim-pulse-red' : ''}`}
      style={{
        position: 'relative',
        padding: '16px 20px',
        border: `1px solid ${cfg.border}`,
        boxShadow: isCritical ? `0 0 30px ${cfg.glow}` : `0 0 15px ${cfg.glow}`,
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      {isCritical && <div className="holo-scanline" />}

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, position: 'relative', zIndex: 2 }}>
        {/* 图标 + 告警波 */}
        <div style={{ position: 'relative', width: 38, height: 38, flexShrink: 0 }}>
          {isCritical && <span className="holo-alert-wave" style={{ position: 'absolute', inset: 0 }} />}
          <div
            style={{
              position: 'relative',
              zIndex: 2,
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(255, 255, 255, 0.05)',
              border: `1px solid ${cfg.color}`,
              color: cfg.color,
              fontWeight: 800,
              fontSize: 16,
              textTransform: 'uppercase',
              textShadow: `0 0 8px ${cfg.color}`,
            }}
          >
            {cfg.icon}
          </div>
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
