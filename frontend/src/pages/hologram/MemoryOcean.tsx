/**
 * Page 09 - Memory Ocean (记忆海洋)
 *
 * 真实数据来源：Guardian `GET /api/digital-twin/{vehicleId}/memories`
 * （直接落盘 carsoul_dev.db，非前端 Mock）。车辆身份由 useCurrentVehicle
 * 统一提供整数 vehicle_id。取不到数据时显示「暂无记忆」，绝不回填 Mock。
 */
import { useState, useMemo, useEffect } from "react";
import { GlassPanel, DemoBadge } from "@/components";
import { useCurrentVehicle } from "@/hooks/useCurrentVehicle";
import { digitalTwinService } from "@/services/digitalTwinService";
import type { DigitalTwinMemory } from "@/services/digitalTwinService";
import type { MemoryItem } from "@/services/holoData";
import { Empty, Spin } from "antd";

type FilterTab = "all" | "driving" | "maintenance" | "alert" | "emotion" | "milestone";

const TABS: { key: FilterTab; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "driving", label: "驾驶" },
  { key: "maintenance", label: "维护" },
  { key: "alert", label: "告警" },
  { key: "milestone", label: "里程碑" },
];

const TYPE_COLOR: Record<string, string> = {
  driving: "#00f0ff",
  maintenance: "#ffb800",
  alert: "#ff3860",
  emotion: "#ec4899",
  milestone: "#00ff9d",
};

const TYPE_ICON: Record<string, string> = {
  driving: "🚗",
  maintenance: "🔧",
  alert: "⚠️",
  emotion: "🎵",
  milestone: "🏆",
};

/** 真实记忆类型 → MemoryItem 展示类型 */
function mapMemoryType(t: string): MemoryItem["type"] {
  switch (t) {
    case "warning": return "alert";
    case "recovery": return "maintenance";
    case "emotion": return "emotion";
    case "milestone": return "milestone";
    case "habit":
    case "event":
    case "preference":
    case "context":
    default: return "driving";
  }
}

function fmtTime(iso: string): string {
  // 2026-08-08T21:20:19 → 2026-08-08 21:20
  return iso.replace("T", " ").slice(0, 16);
}

function toMemoryItem(m: DigitalTwinMemory): MemoryItem {
  const type = mapMemoryType(m.memory_type);
  return {
    id: String(m.id),
    time: fmtTime(m.created_time),
    type,
    content: m.content,
    aiLearning: `重要性 ${m.importance}/10`,
    confidence: m.importance * 10,
    icon: TYPE_ICON[type],
  };
}

export default function MemoryOcean() {
  const { vehicle } = useCurrentVehicle();
  const [filter, setFilter] = useState<FilterTab>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!vehicle) return;
    let alive = true;
    setLoading(true);
    setError(false);
    digitalTwinService
      .getMemories(vehicle.id, 100)
      .then((data) => {
        if (!alive) return;
        setItems(data.items.map(toMemoryItem));
        setTotal(data.total);
      })
      .catch(() => {
        if (alive) setError(true);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [vehicle]);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((m) => m.type === filter);
  }, [filter, items]);

  // 真实聚合洞察（来自真实记忆分布，非写死文案）
  const insight = useMemo(() => {
    const byType: Record<string, number> = {};
    items.forEach((m) => (byType[m.type] = (byType[m.type] || 0) + 1));
    const top = Object.entries(byType).sort((a, b) => b[1] - a[1])[0];
    return { byType, top };
  }, [items]);

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16, position: "relative" }}>
      <DemoBadge level="L3" visible />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <WaveBackground />

      <div style={{ position: "relative", zIndex: 2 }}>
        {/* Header with count */}
        <div className="holo-anim-fade-in" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
          <div>
            <h2 className="holo-section-title">记忆海洋 · 车辆数字记忆</h2>
            <p className="holo-text-dim" style={{ fontSize: 13, margin: "4px 0 0" }}>
              每一段旅程都被铭记 · 真实记忆落盘于车辆数字生命档案
            </p>
          </div>
          <div className="holo-glass holo-corners" style={{ padding: "14px 28px", textAlign: "center" }}>
            <div className="holo-gradient-text holo-anim-glow-text" style={{ fontSize: 32, fontWeight: 900, lineHeight: 1 }}>
              {loading ? "…" : total.toLocaleString()}
            </div>
            <div className="holo-text-dim" style={{ fontSize: 11, marginTop: 4, letterSpacing: "0.1em" }}>条真实记忆</div>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="holo-anim-fade-in" style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={filter === tab.key ? "holo-btn" : "holo-btn holo-btn-ghost"}
              style={{ padding: "8px 20px", fontSize: 14 }}
              onClick={() => setFilter(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Memory grid */}
        {loading ? (
          <div style={{ textAlign: "center", padding: 80 }}>
            <Spin size="large" />
          </div>
        ) : error ? (
          <GlassPanel className="holo-anim-fade-in holo-corners" style={{ textAlign: "center", padding: 60 }}>
            <Empty description={<span className="holo-text-dim">记忆数据取数失败，请稍后重试</span>} />
          </GlassPanel>
        ) : filtered.length === 0 ? (
          <GlassPanel className="holo-anim-fade-in holo-corners" style={{ textAlign: "center", padding: 60 }}>
            <Empty description={<span className="holo-text-dim">暂无该类型记忆</span>} />
          </GlassPanel>
        ) : (
          <div className="holo-grid holo-grid-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
            {filtered.map((memory, i) => (
              <MemoryCard key={memory.id} memory={memory} index={i} />
            ))}
          </div>
        )}

        {/* AI insights — 来自真实记忆分布的聚合，非写死 */}
        {!loading && !error && items.length > 0 && (
          <GlassPanel className="holo-anim-fade-in holo-corners" style={{ marginTop: 20 }}>
            <div className="holo-section-title">AI 学习洞察</div>
            <div className="holo-grid holo-grid-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
              <InsightItem
                icon="🧠"
                color="#00f0ff"
                title="真实记忆总量"
                text={`本车已积累 ${total} 条真实数字记忆，全部落盘于车辆数字生命档案。`}
              />
              <InsightItem
                icon="📊"
                color="#ffb800"
                title="主导记忆类型"
                text={
                  insight.top
                    ? `占比最高为「${insight.top[0]}」类记忆，共 ${insight.top[1]} 条。`
                    : "暂无可分析类型。"
                }
              />
              <InsightItem
                icon="🔍"
                color="#ec4899"
                title="数据来源"
                text="记忆由系统基于真实出行、保养与告警事件自动沉淀，可经数字生命接口真实写入。"
              />
            </div>
          </GlassPanel>
        )}
      </div>
    </div>
  );
}

