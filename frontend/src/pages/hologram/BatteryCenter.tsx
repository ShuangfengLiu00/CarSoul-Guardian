/**
 * Page 05 - Battery Soul Center (电池灵魂中心)
 *
 * Large battery visualization with EnergyRing (health 98%), stats (temp, capacity,
 * cycle, voltage), 12 battery cells grid, ECharts 30-day health & temperature
 * trend line chart, and an AI prediction.
 */
import ReactECharts from "echarts-for-react";
import { GlassPanel, EnergyRing } from "@/components/hologram";
import { DemoBadge } from "@/components";
import {
  vehicleTwin,
  batteryTrendData,
  getHealthColor,
  getHealthLabel,
} from "@/services/holoData";

export default function BatteryCenter() {
  const b = vehicleTwin.battery;
  const color = getHealthColor(b.health);

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2 className="holo-section-title holo-anim-fade-in" style={{ position: "relative", zIndex: 2 }}>
        电池灵魂中心 · 数字生命之源
      </h2>

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: "360px 1fr",
          gap: 16,
        }}
      >
        {/* Left: Battery core visualization */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <GlassPanel className="holo-anim-fade-scale holo-corners" style={{ textAlign: "center" }}>
            <div className="holo-section-title" style={{ justifyContent: "center" }}>电池健康核</div>
            <div style={{ display: "flex", justifyContent: "center", padding: "20px 0 12px", position: "relative" }}>
              <div className="holo-anim-breathe" style={{ position: "absolute", width: 220, height: 220, borderRadius: "50%", background: `radial-gradient(circle, ${color}22 0%, transparent 70%)` }} />
              <EnergyRing
                value={b.health}
                size={200}
                color={color}
                label={`${b.health}%`}
                subLabel={getHealthLabel(b.health)}
                strokeWidth={12}
              />
            </div>
            <div style={{ fontSize: 40, marginTop: 8 }}>🔋</div>
            <div className="holo-text-dim" style={{ fontSize: 13 }}>{vehicleTwin.model} · 动力电池组</div>
          </GlassPanel>

          <GlassPanel className="holo-anim-fade-in holo-corners" title="核心参数">
            <Stat label="温度" value={`${b.temperature}`} unit="°C" color="#ffb800" />
            <Stat label="容量保持" value={`${b.capacity}`} unit="%" color="#00f0ff" />
            <Stat label="循环次数" value={`${b.cycle} / ${b.maxCycles}`} color="#a855f7" />
            <Stat label="电压" value={`${b.voltage}`} unit="V" color="#00ff9d" />
            <Stat label="电流" value={`${b.current}`} unit="A" color="#3b82f6" />
          </GlassPanel>
        </div>

        {/* Right: cells + trend + prediction */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 12 cells */}
          <GlassPanel className="holo-anim-fade-in holo-corners" title="12 电芯实时状态">
            <div className="holo-grid holo-grid-4" style={{ gridTemplateColumns: "repeat(6, 1fr)" }}>
              {b.cells.map((cell, i) => (
                <div
                  key={cell.id}
                  className="holo-glass holo-glass-hover holo-anim-fade-in holo-corners"
                  style={{ animationDelay: `${i * 0.06}s`, padding: "12px 8px", borderRadius: 10, textAlign: "center", position: "relative" }}
                >
                  <div className="holo-text-dim" style={{ fontSize: 10, letterSpacing: "0.1em" }}>CELL #{cell.id}</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: getHealthColor(cell.health), marginTop: 4 }}>
                    {cell.voltage.toFixed(2)}
                    <span className="holo-text-dim" style={{ fontSize: 11, fontWeight: 400 }}>V</span>
                  </div>
                  <div className="holo-text-dim" style={{ fontSize: 11, marginTop: 2 }}>{cell.temp.toFixed(1)}°C</div>
                  <div className="holo-energy-bar" style={{ marginTop: 8 }}>
                    <div className="holo-energy-bar__fill" style={{ width: `${cell.health}%`, background: getHealthColor(cell.health) }} />
                  </div>
                  <div style={{ fontSize: 10, marginTop: 4, color: getHealthColor(cell.health) }}>{cell.health.toFixed(1)}%</div>
                </div>
              ))}
            </div>
          </GlassPanel>

          {/* Trend chart */}
          <GlassPanel className="holo-anim-fade-in holo-corners" title="30 天电池健康与温度趋势">
            <ReactECharts option={trendOption} style={{ height: 280 }} />
          </GlassPanel>

          {/* AI prediction */}
          <GlassPanel className="holo-anim-fade-in holo-corners">
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ fontSize: 36 }} className="holo-anim-float">🔮</div>
              <div>
                <div className="holo-text-dim" style={{ fontSize: 12, letterSpacing: "0.1em" }}>AI 寿命预测</div>
                <div className="holo-text-green holo-anim-glow-text" style={{ fontSize: 22, fontWeight: 800 }}>
                  状态健康 · 剩余 {b.remainingLife} 年
                </div>
                <div className="holo-text-dim" style={{ fontSize: 12, marginTop: 4 }}>
                  衰减率 0.8%/年，优于行业平均 1.5%，预计到达 80% 容量需 {b.remainingLife} 年
                </div>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, unit, color }: { label: string; value: string; unit?: string; color?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 0" }}>
      <span className="holo-text-dim" style={{ fontSize: 13 }}>{label}</span>
      <span className="holo-text-bright" style={{ fontSize: 16, fontWeight: 700, color }}>
        {value}
        {unit && <span className="holo-text-dim" style={{ fontSize: 12, marginLeft: 3, fontWeight: 400 }}>{unit}</span>}
      </span>
    </div>
  );
}

const trendOption = {
  backgroundColor: "transparent",
  textStyle: { color: "#e2e8f0" },
  tooltip: {
    trigger: "axis",
    backgroundColor: "rgba(5,8,22,0.9)",
    borderColor: "rgba(0,240,255,0.3)",
    textStyle: { color: "#e2e8f0" },
  },
  legend: {
    data: ["健康度", "温度"],
    textStyle: { color: "#94a3b8" },
    top: 0,
  },
  xAxis: {
    type: "category",
    data: batteryTrendData.map((d) => `D${d.day}`),
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
    axisLabel: { color: "#94a3b8", fontSize: 10, interval: 4 },
  },
  yAxis: [
    {
      type: "value",
      name: "健康度",
      min: 97,
      max: 99,
      nameTextStyle: { color: "#94a3b8" },
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
      axisLabel: { color: "#94a3b8" },
    },
    {
      type: "value",
      name: "温度",
      min: 25,
      max: 38,
      nameTextStyle: { color: "#94a3b8" },
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
      splitLine: { show: false },
      axisLabel: { color: "#94a3b8", formatter: "{value}°C" },
    },
  ],
  series: [
    {
      name: "健康度",
      type: "line",
      data: batteryTrendData.map((d) => Number(d.health.toFixed(2))),
      smooth: true,
      symbol: "none",
      lineStyle: { color: "#00ff9d", width: 2 },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(0,255,157,0.25)" },
            { offset: 1, color: "rgba(0,255,157,0)" },
          ],
        },
      },
    },
    {
      name: "温度",
      type: "line",
      yAxisIndex: 1,
      data: batteryTrendData.map((d) => Number(d.temp.toFixed(1))),
      smooth: true,
      symbol: "none",
      lineStyle: { color: "#ffb800", width: 2 },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(255,184,0,0.2)" },
            { offset: 1, color: "rgba(255,184,0,0)" },
          ],
        },
      },
    },
  ],
};
