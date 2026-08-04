/**
 * Page 09 - Memory Ocean (记忆海洋)
 *
 * Wave-like background animation, memory cards floating in a grid, filter tabs
 * (全部/驾驶/维护/告警/里程碑), memory count stat at top, and an AI learning
 * insights section.
 */
import { useState, useMemo } from "react";
import { GlassPanel } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { memories, vehicleTwin } from "@/services/holoData";
import type { MemoryItem } from "@/services/holoData";

type FilterTab = "all" | "driving" | "maintenance" | "alert" | "milestone";

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

export default function MemoryOcean() {
  const [filter, setFilter] = useState<FilterTab>("all");

  const filtered = useMemo(() => {
    if (filter === "all") return memories;
    return memories.filter((m) => m.type === filter);
  }, [filter]);

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16, position: "relative" }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      {/* Wave background */}
      <WaveBackground />

      <div style={{ position: "relative", zIndex: 2 }}>
        {/* Header with count */}
        <div className="holo-anim-fade-in" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
          <div>
            <h2 className="holo-section-title">记忆海洋 · 车辆数字记忆</h2>
            <p className="holo-text-dim" style={{ fontSize: 13, margin: "4px 0 0" }}>
              每一段旅程都被铭记 · AI 持续学习进化
            </p>
          </div>
          <div className="holo-glass holo-corners" style={{ padding: "14px 28px", textAlign: "center" }}>
            <div className="holo-gradient-text holo-anim-glow-text" style={{ fontSize: 32, fontWeight: 900, lineHeight: 1 }}>
              {vehicleTwin.memoryCount.toLocaleString()}
            </div>
            <div className="holo-text-dim" style={{ fontSize: 11, marginTop: 4, letterSpacing: "0.1em" }}>条记忆记录</div>
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
        <div className="holo-grid holo-grid-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
          {filtered.map((memory, i) => (
            <MemoryCard key={memory.id} memory={memory} index={i} />
          ))}
        </div>

        {/* AI insights */}
        <GlassPanel className="holo-anim-fade-in holo-corners" style={{ marginTop: 20 }}>
          <div className="holo-section-title">AI 学习洞察</div>
          <div className="holo-grid holo-grid-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
            <InsightItem
              icon="📊"
              color="#00f0ff"
              title="驾驶习惯学习"
              text="已连续 7 天保持低能耗驾驶模式，能效评分 A+，AI 正在优化能量回收策略。"
            />
            <InsightItem
              icon="🔔"
              color="#ffb800"
              title="异常模式识别"
              text="检测到下坡路段频繁急刹，建议启用动能回收强档模式以提升能效与制动寿命。"
            />
            <InsightItem
              icon="🎵"
              color="#ec4899"
              title="情绪与行为关联"
              text="夜间播放轻音乐时驾驶风格明显平稳，音乐有助于改善驾驶习惯，置信度 78%。"
            />
          </div>
        </GlassPanel>
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
        <span className="holo-text-dim" style={{ fontSize: 12 }}>{memory.time}</span>
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
