/**
 * 故事模式 /story
 * 已接通真实数字生命叙事数据（Guardian `/api/digital-twin/{id}/life-events`，
 * 由 soulService.listLifeEvents 拉取车辆真实生命事件）。数据全部来自真实
 * 端点，无任何预录脚本 / 模拟数据。无事件时诚实显示空态。
 */
import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Col,
  Empty,
  Row,
  Select,
  Skeleton,
  Space,
  Tag,
  Timeline,
  Typography,
  Alert,
} from "antd";
import {
  ReadOutlined,
  CarOutlined,
  EnvironmentOutlined,
  ToolOutlined,
  WarningOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { vehicleService, soulService } from "@/services";
import type { Vehicle, VehicleLifeEventItem } from "@/services/types";

const { Title, Text } = Typography;

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

function fmtDate(s?: string | null): string {
  if (!s) return "-";
  return dayjs(s).format("YYYY-MM-DD");
}

export default function StoryMode() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclesLoading, setVehiclesLoading] = useState(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);
  const [events, setEvents] = useState<VehicleLifeEventItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const loadVehicles = useCallback(async () => {
    setVehiclesLoading(true);
    try {
      const data = await vehicleService.list();
      setVehicles(data.items);
      if (!selectedVehicleId && data.items.length > 0) {
        setSelectedVehicleId(data.items[0].id);
      }
    } catch {
      /* interceptor handles */
    } finally {
      setVehiclesLoading(false);
    }
  }, [selectedVehicleId]);

  const loadEvents = useCallback(async (id: number) => {
    setLoading(true);
    setError(false);
    try {
      const res = await soulService.listLifeEvents(id, undefined, 100);
      setEvents(res.items ?? []);
    } catch {
      setError(true);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  useEffect(() => {
    if (selectedVehicleId != null) loadEvents(selectedVehicleId);
    else setEvents([]);
  }, [selectedVehicleId, loadEvents]);

  const vehicleOptions = vehicles.map((v) => ({
    value: v.id,
    label: v.nickname
      ? `${v.nickname} (${v.brand} ${v.model})`
      : `${v.brand} ${v.model} (${v.year})`,
  }));

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
          marginBottom: 16,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          <ReadOutlined style={{ marginRight: 8, color: "#3b82f6" }} />
          故事模式
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
      </div>

      {!selectedVehicleId && (
        <Card>
          <Empty
            image={<CarOutlined style={{ fontSize: 56, color: "#9ca3af" }} />}
            description="请选择一辆车，回放它的真实生命故事"
          />
        </Card>
      )}

      {selectedVehicleId && loading && (
        <Card>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      )}

      {selectedVehicleId && !loading && error && (
        <Alert
          type="error"
          showIcon
          message="生命事件数据加载失败"
          description="无法连接数字生命服务，本页不展示任何数据。"
        />
      )}

      {selectedVehicleId && !loading && !error && (
        <Card title={<Space><ReadOutlined /> 真实生命事件叙事</Space>}>
          {events.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="该车暂无生命事件记录（真实状态）"
            />
          ) : (
            <Timeline
              items={events.map((ev) => ({
                color: eventTypeColor[ev.event_type] ?? "gray",
                dot: eventTypeIcon[ev.event_type] ?? <ClockCircleOutlined />,
                children: (
                  <div>
                    <Text strong>{ev.title}</Text>
                    <Tag
                      color={eventTypeColor[ev.event_type] ?? "gray"}
                      style={{ marginLeft: 8, fontSize: 11 }}
                    >
                      {eventTypeText[ev.event_type] ?? ev.event_type}
                    </Tag>
                    <div style={{ fontSize: 12, color: "#9ca3af" }}>
                      {fmtDate(ev.event_time)}
                      {ev.mileage != null ? ` · ${ev.mileage.toLocaleString()} km` : ""}
                      {ev.location ? ` · ${ev.location}` : ""}
                    </div>
                    {ev.description && (
                      <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                        {ev.description}
                      </div>
                    )}
                  </div>
                ),
              }))}
            />
          )}
          <Row style={{ marginTop: 12 }}>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>
                数据来源：车辆数字孪生真实生命事件接口，共 {events.length} 条记录
              </Text>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}
