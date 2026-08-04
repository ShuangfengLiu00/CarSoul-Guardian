import type { CSSProperties, ReactNode } from 'react';

interface GlassPanelProps {
  title?: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  /** 透传到根容器的内联样式 */
  style?: CSSProperties;
  hover?: boolean;
  corners?: boolean;
  scanline?: boolean;
}

/**
 * GlassPanel - 玻璃拟态容器组件
 * 基于 .holo-glass 设计系统，支持角标装饰、扫描线、悬停效果与标题栏。
 */
export function GlassPanel({
  title,
  icon,
  children,
  className = '',
  style,
  hover = false,
  corners = false,
  scanline = false,
}: GlassPanelProps) {
  const classes = [
    'holo-glass',
    hover ? 'holo-glass-hover' : '',
    corners ? 'holo-corners' : '',
    'holo-anim-fade-in',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} style={{ padding: title ? 0 : 20, ...style }}>
      {scanline && <div className="holo-scanline" />}
      {title && (
        <div
          className="holo-text-bright"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '14px 20px',
            borderBottom: '1px solid var(--holo-glass-border)',
            fontSize: 15,
            fontWeight: 700,
            letterSpacing: '0.02em',
            position: 'relative',
            zIndex: 2,
          }}
        >
          {icon && (
            <span style={{ display: 'inline-flex', color: 'var(--holo-cyan)', filter: 'drop-shadow(0 0 6px var(--holo-cyan-glow))' }}>
              {icon}
            </span>
          )}
          <span>{title}</span>
        </div>
      )}
      <div style={{ padding: title ? 20 : 0, position: 'relative', zIndex: 1 }}>{children}</div>
    </div>
  );
}
