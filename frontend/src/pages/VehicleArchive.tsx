import { useEffect, useMemo, useState, useCallback } from "react";
import {
  Card,
  Tabs,
  Table,
  Timeline,
  Progress,
  Tag,
  Statistic,
  Space,
  Button,
  Descriptions,
  Badge,
  Empty,
  Row,
  Col,
  Typography,
  Skeleton,
  Alert as AntAlert,
  List,
  Tooltip,
  Modal,
  Input,
  Form,
  Select,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import {
  ReloadOutlined,
  CarOutlined,
  HeartOutlined,
  AlertOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  SolutionOutlined,
  ApartmentOutlined,
  CheckOutlined,
  CloseOutlined,
  SyncOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  FileTextOutlined,
  ForwardOutlined,
  MessageOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { vehicleService } from "@/services";
import { useCurrentVehicle } from "@/hooks";
import DemoBadge from "@/components/DemoBadge";
import type {
  VehicleArchive,
  LifecycleEvent,
  HealthItem,
  MaintenanceRecord,
  MaintenanceSchedule,
  DrivingBehavior,
  Alert as AlertType,
  OwnershipRecord,
  ServiceOrder,
  ServiceOrderCreate,
  ServiceOrderFeedback,
} from "@/services/types";

const { Title, Text, Paragraph } = Typography;

// ============================================================
// Color / text maps
// ============================================================

function healthColor(score: number | null | undefined): string {
  if (score == null) return "#9ca3af";
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

function healthStatusText(score: number | null | undefined): string {
  if (score == null) return "无数据";
  if (score >= 80) return "良好";
  if (score >= 60) return "注意";
  return "风险";
}

const alertLevelColor: Record<string, string> = {
  critical: "red",
  warning: "orange",
  info: "blue",
};

const alertLevelText: Record<string, string> = {
  critical: "严重",
  warning: "警告",
  info: "提示",
};

const alertStatusText: Record<string, string> = {
  active: "活跃",
  acknowledged: "已确认",
  resolved: "已解决",
};

const alertStatusBadge: Record<string, "error" | "warning" | "success" | "processing" | "default"> = {
  active: "error",
  acknowledged: "warning",
  resolved: "success",
};

const scheduleStatusColor: Record<string, string> = {
  overdue: "red",
  due: "orange",
  pending: "green",
};

const scheduleStatusText: Record<string, string> = {
  overdue: "已逾期",
  due: "即将到期",
  pending: "正常",
};

const eventTypeColor: Record<string, string> = {
  purchase: "green",
  maintenance: "blue",
  repair: "orange",
  accident: "red",
  insurance: "purple",
  inspection: "cyan",
  transfer: "geekblue",
  other: "gray",
};

const eventTypeText: Record<string, string> = {
  purchase: "购车",
  maintenance: "保养",
  repair: "维修",
  accident: "事故",
  insurance: "保险",
  inspection: "年检",
  transfer: "过户",
  other: "其他",
};

const healthLevelColor: Record<string, string> = {
  good: "green",
  warning: "orange",
  critical: "red",
};

const healthLevelText: Record<string, string> = {
  good: "良好",
  warning: "注意",
  critical: "风险",
};

const fuelTypeText: Record<string, string> = {
  gasoline: "汽油",
  diesel: "柴油",
  electric: "电动",
  hybrid: "混动",
  plug_in_hybrid: "插电混动",
};

const vehicleStatusText: Record<string, string> = {
  active: "使用中",
  idle: "闲置",
  sold: "已出售",
  scrapped: "已报废",
};

const vehicleStatusColor: Record<string, string> = {
  active: "green",
  idle: "default",
  sold: "orange",
  scrapped: "red",
};

const maintenanceTypeText: Record<string, string> = {
  routine: "常规保养",
  major: "大保养",
  minor: "小保养",
  repair: "维修",
  inspection: "检查",
  other: "其他",
};

const transferTypeText: Record<string, string> = {
  purchase: "购买",
  sale: "出售",
  transfer: "转让",
  inheritance: "继承",
  gift: "赠与",
  other: "其他",
};

const priorityText: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const priorityColor: Record<string, string> = {
  high: "red",
  medium: "orange",
  low: "green",
};

const twinSyncColor: Record<string, string> = {
  synced: "green",
  syncing: "blue",
  error: "red",
  pending: "orange",
};

const twinSyncText: Record<string, string> = {
  synced: "已同步",
  syncing: "同步中",
  error: "同步异常",
  pending: "待同步",
};

// ============================================================
// Format helpers
// ============================================================

function fmtDate(s?: string | null): string {
  if (!s) return "-";
  const d = dayjs(s);
  return d.isValid() ? d.format("YYYY-MM-DD") : String(s);
}

function fmtDateTime(s?: string | null): string {
  if (!s) return "-";
  const d = dayjs(s);
  return d.isValid() ? d.format("YYYY-MM-DD HH:mm") : String(s);
}

function fmtMileage(m?: number | null): string {
  if (m == null) return "-";
  return `${m.toLocaleString()} km`;
}

function fmtCost(c?: number | null): string {
  if (c == null) return "-";
  return `¥ ${c.toLocaleString()}`;
}

function fmtDuration(sec?: number | null): string {
  if (sec == null) return "-";
  const h = Math.floor(sec / 3600);
  const m = Math.round((sec % 3600) / 60);
  if (h > 0) return `${h} 小时 ${m} 分钟`;
  return `${m} 分钟`;
}

function fmtNumber(n?: number | null, suffix = ""): string {
  if (n == null) return "-";
  return `${n.toLocaleString()}${suffix}`;
}

function renderUnknownValue(v: unknown): string {
  if (v == null) return "-";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

// ============================================================
// Sub-components
// ============================================================

interface TabProps {
  archive: VehicleArchive;
}

// ---- Health Report Tab ----
function HealthReportTab({ archive }: TabProps) {
  const health = archive.latest_health;
  const score = archive.health_score;

  const subsystems = useMemo(() => {
    if (!health) return [];
    return [
      { key: "engine", label: "发动机", score: health.engine_score },
      { key: "brake", label: "制动", score: health.brake_score },
      { key: "tire", label: "轮胎", score: health.tire_score },
      { key: "battery", label: "电池", score: health.battery_score },
      { key: "body", label: "车身", score: health.body_score },
      { key: "electronics", label: "电子", score: health.electronics_score },
    ];
  }, [health]);

  const riskItems = useMemo(() => {
    if (!health?.items) return [];
    return health.items.filter(
      (item) => item.level === "warning" || item.level === "critical",
    );
  }, [health]);

  if (!health) {
    return (
      <Empty
        image={<HeartOutlined style={{ fontSize: 48, color: "#9ca3af" }} />}
        description="暂无健康报告数据"
      />
    );
  }

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="cs-card" title={<Space><HeartOutlined /> 综合健康分数</Space>}>
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <Progress
                type="dashboard"
                percent={score ?? 0}
                strokeColor={healthColor(score)}
                format={(p) => (
                  <span style={{ color: healthColor(score), fontSize: 28, fontWeight: 700 }}>
                    {p}
                  </span>
                )}
                size={180}
              />
              <div style={{ marginTop: 8 }}>
                <Tag
                  color={
                    score == null
                      ? "default"
                      : score >= 80
                        ? "success"
                        : score >= 60
                          ? "warning"
                          : "error"
                  }
                  style={{ fontSize: 14, padding: "2px 12px" }}
                >
                  {healthStatusText(score)}
                </Tag>
              </div>
              {health.summary && (
                <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
                  {health.summary}
                </Paragraph>
              )}
              <Text type="secondary" style={{ fontSize: 12 }}>
                快照时间: {fmtDateTime(health.snapshot_time)} · 里程: {fmtMileage(health.mileage)}
              </Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} md={16}>
          <Card className="cs-card" title={<Space><DashboardOutlined /> 各子系统分数</Space>}>
            <Row gutter={[16, 24]}>
              {subsystems.map((s) => (
                <Col xs={12} md={8} key={s.key}>
                  <div style={{ textAlign: "center" }}>
                    <Progress
                      type="circle"
                      percent={s.score ?? 0}
                      size={100}
                      strokeColor={healthColor(s.score)}
                      format={(p) => (
                        <span style={{ color: healthColor(s.score), fontSize: 18, fontWeight: 600 }}>
                          {s.score == null ? "-" : p}
                        </span>
                      )}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Text strong>{s.label}</Text>
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>

      <Card
        className="cs-card"
        title={<Space><AlertOutlined /> 风险项列表</Space>}
        style={{ marginTop: 16 }}
      >
        {riskItems.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无风险项，车辆各系统状态良好"
          />
        ) : (
          <List
            itemLayout="vertical"
            dataSource={riskItems}
            renderItem={(item: HealthItem) => (
              <List.Item key={item.id}>
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={healthLevelColor[item.level] || "default"}>
                        {healthLevelText[item.level] || item.level}
                      </Tag>
                      <Text strong>{item.item_name}</Text>
                      <Text type="secondary">{item.category}</Text>
                      {item.score != null && (
                        <Tag color={healthColor(item.score) === "#10b981" ? "success" : healthColor(item.score) === "#f59e0b" ? "warning" : "error"}>
                          分数: {item.score}
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      {item.detail && <Paragraph style={{ marginBottom: 4 }}>{item.detail}</Paragraph>}
                      {item.recommendation && (
                        <Space>
                          <Tooltip title="建议">
                            <Tag icon={<CheckOutlined />} color="blue">建议</Tag>
                          </Tooltip>
                          <Text type="secondary">{item.recommendation}</Text>
                        </Space>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}

// ---- Lifecycle Tab ----
function LifecycleTab({ archive }: TabProps) {
  const events = useMemo(() => {
    return [...archive.lifecycle_events].sort(
      (a, b) => dayjs(b.event_date).valueOf() - dayjs(a.event_date).valueOf(),
    );
  }, [archive.lifecycle_events]);

  if (events.length === 0) {
    return (
      <Empty
        image={<ClockCircleOutlined style={{ fontSize: 48, color: "#9ca3af" }} />}
        description="暂无生命周期事件"
      />
    );
  }

  return (
    <Card className="cs-card" title={<Space><ClockCircleOutlined /> 生命周期时间线</Space>}>
      <Timeline
        items={events.map((event: LifecycleEvent) => ({
          color: eventTypeColor[event.event_type] || "gray",
          children: (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <Space>
                  <Tag color={eventTypeColor[event.event_type] || "default"}>
                    {eventTypeText[event.event_type] || event.event_type}
                  </Tag>
                  <Text strong>{event.title}</Text>
                </Space>
                <Text type="secondary">{fmtDate(event.event_date)}</Text>
              </div>
              {event.description && (
                <Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 6 }}>
                  {event.description}
                </Paragraph>
              )}
              <Space wrap size={[4, 4]}>
                {event.mileage != null && <Tag>里程: {fmtMileage(event.mileage)}</Tag>}
                {event.cost != null && <Tag color="volcano">费用: {fmtCost(event.cost)}</Tag>}
                {event.location && (
                  <Tag icon={<EnvironmentOutlined />}>{event.location}</Tag>
                )}
                {event.severity && <Tag color="red">严重度: {event.severity}</Tag>}
              </Space>
            </div>
          ),
        }))}
      />
    </Card>
  );
}

// ---- Maintenance Tab ----
function MaintenanceTab({ archive }: TabProps) {
  const recordColumns: TableColumnsType<MaintenanceRecord> = [
    {
      title: "日期",
      dataIndex: "maintenance_date",
      key: "maintenance_date",
      width: 120,
      render: (v: string) => fmtDate(v),
      sorter: (a, b) => dayjs(a.maintenance_date).valueOf() - dayjs(b.maintenance_date).valueOf(),
      defaultSortOrder: "descend",
    },
    {
      title: "类型",
      dataIndex: "maintenance_type",
      key: "maintenance_type",
      width: 100,
      render: (v: string) => (
        <Tag>{maintenanceTypeText[v] || v}</Tag>
      ),
    },
    {
      title: "类别",
      dataIndex: "category",
      key: "category",
      width: 100,
    },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: "里程",
      dataIndex: "mileage",
      key: "mileage",
      width: 110,
      render: (v: number) => fmtMileage(v),
    },
    {
      title: "费用",
      dataIndex: "cost",
      key: "cost",
      width: 110,
      render: (v: number) => fmtCost(v),
      sorter: (a, b) => (a.cost ?? 0) - (b.cost ?? 0),
    },
    {
      title: "服务商",
      dataIndex: "service_provider",
      key: "service_provider",
      width: 140,
      ellipsis: true,
      render: (v: string) => v || "-",
    },
  ];

  const scheduleColumns: TableColumnsType<MaintenanceSchedule> = [
    {
      title: "项目",
      dataIndex: "item_name",
      key: "item_name",
      width: 140,
    },
    {
      title: "类别",
      dataIndex: "category",
      key: "category",
      width: 100,
    },
    {
      title: "间隔",
      key: "interval",
      width: 140,
      render: (_: unknown, r: MaintenanceSchedule) => {
        const parts: string[] = [];
        if (r.interval_km) parts.push(`${r.interval_km.toLocaleString()} km`);
        if (r.interval_days) parts.push(`${r.interval_days} 天`);
        return parts.length ? parts.join(" / ") : "-";
      },
    },
    {
      title: "下次到期",
      key: "next_due",
      width: 180,
      render: (_: unknown, r: MaintenanceSchedule) => (
        <Space direction="vertical" size={0}>
          {r.next_due_date && <Text>{fmtDate(r.next_due_date)}</Text>}
          {r.next_due_km != null && <Text type="secondary">{fmtMileage(r.next_due_km)}</Text>}
          {!r.next_due_date && r.next_due_km == null && <Text type="secondary">-</Text>}
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string) => (
        <Tag color={scheduleStatusColor[v] || "default"}>
          {scheduleStatusText[v] || v}
        </Tag>
      ),
      sorter: (a, b) => {
        const order: Record<string, number> = { overdue: 0, due: 1, pending: 2 };
        return (order[a.status] ?? 3) - (order[b.status] ?? 3);
      },
      defaultSortOrder: "ascend",
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 90,
      render: (v: string) => (
        <Tag color={priorityColor[v] || "default"}>{priorityText[v] || v}</Tag>
      ),
    },
    {
      title: "备注",
      dataIndex: "notes",
      key: "notes",
      ellipsis: true,
      render: (v: string) => v || "-",
    },
  ];

  return (
    <div>
      <Card
        className="cs-card"
        title={<Space><ToolOutlined /> 保养记录</Space>}
        style={{ marginBottom: 16 }}
      >
        <Table
          rowKey="id"
          size="middle"
          columns={recordColumns}
          dataSource={archive.maintenance_records}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          locale={{ emptyText: "暂无保养记录" }}
          scroll={{ x: 800 }}
        />
      </Card>

      <Card className="cs-card" title={<Space><ClockCircleOutlined /> 保养计划</Space>}>
        <Table
          rowKey="id"
          size="middle"
          columns={scheduleColumns}
          dataSource={archive.maintenance_schedules}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          locale={{ emptyText: "暂无保养计划" }}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  );
}

// ---- Driving Behavior Tab ----
function DrivingBehaviorTab({ archive }: TabProps) {
  const behaviors = archive.driving_behaviors;

  const summary = useMemo(() => {
    if (behaviors.length === 0) return null;
    const totalTrips = behaviors.reduce((s, b) => s + b.trip_count, 0);
    const totalDistance = behaviors.reduce((s, b) => s + b.total_distance, 0);
    const totalDuration = behaviors.reduce((s, b) => s + b.total_duration, 0);
    const safetyScores = behaviors
      .map((b) => b.safety_score)
      .filter((v): v is number => v != null);
    const ecoScores = behaviors
      .map((b) => b.eco_score)
      .filter((v): v is number => v != null);
    const totalHarsh = behaviors.reduce(
      (s, b) =>
        s +
        b.harsh_acceleration_count +
        b.harsh_braking_count +
        b.sharp_turn_count +
        b.overspeed_count,
      0,
    );
    const totalFuel = behaviors.reduce((s, b) => s + (b.fuel_consumption ?? 0), 0);
    return {
      totalTrips,
      totalDistance,
      totalDuration,
      avgSafety: safetyScores.length
        ? safetyScores.reduce((a, b) => a + b, 0) / safetyScores.length
        : null,
      avgEco: ecoScores.length
        ? ecoScores.reduce((a, b) => a + b, 0) / ecoScores.length
        : null,
      totalHarsh,
      totalFuel,
      days: behaviors.length,
    };
  }, [behaviors]);

  const columns: TableColumnsType<DrivingBehavior> = [
    {
      title: "日期",
      dataIndex: "record_date",
      key: "record_date",
      width: 120,
      render: (v: string) => fmtDate(v),
      sorter: (a, b) => dayjs(a.record_date).valueOf() - dayjs(b.record_date).valueOf(),
      defaultSortOrder: "descend",
    },
    {
      title: "行程数",
      dataIndex: "trip_count",
      key: "trip_count",
      width: 80,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: "距离",
      dataIndex: "total_distance",
      key: "total_distance",
      width: 110,
      render: (v: number) => fmtNumber(v, " km"),
    },
    {
      title: "时长",
      dataIndex: "total_duration",
      key: "total_duration",
      width: 120,
      render: (v: number) => fmtDuration(v),
    },
    {
      title: "平均速度",
      dataIndex: "avg_speed",
      key: "avg_speed",
      width: 100,
      render: (v: number) => (v != null ? `${v.toFixed(1)} km/h` : "-"),
    },
    {
      title: "安全评分",
      dataIndex: "safety_score",
      key: "safety_score",
      width: 100,
      render: (v: number) =>
        v != null ? (
          <Tag color={healthColor(v) === "#10b981" ? "success" : healthColor(v) === "#f59e0b" ? "warning" : "error"}>
            {v.toFixed(1)}
          </Tag>
        ) : (
          "-"
        ),
      sorter: (a, b) => (a.safety_score ?? 0) - (b.safety_score ?? 0),
    },
    {
      title: "能耗评分",
      dataIndex: "eco_score",
      key: "eco_score",
      width: 100,
      render: (v: number) =>
        v != null ? (
          <Tag color={healthColor(v) === "#10b981" ? "success" : healthColor(v) === "#f59e0b" ? "warning" : "error"}>
            {v.toFixed(1)}
          </Tag>
        ) : (
          "-"
        ),
      sorter: (a, b) => (a.eco_score ?? 0) - (b.eco_score ?? 0),
    },
    {
      title: "急加速",
      dataIndex: "harsh_acceleration_count",
      key: "harsh_acceleration_count",
      width: 80,
      render: (v: number) => (v > 0 ? <Text type="warning">{v}</Text> : v),
    },
    {
      title: "急刹车",
      dataIndex: "harsh_braking_count",
      key: "harsh_braking_count",
      width: 80,
      render: (v: number) => (v > 0 ? <Text type="danger">{v}</Text> : v),
    },
  ];

  return (
    <div>
      {summary && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="统计天数"
                value={summary.days}
                suffix="天"
                prefix={<ClockCircleOutlined style={{ color: "#3b82f6" }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="总行程数"
                value={summary.totalTrips}
                suffix="次"
                prefix={<CarOutlined style={{ color: "#6366f1" }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="总行驶距离"
                value={summary.totalDistance}
                suffix="km"
                precision={0}
                prefix={<EnvironmentOutlined style={{ color: "#10b981" }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="总行驶时长"
                value={fmtDuration(summary.totalDuration)}
                prefix={<ClockCircleOutlined style={{ color: "#f59e0b" }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="平均安全评分"
                value={summary.avgSafety ?? 0}
                suffix="/100"
                precision={1}
                valueStyle={{ color: healthColor(summary.avgSafety) }}
                prefix={<HeartOutlined style={{ color: healthColor(summary.avgSafety) }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="平均能耗评分"
                value={summary.avgEco ?? 0}
                suffix="/100"
                precision={1}
                valueStyle={{ color: healthColor(summary.avgEco) }}
                prefix={<ThunderboltOutlined style={{ color: healthColor(summary.avgEco) }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="急驾驶事件"
                value={summary.totalHarsh}
                suffix="次"
                valueStyle={summary.totalHarsh > 0 ? { color: "#ef4444" } : undefined}
                prefix={<AlertOutlined style={{ color: "#ef4444" }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="cs-card">
              <Statistic
                title="总能耗"
                value={summary.totalFuel}
                suffix="L"
                precision={1}
                prefix={<ThunderboltOutlined style={{ color: "#8b5cf6" }} />}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card className="cs-card" title={<Space><DashboardOutlined /> 近 30 天驾驶数据</Space>}>
        <Table
          rowKey="id"
          size="middle"
          columns={columns}
          dataSource={behaviors}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{ emptyText: "暂无驾驶行为数据" }}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  );
}

// ---- Alerts Tab ----
interface AlertsTabProps extends TabProps {
  vehicleId: number;
  onAction: (alertId: number, status: string) => void;
  updatingIds: Set<number>;
}

function AlertsTab({ archive, onAction, updatingIds }: AlertsTabProps) {
  const sortedAlerts = useMemo(() => {
    const levelOrder: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    const statusOrder: Record<string, number> = { active: 0, acknowledged: 1, resolved: 2 };
    return [...archive.alerts].sort((a, b) => {
      const lo = (levelOrder[a.level] ?? 3) - (levelOrder[b.level] ?? 3);
      if (lo !== 0) return lo;
      const so = (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3);
      if (so !== 0) return so;
      return dayjs(b.triggered_at).valueOf() - dayjs(a.triggered_at).valueOf();
    });
  }, [archive.alerts]);

  const counts = useMemo(() => {
    const active = archive.alerts.filter((a) => a.status === "active").length;
    const acknowledged = archive.alerts.filter((a) => a.status === "acknowledged").length;
    const resolved = archive.alerts.filter((a) => a.status === "resolved").length;
    const critical = archive.alerts.filter((a) => a.level === "critical" && a.status !== "resolved").length;
    return { active, acknowledged, resolved, critical };
  }, [archive.alerts]);

  if (sortedAlerts.length === 0) {
    return (
      <Empty
        image={<AlertOutlined style={{ fontSize: 48, color: "#9ca3af" }} />}
        description="暂无告警记录"
      />
    );
  }

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="活跃告警" value={counts.active} valueStyle={{ color: "#ef4444" }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="严重告警" value={counts.critical} valueStyle={{ color: "#ef4444" }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="已确认" value={counts.acknowledged} valueStyle={{ color: "#f59e0b" }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="已解决" value={counts.resolved} valueStyle={{ color: "#10b981" }} />
          </Card>
        </Col>
      </Row>

      <List
        dataSource={sortedAlerts}
        renderItem={(alert: AlertType) => (
          <Card
            className="cs-card"
            size="small"
            style={{ marginBottom: 12 }}
            styles={{
              body: { padding: "12px 16px" },
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <Space wrap>
                <Tag color={alertLevelColor[alert.level] || "default"} style={{ fontWeight: 600 }}>
                  {alertLevelText[alert.level] || alert.level}
                </Tag>
                <Badge status={alertStatusBadge[alert.status] || "default"} text={alertStatusText[alert.status] || alert.status} />
                {alert.category && <Tag>{alert.category}</Tag>}
                <Text strong>{alert.title}</Text>
              </Space>
              <Space>
                {alert.status === "active" && (
                  <Button
                    size="middle"
                    icon={<CheckOutlined />}
                    loading={updatingIds.has(alert.id)}
                    onClick={() => onAction(alert.id, "acknowledged")}
                  >
                    确认
                  </Button>
                )}
                {alert.status !== "resolved" && (
                  <Button
                    size="middle"
                    type="primary"
                    icon={<CloseOutlined />}
                    loading={updatingIds.has(alert.id)}
                    onClick={() => onAction(alert.id, "resolved")}
                  >
                    解决
                  </Button>
                )}
              </Space>
            </div>
            {alert.detail && (
              <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 4 }}>
                {alert.detail}
              </Paragraph>
            )}
            {alert.recommendation && (
              <Space style={{ marginTop: 4 }}>
                <Tag icon={<CheckOutlined />} color="blue">建议</Tag>
                <Text type="secondary">{alert.recommendation}</Text>
              </Space>
            )}
            <div style={{ marginTop: 8 }}>
              <Space split={<Text type="secondary">|</Text>}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  触发时间: {fmtDateTime(alert.triggered_at)}
                </Text>
                {alert.acknowledged_at && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    确认: {fmtDateTime(alert.acknowledged_at)}
                  </Text>
                )}
                {alert.resolved_at && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    解决: {fmtDateTime(alert.resolved_at)}
                  </Text>
                )}
              </Space>
            </div>
          </Card>
        )}
      />
    </div>
  );
}

// ---- Ownership Tab ----
function OwnershipTab({ archive }: TabProps) {
  const columns: TableColumnsType<OwnershipRecord> = [
    {
      title: "车主",
      dataIndex: "owner_name",
      key: "owner_name",
      width: 120,
      render: (v: string) => v || "-",
    },
    {
      title: "转移类型",
      dataIndex: "transfer_type",
      key: "transfer_type",
      width: 100,
      render: (v: string) => (
        <Tag color="blue">{transferTypeText[v] || v}</Tag>
      ),
    },
    {
      title: "开始日期",
      dataIndex: "start_date",
      key: "start_date",
      width: 120,
      render: (v: string) => fmtDate(v),
      sorter: (a, b) => dayjs(a.start_date).valueOf() - dayjs(b.start_date).valueOf(),
      defaultSortOrder: "ascend",
    },
    {
      title: "结束日期",
      dataIndex: "end_date",
      key: "end_date",
      width: 120,
      render: (v: string) => fmtDate(v),
    },
    {
      title: "购买价格",
      dataIndex: "purchase_price",
      key: "purchase_price",
      width: 120,
      render: (v: number) => fmtCost(v),
    },
    {
      title: "出售价格",
      dataIndex: "sale_price",
      key: "sale_price",
      width: 120,
      render: (v: number) => fmtCost(v),
    },
    {
      title: "转移时里程",
      dataIndex: "mileage_at_transfer",
      key: "mileage_at_transfer",
      width: 130,
      render: (v: number) => fmtMileage(v),
    },
    {
      title: "备注",
      dataIndex: "notes",
      key: "notes",
      ellipsis: true,
      render: (v: string) => v || "-",
    },
  ];

  return (
    <Card className="cs-card" title={<Space><SolutionOutlined /> 所有权变更历史</Space>}>
      <Table
        rowKey="id"
        size="middle"
        columns={columns}
        dataSource={archive.ownership_history}
        pagination={{ pageSize: 10, showSizeChanger: false }}
        locale={{ emptyText: "暂无所有权记录" }}
        scroll={{ x: 900 }}
      />
    </Card>
  );
}

// ---- Digital Twin Tab ----
function DigitalTwinTab({ archive }: TabProps) {
  const twin = archive.digital_twin;

  if (!twin) {
    return (
      <Empty
        image={<ApartmentOutlined style={{ fontSize: 48, color: "#9ca3af" }} />}
        description="该车辆暂未创建数字孪生模型"
      />
    );
  }

  const telemetryEntries = twin.telemetry
    ? Object.entries(twin.telemetry)
    : [];
  const configEntries = twin.config
    ? Object.entries(twin.config)
    : [];

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card
            className="cs-card"
            title={<Space><ApartmentOutlined /> 数字孪生状态</Space>}
          >
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="模型版本">{twin.model_version}</Descriptions.Item>
              <Descriptions.Item label="模型 ID">{twin.model_url || "-"}</Descriptions.Item>
              <Descriptions.Item label="同步状态">
                <Tag
                  color={twinSyncColor[twin.sync_status] || "default"}
                  icon={twin.sync_status === "syncing" ? <SyncOutlined spin /> : undefined}
                >
                  {twinSyncText[twin.sync_status] || twin.sync_status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="同步频率">{twin.sync_frequency}</Descriptions.Item>
              <Descriptions.Item label="上次同步">{fmtDateTime(twin.last_sync_at)}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{fmtDateTime(twin.created_at)}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{fmtDateTime(twin.updated_at)}</Descriptions.Item>
              {twin.notes && (
                <Descriptions.Item label="备注">{twin.notes}</Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            className="cs-card"
            title={<Space><ThunderboltOutlined /> 遥测数据</Space>}
            style={{ marginBottom: 16 }}
          >
            {telemetryEntries.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无遥测数据" />
            ) : (
              <Descriptions column={1} size="small" bordered>
                {telemetryEntries.map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {renderUnknownValue(v)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            )}
          </Card>

          <Card className="cs-card" title={<Space><ToolOutlined /> 孪生配置</Space>}>
            {configEntries.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无配置数据" />
            ) : (
              <Descriptions column={1} size="small" bordered>
                {configEntries.map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {renderUnknownValue(v)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

// ============================================================
// Service order maps (§3A.1)
// ============================================================

const serviceOrderStatusText: Record<string, string> = {
  created: "已创建",
  booked: "已预约",
  in_service: "维修中",
  done: "已完成",
  closed: "已关闭",
};

const serviceOrderStatusColor: Record<string, string> = {
  created: "blue",
  booked: "cyan",
  in_service: "orange",
  done: "green",
  closed: "default",
};

const serviceOrderStatusDotColor: Record<string, string> = {
  created: "blue",
  booked: "cyan",
  in_service: "orange",
  done: "green",
  closed: "gray",
  feedback: "purple",
};

const serviceTypeText: Record<string, string> = {
  roadside_assist: "道路救援",
  manufacturer_service: "车企服务",
  insurance_service: "保险服务",
  maintenance: "保养维护",
  diagnostic: "诊断检查",
};

const feedbackTypeText: Record<string, string> = {
  confirmed: "确认问题",
  false_alarm: "误报",
  no_event: "无异常",
  partial: "部分确认",
};

const feedbackTypeColor: Record<string, string> = {
  confirmed: "green",
  false_alarm: "orange",
  no_event: "blue",
  partial: "gold",
};

const STATUS_FLOW = ["created", "booked", "in_service", "done", "closed"];

function nextStatus(current: string): string | null {
  const idx = STATUS_FLOW.indexOf(current);
  if (idx < STATUS_FLOW.length - 1) return STATUS_FLOW[idx + 1];
  return null;
}

// ============================================================
// Service Orders Tab (§3A.1 — after-sales closed loop)
// ============================================================

interface ServiceOrdersTabProps {
  vehicleId: number;
}

function ServiceOrdersTab({ vehicleId }: ServiceOrdersTabProps) {
  const [orders, setOrders] = useState<ServiceOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<ServiceOrder | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [feedbackForm] = Form.useForm();
  const [createForm] = Form.useForm();

  const loadOrders = useCallback(async () => {
    setLoading(true);
    try {
      const data = await vehicleService.listServiceOrders(vehicleId);
      setOrders(data.items);
    } catch {
      /* handled by interceptor */
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const handleViewDetail = async (orderId: number) => {
    try {
      const order = await vehicleService.getServiceOrder(vehicleId, orderId);
      setSelectedOrder(order);
      setDetailVisible(true);
    } catch {
      message.error("加载工单详情失败");
    }
  };

  const handleAdvance = async (orderId: number, note?: string) => {
    setAdvancing(true);
    try {
      const updated = await vehicleService.advanceServiceOrder(vehicleId, orderId, {
        note,
      });
      setSelectedOrder(updated);
      message.success(`工单已推进至「${serviceOrderStatusText[updated.status]}」`);
      await loadOrders();
    } catch {
      message.error("推进工单状态失败");
    } finally {
      setAdvancing(false);
    }
  };

  const handleSubmitFeedback = async () => {
    if (selectedOrder == null) return;
    try {
      const values = await feedbackForm.validateFields();
      const updated = await vehicleService.submitServiceFeedback(
        vehicleId,
        selectedOrder.id,
        values as ServiceOrderFeedback,
      );
      setSelectedOrder(updated);
      setFeedbackVisible(false);
      feedbackForm.resetFields();
      message.success("售后反馈已提交");
      await loadOrders();
    } catch {
      message.error("提交反馈失败");
    }
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      await vehicleService.createServiceOrder(vehicleId, values as ServiceOrderCreate);
      setCreateVisible(false);
      createForm.resetFields();
      message.success("工单已创建");
      await loadOrders();
    } catch {
      message.error("创建工单失败");
    }
  };

  const columns: TableColumnsType<ServiceOrder> = [
    {
      title: "工单ID",
      dataIndex: "id",
      key: "id",
      width: 80,
    },
    {
      title: "服务类型",
      dataIndex: "service_type",
      key: "service_type",
      width: 110,
      render: (v: string) => (
        <Tag>{serviceTypeText[v] || v}</Tag>
      ),
    },
    {
      title: "服务名称",
      dataIndex: "service_name",
      key: "service_name",
      ellipsis: true,
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 80,
      render: (v: string) => (
        <Tag color={priorityColor[v] || "default"}>{priorityText[v] || v}</Tag>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string) => (
        <Tag color={serviceOrderStatusColor[v] || "default"}>
          {serviceOrderStatusText[v] || v}
        </Tag>
      ),
    },
    {
      title: "反馈",
      dataIndex: "feedback_type",
      key: "feedback_type",
      width: 100,
      render: (v: string | null) =>
        v ? (
          <Tag color={feedbackTypeColor[v] || "default"}>
            {feedbackTypeText[v] || v}
          </Tag>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 150,
      render: (v: string) => fmtDateTime(v),
      sorter: (a, b) => dayjs(a.created_at).valueOf() - dayjs(b.created_at).valueOf(),
      defaultSortOrder: "descend",
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: unknown, r: ServiceOrder) => (
        <Button
          size="small"
          type="link"
          icon={<FileTextOutlined />}
          onClick={() => handleViewDetail(r.id)}
        >
          详情
        </Button>
      ),
    },
  ];

  // Summary counts
  const activeCount = orders.filter(
    (o) => o.status !== "closed",
  ).length;
  const doneCount = orders.filter((o) => o.status === "done").length;
  const closedCount = orders.filter((o) => o.status === "closed").length;
  const feedbackCount = orders.filter((o) => o.feedback_type != null).length;

  return (
    <div>
      {/* Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="进行中工单" value={activeCount} suffix="单" />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="待反馈" value={doneCount} suffix="单" valueStyle={{ color: "#f59e0b" }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="已关闭" value={closedCount} suffix="单" valueStyle={{ color: "#10b981" }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card">
            <Statistic title="已反馈" value={feedbackCount} suffix="单" />
          </Card>
        </Col>
      </Row>

      {/* Order list */}
      <Card
        className="cs-card"
        title={
          <Space>
            <CustomerServiceOutlined />
            售后工单列表
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateVisible(true)}
          >
            创建工单
          </Button>
        }
      >
        <Table
          rowKey="id"
          size="middle"
          columns={columns}
          dataSource={orders}
          loading={loading}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          locale={{ emptyText: "暂无售后工单" }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* Detail modal */}
      <Modal
        title={
          <Space>
            <CustomerServiceOutlined />
            工单详情 #{selectedOrder?.id}
          </Space>
        }
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={720}
      >
        {selectedOrder && (
          <div>
            {/* Order info */}
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="服务类型" span={1}>
                <Tag>{serviceTypeText[selectedOrder.service_type] || selectedOrder.service_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态" span={1}>
                <Tag color={serviceOrderStatusColor[selectedOrder.status]}>
                  {serviceOrderStatusText[selectedOrder.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="服务名称" span={2}>
                <Text strong>{selectedOrder.service_name}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="优先级" span={1}>
                <Tag color={priorityColor[selectedOrder.priority]}>
                  {priorityText[selectedOrder.priority]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="预估响应" span={1}>
                {selectedOrder.estimated_response || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="创建原因" span={2}>
                {selectedOrder.reason}
              </Descriptions.Item>
              {selectedOrder.diagnosis_summary && (
                <Descriptions.Item label="诊断摘要" span={2}>
                  <Text type="secondary">{selectedOrder.diagnosis_summary}</Text>
                </Descriptions.Item>
              )}
              {selectedOrder.service_provider && (
                <Descriptions.Item label="服务商" span={1}>
                  {selectedOrder.service_provider}
                </Descriptions.Item>
              )}
              {selectedOrder.cost != null && (
                <Descriptions.Item label="费用" span={1}>
                  {fmtCost(selectedOrder.cost)}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建时间" span={1}>
                {fmtDateTime(selectedOrder.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间" span={1}>
                {fmtDateTime(selectedOrder.updated_at)}
              </Descriptions.Item>
            </Descriptions>

            {/* Progress timeline */}
            <Card
              size="small"
              title={<Space><ClockCircleOutlined /> 进度时间线</Space>}
              style={{ marginBottom: 16 }}
            >
              <Timeline
                items={(selectedOrder.status_history || []).map((h) => ({
                  color: serviceOrderStatusDotColor[h.status] || "gray",
                  children: (
                    <div>
                      <Space>
                        <Tag color={serviceOrderStatusColor[h.status] || "default"}>
                          {serviceOrderStatusText[h.status] || h.status}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {fmtDateTime(h.timestamp)}
                        </Text>
                      </Space>
                      {h.note && (
                        <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>
                          {h.note}
                        </div>
                      )}
                    </div>
                  ),
                }))}
              />
            </Card>

            {/* Feedback display */}
            {selectedOrder.feedback_type && (
              <Card
                size="small"
                title={<Space><MessageOutlined /> 售后反馈</Space>}
                style={{ marginBottom: 16 }}
              >
                <Space direction="vertical" size="small">
                  <Space>
                    <Tag color={feedbackTypeColor[selectedOrder.feedback_type]}>
                      {feedbackTypeText[selectedOrder.feedback_type]}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {fmtDateTime(selectedOrder.feedback_at)}
                    </Text>
                  </Space>
                  {selectedOrder.feedback_note && (
                    <Text>{selectedOrder.feedback_note}</Text>
                  )}
                </Space>
              </Card>
            )}

            {/* Actions */}
            <Space wrap>
              {nextStatus(selectedOrder.status) && (
                <Button
                  type="primary"
                  icon={<ForwardOutlined />}
                  loading={advancing}
                  onClick={() => handleAdvance(selectedOrder.id)}
                >
                  推进至「{serviceOrderStatusText[nextStatus(selectedOrder.status)!]}」
                </Button>
              )}
              {(selectedOrder.status === "done" || selectedOrder.status === "closed") &&
                !selectedOrder.feedback_type && (
                  <Button
                    icon={<MessageOutlined />}
                    onClick={() => {
                      feedbackForm.resetFields();
                      setFeedbackVisible(true);
                    }}
                  >
                    提交售后反馈
                  </Button>
                )}
            </Space>
          </div>
        )}
      </Modal>

      {/* Feedback modal */}
      <Modal
        title="售后反馈"
        open={feedbackVisible}
        onOk={handleSubmitFeedback}
        onCancel={() => setFeedbackVisible(false)}
        okText="提交"
        cancelText="取消"
      >
        <Form form={feedbackForm} layout="vertical">
          <Form.Item
            name="feedback_type"
            label="反馈类型"
            rules={[{ required: true, message: "请选择反馈类型" }]}
          >
            <Select placeholder="选择反馈类型">
              <Select.Option value="confirmed">确认问题 — 诊断准确，确实存在该问题</Select.Option>
              <Select.Option value="false_alarm">误报 — 实际无异常</Select.Option>
              <Select.Option value="no_event">无异常 — 检查后未发现问题</Select.Option>
              <Select.Option value="partial">部分确认 — 部分问题属实</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="feedback_note" label="反馈备注">
            <Input.TextArea
              rows={3}
              placeholder="补充说明（可选）"
              maxLength={500}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create modal */}
      <Modal
        title="创建售后工单"
        open={createVisible}
        onOk={handleCreate}
        onCancel={() => setCreateVisible(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="service_type"
            label="服务类型"
            rules={[{ required: true, message: "请选择服务类型" }]}
          >
            <Select placeholder="选择服务类型">
              <Select.Option value="manufacturer_service">车企服务</Select.Option>
              <Select.Option value="roadside_assist">道路救援</Select.Option>
              <Select.Option value="insurance_service">保险服务</Select.Option>
              <Select.Option value="maintenance">保养维护</Select.Option>
              <Select.Option value="diagnostic">诊断检查</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="service_name"
            label="服务名称"
            rules={[{ required: true, message: "请输入服务名称" }]}
          >
            <Input placeholder="如：电池冷却系统检查" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue="medium">
            <Select>
              <Select.Option value="high">高</Select.Option>
              <Select.Option value="medium">中</Select.Option>
              <Select.Option value="low">低</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="reason"
            label="创建原因"
            rules={[{ required: true, message: "请输入创建原因" }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="描述创建此工单的原因（通常来自 Agent 诊断）"
              maxLength={500}
              showCount
            />
          </Form.Item>
          <Form.Item name="description" label="补充描述">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

// ============================================================
// Main Component
// ============================================================

export default function VehicleArchive() {
  const { vehicle, loading: vehicleLoading, refresh: refreshVehicle } = useCurrentVehicle();
  const [archive, setArchive] = useState<VehicleArchive | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const [updatingAlertIds, setUpdatingAlertIds] = useState<Set<number>>(new Set());

  // Load archive for current vehicle
  const loadArchive = async (id: number) => {
    setArchiveLoading(true);
    setArchiveError(null);
    try {
      const data = await vehicleService.getArchive(id);
      setArchive(data);
    } catch (e) {
      setArchive(null);
      setArchiveError(e instanceof Error ? e.message : "加载档案失败");
    } finally {
      setArchiveLoading(false);
    }
  };

  useEffect(() => {
    if (vehicle != null) {
      loadArchive(vehicle.id);
    } else {
      setArchive(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle]);

  // Alert action (acknowledge / resolve)
  const handleAlertAction = async (alertId: number, status: string) => {
    if (vehicle == null) return;
    setUpdatingAlertIds((prev) => new Set(prev).add(alertId));
    try {
      await vehicleService.updateAlert(vehicle.id, alertId, { status });
      message.success(status === "acknowledged" ? "告警已确认" : "告警已解决");
      await loadArchive(vehicle.id);
    } catch {
      /* error handled by interceptor */
    } finally {
      setUpdatingAlertIds((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  // Summary bar values
  const healthScore = archive?.health_score ?? null;
  const activeAlertCount = archive?.active_alert_count ?? 0;
  const totalMaintenanceCost = archive?.total_maintenance_cost ?? 0;
  const nextMaintenanceCount = archive?.next_maintenance_items?.length ?? 0;

  // Tab items
  const tabItems = archive
    ? [
        {
          key: "health",
          label: (
            <span>
              <HeartOutlined /> 健康报告
            </span>
          ),
          children: <HealthReportTab archive={archive} />,
        },
        {
          key: "lifecycle",
          label: (
            <span>
              <ClockCircleOutlined /> 生命周期
            </span>
          ),
          children: <LifecycleTab archive={archive} />,
        },
        {
          key: "maintenance",
          label: (
            <span>
              <ToolOutlined /> 保养记录
            </span>
          ),
          children: <MaintenanceTab archive={archive} />,
        },
        {
          key: "driving",
          label: (
            <span>
              <DashboardOutlined /> 驾驶行为
            </span>
          ),
          children: <DrivingBehaviorTab archive={archive} />,
        },
        {
          key: "alerts",
          label: (
            <span>
              <AlertOutlined /> 告警
              {activeAlertCount > 0 && (
                <Badge
                  count={activeAlertCount}
                  size="small"
                  offset={[6, -2]}
                  style={{ marginLeft: 4 }}
                />
              )}
            </span>
          ),
          children: (
            <AlertsTab
              archive={archive}
              vehicleId={vehicle!.id}
              onAction={handleAlertAction}
              updatingIds={updatingAlertIds}
            />
          ),
        },
        {
          key: "ownership",
          label: (
            <span>
              <SolutionOutlined /> 所有权
            </span>
          ),
          children: <OwnershipTab archive={archive} />,
        },
        {
          key: "service-orders",
          label: (
            <span>
              <CustomerServiceOutlined /> 售后工单
            </span>
          ),
          children: <ServiceOrdersTab vehicleId={vehicle!.id} />,
        },
        {
          key: "twin",
          label: (
            <span>
              <ApartmentOutlined /> 数字孪生
            </span>
          ),
          children: <DigitalTwinTab archive={archive} />,
        },
      ]
    : [];

  return (
    <div>
      {/* Header */}
      <Space style={{ justifyContent: "space-between", width: "100%", marginBottom: 16 }} wrap>
        <Space align="center">
          <Title level={3} style={{ margin: 0 }}>
            车辆数字生命档案
          </Title>
          {/* 当前默认车辆为 seed 持久虚构车「小白」，数据非真实车辆 — 挂 L2b 角标修复 GOAI 红线2 正向失真。
              TODO: 待后端 provenance 信封（R-01）落地后改为 level={provenance.badge_level} 驱动，不再硬编码。 */}
          <DemoBadge level="L2b" inline />
        </Space>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => {
            refreshVehicle();
            if (vehicle != null) loadArchive(vehicle.id);
          }}
        >
          刷新
        </Button>
      </Space>

      {/* Archive content */}
      {vehicleLoading ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : !vehicle ? (
        <Card className="cs-card">
          <Empty
            image={<CarOutlined style={{ fontSize: 56, color: "#9ca3af" }} />}
            description="本车数据尚未就绪"
            style={{ padding: "60px 0" }}
          />
        </Card>
      ) : archiveLoading && !archive ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : archiveError ? (
        <AntAlert
          type="error"
          showIcon
          message="档案加载失败"
          description={`${archiveError} — 请确认后端服务正常并重试。`}
          action={
            <Button
              size="middle"
              onClick={() => vehicle != null && loadArchive(vehicle.id)}
            >
              重试
            </Button>
          }
        />
      ) : archive ? (
        <div>
          {/* Summary bar */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} md={6}>
              <Card className="cs-card">
                <Statistic
                  title="健康分数"
                  value={healthScore ?? 0}
                  suffix="/100"
                  valueStyle={{ color: healthColor(healthScore) }}
                  prefix={<HeartOutlined style={{ color: healthColor(healthScore) }} />}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card className="cs-card">
                <Statistic
                  title="活跃告警"
                  value={activeAlertCount}
                  suffix="条"
                  valueStyle={activeAlertCount > 0 ? { color: "#ef4444" } : undefined}
                  prefix={<AlertOutlined style={{ color: "#ef4444" }} />}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card className="cs-card">
                <Statistic
                  title="保养总费用"
                  value={totalMaintenanceCost}
                  prefix="¥"
                  precision={2}
                  valueStyle={{ color: "#f59e0b" }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card className="cs-card">
                <Statistic
                  title="下次保养项"
                  value={nextMaintenanceCount}
                  suffix="项"
                  valueStyle={nextMaintenanceCount > 0 ? { color: "#3b82f6" } : undefined}
                  prefix={<ToolOutlined style={{ color: "#3b82f6" }} />}
                />
              </Card>
            </Col>
          </Row>

          {/* Vehicle basic info */}
          <Card
            className="cs-card"
            title={
              <Space>
                <CarOutlined style={{ color: "#3b82f6" }} />
                <span>
                  {archive.vehicle.nickname
                    ? archive.vehicle.nickname
                    : `${archive.vehicle.brand} ${archive.vehicle.model}`}
                </span>
                <Tag color={vehicleStatusColor[archive.vehicle.status] || "default"}>
                  {vehicleStatusText[archive.vehicle.status] || archive.vehicle.status}
                </Tag>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }} size="small">
              <Descriptions.Item label="品牌型号">
                {archive.vehicle.brand} {archive.vehicle.model}
              </Descriptions.Item>
              <Descriptions.Item label="年份">{archive.vehicle.year}</Descriptions.Item>
              <Descriptions.Item label="车牌号">
                {archive.vehicle.plate_number || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="VIN" span={2}>
                <Text copyable>{archive.vehicle.vin}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="颜色">
                {archive.vehicle.color || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="里程">
                {fmtMileage(archive.vehicle.mileage)}
              </Descriptions.Item>
              <Descriptions.Item label="燃料类型">
                <Tag color="blue">{fuelTypeText[archive.vehicle.fuel_type] || archive.vehicle.fuel_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="发动机类型">
                {archive.vehicle.engine_type || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="购买日期">
                {fmtDate(archive.vehicle.purchase_date)}
              </Descriptions.Item>
              <Descriptions.Item label="购买价格">
                {archive.vehicle.purchase_price != null
                  ? fmtCost(archive.vehicle.purchase_price)
                  : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="经销商">
                {archive.vehicle.dealer || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="保险公司">
                {archive.vehicle.insurance_company || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="保险单号">
                {archive.vehicle.insurance_policy_no || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="保险到期">
                {archive.vehicle.insurance_expiry ? (
                  <Tag color={dayjs(archive.vehicle.insurance_expiry).isBefore(dayjs().add(30, "day")) ? "red" : "green"}>
                    {fmtDate(archive.vehicle.insurance_expiry)}
                  </Tag>
                ) : (
                  "-"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="注册日期">
                {fmtDate(archive.vehicle.registration_date)}
              </Descriptions.Item>
              <Descriptions.Item label="年检到期">
                {archive.vehicle.inspection_expiry ? (
                  <Tag color={dayjs(archive.vehicle.inspection_expiry).isBefore(dayjs().add(30, "day")) ? "red" : "green"}>
                    {fmtDate(archive.vehicle.inspection_expiry)}
                  </Tag>
                ) : (
                  "-"
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* Tabs */}
          <Card className="cs-card" styles={{ body: { padding: "12px 16px" } }}>
            <Tabs items={tabItems} size="large" destroyInactiveTabPane={false} />
          </Card>
        </div>
      ) : null}
    </div>
  );
}

