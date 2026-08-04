/**
 * Agent Governance Dashboard — 智能体治理控制台.
 *
 * Visualises all governance modules:
 *  - Agent Registry (10 agents with metadata, state, stats)
 *  - Skill Registry (skills as first-class entities)
 *  - MCP Registry (vehicle capability interfaces)
 *  - Workflow Permissions (per-workflow access control)
 *  - Sandbox (safe execution environment)
 *  - Version Manager (canary/stable rollout)
 *  - AgentLoop Observation Layer (trace, evaluation, optimization, evolution)
 */
import { useEffect, useState, useCallback } from "react";
import {
  Card,
  Tabs,
  Table,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Button,
  Descriptions,
  Timeline,
  Progress,
  Badge,
  Empty,
  Skeleton,
  Typography,
  Tooltip,
  message,
  Collapse,
} from "antd";
import {
  RobotOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  LockOutlined,
  SafetyOutlined,
  BranchesOutlined,
  EyeOutlined,
  ExperimentOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { governanceService } from "@/services/governanceService";
import type {
  AgentMetadata,
  SkillMetadata,
  MCPInterface,
  WorkflowPermission,
  SandboxStatus,
  AgentVersion,
  TraceRecord,
  TokenStats,
  OptimizationAction,
  EvolutionSummary,
} from "@/services/governanceService";

const { Title, Text, Paragraph } = Typography;

// ------------------------------------------------------------------
//  Helpers
// ------------------------------------------------------------------
const stateColor: Record<string, string> = {
  ACTIVE: "success",
  BUSY: "processing",
  ERROR: "error",
  UPDATING: "warning",
  OFFLINE: "default",
};

const categoryColor: Record<string, string> = {
  analysis: "blue",
  prediction: "purple",
  detection: "orange",
  diagnosis: "red",
  general: "default",
};

const versionStatusColor: Record<string, string> = {
  stable: "success",
  canary: "warning",
  deprecated: "error",
  draft: "default",
};

const priorityColor: Record<string, string> = {
  high: "red",
  medium: "orange",
  low: "blue",
};

function fmtTime(s?: string | null): string {
  if (!s) return "-";
  const d = new Date(s);
  if (isNaN(d.getTime())) return s;
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

// ------------------------------------------------------------------
//  Sub-component: Overview tab
// ------------------------------------------------------------------
function OverviewTab({ overview, loading }: { overview: any; loading: boolean }) {
  if (loading) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (!overview) return <Empty description="暂无数据" />;

  const health = overview.fleet_health || {};
  const agents: AgentMetadata[] = overview.agents || [];

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="注册 Agent"
              value={overview.registry?.agent_count ?? 0}
              prefix={<RobotOutlined style={{ color: "#3b82f6" }} />}
              valueStyle={{ color: "#3b82f6", fontSize: 28 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              活跃: {overview.registry?.active_count ?? 0}
            </Text>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="活跃 / 总数"
              value={health.active ?? 0}
              suffix={`/ ${health.total ?? 0}`}
              prefix={<CheckCircleOutlined style={{ color: "#10b981" }} />}
              valueStyle={{ color: "#10b981", fontSize: 28 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              忙碌: {health.busy ?? 0} | 错误: {health.error ?? 0}
            </Text>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="Judge Agent"
              value="就绪"
              prefix={<SafetyOutlined style={{ color: "#8b5cf6" }} />}
              valueStyle={{ color: "#8b5cf6", fontSize: 28 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              冲突仲裁引擎
            </Text>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="治理模块"
              value={7}
              prefix={<ExperimentOutlined style={{ color: "#f59e0b" }} />}
              valueStyle={{ color: "#f59e0b", fontSize: 28 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              全部在线
            </Text>
          </Card>
        </Col>
      </Row>

      <Card className="cs-card" title={<Space><RobotOutlined /> Agent 舰队状态</Space>} style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          {agents.map((agent) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={agent.agent_id}>
              <Card size="small" className="cs-card" style={{ marginBottom: 8 }}>
                <Space direction="vertical" size={4} style={{ width: "100%" }}>
                  <Space>
                    <Badge status={stateColor[agent.state] as any} />
                    <Text strong style={{ fontSize: 14 }}>{agent.name}</Text>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>{agent.role}</Text>
                  <Space size={4} wrap>
                    <Tag color="blue" style={{ fontSize: 11 }}>v{agent.version}</Tag>
                    <Tag style={{ fontSize: 11 }}>{agent.capabilities?.length ?? 0} 能力</Tag>
                  </Space>
                  {agent.stats && (
                    <div style={{ marginTop: 4 }}>
                      <Progress
                        percent={Math.round((agent.stats.success_rate ?? 0) * 100)}
                        size="small"
                        strokeColor={agent.stats.success_rate >= 0.9 ? "#10b981" : agent.stats.success_rate >= 0.7 ? "#f59e0b" : "#ef4444"}
                        format={(p) => `${p}%`}
                      />
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        调用 {agent.stats.total_invocations ?? 0} 次
                      </Text>
                    </div>
                  )}
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------
//  Sub-component: Agents tab
// ------------------------------------------------------------------
function AgentsTab({ agents, loading }: { agents: AgentMetadata[]; loading: boolean }) {
  const columns = [
    {
      title: "Agent",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: AgentMetadata) => (
        <Space direction="vertical" size={0}>
          <Space>
            <Badge status={stateColor[record.state] as any} />
            <Text strong>{text}</Text>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.agent_id}</Text>
        </Space>
      ),
    },
    {
      title: "角色",
      dataIndex: "role",
      key: "role",
      render: (text: string) => <Text style={{ fontSize: 13 }}>{text}</Text>,
    },
    {
      title: "版本",
      dataIndex: "version",
      key: "version",
      render: (v: string) => <Tag color="blue">v{v}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "state",
      key: "state",
      render: (s: string) => <Tag color={stateColor[s] || "default"}>{s}</Tag>,
    },
    {
      title: "能力",
      dataIndex: "capabilities",
      key: "capabilities",
      render: (caps: string[]) => (
        <Space size={4} wrap>
          {caps?.slice(0, 3).map((c) => (
            <Tag key={c} style={{ fontSize: 11 }}>{c}</Tag>
          ))}
          {caps?.length > 3 && <Tag>+{caps.length - 3}</Tag>}
        </Space>
      ),
    },
    {
      title: "调用统计",
      key: "stats",
      render: (_: any, record: AgentMetadata) => {
        const s = record.stats;
        if (!s) return "-";
        const rate = Math.round((s.success_rate ?? 0) * 100);
        return (
          <Space direction="vertical" size={0}>
            <Text style={{ fontSize: 12 }}>调用 {s.total_invocations ?? 0} | 错误 {s.error_count ?? 0}</Text>
            <Progress percent={rate} size="small" strokeColor={rate >= 90 ? "#10b981" : rate >= 70 ? "#f59e0b" : "#ef4444"} />
          </Space>
        );
      },
    },
    {
      title: "最后调用",
      dataIndex: ["stats", "last_invoked"],
      key: "last_invoked",
      render: (t: string | null) => <Text type="secondary" style={{ fontSize: 12 }}>{fmtTime(t)}</Text>,
    },
  ];

  return (
    <Card className="cs-card">
      {loading ? (
        <Skeleton active />
      ) : (
        <Table
          dataSource={agents}
          columns={columns}
          rowKey="agent_id"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          expandable={{
            expandedRowRender: (record) => (
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="描述" span={2}>{record.description}</Descriptions.Item>
                <Descriptions.Item label="权限" span={2}>
                  <Space wrap>
                    {record.permissions?.map((p) => <Tag key={p}>{p}</Tag>)}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="输入数据">{record.input_data?.join(", ")}</Descriptions.Item>
                <Descriptions.Item label="注册时间">{fmtTime(record.registered_at)}</Descriptions.Item>
              </Descriptions>
            ),
          }}
        />
      )}
    </Card>
  );
}

// ------------------------------------------------------------------
//  Sub-component: Skills tab
// ------------------------------------------------------------------
function SkillsTab({ skills, loading }: { skills: SkillMetadata[]; loading: boolean }) {
  const columns = [
    {
      title: "技能",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: SkillMetadata) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.skill_id}</Text>
        </Space>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (text: string) => <Text style={{ fontSize: 13 }}>{text}</Text>,
    },
    {
      title: "关联 Agent",
      dataIndex: "agent_id",
      key: "agent_id",
      render: (a: string) => <Tag color="blue">{a}</Tag>,
    },
    {
      title: "类别",
      dataIndex: "category",
      key: "category",
      render: (c: string) => <Tag color={categoryColor[c] || "default"}>{c}</Tag>,
    },
    {
      title: "版本",
      dataIndex: "version",
      key: "version",
      render: (v: string) => <Tag>v{v}</Tag>,
    },
    {
      title: "调用条件",
      dataIndex: "call_conditions",
      key: "call_conditions",
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text style={{ fontSize: 12 }}>{text || "-"}</Text>
        </Tooltip>
      ),
    },
    {
      title: "统计",
      key: "stats",
      render: (_: any, record: SkillMetadata) => {
        const s = record.stats;
        if (!s) return "-";
        const rate = Math.round((s.success_rate ?? 0) * 100);
        return (
          <Space direction="vertical" size={0}>
            <Text style={{ fontSize: 12 }}>调用 {s.total_calls ?? 0}</Text>
            <Progress percent={rate} size="small" strokeColor={rate >= 90 ? "#10b981" : "#f59e0b"} />
          </Space>
        );
      },
    },
  ];

  return (
    <Card className="cs-card">
      {loading ? (
        <Skeleton active />
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Statistic title="总技能数" value={skills.length} prefix={<ThunderboltOutlined style={{ color: "#3b82f6" }} />} />
            </Col>
            <Col span={6}>
              <Statistic
                title="技能类别"
                value={new Set(skills.map((s) => s.category)).size}
                prefix={<ExperimentOutlined style={{ color: "#8b5cf6" }} />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总调用次数"
                value={skills.reduce((sum, s) => sum + (s.stats?.total_calls ?? 0), 0)}
                prefix={<SyncOutlined style={{ color: "#10b981" }} />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="关联 Agent"
                value={new Set(skills.map((s) => s.agent_id)).size}
                prefix={<RobotOutlined style={{ color: "#f59e0b" }} />}
              />
            </Col>
          </Row>
          <Table
            dataSource={skills}
            columns={columns}
            rowKey="skill_id"
            pagination={{ pageSize: 10, showSizeChanger: false }}
          />
        </>
      )}
    </Card>
  );
}

// ------------------------------------------------------------------
//  Sub-component: MCP tab
// ------------------------------------------------------------------
function MCPTab({ interfaces, loading }: { interfaces: MCPInterface[]; loading: boolean }) {
  const columns = [
    {
      title: "接口",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: MCPInterface) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.interface_id}</Text>
        </Space>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
    },
    {
      title: "类别",
      dataIndex: "category",
      key: "category",
      render: (c: string) => <Tag color="purple">{c}</Tag>,
    },
    {
      title: "端点",
      dataIndex: "endpoint",
      key: "endpoint",
      render: (ep: string, record: MCPInterface) => (
        <Space>
          <Tag color={record.method === "GET" ? "green" : "blue"}>{record.method}</Tag>
          <Text code style={{ fontSize: 12 }}>{ep}</Text>
        </Space>
      ),
    },
    {
      title: "安全级别",
      dataIndex: "security_level",
      key: "security_level",
      render: (s: string) => (
        <Tag color={s === "high" ? "red" : s === "medium" ? "orange" : "green"}>{s}</Tag>
      ),
    },
    {
      title: "统计",
      key: "stats",
      render: (_: any, record: MCPInterface) => {
        const s = record.stats;
        if (!s) return "-";
        return (
          <Space direction="vertical" size={0}>
            <Text style={{ fontSize: 12 }}>调用 {s.total_calls ?? 0}</Text>
            <Text style={{ fontSize: 12 }} type="secondary">
              延迟 {s.avg_latency_ms?.toFixed(0) ?? 0}ms
            </Text>
          </Space>
        );
      },
    },
  ];

  return (
    <Card className="cs-card">
      {loading ? (
        <Skeleton active />
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Statistic title="MCP 接口总数" value={interfaces.length} prefix={<ApiOutlined style={{ color: "#3b82f6" }} />} />
            </Col>
            <Col span={8}>
              <Statistic
                title="接口类别"
                value={new Set(interfaces.map((i) => i.category)).size}
                prefix={<ExperimentOutlined style={{ color: "#8b5cf6" }} />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="总调用次数"
                value={interfaces.reduce((sum, i) => sum + (i.stats?.total_calls ?? 0), 0)}
                prefix={<SyncOutlined style={{ color: "#10b981" }} />}
              />
            </Col>
          </Row>
          <Table
            dataSource={interfaces}
            columns={columns}
            rowKey="interface_id"
            pagination={{ pageSize: 10, showSizeChanger: false }}
          />
        </>
      )}
    </Card>
  );
}

// ------------------------------------------------------------------
//  Sub-component: Workflow Permissions tab
// ------------------------------------------------------------------
function PermissionsTab({ permissions, loading }: { permissions: WorkflowPermission[]; loading: boolean }) {
  return (
    <Card className="cs-card">
      {loading ? (
        <Skeleton active />
      ) : permissions.length === 0 ? (
        <Empty description="暂无工作流权限配置" />
      ) : (
        <Collapse
          items={permissions.map((perm) => ({
            key: perm.workflow_name,
            label: (
              <Space>
                <LockOutlined />
                <Text strong>{perm.workflow_name}</Text>
                <Tag color="blue">{perm.allowed_agents?.length ?? 0} Agents</Tag>
                <Tag color="purple">{perm.allowed_skills?.length ?? 0} Skills</Tag>
              </Space>
            ),
            children: (
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="描述">{perm.description}</Descriptions.Item>
                <Descriptions.Item label="允许的 Agent">
                  <Space wrap>
                    {perm.allowed_agents?.map((a) => <Tag key={a} color="green">{a}</Tag>)}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="允许的技能">
                  <Space wrap>
                    {perm.allowed_skills?.map((s) => <Tag key={s} color="blue">{s}</Tag>)}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="允许的数据">
                  <Space wrap>
                    {perm.allowed_data?.map((d) => <Tag key={d}>{d}</Tag>)}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="禁止操作">
                  <Space wrap>
                    {perm.denied_actions?.map((d) => <Tag key={d} color="red">{d}</Tag>)}
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            ),
          }))}
          defaultActiveKey={permissions[0]?.workflow_name}
        />
      )}
    </Card>
  );
}

// ------------------------------------------------------------------
//  Sub-component: Sandbox tab
// ------------------------------------------------------------------
function SandboxTab({ sandbox, loading }: { sandbox: SandboxStatus | null; loading: boolean }) {
  if (loading) return <Skeleton active />;
  if (!sandbox) return <Empty description="暂无沙箱数据" />;

  const config = sandbox.config || {};

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="活跃会话"
              value={sandbox.active_sessions ?? 0}
              prefix={<ExperimentOutlined style={{ color: "#3b82f6" }} />}
              valueStyle={{ color: "#3b82f6", fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="总执行次数"
              value={sandbox.total_executions ?? 0}
              prefix={<SyncOutlined style={{ color: "#10b981" }} />}
              valueStyle={{ color: "#10b981", fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="拦截次数"
              value={sandbox.blocked_attempts ?? 0}
              prefix={<ExclamationCircleOutlined style={{ color: "#ef4444" }} />}
              valueStyle={{ color: "#ef4444", fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="内存上限"
              value={config.max_memory_mb ?? 0}
              suffix="MB"
              prefix={<SafetyOutlined style={{ color: "#8b5cf6" }} />}
              valueStyle={{ color: "#8b5cf6", fontSize: 28 }}
            />
          </Card>
        </Col>
      </Row>

      <Card className="cs-card" title={<Space><SafetyOutlined /> 沙箱配置</Space>} style={{ marginTop: 16 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="最大内存">{config.max_memory_mb ?? 0} MB</Descriptions.Item>
          <Descriptions.Item label="CPU 上限">{config.max_cpu_percent ?? 0}%</Descriptions.Item>
          <Descriptions.Item label="超时时间">{config.timeout_seconds ?? 0} 秒</Descriptions.Item>
          <Descriptions.Item label="活跃会话">{sandbox.active_sessions ?? 0}</Descriptions.Item>
          <Descriptions.Item label="允许的域" span={2}>
            <Space wrap>
              {config.allowed_domains?.map((d) => <Tag key={d} color="green">{d}</Tag>) || <Text type="secondary">无</Text>}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="禁止路径" span={2}>
            <Space wrap>
              {config.denied_paths?.map((p) => <Tag key={p} color="red">{p}</Tag>) || <Text type="secondary">无</Text>}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------
//  Sub-component: Version Manager tab
// ------------------------------------------------------------------
function VersionsTab({ versions, loading, onPromote }: { versions: AgentVersion[]; loading: boolean; onPromote: (agentId: string, version: string, toStable: boolean) => void }) {
  const columns = [
    {
      title: "Agent",
      dataIndex: "agent_id",
      key: "agent_id",
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: "版本",
      dataIndex: "version",
      key: "version",
      render: (v: string) => <Text strong>v{v}</Text>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => <Tag color={versionStatusColor[s] || "default"}>{s}</Tag>,
    },
    {
      title: "灰度比例",
      dataIndex: "canary_percentage",
      key: "canary_percentage",
      render: (p: number, record: AgentVersion) =>
        record.status === "canary" ? (
          <Progress percent={p} size="small" strokeColor="#f59e0b" />
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: "发布日期",
      dataIndex: "release_date",
      key: "release_date",
      render: (t: string) => <Text style={{ fontSize: 12 }}>{fmtTime(t)}</Text>,
    },
    {
      title: "变更说明",
      dataIndex: "changes",
      key: "changes",
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text style={{ fontSize: 12 }}>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: AgentVersion) => (
        <Space>
          {record.status === "canary" && (
            <Button
              size="small"
              type="primary"
              onClick={() => onPromote(record.agent_id, record.version, true)}
            >
              升级为正式
            </Button>
          )}
          {record.status === "stable" && (
            <Tag color="success">已发布</Tag>
          )}
          {record.status === "deprecated" && (
            <Tag color="error">已废弃</Tag>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card className="cs-card">
      {loading ? (
        <Skeleton active />
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Statistic title="版本总数" value={versions.length} prefix={<BranchesOutlined style={{ color: "#3b82f6" }} />} />
            </Col>
            <Col span={8}>
              <Statistic
                title="正式版"
                value={versions.filter((v) => v.status === "stable").length}
                valueStyle={{ color: "#10b981" }}
                prefix={<CheckCircleOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="灰度中"
                value={versions.filter((v) => v.status === "canary").length}
                valueStyle={{ color: "#f59e0b" }}
                prefix={<ExperimentOutlined />}
              />
            </Col>
          </Row>
          <Table
            dataSource={versions}
            columns={columns}
            rowKey={(r) => `${r.agent_id}-${r.version}`}
            pagination={{ pageSize: 10, showSizeChanger: false }}
          />
        </>
      )}
    </Card>
  );
}

// ------------------------------------------------------------------
//  Sub-component: Observation tab
// ------------------------------------------------------------------
function ObservationTab({ loading }: { loading: boolean }) {
  const [traces, setTraces] = useState<any[]>([]);
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null);
  const [evaluation, setEvaluation] = useState<any>(null);
  const [optimizations, setOptimizations] = useState<OptimizationAction[]>([]);
  const [evolution, setEvolution] = useState<EvolutionSummary | null>(null);
  const [obsLoading, setObsLoading] = useState(true);

  const loadObservation = useCallback(async () => {
    setObsLoading(true);
    try {
      const [tracesRes, tokenRes, evalRes, optRes, evoRes] = await Promise.all([
        governanceService.recentTraces(15).catch(() => ({ traces: [] })),
        governanceService.tokenStats().catch(() => null),
        governanceService.evaluationSummary().catch(() => null),
        governanceService.pendingOptimizations().catch(() => ({ optimizations: [] })),
        governanceService.evolutionSummary().catch(() => null),
      ]);
      // traces could be a dict or list
      let traceList: any[] = [];
      const rawTraces = (tracesRes as any)?.traces;
      if (Array.isArray(rawTraces)) {
        traceList = rawTraces;
      } else if (rawTraces && typeof rawTraces === "object") {
        traceList = Object.values(rawTraces).flat() as any[];
      }
      setTraces(traceList);
      setTokenStats(tokenRes);
      setEvaluation(evalRes);
      setOptimizations((optRes as any)?.optimizations || []);
      setEvolution(evoRes);
    } catch {
      // ignore
    } finally {
      setObsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadObservation();
  }, [loadObservation]);

  const handleRunOptimization = async () => {
    try {
      const res = await governanceService.runOptimizationCycle();
      message.success(`优化周期完成，生成 ${res.generated_actions} 个优化动作`);
      loadObservation();
    } catch {
      message.error("优化周期执行失败");
    }
  };

  const handleApplyOptimization = async (actionId: string) => {
    try {
      await governanceService.applyOptimization(actionId);
      message.success("优化动作已应用");
      loadObservation();
    } catch {
      message.error("应用优化动作失败");
    }
  };

  if (obsLoading || loading) return <Skeleton active paragraph={{ rows: 10 }} />;

  return (
    <div>
      {/* Token Stats */}
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="总 Trace 数"
              value={tokenStats?.total_traces ?? 0}
              prefix={<EyeOutlined style={{ color: "#3b82f6" }} />}
              valueStyle={{ color: "#3b82f6", fontSize: 26 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="总 Token 消耗"
              value={tokenStats?.total_tokens ?? 0}
              prefix={<ThunderboltOutlined style={{ color: "#f59e0b" }} />}
              valueStyle={{ color: "#f59e0b", fontSize: 26 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="平均 Token/Trace"
              value={tokenStats?.avg_tokens_per_trace?.toFixed(0) ?? 0}
              prefix={<SyncOutlined style={{ color: "#10b981" }} />}
              valueStyle={{ color: "#10b981", fontSize: 26 }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card className="cs-card cs-stat-card">
            <Statistic
              title="待处理优化"
              value={optimizations.length}
              prefix={<ExperimentOutlined style={{ color: "#8b5cf6" }} />}
              valueStyle={{ color: "#8b5cf6", fontSize: 26 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Traces */}
      <Card
        className="cs-card"
        title={<Space><EyeOutlined /> 全链路追踪</Space>}
        style={{ marginTop: 16 }}
      >
        {traces.length === 0 ? (
          <Empty description="暂无执行追踪" />
        ) : (
          <Timeline
            items={traces.slice(0, 15).map((t: any) => ({
              color: t.step === "ERROR" || t.step === "FAIL" ? "red" : t.step === "START" ? "blue" : "green",
              dot: t.step === "START" ? <ClockCircleOutlined /> : <CheckCircleOutlined />,
              children: (
                <div>
                  <Space>
                    <Tag color="blue">{t.agent_id || t.workflow_id || "system"}</Tag>
                    <Tag>{t.step}</Tag>
                    {t.duration_ms > 0 && (
                      <Text type="secondary" style={{ fontSize: 12 }}>{t.duration_ms.toFixed(0)}ms</Text>
                    )}
                    {t.token_usage?.total_tokens > 0 && (
                      <Tag color="orange" style={{ fontSize: 11 }}>{t.token_usage.total_tokens} tokens</Tag>
                    )}
                  </Space>
                  <div style={{ marginTop: 4 }}>
                    <Text style={{ fontSize: 13 }}>{t.detail}</Text>
                  </div>
                  <Text type="secondary" style={{ fontSize: 11 }}>{fmtTime(t.timestamp)}</Text>
                </div>
              ),
            }))}
          />
        )}
      </Card>

      {/* Evaluation & Optimization */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card className="cs-card" title={<Space><CheckCircleOutlined /> Agent 评估</Space>}>
            {evaluation ? (
              <Descriptions column={1} size="small" bordered>
                {Object.entries(evaluation).map(([key, val]: [string, any]) => (
                  <Descriptions.Item key={key} label={key}>
                    {typeof val === "number"
                      ? typeof val === "number" && val <= 1
                        ? `${(val * 100).toFixed(1)}%`
                        : val
                      : typeof val === "object"
                        ? JSON.stringify(val)
                        : String(val ?? "-")}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : (
              <Empty description="暂无评估数据" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            className="cs-card"
            title={<Space><ExperimentOutlined /> 优化动作</Space>}
            extra={
              <Button size="small" icon={<SyncOutlined />} onClick={handleRunOptimization}>
                运行优化周期
              </Button>
            }
          >
            {optimizations.length === 0 ? (
              <Empty description="暂无待处理优化动作" />
            ) : (
              <Space direction="vertical" style={{ width: "100%" }}>
                {optimizations.map((opt) => (
                  <Card key={opt.action_id} size="small" className="cs-card">
                    <Space direction="vertical" size={4} style={{ width: "100%" }}>
                      <Space>
                        <Tag color={priorityColor[opt.priority] || "default"}>{opt.priority}</Tag>
                        <Tag color="blue">{opt.action_type}</Tag>
                        <Tag>{opt.agent_id}</Tag>
                      </Space>
                      <Text style={{ fontSize: 13 }}>{opt.description}</Text>
                      {opt.expected_improvement && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          预期改进: {opt.expected_improvement}
                        </Text>
                      )}
                      <Button
                        size="small"
                        type="primary"
                        onClick={() => handleApplyOptimization(opt.action_id)}
                      >
                        应用优化
                      </Button>
                    </Space>
                  </Card>
                ))}
              </Space>
            )}
          </Card>
        </Col>
      </Row>

      {/* Evolution */}
      <Card className="cs-card" title={<Space><BranchesOutlined /> Agent 自进化</Space>} style={{ marginTop: 16 }}>
        {evolution ? (
          <Row gutter={[16, 16]}>
            <Col xs={12} md={8}>
              <Statistic title="总进化次数" value={evolution.total_evolutions ?? 0} prefix={<BranchesOutlined style={{ color: "#8b5cf6" }} />} />
            </Col>
            <Col xs={12} md={16}>
              <div>
                <Text type="secondary">已进化 Agent: </Text>
                <Space wrap style={{ marginTop: 4 }}>
                  {(evolution.agents_evolved || []).map((a) => (
                    <Tag key={a} color="purple">{a}</Tag>
                  ))}
                  {(!evolution.agents_evolved || evolution.agents_evolved.length === 0) && (
                    <Text type="secondary">暂无</Text>
                  )}
                </Space>
              </div>
            </Col>
            {evolution.recent_evolution && (
              <Col span={24}>
                <Card size="small" className="cs-card" title="最近一次进化">
                  <Descriptions size="small" column={1}>
                    {Object.entries(evolution.recent_evolution).map(([k, v]: [string, any]) => (
                      <Descriptions.Item key={k} label={k}>
                        {typeof v === "object" ? JSON.stringify(v) : String(v ?? "-")}
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                </Card>
              </Col>
            )}
          </Row>
        ) : (
          <Empty description="暂无进化数据" />
        )}
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------
//  Main page
// ------------------------------------------------------------------
export default function Governance() {
  const [activeTab, setActiveTab] = useState("overview");
  const [overview, setOverview] = useState<any>(null);
  const [agents, setAgents] = useState<AgentMetadata[]>([]);
  const [skills, setSkills] = useState<SkillMetadata[]>([]);
  const [mcpInterfaces, setMcpInterfaces] = useState<MCPInterface[]>([]);
  const [permissions, setPermissions] = useState<WorkflowPermission[]>([]);
  const [sandbox, setSandbox] = useState<SandboxStatus | null>(null);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, skillsRes, mcpRes, permRes, sandboxRes, verRes] = await Promise.all([
        governanceService.overview().catch(() => null),
        governanceService.listSkills().catch(() => ({ skills: [] })),
        governanceService.listMCP().catch(() => ({ interfaces: [] })),
        governanceService.listWorkflowPermissions().catch(() => ({ workflows: [] })),
        governanceService.sandboxStatus().catch(() => null),
        governanceService.listVersions().catch(() => ({ versions: [] })),
      ]);
      setOverview(ovRes);
      setAgents(ovRes?.agents || []);
      setSkills((skillsRes as any)?.skills || []);
      setMcpInterfaces((mcpRes as any)?.interfaces || []);
      setPermissions((permRes as any)?.workflows || []);
      setSandbox(sandboxRes);
      setVersions((verRes as any)?.versions || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handlePromote = async (agentId: string, version: string, toStable: boolean) => {
    try {
      if (toStable) {
        await governanceService.promoteStable(agentId, version);
        message.success(`${agentId} v${version} 已升级为正式版`);
      } else {
        await governanceService.promoteCanary(agentId, version);
        message.success(`${agentId} v${version} 已开始灰度`);
      }
      loadAll();
    } catch {
      message.error("版本升级失败");
    }
  };

  const tabItems = [
    {
      key: "overview",
      label: "总览",
      children: <OverviewTab overview={overview} loading={loading} />,
    },
    {
      key: "agents",
      label: `Agent(${agents.length})`,
      children: <AgentsTab agents={agents} loading={loading} />,
    },
    {
      key: "skills",
      label: `技能(${skills.length})`,
      children: <SkillsTab skills={skills} loading={loading} />,
    },
    {
      key: "mcp",
      label: `MCP(${mcpInterfaces.length})`,
      children: <MCPTab interfaces={mcpInterfaces} loading={loading} />,
    },
    {
      key: "permissions",
      label: `权限(${permissions.length})`,
      children: <PermissionsTab permissions={permissions} loading={loading} />,
    },
    {
      key: "sandbox",
      label: "沙箱",
      children: <SandboxTab sandbox={sandbox} loading={loading} />,
    },
    {
      key: "versions",
      label: `版本(${versions.length})`,
      children: <VersionsTab versions={versions} loading={loading} onPromote={handlePromote} />,
    },
    {
      key: "observation",
      label: "AgentLoop",
      children: <ObservationTab loading={loading} />,
    },
  ];

  return (
    <div className="cs-dashboard">
      <div className="cs-dashboard__header">
        <div>
          <Title level={3} style={{ margin: 0 }}>
            智能体治理控制台
          </Title>
          <Paragraph type="secondary" style={{ margin: 0, marginTop: 2 }}>
            Agent Governance Layer · Registry · Skills · MCP · Permissions · Sandbox · Versions · AgentLoop
          </Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      <Card className="cs-card" style={{ marginTop: 16 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
          tabBarStyle={{ marginBottom: 16 }}
        />
      </Card>
    </div>
  );
}
