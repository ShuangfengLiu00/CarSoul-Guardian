/**
 * 控制台 /portal
 * 已改为真实系统控制台：展示 Guardian 与车辆世界模型引擎 carModel 的真实服务
 * 状态（健康总览 / 进化引擎 / 合规闸门），并提供指向本应用内真实工作路由的
 * 导航入口。不再展示生产环境会 404 的 carModel 外链深链。所有状态数据来自
 * 真实端点，无任何模拟数据。
 */
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Card,
  Col,
  Row,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Typography,
} from "antd";
import {
  AppstoreOutlined,
  DashboardOutlined,
  RobotOutlined,
  HeartOutlined,
  CarOutlined,
  SafetyCertificateOutlined,
  RocketOutlined,
  WarningOutlined,
  ReadOutlined,
  DatabaseOutlined,
  ToolOutlined,
  ApartmentOutlined,
  BookOutlined,
  DotChartOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import { get } from "@/utils/request";
import { evolutionService } from "@/services/evolutionService";
import { safetyService } from "@/services/safetyService";

const { Title, Text } = Typography;

interface HealthOverview {
  health_score?: number;
  /** carModel 世界模型 SOH（独立口径，与车辆健康分不同定义） */
  world_model_soh_health?: number | null;
  agent_status?: string;
  recent_alerts?: { level: string; title: string }[];
}

interface NavItem {
  path: string;
  label: string;
  desc: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "总览", desc: "车辆健康与风险总览", icon: <DashboardOutlined /> },
  { path: "/agent", label: "Agent 对话", desc: "与车辆数字灵魂对话", icon: <RobotOutlined /> },
  { path: "/soul", label: "数字生命", desc: "灵魂指数与生命档案", icon: <HeartOutlined /> },
  { path: "/vehicle", label: "车辆档案", desc: "车辆基础信息与维保", icon: <CarOutlined /> },
  { path: "/safety", label: "安全合规", desc: "5 类合规闸门拦截", icon: <SafetyCertificateOutlined /> },
  { path: "/evolution", label: "进化引擎", desc: "Agent 永续进化闭环", icon: <RocketOutlined /> },
  { path: "/risk", label: "风险预测", desc: "电池与健康风险预警", icon: <WarningOutlined /> },
  { path: "/story", label: "故事模式", desc: "真实生命事件叙事", icon: <ReadOutlined /> },
  { path: "/memory", label: "记忆海洋", desc: "车辆真实记忆可视化", icon: <DatabaseOutlined /> },
  { path: "/simulator", label: "仿真沙盘", desc: "真实预测引擎输出", icon: <ToolOutlined /> },
  { path: "/governance", label: "治理", desc: "合规与进化治理台", icon: <ApartmentOutlined /> },
  { path: "/knowledge", label: "知识库", desc: "RAG 知识检索", icon: <BookOutlined /> },
  { path: "/sensors", label: "传感器总览", desc: "全车快照与传感器", icon: <DotChartOutlined /> },
  { path: "/timeline", label: "时间线", desc: "车辆生命周期时间线", icon: <HistoryOutlined /> },
];

export default function Console() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthOverview | null>(null);
  const [evolution, setEvolution] = useState<{ enabled: boolean; cycles: number } | null>(null);
  const [safetyTotal, setSafetyTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [h, e, s] = await Promise.all([
        get<HealthOverview>("/api/health/overview").catch(() => null),
        evolutionService.dashboard().catch(() => null),
        safetyService.gateStats().catch(() => null),
      ]);
      setHealth(h);
      if (e) setEvolution({ enabled: e.engine_enabled, cycles: e.total_cycles });
      if (s) setSafetyTotal(s.total);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <Title level={4} style={{ margin: "0 0 16px" }}>
        <AppstoreOutlined style={{ marginRight: 8, color: "#3b82f6" }} />
        控制台
      </Title>

      {loading && <Skeleton active paragraph={{ rows: 6 }} />}

      {!loading && error && (
        <Alert
          type="error"
          showIcon
          message="服务状态加载失败"
          description="无法连接系统状态服务，本页不展示任何数据。"
        />
      )}

      {!loading && !error && (
        <>
          {/* 真实服务状态 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8}>
              <Card className="cs-card">
                <Statistic
                  title="世界模型引擎健康分"
                  value={health?.world_model_soh_health ?? "取不到"}
                  valueStyle={{ color: "#10b981", fontWeight: 700 }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Agent 状态：{health?.agent_status ?? "未知"}
                </Text>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card className="cs-card">
                <Statistic
                  title="进化引擎周期"
                  value={evolution?.cycles ?? "取不到"}
                  valueStyle={{ color: "#a855f7", fontWeight: 700 }}
                />
                <Tag color={evolution?.enabled ? "green" : "default"} style={{ marginTop: 4 }}>
                  {evolution?.enabled ? "引擎已启用" : "引擎未启用"}
                </Tag>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card className="cs-card">
                <Statistic
                  title="合规闸门累计拦截"
                  value={safetyTotal ?? "取不到"}
                  valueStyle={{ color: "#3b82f6", fontWeight: 700 }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  真实拦截事件计数
                </Text>
              </Card>
            </Col>
          </Row>

          {/* 真实内部导航 */}
          <Card title="功能导航（应用内真实路由）">
            <Row gutter={[12, 12]}>
              {NAV_ITEMS.map((n) => (
                <Col xs={24} sm={12} md={8} lg={6} key={n.path}>
                  <div
                    onClick={() => navigate(n.path)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: 14,
                      border: "1px solid #1f2937",
                      borderRadius: 12,
                      background: "#0f1729",
                      cursor: "pointer",
                      height: "100%",
                    }}
                  >
                    <div style={{ fontSize: 24, color: "#3b82f6" }}>{n.icon}</div>
                    <div>
                      <div style={{ fontWeight: 600, color: "#e2e8f0" }}>{n.label}</div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {n.desc}
                      </Text>
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
            <Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 12 }}>
              数据来源：健康总览 / 进化引擎 / 合规闸门真实端点；导航均为本应用内已部署路由。
            </Text>
          </Card>
        </>
      )}
    </div>
  );
}
