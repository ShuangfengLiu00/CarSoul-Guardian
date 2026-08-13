import { ReactNode, useEffect, useState } from "react";
import { Layout, Menu, theme, Avatar, Space, Typography, Select, Tooltip } from "antd";
import { Outlet } from "react-router-dom";
import {
  DashboardOutlined,
  RobotOutlined,
  CarOutlined,
  CrownOutlined,
  AlertOutlined,
  BookOutlined,
  FieldTimeOutlined,
  CompassOutlined,
  ShoppingOutlined,
  SoundOutlined,
  SafetyCertificateOutlined,
  ControlOutlined,
  ToolOutlined,
  AppstoreOutlined,
  HeartOutlined,
  RocketOutlined,
  ScanOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { RoleProvider, useRole, ROLE_OPTIONS, type Role } from "@/hooks";

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

/**
 * 主域导航（§三 信息架构）。默认着陆页 = 驾驶舱 `/`。
 * 注：`/life`（数字生命）、`/story`（故事模式）属实验能力，按规范不进主动线，
 * 路由保留、可经直达 URL 访问。
 */
const mainItems = [
  { key: "/", icon: <DashboardOutlined />, label: "驾驶舱 Cockpit" },
  { key: "/twin3d", icon: <ScanOutlined />, label: "3D 车辆检测" },
  { key: "/soul", icon: <CrownOutlined />, label: "我的车 Soul" },
  { key: "/vehicle", icon: <CarOutlined />, label: "车辆档案" },
  { key: "/risk", icon: <AlertOutlined />, label: "风险预测" },
  { key: "/agent", icon: <RobotOutlined />, label: "AI 助手" },
  { key: "/knowledge", icon: <BookOutlined />, label: "知识库" },
  { key: "/travel", icon: <CompassOutlined />, label: "出行地图" },
  { key: "/profile", icon: <CarOutlined />, label: "用车档案" },
  { key: "/buy", icon: <ShoppingOutlined />, label: "购车顾问" },
  { key: "/cabin", icon: <SoundOutlined />, label: "座舱陪伴" },
  { key: "/timeline", icon: <FieldTimeOutlined />, label: "时间轴" },
];

/** 治理与合规：分组可折叠。 */
const governItems = [
  { key: "/safety", icon: <SafetyCertificateOutlined />, label: "安全合规" },
  { key: "/governance", icon: <ControlOutlined />, label: "数据治理" },
  { key: "/simulator", icon: <ToolOutlined />, label: "仿真沙盘" },
  { key: "/sensors", icon: <DashboardOutlined />, label: "传感器总览" },
  { key: "/memory", icon: <HeartOutlined />, label: "记忆" },
  { key: "/evolution", icon: <RocketOutlined />, label: "进化引擎" },
  { key: "/portal", icon: <AppstoreOutlined />, label: "控制台" },
];

const GOVERN_KEY = "govern";

/**
 * 各角色在侧栏「治理与合规」分组中隐藏的路由。
 * 主域（mainItems）对所有角色一致；差异体现在治理分组。
 * - owner(C端车主)：隐藏运营/OEM 页（治理沙盘/传感器/仿真/进化/控制台），保留安全合规与记忆
 * - fleet(车队)：保留安全合规/治理/仿真/传感器，隐藏记忆/进化/控制台
 * - insurer(保险)：保留安全合规/治理，隐藏仿真/传感器/记忆/进化/控制台
 * - dealer(二手车商)：保留安全合规，隐藏治理/仿真/传感器/记忆/进化/控制台
 * - oem：全部可见
 */
const ROLE_NAV_HIDDEN: Record<Role, string[]> = {
  owner: ["/governance", "/simulator", "/sensors", "/evolution", "/portal"],
  fleet: ["/memory", "/evolution", "/portal"],
  insurer: ["/simulator", "/sensors", "/memory", "/evolution", "/portal"],
  dealer: ["/governance", "/simulator", "/sensors", "/memory", "/evolution", "/portal"],
  oem: [],
};

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
  return (
    <RoleProvider>
      <MainLayoutInner>{children}</MainLayoutInner>
    </RoleProvider>
  );
}

