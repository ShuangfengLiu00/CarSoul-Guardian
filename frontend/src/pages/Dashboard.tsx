import { useEffect, useMemo, useState } from "react";
import {
  Card,
  Col,
  Row,
  Statistic,
  Tag,
  List,
  Typography,
  Progress,
  Skeleton,
  Space,
  Badge,
  Empty,
} from "antd";
import {
  HeartOutlined,
  RobotOutlined,
  CarOutlined,
  AlertOutlined,
  ThunderboltOutlined,
  FireOutlined,
  DashboardOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import {
  LineChart,
  Line,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";
import { healthService, vehicleService } from "@/services";
import { useCurrentVehicle } from "@/hooks";
import type { HealthOverview, VehicleArchive, Alert } from "@/services/types";
import { DEMO_ARCHIVE } from "@/services/demoData";
import { CriticalAlertOverlay, DemoBadge } from "@/components";
import type { CriticalAlert } from "@/components";

const { Title, Text, Paragraph } = Typography;

const levelColor: Record<string, string> = {
  info: "#3b82f6",
  warning: "#f59e0b",
  critical: "#ef4444",
};

const levelText: Record<string, string> = {
  info: "提示",
  warning: "警告",
  critical: "严重",
};

function fmtTime(s?: string): string {
  if (!s) return "";
  const d = new Date(s);
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function Dashboard() {
  const { vehicle } = useCurrentVehicle();
  const [archive, setArchive] = useState<VehicleArchive | null>(null);
  const [overview, setOverview] = useState<HealthOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingDemo, setUsingDemo] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      // 演示开关：URL 带 ?demo=1 时强制使用含 critical 告警的演示数据
      const forceDemo = new URLSearchParams(window.location.search).get("demo") === "1";
      if (forceDemo) {
        setArchive(DEMO_ARCHIVE);
        setUsingDemo(true);
        setLoading(false);
        return;
      }
      try {
        // 不传 vehicleId：Guardian 的车辆表主键（id=1001）与 carModel 的
        // vehicle_id（如 CS001）是两套命名空间，前端目前没有映射关系；交给后端用
        // CARSOUL_WORLD_DEFAULT_VEHICLE_ID 决定查哪辆车。绝不能用 Guardian 数字主键
        // 冒充 carModel 车辆 id —— 那会命中 carModel 404 被误报成"服务不可达"。
        const h = await healthService.overview().catch(() => null);
        if (!alive) return;
        setOverview(h);
        // 加载本车的完整档案用于可视化
        if (vehicle) {
          try {
            const ar = await vehicleService.getArchive(vehicle.id);
            if (!alive) return;
            if (ar && (ar.health_history?.length || ar.alerts?.length || ar.driving_behaviors?.length)) {
              setArchive(ar);
              setUsingDemo(false);
            } else {
              setArchive(DEMO_ARCHIVE);
              setUsingDemo(true);
            }
          } catch {
            setArchive(DEMO_ARCHIVE);
            setUsingDemo(true);
          }
        } else {
          setArchive(DEMO_ARCHIVE);
          setUsingDemo(true);
        }
      } catch {
        if (!alive) return;
        setArchive(DEMO_ARCHIVE);
        setUsingDemo(true);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [vehicle]);

  // 合并出 critical 告警列表（用于霸屏闪烁）
  const criticalAlerts: CriticalAlert[] = useMemo(() => {
    const alerts: Alert[] = archive?.alerts ?? [];
    const activeCritical = alerts.filter(
      (a) => a.level === "critical" && a.status === "active",
    );
    return activeCritical.map((a) => ({
      id: a.id,
      level: "critical" as const,
      title: a.title,
      detail: a.detail,
      recommendation: a.recommendation,
      triggered_at: a.triggered_at,
      category: a.category,
    }));
  }, [archive]);

  // 健康分只认 carModel 真值（overview.health_score）。**绝不**回落到 demo 档案的
  // health_score（DEMO_ARCHIVE=92）—— 那正是历史版本"假 92 分"的来路：carModel 不可达
  // 时 overview.health_score 为 null，若再 `?? archive?.health_score` 就会把演示 92 透出来。
  // 这里置空，由卡片如实渲染"暂无数据"。
  const score = overview?.health_score ?? null;
  const scoreAvailable = score !== null && score !== undefined;
  const scoreColor = useMemo(() => {
    if (score === null || score === undefined) return "#8c8c8c";
    if (score >= 85) return "#10b981";
    if (score >= 60) return "#f59e0b";
    return "#ef4444";
  }, [score]);

  // 健康趋势数据
  const healthTrend = useMemo(() => {
    const hist = archive?.health_history ?? [];
    return hist.map((h) => ({
      time: new Date(h.snapshot_time).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
      健康指数: h.health_score,
      电池: h.battery_score ?? 0,
      制动: h.brake_score ?? 0,
    }));
  }, [archive]);

  // 子系统雷达数据
  const radarData = useMemo(() => {
    const h = archive?.latest_health;
    if (!h) return [];
    return [
      { subject: "发动机", score: h.engine_score ?? 0, full: 100 },
      { subject: "制动", score: h.brake_score ?? 0, full: 100 },
      { subject: "轮胎", score: h.tire_score ?? 0, full: 100 },
      { subject: "电池", score: h.battery_score ?? 0, full: 100 },
      { subject: "车身", score: h.body_score ?? 0, full: 100 },
      { subject: "电子", score: h.electronics_score ?? 0, full: 100 },
    ];
  }, [archive]);

  // 告警分布
  const alertDist = useMemo(() => {
    const alerts = archive?.alerts ?? [];
    const c = alerts.filter((a) => a.level === "critical").length;
    const w = alerts.filter((a) => a.level === "warning").length;
    const i = alerts.filter((a) => a.level === "info").length;
    return [
      { name: "严重", value: c, color: "#ef4444" },
      { name: "警告", value: w, color: "#f59e0b" },
      { name: "提示", value: i, color: "#3b82f6" },
    ].filter((d) => d.value > 0);
  }, [archive]);

  // 驾驶行为：急驾驶事件柱状图
  const drivingHarsh = useMemo(() => {
    const beh = archive?.driving_behaviors ?? [];
    return beh.slice(-10).map((b) => ({
      date: b.record_date.slice(5),
      急加速: b.harsh_acceleration_count,
      急刹车: b.harsh_braking_count,
      急转弯: b.sharp_turn_count,
      超速: b.overspeed_count,
    }));
  }, [archive]);

  // 驾驶评分趋势
  const drivingScore = useMemo(() => {
    const beh = archive?.driving_behaviors ?? [];
    return beh.slice(-14).map((b) => ({
      date: b.record_date.slice(5),
      安全: b.safety_score ?? 0,
      能耗: b.eco_score ?? 0,
    }));
  }, [archive]);

  if (loading) return <Skeleton active paragraph={{ rows: 12 }} />;

  const recentAlerts = overview?.recent_alerts ?? [];
  const alertsForList = archive?.alerts ?? [];

  // AI 守护状态的唯一呈现来源。
  // 诚实降级原则：只有后端明确报 "active" 才显示运行中；"degraded" 必须
  // 可见地标成降级；拿不到值一律 unknown/待机，绝不默认变绿。
  // usingDemo 不再参与判定——演示数据由右上角 DemoBadge 单独标注，
  // 不允许把降级洗成"运行中"。
  const rawAgentStatus = overview?.agent_status ?? "unknown";
  const agentPresentation: {
    label: string;
    color: string;
    badgeStatus: "success" | "warning" | "default";
    badgeText: string;
    tagColor: string;
  } =
    rawAgentStatus === "active"
      ? {
          label: "运行中",
          color: "#3b82f6",
          badgeStatus: "success",
          badgeText: "守护引擎在线",
          tagColor: "green",
        }
      : rawAgentStatus === "degraded"
        ? {
            label: "降级运行",
            color: "#f59e0b",
            badgeStatus: "warning",
            badgeText: "降级模式（未经大模型）",
            tagColor: "orange",
          }
        : {
            label: "待机",
            color: "#8c8c8c",
            badgeStatus: "default",
            badgeText: "守护引擎状态未知",
            tagColor: "default",
          };

  return (
    <div className="cs-dashboard">
      {/* 演示模式固定角标（右上角） */}
      {usingDemo && <DemoBadge />}

      {/* 霸屏闪烁警示（critical 告警时触发） */}
      <CriticalAlertOverlay alerts={criticalAlerts} />

      {/* 标题区 */}
      <div className="cs-dashboard__header">
        <div>
          <Title level={3} style={{ margin: 0 }}>
            CarSoul Guardian
          </Title>
          <Paragraph type="secondary" style={{ margin: 0, marginTop: 2 }}>
            AI 汽车私人管家 · 车辆数字生命档案 · 主动式汽车健康管理
          </Paragraph>
        </div>
        <Space>
          <DemoBadge inline />
          <Tag color={agentPresentation.tagColor} style={{ borderRadius: 12, padding: "2px 12px" }}>
            <RobotOutlined /> {agentPresentation.label}
          </Tag>
        </Space>
      </div>

      {/* 顶部统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="车辆健康指数"
              value={scoreAvailable ? score : "暂无数据"}
              suffix={scoreAvailable ? "/100" : undefined}
              prefix={<HeartOutlined style={{ color: scoreColor }} />}
              valueStyle={{ color: scoreColor, fontSize: 32 }}
            />
            {scoreAvailable ? (
              <>
                <Progress percent={score ?? 0} showInfo={false} strokeColor={scoreColor} size="small" style={{ marginTop: 8 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {[overview?.data_source, overview?.as_of ? `观测 ${fmtTime(overview.as_of)}` : null]
                    .filter(Boolean)
                    .join(" · ") || "数据来源：carModel"}
                </Text>
              </>
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {overview?.data_status?.detail ?? "暂无真实车况数据（carModel 不可达或未指定车辆）"}
              </Text>
            )}
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="AI 守护状态"
              value={agentPresentation.label}
              prefix={<RobotOutlined style={{ color: agentPresentation.color }} />}
              valueStyle={{ color: agentPresentation.color, fontSize: 28 }}
            />
            <Badge
              status={agentPresentation.badgeStatus}
              text={agentPresentation.badgeText}
              style={{ marginTop: 6 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="累计里程"
              value={archive?.vehicle.mileage ?? 0}
              suffix="km"
              prefix={<CarOutlined style={{ color: "#6366f1" }} />}
              valueStyle={{ fontSize: 32 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {archive?.vehicle.brand} {archive?.vehicle.model}
            </Text>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card cs-stat-card--alert">
            <Statistic
              title="活跃告警"
              value={archive?.active_alert_count ?? 0}
              prefix={<AlertOutlined style={{ color: "#ef4444" }} />}
              valueStyle={{ color: "#ef4444", fontSize: 32 }}
            />
            <Badge status="error" text={`${criticalAlerts.length} 条严重`} style={{ marginTop: 6 }} />
          </Card>
        </Col>
      </Row>

      {/* 第一行图表：健康趋势 + 子系统雷达 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={15}>
          <Card
            className="cs-card"
            title={<Space><ThunderboltOutlined /> 健康指数趋势</Space>}
            extra={<Tag color={scoreColor}>{scoreAvailable ? score : "暂无"}</Tag>}
          >
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={healthTrend} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <defs>
                  <linearGradient id="healthGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={scoreColor} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={scoreColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <RTooltip />
                <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "警戒线", fontSize: 10, fill: "#f59e0b" }} />
                <Area
                  type="monotone"
                  dataKey="健康指数"
                  stroke={scoreColor}
                  strokeWidth={3}
                  fill="url(#healthGrad)"
                  dot={{ r: 3, fill: scoreColor }}
                  activeDot={{ r: 6 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card className="cs-card" title={<Space><DashboardOutlined /> 子系统健康</Space>}>
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData} outerRadius="75%">
                <PolarGrid stroke="#eef0f4" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12, fill: "#6b7280" }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                <RTooltip />
                <Radar name="得分" dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* 第二行图表：告警分布 + 驾驶评分趋势 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={8}>
          <Card className="cs-card" title={<Space><AlertOutlined /> 告警等级分布</Space>}>
            {alertDist.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无告警" style={{ padding: "40px 0" }} />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={alertDist}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    label={(entry) => `${entry.name} ${entry.value}`}
                    labelLine={false}
                  >
                    {alertDist.map((d) => (
                      <Cell key={d.name} fill={d.color} />
                    ))}
                  </Pie>
                  <RTooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card className="cs-card" title={<Space><SafetyCertificateOutlined /> 驾驶评分趋势（近14天）</Space>}>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={drivingScore} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <RTooltip />
                <Line type="monotone" dataKey="安全" stroke="#10b981" strokeWidth={2.5} dot={{ r: 2 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="能耗" stroke="#8b5cf6" strokeWidth={2.5} dot={{ r: 2 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* 第三行：急驾驶事件柱状图 + 最近告警列表 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card className="cs-card" title={<Space><FireOutlined /> 急驾驶事件（近10天）</Space>}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={drivingHarsh} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <RTooltip />
                <Bar dataKey="急加速" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} />
                <Bar dataKey="急刹车" stackId="a" fill="#ef4444" radius={[0, 0, 0, 0]} />
                <Bar dataKey="急转弯" stackId="a" fill="#8b5cf6" radius={[0, 0, 0, 0]} />
                <Bar dataKey="超速" stackId="a" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            className="cs-card"
            title={<Space><AlertOutlined /> 最近告警</Space>}
            extra={<Tag color={agentPresentation.tagColor}>{rawAgentStatus}</Tag>}
          >
            <List
              dataSource={alertsForList.length ? alertsForList.slice(0, 6) : recentAlerts.map((a, i) => ({ ...a, id: i, vehicle_id: 0, alert_type: "", status: "active", triggered_at: new Date().toISOString() }))}
              locale={{ emptyText: "暂无提醒" }}
              renderItem={(item: any) => (
                <List.Item style={{ paddingLeft: 0, paddingRight: 0 }}>
                  <List.Item.Meta
                    avatar={
                      <Tag color={levelColor[item.level]} style={{ minWidth: 48, textAlign: "center" }}>
                        {levelText[item.level] ?? item.level}
                      </Tag>
                    }
                    title={
                      <Space>
                        <Text strong>{item.title}</Text>
                        {item.level === "critical" && <Badge status="error" />}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={0}>
                        {item.detail && <Text type="secondary" style={{ fontSize: 13 }}>{item.detail}</Text>}
                        {item.triggered_at && <Text type="secondary" style={{ fontSize: 11 }}>{fmtTime(item.triggered_at)}</Text>}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
