/**
 * SensorOverview — 传感器总览（B 阶段前端交付）
 *
 * 拉取 GET /api/vehicle/{id}/sensors/snapshot，把全车 6 个域、58 项信号
 * 的当前值 / 单位 / normal-warn-crit 状态 / registry 量程与阈值一屏铺开，
 * 让用户「看得见这辆车到底有哪些数据」。
 *
 * 数据性质：快照读的是 seed 持久虚构车（后端 provenance.data_source="seed"、
 * demo_mode=true），因此固定挂 L2b 角标。
 * TODO: 后端 provenance 信封已带 badge_level，后续可改为 level={snapshot.provenance.badge_level} 驱动。
 */
import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Collapse,
  Button,
  Space,
  Typography,
  Tag,
  Table,
  Statistic,
  Row,
  Col,
  Empty,
  Spin,
  Select,
  Alert,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DashboardOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useCurrentVehicle } from "@/hooks";
import DemoBadge from "@/components/DemoBadge";
import { vehicleService } from "@/services";
import type {
  SensorSnapshot,
  SensorSnapshotSensor,
  SensorStatus,
} from "@/services/types";

const { Title, Text, Paragraph } = Typography;

/** 传感器状态 → 颜色 / 中文标签。 */
const STATUS_META: Record<SensorStatus, { color: string; label: string }> = {
  normal: { color: "green", label: "正常" },
  warn: { color: "gold", label: "预警" },
  crit: { color: "red", label: "危险" },
};

/** 读数来源 → 中文。 */
const SOURCE_LABEL: Record<string, string> = {
  seed: "库内读数",
  default: "基线回落",
};

/** 域筛选下拉项（与后端 sensor_registry.DOMAINS 对齐）。 */
const DOMAIN_OPTIONS = [
  { value: "battery", label: "电池系统" },
  { value: "motor", label: "电机/驱动" },
  { value: "chassis", label: "底盘/制动/轮胎" },
  { value: "thermal", label: "热管理" },
  { value: "environment", label: "环境/定位" },
  { value: "can_bus", label: "CAN总线/网络健康" },
];

/** 把数值裁到最多 3 位小数，避免 0.30000000000000004 这类浮点噪声。 */
function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  return Number.isInteger(n) ? String(n) : String(Number(n.toFixed(3)));
}

/** 由 spec 阈值拼出人类可读的告警提示，如 "warn <20 / crit >55"。 */
function thresholdHint(sensor: SensorSnapshotSensor): string {
  const s = sensor.spec;
  if (!s) return "—";
  const parts: string[] = [];
  if (s.warn_low != null) parts.push(`warn <${fmt(s.warn_low)}`);
  if (s.warn_high != null) parts.push(`warn >${fmt(s.warn_high)}`);
  if (s.crit_low != null) parts.push(`crit <${fmt(s.crit_low)}`);
  if (s.crit_high != null) parts.push(`crit >${fmt(s.crit_high)}`);
  return parts.length > 0 ? parts.join(" / ") : "无阈值";
}

const COLUMNS: ColumnsType<SensorSnapshotSensor> = [
  {
    title: "传感器",
    dataIndex: "label",
    key: "label",
    width: 220,
    render: (_: string, r) => (
      <div>
        <Text strong>{r.label}</Text>
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.sensor_type}
          </Text>
        </div>
      </div>
    ),
  },
  {
    title: "当前值",
    dataIndex: "value",
    key: "value",
    width: 140,
    render: (_: number, r) => (
      <Space size={4}>
        <Text strong style={{ fontSize: 15 }}>
          {fmt(r.value)}
        </Text>
        {r.unit && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.unit}
          </Text>
        )}
      </Space>
    ),
  },
  {
    title: "状态",
    dataIndex: "status",
    key: "status",
    width: 90,
    render: (_: SensorStatus, r) => (
      <Tag color={STATUS_META[r.status].color}>{STATUS_META[r.status].label}</Tag>
    ),
  },
  {
    title: "量程",
    key: "range",
    width: 150,
    render: (_, r) =>
      r.spec && r.spec.min != null && r.spec.max != null ? (
        <Text type="secondary" style={{ fontSize: 13 }}>
          {fmt(r.spec.min)} – {fmt(r.spec.max)}
          {r.unit ? ` ${r.unit}` : ""}
        </Text>
      ) : (
        <Text type="secondary">—</Text>
      ),
  },
  {
    title: "告警阈值",
    key: "threshold",
    render: (_, r) => (
      <Text type="secondary" style={{ fontSize: 13 }}>
        {thresholdHint(r)}
      </Text>
    ),
  },
  {
    title: "上报频率",
    key: "hz",
    width: 110,
    render: (_, r) =>
      r.spec?.sample_hz_upload != null ? (
        <Text type="secondary" style={{ fontSize: 13 }}>
          {fmt(r.spec.sample_hz_upload)} Hz
        </Text>
      ) : (
        <Text type="secondary">—</Text>
      ),
  },
  {
    title: "来源",
    dataIndex: "source",
    key: "source",
    width: 100,
    render: (_: string, r) => (
      <Tag color={r.source === "seed" ? "blue" : "default"}>
        {SOURCE_LABEL[r.source] || r.source}
      </Tag>
    ),
  },
];

