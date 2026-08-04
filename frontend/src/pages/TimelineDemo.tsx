/**
 * TimelineDemo — 第8步「一辆车的一生」杀手 Demo
 *
 * 3 年叙事时间线：2025 诞生 → 2026 用车 → 2027 异常
 * - 年份滑块切换阶段
 * - 记忆流侧栏展示逐年记忆条目
 * - 异常阶段展示 Agent 协作视图
 * - 终幕报告卡（每个数字可追溯）
 * - 演示模式角标（红线2合规）
 */
import { useState, useEffect } from "react";
import {
  Card, Row, Col, Tag, Statistic, Timeline, Badge, Button, Space,
  Divider, Typography, Progress, Collapse, Empty, Spin,
} from "antd";
import {
  CarOutlined, ThunderboltOutlined, AlertOutlined, HeartOutlined,
  RobotOutlined, ExperimentOutlined, SafetyCertificateOutlined,
  DollarOutlined, HistoryOutlined, CheckCircleOutlined, WarningOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import { timelineService } from "@/services/timelineService";
import { TIMELINE_DEMO_DATA } from "@/services/timelineData";
import type { LifeStoryResponse, TimelinePhase, TraceableItem } from "@/services/timelineTypes";
import { DemoBadge } from "@/components";

const { Title, Text, Paragraph } = Typography;

// Event type config
const EVENT_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  birth: { color: "purple", icon: <CarOutlined /> },
  mileage: { color: "blue", icon: <ThunderboltOutlined /> },
  maintenance: { color: "orange", icon: <CheckCircleOutlined /> },
  warning: { color: "gold", icon: <WarningOutlined /> },
  anomaly: { color: "red", icon: <AlertOutlined /> },
  milestone: { color: "green", icon: <SafetyCertificateOutlined /> },
};

// Agent config
const AGENT_CONFIG: Record<string, { icon: React.ReactNode; color: string }> = {
  battery: { icon: <ThunderboltOutlined />, color: "#ff4d4f" },
  diagnosis: { icon: <ExperimentOutlined />, color: "#faad14" },
  safety: { icon: <SafetyCertificateOutlined />, color: "#52c41a" },
  value: { icon: <DollarOutlined />, color: "#1890ff" },
};

const SEVERITY_CONFIG: Record<string, { color: string; label: string }> = {
  info: { color: "blue", label: "信息" },
  warning: { color: "orange", label: "警告" },
  critical: { color: "red", label: "严重" },
};

const SOURCE_CONFIG: Record<string, { color: string; label: string }> = {
  memory: { color: "purple", label: "记忆" },
  telemetry: { color: "cyan", label: "遥测" },
  agent: { color: "magenta", label: "Agent" },
};

