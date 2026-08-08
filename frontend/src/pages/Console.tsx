import { useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { Card, Row, Col, Typography, Tag, Space } from "antd";
import {
  RobotOutlined,
  HeartOutlined,
  CarOutlined,
  AlertOutlined,
  SafetyCertificateOutlined,
  ControlOutlined,
  RocketOutlined,
  ExperimentOutlined,
  DashboardOutlined,
  ApiOutlined,
  GlobalOutlined,
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

type Entry = {
  key: string;
  title: string;
  desc: string;
  icon: ReactNode;
  to?: string;
  href?: string;
  tag?: string;
};

/** Guardian 本体内的核心页面（SPA 内跳转） */
const coreEntries: Entry[] = [
  { key: "dashboard", title: "总览 Dashboard", desc: "健康与告警一屏掌握", icon: <DashboardOutlined />, to: "/" },
  { key: "agent", title: "AI 守护对话", desc: "多专家 Agent 闭环答疑", icon: <RobotOutlined />, to: "/agent" },
  { key: "life", title: "数字生命", desc: "车辆一生档案与记忆", icon: <HeartOutlined />, to: "/life" },
  { key: "vehicle", title: "车辆档案", desc: "单车全量数据透视", icon: <CarOutlined />, to: "/vehicle" },
  { key: "risk", title: "风险预测", desc: "故障 / 残值前瞻预警", icon: <AlertOutlined />, to: "/risk" },
  { key: "safety", title: "安全合规", desc: "守护边界与披露", icon: <SafetyCertificateOutlined />, to: "/safety" },
  { key: "governance", title: "治理控制台", desc: "Agent 权限与版本", icon: <ControlOutlined />, to: "/governance" },
  { key: "memory", title: "记忆海洋", desc: "车辆记忆可视化", icon: <ExperimentOutlined />, to: "/memory" },
  { key: "evolution", title: "进化引擎", desc: "模型持续进化", icon: <RocketOutlined />, to: "/evolution" },
];

/** 车辆世界模型引擎 carModel（同源，独立页面打开） */
const engineEntries: Entry[] = [
  { key: "health", title: "引擎健康", desc: "xgb-battery-v1.0 自检", icon: <ApiOutlined />, href: "/health", tag: "carModel" },
  { key: "docs", title: "API 文档", desc: "FastAPI Swagger 契约", icon: <ApiOutlined />, href: "/docs", tag: "carModel" },
  { key: "cockpit", title: "3D 数字孪生驾驶舱", desc: "实车状态可视化", icon: <GlobalOutlined />, href: "/cockpit/", tag: "carModel" },
];

export default function Console() {
  const navigate = useNavigate();

  const go = (e: Entry) => {
    if (e.href) window.open(e.href, "_blank", "noopener");
    else if (e.to) navigate(e.to);
  };

  const renderCard = (e: Entry) => (
    <Col xs={24} sm={12} md={8} lg={6} key={e.key}>
      <Card hoverable className="cs-card" onClick={() => go(e)} style={{ height: "100%" }}>
        <Space align="start" size={14} style={{ width: "100%" }}>
          <div style={{ fontSize: 26, lineHeight: 1, color: "#3b82f6" }}>{e.icon}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div>
              <Text strong style={{ fontSize: 15 }}>
                {e.title}
              </Text>
              {e.tag && (
                <Tag color="cyan" style={{ marginLeft: 6, transform: "scale(0.85)", transformOrigin: "left" }}>
                  {e.tag}
                </Tag>
              )}
            </div>
            <div style={{ marginTop: 4 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {e.desc}
              </Text>
            </div>
          </div>
        </Space>
      </Card>
    </Col>
  );

  return (
    <div className="cs-content-wrap">
      <Title level={3} style={{ marginBottom: 2 }}>
        <span className="cs-gradient-text">统一入口</span> · CarSoul Guardian 控制台
      </Title>
      <Paragraph type="secondary" style={{ marginTop: 0, marginBottom: 18 }}>
        一个入口直达所有能力：对话、数字生命、预测、治理，以及底层车辆世界模型引擎。点卡片即可跳转。
      </Paragraph>

      <Title level={5} style={{ marginBottom: 12 }}>
        核心功能
      </Title>
      <Row gutter={[16, 16]}>{coreEntries.map(renderCard)}</Row>

      <Title level={5} style={{ margin: "28px 0 12px" }}>
        车辆世界模型引擎 · carModel
      </Title>
      <Row gutter={[16, 16]}>{engineEntries.map(renderCard)}</Row>
    </div>
  );
}
