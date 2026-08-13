/**
 * 进化引擎 /evolution
 * 已接通真实进化引擎数据（Guardian `/api/governance/evolution/*`，后端由
 * carsoul_agent.observation.* 真实引擎逻辑支撑）：
 *   - dashboard()：经验挖掘 / 反思引擎 / 技能进化 / 评估 / 进化记忆 真实指标
 *   - runCycle()：触发一次真实进化周期（处理真实 Agent 观测，非演示数据）
 *   - timeline()：真实进化里程碑
 * 数据全部来自真实端点。当前若无周期运行，指标为真实 0 / 空——按诚实数据
 * 纪律显示「尚未产生数据」，绝不灌 seed 演示数据、不渲染占位数字。
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  List,
  Row,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Timeline,
  Typography,
  message,
} from "antd";
import {
  RocketOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  FieldTimeOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import {
  evolutionService,
  type EvolutionDashboard,
  type EvolutionTimelineEntry,
} from "@/services/evolutionService";

const { Title, Text, Paragraph } = Typography;

function fmtDateTime(s?: string | null): string {
  if (!s) return "-";
  return dayjs(s).format("YYYY-MM-DD HH:mm");
}

interface MetricCard {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
  hint: string;
}

export default function EvolutionEngine() {
  const [dash, setDash] = useState<EvolutionDashboard | null>(null);
  const [timeline, setTimeline] = useState<EvolutionTimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [cycling, setCycling] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [d, t] = await Promise.all([
        evolutionService.dashboard(),
        evolutionService.timeline(30).catch(() => ({ entries: [] })),
      ]);
      setDash(d);
      setTimeline(t.entries ?? []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRunCycle = async () => {
    setCycling(true);
    try {
      const res = await evolutionService.runCycle();
      message.success(
        res.success
          ? `周期 ${res.cycle_id} 完成：挖掘 ${res.experiences_mined} 经验 / ${res.patterns_discovered} 模式 / 进化 ${res.skills_evolved} 技能`
          : `周期 ${res.cycle_id} 结束（无新观测可处理）`,
      );
      await load();
    } catch {
      message.error("进化周期运行失败");
    } finally {
      setCycling(false);
    }
  };

  const metrics: MetricCard[] = dash
    ? [
        {
          label: "经验挖掘",
          value: dash.experience.total_cases,
          icon: <ExperimentOutlined />,
          hint: `模式 ${dash.experience.total_patterns ?? 0} · 均置信 ${(dash.experience.avg_confidence ?? 0).toFixed(2)}`,
        },
        {
          label: "反思引擎",
          value: dash.reflection.total_reflections,
          icon: <NodeIndexOutlined />,
          hint: `成功率 ${(dash.reflection.success_rate ?? 0).toFixed(2)} · 高优 ${dash.reflection.high_priority_count ?? 0}`,
        },
        {
          label: "技能进化",
          value: dash.skill_evolution.tracked_skills,
          icon: <ThunderboltOutlined />,
          hint: `提案 ${dash.skill_evolution.pending_proposals ?? 0} · 已部署 ${dash.skill_evolution.deployed_versions ?? 0}`,
        },
        {
          label: "评估",
          value: dash.evaluation.total_evaluations,
          icon: <DatabaseOutlined />,
          hint: `反馈 ${dash.evaluation.feedback_count ?? 0}`,
        },
        {
          label: "进化记忆",
          value: dash.evolution_memory.total_milestones,
          icon: <FieldTimeOutlined />,
          hint: `智能体 ${dash.evolution_memory.unique_agents ?? 0}`,
        },
      ]
    : [];

  return (
    <div>
      {/* 顶部：标题 + 真实进化周期控制 */}
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
        <Space align="center" size="middle">
          <Title level={4} style={{ margin: 0 }}>
            <RocketOutlined style={{ marginRight: 8, color: "#a855f7" }} />
            进化引擎
          </Title>
          {dash && (
            <Tag color={dash.engine_enabled ? "green" : "default"}>
              {dash.engine_enabled ? "引擎已启用" : "引擎未启用"}
            </Tag>
          )}
        </Space>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          loading={cycling}
          onClick={handleRunCycle}
        >
          运行进化周期
        </Button>
      </div>

      {loading && <Card><Skeleton active paragraph={{ rows: 8 }} /></Card>}

      {!loading && error && (
        <Alert
          type="error"
          showIcon
          message="进化引擎服务暂不可用"
          description="无法连接进化引擎，本页不展示任何数字。请稍后重试或联系管理员。"
        />
      )}

      {!loading && !error && dash && (
        <>
          {/* 总览指标 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={12} lg={8}>
              <Card className="cs-card">
                <Statistic title="累计进化周期" value={dash.total_cycles} />
                <Paragraph type="secondary" style={{ margin: "8px 0 0", fontSize: 12 }}>
                  {dash.last_cycle
                    ? `上次：${fmtDateTime(dash.last_cycle.completed_at)}`
                    : "尚无运行记录"}
                </Paragraph>
              </Card>
            </Col>
            {metrics.map((m) => (
              <Col xs={24} sm={12} lg={8} key={m.label}>
                <Card className="cs-card" style={{ height: "100%" }}>
                  <Space align="start" size={12}>
                    <div style={{ fontSize: 26, color: "#a855f7" }}>{m.icon}</div>
                    <div>
                      <div style={{ fontWeight: 600 }}>{m.label}</div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{m.hint}</Text>
                    </div>
                  </Space>
                  <div style={{ fontSize: 34, fontWeight: 800, color: "#1f2937", margin: "12px 0 0" }}>
                    {m.value ?? 0}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>

          {/* 上次周期详情 */}
          <Card
            title={<Space><PlayCircleOutlined /> 上次进化周期</Space>}
            style={{ marginBottom: 16 }}
          >
            {!dash.last_cycle ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="进化闭环尚未产生任何周期数据（真实状态）"
              />
            ) : (
              <Space direction="vertical" size={4}>
                <Text strong>周期 {dash.last_cycle.cycle_id}</Text>
                <Text type="secondary">
                  {fmtDateTime(dash.last_cycle.started_at)} → {fmtDateTime(dash.last_cycle.completed_at)}
                  {" · "}
                  {dash.last_cycle.success ? "成功" : "未成功"}
                </Text>
                {dash.last_cycle.summary && (
                  <Paragraph style={{ margin: "4px 0 0" }}>{dash.last_cycle.summary}</Paragraph>
                )}
              </Space>
            )}
          </Card>

          {/* 进化时间线（真实里程碑） */}
          <Card title={<Space><FieldTimeOutlined /> 进化时间线</Space>}>
            {timeline.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无进化里程碑"
              />
            ) : (
              <Timeline
                items={timeline.map((e) => ({
                  color:
                    e.impact_level === "high"
                      ? "green"
                      : e.impact_level === "low"
                      ? "gray"
                      : "blue",
                  children: (
                    <div>
                      <Text strong>{e.title}</Text>
                      <Tag style={{ marginLeft: 8, fontSize: 11 }}>{e.event_type}</Tag>
                      <div style={{ fontSize: 12, color: "#9ca3af" }}>{fmtDateTime(e.timestamp)}</div>
                      {e.description && (
                        <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                          {e.description}
                        </div>
                      )}
                    </div>
                  ),
                }))}
              />
            )}
          </Card>
        </>
      )}
    </div>
  );
}
