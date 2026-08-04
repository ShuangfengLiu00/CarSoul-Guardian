/**
 * Page 04 - Health Dashboard (健康仪表盘)
 *
 * Large central EnergyRing for overall health, 6 component health cards each
 * with an EnergyRing, an ECharts radar chart (healthRadarData), a weekly
 * health score trend line chart (drivingDNA.weeklyScore), and an AI summary.
 */
import ReactECharts from "echarts-for-react";
import { GlassPanel, EnergyRing } from "@/components/hologram";
import { DemoBadge } from "@/components";
import {
  vehicleTwin,
  healthRadarData,
  getHealthColor,
  getHealthLabel,
} from "@/services/holoData";

const COMPONENTS = [
  { name: "电池", value: vehicleTwin.battery.health, icon: "🔋" },
  { name: "电机", value: vehicleTwin.motor.health, icon: "⚡" },
  { name: "制动", value: vehicleTwin.brake.health, icon: "🛑" },
  { name: "轮胎", value: vehicleTwin.tire.health, icon: "🛞" },
  { name: "底盘", value: vehicleTwin.chassis.health, icon: "🔩" },
  { name: "安全", value: 96, icon: "🛡️" },
];

export default function HealthDashboard() {
  const overallColor = getHealthColor(vehicleTwin.health);

  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2 className="holo-section-title holo-anim-fade-in" style={{ position: "relative", zIndex: 2 }}>
        健康仪表盘 · 车辆生命体征
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
        {/* Left: Central health ring + summary */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <GlassPanel className="holo-anim-fade-scale holo-corners" style={{ textAlign: "center" }}>
            <div className="holo-section-title" style={{ justifyContent: "center" }}>综合健康度</div>
            <div style={{ display: "flex", justifyContent: "center", padding: "16px 0 8px" }}>
              <EnergyRing
                value={vehicleTwin.health}
                size={200}
                color={overallColor}
                label={`${vehicleTwin.health}`}
                subLabel={getHealthLabel(vehicleTwin.health)}
                strokeWidth={12}
              />
            </div>
            <div className="holo-text-dim" style={{ fontSize: 13, marginBottom: 12 }}>
              优于同级车辆 85%
            </div>
          </GlassPanel>

          <GlassPanel className="holo-anim-fade-in holo-corners" title="AI 健康摘要">
            <p className="holo-text" style={{ fontSize: 13, lineHeight: 1.8, margin: 0 }}>
              综合健康度 <span className="holo-text-green" style={{ fontWeight: 700 }}>96%</span>，处于优秀水平。
              电池与电机状态最佳，制动系统因前刹车片磨损略需关注。
              建议保持当前驾驶习惯，预计下一次保养在 <span className="holo-text-cyan">3,544km</span> 后进行。
            </p>
            <div className="holo-divider" />
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <MiniStat label="陪伴天数" value={`${vehicleTwin.age}`} />
              <MiniStat label="累计里程" value={`${(vehicleTwin.mileage / 1000).toFixed(1)}k`} />
              <MiniStat label="记忆条数" value={`${(vehicleTwin.memoryCount / 1000).toFixed(1)}k`} />
            </div>
          </GlassPanel>
        </div>

        {/* Right: charts + component cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 6 component cards */}
          <div className="holo-grid holo-grid-3">
            {COMPONENTS.map((c, i) => (
              <GlassPanel
                key={c.name}
                className="holo-glass-hover holo-anim-fade-in holo-corners"
                style={{ animationDelay: `${i * 0.1}s`, display: "flex", alignItems: "center", gap: 14 }}
              >
                <EnergyRing value={c.value} size={72} color={getHealthColor(c.value)} strokeWidth={6} />
                <div>
                  <div className="holo-text-bright" style={{ fontSize: 15, fontWeight: 700 }}>
                    {c.icon} {c.name}
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: getHealthColor(c.value) }}>{c.value}%</div>
                  <div className="holo-text-dim" style={{ fontSize: 11 }}>{getHealthLabel(c.value)}</div>
                </div>
              </GlassPanel>
            ))}
          </div>

          {/* Charts row */}
          <div className="holo-grid holo-grid-2">
            <GlassPanel className="holo-anim-fade-in holo-corners" title="健康雷达">
              <ReactECharts option={radarOption} style={{ height: 300 }} />
            </GlassPanel>
            <GlassPanel className="holo-anim-fade-in holo-corners" title="本周健康评分趋势">
              <ReactECharts option={trendOption} style={{ height: 300 }} />
            </GlassPanel>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div className="holo-text-bright" style={{ fontSize: 18, fontWeight: 700 }}>{value}</div>
      <div className="holo-text-dim" style={{ fontSize: 11 }}>{label}</div>
    </div>
  );
}

const radarOption = {
  backgroundColor: "transparent",
  textStyle: { color: "#e2e8f0" },
  tooltip: { backgroundColor: "rgba(5,8,22,0.9)", borderColor: "rgba(0,240,255,0.3)", textStyle: { color: "#e2e8f0" } },
  radar: {
    indicator: healthRadarData.map((d) => ({ name: d.name, max: d.fullMark })),
    axisName: { color: "#94a3b8", fontSize: 12 },
    splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    splitArea: { areaStyle: { color: ["rgba(0,240,255,0.02)", "rgba(0,240,255,0.04)"] } },
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
  },
  series: [
    {
      type: "radar",
      data: [
        {
          value: healthRadarData.map((d) => d.value),
          name: "当前健康",
          areaStyle: { color: "rgba(0,240,255,0.2)" },
          lineStyle: { color: "#00f0ff", width: 2 },
          itemStyle: { color: "#00f0ff" },
        },
      ],
    },
  ],
};

const weekDays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const trendOption = {
  backgroundColor: "transparent",
  textStyle: { color: "#e2e8f0" },
  tooltip: { trigger: "axis", backgroundColor: "rgba(5,8,22,0.9)", borderColor: "rgba(0,240,255,0.3)", textStyle: { color: "#e2e8f0" } },
  xAxis: {
    type: "category",
    data: weekDays,
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
    axisLabel: { color: "#94a3b8" },
  },
  yAxis: {
    type: "value",
    min: 80,
    max: 100,
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
    splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    axisLabel: { color: "#94a3b8" },
  },
  series: [
    {
      type: "line",
      data: vehicleTwin.drivingDNA.weeklyScore,
      smooth: true,
      symbol: "circle",
      symbolSize: 8,
      lineStyle: { color: "#00ff9d", width: 3, shadowColor: "rgba(0,255,157,0.5)", shadowBlur: 10 },
      itemStyle: { color: "#00ff9d" },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(0,255,157,0.3)" },
            { offset: 1, color: "rgba(0,255,157,0)" },
          ],
        },
      },
    },
  ],
};