export default function SensorOverview() {
  const { vehicle, loading: vehicleLoading } = useCurrentVehicle();
  const [snapshot, setSnapshot] = useState<SensorSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [domainFilter, setDomainFilter] = useState<string[]>([]);

  const vehicleId = vehicle?.id;

  const fetchSnapshot = useCallback(async () => {
    if (!vehicleId) return;
    setLoading(true);
    setFailed(false);
    try {
      const res = await vehicleService.getSensorSnapshot(vehicleId, {
        domain: domainFilter.length > 0 ? domainFilter.join(",") : undefined,
        include_spec: true,
      });
      setSnapshot(res);
    } catch {
      // 全局拦截器已用 message.error 弹出后端 detail，这里只置空并留出重试入口。
      setSnapshot(null);
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, [vehicleId, domainFilter]);

  useEffect(() => {
    fetchSnapshot();
  }, [fetchSnapshot]);

  const handleRefresh = useCallback(async () => {
    await fetchSnapshot();
    message.success("快照已刷新");
  }, [fetchSnapshot]);

  if (vehicleLoading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" tip="加载车辆信息…" />
      </div>
    );
  }

  if (!vehicle) {
    return (
      <Card className="cs-card">
        <Empty description="暂无车辆，请先在车辆档案中添加车辆" />
      </Card>
    );
  }

  const totalSensors =
    snapshot?.domains.reduce((acc, d) => acc + d.sensors.length, 0) ?? 0;
  const abnormalSensors =
    snapshot?.domains.reduce(
      (acc, d) => acc + d.sensors.filter((s) => s.status !== "normal").length,
      0,
    ) ?? 0;

  return (
    <div>
      {/* Header */}
      <Space
        style={{ justifyContent: "space-between", width: "100%", marginBottom: 16 }}
        wrap
      >
        <Space align="center">
          <DashboardOutlined style={{ fontSize: 28, color: "#3b82f6" }} />
          <Title level={3} style={{ margin: 0 }}>
            传感器总览
          </Title>
          {/* 快照来自 seed 持久虚构车「小白」，后端恒 demo_mode=true → L2b。 */}
          <DemoBadge level="L2b" inline />
        </Space>
        <Space wrap>
          <Select
            mode="multiple"
            allowClear
            placeholder="按域筛选（缺省全部 6 域）"
            style={{ minWidth: 240 }}
            value={domainFilter}
            onChange={(v: string[]) => setDomainFilter(v)}
            options={DOMAIN_OPTIONS}
            maxTagCount="responsive"
          />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            刷新快照
          </Button>
        </Space>
      </Space>

      <Paragraph type="secondary" style={{ marginTop: -8, marginBottom: 16 }}>
        全车传感器当前快照：按 6 个域分组，每项信号展示当前值、registry 量程与
        warn / crit 阈值，以及该读数是取自库内还是回落到基线。
      </Paragraph>

      {failed && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="快照拉取失败"
          description="若提示「该车辆暂无传感器数据」，请先到「推演沙盘」生成模拟数据，再回到本页刷新。"
          action={
            <Button size="small" onClick={fetchSnapshot}>
              重试
            </Button>
          }
        />
      )}

      {/* 基线摘要 */}
      {snapshot && (
        <Card className="cs-card" style={{ marginBottom: 16 }} loading={loading}>
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Statistic
                title="基线健康分"
                value={snapshot.baseline.health_score}
                suffix={`/ 100 · ${snapshot.baseline.grade_label}`}
                valueStyle={{
                  color: snapshot.baseline.health_score >= 80 ? "#3f8600" : "#cf1322",
                }}
                prefix={<ThunderboltOutlined />}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title="信号总数"
                value={totalSensors}
                suffix={`项 / ${snapshot.domains.length} 域`}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title="异常信号"
                value={abnormalSensors}
                suffix="项"
                valueStyle={{ color: abnormalSensors > 0 ? "#cf1322" : "#3f8600" }}
              />
            </Col>
            <Col xs={12} md={6}>
              <div>
                <Text type="secondary" style={{ fontSize: 14 }}>
                  数据来源
                </Text>
                <div style={{ marginTop: 6 }}>
                  <Space size={6} wrap>
                    <Tag color="orange">{snapshot.provenance.badge_level}</Tag>
                    <Tag>{snapshot.provenance.origin}</Tag>
                    <Tag color="cyan">{snapshot.energy_type}</Tag>
                  </Space>
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  快照时间：{new Date(snapshot.as_of).toLocaleString("zh-CN")}
                </Text>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* 分域明细 */}
      {loading && !snapshot ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <Spin size="large" tip="加载传感器快照…" />
        </div>
      ) : !snapshot || snapshot.domains.length === 0 ? (
        <Card className="cs-card">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无传感器快照数据"
          />
        </Card>
      ) : (
        <Collapse
          defaultActiveKey={snapshot.domains.map((d) => d.domain)}
          items={snapshot.domains.map((d) => {
            const abnormal = d.sensors.filter((s) => s.status !== "normal").length;
            const score = snapshot.baseline.breakdown?.[d.domain];
            return {
              key: d.domain,
              label: (
                <Space size={8} wrap>
                  <Text strong>{d.label}</Text>
                  <Tag>{d.sensors.length} 项</Tag>
                  {score != null && <Tag color="blue">域得分 {fmt(score)}</Tag>}
                  {d.vhs_weight != null && d.vhs_weight > 0 && (
                    <Tag color="purple">VHS 权重 {fmt(d.vhs_weight)}</Tag>
                  )}
                  {abnormal > 0 && <Tag color="red">{abnormal} 项异常</Tag>}
                </Space>
              ),
              children: (
                <Table<SensorSnapshotSensor>
                  rowKey="sensor_type"
                  size="small"
                  pagination={false}
                  columns={COLUMNS}
                  dataSource={d.sensors}
                  scroll={{ x: 900 }}
                  onRow={(r) => ({
                    style:
                      r.status === "crit"
                        ? { background: "#fff1f0", borderLeft: "3px solid #cf1322" }
                        : r.status === "warn"
                          ? { background: "#fffbe6", borderLeft: "3px solid #faad14" }
                          : undefined,
                  })}
                />
              ),
            };
          })}
        />
      )}
    </div>
  );
}
