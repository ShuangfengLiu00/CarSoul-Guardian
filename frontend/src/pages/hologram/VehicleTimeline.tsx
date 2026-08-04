/**
 * Page 10 - Vehicle Timeline (车辆生命时间线)
 *
 * Vertical timeline with timelineEvents data. Each event has date, title,
 * description, icon. Different colors for event types (birth=purple,
 * mileage=cyan, maintenance=amber, milestone=green). Current position
 * highlighted. Future events shown with dashed style. Stats at top.
 */
import { GlassPanel } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { timelineEvents, vehicleTwin } from "@/services/holoData";
import type { TimelineEvent } from "@/services/holoData";

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  birth: { color: "#a855f7", label: "诞生" },
  mileage: { color: "#00f0ff", label: "里程" },
  maintenance: { color: "#ffb800", label: "保养" },
  alert: { color: "#ff3860", label: "告警" },
  milestone: { color: "#00ff9d", label: "里程碑" },
};

export default function VehicleTimeline() {
  const currentIndex = timelineEvents.findIndex((e) => e.title === "现在");

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2 className="holo-section-title holo-anim-fade-in" style={{ position: "relative", zIndex: 2 }}>
        车辆生命时间线 · 数字生命轨迹
      </h2>

      {/* Stats */}
      <div className="holo-grid holo-grid-3 holo-anim-fade-in" style={{ position: "relative", zIndex: 2, marginBottom: 24 }}>
        <GlassPanel className="holo-glass-hover holo-corners holo-stat">
          <div className="holo-stat__label">陪伴天数</div>
          <div className="holo-stat__value holo-text-cyan">{vehicleTwin.age}</div>
          <div className="holo-stat__sub">天 · 自 2025-06-20 起</div>
        </GlassPanel>
        <GlassPanel className="holo-glass-hover holo-corners holo-stat">
          <div className="holo-stat__label">累计里程</div>
          <div className="holo-stat__value holo-text-green">{vehicleTwin.mileage.toLocaleString()}</div>
          <div className="holo-stat__sub">公里</div>
        </GlassPanel>
        <GlassPanel className="holo-glass-hover holo-corners holo-stat">
          <div className="holo-stat__label">保养次数</div>
          <div className="holo-stat__value holo-text-amber">4</div>
          <div className="holo-stat__sub">次常规保养</div>
        </GlassPanel>
      </div>

      {/* Timeline */}
      <GlassPanel className="holo-anim-fade-in holo-corners" style={{ position: "relative", zIndex: 2, maxWidth: 820, margin: "0 auto" }}>
        <div style={{ position: "relative", padding: "8px 0" }}>
          {/* Vertical line */}
          <div
            style={{
              position: "absolute",
              left: 32,
              top: 16,
              bottom: 16,
              width: 2,
              background: "linear-gradient(180deg, #a855f7 0%, #00f0ff 50%, #ffb800 100%)",
              boxShadow: "0 0 12px rgba(0,240,255,0.3)",
            }}
          />

          {timelineEvents.map((event, i) => (
            <TimelineNode
              key={event.id}
              event={event}
              index={i}
              isCurrent={i === currentIndex}
              isFuture={currentIndex >= 0 && i > currentIndex}
            />
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}

function TimelineNode({
  event,
  index,
  isCurrent,
  isFuture,
}: {
  event: TimelineEvent;
  index: number;
  isCurrent: boolean;
  isFuture: boolean;
}) {
  const cfg = TYPE_CONFIG[event.type] ?? TYPE_CONFIG.mileage;

  return (
    <div
      className="holo-anim-fade-in"
      style={{
        position: "relative",
        paddingLeft: 72,
        paddingBottom: 28,
        opacity: isFuture ? 0.55 : 1,
        animationDelay: `${index * 0.1}s`,
      }}
    >
      {/* Dot */}
      <div
        className={`holo-anim-fade-in ${isCurrent ? "holo-anim-pulse" : ""}`}
        style={{
          position: "absolute",
          left: 24,
          top: 4,
          width: 18,
          height: 18,
          borderRadius: "50%",
          background: cfg.color,
          border: `3px solid ${isCurrent ? "#fff" : "rgba(5,8,22,0.8)"}`,
          boxShadow: `0 0 ${isCurrent ? 20 : 10}px ${cfg.color}`,
          zIndex: 2,
          transform: "translateX(0)",
          animationDelay: `${index * 0.1}s`,
        }}
      >
        {isCurrent && <div className="holo-alert-wave" />}
      </div>

      {/* Content card */}
      <div
        className={`holo-glass holo-glass-hover holo-corners ${isFuture ? "" : ""}`}
        style={{
          padding: 16,
          borderRadius: 12,
          borderLeft: `3px solid ${cfg.color}`,
          borderStyle: isFuture ? "dashed" : "solid",
          borderWidth: isFuture ? 1 : undefined,
          borderColor: isFuture ? `${cfg.color}55` : undefined,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 22 }}>{event.icon}</span>
          <span className="holo-text-bright" style={{ fontSize: 16, fontWeight: 700 }}>{event.title}</span>
          {isCurrent && (
            <span className="holo-chip holo-chip-green holo-anim-pulse" style={{ marginLeft: "auto" }}>
              当前
            </span>
          )}
          {isFuture && (
            <span className="holo-chip holo-chip-purple" style={{ marginLeft: "auto" }}>
              未来
            </span>
          )}
          {!isCurrent && !isFuture && (
            <span className="holo-chip" style={{ marginLeft: "auto", borderColor: `${cfg.color}55`, color: cfg.color, background: `${cfg.color}11` }}>
              {cfg.label}
            </span>
          )}
        </div>
        <div className="holo-text-dim" style={{ fontSize: 12, marginBottom: 6, letterSpacing: "0.05em" }}>
          {event.date}
        </div>
        <p className="holo-text" style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>
          {event.description}
        </p>
      </div>
    </div>
  );
}
