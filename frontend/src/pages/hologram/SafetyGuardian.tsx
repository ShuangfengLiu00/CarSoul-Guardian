/**
 * Page 18 - Safety Guardian (安全守护)
 *
 * Large safety score (96) with EnergyRing, active protection list (Battery/Brake/
 * Tire/Motor/Chassis all checked), risk assessment cards from alerts data
 * (warning level highlighted), driving DNA summary (aggression/smoothness/
 * energySaving), and driving personality "城市效率型".
 */
import { GlassPanel, EnergyRing } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { vehicleTwin, alerts, getHealthColor } from "@/services/holoData";

const PROTECTION_LIST = [
  { name: "电池", icon: "🔋", active: true },
  { name: "制动", icon: "🛑", active: true },
  { name: "轮胎", icon: "🛞", active: true },
  { name: "电机", icon: "⚡", active: true },
  { name: "底盘", icon: "🔩", active: true },
];

export default function SafetyGuardian() {
  const dna = vehicleTwin.drivingDNA;
  const safetyScore = 96;

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2 className="holo-section-title holo-anim-fade-in" style={{ position: "relative", zIndex: 2 }}>
        安全守护 · 全方位防护中心
      </h2>

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: "340px 1fr",
          gap: 16,
        }}
      >
        {/* Left: Safety score + protection list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <GlassPanel className="holo-anim-fade-scale holo-corners" style={{ textAlign: "center" }}>
            <div className="holo-section-title" style={{ justifyContent: "center" }}>安全评分</div>
            <div style={{ display: "flex", justifyContent: "center", padding: "20px 0 12px", position: "relative" }}>
              <div className="holo-anim-breathe" style={{ position: "absolute", width: 220, height: 220, borderRadius: "50%", background: "radial-gradient(circle, rgba(0,255,157,0.15) 0%, transparent 70%)" }} />
              <EnergyRing
                value={safetyScore}
                size={200}
                color={getHealthColor(safetyScore)}
                label={`${safetyScore}`}
                subLabel="优秀"
                strokeWidth={12}
              />
            </div>
            <div className="holo-text-green holo-anim-glow-text" style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>
              全方位防护运行中
            </div>
          </GlassPanel>

          <GlassPanel className="holo-anim-fade-in holo-corners" title="主动防护清单">
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {PROTECTION_LIST.map((p, i) => (
                <div
                  key={p.name}
                  className="holo-glass holo-glass-hover holo-anim-fade-in"
                  style={{ animationDelay: `${i * 0.08}s`, padding: "12px 14px", borderRadius: 10, display: "flex", alignItems: "center", gap: 12 }}
                >
                  <span style={{ fontSize: 20 }}>{p.icon}</span>
                  <span className="holo-text-bright" style={{ fontSize: 14, fontWeight: 600, flex: 1 }}>{p.name}</span>
                  <span className="holo-chip holo-chip-green">
                    <span style={{ marginRight: 2 }}>✔</span> 已守护
                  </span>
                </div>
              ))}
            </div>
          </GlassPanel>
        </div>

        {/* Right: Risk assessment + driving DNA */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Risk assessment cards */}
          <GlassPanel className="holo-anim-fade-in holo-corners" title="风险评估">
            <div className="holo-grid holo-grid-2">
              {alerts.map((alert, i) => {
                const isWarning = alert.level === "warning";
                const color = alert.level === "warning" ? "#ffb800" : alert.level === "critical" ? "#ff3860" : "#00f0ff";
                return (
                  <div
                    key={alert.id}
                    className={`holo-glass holo-glass-hover holo-anim-fade-in holo-corners ${isWarning ? "holo-anim-pulse" : ""}`}
                    style={{
                      animationDelay: `${i * 0.1}s`,
                      padding: 14,
                      borderRadius: 12,
                      borderLeft: `3px solid ${color}`,
                      background: isWarning ? "rgba(255,184,0,0.06)" : undefined,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color }}>{alert.title}</span>
                      <span className="holo-chip" style={{ borderColor: `${color}55`, color, background: `${color}11`, fontSize: 10 }}>
                        {alert.level === "warning" ? "预警" : alert.level === "critical" ? "严重" : "提示"}
                      </span>
                    </div>
                    <p className="holo-text-dim" style={{ fontSize: 12, lineHeight: 1.6, margin: "0 0 8px" }}>{alert.detail}</p>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className="holo-text-dim" style={{ fontSize: 11 }}>{alert.source}</span>
                      <span className="holo-text-dim" style={{ fontSize: 11 }}>{alert.time}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassPanel>

          {/* Driving DNA */}
          <GlassPanel className="holo-anim-fade-in holo-corners" title="驾驶基因分析">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <DnaBar label="激进程度" value={dna.aggression} color="#ff3860" />
                <DnaBar label="平顺度" value={dna.smoothness} color="#00ff9d" />
                <DnaBar label="节能驾驶" value={dna.energySaving} color="#00f0ff" />
                <DnaBar label="夜间驾驶" value={dna.nightDriving} color="#a855f7" />
                <DnaBar label="高速占比" value={dna.highwayRatio} color="#3b82f6" />
              </div>

              <div className="holo-glass holo-corners" style={{ padding: 20, borderRadius: 14, textAlign: "center", display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
                <div className="holo-text-dim" style={{ fontSize: 12, letterSpacing: "0.1em" }}>驾驶人格画像</div>
                <div style={{ fontSize: 48 }} className="holo-anim-float">🧬</div>
                <div className="holo-gradient-text holo-anim-glow-text" style={{ fontSize: 24, fontWeight: 900 }}>
                  {dna.personality}
                </div>
                <div className="holo-text-dim" style={{ fontSize: 12, lineHeight: 1.6 }}>
                  驾驶风格平稳节能，能效表现优异。建议适当减少急刹以进一步降低制动磨损。
                </div>
                <div className="holo-chip holo-chip-green" style={{ alignSelf: "center" }}>
                  安全等级：A+
                </div>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}

function DnaBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span className="holo-text-dim" style={{ fontSize: 13 }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>{value}%</span>
      </div>
      <div className="holo-energy-bar">
        <div className="holo-energy-bar__fill" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}
