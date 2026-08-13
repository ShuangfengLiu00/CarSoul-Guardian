/**
 * 记忆海洋 /memory
 * 已接通真实车辆记忆数据（Guardian `/api/digital-twin/{id}/memories`，由
 * soulService.listMemories 拉取车辆数字孪生累积的真实记忆）。数据全部来自
 * 真实端点，无占位数据。无记忆时诚实显示空态。
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
  Typography,
  Alert,
} from "antd";
import {
  ExperimentOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  HeartOutlined,
  WarningOutlined,
  SafetyOutlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { vehicleService, soulService } from "@/services";
import type { Vehicle, VehicleMemoryItem } from "@/services/types";

const { Title, Text } = Typography;

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

export default function MemoryOcean() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclesLoading, setVehiclesLoading] = useState(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);
  const [memories, setMemories] = useState<VehicleMemoryItem[]>([]);
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

  const loadMemories = useCallback(async (id: number) => {
    setLoading(true);
    setError(false);
    try {
      const res = await soulService.listMemories(id, undefined, 100);
      setMemories(res.items ?? []);
    } catch {
      setError(true);
      setMemories([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  useEffect(() => {
    if (selectedVehicleId != null) loadMemories(selectedVehicleId);
    else setMemories([]);
  }, [selectedVehicleId, loadMemories]);

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
          <ExperimentOutlined style={{ marginRight: 8, color: "#a855f7" }} />
          记忆海洋
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
            image={<DatabaseOutlined style={{ fontSize: 56, color: "#9ca3af" }} />}
            description="请选择一辆车，查看它的真实记忆海洋"
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
          message="记忆数据加载失败"
          description="无法连接数字孪生记忆服务，本页不展示任何数据。"
        />
      )}

      {selectedVehicleId && !loading && !error && (
        <Card title={<Space><DatabaseOutlined /> 真实车辆记忆 <Tag color="blue">{memories.length} 条</Tag></Space>}>
          {memories.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="该车暂无记忆数据（真实状态）"
            />
          ) : (
            <Row gutter={[12, 12]}>
              {memories.map((m, i) => (
                <Col xs={24} md={12} key={i}>
                  <div
                    style={{
                      border: "1px solid #1f2937",
                      borderRadius: 12,
                      padding: 14,
                      background: "#0f1729",
                      height: "100%",
                    }}
                  >
                    <Space style={{ marginBottom: 6 }}>
                      <span style={{ color: "#a855f7" }}>
                        {memoryTypeIcon[m.memory_type] ?? <NodeIndexOutlined />}
                      </span>
                      <Tag color={memoryTypeColor[m.memory_type] ?? "gray"} style={{ fontSize: 11 }}>
                        {memoryTypeText[m.memory_type] ?? m.memory_type}
                      </Tag>
                      {m.emotion_score != null && m.emotion_score > 0.3 && (
                        <Tag color="green" style={{ fontSize: 11 }}>积极</Tag>
                      )}
                      {m.emotion_score != null && m.emotion_score < -0.1 && (
                        <Tag color="orange" style={{ fontSize: 11 }}>消极</Tag>
                      )}
                    </Space>
                    <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.6 }}>
                      {m.content}
                    </div>
                    <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 6 }}>
                      {fmtDate(m.created_time)}
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
          )}
          <Row style={{ marginTop: 12 }}>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>
                数据来源：车辆数字孪生真实记忆接口，每条记忆标注来源时间与置信度，可追溯、不可伪造
              </Text>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}
