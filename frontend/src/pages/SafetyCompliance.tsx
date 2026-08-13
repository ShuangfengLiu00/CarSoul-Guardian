/**
 * 安全合规 /safety
 * 已接通真实合规闸门数据（Guardian `GET /api/safety/gate-stats` → carModel
 * `carmodel:/agent/compliance/gate-stats` 真实运行时拦截计数；脱敏样本来自
 * `GET /api/safety/samples`）。数据全部来自真实端点，无任何模拟/占位数据。
 *
 * 诚实数据纪律（沿用 services/safetyService.ts）：
 * - 计数字段为 `number | null`；`null` 才显示「取不到」，绝不把 null 渲染成 0。
 * - source !== "real" 或 data_status.code !== "ok_carmodel_gate_stats" 时，
 *   整页显示「合规计数暂不可用」，不展示任何数字。
 * - storage === "memory" 或 degraded_reason 非空时，加注「计数可能不全」。
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Card,
  Col,
  Empty,
  List,
  Row,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  SafetyCertificateOutlined,
  IdcardOutlined,
  GlobalOutlined,
  AlertOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  FieldTimeOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import {
  safetyService,
  type GateStatsResponse,
  type ComplianceSample,
} from "@/services/safetyService";
import { useRole, ROLE_DISCLOSURE, ROLE_LABELS } from "@/hooks";

const { Title, Text, Paragraph } = Typography;

interface GateMeta {
  key: keyof Pick<
    GateStatsResponse,
    "identity" | "geo" | "data_fraud" | "repair_mislead" | "safety_critical"
  >;
  label: string;
  desc: string;
  icon: React.ReactNode;
}

const GATE_META: GateMeta[] = [
  {
    key: "identity",
    label: "身份闸门",
    desc: "拦截非授权主体的车辆数据访问与操作指令",
    icon: <IdcardOutlined />,
  },
  {
    key: "geo",
    label: "地理闸门",
    desc: "约束跨区域数据出境与定位披露边界",
    icon: <GlobalOutlined />,
  },
  {
    key: "data_fraud",
    label: "数据欺诈闸门",
    desc: "识别并阻断伪造里程 / 篡改健康分",
    icon: <AlertOutlined />,
  },
  {
    key: "repair_mislead",
    label: "维修误导闸门",
    desc: "防止夸大或虚假的维修建议",
    icon: <ToolOutlined />,
  },
  {
    key: "safety_critical",
    label: "安全关键闸门",
    desc: "守住涉及行车安全的不可妥协红线",
    icon: <ThunderboltOutlined />,
  },
];

function fmtDateTime(s?: string | null): string {
  if (!s) return "-";
  return dayjs(s).format("YYYY-MM-DD HH:mm");
}

export default function SafetyCompliance() {
  const { role } = useRole();
  const d = ROLE_DISCLOSURE[role];

  const [stats, setStats] = useState<GateStatsResponse | null>(null);
  const [samples, setSamples] = useState<ComplianceSample[]>([]);
  const [samplesMeta, setSamplesMeta] = useState<{
    available: boolean;
    totalStored: number | null;
    coverage: number | null;
    retentionDays: number | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [statsRes, samplesRes] = await Promise.all([
        safetyService.gateStats(),
        safetyService.samples({ limit: 20 }).catch(() => null),
      ]);
      setStats(statsRes);
      if (samplesRes) {
        setSamples(samplesRes.samples ?? []);
        setSamplesMeta({
          available: samplesRes.available,
          totalStored: samplesRes.total_stored,
          coverage: samplesRes.coverage,
          retentionDays: samplesRes.retention_days,
        });
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const available =
    !!stats &&
    stats.source === "real" &&
    stats.data_status?.code === "ok_carmodel_gate_stats";

  const isMemory = stats?.storage === "memory";
  const degraded = !!stats?.degraded_reason;

  return (
    <div>
      {/* 客户角色视角横幅：切换角色后文案同步变化 */}
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={`当前视角：${ROLE_LABELS[role]}`}
        description={d.perspective}
      />

      {loading && (
        <Card>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      )}

      {!loading && error && (
        <Alert
          type="error"
          showIcon
          message="合规计数服务暂不可用"
          description="无法连接合规闸门计数服务，本页不展示任何数字。请稍后重试或联系管理员。"
        />
      )}

      {!loading && !error && !available && (
        <Alert
          type="warning"
          showIcon
          message="合规计数暂不可用"
          description="当前无法取得真实合规闸门计数（数据来源未就绪）。按诚实数据纪律，本页不展示任何数字，不渲染占位数据。"
        />
      )}

      {!loading && !error && available && stats && (
        <>
          {/* 总览 */}
          <Card style={{ marginBottom: 16 }}>
            <Row align="middle" gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Statistic
                  title="累计合规拦截"
                  value={stats.total ?? "取不到"}
                  suffix="次"
                  valueStyle={{ color: "#3b82f6", fontWeight: 700 }}
                />
              </Col>
              <Col xs={24} md={8}>
                <Space direction="vertical" size={2}>
                  <Text type="secondary">统计起始</Text>
                  <Text strong>
                    <FieldTimeOutlined /> {fmtDateTime(stats.since)}
                  </Text>
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Space direction="vertical" size={4}>
                  <Tag color={isMemory ? "orange" : "green"}>
                    {isMemory ? "计数可能不全（内存级）" : "已落盘（SQLite·可信）"}
                  </Tag>
                  {degraded && (
                    <Tooltip title={stats.degraded_reason ?? ""}>
                      <Tag color="orange">计数链路已知缺陷</Tag>
                    </Tooltip>
                  )}
                </Space>
              </Col>
            </Row>
            <Paragraph type="secondary" style={{ margin: "12px 0 0", fontSize: 12 }}>
              数据来源：{stats.data_source}
              {stats.updated_at ? ` · 最近一次拦截 ${fmtDateTime(stats.updated_at)}` : ""}
            </Paragraph>
          </Card>

          {/* 5 类闸门卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {GATE_META.map((g) => {
              const val = stats[g.key];
              return (
                <Col xs={24} sm={12} lg={8} key={g.key}>
                  <Card className="cs-card" style={{ height: "100%" }}>
                    <Space align="start" size={12}>
                      <div style={{ fontSize: 28, color: "#3b82f6" }}>{g.icon}</div>
                      <div>
                        <div style={{ fontWeight: 600 }}>{g.label}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {g.desc}
                        </Text>
                      </div>
                    </Space>
                    <div
                      style={{
                        fontSize: 36,
                        fontWeight: 800,
                        color: "#1f2937",
                        margin: "14px 0 0",
                      }}
                    >
                      {val == null ? "取不到" : val}
                      <span style={{ fontSize: 14, fontWeight: 400, color: "#9ca3af" }}> 次</span>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>

          {/* 脱敏样本（PIPL 合规留存） */}
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                合规拦截脱敏样本
                {samplesMeta?.available && (
                  <Tag color="blue">留存 {samplesMeta.totalStored ?? "?"} 条</Tag>
                )}
              </Space>
            }
          >
            {!samplesMeta?.available ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="脱敏样本暂不可用"
              />
            ) : samples.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无脱敏样本" />
            ) : (
              <List
                size="small"
                dataSource={samples}
                renderItem={(s) => (
                  <List.Item>
                    <Space>
                      <Tag color="volcano">{s.category}</Tag>
                      <Text>{s.masked}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {fmtDateTime(s.created_at)}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            )}
            {samplesMeta && (
              <Paragraph type="secondary" style={{ margin: "12px 0 0", fontSize: 12 }}>
                样本为 PIPL 范围内唯一合法的明细留存形式：原始问句不可见、不可反推。
                {samplesMeta.coverage != null &&
                  ` 覆盖完整度 ${(samplesMeta.coverage * 100).toFixed(0)}%`}
                {samplesMeta.retentionDays != null &&
                  ` · 留存 ${samplesMeta.retentionDays} 天`}
              </Paragraph>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
