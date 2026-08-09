/**
 * StoryMode – TASK011 Demo 场景包装
 *
 * A cinematic 5-act walkthrough of the CarSoul Guardian battery thermal risk
 * protection loop.  Designed for on-stage GOAI competition demo: 5 minutes,
 * auto-playable, fully self-contained (no backend required).
 *
 * 触摸 / 大屏适配：
 * - 左右滑动手势切换幕（pointer: coarse）
 * - kiosk 模式（触摸大屏 ≥1600px）整体放大字号与间距，适配远距离视距
 * - 控制按钮加大，Tooltip 兼容触摸点击触发
 */
import { useState, useEffect, useRef, useCallback } from "react";
import type { TouchEvent as ReactTouchEvent } from "react";
import { Button, Space, Typography, Progress, Tag, Row, Col, Tooltip, Empty, Spin, Alert, Timeline } from "antd";
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepForwardOutlined,
  StepBackwardOutlined,
  ReloadOutlined,
  CarOutlined,
  ThunderboltOutlined,
  AlertOutlined,
  RobotOutlined,
  BellOutlined,
  SafetyCertificateOutlined,
  HeartOutlined,
  FireOutlined,
} from "@ant-design/icons";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import {
  ACTS,
  ACT_DURATIONS,
  ACT_COUNT,
  ACT1_STATUS,
  ACT1_HEALTH_SCORE,
  BATTERY_CURVE,
  ACT2_HIGHLIGHTS,
  EXPERT_PANEL,
  CROSS_VALIDATION_SUMMARY,
  REASONING_CHAINS,
  AGENT_JUDGMENT,
  RISK_INDEX,
  RISK_LEVEL,
  PUSH_NOTIFICATION,
  CLOSURE_ITEMS,
  FINAL_HEALTH_SCORE,
  DIGITAL_LIFE_GROWTH,
  GUARDIAN_MEMORY,
  AGENT_ADAPTATION,
  WHY_AGENT,
  ARCHITECTURE_CHAIN,
  CLOSING_TAGLINE,
  CLOSING_BRAND,
  CLOSING_SUBTITLE,
  STORY_VEHICLE,
} from "@/services/storyData";
import { DemoBadge } from "@/components";
import { useCurrentVehicle } from "@/hooks/useCurrentVehicle";
import { digitalTwinService } from "@/services/digitalTwinService";
import type { DigitalTwinLifeEvent, DigitalTwinMemory } from "@/services/digitalTwinService";

const { Title, Text } = Typography;

const THEME_COLORS = {
  calm: { primary: "#00A8E8", secondary: "#0077B6", bg: "calm" },
  warn: { primary: "#F77F00", secondary: "#E76F51", bg: "warn" },
  danger: { primary: "#D62828", secondary: "#E76F51", bg: "danger" },
  ok: { primary: "#2A9D8F", secondary: "#10b981", bg: "ok" },
};

// ============================================================
// ACT 1 — Vehicle Digital Life Homepage
// ============================================================
function Act1Content({ kiosk }: { kiosk: boolean }) {
  const circle = kiosk ? 170 : 120;
  const ring = kiosk ? 250 : 180;
  return (
    <div className="story-act" style={{ textAlign: "center", padding: kiosk ? "32px 0" : "20px 0" }}>
      {/* Car silhouette with pulsing glow */}
      <div style={{ position: "relative", marginBottom: kiosk ? 32 : 24 }}>
        <div
          className="story-pulse"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: circle,
            height: circle,
            borderRadius: "50%",
            background: "rgba(0,168,232,0.10)",
            border: "2px solid rgba(0,168,232,0.30)",
          }}
        >
          <CarOutlined style={{ fontSize: kiosk ? 76 : 56, color: "#00A8E8" }} />
        </div>
        {/* Data stream rings */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%,-50%)",
            width: ring,
            height: ring,
            borderRadius: "50%",
            border: "1px dashed rgba(0,168,232,0.15)",
            animation: "storyPulse 4s ease-in-out infinite",
          }}
        />
      </div>

      <div style={{ color: "#cfe8f7", marginBottom: 6, fontSize: kiosk ? 20 : 15 }}>
        {STORY_VEHICLE.brand} {STORY_VEHICLE.model} ({STORY_VEHICLE.year})
      </div>
      <Text style={{ color: "#5A6B82", fontSize: kiosk ? 15 : 13 }}>
        VIN: {STORY_VEHICLE.vin} · 里程 {STORY_VEHICLE.mileage.toLocaleString()} km ·{" "}
        {STORY_VEHICLE.parkingLocation}
      </Text>

      {/* Health Score */}
      <div style={{ marginTop: kiosk ? 36 : 28, marginBottom: kiosk ? 28 : 24 }}>
        <Progress
          type="dashboard"
          percent={ACT1_HEALTH_SCORE}
          size={kiosk ? 220 : 160}
          strokeColor={{ from: "#00A8E8", to: "#2A9D8F" }}
          format={(p) => (
            <div>
              <div style={{ fontSize: kiosk ? 44 : 32, fontWeight: 700, color: "#2A9D8F" }}>{p}</div>
              <div style={{ fontSize: kiosk ? 14 : 11, color: "#5A6B82" }}>健康评分</div>
            </div>
          )}
        />
        <div style={{ marginTop: 8 }}>
          <Tag color="green" style={{ borderRadius: 12, padding: kiosk ? "4px 18px" : "2px 14px", fontSize: kiosk ? 15 : undefined }}>
            正常
          </Tag>
        </div>
      </div>

      {/* Status cards */}
      <Row gutter={[12, 12]} style={{ maxWidth: kiosk ? 880 : 720, margin: "0 auto" }}>
        {ACT1_STATUS.map((s, i) => (
          <Col xs={12} md={6} key={s.key}>
            <div
              className="story-glass story-fade-in"
              style={{ padding: kiosk ? "22px 14px" : "16px 12px", textAlign: "center", animationDelay: `${i * 0.1}s` }}
            >
              <div style={{ fontSize: kiosk ? 14 : 11, color: "#5A6B82", marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: kiosk ? 28 : 20, fontWeight: 700, color: "#e8eef5" }}>{s.value}</div>
              {s.unit && <div style={{ fontSize: kiosk ? 12 : 10, color: "#5A6B82" }}>{s.unit}</div>}
            </div>
          </Col>
        ))}
      </Row>

      {/* Voiceover */}
      <div
        className="story-fade-in"
        style={{
          marginTop: kiosk ? 36 : 28,
          padding: kiosk ? "16px 28px" : "12px 24px",
          maxWidth: kiosk ? 760 : 620,
          margin: `${kiosk ? 36 : 28}px auto 0`,
          color: "#8ea5c4",
          fontStyle: "italic",
          fontSize: kiosk ? 17 : 13,
          lineHeight: 1.8,
        }}
      >
        "这是一辆新能源汽车的数字生命。此刻它停在地下停车场，车主已经回家。
        但它的 AI 守护者——CarSoul，从未休息。"
      </div>
    </div>
  );
}