function MemoryCard({ memory, index }: { memory: MemoryItem; index: number }) {
  const color = TYPE_COLOR[memory.type] ?? "#94a3b8";
  return (
    <div
      className="holo-glass holo-glass-hover holo-corners holo-anim-fade-in holo-anim-float"
      style={{
        animationDelay: `${index * 0.1}s`,
        padding: 18,
        borderRadius: 14,
        borderLeft: `3px solid ${color}`,
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <span style={{ fontSize: 24 }}>{memory.icon}</span>
        <span style={{ fontSize: 12 }} className="holo-text-dim">{memory.time}</span>
        <span className="holo-chip" style={{ marginLeft: "auto", borderColor: `${color}55`, color, background: `${color}11` }}>
          {memory.type}
        </span>
      </div>

      <p className="holo-text" style={{ fontSize: 13, lineHeight: 1.7, margin: "0 0 12px" }}>
        {memory.content}
      </p>

      {memory.aiLearning && (
        <div className="holo-glass" style={{ padding: 10, borderRadius: 8, marginBottom: 10 }}>
          <div className="holo-text-cyan" style={{ fontSize: 11, marginBottom: 4 }}>🤖 AI 学习</div>
          <div className="holo-text-dim" style={{ fontSize: 12, lineHeight: 1.5 }}>{memory.aiLearning}</div>
        </div>
      )}

      {typeof memory.confidence === "number" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span className="holo-text-dim" style={{ fontSize: 11 }}>置信度</span>
            <span style={{ fontSize: 11, fontWeight: 700, color }}>{memory.confidence}%</span>
          </div>
          <div className="holo-energy-bar">
            <div className="holo-energy-bar__fill" style={{ width: `${memory.confidence}%`, background: color }} />
          </div>
        </div>
      )}
    </div>
  );
}

function InsightItem({ icon, color, title, text }: { icon: string; color: string; title: string; text: string }) {
  return (
    <div className="holo-glass holo-glass-hover" style={{ padding: 16, borderRadius: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 20 }}>{icon}</span>
        <span style={{ fontSize: 14, fontWeight: 700, color }}>{title}</span>
      </div>
      <p className="holo-text-dim" style={{ fontSize: 12, lineHeight: 1.6, margin: 0 }}>{text}</p>
    </div>
  );
}

function WaveBackground() {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1, pointerEvents: "none", overflow: "hidden" }}>
      <svg
        style={{ position: "absolute", bottom: 0, left: 0, width: "200%", height: "40%", opacity: 0.15 }}
        viewBox="0 0 1440 320"
        preserveAspectRatio="none"
      >
        <path
          fill="#00f0ff"
          d="M0,160 C320,260 640,60 960,160 C1280,260 1440,160 1440,160 L1440,320 L0,320 Z"
        >
          <animate attributeName="d" dur="8s" repeatCount="indefinite"
            values="M0,160 C320,260 640,60 960,160 C1280,260 1440,160 1440,160 L1440,320 L0,320 Z;
                    M0,180 C320,80 640,240 960,140 C1280,60 1440,180 1440,180 L1440,320 L0,320 Z;
                    M0,160 C320,260 640,60 960,160 C1280,260 1440,160 1440,160 L1440,320 L0,320 Z" />
        </path>
      </svg>
      <svg
        style={{ position: "absolute", bottom: 0, left: 0, width: "200%", height: "30%", opacity: 0.1 }}
        viewBox="0 0 1440 320"
        preserveAspectRatio="none"
      >
        <path fill="#a855f7" d="M0,200 C400,120 800,280 1440,200 L1440,320 L0,320 Z">
          <animate attributeName="d" dur="10s" repeatCount="indefinite"
            values="M0,200 C400,120 800,280 1440,200 L1440,320 L0,320 Z;
                    M0,220 C400,300 800,140 1440,220 L1440,320 L0,320 Z;
                    M0,200 C400,120 800,280 1440,200 L1440,320 L0,320 Z" />
        </path>
      </svg>
    </div>
  );
}
