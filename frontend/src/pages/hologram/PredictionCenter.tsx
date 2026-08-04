/**
 * Page 15 - Prediction Center (未来预测中心)
 *
 * Timeline from NOW to 2030, 4 prediction cards with risk indicators, an ECharts
 * line chart for 6-year vehicle value prediction (valuePredictionData), and each
 * prediction shows component, current vs future value, days remaining, risk level,
 * reason and suggestion. Purple gradient title.
 */
import ReactECharts from "echarts-for-react";
import { GlassPanel } from "@/components/hologram";
import { DemoBadge } from "@/components";
import { predictions, valuePredictionData, getRiskColor } from "@/services/holoData";

const RISK_LABEL: Record<string, string> = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

const TIMELINE = [
  { label: "NOW", year: "2026", desc: "当前状态" },
  { label: "+45天", year: "2026", desc: "刹车片更换" },
  { label: "+1年", year: "2027", desc: "电池容量监测" },
  { label: "+4年", year: "2030", desc: "残值评估" },
];

export default function PredictionCenter() {
  return (
    <div className="holo-page" style={{ minHeight: "100vh", padding: 16 }}>
      <DemoBadge />
      <div className="holo-scanline" style={{ position: "fixed", inset: 0, zIndex: 0 }} />

      <h2
        className="holo-gradient-text-purple holo-anim-glow-text holo-anim-fade-in"
        style={{ position: "relative", zIndex: 2, fontSize: 26, fontWeight: 900, marginBottom: 4 }}
      >
        AI 未来预测
      </h2>
      <p className="holo-text-dim holo-anim-fade-in" style={{ position: "relative", zIndex: 2, fontSize: 13, margin: "0 0 20px" }}>
        基于数字孪生与历史数据 · 预见车辆未来
      </p>

      {/* Timeline */}
      <GlassPanel className="holo-anim-fade-in holo-corners" style={{ marginBottom: 16 }}>
        <div style={{ position: "relative", display: "flex", justifyContent: "space-between", padding: "24px 16px 8px" }}>
          <div style={{ position: "absolute", left: 24, right: 24, top: 38, height: 2, background: "linear-gradient(90deg, #00f0ff, #a855f7, #ff3860)" }} />
          {TIMELINE.map((t, i) => (
            <div key={i} style={{ position: "relative", zIndex: 1, textAlign: "center", flex: 1 }}>
              <div
                className="holo-anim-pulse"
                style={{
                  width: 16, height: 16, borderRadius: "50%", margin: "0 auto 10px",
                  background: i === 0 ? "#00f0ff" : i === TIMELINE.length - 1 ? "#ff3860" : "#a855f7",
                  boxShadow: `0 0 12px ${i === 0 ? "#00f0ff" : i === TIMELINE.length - 1 ? "#ff3860" : "#a855f7"}`,
                }}
              />
              <div className="holo-text-bright" style={{ fontSize: 14, fontWeight: 700 }}>{t.label}</div>
              <div className="holo-text-dim" style={{ fontSize: 11 }}>{t.year} · {t.desc}</div>
            </div>
          ))}
        </div>
      </GlassPanel>

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        {/* Left: prediction cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {predictions.map((p, i) => {
            const color = getRiskColor(p.risk);
            return (
              <GlassPanel
                key={p.component}
                className="holo-glass-hover holo-anim-fade-in holo-corners"
                style={{ animationDelay: `${i * 0.1}s`, borderLeft: `3px solid ${color}` }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <span className="holo-text-bright" style={{ fontSize: 16, fontWeight: 700 }}>{p.component}</span>
                  <span className="holo-chip" style={{ borderColor: `${color}55`, color, background: `${color}11` }}>
                    {RISK_LABEL[p.risk]}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
                  <div style={{ textAlign: "center" }}>
                    <div className="holo-text-dim" style={{ fontSize: 11 }}>当前</div>
                    <div className="holo-text-cyan" style={{ fontSize: 22, fontWeight: 800 }}>{p.currentValue}{p.unit}</div>
                  </div>
                  <div className="holo-text-dim" style={{ fontSize: 20 }}>→</div>
                  <div style={{ textAlign: "center" }}>
                    <div className="holo-text-dim" style={{ fontSize: 11 }}>预测</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color }}>{p.futureValue}{p.unit}</div>
                  </div>
                  <div style={{ flex: 1, textAlign: "right" }}>
                    <div className="holo-text-dim" style={{ fontSize: 11 }}>剩余</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color }}>{p.daysRemaining} 天</div>
                  </div>
                </div>

                <div className="holo-energy-bar" style={{ marginBottom: 10 }}>
                  <div className="holo-energy-bar__fill" style={{ width: `${(p.futureValue / p.currentValue) * 100}%`, background: color }} />
                </div>

                <div className="holo-glass" style={{ padding: 10, borderRadius: 8, marginBottom: 8 }}>
                  <div className="holo-text-dim" style={{ fontSize: 11, marginBottom: 3 }}>原因</div>
                  <div className="holo-text" style={{ fontSize: 12, lineHeight: 1.5 }}>{p.reason}</div>
                </div>
                <div className="holo-glass" style={{ padding: 10, borderRadius: 8, borderLeft: `2px solid ${color}` }}>
                  <div className="holo-text-dim" style={{ fontSize: 11, marginBottom: 3 }}>建议</div>
                  <div className="holo-text" style={{ fontSize: 12, lineHeight: 1.5 }}>{p.suggestion}</div>
                </div>
              </GlassPanel>
            );
          })}
        </div>

        {/* Right: value prediction chart + summary */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <GlassPanel className="holo-anim-fade-in holo-corners" title="车辆残值预测 · 6 年趋势">
            <ReactECharts option={valueOption} style={{ height: 320 }} />
          </GlassPanel>

          <GlassPanel className="holo-anim-fade-in holo-corners">
            <div className="holo-section-title">AI 预测摘要</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <SummaryItem color="#ffb800" title="前刹车片" text="磨损达 55%，45 天内建议更换，避免影响制动安全。" />
              <SummaryItem color="#ffb800" title="左前轮胎" text="胎纹 5.2mm，60 天后建议检查更换。" />
              <SummaryItem color="#00ff9d" title="电池容量" text="衰减率 0.8%/年优于行业，6.2 年后到达 80%。" />
              <SummaryItem color="#00ff9d" title="残值评估" text="当前估值 28.5 万，年衰减率 8.2%，2030 年约 60%。" />
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}

function SummaryItem({ color, title, text }: { color: string; title: string; text: string }) {
  return (
    <div className="holo-glass" style={{ padding: 12, borderRadius: 10, borderLeft: `3px solid ${color}` }}>
      <div style={{ fontSize: 13, fontWeight: 700, color, marginBottom: 4 }}>{title}</div>
      <div className="holo-text-dim" style={{ fontSize: 12, lineHeight: 1.5 }}>{text}</div>
    </div>
  );
}

const valueOption = {
  backgroundColor: "transparent",
  textStyle: { color: "#e2e8f0" },
  tooltip: {
    trigger: "axis",
    backgroundColor: "rgba(5,8,22,0.9)",
    borderColor: "rgba(168,85,247,0.3)",
    textStyle: { color: "#e2e8f0" },
    formatter: (params: any) => `${params[0].name}年<br/>残值：${params[0].value}%`,
  },
  xAxis: {
    type: "category",
    data: valuePredictionData.map((d) => d.year),
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
    axisLabel: { color: "#94a3b8" },
  },
  yAxis: {
    type: "value",
    min: 50,
    max: 100,
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
    splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    axisLabel: { color: "#94a3b8", formatter: "{value}%" },
  },
  series: [
    {
      type: "line",
      data: valuePredictionData.map((d) => d.value),
      smooth: true,
      symbol: "circle",
      symbolSize: 10,
      lineStyle: { color: "#a855f7", width: 3, shadowColor: "rgba(168,85,247,0.6)", shadowBlur: 12 },
      itemStyle: { color: "#a855f7", borderColor: "#fff", borderWidth: 2 },
      areaStyle: {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(168,85,247,0.35)" },
            { offset: 1, color: "rgba(168,85,247,0)" },
          ],
        },
      },
      markLine: {
        symbol: "none",
        data: [{ yAxis: 80, lineStyle: { color: "#ff3860", type: "dashed" }, label: { formatter: "80% 警戒线", color: "#ff3860" } }],
      },
    },
  ],
};