export default function TimelineDemo() {
  const [data, setData] = useState<LifeStoryResponse>(TIMELINE_DEMO_DATA);
  const [loading, setLoading] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [showReport, setShowReport] = useState(false);
  const [tracedItem, setTracedItem] = useState<TraceableItem | null>(null);

  useEffect(() => {
    setLoading(true);
    timelineService.lifeStory().then((res) => {
      setData(res);
      setLoading(false);
    });
  }, []);

  const phase: TimelinePhase | undefined = data.phases[phaseIndex];

  if (loading || !phase) {
    return (
      <div style={{ textAlign: "center", padding: "120px 0" }}>
        <Spin size="large" tip="加载车辆生命故事..." />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "0 16px 48px" }}>
      <DemoBadge />
      {/* ===== Header ===== */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <Space>
          <Title level={3} style={{ margin: 0 }}>
            一辆车的一生
          </Title>
          <Text type="secondary">{data.vehicle.name} · {data.vehicle.brand} {data.vehicle.model}</Text>
        </Space>
        <DemoBadge inline />
      </div>

      {/* ===== Year Slider ===== */}
      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 16, flexWrap: "wrap" }}>
          {data.phases.map((p, i) => (
            <Button
              key={p.year}
              type={i === phaseIndex ? "primary" : "default"}
              size="large"
              onClick={() => { setPhaseIndex(i); setShowReport(false); }}
              style={{
                minWidth: 160,
                borderRadius: 8,
                borderColor: i === phaseIndex ? p.color : undefined,
                background: i === phaseIndex ? p.color : undefined,
              }}
            >
              <Space>
                <span style={{ fontSize: 18, fontWeight: 700 }}>{p.year}</span>
                <span>{p.label}</span>
              </Space>
            </Button>
          ))}
          <Button
            size="large"
            type={showReport ? "primary" : "default"}
            ghost={showReport}
            onClick={() => setShowReport(true)}
            style={{ minWidth: 160, borderRadius: 8 }}
          >
            <Space>
              <HeartOutlined />
              终幕报告
            </Space>
          </Button>
        </div>
      </Card>

      {/* ===== Main Content ===== */}
      {showReport ? (
        <ReportCard report={data.report} onTrace={setTracedItem} />
      ) : (
        <Row gutter={[24, 24]}>
          {/* Left: Phase content + events */}
          <Col xs={24} lg={16}>
            <PhaseDetail phase={phase} />

            {/* Agent Collaboration (only for anomaly phase) */}
            {phase.agent_collaboration?.triggered && (
              <AgentCollaborationView collab={phase.agent_collaboration} />
            )}
          </Col>

          {/* Right: Memory flow sidebar */}
          <Col xs={24} lg={8}>
            <MemoryFlow phase={phase} allPhases={data.phases} />
          </Col>
        </Row>
      )}

      {/* ===== Trace Detail Modal ===== */}
      {tracedItem && (
        <Card
          size="small"
          style={{
            position: "fixed", bottom: 24, right: 24, maxWidth: 400, zIndex: 1000,
            boxShadow: "0 8px 24px rgba(0,0,0,0.15)", borderRadius: 12,
          }}
          title={<Space><Tag color={SOURCE_CONFIG[tracedItem.source_type]?.color}>来源: {SOURCE_CONFIG[tracedItem.source_type]?.label}</Tag>{tracedItem.label}</Space>}
          extra={<Button size="small" type="text" onClick={() => setTracedItem(null)}>关闭</Button>}
        >
          <Statistic title="数值" value={tracedItem.value} />
          <Divider style={{ margin: "12px 0" }} />
          <Text type="secondary" style={{ fontSize: 13 }}>
            <strong>来源 ID:</strong> {tracedItem.source_id}
          </Text>
          <br />
          <Text style={{ fontSize: 13 }}>{tracedItem.source_description}</Text>
        </Card>
      )}
    </div>
  );
}


