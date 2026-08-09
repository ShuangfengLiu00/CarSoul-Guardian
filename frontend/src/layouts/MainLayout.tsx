import { ReactNode, useEffect, useState } from "react";
import { Layout, Menu, theme, Avatar, Space, Typography } from "antd";
import { Outlet } from "react-router-dom";
import {
  DashboardOutlined,
  RobotOutlined,
  CarOutlined,
  HeartOutlined,
  PlayCircleOutlined,
  ToolOutlined,
  CrownOutlined,
  AlertOutlined,
  SafetyCertificateOutlined,
  ControlOutlined,
  RocketOutlined,
  FieldTimeOutlined,
  AppstoreOutlined,
  BookOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

/**
 * 主菜单（核心动线）。
 * 注意：/story 与 /evolution 已移出主菜单（见 LAB_ITEMS），路由本身保留，
 * 仅通过「实验室」二级入口或直达 URL 访问，避免把未成熟能力放进主动线。
 */
const menuItems = [
  { key: "/portal", icon: <AppstoreOutlined />, label: "统一入口" },
  { key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "/agent", icon: <RobotOutlined />, label: "AI 守护" },
  { key: "/vehicle", icon: <CarOutlined />, label: "车辆档案" },
  { key: "/life", icon: <HeartOutlined />, label: "数字生命" },
  { key: "/soul", icon: <CrownOutlined />, label: "灵魂主页" },
  { key: "/knowledge", icon: <BookOutlined />, label: "知识库" },
  { key: "/risk", icon: <AlertOutlined />, label: "风险预测" },
  { key: "/safety", icon: <SafetyCertificateOutlined />, label: "安全合规" },
  { key: "/simulator", icon: <ToolOutlined />, label: "推演沙盘" },
  { key: "/sensors", icon: <DashboardOutlined />, label: "传感器总览" },
  { key: "/governance", icon: <ControlOutlined />, label: "治理控制台" },
  { key: "/timeline", icon: <FieldTimeOutlined />, label: "一辆车的一生" },
];

/** 实验室（二级入口）：路由保留但不进主动线。 */
const LAB_ITEMS = [
  { key: "/story", icon: <PlayCircleOutlined />, label: "故事模式" },
  { key: "/evolution", icon: <RocketOutlined />, label: "进化引擎" },
];

const LAB_GROUP_KEY = "lab";

/** 桌面侧栏渲染项 = 主菜单 + 「实验室」折叠子菜单。 */
const siderItems = [
  ...menuItems,
  {
    key: LAB_GROUP_KEY,
    icon: <ExperimentOutlined />,
    label: "实验室",
    children: LAB_ITEMS,
  },
];

/** 用于高亮匹配的全量路由项（含实验室）。 */
const ALL_ROUTE_ITEMS = [...menuItems, ...LAB_ITEMS];

// 平板/手机检测：触摸设备 或 窄屏
function useIsTablet() {
  const [isTablet, setIsTablet] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(pointer: coarse), (max-width: 1024px)");
    const update = () => setIsTablet(mq.matches);
    update();
    if (mq.addEventListener) {
      mq.addEventListener("change", update);
      return () => mq.removeEventListener("change", update);
    }
    mq.addListener(update);
    return () => mq.removeListener(update);
  }, []);
  return isTablet;
}

export default function MainLayout({ children }: { children?: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isTablet = useIsTablet();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const selectedKey =
    ALL_ROUTE_ITEMS.find((m) => location.pathname.startsWith(m.key) && m.key !== "/")?.key ||
    (location.pathname === "/" ? "/" : "/");

  // 命中实验室路由时自动展开「实验室」子菜单，保证直达 URL 也能定位。
  const openKeys = LAB_ITEMS.some((m) => m.key === selectedKey) ? [LAB_GROUP_KEY] : undefined;

  // ===== 平板/手机布局：顶部 Header + 底部 Tab Bar =====
  if (isTablet) {
    return (
      <Layout className="cs-tablet-layout" style={{ minHeight: "100vh", background: "var(--cs-bg)" }}>
        <Header
          className="cs-tablet-header"
          style={{
            background: colorBgContainer,
            padding: "0 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #eef0f4",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <Space align="center" size={10}>
            <Avatar
              size={36}
              style={{ background: "linear-gradient(135deg,#3b82f6,#10b981)" }}
              icon={<HeartOutlined />}
            />
            <div>
              <Title level={5} style={{ margin: 0, lineHeight: 1.1, fontSize: 16 }}>
                CarSoul Guardian
              </Title>
              <Text type="secondary" style={{ fontSize: 11 }}>
                AI 汽车守护
              </Text>
            </div>
          </Space>
          <span className="cs-gradient-text" style={{ fontWeight: 700, fontSize: 13 }}>
            守护在线
          </span>
        </Header>

        <Content style={{ margin: 0, flex: 1, paddingBottom: 72 }}>
          <div className="cs-content-wrap cs-content-wrap--tablet">{children ?? <Outlet />}</div>
        </Content>

        {/* 底部 Tab Bar */}
        <nav className="cs-tablet-tabbar" role="tablist">
          {menuItems.map((m) => {
            const active = selectedKey === m.key;
            return (
              <button
                key={m.key}
                role="tab"
                aria-selected={active}
                className={`cs-tablet-tabbar__item${active ? " is-active" : ""}`}
                onClick={() => navigate(m.key)}
              >
                <span className="cs-tablet-tabbar__icon">{m.icon}</span>
                <span className="cs-tablet-tabbar__label">{m.label}</span>
              </button>
            );
          })}
        </nav>
      </Layout>
    );
  }

  // ===== 桌面布局：侧栏 =====
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        width={248}
        zeroWidthTriggerStyle={{ top: 12 }}
        style={{ background: colorBgContainer }}
      >
        <div style={{ padding: "22px 18px" }}>
          <Space align="center" size={10}>
            <Avatar
              size={44}
              style={{ background: "linear-gradient(135deg,#3b82f6,#10b981)" }}
              icon={<HeartOutlined />}
            />
            <div>
              <Title level={5} style={{ margin: 0, lineHeight: 1.1 }}>
                CarSoul
              </Title>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Guardian
              </Text>
            </div>
          </Space>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={openKeys}
          items={siderItems}
          onClick={({ key }) => {
            if (key === LAB_GROUP_KEY) return;
            navigate(key);
          }}
          style={{ borderInlineEnd: "none", padding: "4px 0" }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: colorBgContainer,
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #eef0f4",
          }}
        >
          <Text strong style={{ fontSize: 18 }}>
            CarSoul Guardian — 汽车生命守护智能体
          </Text>
          <Space>
            <span
              className="cs-gradient-text"
              style={{ fontWeight: 700, fontSize: 15 }}
            >
              CarSoul Guardian
            </span>
          </Space>
        </Header>
        <Content style={{ margin: 0 }}>
          <div className="cs-content-wrap">{children ?? <Outlet />}</div>
        </Content>
      </Layout>
    </Layout>
  );
}
