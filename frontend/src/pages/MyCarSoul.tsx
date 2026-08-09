import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Button,
  Space,
  Row,
  Col,
  Progress,
  Timeline,
  Tag,
  Statistic,
  Skeleton,
  Empty,
  Tooltip,
  Typography,
  message,
  Spin,
  Select,
  Divider,
} from "antd";
import type { ProgressProps } from "antd";
import {
  ReloadOutlined,
  CarOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  FireOutlined,
  DashboardOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  RobotOutlined,
  BulbOutlined,
  WarningOutlined,
  ToolOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  CrownOutlined,
  DatabaseOutlined,
  SafetyOutlined,
  GiftOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { vehicleService, soulService } from "@/services";
import type {
  Vehicle,
  SoulProfile,
  LifecycleGenerationResult,
  VehicleLifeEventItem,
  VehicleMemoryItem,
  VehicleHealthMetric,
  VehiclePredictionItem,
} from "@/services/types";

const { Title, Paragraph, Text } = Typography;

// ============================================================
// Constants & helpers
// ============================================================

const energyTypeText: Record<string, string> = {
  gasoline: "汽油",
  diesel: "柴油",
  electric: "电动",
  hybrid: "混动",
  plug_in_hybrid: "插电混动",
  fuel: "燃油",
};

const gradeColor: Record<string, string> = {
  legendary: "#a855f7",
  excellent: "#10b981",
  normal: "#3b82f6",
  risk: "#ef4444",
};

const stageColor: Record<string, string> = {
  NEW: "#10b981",
  GROWTH: "#3b82f6",
  MATURE: "#6366f1",
  AGING: "#f59e0b",
  RETIRE: "#6b7280",
};

function healthStrokeColor(score?: number | null): ProgressProps["strokeColor"] {
  if (score == null) return "#d1d5db";
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

function riskTagColor(level: string): string {
  if (level === "high" || level === "critical") return "red";
  if (level === "medium") return "orange";
  return "green";
}

function riskTagText(level: string): string {
  if (level === "critical") return "严重";
  if (level === "high") return "高风险";
  if (level === "medium") return "中风险";
  return "低风险";
}

const eventTypeIcon: Record<string, React.ReactNode> = {
  PURCHASE: <CarOutlined />,
  FIRST_DRIVE: <CarOutlined />,
  TRAVEL: <EnvironmentOutlined />,
  MAINTENANCE: <ToolOutlined />,
  ACCIDENT: <WarningOutlined />,
  WARNING: <WarningOutlined />,
  RECOVERY: <SafetyOutlined />,
  UPGRADE: <ThunderboltOutlined />,
  CUSTOM: <ClockCircleOutlined />,
};

const eventTypeColor: Record<string, string> = {
  PURCHASE: "green",
  FIRST_DRIVE: "cyan",
  TRAVEL: "blue",
  MAINTENANCE: "geekblue",
  ACCIDENT: "red",
  WARNING: "orange",
  RECOVERY: "green",
  UPGRADE: "purple",
  CUSTOM: "gray",
};

const eventTypeText: Record<string, string> = {
  PURCHASE: "购入",
  FIRST_DRIVE: "首次驾驶",
  TRAVEL: "出行",
  MAINTENANCE: "保养",
  ACCIDENT: "事故",
  WARNING: "预警",
  RECOVERY: "恢复",
  UPGRADE: "升级",
  CUSTOM: "其他",
};

const memoryTypeIcon: Record<string, React.ReactNode> = {
  habit: <ClockCircleOutlined />,
  event: <ExperimentOutlined />,
  preference: <HeartOutlined />,
  warning: <WarningOutlined />,
  recovery: <SafetyOutlined />,
  emotion: <DatabaseOutlined />,
  context: <NodeIndexOutlined />,
};

const memoryTypeColor: Record<string, string> = {
  habit: "blue",
  event: "cyan",
  preference: "pink",
  warning: "orange",
  recovery: "green",
  emotion: "purple",
  context: "gray",
};

const memoryTypeText: Record<string, string> = {
  habit: "习惯",
  event: "事件",
  preference: "偏好",
  warning: "预警",
  recovery: "恢复",
  emotion: "情感",
  context: "上下文",
};

function fmtDate(s?: string | null): string {
  if (!s) return "-";
  return dayjs(s).format("YYYY-MM-DD");
}

function fmtDateTime(s?: string | null): string {
  if (!s) return "-";
  return dayjs(s).format("YYYY-MM-DD HH:mm");
}

const componentLabel: Record<string, string> = {
  battery: "电池系统",
  motor: "电机系统",
  brake: "制动系统",
  tire: "轮胎系统",
  body: "车身结构",
  electronics: "电子系统",
  cooling: "冷却系统",
  engine: "发动机",
};

// ============================================================
// Sub-components
// ============================================================

interface SoulHeroProps {
  profile: SoulProfile;
}

function SoulHero({ profile }: SoulHeroProps) {
  const score = profile.soul_score;
  const color = gradeColor[profile.soul_grade] ?? "#3b82f6";

  return (
    <div className="cs-soul-hero">
      <div className="cs-soul-hero__top">
        <div style={{ flex: "1 1 300px", minWidth: 280 }}>
          <div className="cs-soul-hero__soulid">
            <CrownOutlined style={{ marginRight: 6 }} />
            灵魂ID · {profile.soul_id}
          </div>
          <div className="cs-soul-hero__name">{profile.name}</div>
          <div className="cs-soul-hero__meta">
            {profile.brand} {profile.model}
            {profile.year ? ` · ${profile.year}款` : ""}
            {" · "}
            {energyTypeText[profile.energy_type] ?? profile.energy_type}
          </div>
          <div className="cs-soul-hero__stage">
            <Tag
              color={stageColor[profile.life_stage] ?? "#6b7280"}
              style={{ borderRadius: 999, fontWeight: 700, border: "none", padding: "2px 14px" }}
            >
              {profile.life_stage_label}
            </Tag>
            <span className="cs-soul-hero__companion">
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              陪伴 {profile.companion_days} 天
            </span>
          </div>
        </div>
        <div className="cs-soul-hero__score">
          <div className="cs-soul-hero__scorenum" style={{ color }}>
            {score}
          </div>
          <div className="cs-soul-hero__scorelabel">灵魂指数 VSS</div>
          <Tag
            color={color}
            style={{ borderRadius: 999, fontWeight: 700, border: "none", padding: "2px 14px", marginTop: 6 }}
          >
            {profile.soul_grade_label}
          </Tag>
        </div>
      </div>
    </div>
  );
}

interface VitalsProps {
  profile: SoulProfile;
}

function VitalsRow({ profile }: VitalsProps) {
  const vitals = [
    {
      icon: <ClockCircleOutlined />,
      label: "陪伴时间",
      value: `${profile.companion_days} 天`,
      sub: `${(profile.companion_days / 365).toFixed(1)} 年`,
    },
    {
      icon: <DashboardOutlined />,
      label: "行驶里程",
      value: profile.mileage_label,
      sub: `${profile.mileage.toLocaleString()} km`,
    },
    {
      icon: <GiftOutlined />,
      label: "生命事件",
      value: `${profile.life_events_count} 次`,
      sub: "生命周期",
    },
    {
      icon: <DatabaseOutlined />,
      label: "AI 记忆",
      value: `${profile.memories_count} 条`,
      sub: "上下文记忆",
    },
    {
      icon: <HeartOutlined />,
      label: "整体健康",
      value: profile.health_score != null ? `${Math.round(profile.health_score)}` : "--",
      sub: "健康指数",
    },
    {
      icon: <ExperimentOutlined />,
      label: "驾驶人格",
      value: profile.driver_style_label,
      sub: profile.driver_profile?.eco_score != null
        ? `节能 ${Math.round(profile.driver_profile.eco_score)}`
        : undefined,
    },
  ];

  return (
    <div className="cs-soul-vitals">
      {vitals.map((v, i) => (
        <div className="cs-soul-vital" key={i}>
          <div className="cs-soul-vital__label">
            {v.icon}
            {v.label}
          </div>
          <div className="cs-soul-vital__value">{v.value}</div>
          {v.sub && <div className="cs-soul-vital__sub">{v.sub}</div>}
        </div>
      ))}
    </div>
  );
}

interface VssBreakdownProps {
  profile: SoulProfile;
}

function VssBreakdown({ profile }: VssBreakdownProps) {
  const b = profile.soul_breakdown;
  const weights: Record<string, string> = {
    health: "40%",
    memory: "15%",
    maintenance: "15%",
    driving: "15%",
    prediction: "15%",
  };
  const labels: Record<string, string> = {
    health: "健康状态",
    memory: "记忆丰富度",
    maintenance: "维护质量",
    driving: "驾驶关系",
    prediction: "预测稳定性",
  };
  const rows = [
    { key: "health", val: b.health, contrib: b.health_contribution },
    { key: "memory", val: b.memory, contrib: b.memory_contribution },
    { key: "maintenance", val: b.maintenance, contrib: b.maintenance_contribution },
    { key: "driving", val: b.driving, contrib: b.driving_contribution },
    { key: "prediction", val: b.prediction, contrib: b.prediction_contribution },
  ];

  return (
    <Card
      className="cs-card"
      title={<Space><DashboardOutlined /> 灵魂指数构成 (VSS)</Space>}
      style={{ height: "100%" }}
    >
      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 44, fontWeight: 800, color: gradeColor[profile.soul_grade] ?? "#3b82f6" }}>
          {profile.soul_score}
        </div>
        <Tag
          color={gradeColor[profile.soul_grade] ?? "#3b82f6"}
          style={{ marginTop: 4, fontWeight: 700, border: "none" }}
        >
          {profile.soul_grade_label}
        </Tag>
      </div>
      <div className="cs-soul-subsys">
        {rows.map((r) => (
          <div className="cs-soul-subsys__row" key={r.key}>
            <Tooltip title={`权重 ${weights[r.key]} · 贡献 ${r.contrib}`}>
              <span className="cs-soul-subsys__name">
                {labels[r.key]}
                <span className="cs-soul-subsys__weight">{weights[r.key]}</span>
              </span>
            </Tooltip>
            <Progress
              className="cs-soul-subsys__bar"
              percent={Math.round(r.val)}
              size="small"
              strokeColor={healthStrokeColor(r.val)}
              format={() => ""}
            />
            <span
              className="cs-soul-subsys__val"
              style={{ color: healthStrokeColor(r.val) as string }}
            >
              {Math.round(r.val)}
            </span>
          </div>
        ))}
      </div>
      <Divider style={{ margin: "12px 0" }} />
      <div style={{ fontSize: 12, color: "#9ca3af", textAlign: "center" }}>
        VSS = Health × 40% + Memory × 15% + Maintenance × 15% + Driving × 15% + Prediction × 15%
      </div>
    </Card>
  );
}

