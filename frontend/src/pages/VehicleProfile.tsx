import { useEffect, useState } from "react";
import {
  Card,
  Tabs,
  Statistic,
  Row,
  Col,
  Table,
  Tag,
  List,
  Typography,
  Alert as AntAlert,
  Empty,
  Space,
  Progress,
} from "antd";
import type { TableColumnsType } from "antd";
import {
  ThunderboltOutlined,
  ToolOutlined,
  AlertOutlined,
  SafetyOutlined,
  CarOutlined,
} from "@ant-design/icons";
import { vehicleService } from "@/services/vehicleService";
import type {
  DrivingBehaviorSummary,
  MaintenanceRecord,
  MaintenanceSchedule,
  Alert,
} from "@/services/types";
import { useCurrentVehicle } from "@/hooks/useCurrentVehicle";

const { Title, Text } = Typography;

export default function VehicleProfile() {
  const { vehicle } = useCurrentVehicle();
  const vehicleId = vehicle?.id;

  const [summary, setSummary] = useState<DrivingBehaviorSummary | null>(null);
  const [maintenance, setMaintenance] = useState<MaintenanceRecord[]>([]);
  const [schedules, setSchedules] = useState<MaintenanceSchedule[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    if (!vehicleId) return;
    vehicleService
      .getDrivingBehaviorSummary(vehicleId, 30)
      .then((r) => setSummary(r ?? null))
      .catch(() => setSummary(null));
    vehicleService
      .listMaintenanceRecords(vehicleId, 20)
      .then((r) => setMaintenance(r?.items ?? []))
      .catch(() => setMaintenance([]));
    vehicleService
      .listMaintenanceSchedules(vehicleId)
      .then((r) => setSchedules((r as unknown as { items?: MaintenanceSchedule[] })?.items ?? []))
      .catch(() => setSchedules([]));
    vehicleService
      .listAlerts(vehicleId)
      .then((r) => setAlerts(r?.items ?? []))
      .catch(() => setAlerts([]));
  }, [vehicleId]);

  const distance = Number(summary?.total_distance ?? 0);
  const harsh = Number(summary?.total_harsh_events ?? 0);
  const safety = summary?.avg_safety_score != null ? Number(summary.avg_safety_score) : null;
  const eco = summary?.avg_eco_score != null ? Number(summary.avg_eco_score) : null;

  const maintCols: TableColumnsType<MaintenanceRecord> = [
    { title: "日期", dataIndex: "maintenance_date", key: "maintenance_date", width: 120 },
    { title: "项目", dataIndex: "maintenance_type", key: "maintenance_type" },
    { title: "里程", dataIndex: "mileage", key: "mileage", width: 110 },
    { title: "说明", dataIndex: "description", key: "description", ellipsis: true },
  ];

  const alertCols: TableColumnsType<Alert> = [
    { title: "等级", dataIndex: "level", key: "level", width: 90, render: (v: string) => (
        <Tag color={v?.toLowerCase() === "high" ? "red" : v?.toLowerCase() === "medium" ? "orange" : "blue"}>{String(v ?? "").toUpperCase()}</Tag>
      ) },
    { title: "类型", dataIndex: "alert_type", key: "alert_type", width: 130 },
    { title: "内容", dataIndex: "title", key: "title", ellipsis: true },
    { title: "状态", dataIndex: "status", key: "status", width: 100, render: (v: string) => <Tag>{String(v ?? "open")}</Tag> },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1280, margin: "0 auto" }}>
      <Title level={3}>
        <CarOutlined style={{ marginRight: 8, color: "#2563EB" }} />
        用车档案
      </Title>
      <Text type="secondary">驾驶行为画像 / 保养记录与提醒 / 风险预警 —— 全生命周期数据一屏掌握</Text>

      <Row gutter={16} style={{ marginTop: 20 }}>
        <Col span={6}>
          <Card>
            <Statistic title="近 30 天总里程" value={(distance / 1000).toFixed(1)} suffix="km" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="急加速 / 急刹事件" value={harsh} suffix="次" valueStyle={{ color: harsh > 20 ? "#cf1322" : undefined }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="驾驶安全分" value={safety ?? 0} precision={1} suffix="/100" valueStyle={{ color: safety != null && safety >= 80 ? "#3f8600" : undefined }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="节能分" value={eco ?? 0} precision={1} suffix="/100" valueStyle={{ color: eco != null && eco >= 80 ? "#3f8600" : undefined }} />
          </Card>
        </Col>
      </Row>

      {summary && Number(summary.trip_count ?? 0) > 0 && (
        <Card style={{ marginTop: 16 }} title="行为画像">
          <Text type="secondary">近 30 天 {summary.trip_count} 次行程，累计里程 {(distance / 1000).toFixed(0)} km</Text>
          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={12}>
              <Text>安全驾驶</Text>
              <Progress percent={safety ?? 0} status={safety != null && safety >= 80 ? "success" : "active"} />
            </Col>
            <Col span={12}>
              <Text>节能驾驶</Text>
              <Progress percent={eco ?? 0} status={eco != null && eco >= 80 ? "success" : "active"} />
            </Col>
          </Row>
        </Card>
      )}

      <Tabs
        style={{ marginTop: 16 }}
        items={[
          {
            key: "maint",
            label: (<Space><ToolOutlined />保养记录</Space>),
            children: (
              <Card>
                {maintenance.length === 0 ? (
                  <Empty description="暂无保养记录" />
                ) : (
                  <Table rowKey={(r, i) => `${i}`} columns={maintCols} dataSource={maintenance} size="small" pagination={false} />
                )}
              </Card>
            ),
          },
          {
            key: "sched",
            label: (<Space><ToolOutlined />保养提醒</Space>),
            children: (
              <Card>
                {schedules.length === 0 ? (
                  <Empty description="暂无保养计划" />
                ) : (
                  <List
                    size="small"
                    dataSource={schedules}
                    renderItem={(s, idx) => (
                      <List.Item>
                        <Space>
                          <Tag color="blue">{String(s.next_due_date ?? "")}</Tag>
                          <Text>{String(s.item_name ?? `保养计划 ${idx + 1}`)}</Text>
                          <Text type="secondary">建议里程 {String(s.next_due_km ?? "-")} km</Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            ),
          },
          {
            key: "alerts",
            label: (<Space><AlertOutlined />风险预警</Space>),
            children: (
              <Card>
                {alerts.length === 0 ? (
                  <AntAlert type="success" showIcon message="当前无风险告警" />
                ) : (
                  <Table rowKey={(r, i) => `${i}`} columns={alertCols} dataSource={alerts} size="small" pagination={false} />
                )}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
