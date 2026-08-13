/**
 * 仿真沙盘 /simulator
 * 已接通真实预测引擎输出（Guardian `/api/digital-twin/{id}/predictions`，由
 * soulService.listPredictions 拉取车辆世界模型引擎 xgb-battery-v1.0 的真实
 * 预测结论）。展示真实预测（组件 / 风险 / 置信度 / 根因 / 建议），不渲染任何
 * 模拟情景数字。交互式 what-if 情景推演（用户输入策略 → 推演结果）依赖的预测
 * 引擎接口当前未开放，本页如实说明，不伪称已具备。
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Card,
  Col,
  Empty,
  Row,
  Select,
  Skeleton,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  ToolOutlined,
  RobotOutlined,
  BulbOutlined,
} from "@ant-design/icons";
import { vehicleService, soulService } from "@/services";
import type { Vehicle, VehiclePredictionItem } from "@/services/types";

const { Title, Text, Paragraph } = Typography;

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

export default function VehicleSimulator() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclesLoading, setVehiclesLoading] = useState(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);
  const [predictions, setPredictions] = useState<VehiclePredictionItem[]>([]);
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

  const loadPredictions = useCallback(async (id: number) => {
    setLoading(true);
    setError(false);
    try {
      const res = await soulService.listPredictions(id, undefined, 50);
      setPredictions(res.items ?? []);
    } catch {
      setError(true);
      setPredictions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  useEffect(() => {
    if (selectedVehicleId != null) loadPredictions(selectedVehicleId);
    else setPredictions([]);
  }, [selectedVehicleId, loadPredictions]);

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
          <ToolOutlined style={{ marginRight: 8, color: "#3b82f6" }} />
          仿真沙盘
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

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="真实预测引擎输出"
        description="以下为车辆世界模型引擎（xgb-battery-v1.0）对当前车辆产生的真实预测结论。交互式 what-if 情景推演接口尚未开放，本页如实呈现真实预测，不伪称可自定义策略推演。"
      />

      {!selectedVehicleId && (
        <Card>
          <Empty
            image={<ToolOutlined style={{ fontSize: 56, color: "#9ca3af" }} />}
            description="请选择一辆车，查看真实预测推演"
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
          message="预测数据加载失败"
          description="无法连接预测引擎，本页不展示任何数据。"
        />
      )}

      {selectedVehicleId && !loading && !error && (
        <Card title={<Space><RobotOutlined /> 真实预测结论 <Tag color="blue">{predictions.length} 项</Tag></Space>}>
          {predictions.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="该车暂无预测数据（真实状态）"
            />
          ) : (
            <Row gutter={[12, 12]}>
              {predictions.map((p, i) => (
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
                      <Text strong>{componentLabel[p.target_component] ?? p.target_component}</Text>
                      <Tag color={riskTagColor(p.risk_level)}>{riskTagText(p.risk_level)}</Tag>
                      {p.confidence != null && (
                        <Tag color="default" style={{ fontSize: 11 }}>
                          可信度 {Math.round(p.confidence * 100)}%
                        </Tag>
                      )}
                    </Space>
                    <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.6 }}>
                      {p.prediction}
                    </div>
                    {p.root_cause && (
                      <Paragraph type="secondary" style={{ fontSize: 12, margin: "6px 0 0" }}>
                        根因：{p.root_cause}
                      </Paragraph>
                    )}
                    {p.predicted_value != null && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        预测剩余：{Math.round(p.predicted_value)} {p.predicted_unit ?? ""}
                      </Text>
                    )}
                    {p.suggestion && (
                      <div style={{ fontSize: 12, color: "#10b981", marginTop: 6 }}>
                        <BulbOutlined /> {p.suggestion}
                      </div>
                    )}
                  </div>
                </Col>
              ))}
            </Row>
          )}
          <Row style={{ marginTop: 12 }}>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>
                数据来源：车辆世界模型预测引擎真实输出，结论可解释、可溯源
              </Text>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}
