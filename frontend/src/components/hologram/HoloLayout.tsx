import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { vehicleTwin, getHealthColor, getHealthLabel } from '@/services/holoData';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/holo', label: '宇宙入口', icon: '🌌' },
  { path: '/holo/universe', label: '车辆宇宙', icon: '🪐' },
  { path: '/holo/twin', label: '数字孪生', icon: '🔮' },
  { path: '/holo/health', label: '健康仪表', icon: '💚' },
  { path: '/holo/battery', label: '电池中心', icon: '🔋' },
  { path: '/holo/agents', label: 'Agent星系', icon: '🤖' },
  { path: '/holo/memory', label: '记忆海洋', icon: '🧠' },
  { path: '/holo/prediction', label: '预测中心', icon: '📊' },
  { path: '/holo/safety', label: '安全守护', icon: '🛡️' },
  { path: '/holo/timeline', label: '时间轴', icon: '⏳' },
  { path: '/holo/evolution', label: '进化引擎', icon: '🧬' },
  { path: '/holo/chat', label: 'AI对话', icon: '💬' },
];

interface HoloLayoutProps {
  children: ReactNode;
  activePath: string;
}

/**
 * HoloLayout - 全息驾驶舱主布局
 * 固定侧边栏 + 内容区，侧边栏含呼吸 Logo、导航项与底部健康指数指示器。
 */
export function HoloLayout({ children, activePath }: HoloLayoutProps) {
  const navigate = useNavigate();
  const health = vehicleTwin.health;
  const healthColor = getHealthColor(health);
  const healthLabel = getHealthLabel(health);

  return (
    <div className="holo-page">
      <aside className="holo-sidebar">
        {/* Logo */}
        <div className="holo-sidebar__logo">
          <div
            className="holo-anim-breathe"
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              background: 'var(--holo-gradient-purple)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
              boxShadow: '0 0 16px var(--holo-purple-glow)',
              flexShrink: 0,
            }}
          >
            🛡️
          </div>
          <div>
            <div className="holo-gradient-text" style={{ fontSize: 15, fontWeight: 800, lineHeight: 1.1 }}>
              CarSoul
            </div>
            <div className="holo-text-dim" style={{ fontSize: 10, letterSpacing: '0.12em' }}>
              GUARDIAN
            </div>
          </div>
        </div>

        {/* 导航 */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NAV_ITEMS.map((item) => {
            const isActive = activePath === item.path;
            return (
              <button
                key={item.path}
                type="button"
                className={`holo-sidebar__item ${isActive ? 'is-active' : ''}`}
                onClick={() => navigate(item.path)}
              >
                <span style={{ fontSize: 16, width: 22, textAlign: 'center' }}>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* 底部健康指数指示器 */}
        <div
          className="holo-glass"
          style={{
            marginTop: 20,
            padding: 16,
            borderRadius: 12,
          }}
        >
          <div className="holo-text-dim" style={{ fontSize: 11, marginBottom: 8, letterSpacing: '0.08em' }}>
            车辆健康指数
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span
              style={{
                fontSize: 28,
                fontWeight: 800,
                color: healthColor,
                textShadow: `0 0 12px ${healthColor}`,
                lineHeight: 1,
              }}
            >
              {health}
            </span>
            <span className="holo-text-dim" style={{ fontSize: 12 }}>
              / 100
            </span>
          </div>
          <div className="holo-energy-bar" style={{ marginTop: 10 }}>
            <div
              className="holo-energy-bar__fill"
              style={{ width: `${health}%`, background: `linear-gradient(90deg, ${healthColor}, transparent)` }}
            />
          </div>
          <div className="holo-text-dim" style={{ marginTop: 6, fontSize: 11 }}>
            状态: <span style={{ color: healthColor }}>{healthLabel}</span>
          </div>
        </div>
      </aside>

      {/* 内容区 */}
      <main className="holo-content" style={{ paddingTop: 32 }}>
        {children}
      </main>
    </div>
  );
}