interface HealthMetricsProps {
  metrics: VehicleHealthMetric[];
}

function HealthMetricsPanel({ metrics }: HealthMetricsProps) {
  if (!metrics || metrics.length === 0) {
    return (
      <Card className="cs-card" title={<Space><HeartOutlined /> 组件健康指标</Space>} style={{ height: "100%" }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无健康指标数据" />
      </Card>
    );
  }

  return (
    <Card className="cs-card" title={<Space><HeartOutlined /> 组件健康指标</Space>} style={{ height: "100%" }}>
      <div className="cs-soul-subsys">
        {metrics.map((m, i) => (
          <div className="cs-soul-subsys__row" key={i}>
            <span className="cs-soul-subsys__name">
              {componentLabel[m.component] ?? m.component}
            </span>
            <Progress
              className="cs-soul-subsys__bar"
              percent={Math.round(m.health_score ?? 0)}
              size="small"
              strokeColor={healthStrokeColor(m.health_score)}
              format={() => ""}
            />
            <span className="cs-soul-subsys__val" style={{ color: healthStrokeColor(m.health_score) as string }}>
              {m.health_score != null ? Math.round(m.health_score) : "--"}
            </span>
            <Tag color={riskTagColor(m.risk_level)} style={{ marginLeft: 8, fontSize: 11 }}>
              {riskTagText(m.risk_level)}
            </Tag>
          </div>
        ))}
        {metrics.some((m) => m.wear_level != null) && (
          <div style={{ marginTop: 8, fontSize: 12, color: "#9ca3af" }}>
            <ToolOutlined style={{ marginRight: 4 }} />
            磨损度: {metrics.map((m) => `${componentLabel[m.component] ?? m.component} ${Math.round(m.wear_level ?? 0)}%`).join(" · ")}
          </div>
        )}
      </div>
    </Card>
  );
}

interface EventsProps {
  events: VehicleLifeEventItem[];
}

function LifeEventsTimeline({ events }: EventsProps) {
  if (!events || events.length === 0) {
    return (
      <Card className="cs-card" title={<Space><ClockCircleOutlined /> 生命事件时间线</Space>} style={{ height: "100%" }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无生命事件" />
      </Card>
    );
  }

  const items = events.slice(0, 20).map((ev) => ({
    color: eventTypeColor[ev.event_type] ?? "gray",
    dot: eventTypeIcon[ev.event_type] ?? <ClockCircleOutlined />,
    children: (
      <div>
        <div style={{ fontWeight: 600, fontSize: 13 }}>
          {ev.title}
          <Tag color={eventTypeColor[ev.event_type] ?? "gray"} style={{ marginLeft: 8, fontSize: 11 }}>
            {eventTypeText[ev.event_type] ?? ev.event_type}
          </Tag>
          {ev.importance >= 8 && (
            <Tag color="gold" style={{ marginLeft: 4, fontSize: 11 }}>
              <CrownOutlined /> 重要
            </Tag>
          )}
        </div>
        <div style={{ fontSize: 12, color: "#9ca3af" }}>
          {fmtDate(ev.event_time)}
          {ev.mileage != null ? ` · ${ev.mileage.toLocaleString()} km` : ""}
          {ev.cost != null ? ` · ¥${ev.cost}` : ""}
          {ev.location ? ` · ${ev.location}` : ""}
        </div>
        {ev.description && (
          <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{ev.description}</div>
        )}
      </div>
    ),
  }));

  return (
    <Card className="cs-card" title={<Space><ClockCircleOutlined /> 生命事件时间线</Space>} style={{ height: "100%" }}>
      <Timeline items={items} />
    </Card>
  );
}

interface MemoriesProps {
  memories: VehicleMemoryItem[];
}

function MemoriesPanel({ memories }: MemoriesProps) {
  if (!memories || memories.length === 0) {
    return (
      <Card className="cs-card" title={<Space><DatabaseOutlined /> 车辆记忆</Space>} style={{ height: "100%" }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无记忆数据" />
      </Card>
    );
  }

  return (
    <Card
      className="cs-card"
      title={<Space><DatabaseOutlined /> 车辆记忆 <Tag color="blue">{memories.length} 条</Tag></Space>}
      style={{ height: "100%" }}
    >
      <div className="cs-soul-memory">
        {memories.map((m, i) => (
          <div className="cs-soul-memory__item" key={i}>
            <div className="cs-soul-memory__head">
              {memoryTypeIcon[m.memory_type] ?? <NodeIndexOutlined />}
              <Tag color={memoryTypeColor[m.memory_type] ?? "gray"} style={{ fontSize: 11 }}>
                {memoryTypeText[m.memory_type] ?? m.memory_type}
              </Tag>
              {m.emotion_score != null && m.emotion_score > 0.3 && (
                <Tag color="green" style={{ fontSize: 11 }}>积极</Tag>
              )}
              {m.emotion_score != null && m.emotion_score < -0.1 && (
                <Tag color="orange" style={{ fontSize: 11 }}>消极</Tag>
              )}
            </div>
            <div className="cs-soul-memory__content">{m.content}</div>
            <div className="cs-soul-memory__time">{fmtDate(m.created_time)}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

interface PredictionsProps {
  predictions: VehiclePredictionItem[];
}

function PredictionsPanel({ predictions }: PredictionsProps) {
  if (!predictions || predictions.length === 0) {
    return (
      <Card className="cs-card" title={<Space><RobotOutlined /> AI 预测</Space>} style={{ height: "100%" }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无预测数据" />
      </Card>
    );
  }

  return (
    <Card className="cs-card" title={<Space><RobotOutlined /> AI 预测 <Tag color="blue">{predictions.length} 项</Tag></Space>} style={{ height: "100%" }}>
      <div className="cs-soul-pred">
        {predictions.map((p, i) => (
          <div className="cs-soul-pred__item" key={i}>
            <div className="cs-soul-pred__head">
              <span className="cs-soul-pred__comp">
                {componentLabel[p.target_component] ?? p.target_component}
              </span>
              <Tag color={riskTagColor(p.risk_level)}>
                {riskTagText(p.risk_level)}
              </Tag>
              {p.confidence != null && (
                <span style={{ fontSize: 11, color: "#9ca3af" }}>
                  可信度 {Math.round(p.confidence * 100)}%
                </span>
              )}
            </div>
            <div className="cs-soul-pred__text">{p.prediction}</div>
            {p.predicted_value != null && (
              <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
                预测剩余: {Math.round(p.predicted_value)} {p.predicted_unit ?? ""}
              </div>
            )}
            {p.suggestion && (
              <div className="cs-soul-pred__sugg">
                <BulbOutlined />
                {p.suggestion}
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

interface InsightsProps {
  insights: string[];
}

function AiInsightsPanel({ insights }: InsightsProps) {
  return (
    <Card
      className="cs-card"
      title={<Space><BulbOutlined style={{ color: "#f59e0b" }} /> AI 洞察</Space>}
    >
      {insights && insights.length > 0 ? (
        <ul className="cs-soul-insights">
          {insights.map((s, i) => (
            <li className="cs-soul-insights__item" key={i}>
              <BulbOutlined className="cs-soul-insights__icon" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无 AI 洞察" />
      )}
    </Card>
  );
}

interface AgentHooksProps {
  profile: SoulProfile;
  onQuery: (agentType: string) => void;
  loading: boolean;
}

function AgentHooksPanel({ profile, onQuery, loading }: AgentHooksProps) {
  const agents = [
    { key: "doctor", icon: <RobotOutlined />, label: "AI 车辆医生", desc: "健康诊断与故障分析", color: "#3b82f6" },
    { key: "maintenance", icon: <ToolOutlined />, label: "AI 维修顾问", desc: "维护建议与保养方案", color: "#10b981" },
    { key: "insurance", icon: <SafetyOutlined />, label: "AI 保险顾问", desc: "风险评估与保费方案", color: "#a855f7" },
  ];

  return (
    <Card className="cs-card" title={<Space><NodeIndexOutlined /> Agent 接口预留</Space>}>
      <Row gutter={[12, 12]}>
        {agents.map((a) => (
          <Col xs={24} md={8} key={a.key}>
            <div
              className="cs-soul-agent"
              style={{ borderLeft: `3px solid ${a.color}` }}
              onClick={() => onQuery(a.key)}
            >
              <div className="cs-soul-agent__icon" style={{ color: a.color }}>
                {a.icon}
              </div>
              <div className="cs-soul-agent__body">
                <div className="cs-soul-agent__title">{a.label}</div>
                <div className="cs-soul-agent__desc">{a.desc}</div>
              </div>
              <Tag color={profile.agent_hooks?.[`ai_${a.key}`]?.status === "available" ? "green" : "default"} style={{ fontSize: 11 }}>
                {profile.agent_hooks?.[`ai_${a.key}`]?.status === "available" ? "可用" : "未激活"}
              </Tag>
            </div>
          </Col>
        ))}
      </Row>
      {loading && (
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <Spin tip="Agent 正在分析..." />
        </div>
      )}
    </Card>
  );
}

// ============================================================
// Main page
// ============================================================

export default function MyCarSoul() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclesLoading, setVehiclesLoading] = useState(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);
  const [profile, setProfile] = useState<SoulProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentResult, setAgentResult] = useState<string | null>(null);

  const loadVehicles = useCallback(async () => {
    setVehiclesLoading(true);
    try {
      const data = await vehicleService.list();
      setVehicles(data.items);
      if (!selectedVehicleId && data.items.length > 0) {
        setSelectedVehicleId(data.items[0].id);
      }
    } catch {
      /* handled by interceptor */
    } finally {
      setVehiclesLoading(false);
    }
  }, [selectedVehicleId]);

  const loadProfile = useCallback(async (id: number) => {
    setLoading(true);
    setAgentResult(null);
    try {
      const p = await soulService.getSoulProfile(id);
      setProfile(p);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  useEffect(() => {
    if (selectedVehicleId != null) {
      loadProfile(selectedVehicleId);
    } else {
      setProfile(null);
    }
  }, [selectedVehicleId, loadProfile]);

  const handleGenerateLifecycle = async () => {
    if (selectedVehicleId == null) return;
    setGenerating(true);
    try {
      const result: LifecycleGenerationResult = await soulService.generateLifecycle(
        selectedVehicleId,
        true,
      );
      if (result.skipped) {
        message.info(result.message);
      } else {
        message.success(
          `已生成365天生命周期: ${result.health_metrics ?? 0} 条健康指标, ` +
          `${result.sensor_readings ?? 0} 条传感器数据, ` +
          `${result.life_events ?? 0} 个生命事件, ` +
          `${result.memories ?? 0} 条记忆, ` +
          `${result.predictions ?? 0} 个预测`,
        );
      }
      await loadProfile(selectedVehicleId);
    } catch {
      message.error("生命周期数据生成失败");
    } finally {
      setGenerating(false);
    }
  };

  const handleAgentQuery = async (agentType: string) => {
    if (selectedVehicleId == null) return;
    setAgentLoading(true);
    setAgentResult(null);
    try {
      const resp = await soulService.queryAgent(
        selectedVehicleId,
        agentType,
        "请给出当前车辆的全面分析报告。",
      );
      setAgentResult(`【${resp.agent_type}】\n${resp.answer}`);
      message.success("Agent 分析完成");
    } catch {
      message.error("Agent 查询失败");
    } finally {
      setAgentLoading(false);
    }
  };

  const vehicleOptions = vehicles.map((v) => ({
    value: v.id,
    label: v.nickname
      ? `${v.nickname} (${v.brand} ${v.model})`
      : `${v.brand} ${v.model} (${v.year})`,
  }));

  return (
    <div>
      {/* 本页数据全部来自 soulService / vehicleService 真实接口（getSoulProfile / list），
          失败时置 null 走空态，没有任何 demo 数据分支 —— 故不挂 DemoBadge。
          若后续引入占位数据，请用 <DemoBadge level="L2" visible={...} /> 条件式挂载。 */}
      {/* ---- Header ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
          marginBottom: 20,
        }}
      >
        <Space align="center" size="middle">
          <Title level={4} style={{ margin: 0 }}>
            <CrownOutlined style={{ marginRight: 8, color: "#a855f7" }} />
            My CarSoul
          </Title>
          <Select
            value={selectedVehicleId ?? undefined}
            onChange={(v) => setSelectedVehicleId(v)}
            style={{ minWidth: 240 }}
            placeholder="选择车辆"
            loading={vehiclesLoading}
            options={vehicleOptions}
            showSearch
            optionFilterProp="label"
          />
        </Space>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => selectedVehicleId && loadProfile(selectedVehicleId)}
            disabled={selectedVehicleId == null}
          >
            刷新灵魂
          </Button>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={generating}
            onClick={handleGenerateLifecycle}
            disabled={selectedVehicleId == null}
          >
            生成365天生命周期
          </Button>
        </Space>
      </div>

      {/* ---- Empty state ---- */}
      {!selectedVehicleId && (
        <Card className="cs-card">
          <Empty
            image={<CarOutlined style={{ fontSize: 56, color: "#9ca3af" }} />}
            description="请选择一辆车，查看它的数字灵魂档案"
          >
            {!vehicles.length && !vehiclesLoading && (
              <Paragraph type="secondary" style={{ textAlign: "center" }}>
                还没有车辆？前往「车辆档案」页面创建第一辆车，开启数字生命之旅。
              </Paragraph>
            )}
          </Empty>
        </Card>
      )}

      {/* ---- Loading state ---- */}
      {selectedVehicleId && loading && (
        <Card className="cs-card">
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      )}

      {/* ---- Main content ---- */}
      {selectedVehicleId && !loading && profile && (
        <Spin spinning={false}>
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <SoulHero profile={profile} />
            </Col>
            <Col span={24}>
              <VitalsRow profile={profile} />
            </Col>
            <Col xs={24} lg={12}>
              <VssBreakdown profile={profile} />
            </Col>
            <Col xs={24} lg={12}>
              <HealthMetricsPanel metrics={profile.health_metrics} />
            </Col>
            <Col xs={24} lg={12}>
              <LifeEventsTimeline events={profile.life_events} />
            </Col>
            <Col xs={24} lg={12}>
              <MemoriesPanel memories={profile.memories} />
            </Col>
            <Col xs={24} lg={12}>
              <PredictionsPanel predictions={profile.predictions} />
            </Col>
            <Col xs={24} lg={12}>
              <AiInsightsPanel insights={profile.ai_insights} />
            </Col>
            <Col span={24}>
              <AgentHooksPanel
                profile={profile}
                onQuery={handleAgentQuery}
                loading={agentLoading}
              />
            </Col>
            {agentResult && (
              <Col span={24}>
                <Card className="cs-card" title={<Space><RobotOutlined /> Agent 分析结果</Space>}>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.6 }}>
                    {agentResult}
                  </pre>
                </Card>
              </Col>
            )}
          </Row>

          {/* Footer */}
          <div style={{ textAlign: "center", marginTop: 24, color: "#9ca3af", fontSize: 12 }}>
            <CrownOutlined style={{ marginRight: 6 }} />
            每辆车都有一份持续成长的数字生命档案 · 灵魂ID: {profile.soul_id}
          </div>
        </Spin>
      )}
    </div>
  );
}