// ------------------------------------------------------------------ //
//  Phase Detail — telemetry + events timeline
// ------------------------------------------------------------------ //
function PhaseDetail({ phase }: { phase: TimelinePhase }) {
  const { telemetry } = phase;
  return (
    <>
      <Card
        title={
          <Space>
            <Badge color={phase.color} />
            <span style={{ fontSize: 18, fontWeight: 700 }}>{phase.year} · {phase.label}</span>
          </Space>
        }
        style={{ marginBottom: 24, borderRadius: 12, borderTop: `3px solid ${phase.color}` }}
      >
        <Paragraph type="secondary">{phase.summary}</Paragraph>

        {/* Telemetry Stats */}
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8}>
            <Statistic
              title="SOH 电池健康度"
              value={telemetry.soh}
              suffix="%"
              valueStyle={{ color: telemetry.soh > 95 ? "#52c41a" : telemetry.soh > 90 ? "#faad14" : "#ff4d4f" }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic title="累计里程" value={telemetry.mileage} suffix="km" />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="电池温度"
              value={telemetry.battery_temp}
              suffix="°C"
              valueStyle={{ color: telemetry.battery_temp > 40 ? "#ff4d4f" : "#1890ff" }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="充电速度"
              value={Math.round(telemetry.charging_speed_ratio * 100)}
              suffix="%"
              valueStyle={{ color: telemetry.charging_speed_ratio < 0.9 ? "#ff4d4f" : "#52c41a" }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic title="充电循环" value={telemetry.charge_cycles} suffix="次" />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="快充占比"
              value={Math.round(telemetry.fast_charge_ratio * 100)}
              suffix="%"
              valueStyle={{ color: telemetry.fast_charge_ratio > 0.5 ? "#faad14" : "#1890ff" }}
            />
          </Col>
        </Row>
      </Card>

      {/* Events Timeline */}
      <Card title="生命事件" style={{ marginBottom: 24, borderRadius: 12 }}>
        <Timeline
          items={phase.events.map((evt) => {
            const cfg = EVENT_CONFIG[evt.event_type] || EVENT_CONFIG.milestone;
            return {
              color: cfg.color,
              dot: cfg.icon,
              children: (
                <div>
                  <Space>
                    <Text strong>{evt.title}</Text>
                    <Tag color={cfg.color}>{evt.date}</Tag>
                    {evt.mileage !== null && (
                      <Text type="secondary" style={{ fontSize: 12 }}>{evt.mileage.toLocaleString()} km</Text>
                    )}
                  </Space>
                  <br />
                  <Text type="secondary" style={{ fontSize: 13 }}>{evt.description}</Text>
                </div>
              ),
            };
          })}
        />
      </Card>
    </>
  );
}


// ------------------------------------------------------------------ //
//  Agent Collaboration View
// ------------------------------------------------------------------ //
function AgentCollaborationView({ collab }: { collab: NonNullable<TimelinePhase["agent_collaboration"]> }) {
  return (
    <Card
      title={
        <Space>
          <RobotOutlined style={{ color: "#722ed1" }} />
          <span>Guardian 召集 · Agent 协作诊断</span>
          <Tag color="red">已触发</Tag>
        </Space>
      }
      style={{ marginBottom: 24, borderRadius: 12, border: "1px solid #ffccc7" }}
    >
      {/* Trigger reason */}
      <Card size="small" style={{ marginBottom: 16, background: "#fff2f0", border: "1px solid #ffccc7" }}>
        <Text strong><AlertOutlined /> 触发原因：</Text>
        <br />
        <Text>{collab.trigger_reason}</Text>
      </Card>

      {/* Guardian Summary */}
      {collab.guardian_summary && (
        <Card size="small" style={{ marginBottom: 16, background: "#f9f0ff", border: "1px solid #d3adf7" }}>
          <Text strong style={{ color: "#722ed1" }}><RobotOutlined /> Guardian 汇总：</Text>
          <br />
          <Text>{collab.guardian_summary}</Text>
        </Card>
      )}

      {/* Agent Findings Grid */}
      <Row gutter={[16, 16]}>
        {collab.findings.map((f, i) => {
          const cfg = AGENT_CONFIG[f.agent_name] || AGENT_CONFIG.diagnosis;
          const sev = SEVERITY_CONFIG[f.severity] || SEVERITY_CONFIG.info;
          return (
            <Col xs={24} sm={12} key={i}>
              <Card
                size="small"
                style={{ borderRadius: 8, borderTop: `2px solid ${cfg.color}` }}
                title={
                  <Space>
                    <span style={{ color: cfg.color, fontSize: 16 }}>{cfg.icon}</span>
                    <Text strong>{f.agent_name}</Text>
                    <Tag color={sev.color}>{sev.label}</Tag>
                  </Space>
                }
              >
                <Paragraph style={{ fontSize: 13, marginBottom: 8 }}>{f.finding}</Paragraph>
                <Divider style={{ margin: "8px 0" }} />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  <CheckCircleOutlined /> 建议：{f.recommendation}
                </Text>
                <br />
                <Progress
                  percent={Math.round(f.confidence * 100)}
                  size="small"
                  format={(p) => `置信度 ${p}%`}
                  strokeColor={cfg.color}
                />
              </Card>
            </Col>
          );
        })}
      </Row>
    </Card>
  );
}


// ------------------------------------------------------------------ //
//  Memory Flow Sidebar
// ------------------------------------------------------------------ //
function MemoryFlow({ phase, allPhases }: { phase: TimelinePhase; allPhases: TimelinePhase[] }) {
  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>记忆流</span>
        </Space>
      }
      style={{ borderRadius: 12, position: "sticky", top: 80 }}
    >
      {/* Current phase memories */}
      <div style={{ marginBottom: 16 }}>
        <Tag color={phase.color} style={{ marginBottom: 8 }}>{phase.year} · {phase.label}</Tag>
        {phase.memories.map((mem) => (
          <MemoryCard key={mem.id} mem={mem} />
        ))}
      </div>

      <Divider style={{ margin: "12px 0" }} />

      {/* Other phases summary */}
      <Text type="secondary" strong>其他阶段记忆</Text>
      {allPhases
        .filter((p) => p.year !== phase.year)
        .map((p) => (
          <div key={p.year} style={{ marginTop: 8 }}>
            <Tag color={p.color} style={{ marginBottom: 4 }}>{p.year} · {p.label}（{p.memories.length}条）</Tag>
          </div>
        ))}
    </Card>
  );
}

