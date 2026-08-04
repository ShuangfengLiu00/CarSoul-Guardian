/**
 * Page 02 - Vehicle Universe Home (车辆宇宙主页)
 *
 * Main cockpit page. Central 3D scene with Vehicle3D + AgentGalaxy3D +
 * SpaceBackground. Left panel = vehicle soul core (EnergyRing), right panel =
 * today's alerts (CosmicAlert), bottom panel = agent status summary, top =
 * key stats.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  HoloCanvas,
  SpaceBackground,
  Vehicle3D,
  AgentGalaxy3D,
} from "@/components/three";
import { GlassPanel, EnergyRing, CosmicAlert, StatCard } from "@/components/hologram";
import { DemoBadge } from "@/components";
import {
  vehicleTwin,
  agents,
  alerts,
  getHealthColor,
  getHealthLabel,
} from "@/services/holoData";

export default function VehicleUniverse() {
  const navigate = useNavigate();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const activeAgents = agents.filter((a) => a.status !== "idle");

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      {/* Top stats bar */}
      <div
        className="holo-grid holo-grid-4 holo-anim-fade-in"
        style={{ position: "relative", zIndex: 2, marginBottom: 16 }}
      >
        <GlassPanel className="holo-glass-hover">
          <StatCard
            label="健康度"
            value={`${vehicleTwin.health}`}
            sub={getHealthLabel(vehicleTwin.health)}
            color={getHealthColor(vehicleTwin.health)}
            icon="💚"
          />
        </GlassPanel>
        <GlassPanel className="holo-glass-hover">
          <StatCard label="累计里程" value={`${vehicleTwin.mileage.toLocaleString()}`} sub="公里" color="#00f0ff" icon="🛣️" />
        </GlassPanel>
        <GlassPanel className="holo-glass-hover">
          <StatCard label="记忆条数" value={`${vehicleTwin.memoryCount.toLocaleString()}`} sub="条数字记忆" color="#ec4899" icon="🧠" />
        </GlassPanel>
        <GlassPanel className="holo-glass-hover">
          <StatCard label="活跃守护" value={`${activeAgents.length}`} sub={`/ ${agents.length} 个智能体`} color="#a855f7" icon="🤖" />
        </GlassPanel>
      </div>

      {/* Main 3-column layout */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: "320px 1fr 340px",
          gap: 16,
          minHeight: "calc(100vh - 180px)",
        }}
      >
        {/* Left panel: Vehicle Soul Core */}
        <GlassPanel
          className="holo-anim-slide-left holo-corners"
          title="车辆灵魂核"
          style={{ display: "flex", flexDirection: "column" }}
        >
          <div style={{ display: "flex", justifyContent: "center", padding: "24px 0" }}>
            <EnergyRing
              value={vehicleTwin.health}
              size={180}
              color={getHealthColor(vehicleTwin.health)}
              label="综合健康"
              subLabel={getHealthLabel(vehicleTwin.health)}
            />
          </div>
          <div className="holo-divider" />
          <div style={{ display: "flex", flexDirection: "column", gap: 14, padding: "8px 0" }}>
            <SoulRow label="车辆名称" value={vehicleTwin.name} />
            <SoulRow label="车型" value={vehicleTwin.model} />
            <SoulRow label="陪伴时长" value={`${vehicleTwin.age} 天`} accent="#00f0ff" />
            <SoulRow label="记忆记录" value={`${vehicleTwin.memoryCount.toLocaleString()} 条`} accent="#ec4899" />
            <SoulRow label="最后更新" value={vehicleTwin.lastUpdate} />
          </div>
          <div style={{ marginTop: "auto", paddingTop: 16 }}>
            <button className="holo-btn" style={{ width: "100%" }} onClick={() => navigate("/holo/twin")}>
              查看数字孪生
            </button>
          </div>
        </GlassPanel>

        {/* Center: 3D scene */}
        <GlassPanel
          className="holo-anim-fade-scale"
          style={{ padding: 0, overflow: "hidden", minHeight: 460, position: "relative" }}
        >
          <div className="holo-corners" style={{ position: "absolute", inset: 0, zIndex: 2, pointerEvents: "none" }} />
          <HoloCanvas cameraPosition={[0, 2, 8]}>
            <SpaceBackground />
            <Vehicle3D autoRotate rotationSpeed={0.4} scale={0.9} />
            <AgentGalaxy3D agents={agents} onAgentClick={(id) => setSelectedAgent(id)} selectedAgent={selectedAgent ?? undefined} />
          </HoloCanvas>
          <div
            className="holo-text-dim"
            style={{ position: "absolute", bottom: 12, left: 16, fontSize: 12, letterSpacing: "0.1em", zIndex: 2 }}
          >
            车辆宇宙 · 11 个智能体环绕守护
          </div>
          {selectedAgent && (
            <div
              className="holo-glass"
              style={{ position: "absolute", top: 12, right: 12, padding: "10px 14px", zIndex: 2, maxWidth: 220 }}
            >
              {(() => {
                const a = agents.find((x) => x.id === selectedAgent);
                if (!a) return null;
                return (
                  <>
                    <div style={{ fontSize: 14, fontWeight: 700, color: a.color }}>
                      {a.icon} {a.nameCn}
                    </div>
                    <div className="holo-text-dim" style={{ fontSize: 12, marginTop: 4 }}>
                      {a.role}
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </GlassPanel>

        {/* Right panel: Today's alerts */}
        <GlassPanel
          className="holo-anim-slide-right holo-corners"
          title="今日告警"
          style={{ display: "flex", flexDirection: "column" }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flex: 1, paddingRight: 4 }}>
            {alerts.map((alert, i) => (
              <div key={alert.id} className="holo-anim-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
                <CosmicAlert
                  level={alert.level}
                  title={alert.title}
                  detail={alert.detail}
                  time={alert.time}
                  source={alert.source}
                />
              </div>
            ))}
          </div>
          <div className="holo-divider" />
          <button className="holo-btn-ghost holo-btn" style={{ width: "100%" }} onClick={() => navigate("/holo/safety")}>
            进入安全守护
          </button>
        </GlassPanel>
      </div>

      {/* Bottom: Agent status summary */}
      <GlassPanel className="holo-anim-fade-in" style={{ marginTop: 16 }} title="智能体状态总览">
        <div className="holo-grid holo-grid-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          {agents.slice(0, 8).map((agent, i) => (
            <AgentMiniCard key={agent.id} agent={agent} delay={i * 0.08} onClick={() => navigate("/holo/agents")} />
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}

function SoulRow({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span className="holo-text-dim" style={{ fontSize: 13 }}>
        {label}
      </span>
      <span
        className="holo-text-bright"
        style={{ fontSize: 14, fontWeight: 600, color: accent, textShadow: accent ? `0 0 8px ${accent}66` : undefined }}
      >
        {value}
      </span>
    </div>
  );
}

function AgentMiniCard({
  agent,
  delay,
  onClick,
}: {
  agent: (typeof agents)[number];
  delay: number;
  onClick: () => void;
}) {
  const statusConfig = {
    working: { color: "#00ff9d", label: "运行中", anim: "holo-anim-pulse" },
    thinking: { color: "#ffb800", label: "思考中", anim: "holo-anim-pulse" },
    idle: { color: "#64748b", label: "待命", anim: "" },
  } as const;
  const cfg = statusConfig[agent.status];

  return (
    <div
      className={`holo-glass holo-glass-hover holo-anim-fade-in ${cfg.anim}`}
      style={{ animationDelay: `${delay}s`, padding: "12px 14px", borderRadius: 12, cursor: "pointer" }}
      onClick={onClick}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 22 }}>{agent.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: agent.color, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {agent.nameCn}
          </div>
          <div className="holo-text-dim" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: cfg.color, display: "inline-block", boxShadow: `0 0 6px ${cfg.color}` }} />
            {cfg.label}
          </div>
        </div>
      </div>
      <div className="holo-text-dim" style={{ fontSize: 11, marginTop: 6 }}>
        任务 {agent.tasksCompleted.toLocaleString()}
      </div>
    </div>
  );
}
