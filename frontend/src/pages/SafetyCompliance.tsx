import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Tag,
  Space,
  Divider,
  Alert,
  Timeline,
  Badge,
  Row,
  Col,
  Statistic,
  Button,
  Modal,
  Spin,
} from "antd";
import { safetyService } from "@/services/safetyService";
import type { GateStatsResponse, GateCategoryKey } from "@/services/safetyService";
import {
  SafetyCertificateOutlined,
  LockOutlined,
  RobotOutlined,
  CarOutlined,
  FileProtectOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";

const { Title, Paragraph, Text, Link } = Typography;

/** 合规条目 */
interface ComplianceItem {
  title: string;
  status: "compliant" | "partial" | "planned";
  description: string;
  evidence: string;
}

const dataSafetyItems: ComplianceItem[] = [
  {
    title: "数据采集最小化原则",
    status: "compliant",
    description:
      "仅采集车辆运行所必需的数据（VIN、里程、传感器读数、驾驶行为统计），不采集与车辆健康无关的个人隐私信息。所有数据采集均在用户明确授权后进行。",
    evidence: "backend/app/models/ — 所有数据模型均围绕车辆实体设计，无独立个人隐私字段。",
  },
  {
    title: "数据存储加密",
    status: "compliant",
    description:
      "数据库连接使用加密传输（生产环境 PostgreSQL 支持 SSL）。JWT 令牌签名验证用户身份，敏感操作需二次确认。",
    evidence: "backend/app/core/security.py — JWT 认证 + HS256 签名。",
  },
  {
    title: "数据本地化处理",
    status: "compliant",
    description:
      "开发环境使用 SQLite 本地存储，生产环境支持私有化部署。所有车辆数据在本地或私有云内处理，不上传至第三方服务器。",
    evidence: "backend/app/core/config.py — DATABASE_URL 可配置为本地或私有数据库。",
  },
  {
    title: "数据删除权",
    status: "compliant",
    description:
      "用户可随时删除车辆及其关联的所有数据（健康快照、保养记录、驾驶行为、告警、生命周期事件），删除操作级联执行，不可恢复。",
    evidence: "backend/app/api/vehicle/router.py — DELETE /api/vehicle/{id} 级联删除。",
  },
];

const aiSafetyItems: ComplianceItem[] = [
  {
    title: "AI 输出可解释性",
    status: "compliant",
    description:
      "Agent 的每一次推理均输出完整的思维链（Chain-of-Thought）：感知 → 诊断 → 专家会诊 → 风险评估 → 建议。用户可在风险预测页面查看完整推理轨迹。",
    evidence: "frontend/src/pages/RiskPrediction.tsx — 推理轨迹详情面板；backend/app/services/risk_prediction_service.py",
  },
  {
    title: "人机协同决策",
    status: "compliant",
    description:
      "AI 仅提供辅助建议，不替代人类决策。风险预测需用户确认（acknowledge）后才会更新状态，处置结果由用户提交反馈闭合环路。",
    evidence: "风险预测闭环：predict → acknowledge → feedback → accuracy。",
  },
  {
    title: "AI 幻觉防护",
    status: "compliant",
    description:
      "Agent 工具层优先查询后端数据库获取真实数据，仅在 DB 不可用时降级到 Mock 数据。所有工具返回的数据均有数据源标识，Agent 回答基于工具返回的结构化数据而非自由生成。",
    evidence: "ai-agent/carsoul_agent/tools/vehicle_tools.py — DB-backed with Mock fallback。",
  },
  {
    title: "安全降级机制",
    status: "compliant",
    description:
      "当 LLM 后端不可用时，系统自动降级到规则引擎（rule-based fallback），确保核心功能不中断。降级状态在 UI 中明确标识。",
    evidence: "backend/app/services/agent_service.py — _fallback_respond()。",
  },
  {
    title: "主动巡检安全边界",
    status: "compliant",
    description:
      "主动巡检调度器仅在后台执行只读分析（查询数据、生成预测），不执行任何写入或控制操作。巡检间隔可配置，支持手动暂停/恢复。",
    evidence: "backend/app/services/scheduler.py — APScheduler 巡检任务。",
  },
];

const vehicleSafetyItems: ComplianceItem[] = [
  {
    title: "只读数据接口",
    status: "compliant",
    description:
      "系统通过 OBD 接口和车辆 API 读取车辆状态数据，不向车辆发送任何控制指令。所有车辆交互均为只读操作，不影响车辆正常行驶。",
    evidence: "所有 vehicle_tools 工具方法均为查询操作，无写入/控制方法。",
  },
  {
    title: "驾驶安全提示",
    status: "compliant",
    description:
      "驾驶行为分析结果包含安全评分和建议，但仅在停车状态下通过车机大屏展示。系统不干扰驾驶过程，不发送弹窗或声音提示。",
    evidence: "frontend/ — 所有页面设计为车机大屏模式，停车时交互。",
  },
  {
    title: "故障预警不替代专业检修",
    status: "compliant",
    description:
      "风险预测和告警仅作为预警参考，明确告知用户「请以专业检修机构诊断为准」。严重故障建议直接联系服务中心。",
    evidence: "告警 recommendation 字段始终包含专业检修建议。",
  },
];

const privacyItems: ComplianceItem[] = [
  {
    title: "《个人信息保护法》合规",
    status: "compliant",
    description:
      "遵循最小必要原则采集数据，用户享有知情权、决定权、删除权。数据采集前明确告知用途，用户可随时撤回授权并删除数据。",
    evidence: "本声明页 + DELETE API 级联删除。",
  },
  {
    title: "《数据安全法》合规",
    status: "compliant",
    description:
      "建立数据分类分级管理机制。车辆运行数据归类为一般数据，不包含敏感个人信息。生产环境支持数据加密存储和传输。",
    evidence: "backend/app/core/config.py — 支持 PostgreSQL SSL 连接。",
  },
  {
    title: "《网络安全法》合规",
    status: "compliant",
    description:
      "系统具备身份认证（JWT）、访问控制、日志审计能力。API 接口均需认证，未授权请求返回 401。",
    evidence: "backend/app/core/security.py — JWT 认证中间件。",
  },
  {
    title: "汽车数据安全管理规定",
    status: "compliant",
    description:
      "遵循《汽车数据安全管理若干规定（试行）》，对涉及个人信息和重要数据的处理活动进行记录，坚持车内处理原则、不公开不提供原则。",
    evidence: "数据本地化处理 + 只读车辆接口。",
  },
];

const statusConfig = {
  compliant: { color: "success", text: "已合规", icon: <CheckCircleOutlined /> },
  partial: { color: "warning", text: "部分合规", icon: <ExclamationCircleOutlined /> },
  planned: { color: "default", text: "规划中", icon: <ExclamationCircleOutlined /> },
};

function ComplianceCard({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: ComplianceItem[];
}) {
  return (
    <Card
      style={{ marginBottom: 16 }}
      title={
        <Space>
          {icon}
          <span>{title}</span>
          <Tag color="blue">{items.filter((i) => i.status === "compliant").length}/{items.length} 已合规</Tag>
        </Space>
      }
    >
      {items.map((item, idx) => {
        const cfg = statusConfig[item.status];
        return (
          <div key={idx} style={{ marginBottom: idx < items.length - 1 ? 16 : 0 }}>
            <Space align="start" style={{ width: "100%" }}>
              <Badge color={cfg.color === "success" ? "green" : cfg.color === "warning" ? "orange" : "default"} />
              <div style={{ flex: 1 }}>
                <Space>
                  <Text strong>{item.title}</Text>
                  <Tag color={cfg.color} icon={cfg.icon}>
                    {cfg.text}
                  </Tag>
                </Space>
                <Paragraph style={{ marginTop: 4, marginBottom: 4, color: "var(--cs-text-secondary)" }}>
                  {item.description}
                </Paragraph>
                <Text type="secondary" style={{ fontSize: 12, fontFamily: "monospace" }}>
                  技术佐证：{item.evidence}
                </Text>
              </div>
            </Space>
            {idx < items.length - 1 && <Divider style={{ margin: "12px 0" }} />}
          </div>
        );
      })}
    </Card>
  );
}

/** 合规闸门真实拦截计数面板 —— 严格按后端诚实数据纪律渲染。 */
function GateStatsPanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<GateStatsResponse | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    safetyService
      .gateStats()
      .then((data) => {
        if (alive) setStats(data);
      })
      .catch((e: unknown) => {
        if (alive) {
          const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          setError(typeof detail === "string" ? detail : "合规计数取数失败");
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (loading) {
    return (
      <Card style={{ marginBottom: 16 }}>
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      </Card>
    );
  }

  // 真实计数取不到：后端 unavailable / payload 非法 / 网络失败 —— 绝不回填 0，整卡显示暂不可用。
  const unavailable = !stats || stats.data_status?.code !== "ok_carmodel_gate_stats";

  if (unavailable) {
    const reason = stats?.data_status?.detail || error || "合规计数暂不可用";
    return (
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            合规闸门真实拦截计数
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Alert type="info" showIcon message="合规计数暂不可用" description={reason} />
      </Card>
    );
  }

  const categories: { key: GateCategoryKey; label: string; refuse: boolean }[] = [
    { key: "identity", label: "身份信息索取拦截", refuse: true },
    { key: "geo", label: "位置/轨迹索取拦截", refuse: true },
    { key: "data_fraud", label: "伪造/篡改车辆数据诱导拦截", refuse: true },
    { key: "repair_mislead", label: "危险自修诱导拦截", refuse: true },
    // safety_critical 处置是 safety_disclaim（免责+导向专业检修），并非 refuse 拦截，措辞需区分。
    { key: "safety_critical", label: "安全结论索取（免责引导）", refuse: false },
  ];

  const degraded = stats.storage === "memory" || !!stats.degraded_reason;

  return (
    <Card
      title={
        <Space>
          <SafetyCertificateOutlined />
          合规闸门真实拦截计数
        </Space>
      }
      extra={
        <Tag color={degraded ? "orange" : "green"}>
          {degraded ? "计数可能不全" : "真实累计"}
        </Tag>
      }
      style={{ marginBottom: 16 }}
    >
      <Row gutter={[16, 16]}>
        {categories.map((c) => {
          const v = stats[c.key];
          return (
            <Col xs={12} sm={8} md={4} key={c.key}>
              <Statistic
                title={c.label}
                // null（取不到）必须显示「暂无数据」，绝不用 0 冒充「从未触发」。
                value={v ?? 0}
                formatter={(val) => (v === null ? <Text type="secondary">暂无数据</Text> : val)}
                valueStyle={{ color: c.refuse ? undefined : "#f59e0b" }}
              />
            </Col>
          );
        })}
      </Row>
      <Divider style={{ margin: "12px 0" }} />
      <Space direction="vertical" size={2} style={{ width: "100%" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          统计窗口：自 {stats.since || "尚无拦截记录"} 起 · 最近一次：{stats.updated_at || "—"}
        </Text>
        <Text type="secondary" style={{ fontSize: 12, fontFamily: "monospace" }}>
          数据来源：{stats.data_source}
        </Text>
        {degraded && (
          <Text type="warning" style={{ fontSize: 12 }}>
            注意：{stats.degraded_reason || "计数链路降级，该值可能偏小且重启清零"}
          </Text>
        )}
      </Space>
    </Card>
  );
}

export default function SafetyCompliance() {
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);

  return (
    <div className="cs-content-wrap">
      {/* Header */}
      <Card style={{ marginBottom: 16, background: "linear-gradient(135deg, #f0f7ff, #e8f5e9)" }}>
        <Row align="middle" gutter={24}>
          <Col>
            <SafetyCertificateOutlined style={{ fontSize: 48, color: "#3b82f6" }} />
          </Col>
          <Col flex={1}>
            <Title level={3} style={{ margin: 0 }}>
              安全合规声明
            </Title>
            <Text type="secondary">
              CarSoul Guardian 致力于在 AI 汽车守护领域实现最高标准的数据安全、AI 伦理与法律合规。
              本声明适用于系统的所有功能模块，包括 AI 守护引擎、风险预测、车辆数字生命档案等。
            </Text>
          </Col>
        </Row>
      </Card>

      {/* 真实合规闸门拦截计数（接 carModel 真实运行时计数，绝不硬编码） */}
      <GateStatsPanel />

      {/* Quick stats —— 由静态声明数组实时计数，避免写死数字 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="合规条目"
              value={dataSafetyItems.length + aiSafetyItems.length + vehicleSafetyItems.length + privacyItems.length}
              prefix={<SafetyCertificateOutlined />}
              suffix={<Tag color="success" style={{ fontSize: 12 }}>全部已合规</Tag>}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据安全"
              value={dataSafetyItems.length}
              suffix="项"
              prefix={<LockOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="AI 安全"
              value={aiSafetyItems.length}
              suffix="项"
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="法律法规"
              value={privacyItems.length}
              suffix="项"
              prefix={<FileProtectOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Compliance sections */}
      <ComplianceCard
        icon={<LockOutlined style={{ color: "#3b82f6" }} />}
        title="数据安全合规"
        items={dataSafetyItems}
      />

      <ComplianceCard
        icon={<RobotOutlined style={{ color: "#10b981" }} />}
        title="AI 智能体安全合规"
        items={aiSafetyItems}
      />

      <ComplianceCard
        icon={<CarOutlined style={{ color: "#f59e0b" }} />}
        title="车辆安全合规"
        items={vehicleSafetyItems}
      />

      <ComplianceCard
        icon={<FileProtectOutlined style={{ color: "#8b5cf6" }} />}
        title="隐私保护与法律法规合规"
        items={privacyItems}
      />

      {/* Safety lifecycle */}
      <Card title={<Space><SafetyCertificateOutlined />安全合规生命周期</Space>} style={{ marginBottom: 16 }}>
        <Timeline
          items={[
            {
              color: "green",
              children: (
                <Space direction="vertical">
                  <Text strong>设计阶段 — 安全前置</Text>
                  <Text type="secondary">采用最小数据采集原则，所有数据模型围绕车辆实体设计，从架构层面排除非必要隐私数据。</Text>
                </Space>
              ),
            },
            {
              color: "blue",
              children: (
                <Space direction="vertical">
                  <Text strong>开发阶段 — 安全编码</Text>
                  <Text type="secondary">JWT 身份认证、API 权限控制、SQLAlchemy ORM 防注入、输入校验、AI 工具层 DB 优先 + Mock 降级。</Text>
                </Space>
              ),
            },
            {
              color: "blue",
              children: (
                <Space direction="vertical">
                  <Text strong>运行阶段 — 主动守护</Text>
                  <Text type="secondary">APScheduler 定时巡检车辆健康，风险预测闭环（预测→确认→反馈→准确率），告警生命周期管理。</Text>
                </Space>
              ),
            },
            {
              color: "green",
              children: (
                <Space direction="vertical">
                  <Text strong>退役阶段 — 数据销毁</Text>
                  <Text type="secondary">用户可随时删除车辆及全部关联数据，级联删除不可恢复，保障用户数据删除权。</Text>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* Disclaimer */}
      <Alert
        type="warning"
        showIcon
        icon={<ExclamationCircleOutlined />}
        message="安全免责声明"
        description={
          <Space direction="vertical" size={4}>
            <Text>
              CarSoul Guardian 提供的 AI 守护建议、风险预测、健康评分均为辅助参考信息，不构成专业维修建议。
              车辆故障诊断与维修请以专业检修机构结论为准。
            </Text>
            <Text>
              系统不对因依赖 AI 建议而导致的任何损失承担责任。用户在驾驶过程中应始终遵守交通法规，
              不得因查看系统信息而分心驾驶。
            </Text>
            <Link onClick={() => setDisclaimerOpen(true)}>查看完整免责声明 →</Link>
          </Space>
        }
        style={{ marginBottom: 16 }}
      />

      <Modal
        title="完整免责声明"
        open={disclaimerOpen}
        onCancel={() => setDisclaimerOpen(false)}
        footer={<Button type="primary" onClick={() => setDisclaimerOpen(false)}>我已知晓</Button>}
        width={640}
      >
        <Typography>
          <Paragraph>
            <Text strong>1. 服务性质</Text>
            <br />
            <Text>
              CarSoul Guardian（以下简称"本系统"）是一款基于 AI Agent 的汽车生命周期守护系统，
              提供车辆健康监测、风险预测、保养建议等辅助功能。本系统提供的所有信息和建议均为参考性质，
              不构成专业维修、保险或法律建议。
            </Text>
          </Paragraph>
          <Paragraph>
            <Text strong>2. 准确性声明</Text>
            <br />
            <Text>
              本系统通过传感器数据、OBD 接口和 AI 模型进行分析，但不保证分析结果的绝对准确性。
              风险预测准确率基于历史数据统计，不代表对未来事件的确定性判断。
            </Text>
          </Paragraph>
          <Paragraph>
            <Text strong>3. 驾驶安全</Text>
            <br />
            <Text>
              本系统设计为停车状态下通过车机大屏交互。驾驶过程中严禁操作本系统。
              因驾驶过程中操作系统导致的任何事故，本系统不承担责任。
            </Text>
          </Paragraph>
          <Paragraph>
            <Text strong>4. 数据使用</Text>
            <br />
            <Text>
              本系统采集的车辆数据仅用于车辆健康分析和守护建议生成，不用于商业广告、用户画像或其他非车辆守护目的。
              用户数据存储在本地或私有云中，不上传至第三方。
            </Text>
          </Paragraph>
          <Paragraph>
            <Text strong>5. 责任限制</Text>
            <br />
            <Text>
              在适用法律允许的最大范围内，本系统不对因使用或无法使用本系统而导致的任何直接、间接、附带或后果性损失承担责任。
            </Text>
          </Paragraph>
        </Typography>
      </Modal>

      {/* Footer */}
      <div style={{ textAlign: "center", padding: "24px 0", color: "var(--cs-text-secondary)" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          CarSoul Guardian © 2024-2026 · 安全合规版本 v1.0 · 最后更新：2026-08-02
        </Text>
      </div>
    </div>
  );
}
