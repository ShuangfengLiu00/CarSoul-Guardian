/**
 * Page 11 - Agent Galaxy (智能体星系)
 *
 * 3D scene with AgentGalaxy3D showing all 11 agents orbiting. Agent list on the
 * right with status indicators. Click an agent to see details. Manager Agent is
 * highlighted in the center. Connection lines visualization.
 */
import { useState } from "react";
import { HoloCanvas, SpaceBackground, AgentGalaxy3D } from "@/components/three";
import { GlassPanel, DataStream } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { agents } from "@/services/holoData";
import type { AgentInfo } from "@/services/holoData";

const STATUS_CONFIG = {
  working: { color: "#00ff9d", label: "运行中", dotAnim: "holo-anim-pulse" },
  thinking: { color: "#ffb800", label: "思考中", dotAnim: "holo-anim-pulse" },
  idle: { color: "#64748b", label: "待命", dotAnim: "" },
} as const;

export default function AgentGalaxyPage() {
  const [selectedId, setSelectedId] = useState<string>("manager");
  const selected = agents.find((a) => a.id === selectedId) ?? agents[0];
  const manager = agents.find((a) => a.id === "manager")!;
  const orbitAgents = agents.filter((a) => a.id !== "manager");

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2 className="holo-section-title holo-anim-fade-in" style={{ position: "relative", zIndex: 2 }}>
        智能体星系 · 11 守护者协同
      </h2>

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: "1fr 380px",
          gap: 16,
          minHeight: "calc(100vh - 110px)",
        }}
      >
        {/* Left: 3D galaxy */}
        <GlassPanel className="holo-anim-fade-scale holo-corners" style={{ padding: 0, overflow: "hidden", position: "relative" }}>
          <HoloCanvas cameraPosition={[0, 6, 9]}>
            <SpaceBackground />
            <AgentGalaxy3D
              agents={agents}
              selectedAgent={selectedId}
              onAgentClick={(id) => setSelectedId(id)}
              showConnections
            />
          </HoloCanvas>

          {/* Manager highlight label */}
          <div
            className="holo-glass holo-anim-fade-in"
            style={{ position: "absolute", top: 16, left: 16, padding: "10px 16px", zIndex: 2, borderLeft: `3px solid ${manager.color}` }}
          >
            <div style={{ fontSize: 13, fontWeight: 700, color: manager.color }}>{manager.icon} {manager.nameCn}</div>
            <div className="holo-text-dim" style={{ fontSize: 11 }}>星系中心 · 总调度</div>
          </div>

          {/* Connection legend */}
          <div className="holo-text-dim" style={{ position: "absolute", bottom: 12, left: 16, fontSize: 12, zIndex: 2 }}>
            <span className="holo-text-cyan">━━</span> 守护连接 · {orbitAgents.length} 个智能体环绕运行
          </div>
        </GlassPanel>

        {/* Right: Agent list + detail */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Selected agent detail */}
          <GlassPanel className="holo-anim-slide-right holo-corners" title="智能体详情">
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
              <div
                className="holo-anim-breathe"
                style={{
                  width: 56, height: 56, borderRadius: "50%",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 28, background: `${selected.color}22`, border: `2px solid ${selected.color}`,
                  boxShadow: `0 0 20px ${selected.color}55`,
                }}
              >
                {selected.icon}
              </div>
              <div>
                <div className="holo-text-bright" style={{ fontSize: 18, fontWeight: 800, color: selected.color }}>
                  {selected.nameCn}
                </div>
                <div className="holo-text-dim" style={{ fontSize: 12 }}>{selected.name} · {selected.role}</div>
              </div>
            </div>

            <DataStream lines={3} />

            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
              <DetailRow label="状态" value={
                <span style={{ color: STATUS_CONFIG[selected.status].color, display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <span className={STATUS_CONFIG[selected.status].dotAnim} style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS_CONFIG[selected.status].color, display: "inline-block", boxShadow: `0 0 8px ${STATUS_CONFIG[selected.status].color}` }} />
                  {STATUS_CONFIG[selected.status].label}
                </span>
              } />
              <DetailRow label="完成任务" value={`${selected.tasksCompleted.toLocaleString()}`} />
              <DetailRow label="监控范围" value={selected.monitoring} />
              <DetailRow label="置信度" value={`${(selected.confidence * 100).toFixed(0)}%`} accent="#00f0ff" />
            </div>

            <div className="holo-divider" />
            <div className="holo-text-dim" style={{ fontSize: 12, marginBottom: 4 }}>最近决策</div>
            <div className="holo-glass" style={{ padding: 12, borderRadius: 10, borderLeft: `3px solid ${selected.color}` }}>
              <span className="holo-text" style={{ fontSize: 13, lineHeight: 1.6 }}>{selected.latestDecision}</span>
            </div>
          </GlassPanel>

          {/* Agent list */}
          <GlassPanel className="holo-anim-slide-right holo-corners" style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }} title="全部智能体">
            <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, paddingRight: 4 }}>
              {agents.map((agent, i) => (
                <AgentListItem
                  key={agent.id}
                  agent={agent}
                  selected={agent.id === selectedId}
                  delay={i * 0.05}
                  onClick={() => setSelectedId(agent.id)}
                />
              ))}
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span className="holo-text-dim" style={{ fontSize: 12 }}>{label}</span>
      <span className="holo-text-bright" style={{ fontSize: 13, fontWeight: 600, color: accent }}>{value}</span>
    </div>
  );
}

function AgentListItem({ agent, selected, delay, onClick }: { agent: AgentInfo; selected: boolean; delay: number; onClick: () => void }) {
  const cfg = STATUS_CONFIG[agent.status];
  return (
    <div
      className={`holo-glass holo-glass-hover holo-anim-fade-in ${selected ? "holo-anim-pulse" : ""}`}
      style={{
        animationDelay: `${delay}s`,
        padding: "10px 12px",
        borderRadius: 10,
        cursor: "pointer",
        borderLeft: selected ? `3px solid ${agent.color}` : "3px solid transparent",
        background: selected ? `${agent.color}11` : undefined,
      }}
      onClick={onClick}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 20 }}>{agent.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: agent.color, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {agent.nameCn}
          </div>
          <div className="holo-text-dim" style={{ fontSize: 11 }}>{agent.role}</div>
        </div>
        <span className={cfg.dotAnim} style={{ width: 8, height: 8, borderRadius: "50%", background: cfg.color, display: "inline-block", boxShadow: `0 0 8px ${cfg.color}`, flexShrink: 0 }} />
      </div>
    </div>
  );
}
