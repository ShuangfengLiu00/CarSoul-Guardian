import { useEffect, useMemo, useRef, useState } from "react";
import {
  Card,
  Row,
  Col,
  Tag,
  Progress,
  Button,
  Typography,
  Space,
  Empty,
  Statistic,
  Divider,
} from "antd";
import {
  CarOutlined,
  ThunderboltOutlined,
  DashboardOutlined,
  ApiOutlined,
  DeploymentUnitOutlined,
  ControlOutlined,
  SafetyCertificateOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { ClosedLoopTrace, DemoBadge } from "@/components";
import {
  DEMO_VEHICLE,
  DEMO_LATEST_HEALTH,
  DEMO_ALERTS,
  DEMO_MAINTENANCE_SCHEDULES,
} from "@/services/demoData";
import type { ClosedLoop, Alert, MaintenanceSchedule } from "@/services/types";

const { Title, Text, Paragraph } = Typography;

type Phase = "idle" | "detect" | "guard" | "recovered";

interface Part {
  key: string;
  name: string;
  field:
    | "engine_score"
    | "brake_score"
    | "tire_score"
    | "battery_score"
    | "body_score"
    | "electronics_score";
  icon: typeof CarOutlined;
  /** 标注气泡中心 */
  chipX: number;
  chipY: number;
  /** 引线指向的零件锚点 */
  leadX: number;
  leadY: number;
  /** alert category that maps to this part */
  alertCategory?: string;
  /** maintenance-schedule category that maps to this part */
  schedCategory?: string;
  /** generic repair tip */
  tips: string[];
}

const PARTS: Part[] = [
  {
    key: "body",
    name: "车身结构",
    field: "body_score",
    icon: CarOutlined,
    chipX: 372,
    chipY: 80,
    leadX: 361,
    leadY: 150,
    schedCategory: "车身",
    tips: ["检查漆面与底盘锈蚀", "关注车门密封与异响", "事故后做四轮定位"],
  },
  {
    key: "electronics",
    name: "电子电气",
    field: "electronics_score",
    icon: ControlOutlined,
    chipX: 112,
    chipY: 80,
    leadX: 141,
    leadY: 216,
    schedCategory: "电子",
    tips: ["扫描故障码排查偶发报警", "检查电瓶电压与线束", "升级车机与控制器固件"],
  },
  {
    key: "powertrain",
    name: "动力系统",
    field: "engine_score",
    icon: DashboardOutlined,
    chipX: 648,
    chipY: 250,
    leadX: 520,
    leadY: 252,
    schedCategory: "常规",
    tips: ["检查电机/发动机工况与冷却液", "关注加速抖动与异响", "按周期更换机油机滤"],
  },
  {
    key: "battery",
    name: "电池系统",
    field: "battery_score",
    icon: ThunderboltOutlined,
    chipX: 372,
    chipY: 362,
    leadX: 372,
    leadY: 270,
    alertCategory: "电池系统",
    schedCategory: "电池",
    tips: ["监测电池温度与 SOC 趋势", "关注冷却效率与热失控风险", "定期到店做电池健康检测"],
  },
  {
    key: "brake",
    name: "制动系统",
    field: "brake_score",
    icon: ApiOutlined,
    chipX: 200,
    chipY: 362,
    leadX: 200,
    leadY: 304,
    schedCategory: "制动",
    tips: ["检查刹车片剩余厚度", "关注制动距离与异响", "定期更换制动液"],
  },
  {
    key: "tire",
    name: "轮胎系统",
    field: "tire_score",
    icon: DeploymentUnitOutlined,
    chipX: 535,
    chipY: 362,
    leadX: 535,
    leadY: 328,
    alertCategory: "轮胎系统",
    schedCategory: "轮胎",
    tips: ["保持推荐胎压", "检查胎纹深度与磨损", "定期四轮换位"],
  },
];

const scoreColor = (s: number) =>
  s >= 85 ? "#10b981" : s >= 60 ? "#f59e0b" : "#ef4444";
const scoreLevel = (s: number) =>
  s >= 85 ? "良好" : s >= 60 ? "关注" : "需检修";

/** 渲染每个子系统在车辆上的真实形态（剖视图） */
function renderPartGeo(key: string, color: string, active: boolean) {
  const fillOp = active ? 0.42 : 0.24;
  switch (key) {
    case "body":
      return (
        <>
          {/* 车顶纵梁 */}
          <line x1="252" y1="150" x2="470" y2="150" stroke={color} strokeWidth="5" strokeLinecap="round" opacity={active ? 0.95 : 0.6} />
          {/* A 柱 */}
          <line x1="252" y1="150" x2="232" y2="206" stroke={color} strokeWidth="5" strokeLinecap="round" opacity={active ? 0.95 : 0.6} />
          {/* C 柱 */}
          <line x1="470" y1="150" x2="520" y2="206" stroke={color} strokeWidth="5" strokeLinecap="round" opacity={active ? 0.95 : 0.6} />
          {/* B 柱 */}
          <line x1="360" y1="150" x2="360" y2="200" stroke={color} strokeWidth="4" strokeLinecap="round" opacity={active ? 0.9 : 0.55} />
          {/* 门槛梁 */}
          <line x1="120" y1="278" x2="600" y2="278" stroke={color} strokeWidth="4" strokeLinecap="round" opacity={active ? 0.9 : 0.5} />
        </>
      );
    case "electronics":
      return (
        <>
          {/* ECU 控制盒（前备舱） */}
          <rect x="118" y="216" width="46" height="30" rx="4" fill={color} fillOpacity={fillOp} stroke={color} strokeWidth="2" />
          <circle cx="141" cy="231" r="4" fill={color} />
          <line x1="125" y1="224" x2="157" y2="224" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="125" y1="240" x2="157" y2="240" stroke={color} strokeWidth="1" opacity="0.6" />
          {/* 线束 */}
          <path d="M 164 231 C 200 235, 210 250, 250 252 S 360 256, 420 252 S 520 246, 560 240" fill="none" stroke={color} strokeWidth="2" opacity="0.7" strokeDasharray="3 3" />
          {/* 中控屏 */}
          <rect x="300" y="172" width="34" height="22" rx="3" fill={color} fillOpacity={fillOp} stroke={color} strokeWidth="1.5" />
          <line x1="305" y1="178" x2="329" y2="178" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="305" y1="184" x2="324" y2="184" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="305" y1="189" x2="328" y2="189" stroke={color} strokeWidth="1" opacity="0.6" />
        </>
      );
    case "powertrain":
      return (
        <>
          {/* 后桥驱动电机 */}
          <ellipse cx="498" cy="270" rx="40" ry="26" fill={color} fillOpacity={fillOp} stroke={color} strokeWidth="2" />
          {Array.from({ length: 7 }).map((_, i) => (
            <line key={i} x1={470 + i * 8} y1="250" x2={470 + i * 8} y2="290" stroke={color} strokeWidth="1" opacity="0.5" />
          ))}
          <circle cx="498" cy="270" r="7" fill={color} />
          {/* 传动轴连后轮 */}
          <line x1="498" y1="282" x2="535" y2="282" stroke={color} strokeWidth="3" opacity="0.8" />
        </>
      );
    case "battery":
      return (
        <>
          {/* 滑板式电池组（底盘） */}
          <rect x="222" y="258" width="300" height="24" rx="5" fill={color} fillOpacity={fillOp} stroke={color} strokeWidth="2" />
          {Array.from({ length: 9 }).map((_, i) => (
            <line key={i} x1={236 + i * 32} y1="260" x2={236 + i * 32} y2="280" stroke={color} strokeWidth="1.2" opacity="0.7" />
          ))}
          <line x1="226" y1="270" x2="518" y2="270" stroke={color} strokeWidth="1" opacity="0.5" />
          {/* 高压接口 */}
          <rect x="208" y="262" width="14" height="16" rx="2" fill={color} fillOpacity={0.7} />
          <rect x="522" y="262" width="14" height="16" rx="2" fill={color} fillOpacity={0.7} />
        </>
      );
    case "brake":
      return (
        <>
          {[200, 535].map((cx) => (
            <g key={cx}>
              {/* 制动盘 */}
              <circle cx={cx} cy={282} r={22} fill={color} fillOpacity={fillOp} stroke={color} strokeWidth="2" />
              {/* 盘面钻孔 */}
              {[0, 60, 120, 180, 240, 300].map((a) => (
                <circle key={a} cx={cx + Math.cos((a * Math.PI) / 180) * 13} cy={282 + Math.sin((a * Math.PI) / 180) * 13} r="2" fill={color} opacity="0.85" />
              ))}
              {/* 卡钳 */}
              <rect x={cx - 7} y={252} width="14" height="10" rx="2" fill={color} fillOpacity="0.85" />
            </g>
          ))}
        </>
      );
    case "tire":
      return (
        <>
          {[200, 535].map((cx) => (
            <g key={cx}>
              {/* 胎面环 */}
              <circle cx={cx} cy={282} r={46} fill="none" stroke={color} strokeWidth="10" opacity={active ? 0.95 : 0.7} />
              {/* 胎纹 */}
              {Array.from({ length: 24 }).map((_, i) => {
                const a = (i * 15 * Math.PI) / 180;
                return (
                  <line key={i} x1={cx + Math.cos(a) * 42} y1={282 + Math.sin(a) * 42} x2={cx + Math.cos(a) * 46} y2={282 + Math.sin(a) * 46} stroke={color} strokeWidth="2" opacity="0.6" />
                );
              })}
            </g>
          ))}
        </>
      );
    default:
      return null;
  }
}

const BATTERY_THERMAL_LOOP: ClosedLoop = {
  is_normal: false,
  steps: [
    {
      step: "perceive",
      agent: "perception",
      title: "状态感知",
      detail: "电池组温度 48.0℃ 超阈值 40℃，冷却效率降至 62%，SOC 异常下降。",
      status: "done",
      data: { battery_temp: 48, cooling: 62 },
    },
    {
      step: "understand",
      agent: "diagnosis",
      title: "故障诊断",
      detail: "根因：冷却液循环异常导致热积聚，置信度 88%。",
      status: "done",
      data: { root_cause: "冷却液循环异常", confidence: 0.88 },
    },
    {
      step: "reason",
      agent: "risk",
      title: "风险评估",
      detail: "热失控风险 HIGH，2 小时内演变为故障概率 72%。",
      status: "done",
      data: { level: "high", probability: 0.72, eta_hours: 2 },
    },
    {
      step: "tool",
      agent: "explainer",
      title: "守护建议",
      detail: "已远程启动电池主动冷却，建议近期前往服务中心检测冷却系统。",
      status: "done",
      data: {},
    },
    {
      step: "act",
      agent: "service",
      title: "服务执行",
      detail: "已推送 critical 提醒并记录至车辆数字生命档案。",
      status: "done",
      data: {},
    },
  ],
  anomalies: [{ name: "电池温度超限", value: "48.0℃", threshold: "40℃" }],
  diagnosis: { root_cause: "冷却液循环异常", confidence: 0.88 },
  risk: { level: "high", probability: 0.72, eta_hours: 2 },
  actions: [
    "远程启动电池主动冷却",
    "推送 critical 级别提醒",
    "记录热事件至数字生命档案",
    "建议预约服务中心检测冷却系统",
  ],
  reminder: { title: "电池热失控风险·已启动主动冷却", level: "critical" },
};

const NORMAL_LOOP: ClosedLoop = {
  is_normal: true,
  steps: [
    {
      step: "perceive",
      agent: "perception",
      title: "状态感知",
      detail: "全部传感器读数在阈值内，无异常。",
      status: "done",
    },
    {
      step: "normal_report",
      agent: "explainer",
      title: "健康报告",
      detail: "车辆健康指数 90/100，各子系统运转正常。",
      status: "done",
    },
    {
      step: "act",
      agent: "service",
      title: "服务执行",
      detail: "无守护动作触发，记录本次巡检至数字生命档案。",
      status: "done",
    },
  ],
  anomalies: [],
  diagnosis: {},
  risk: {},
  actions: [],
  reminder: null,
};

const TELEM_BY_PHASE: Record<Phase, Record<string, number>> = {
  idle: { battery_temp: 35.0, battery_soc: 72, cooling_efficiency: 92, cabin_temp: 26, tire_pressure_fl: 2.3 },
  detect: { battery_temp: 43.2, battery_soc: 70, cooling_efficiency: 78, cabin_temp: 26, tire_pressure_fl: 2.3 },
  guard: { battery_temp: 48.0, battery_soc: 63, cooling_efficiency: 62, cabin_temp: 27, tire_pressure_fl: 2.1 },
  recovered: { battery_temp: 38.5, battery_soc: 66, cooling_efficiency: 78, cabin_temp: 26, tire_pressure_fl: 2.3 },
};

const BATTERY_SCORE_BY_PHASE: Record<Phase, number> = {
  idle: 90,
  detect: 72,
  guard: 58,
  recovered: 76,
};

export default function VehicleSimulator() {
  const [selected, setSelected] = useState<string>("battery");
  const [phase, setPhase] = useState<Phase>("idle");
  const timers = useRef<number[]>([]);

  const clearTimers = () => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  };

  useEffect(() => () => clearTimers(), []);

  const startSim = () => {
    clearTimers();
    setPhase("detect");
    timers.current.push(window.setTimeout(() => setPhase("guard"), 1300));
    timers.current.push(window.setTimeout(() => setPhase("recovered"), 3400));
  };

  const resetSim = () => {
    clearTimers();
    setPhase("idle");
  };

  const health = DEMO_LATEST_HEALTH;
  const telem = TELEM_BY_PHASE[phase];

  const partScore = (p: Part) =>
    p.key === "battery"
      ? BATTERY_SCORE_BY_PHASE[phase]
      : (health[p.field] ?? 85);

  const selectedPart = PARTS.find((p) => p.key === selected) ?? PARTS[3];
  const selScore = partScore(selectedPart);

  const partAlerts = useMemo<Alert[]>(
    () =>
      selectedPart.alertCategory
        ? DEMO_ALERTS.filter((a) => a.category === selectedPart.alertCategory)
        : [],
    [selectedPart],
  );
  const partSchedules = useMemo<MaintenanceSchedule[]>(
    () =>
      selectedPart.schedCategory
        ? DEMO_MAINTENANCE_SCHEDULES.filter(
            (s) => s.category === selectedPart.schedCategory,
          )
        : [],
    [selectedPart],
  );

  const loop = phase === "idle" ? NORMAL_LOOP : BATTERY_THERMAL_LOOP;

  const phaseTag = () => {
    switch (phase) {
      case "detect":
        return <Tag color="orange">感知异常中…</Tag>;
      case "guard":
        return <Tag color="red">守护闭环执行中</Tag>;
      case "recovered":
        return <Tag color="green">守护完成·温度回落</Tag>;
      default:
        return <Tag color="blue">正常巡检</Tag>;
    }
  };

  return (
    <div>
      <DemoBadge level="L3" visible />
      <Space className="cs-dashboard__header" style={{ marginBottom: 4 }}>
        <Title level={3} style={{ margin: 0 }}>
          车辆演示推演
        </Title>
        {phaseTag()}
      </Space>
      <Paragraph type="secondary" style={{ marginTop: -2, marginBottom: 14 }}>
        数字孪生车辆剖面图 · 点击车辆部件查看健康与检修建议 · 一键仿真守护闭环
      </Paragraph>

      <Row gutter={[16, 16]}>
        {/* 车辆剖视图舞台 */}
        <Col xs={24} lg={15}>
          <Card className="cs-card" styles={{ body: { padding: 12 } }}>
            <div className="cs-sim-stage" style={{ color: "#e2e8f0" }}>
              <Row justify="space-between" align="middle" style={{ marginBottom: 8 }}>
                <Space>
                  <CarOutlined style={{ fontSize: 20, color: "#60a5fa" }} />
                  <Text style={{ color: "#e2e8f0", fontWeight: 600, fontSize: 16 }}>
                    {DEMO_VEHICLE.brand} {DEMO_VEHICLE.model}
                  </Text>
                  <Tag color="blue">{DEMO_VEHICLE.year}</Tag>
                  <Text style={{ color: "#94a3b8", fontSize: 13 }}>
                    {DEMO_VEHICLE.fuel_type === "electric" ? "纯电" : DEMO_VEHICLE.fuel_type}
                  </Text>
                </Space>
                <Statistic
                  value={health.health_score}
                  suffix="/100"
                  prefix={<SafetyCertificateOutlined style={{ color: "#10b981" }} />}
                  valueStyle={{ color: scoreColor(health.health_score), fontSize: 24 }}
                />
              </Row>

              <svg viewBox="0 0 720 380" style={{ width: "100%", height: "auto", display: "block" }}>
                <defs>
                  <linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.18" />
                    <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.08" />
                  </linearGradient>
                  <linearGradient id="glassGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7dd3fc" stopOpacity="0.55" />
                    <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.32" />
                  </linearGradient>
                  <radialGradient id="stageGlow" cx="50%" cy="38%" r="75%">
                    <stop offset="0%" stopColor="#16243d" />
                    <stop offset="100%" stopColor="#0b1220" />
                  </radialGradient>
                </defs>

                {/* 舞台底色 */}
                <rect x="0" y="0" width="720" height="380" fill="url(#stageGlow)" />
                {/* 地面 + 投影 */}
                <ellipse cx="367" cy="332" rx="300" ry="7" fill="#000" opacity="0.4" />
                <line x1="40" y1="336" x2="680" y2="336" stroke="#1e293b" strokeWidth="2" />
                <line x1="40" y1="340" x2="680" y2="340" stroke="#0f1b2d" strokeWidth="6" opacity="0.6" />

                {/* ===== 中性车辆骨架（不可交互） ===== */}
                <g pointerEvents="none">
                  {/* 车身轮廓 */}
                  <path
                    d="M 95 278 L 95 244 C 95 230 110 222 128 220 L 232 206 L 252 150 C 256 140 268 134 282 134 L 452 134 C 470 134 482 142 488 154 L 520 206 L 596 214 C 618 216 630 228 630 246 L 630 278 Z"
                    fill="url(#bodyGrad)"
                    stroke="#5b6b86"
                    strokeWidth="1.5"
                  />
                  {/* 车窗玻璃 */}
                  <path d="M 268 150 C 272 144 280 140 288 140 L 446 140 C 456 140 464 146 468 156 L 488 200 L 250 200 Z" fill="url(#glassGrad)" opacity="0.85" />
                  {/* 腰线 */}
                  <line x1="250" y1="200" x2="500" y2="200" stroke="#475569" strokeWidth="1.5" opacity="0.55" />
                  {/* 引擎盖线 */}
                  <line x1="128" y1="220" x2="232" y2="206" stroke="#475569" strokeWidth="1.2" opacity="0.45" />
                  {/* 门缝 */}
                  <line x1="345" y1="150" x2="345" y2="272" stroke="#475569" strokeWidth="1" opacity="0.3" strokeDasharray="4 4" />
                  <line x1="432" y1="150" x2="432" y2="272" stroke="#475569" strokeWidth="1" opacity="0.3" strokeDasharray="4 4" />
                  {/* 大灯 / 尾灯 */}
                  <rect x="100" y="244" width="26" height="8" rx="4" fill="#fde68a" opacity="0.9" />
                  <rect x="600" y="244" width="24" height="8" rx="4" fill="#f87171" opacity="0.85" />
                  {/* 门把手 */}
                  <rect x="378" y="216" width="22" height="4" rx="2" fill="#3b5168" opacity="0.6" />
                  {/* 轮拱（挖空） */}
                  <circle cx="200" cy="282" r="52" fill="#0b1220" />
                  <circle cx="535" cy="282" r="52" fill="#0b1220" />
                  {/* 中性轮组 */}
                  {[200, 535].map((cx) => (
                    <g key={cx}>
                      <circle cx={cx} cy={282} r={46} fill="#0f172a" stroke="#334155" strokeWidth="2" />
                      <circle cx={cx} cy={282} r={30} fill="#475569" />
                      {/* 轮辐 */}
                      {[0, 72, 144, 216, 288].map((a) => (
                        <line key={a} x1={cx} y1={282} x2={cx + Math.cos((a * Math.PI) / 180) * 28} y2={282 + Math.sin((a * Math.PI) / 180) * 28} stroke="#64748b" strokeWidth="3" />
                      ))}
                      <circle cx={cx} cy={282} r={8} fill="#1e293b" />
                      <circle cx={cx} cy={282} r={3} fill="#94a3b8" />
                    </g>
                  ))}
                </g>

                {/* ===== 交互式部件层（按健康分着色） ===== */}
                {PARTS.map((p) => {
                  const s = partScore(p);
                  const color = scoreColor(s);
                  const active = selected === p.key;
                  return (
                    <g
                      key={p.key}
                      className={`cs-sim-part ${active ? "cs-sim-part--active" : ""}`}
                      onClick={() => setSelected(p.key)}
                      style={{ color, opacity: active ? 1 : 0.72 }}
                    >
                      {renderPartGeo(p.key, color, active)}
                    </g>
                  );
                })}

                {/* ===== 引线标注气泡 ===== */}
                {PARTS.map((p) => {
                  const s = partScore(p);
                  const color = scoreColor(s);
                  const active = selected === p.key;
                  return (
                    <g key={`lab-${p.key}`} style={{ pointerEvents: "none" }}>
                      <line
                        x1={p.chipX}
                        y1={p.chipY}
                        x2={p.leadX}
                        y2={p.leadY}
                        stroke={color}
                        strokeWidth="1.2"
                        opacity={active ? 0.9 : 0.35}
                        strokeDasharray="3 3"
                      />
                      <circle cx={p.leadX} cy={p.leadY} r="3" fill={color} opacity={active ? 1 : 0.6} />
                      <g className="cs-sim-chip-text" onClick={() => setSelected(p.key)} style={{ cursor: "pointer", pointerEvents: "all" }}>
                        <rect
                          x={p.chipX - 46}
                          y={p.chipY - 14}
                          width="92"
                          height="28"
                          rx="14"
                          fill={active ? color : "#0f1b2d"}
                          fillOpacity={active ? 0.95 : 0.78}
                          stroke={color}
                          strokeWidth="1.5"
                        />
                        <text x={p.chipX} y={p.chipY - 1} textAnchor="middle" fill={active ? "#fff" : color} fontSize="11" fontWeight="700">
                          {p.name}
                        </text>
                        <text x={p.chipX} y={p.chipY + 10} textAnchor="middle" fill={active ? "#fff" : color} fontSize="10" fontWeight="700">
                          {s} 分
                        </text>
                      </g>
                    </g>
                  );
                })}
              </svg>

              {/* 图例 */}
              <div className="cs-sim-legend" style={{ marginTop: 8 }}>
                <span className="cs-sim-legend-item">
                  <span className="cs-sim-legend-dot" style={{ background: "#10b981" }} /> 良好 ≥85
                </span>
                <span className="cs-sim-legend-item">
                  <span className="cs-sim-legend-dot" style={{ background: "#f59e0b" }} /> 关注 60-84
                </span>
                <span className="cs-sim-legend-item">
                  <span className="cs-sim-legend-dot" style={{ background: "#ef4444" }} /> 需检修 &lt;60
                </span>
                <span style={{ color: "#64748b" }}>· 点击部件查看详情</span>
              </div>
            </div>

            {/* 实时遥测条 */}
            <div className="cs-sim-telem" style={{ marginTop: 12 }}>
              {[
                { k: "battery_temp", label: "电池温度", unit: "℃", warn: telem.battery_temp > 40 },
                { k: "battery_soc", label: "电池 SOC", unit: "%" },
                { k: "cooling_efficiency", label: "冷却效率", unit: "%", warn: telem.cooling_efficiency < 70 },
                { k: "cabin_temp", label: "车内温度", unit: "℃" },
                { k: "tire_pressure_fl", label: "左前胎压", unit: "bar", warn: telem.tire_pressure_fl < 2.2 },
              ].map((t) => (
                <div className="cs-sim-telem-item" key={t.k}>
                  <div className="cs-sim-telem-label">{t.label}</div>
                  <div className="cs-sim-telem-value" style={{ color: t.warn ? "#f87171" : "#e2e8f0" }}>
                    {telem[t.k as keyof typeof telem]}
                    <span className="cs-sim-telem-unit">{t.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* 检修面板 */}
        <Col xs={24} lg={9}>
          <Card
            className="cs-card"
            title={
              <Space>
                <selectedPart.icon style={{ color: scoreColor(selScore) }} />
                {selectedPart.name} · 检修面板
              </Space>
            }
            extra={<Tag color={selScore >= 85 ? "green" : selScore >= 60 ? "orange" : "red"}>{scoreLevel(selScore)}</Tag>}
          >
            <div style={{ textAlign: "center", marginBottom: 12 }}>
              <Progress
                type="dashboard"
                percent={selScore}
                strokeColor={scoreColor(selScore)}
                format={(p) => `${p}`}
              />
              <Text type="secondary">健康评分</Text>
            </div>

            <Divider style={{ margin: "8px 0" }}>风险告警</Divider>
            {partAlerts.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={<span style={{ color: "#10b981" }}>该系统无活跃告警</span>}
              />
            ) : (
              partAlerts.map((a) => (
                <div
                  key={a.id}
                  style={{
                    background: a.level === "critical" ? "#fef2f2" : "#fffbeb",
                    border: `1px solid ${a.level === "critical" ? "#fecaca" : "#fde68a"}`,
                    borderRadius: 10,
                    padding: "10px 12px",
                    marginBottom: 8,
                  }}
                >
                  <Space style={{ width: "100%", justifyContent: "space-between" }}>
                    <Text strong style={{ fontSize: 14 }}>
                      {a.title}
                    </Text>
                    <Tag color={a.level === "critical" ? "red" : "orange"}>{a.level}</Tag>
                  </Space>
                  <Paragraph style={{ margin: "6px 0 0", fontSize: 13, color: "#6b7280" }}>
                    {a.detail}
                  </Paragraph>
                  {a.recommendation && (
                    <Text type="success" style={{ fontSize: 13 }}>
                      <CheckCircleOutlined style={{ marginRight: 4 }} />
                      {a.recommendation}
                    </Text>
                  )}
                </div>
              ))
            )}

            <Divider style={{ margin: "12px 0 8px" }}>检修建议</Divider>
            <ul style={{ margin: 0, paddingLeft: 4, listStyle: "none" }}>
              {selectedPart.tips.map((tip, i) => (
                <li key={i} style={{ fontSize: 14, color: "#374151", lineHeight: 1.9 }}>
                  <ToolOutlined style={{ color: "#3b82f6", marginRight: 8 }} />
                  {tip}
                </li>
              ))}
            </ul>

            {partSchedules.length > 0 && (
              <>
                <Divider style={{ margin: "12px 0 8px" }}>相关保养计划</Divider>
                {partSchedules.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "6px 0",
                      fontSize: 13,
                    }}
                  >
                    <span>
                      <Tag color={s.status === "due" ? "orange" : "default"}>{s.status}</Tag>
                      {s.item_name}
                    </span>
                    <Text type="secondary">
                      {s.next_due_km ? `${s.next_due_km} km` : ""}
                      {s.next_due_date ? ` · ${s.next_due_date}` : ""}
                    </Text>
                  </div>
                ))}
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* 守护闭环仿真演示 */}
      <Card
        className="cs-card"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <AlertOutlined style={{ color: "#3b82f6" }} />
            守护闭环仿真 · {phase === "idle" ? "正常巡检" : "电池热失控守护演示"}
          </Space>
        }
        extra={
          phase === "idle" ? (
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={startSim}
            >
              启动仿真守护
            </Button>
          ) : (
            <Button size="large" icon={<ReloadOutlined />} onClick={resetSim}>
              重置仿真
            </Button>
          )
        }
      >
        <ClosedLoopTrace loop={loop} />
        {phase === "detect" && (
          <div style={{ marginTop: 10, color: "#b45309", fontSize: 14 }}>
            <AlertOutlined style={{ marginRight: 6 }} />
            数字孪生感知到电池温度异常上升，正在向守护引擎上报…
          </div>
        )}
        {phase === "recovered" && (
          <div style={{ marginTop: 10, color: "#10b981", fontSize: 14 }}>
            <CheckCircleOutlined style={{ marginRight: 6 }} />
            主动冷却已生效，电池温度回落至安全区间，守护闭环完成并写入数字生命档案。
          </div>
        )}
      </Card>
    </div>
  );
}
