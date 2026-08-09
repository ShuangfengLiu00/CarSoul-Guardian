import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
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
} from "@ant-design/icons";
import dayjs from "dayjs";
import { vehicleService } from "@/services";
import { useCurrentVehicle } from "@/hooks";
import type {
  VehicleLifeRecord,
  VehicleHealthScore,
  SimulationResult,
  LifeEventItem,
  PredictionItem,
} from "@/services/types";

const { Title, Paragraph } = Typography;

// ============================================================
// Helpers
// ============================================================

const energyTypeText: Record<string, string> = {
  gasoline: "汽油",
  diesel: "柴油",
  electric: "电动",
  hybrid: "混动",
  plug_in_hybrid: "插电混动",
  fuel: "燃油",
};

const statusColor: Record<string, string> = {
  GOOD: "#10b981",
  WARNING: "#f59e0b",
  DANGER: "#ef4444",
  END_OF_LIFE: "#6b7280",
};

function healthStrokeColor(score?: number | null): ProgressProps["strokeColor"] {
  if (score == null) return "#d1d5db";
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

function riskTagColor(level: string): string {
  if (level === "high") return "red";
  if (level === "medium") return "orange";
  return "green";
}

function riskTagText(level: string): string {
  if (level === "high") return "高风险";
  if (level === "medium") return "中风险";
  return "低风险";
}

function fmtDateShort(s?: string | null): string {
  if (!s) return "-";
  const d = dayjs(s);
  return d.isValid() ? d.format("YYYY-MM-DD") : String(s);
}

function fmtDateTimeShort(s?: string | null): string {
  if (!s) return "-";
  const d = dayjs(s);
  return d.isValid() ? d.format("YYYY-MM-DD HH:mm") : String(s);
}

const eventTypeIcon: Record<string, ReactNode> = {
  purchase: <CarOutlined />,
  maintenance: <ToolOutlined />,
  repair: <ToolOutlined />,
  accident: <WarningOutlined />,
  inspection: <ExperimentOutlined />,
  insurance: <NodeIndexOutlined />,
  transfer: <NodeIndexOutlined />,
  registration: <NodeIndexOutlined />,
  custom: <ClockCircleOutlined />,
};

const eventTypeColor: Record<string, string> = {
  purchase: "green",
  maintenance: "blue",
  repair: "orange",
  accident: "red",
  inspection: "cyan",
  insurance: "purple",
  transfer: "geekblue",
  registration: "geekblue",
  custom: "gray",
};

const eventTypeText: Record<string, string> = {
  purchase: "购车",
  maintenance: "保养",
  repair: "维修",
  accident: "事故",
  inspection: "检查",
  insurance: "保险",
  transfer: "过户",
  registration: "登记",
  custom: "其他",
};

// ============================================================
// Sub-components
// ============================================================

interface HeroProps {
  record: VehicleLifeRecord;
}

function LifeHero({ record }: HeroProps) {
  const id = record.identity;
  const score = record.health_score ?? null;
  const scoreColor =
    score == null ? "#fff" : score >= 80 ? "#34d399" : score >= 60 ? "#fbbf24" : "#f87171";

  return (
    <div className="cs-life-hero">
      <div className="cs-life-hero__top">
        <div style={{ flex: "1 1 240px", minWidth: 240 }}>
          <div className="cs-life-hero__id">数字身份 · {id.digital_identity}</div>
          <div className="cs-life-hero__name">{id.name}</div>
          <div className="cs-life-hero__meta">
            {id.brand} {id.model} · {id.year}款 ·{" "}
            {energyTypeText[id.energy_type] ?? id.energy_type}
            {id.color ? ` · ${id.color}` : ""}
          </div>
          <div className="cs-life-hero__meta" style={{ marginTop: 4, fontFamily: "monospace" }}>
            VIN: {id.vin}
          </div>
        </div>
        <div style={{ flex: "0 0 auto" }}>
          <Tag
            color={statusColor[record.status] ?? "#6b7280"}
            style={{ borderRadius: 999, fontWeight: 700, border: "none", padding: "2px 14px" }}
          >
            {record.status_label}
          </Tag>
        </div>
      </div>

      <div className="cs-life-score" style={{ marginTop: 18 }}>
        <div
          className="cs-life-score__num"
          style={{ color: scoreColor }}
        >
          {score ?? "--"}
        </div>
        <div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.75)" }}>健康指数 VHS</div>
          {record.health_grade_label && (
            <span className="cs-life-score__grade">{record.health_grade_label}</span>
          )}
          {record.predicted_lifespan_label && (
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", marginTop: 8 }}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {record.predicted_lifespan_label}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface VitalsProps {
  record: VehicleLifeRecord;
}

function VitalsRow({ record }: VitalsProps) {
  const vitals = [
    {
      icon: <ClockCircleOutlined />,
      label: "车辆年龄",
      value: record.age_label,
      sub: record.age_years ? `${record.age_years.toFixed(1)} 年` : undefined,
    },
    {
      icon: <DashboardOutlined />,
      label: "累计里程",
      value: record.mileage_label,
      sub: `${record.mileage.toLocaleString()} km`,
    },
    {
      icon: <FireOutlined />,
      label: "今日温度",
      value: record.today_temperature != null ? `${record.today_temperature}℃` : "--",
      sub: "实时",
    },
    {
      icon: <ThunderboltOutlined />,
      label: "剩余油/电量",
      value:
        record.today_fuel_level != null ? `${record.today_fuel_level}%` : "--",
      sub: "实时",
    },
    {
      icon: <EnvironmentOutlined />,
      label: "当前位置",
      value:
        (record.today_location as { name?: string } | null)?.name ?? "--",
      sub: "实时定位",
    },
    {
      icon: <ClockCircleOutlined />,
      label: "预测剩余寿命",
      value:
        record.predicted_remaining_years != null
          ? `${record.predicted_remaining_years.toFixed(1)} 年`
          : "--",
      sub: record.predicted_lifespan_label,
    },
  ];

  return (
    <div className="cs-life-vitals">
      {vitals.map((v, i) => (
        <div className="cs-life-vital" key={i}>
          <div className="cs-life-vital__label">
            {v.icon}
            {v.label}
          </div>
          <div className="cs-life-vital__value">{v.value}</div>
          {v.sub && <div className="cs-life-vital__sub">{v.sub}</div>}
        </div>
      ))}
    </div>
  );
}

interface SubsysProps {
  record: VehicleLifeRecord;
}

function SubsystemHealth({ record }: SubsysProps) {
  const items = [
    { key: "engine", label: "发动机", value: record.engine_health, icon: <CarOutlined /> },
    { key: "battery", label: "电池", value: record.battery_health, icon: <ThunderboltOutlined /> },
    { key: "brake", label: "制动", value: record.brake_health, icon: <ToolOutlined /> },
    { key: "tire", label: "轮胎", value: record.tire_health, icon: <DashboardOutlined /> },
  ];

  return (
    <Card className="cs-card" title={<Space><HeartOutlined /> 子系统健康</Space>} style={{ height: "100%" }}>
      <div className="cs-life-subsys">
        {items.map((it) => (
          <div className="cs-life-subsys__row" key={it.key}>
            <span className="cs-life-subsys__name">
              {it.icon} {it.label}
            </span>
            <Progress
              className="cs-life-subsys__bar"
              percent={Math.round(it.value ?? 0)}
              size="small"
              strokeColor={healthStrokeColor(it.value)}
              format={() => ""}
            />
            <span
              className="cs-life-subsys__val"
              style={{ color: healthStrokeColor(it.value) as string }}
            >
              {it.value != null ? Math.round(it.value) : "--"}
            </span>
          </div>
        ))}
        {items.every((it) => it.value == null) && (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无子系统健康数据"
          />
        )}
      </div>
    </Card>
  );
}

interface VhsBreakdownProps {
  score: VehicleHealthScore | null;
  loading: boolean;
}

function VhsBreakdown({ score, loading }: VhsBreakdownProps) {
  if (loading) {
    return (
      <Card className="cs-card" title={<Space><DashboardOutlined /> 健康评分构成 (VHS)</Space>} style={{ height: "100%" }}>
        <Skeleton active paragraph={{ rows: 5 }} />
      </Card>
    );
  }

  if (!score) {
    return (
      <Card className="cs-card" title={<Space><DashboardOutlined /> 健康评分构成 (VHS)</Space>} style={{ height: "100%" }}>
        <div className="cs-life-empty">
          <DashboardOutlined style={{ fontSize: 36, marginBottom: 8 }} />
          <div>暂无评分数据</div>
        </div>
      </Card>
    );
  }

  const b = score.breakdown;
  const rows = [
    { label: "发动机", weight: "30%", val: b.engine, contrib: b.engine_contribution },
    { label: "电池", weight: "25%", val: b.battery, contrib: b.battery_contribution },
    { label: "底盘", weight: "15%", val: b.chassis, contrib: b.chassis_contribution },
    { label: "驾驶习惯", weight: "15%", val: b.driving, contrib: b.driving_contribution },
    { label: "维修记录", weight: "15%", val: b.maintenance, contrib: b.maintenance_contribution },
  ];

  return (
    <Card
      className="cs-card"
      title={<Space><DashboardOutlined /> 健康评分构成 (VHS)</Space>}
      style={{ height: "100%" }}
    >
      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 40, fontWeight: 800, color: healthStrokeColor(score.score) as string }}>
          {score.score}
        </div>
        <Tag color={score.grade === "risk" ? "red" : score.grade === "fair" ? "orange" : "green"} style={{ marginTop: 4 }}>
          {score.grade_label}
        </Tag>
      </div>
      <div className="cs-life-subsys">
        {rows.map((r) => (
          <div className="cs-life-subsys__row" key={r.label}>
            <Tooltip title={`权重 ${r.weight}`}>
              <span className="cs-life-subsys__name">{r.label}</span>
            </Tooltip>
            <Progress
              className="cs-life-subsys__bar"
              percent={Math.round(r.val)}
              size="small"
              strokeColor={healthStrokeColor(r.val)}
              format={() => ""}
            />
            <span
              className="cs-life-subsys__val"
              style={{ color: healthStrokeColor(r.val) as string }}
            >
              {Math.round(r.val)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

interface EventsProps {
  events: LifeEventItem[];
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
          <Tag
            color={eventTypeColor[ev.event_type] ?? "gray"}
            style={{ marginLeft: 8, fontSize: 11 }}
          >
            {eventTypeText[ev.event_type] ?? ev.event_type}
          </Tag>
        </div>
        <div style={{ fontSize: 12, color: "#9ca3af" }}>
          {fmtDateShort(ev.date)}
          {ev.mileage != null ? ` · ${ev.mileage.toLocaleString()} km` : ""}
          {ev.cost != null ? ` · ¥${ev.cost}` : ""}
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

interface PredProps {
  predictions: PredictionItem[];
}

function PredictionsPanel({ predictions }: PredProps) {
  if (!predictions || predictions.length === 0) {
    return (
      <Card className="cs-card" title={<Space><RobotOutlined /> AI 预测性维护</Space>} style={{ height: "100%" }}>
        <div className="cs-life-empty">
          <RobotOutlined style={{ fontSize: 36, marginBottom: 8 }} />
          <div>暂无预测数据</div>
          <div style={{ fontSize: 12, marginTop: 4 }}>
            运行模拟数据生成器后将产生预测
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="cs-card" title={<Space><RobotOutlined /> AI 预测性维护</Space>} style={{ height: "100%" }}>
      <div className="cs-life-pred">
        {predictions.map((p, i) => (
          <div className="cs-life-pred__item" key={i}>
            <div className="cs-life-pred__head">
              <span className="cs-life-pred__comp">{p.component}</span>
              <Tag color={riskTagColor(p.risk_level)}>
                {riskTagText(p.risk_level)}
              </Tag>
            </div>
            <div className="cs-life-pred__reason">{p.reason}</div>
            {p.current_health != null && (
              <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
                当前健康度: {Math.round(p.current_health)}
                {p.predicted_failure_date
                  ? ` · 预计失效: ${fmtDateShort(p.predicted_failure_date)}`
                  : ""}
              </div>
            )}
            {p.suggestion && (
              <div className="cs-life-pred__sugg">
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

interface SuggestProps {
  suggestions: string[];
}

function AiSuggestionsPanel({ suggestions }: SuggestProps) {
  return (
    <Card
      className="cs-card"
      title={
        <Space>
          <BulbOutlined style={{ color: "#f59e0b" }} />
          AI 建议
          <Tag color="blue" style={{ fontSize: 11 }}>
            TASK008 预览
          </Tag>
        </Space>
      }
    >
      {suggestions && suggestions.length > 0 ? (
        <ul className="cs-life-suggest">
          {suggestions.map((s, i) => (
            <li className="cs-life-suggest__item" key={i}>
              <BulbOutlined className="cs-life-suggest__icon" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="cs-life-empty">
          <BulbOutlined style={{ fontSize: 36, marginBottom: 8 }} />
          <div>暂无 AI 建议</div>
          <div style={{ fontSize: 12, marginTop: 4 }}>
            AI 车辆医生将在 TASK008 接入
          </div>
        </div>
      )}
    </Card>
  );
}

interface StatsProps {
  record: VehicleLifeRecord;
}

function StatsRow({ record }: StatsProps) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={12} md={8}>
        <Card className="cs-card">
          <Statistic
            title="总行程数"
            value={record.total_trips}
            suffix="次"
            prefix={<CarOutlined style={{ color: "#3b82f6" }} />}
          />
        </Card>
      </Col>
      <Col xs={12} md={8}>
        <Card className="cs-card">
          <Statistic
            title="累计维修费用"
            value={record.total_maintenance_cost}
            prefix="¥"
            precision={2}
            valueStyle={{ color: "#ef4444" }}
          />
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card className="cs-card">
          <Statistic
            title="故障记录"
            value={record.fault_count}
            suffix="次"
            prefix={<WarningOutlined style={{ color: "#f59e0b" }} />}
          />
          {record.active_fault_count > 0 && (
            <Tag color="red" style={{ marginTop: 8 }}>
              活跃故障 {record.active_fault_count}
            </Tag>
          )}
        </Card>
      </Col>
    </Row>
  );
}

// ============================================================
// Main page
// ============================================================

export default function VehicleLifeHome() {
  const { vehicle, loading: vehicleLoading, hasNoVehicle, refresh: refreshVehicle } = useCurrentVehicle();
  const [lifeRecord, setLifeRecord] = useState<VehicleLifeRecord | null>(null);
  const [healthScore, setHealthScore] = useState<VehicleHealthScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [scoreLoading, setScoreLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);

  // ---- Load life record + health score for current vehicle ----
  const loadLifeRecord = useCallback(async (id: number) => {
    setLoading(true);
    setScoreLoading(true);
    try {
      const [life, score] = await Promise.all([
        vehicleService.getLifeRecord(id),
        vehicleService.getHealthScore(id).catch(() => null),
      ]);
      setLifeRecord(life);
      setHealthScore(score);
    } catch {
      setLifeRecord(null);
      setHealthScore(null);
    } finally {
      setLoading(false);
      setScoreLoading(false);
    }
  }, []);

  useEffect(() => {
    if (vehicle != null) {
      loadLifeRecord(vehicle.id);
    } else {
      setLifeRecord(null);
      setHealthScore(null);
    }
  }, [vehicle, loadLifeRecord]);

  // ---- Quick simulator ----
  const handleQuickSimulate = async () => {
    if (vehicle == null) return;
    setSimulating(true);
    try {
      const result: SimulationResult = await vehicleService.simulateQuick(
        vehicle.id,
        { sensorPoints: 48, tripCount: 8, faultCount: 1, days: 7 },
      );
      message.success(
        `已生成 ${result.sensor_data_created} 条传感器数据、${result.trips_created} 条行程、${result.faults_created} 条故障`,
      );
      await loadLifeRecord(vehicle.id);
    } catch {
      /* handled by interceptor */
    } finally {
      setSimulating(false);
    }
  };

  const vehicleName = useMemo(() => {
    if (!vehicle) return "本车";
    return vehicle.nickname
      ? `${vehicle.nickname} (${vehicle.brand} ${vehicle.model})`
      : `${vehicle.brand} ${vehicle.model}`;
  }, [vehicle]);

  return (
    <div>
      {/* 本页数据全部来自 vehicleService 真实接口（getLifeRecord / getHealthScore），
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
        <Title level={4} style={{ margin: 0 }}>
          <CarOutlined style={{ marginRight: 8, color: "#3b82f6" }} />
          {vehicleName}
        </Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => vehicle && loadLifeRecord(vehicle.id)}
            disabled={vehicle == null}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={simulating}
            onClick={handleQuickSimulate}
            disabled={vehicle == null}
          >
            生成模拟数据
          </Button>
        </Space>
      </div>

      {/* ---- Body ---- */}
      {vehicleLoading && (
        <Card className="cs-card">
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      )}

      {hasNoVehicle && !vehicleLoading && (
        <Card className="cs-card">
          <Empty
            image={<CarOutlined style={{ fontSize: 56, color: "#9ca3af" }} />}
            description="本车数据尚未就绪"
          >
            <Paragraph type="secondary" style={{ textAlign: "center", marginBottom: 16 }}>
              系统正在初始化本车数字生命档案，请稍后重试。
            </Paragraph>
            <div style={{ textAlign: "center" }}>
              <Button icon={<ReloadOutlined />} onClick={refreshVehicle}>
                重新检测
              </Button>
            </div>
          </Empty>
        </Card>
      )}

      {vehicle && loading && (
        <Card className="cs-card">
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      )}

      {vehicle && !loading && lifeRecord && (
        <Spin spinning={false}>
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <LifeHero record={lifeRecord} />
            </Col>
            <Col span={24}>
              <VitalsRow record={lifeRecord} />
            </Col>
            <Col span={24}>
              <StatsRow record={lifeRecord} />
            </Col>
            <Col xs={24} lg={12}>
              <SubsystemHealth record={lifeRecord} />
            </Col>
            <Col xs={24} lg={12}>
              <VhsBreakdown score={healthScore} loading={scoreLoading} />
            </Col>
            <Col xs={24} lg={12}>
              <LifeEventsTimeline events={lifeRecord.life_events} />
            </Col>
            <Col xs={24} lg={12}>
              <PredictionsPanel predictions={lifeRecord.predictions} />
            </Col>
            <Col span={24}>
              <AiSuggestionsPanel suggestions={lifeRecord.ai_suggestions} />
            </Col>
          </Row>

          {/* Footer hint */}
          <div style={{ textAlign: "center", marginTop: 24, color: "#9ca3af", fontSize: 12 }}>
            <RobotOutlined style={{ marginRight: 6 }} />
            AI 车辆医生与多智能体车辆专家系统将在 TASK008 接入 ·{" "}
            最后更新: {fmtDateTimeShort(vehicle.updated_at)}
          </div>
        </Spin>
      )}
    </div>
  );
}