// ============================================================
// ACT 2 — Anomaly Detection
// ============================================================
function Act2Content({ kiosk }: { kiosk: boolean }) {
  return (
    <div className="story-act" style={{ padding: kiosk ? "20px 0" : "12px 0" }}>
      <div style={{ textAlign: "center", marginBottom: kiosk ? 28 : 20 }}>
        <Tag
          color="orange"
          className="story-blink"
          style={{ fontSize: kiosk ? 17 : 13, padding: kiosk ? "6px 20px" : "4px 16px", borderRadius: 12 }}
        >
          <AlertOutlined /> CarSoul 已感知到异常信号
        </Tag>
      </div>

      {/* Temperature highlight cards */}
      <Row gutter={[12, 12]} style={{ maxWidth: kiosk ? 720 : 600, margin: `0 auto ${kiosk ? 28 : 20}px` }}>
        {ACT2_HIGHLIGHTS.map((h, i) => (
          <Col xs={24} sm={8} key={i}>
            <div
              className="story-glass story-fade-in"
              style={{
                padding: kiosk ? "22px 14px" : "16px 12px",
                textAlign: "center",
                animationDelay: `${i * 0.15}s`,
                borderColor: h.color + "40",
              }}
            >
              <div style={{ fontSize: kiosk ? 40 : 28, fontWeight: 700, color: h.color, fontFamily: "monospace" }}>
                {h.temp}℃
              </div>
              <div style={{ fontSize: kiosk ? 14 : 11, color: "#5A6B82", marginTop: 4 }}>{h.time}</div>
              <div style={{ fontSize: kiosk ? 14 : 11, color: h.color, marginTop: 2 }}>{h.status}</div>
            </div>
          </Col>
        ))}
      </Row>

      {/* Dual-axis chart */}
      <div
        className="story-glass"
        style={{ padding: kiosk ? "20px 16px 10px" : "16px 12px 8px", maxWidth: kiosk ? 880 : 720, margin: "0 auto" }}
      >
        <div style={{ textAlign: "center", marginBottom: 8 }}>
          <Text style={{ color: "#cfe8f7", fontSize: kiosk ? 17 : 14 }}>
            电池温度 vs 冷却效率 · 剪刀差
          </Text>
        </div>
        <ResponsiveContainer width="100%" height={kiosk ? 340 : 260}>
          <LineChart data={BATTERY_CURVE} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="time" stroke="#5A6B82" tick={{ fontSize: kiosk ? 13 : 11 }} />
            <YAxis
              yAxisId="temp"
              orientation="left"
              stroke="#F77F00"
              tick={{ fontSize: kiosk ? 13 : 11 }}
              domain={[25, 50]}
              unit="℃"
            />
            <YAxis
              yAxisId="cooling"
              orientation="right"
              stroke="#00A8E8"
              tick={{ fontSize: kiosk ? 13 : 11 }}
              domain={[50, 100]}
              unit="%"
            />
            <RTooltip
              contentStyle={{
                background: "rgba(15,27,45,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#e8eef5",
                fontSize: kiosk ? 14 : 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: kiosk ? 13 : 11, color: "#8ea5c4" }} />
            <ReferenceLine
              y={40}
              yAxisId="temp"
              stroke="#E76F51"
              strokeDasharray="5 5"
              label={{ value: "危险阈值 40℃", fill: "#E76F51", fontSize: kiosk ? 12 : 10 }}
            />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="temp"
              name="电池温度"
              stroke="#F77F00"
              strokeWidth={kiosk ? 3.5 : 2.5}
              dot={{ fill: "#F77F00", r: kiosk ? 5 : 3 }}
              activeDot={{ r: kiosk ? 7 : 5 }}
            />
            <Line
              yAxisId="cooling"
              type="monotone"
              dataKey="cooling"
              name="冷却效率"
              stroke="#00A8E8"
              strokeWidth={kiosk ? 3.5 : 2.5}
              dot={{ fill: "#00A8E8", r: kiosk ? 5 : 3 }}
              activeDot={{ r: kiosk ? 7 : 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ============================================================
// ACT 3 — Agent Reasoning
// ============================================================
function Act3Content({ kiosk }: { kiosk: boolean }) {
  const [visibleExperts, setVisibleExperts] = useState(0);
  const [showCrossVal, setShowCrossVal] = useState(false);
  const [visibleChains, setVisibleChains] = useState(0);
  const [showJudgment, setShowJudgment] = useState(false);

  useEffect(() => {
    setVisibleExperts(0);
    setShowCrossVal(false);
    setVisibleChains(0);
    setShowJudgment(false);
    const timers: number[] = [];
    // Phase 1: Experts light up sequentially
    timers.push(window.setTimeout(() => setVisibleExperts(1), 300));
    timers.push(window.setTimeout(() => setVisibleExperts(2), 900));
    timers.push(window.setTimeout(() => setVisibleExperts(3), 1500));
    timers.push(window.setTimeout(() => setVisibleExperts(4), 2100));
    timers.push(window.setTimeout(() => setVisibleExperts(5), 2700));
    // Phase 2: Cross-validation summary
    timers.push(window.setTimeout(() => setShowCrossVal(true), 3300));
    // Phase 3: Reasoning chains
    timers.push(window.setTimeout(() => setVisibleChains(1), 4000));
    timers.push(window.setTimeout(() => setVisibleChains(2), 5200));
    timers.push(window.setTimeout(() => setVisibleChains(3), 6400));
    // Phase 4: Agent judgment
    timers.push(window.setTimeout(() => setShowJudgment(true), 7200));
    return () => timers.forEach(clearTimeout);
  }, []);

  const severityColor: Record<string, string> = {
    info: "#00A8E8",
    warn: "#F77F00",
    danger: "#E76F51",
  };

  return (
    <div className="story-act" style={{ padding: kiosk ? "20px 0" : "12px 0" }}>
      <div style={{ textAlign: "center", marginBottom: kiosk ? 24 : 16 }}>
        <Space>
          <RobotOutlined className="story-pulse" style={{ fontSize: kiosk ? 32 : 24, color: "#00A8E8" }} />
          <Text style={{ color: "#cfe8f7", fontSize: kiosk ? 21 : 16, fontWeight: 600 }}>
            多智能体专家会诊中…
          </Text>
        </Space>
      </div>

      {/* Phase 1: Expert Panel — 5 specialists light up sequentially */}
      <div style={{ maxWidth: kiosk ? 820 : 680, margin: "0 auto" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: kiosk ? 12 : 8, justifyContent: "center" }}>
          {EXPERT_PANEL.map((expert, i) => {
            if (i >= visibleExperts) return null;
            return (
              <div
                key={expert.key}
                className="story-fade-in"
                style={{
                  flex: kiosk ? "1 1 220px" : "1 1 180px",
                  maxWidth: kiosk ? 240 : 200,
                  padding: kiosk ? "14px 16px" : "10px 12px",
                  background: "rgba(255,255,255,0.05)",
                  border: `1px solid ${expert.color}40`,
                  borderLeft: `3px solid ${expert.color}`,
                  borderRadius: "0 10px 10px 0",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                  <span style={{ fontSize: kiosk ? 22 : 18 }}>{expert.icon}</span>
                  <div>
                    <div style={{ color: expert.color, fontSize: kiosk ? 15 : 12, fontWeight: 700 }}>
                      {expert.name}
                    </div>
                    <div style={{ color: "#5A6B82", fontSize: kiosk ? 11 : 9 }}>
                      {expert.specialty}
                    </div>
                  </div>
                </div>
                <div style={{ color: "#cfe8f7", fontSize: kiosk ? 14 : 11, lineHeight: 1.6, marginBottom: 4 }}>
                  {expert.finding}
                </div>
                <div style={{ color: expert.color, fontSize: kiosk ? 12 : 10, fontStyle: "italic", opacity: 0.8 }}>
                  {expert.crossCheck}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Phase 2: Cross-validation summary */}
      {showCrossVal && (
        <div
          className="story-fade-in"
          style={{
            maxWidth: kiosk ? 780 : 640,
            margin: `${kiosk ? 16 : 12}px auto 0`,
            padding: kiosk ? "14px 20px" : "10px 16px",
            background: "rgba(0,168,232,0.08)",
            border: "1px solid rgba(0,168,232,0.25)",
            borderRadius: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <span style={{ fontSize: kiosk ? 16 : 14 }}>🔗</span>
            <Text style={{ color: "#00A8E8", fontSize: kiosk ? 14 : 11, fontWeight: 700 }}>
              交叉验证完成
            </Text>
          </div>
          <div style={{ color: "#8ea5c4", fontSize: kiosk ? 14 : 11, lineHeight: 1.6 }}>
            {CROSS_VALIDATION_SUMMARY}
          </div>
        </div>
      )}

      {/* Phase 3: Reasoning chains */}
      {visibleChains > 0 && (
        <div style={{ maxWidth: kiosk ? 780 : 640, margin: `${kiosk ? 16 : 12}px auto 0` }}>
          <div style={{ textAlign: "center", marginBottom: kiosk ? 12 : 8 }}>
            <Text style={{ color: "#5A6B82", fontSize: kiosk ? 14 : 11, textTransform: "uppercase", letterSpacing: "0.1em" }}>
              会诊推理链
            </Text>
          </div>
          {REASONING_CHAINS.map((chain, i) => {
            if (i >= visibleChains) return null;
            const color = severityColor[chain.severity];
            return (
              <div
                key={chain.id}
                className="story-slide-right"
                style={{
                  marginBottom: kiosk ? 14 : 10,
                  animationDelay: `${i * 0.1}s`,
                  padding: kiosk ? "16px 20px" : "12px 16px",
                  background: "rgba(255,255,255,0.05)",
                  borderLeft: `3px solid ${color}`,
                  borderRadius: "0 12px 12px 0",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <Text style={{ color, fontSize: kiosk ? 14 : 12, fontWeight: 600 }}>{chain.label}</Text>
                  {chain.metric && (
                    <Tag
                      style={{
                        borderColor: color + "40",
                        color,
                        background: color + "12",
                        fontSize: kiosk ? 12 : 10,
                        borderRadius: 8,
                        padding: kiosk ? "2px 10px" : "1px 8px",
                      }}
                    >
                      {chain.metric}
                    </Tag>
                  )}
                </div>
                <div style={{ color: "#e8eef5", fontSize: kiosk ? 16 : 13, fontWeight: 600, marginBottom: 4 }}>
                  {chain.title}
                </div>
                <div style={{ color: "#8ea5c4", fontSize: kiosk ? 14 : 12, lineHeight: 1.6 }}>
                  {chain.content}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Phase 4: Agent judgment */}
      {showJudgment && (
        <div
          className="story-fade-in"
          style={{
            maxWidth: kiosk ? 780 : 640,
            margin: `${kiosk ? 16 : 12}px auto 0`,
            padding: kiosk ? "18px 22px" : "14px 18px",
            background: "rgba(231,111,81,0.10)",
            border: "1px solid rgba(231,111,81,0.30)",
            borderRadius: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <ThunderboltOutlined style={{ color: "#E76F51", fontSize: kiosk ? 22 : 18 }} />
            <Text style={{ color: "#E76F51", fontSize: kiosk ? 17 : 13, fontWeight: 700 }}>
              CarSoul Agent 判断
            </Text>
          </div>
          <div style={{ color: "#e8eef5", fontSize: kiosk ? 16 : 13, lineHeight: 1.7 }}>
            "{AGENT_JUDGMENT}"
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// ACT 4 — Active Protection
// ============================================================
function Act4Content({ kiosk }: { kiosk: boolean }) {
  return (
    <div className="story-act" style={{ padding: kiosk ? "20px 0" : "12px 0" }}>
      <Row gutter={[20, 20]} align="middle" style={{ maxWidth: kiosk ? 920 : 760, margin: "0 auto" }}>
        {/* Left: Risk gauge + shielded car */}
        <Col xs={24} md={10} style={{ textAlign: "center" }}>
          <div
            className="story-shield"
            style={{
              display: "inline-flex",
              flexDirection: "column",
              alignItems: "center",
              padding: kiosk ? "26px 28px" : "20px 24px",
              borderRadius: 16,
              background: "rgba(42,157,143,0.06)",
              border: "1px solid rgba(42,157,143,0.20)",
            }}
          >
            <SafetyCertificateOutlined className="story-pulse" style={{ fontSize: kiosk ? 64 : 48, color: "#2A9D8F" }} />
            <div style={{ marginTop: 8 }}>
              <Progress
                type="dashboard"
                percent={Math.round(RISK_INDEX * 100)}
                size={kiosk ? 160 : 120}
                strokeColor={{ from: "#F77F00", to: "#D62828" }}
                format={(p) => (
                  <div>
                    <div style={{ fontSize: kiosk ? 30 : 22, fontWeight: 700, color: "#F77F00" }}>
                      {(p! / 100).toFixed(2)}
                    </div>
                    <div style={{ fontSize: kiosk ? 13 : 10, color: "#5A6B82" }}>风险指数</div>
                  </div>
                )}
              />
            </div>
            <Tag
              color="orange"
              style={{ marginTop: 8, fontSize: kiosk ? 16 : 13, padding: kiosk ? "4px 18px" : "2px 14px", borderRadius: 12 }}
            >
              {RISK_LEVEL} · 触发主动守护
            </Tag>
          </div>
          <div style={{ marginTop: 10, color: "#5A6B82", fontSize: kiosk ? 15 : 12 }}>
            车辆数字孪生亮起守护光盾
          </div>
        </Col>

        {/* Right: Phone notification mockup */}
        <Col xs={24} md={14} style={{ display: "flex", justifyContent: "center" }}>
          <div className="story-phone" style={{ width: kiosk ? 360 : 300 }}>
            <div className="story-phone-screen" style={{ padding: kiosk ? 20 : 16 }}>
              {/* Phone status bar */}
              <div style={{ display: "flex", justifyContent: "space-between", color: "#5A6B82", fontSize: kiosk ? 13 : 11, marginBottom: 12 }}>
                <span>{PUSH_NOTIFICATION.time}</span>
                <span>📶 🔋</span>
              </div>

              {/* Push notification */}
              <div
                className="story-fade-in"
                style={{
                  background: "rgba(255,255,255,0.08)",
                  borderRadius: 14,
                  padding: kiosk ? "18px 20px" : "14px 16px",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div
                    style={{
                      width: kiosk ? 38 : 32,
                      height: kiosk ? 38 : 32,
                      borderRadius: 8,
                      background: "linear-gradient(135deg,#3b82f6,#10b981)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <HeartOutlined style={{ color: "#fff", fontSize: kiosk ? 19 : 16 }} />
                  </div>
                  <div>
                    <div style={{ color: "#e8eef5", fontSize: kiosk ? 15 : 13, fontWeight: 600 }}>
                      {PUSH_NOTIFICATION.appName}
                    </div>
                    <div style={{ color: "#5A6B82", fontSize: kiosk ? 11 : 10 }}>刚刚</div>
                  </div>
                  <BellOutlined style={{ color: "#5A6B82", fontSize: kiosk ? 16 : 14, marginLeft: "auto" }} />
                </div>

                <div style={{ color: "#F77F00", fontSize: kiosk ? 17 : 14, fontWeight: 600, marginBottom: 6 }}>
                  {PUSH_NOTIFICATION.title}
                </div>
                <div style={{ color: "#cfe8f7", fontSize: kiosk ? 14 : 12, lineHeight: 1.7, marginBottom: 10 }}>
                  {PUSH_NOTIFICATION.body}
                </div>

                <div
                  style={{
                    background: "rgba(247,127,0,0.08)",
                    borderRadius: 8,
                    padding: kiosk ? "10px 12px" : "8px 10px",
                    marginBottom: 8,
                    fontSize: kiosk ? 14 : 12,
                    color: "#cfe8f7",
                    lineHeight: 1.8,
                  }}
                >
                  <div>风险等级：<span style={{ color: "#F77F00", fontWeight: 600 }}>{PUSH_NOTIFICATION.riskLevel}</span></div>
                  <div>当前温度：<span style={{ color: "#F77F00" }}>{PUSH_NOTIFICATION.currentTemp}</span></div>
                  <div>建议措施：{PUSH_NOTIFICATION.suggestion}</div>
                </div>

                <div
                  style={{
                    color: "#00A8E8",
                    fontSize: kiosk ? 14 : 12,
                    textAlign: "center",
                    padding: "4px 0",
                    borderTop: "1px solid rgba(255,255,255,0.06)",
                  }}
                >
                  完整健康报告已生成，点击查看 →
                </div>
              </div>

              {/* Lock screen hint */}
              <div style={{ textAlign: "center", marginTop: 16, color: "#3a4a6a", fontSize: kiosk ? 13 : 11 }}>
                深夜推送 · 车主熟睡中 · 守护已启动
              </div>
            </div>
          </div>
        </Col>
      </Row>

      {/* Voiceover */}
      <div
        className="story-fade-in"
        style={{
          marginTop: kiosk ? 28 : 20,
          padding: kiosk ? "14px 28px" : "10px 24px",
          maxWidth: kiosk ? 760 : 620,
          margin: `${kiosk ? 28 : 20}px auto 0`,
          color: "#8ea5c4",
          fontStyle: "italic",
          fontSize: kiosk ? 17 : 13,
          lineHeight: 1.8,
          textAlign: "center",
        }}
      >
        "CarSoul 没有等到故障发生。它在风险还是'趋势'的时候就找到了车主——
        在深夜，在车主熟睡的时候，守护已经开始了。"
      </div>
    </div>
  );
}

// ============================================================
// ACT 5 — Digital Life Growth
// ============================================================
function Act5Content({ kiosk }: { kiosk: boolean }) {
  const [visibleGrowth, setVisibleGrowth] = useState(0);
  const [visibleAdaptation, setVisibleAdaptation] = useState(0);

  useEffect(() => {
    setVisibleGrowth(0);
    setVisibleAdaptation(0);
    const timers: number[] = [];
    timers.push(window.setTimeout(() => setVisibleGrowth(1), 400));
    timers.push(window.setTimeout(() => setVisibleGrowth(2), 1100));
    timers.push(window.setTimeout(() => setVisibleGrowth(3), 1800));
    timers.push(window.setTimeout(() => setVisibleGrowth(4), 2500));
    timers.push(window.setTimeout(() => setVisibleAdaptation(1), 3200));
    timers.push(window.setTimeout(() => setVisibleAdaptation(2), 3700));
    timers.push(window.setTimeout(() => setVisibleAdaptation(3), 4200));
    timers.push(window.setTimeout(() => setVisibleAdaptation(4), 4700));
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="story-act" style={{ padding: kiosk ? "16px 0" : "10px 0" }}>
      {/* Part A — Service closure (compact) */}
      <Row gutter={[10, 10]} style={{ maxWidth: kiosk ? 860 : 700, margin: `0 auto ${kiosk ? 18 : 14}px` }}>
        {CLOSURE_ITEMS.map((item, i) => (
          <Col xs={24} sm={8} key={item.key}>
            <div
              className="story-glass story-fade-in"
              style={{
                padding: kiosk ? "16px 12px" : "13px 10px",
                textAlign: "center",
                animationDelay: `${i * 0.1}s`,
                borderColor: "rgba(42,157,143,0.20)",
              }}
            >
              <div style={{ fontSize: kiosk ? 28 : 22, marginBottom: 4 }}>{item.icon}</div>
              <div style={{ fontSize: kiosk ? 15 : 12, fontWeight: 700, color: "#e8eef5", marginBottom: 4 }}>
                {item.title}
              </div>
              <Tag color="green" style={{ fontSize: kiosk ? 12 : 10, borderRadius: 8 }}>
                {item.status}
              </Tag>
            </div>
          </Col>
        ))}
      </Row>

      {/* Health score change · 守护前 → 守护后 → 数字生命成长 */}
      <div style={{ textAlign: "center", marginBottom: kiosk ? 22 : 16 }}>
        <Space size="large" align="center" wrap>
          <div>
            <div style={{ fontSize: kiosk ? 13 : 11, color: "#5A6B82" }}>守护前</div>
            <div style={{ fontSize: kiosk ? 32 : 24, fontWeight: 700, color: "#2A9D8F" }}>{ACT1_HEALTH_SCORE}</div>
          </div>
          <div style={{ color: "#5A6B82", fontSize: kiosk ? 22 : 18 }}>→</div>
          <div>
            <div style={{ fontSize: kiosk ? 13 : 11, color: "#5A6B82" }}>守护后</div>
            <div style={{ fontSize: kiosk ? 32 : 24, fontWeight: 700, color: "#F77F00" }}>{FINAL_HEALTH_SCORE}</div>
          </div>
          <div style={{ color: "#5A6B82", fontSize: kiosk ? 22 : 18 }}>→</div>
          <div>
            <div style={{ fontSize: kiosk ? 13 : 11, color: "#5A6B82" }}>数字生命</div>
            <div style={{ fontSize: kiosk ? 32 : 24, fontWeight: 700, color: "#00A8E8" }}>成长 +1</div>
          </div>
        </Space>
      </div>

      {/* Part B — Digital life growth */}
      <div style={{ textAlign: "center", marginBottom: kiosk ? 14 : 10 }}>
        <Text style={{ color: "#00A8E8", fontSize: kiosk ? 18 : 14, fontWeight: 700 }}>
          🌱 这辆车因为这次守护，变得更聪明了
        </Text>
      </div>
      <Row gutter={[10, 10]} style={{ maxWidth: kiosk ? 880 : 720, margin: `0 auto ${kiosk ? 20 : 16}px` }}>
        {DIGITAL_LIFE_GROWTH.map((g, i) => {
          if (i >= visibleGrowth) return null;
          return (
            <Col xs={12} md={6} key={g.key}>
              <div
                className="story-glass story-slide-right"
                style={{
                  padding: kiosk ? "16px 10px" : "13px 9px",
                  textAlign: "center",
                  animationDelay: `${i * 0.1}s`,
                  borderColor: "rgba(0,168,232,0.20)",
                  height: "100%",
                }}
              >
                <div style={{ fontSize: kiosk ? 28 : 22, marginBottom: 6 }}>{g.icon}</div>
                <div style={{ fontSize: kiosk ? 14 : 12, fontWeight: 700, color: "#e8eef5", marginBottom: 4 }}>
                  {g.title}
                </div>
                <div style={{ fontSize: kiosk ? 12 : 10, color: "#8ea5c4", lineHeight: 1.55, marginBottom: 6 }}>
                  {g.description}
                </div>
                <Tag color="blue" style={{ fontSize: kiosk ? 11 : 10, borderRadius: 8 }}>
                  {g.delta}
                </Tag>
              </div>
            </Col>
          );
        })}
      </Row>

      {/* Guardian memory stats */}
      {visibleGrowth >= 4 && (
        <div
          className="story-fade-in"
          style={{
            display: "flex",
            justifyContent: "center",
            gap: kiosk ? 48 : 28,
            margin: `0 auto ${kiosk ? 22 : 16}px`,
            flexWrap: "wrap",
          }}
        >
          {[
            { num: GUARDIAN_MEMORY.totalEvents, label: "累计守护事件" },
            { num: GUARDIAN_MEMORY.lifecycleRecords, label: "生命周期记录" },
            { num: GUARDIAN_MEMORY.growthDays, label: "守护天数" },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: kiosk ? 30 : 22, fontWeight: 700, color: "#00A8E8", fontFamily: "monospace" }}>
                {s.num}
              </div>
              <div style={{ fontSize: kiosk ? 13 : 11, color: "#5A6B82" }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Part B+ — Agent Dynamic Adaptation · 自纠错 */}
      {visibleGrowth >= 4 && (
        <div
          className="story-fade-in"
          style={{
            maxWidth: kiosk ? 880 : 720,
            margin: `0 auto ${kiosk ? 22 : 16}px`,
            padding: kiosk ? "18px 22px" : "14px 16px",
            background: "linear-gradient(135deg, rgba(0,168,232,0.06), rgba(42,157,143,0.06))",
            border: "1px solid rgba(0,168,232,0.20)",
            borderRadius: 14,
          }}
        >
          <div style={{ textAlign: "center", marginBottom: kiosk ? 14 : 10 }}>
            <Space>
              <RobotOutlined style={{ color: "#00A8E8", fontSize: kiosk ? 18 : 15 }} />
              <Text style={{ color: "#00A8E8", fontSize: kiosk ? 16 : 13, fontWeight: 700 }}>
                {AGENT_ADAPTATION.title}
              </Text>
            </Space>
            <div style={{ color: "#5A6B82", fontSize: kiosk ? 12 : 10, marginTop: 2 }}>
              {AGENT_ADAPTATION.subtitle}
            </div>
          </div>

          <div style={{ display: "flex", gap: kiosk ? 6 : 3, flexWrap: "wrap", justifyContent: "center", alignItems: "stretch" }}>
            {AGENT_ADAPTATION.steps.map((step, i) => {
              if (i >= visibleAdaptation) return null;
              const isLast = i === AGENT_ADAPTATION.steps.length - 1;
              return (
                <div key={step.key} style={{ display: "flex", alignItems: "center" }}>
                  <div
                    className="story-slide-right"
                    style={{
                      flex: "1 1 0",
                      minWidth: kiosk ? 130 : 95,
                      maxWidth: kiosk ? 170 : 130,
                      padding: kiosk ? "12px 10px" : "10px 8px",
                      background: "rgba(255,255,255,0.04)",
                      borderLeft: `3px solid ${step.color}`,
                      borderRadius: "0 10px 10px 0",
                      animationDelay: `${i * 0.1}s`,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 4 }}>
                      <span style={{ fontSize: kiosk ? 18 : 15 }}>{step.icon}</span>
                      <span style={{ color: step.color, fontSize: kiosk ? 10 : 9, fontWeight: 700, fontFamily: "monospace" }}>
                        {step.step}
                      </span>
                    </div>
                    <div style={{ color: "#e8eef5", fontSize: kiosk ? 13 : 11, fontWeight: 700, marginBottom: 3 }}>
                      {step.title}
                    </div>
                    <div style={{ color: "#8ea5c4", fontSize: kiosk ? 11 : 9, lineHeight: 1.5 }}>
                      {step.content}
                    </div>
                  </div>
                  {!isLast && visibleAdaptation > i + 1 && (
                    <span style={{ color: "#00A8E8", fontSize: kiosk ? 14 : 10, margin: "0 1px" }}>→</span>
                  )}
                </div>
              );
            })}
          </div>

          {visibleAdaptation >= 4 && (
            <div
              className="story-fade-in"
              style={{
                marginTop: kiosk ? 14 : 10,
                padding: kiosk ? "10px 16px" : "8px 12px",
                background: "rgba(42,157,143,0.08)",
                borderRadius: 10,
                textAlign: "center",
                color: "#2A9D8F",
                fontSize: kiosk ? 14 : 12,
                fontWeight: 600,
                lineHeight: 1.7,
              }}
            >
              {AGENT_ADAPTATION.outcome}
            </div>
          )}
        </div>
      )}

      {/* Part C — Why Agent? */}
      {visibleGrowth >= 4 && (
        <div
          className="story-fade-in"
          style={{
            maxWidth: kiosk ? 820 : 660,
            margin: `0 auto ${kiosk ? 22 : 16}px`,
            padding: kiosk ? "20px 24px" : "16px 18px",
            background: "rgba(0,168,232,0.08)",
            border: "1px solid rgba(0,168,232,0.25)",
            borderRadius: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <RobotOutlined style={{ color: "#00A8E8", fontSize: kiosk ? 22 : 18 }} />
            <Text style={{ color: "#00A8E8", fontSize: kiosk ? 18 : 15, fontWeight: 700 }}>
              {WHY_AGENT.question}
            </Text>
          </div>
          <div style={{ color: "#cfe8f7", fontSize: kiosk ? 15 : 12, lineHeight: 1.8, marginBottom: 12 }}>
            {WHY_AGENT.answer}
          </div>
          <div style={{ display: "flex", gap: kiosk ? 12 : 8, flexWrap: "wrap" }}>
            {WHY_AGENT.points.map((p) => (
              <div
                key={p.label}
                style={{
                  flex: "1 1 0",
                  minWidth: kiosk ? 150 : 100,
                  padding: kiosk ? "10px 12px" : "8px 10px",
                  background: "rgba(255,255,255,0.05)",
                  borderRadius: 10,
                  borderLeft: "3px solid #00A8E8",
                }}
              >
                <div style={{ color: "#00A8E8", fontSize: kiosk ? 14 : 12, fontWeight: 700, marginBottom: 2 }}>
                  {p.label}
                </div>
                <div style={{ color: "#8ea5c4", fontSize: kiosk ? 12 : 10 }}>{p.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Part D — Architecture chain (platform reveal) */}
      {visibleGrowth >= 4 && (
        <div
          className="story-fade-in"
          style={{
            maxWidth: kiosk ? 900 : 720,
            margin: `0 auto ${kiosk ? 22 : 16}px`,
            padding: kiosk ? "14px 20px" : "10px 14px",
            textAlign: "center",
          }}
        >
          <div style={{ color: "#5A6B82", fontSize: kiosk ? 13 : 11, marginBottom: kiosk ? 12 : 8, letterSpacing: "0.1em" }}>
            车辆数字生命系统 · 平台架构
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: kiosk ? 6 : 3 }}>
            {ARCHITECTURE_CHAIN.map((node, i) => {
              const isLast = i === ARCHITECTURE_CHAIN.length - 1;
              return (
                <div key={node} style={{ display: "flex", alignItems: "center" }}>
                  <span
                    style={{
                      fontSize: kiosk ? 14 : 11,
                      fontWeight: 600,
                      color: isLast ? "#2A9D8F" : "#cfe8f7",
                      padding: kiosk ? "6px 12px" : "4px 9px",
                      background: isLast ? "rgba(42,157,143,0.12)" : "rgba(255,255,255,0.05)",
                      border: `1px solid ${isLast ? "rgba(42,157,143,0.3)" : "rgba(255,255,255,0.1)"}`,
                      borderRadius: 8,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {node}
                  </span>
                  {!isLast && (
                    <span style={{ color: "#00A8E8", fontSize: kiosk ? 14 : 11, margin: "0 2px" }}>→</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Part E — Closing */}
      <div
        className="story-fade-in"
        style={{
          textAlign: "center",
          padding: kiosk ? "22px 28px" : "14px 24px",
          maxWidth: kiosk ? 680 : 560,
          margin: "0 auto",
        }}
      >
        <FireOutlined style={{ fontSize: kiosk ? 32 : 26, color: "#F77F00", marginBottom: 10 }} />
        <div
          style={{
            fontSize: kiosk ? 22 : 17,
            fontWeight: 700,
            color: "#e8eef5",
            lineHeight: 1.8,
            marginBottom: 8,
          }}
        >
          {CLOSING_TAGLINE}
        </div>
        <div
          className="cs-gradient-text"
          style={{ fontSize: kiosk ? 30 : 22, fontWeight: 700, letterSpacing: "0.04em" }}
        >
          {CLOSING_BRAND}
        </div>
        <div style={{ fontSize: kiosk ? 14 : 12, color: "#5A6B82", letterSpacing: "0.15em", marginTop: 4 }}>
          {CLOSING_SUBTITLE}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Real Life Story — 用本车真实 life-events + memories 拼叙事
// ============================================================
const EVENT_LABEL: Record<string, string> = {
  PURCHASE: "购车",
  TRAVEL: "出行",
  UPGRADE: "升级",
  MAINTENANCE: "保养",
  WARNING: "预警",
  RECOVERY: "恢复",
  ACCIDENT: "事故",
};

const EVENT_COLOR: Record<string, string> = {
  PURCHASE: "green",
  TRAVEL: "blue",
  UPGRADE: "geekblue",
  MAINTENANCE: "cyan",
  WARNING: "volcano",
  RECOVERY: "green",
  ACCIDENT: "red",
};

const MEM_TYPE_LABEL: Record<string, string> = {
  warning: "预警",
  recovery: "恢复",
  emotion: "情绪",
  milestone: "里程碑",
  driving: "驾驶",
};

const MEM_TYPE_COLOR: Record<string, string> = {
  warning: "red",
  recovery: "green",
  emotion: "magenta",
  milestone: "gold",
  driving: "default",
};

/** 把真实 life-events + memories 合并成一条按时间升序的真实叙事。 */
function RealLifeStorySection({ kiosk }: { kiosk: boolean }) {
  const { vehicle, loading: vehicleLoading } = useCurrentVehicle();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<DigitalTwinLifeEvent[]>([]);
  const [memories, setMemories] = useState<DigitalTwinMemory[]>([]);

  useEffect(() => {
    if (!vehicle) return;
    let alive = true;
    setLoading(true);
    setError(null);
    Promise.all([
      digitalTwinService.getLifeEvents(vehicle.id, 100),
      digitalTwinService.getMemories(vehicle.id, 100),
    ])
      .then(([ev, mem]) => {
        if (!alive) return;
        setEvents(ev.items || []);
        setMemories(mem.items || []);
      })
      .catch((e: unknown) => {
        if (alive) {
          const detail = (e as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail;
          setError(typeof detail === "string" ? detail : "真实数字生命数据取数失败");
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [vehicle]);

  const titleSize = kiosk ? 18 : 14;

  const merged = [
    ...events.map((e) => ({
      kind: "event" as const,
      time: e.event_time,
      node: (
        <div>
          <Space wrap>
            <Tag color={EVENT_COLOR[e.event_type] || "default"}>
              {EVENT_LABEL[e.event_type] || e.event_type}
            </Tag>
            <Text strong style={{ color: "#e8eef5", fontSize: kiosk ? 16 : 13 }}>
              {e.title}
            </Text>
            {e.mileage != null && (
              <Text type="secondary" style={{ fontSize: kiosk ? 12 : 10 }}>
                {e.mileage.toLocaleString()} km
              </Text>
            )}
          </Space>
          {e.description && (
            <div style={{ color: "#cfe8f7", fontSize: kiosk ? 14 : 12, lineHeight: 1.6, marginTop: 4 }}>
              {e.description}
            </div>
          )}
          <div style={{ color: "#5A6B82", fontSize: kiosk ? 12 : 10, marginTop: 2 }}>
            {[e.location, e.event_time].filter(Boolean).join(" · ")}
          </div>
        </div>
      ),
    })),
    ...memories.map((m) => ({
      kind: "memory" as const,
      time: m.created_time,
      node: (
        <div>
          <Space wrap>
            <Tag color={MEM_TYPE_COLOR[m.memory_type] || "default"}>
              {MEM_TYPE_LABEL[m.memory_type] || m.memory_type}
            </Tag>
            {m.importance != null && (
              <Text type="secondary" style={{ fontSize: kiosk ? 12 : 10 }}>
                重要度 {m.importance}
              </Text>
            )}
          </Space>
          <div style={{ color: "#e8eef5", fontSize: kiosk ? 14 : 12, lineHeight: 1.6, marginTop: 4 }}>
            {m.content}
          </div>
          <div style={{ color: "#5A6B82", fontSize: kiosk ? 12 : 10, marginTop: 2 }}>
            {[m.source, m.created_time].filter(Boolean).join(" · ")}
          </div>
        </div>
      ),
    })),
  ]
    .filter((x) => !!x.time)
    .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

  return (
    <div style={{ marginTop: kiosk ? 28 : 20 }}>
      <Space style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0, color: "#e8eef5" }}>
          本车真实数字生命叙事
        </Title>
        <Tag color="blue">life-events + memories 真实落盘</Tag>
      </Space>

      {vehicleLoading || (vehicle && loading) ? (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      ) : !vehicle ? (
        <Alert type="info" showIcon message="暂无可展示的车辆" description="请先选择一辆本车后再查看真实数字生命叙事。" />
      ) : error ? (
        <Alert type="warning" showIcon message="真实数字生命数据暂不可用" description={error} />
      ) : merged.length === 0 ? (
        <Alert
          type="info"
          showIcon
          message="暂无数据"
          description="本车尚未生成任何 life-events 或 memories（可经 generate-lifecycle 真实生成，或手动写入）。按诚实数据纪律不展示占位内容。"
        />
      ) : (
        <Timeline
          mode={kiosk ? "left" : "left"}
          items={merged.map((x) => ({
            color: x.kind === "event" ? "#00A8E8" : "#2A9D8F",
            children: x.node,
          }))}
        />
      )}

      {merged.length > 0 && (
        <Text type="secondary" style={{ fontSize: kiosk ? 12 : 11 }}>
          共 {events.length} 条生命周期事件 · {memories.length} 条记忆 · 按时间升序排列（数据来源：carsoul_dev.db 真实落盘）
        </Text>
      )}
    </div>
  );
}

// ============================================================
// Main StoryMode Component
// ============================================================
export default function StoryMode() {
  const [actIndex, setActIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0); // 0-100 within current act
  const [kiosk, setKiosk] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 触摸大屏检测（pointer: coarse 且宽屏）
  useEffect(() => {
    const mq = window.matchMedia("(pointer: coarse) and (min-width: 1600px)");
    const update = () => setKiosk(mq.matches);
    update();
    if (mq.addEventListener) {
      mq.addEventListener("change", update);
      return () => mq.removeEventListener("change", update);
    }
    mq.addListener(update);
    return () => mq.removeListener(update);
  }, []);

  const goToAct = useCallback((idx: number) => {
    setActIndex(Math.max(0, Math.min(ACT_COUNT - 1, idx)));
    setProgress(0);
  }, []);

  const nextAct = useCallback(() => {
    setActIndex((prev) => {
      if (prev >= ACT_COUNT - 1) {
        setPlaying(false);
        return prev;
      }
      setProgress(0);
      return prev + 1;
    });
  }, []);

  const prevAct = useCallback(() => {
    setActIndex((prev) => {
      if (prev <= 0) return prev;
      setProgress(0);
      return prev - 1;
    });
    setProgress(0);
  }, []);

  const restart = useCallback(() => {
    setActIndex(0);
    setProgress(0);
    setPlaying(false);
  }, []);

  // ===== 触摸滑动手势：左右滑动切换幕 =====
  const touchStartX = useRef<number | null>(null);
  const touchStartY = useRef<number | null>(null);

  const onTouchStart = useCallback((e: ReactTouchEvent<HTMLDivElement>) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  }, []);

  const onTouchEnd = useCallback(
    (e: ReactTouchEvent<HTMLDivElement>) => {
      if (touchStartX.current == null || touchStartY.current == null) return;
      const dx = e.changedTouches[0].clientX - touchStartX.current;
      const dy = e.changedTouches[0].clientY - touchStartY.current;
      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);
      // 水平滑动且位移足够、方向明显优于垂直，才切幕（避免误触垂直滚动）
      if (absDx > 60 && absDx > absDy * 1.6) {
        if (dx < 0) nextAct();
        else prevAct();
      }
      touchStartX.current = null;
      touchStartY.current = null;
    },
    [nextAct, prevAct],
  );

  // Auto-play timer
  useEffect(() => {
    if (!playing) {
      if (tickRef.current) clearInterval(tickRef.current);
      return;
    }
    const duration = ACT_DURATIONS[actIndex];
    const step = 50;
    tickRef.current = setInterval(() => {
      setProgress((p) => {
        const next = p + (step / duration) * 100;
        if (next >= 100) {
          if (actIndex < ACT_COUNT - 1) {
            setActIndex((a) => a + 1);
            return 0;
          }
          setPlaying(false);
          return 100;
        }
        return next;
      });
    }, step);
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [playing, actIndex]);

  const currentAct = ACTS[actIndex];
  const theme = THEME_COLORS[currentAct.theme];

  const renderAct = () => {
    switch (actIndex) {
      case 0: return <Act1Content kiosk={kiosk} />;
      case 1: return <Act2Content kiosk={kiosk} />;
      case 2: return <Act3Content kiosk={kiosk} />;
      case 3: return <Act4Content kiosk={kiosk} />;
      case 4: return <Act5Content kiosk={kiosk} />;
      default: return null;
    }
  };

  return (
    <div className={kiosk ? "cs-kiosk" : undefined}>
      <DemoBadge level="L3" visible />
      {/* Header */}
      <Space style={{ justifyContent: "space-between", width: "100%", marginBottom: 12 }}>
        <Title level={3} style={{ margin: 0 }}>
          Demo 故事模式
        </Title>
        <Space size={12}>
          {kiosk && (
            <Tag color="blue" style={{ borderRadius: 12, fontSize: 13 }}>
              触摸大屏 · 左右滑动切幕
            </Tag>
          )}
          <Tag color={playing ? "processing" : "default"} style={{ borderRadius: 12, fontSize: kiosk ? 15 : undefined }}>
            {currentAct.tag} · {currentAct.timecode}
          </Tag>
        </Space>
      </Space>

      {/* Act selector tabs */}
      <div style={{ display: "flex", gap: kiosk ? 10 : 6, marginBottom: 12, flexWrap: "wrap" }}>
        {ACTS.map((act) => {
          const isActive = act.index === actIndex;
          const t = THEME_COLORS[act.theme];
          return (
            <button
              key={act.index}
              onClick={() => goToAct(act.index)}
              style={{
                flex: "1 1 0",
                minWidth: kiosk ? 160 : 120,
                padding: kiosk ? "12px 14px" : "8px 10px",
                borderRadius: 10,
                border: `1px solid ${isActive ? t.primary : "rgba(15,23,42,0.08)"}`,
                background: isActive ? t.primary + "12" : "#fff",
                cursor: "pointer",
                transition: "all 0.25s",
                textAlign: "left",
              }}
            >
              <div style={{ fontSize: kiosk ? 14 : 11, fontWeight: 700, color: isActive ? t.primary : "#5A6B82" }}>
                {act.tag} · {act.timecode}
              </div>
              <div style={{ fontSize: kiosk ? 15 : 12, color: isActive ? "#1f2937" : "#8ea5c4", marginTop: 2 }}>
                {act.title}
              </div>
            </button>
          );
        })}
      </div>

      {/* Act progress bar */}
      <div style={{ marginBottom: 12 }}>
        <Progress
          percent={progress}
          showInfo={false}
          strokeColor={theme.primary}
          trailColor="rgba(15,23,42,0.06)"
          size={kiosk ? "default" : "small"}
        />
      </div>

      {/* Stage — dark cinematic area（支持触摸滑动切幕） */}
      <div
        className={`story-dark-bg story-theme-${theme.bg}`}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        style={{
          minHeight: kiosk ? 680 : 480,
          padding: kiosk ? "36px 28px" : "28px 20px",
          marginBottom: 12,
          // 允许垂直滚动，将水平手势交给切幕逻辑
          touchAction: "pan-y",
          userSelect: "none",
        }}
      >
        {/* Act title */}
        <div style={{ textAlign: "center", marginBottom: kiosk ? 22 : 16 }}>
          <div
            className="story-fade-in"
            style={{ fontSize: kiosk ? 14 : 11, letterSpacing: "0.2em", fontWeight: 700, color: theme.primary }}
          >
            {currentAct.tag} · {currentAct.timecode}
          </div>
          <div
            className="story-fade-in"
            style={{
              fontSize: kiosk ? 30 : 22,
              fontWeight: 700,
              color: "#e8eef5",
              marginTop: 4,
            }}
          >
            {currentAct.title}
          </div>
          <div
            className="story-fade-in"
            style={{ fontSize: kiosk ? 16 : 13, color: "#5A6B82", marginTop: 2 }}
          >
            {currentAct.subtitle}
          </div>
        </div>

        {/* Act content */}
        {renderAct()}
      </div>

      {/* Controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: kiosk ? 16 : 8,
          padding: kiosk ? "16px 0" : "12px 0",
        }}
      >
        <Tooltip title="上一幕">
          <Button
            icon={<StepBackwardOutlined />}
            onClick={prevAct}
            disabled={actIndex === 0}
            size="large"
            style={{ minWidth: 56, minHeight: 48 }}
          />
        </Tooltip>
        <Button
          type="primary"
          size="large"
          icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
          onClick={() => {
            if (actIndex >= ACT_COUNT - 1 && progress >= 100) {
              restart();
              setTimeout(() => setPlaying(true), 100);
            } else {
              setPlaying(!playing);
            }
          }}
          style={{ borderRadius: 24, paddingInline: kiosk ? 32 : 24, minHeight: 48, fontSize: kiosk ? 17 : undefined }}
        >
          {playing ? "暂停" : actIndex >= ACT_COUNT - 1 && progress >= 100 ? "重播" : "播放"}
        </Button>
        <Tooltip title="下一幕">
          <Button
            icon={<StepForwardOutlined />}
            onClick={nextAct}
            disabled={actIndex >= ACT_COUNT - 1}
            size="large"
            style={{ minWidth: 56, minHeight: 48 }}
          />
        </Tooltip>
        <Tooltip title="重新开始">
          <Button icon={<ReloadOutlined />} onClick={restart} size="large" style={{ minWidth: 56, minHeight: 48 }} />
        </Tooltip>
      </div>

      <div style={{ textAlign: "center" }}>
        <Text type="secondary" style={{ fontSize: kiosk ? 15 : 12 }}>
          五幕剧 · 5 分钟见证 Agent 闭环守护价值 ·{" "}
          {actIndex + 1} / {ACT_COUNT}
        </Text>
      </div>

      {/* 真实数字生命叙事：聚合本车 life-events + memories 真实落盘数据 */}
      <RealLifeStorySection kiosk={kiosk} />
    </div>
  );
}