function MainLayoutInner({ children }: { children?: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isTablet = useIsTablet();
  const {
    token: { colorBgContainer },
  } = theme.useToken();
  const { role, setRole } = useRole();

  // 按角色过滤「治理与合规」分组的菜单项（主域对所有角色一致）。
  const hiddenNav = ROLE_NAV_HIDDEN[role];
  const visibleGovern = governItems.filter((i) => !hiddenNav.includes(i.key));
  const siderItems = visibleGovern.length
    ? [
        ...mainItems,
        {
          key: GOVERN_KEY,
          icon: <ControlOutlined />,
          label: "治理与合规",
          children: visibleGovern,
        },
      ]
    : [...mainItems];
  const ALL_ROUTE_ITEMS = [...mainItems, ...visibleGovern];
  const GOVERN_KEYS = visibleGovern.map((i) => i.key);

  // html[data-role] 驱动全站强调色（§七）；role 同时经 Context 下发给各页面做差异化披露
  useEffect(() => {
    document.documentElement.setAttribute("data-role", role);
  }, [role]);

  const selectedKey =
    ALL_ROUTE_ITEMS.find((m) => location.pathname.startsWith(m.key) && m.key !== "/")?.key ||
    (location.pathname === "/" ? "/" : "/");

  // 命中治理分组路由时自动展开「治理与合规」子菜单
  const openKeys = GOVERN_KEYS.includes(selectedKey) ? [GOVERN_KEY] : undefined;

  const RoleSwitcher = (
    <Select<Role>
      value={role}
      onChange={setRole}
      options={ROLE_OPTIONS}
      size="small"
      style={{ width: 172 }}
      aria-label="角色主题切换"
    />
  );

  const EngineDot = (
    <Tooltip title="预测引擎已连接（carModel :8000）">
      <Space size={6}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "var(--soul-400)",
            display: "inline-block",
            boxShadow: "0 0 8px rgba(45,212,191,.5)",
          }}
        />
        <Text type="secondary" style={{ fontSize: 12 }}>
          引擎在线
        </Text>
      </Space>
    </Tooltip>
  );

  // ===== 平板/手机布局：顶部 Header + 底部 Tab Bar =====
  if (isTablet) {
    return (
      <Layout className="holo-page cs-tablet-layout" style={{ minHeight: "100vh", background: "transparent" }}>
        <Header
          className="cs-tablet-header"
          style={{
            background: colorBgContainer,
            padding: "0 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid var(--line)",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <Space align="center" size={10}>
            <Avatar
              size={36}
              style={{ background: "linear-gradient(135deg,#14b8a6,#0d9488)" }}
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
          {RoleSwitcher}
        </Header>

        <Content style={{ margin: 0, flex: 1, paddingBottom: 72 }}>
          <div className="cs-content-wrap cs-content-wrap--tablet">{children ?? <Outlet />}</div>
        </Content>

        {/* 底部 Tab Bar（主域） */}
        <nav className="cs-tablet-tabbar" role="tablist">
          {mainItems.map((m) => {
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

  // ===== 桌面布局：侧栏（分组可折叠） =====
  return (
    <Layout className="holo-page" style={{ minHeight: "100vh", background: "transparent" }}>
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
              style={{ background: "linear-gradient(135deg,#14b8a6,#0d9488)" }}
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
            if (key === GOVERN_KEY) return;
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
            borderBottom: "1px solid var(--line)",
          }}
        >
          <Text strong style={{ fontSize: 18 }}>
            CarSoul Guardian — 汽车生命守护智能体
          </Text>
          <Space size={16}>
            {EngineDot}
            {RoleSwitcher}
          </Space>
        </Header>
        <Content style={{ margin: 0 }}>
          <div className="cs-content-wrap">{children ?? <Outlet />}</div>
        </Content>
      </Layout>
    </Layout>
  );
}