function MemoryCard({ mem }: { mem: LifeStoryResponse["phases"][0]["memories"][0] }) {
  const typeColor: Record<string, string> = {
    event: "blue", habit: "cyan", warning: "orange",
    recovery: "green", anomaly: "red",
  };
  return (
    <Card
      size="small"
      hoverable
      style={{ marginBottom: 8, borderRadius: 6, borderLeft: `3px solid ${typeColor[mem.event_type] || "#d9d9d9"}` }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <Tag color={typeColor[mem.event_type] || "default"} style={{ fontSize: 11 }}>{mem.event_type}</Tag>
        <Text type="secondary" style={{ fontSize: 11 }}>{mem.occurred_at.slice(0, 10)}</Text>
      </div>
      <Text style={{ fontSize: 13 }}>{mem.summary}</Text>
      {mem.impact_delta !== 0 && (
        <div style={{ marginTop: 4 }}>
          <Text type={mem.impact_delta < 0 ? "danger" : "success"} style={{ fontSize: 11 }}>
            影响: {mem.impact_delta > 0 ? "+" : ""}{mem.impact_delta}
          </Text>
        </div>
      )}
    </Card>
  );
}


// ------------------------------------------------------------------ //
//  Report Card — Final report with traceable items
// ------------------------------------------------------------------ //
function ReportCard({
  report,
  onTrace,
}: {
  report: LifeStoryResponse["report"];
  onTrace: (item: TraceableItem) => void;
}) {
  const { used_car_valuation: val } = report;
  return (
    <div>
      {/* Report Header */}
      <Card style={{ marginBottom: 24, borderRadius: 12, textAlign: "center", background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
        <Title level={2} style={{ color: "#fff", margin: 0 }}>终幕报告</Title>
        <Text style={{ color: "rgba(255,255,255,0.8)" }}>一辆车的一生 · 健康评估与价值预测</Text>
      </Card>

      {/* Key Metrics */}
      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable onClick={() => onTrace(report.traceable_items[0])} style={{ borderRadius: 12, textAlign: "center" }}>
            <Statistic
              title="健康评分"
              value={report.health_score}
              suffix={`/ 100`}
              valueStyle={{ color: "#52c41a", fontSize: 36 }}
            />
            <Tag color="green" style={{ marginTop: 8 }}>{report.health_grade}</Tag>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable onClick={() => onTrace(report.traceable_items[1])} style={{ borderRadius: 12, textAlign: "center" }}>
            <Statistic
              title="12个月电池衰减"
              value={report.battery_degradation_12m}
              prefix="+"
              suffix="%"
              valueStyle={{ color: "#faad14", fontSize: 36 }}
            />
            <Tag color="orange" style={{ marginTop: 8 }}>预计衰减</Tag>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable onClick={() => onTrace(report.traceable_items[3])} style={{ borderRadius: 12, textAlign: "center" }}>
            <Statistic
              title="优化后估值"
              value={val.projected}
              suffix="万元"
              valueStyle={{ color: "#1890ff", fontSize: 36 }}
            />
            <Tag color="blue" style={{ marginTop: 8 }}>+{val.delta} 万元</Tag>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card style={{ borderRadius: 12, textAlign: "center" }}>
            <Statistic
              title="当前估值"
              value={val.current}
              suffix="万元"
              valueStyle={{ color: "#666", fontSize: 36 }}
            />
            <Tag style={{ marginTop: 8 }}>行驶 26,500 km</Tag>
          </Card>
        </Col>
      </Row>

      {/* Charging Strategy */}
      <Card
        title={<Space><ThunderboltOutlined /> 充电策略建议</Space>}
        style={{ marginTop: 24, borderRadius: 12 }}
      >
        <Paragraph>{report.charging_strategy}</Paragraph>
      </Card>

      {/* Traceable Items */}
      <Card
        title={<Space><InfoCircleOutlined /> 可追溯指标（点击查看来源）</Space>}
        style={{ marginTop: 24, borderRadius: 12 }}
      >
        <Row gutter={[16, 16]}>
          {report.traceable_items.map((item, i) => {
            const src = SOURCE_CONFIG[item.source_type] || SOURCE_CONFIG.memory;
            return (
              <Col xs={24} sm={12} md={8} key={i}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => onTrace(item)}
                  style={{ borderRadius: 8, cursor: "pointer" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>{item.label}</Text>
                    <Tag color={src.color} style={{ fontSize: 11 }}>{src.label}</Tag>
                  </div>
                  <Text strong style={{ fontSize: 18 }}>{item.value}</Text>
                  <br />
                  <Text type="secondary" ellipsis style={{ fontSize: 11 }}>
                    {item.source_description}
                  </Text>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>
    </div>
  );
}
