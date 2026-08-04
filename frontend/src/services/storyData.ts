/**
 * Story Mode mock data for TASK011 · Demo 场景包装.
 *
 * All data is simulated — the story mode must run without a backend so the
 * 5-minute demo is always reliable on stage.
 */

// ---- Act timeline (ms) ----
export const ACT_DURATIONS = [50_000, 50_000, 70_000, 60_000, 80_000] as const;
export const ACT_COUNT = 5;

export interface ActMeta {
  index: number;
  tag: string;
  timecode: string;
  title: string;
  subtitle: string;
  theme: "calm" | "warn" | "danger" | "ok";
}

export const ACTS: ActMeta[] = [
  {
    index: 0,
    tag: "ACT 1",
    timecode: "0:00 – 0:50",
    title: "车辆数字生命首页",
    subtitle: "深夜 · 一切正常 · CarSoul 默默守护",
    theme: "calm",
  },
  {
    index: 1,
    tag: "ACT 2",
    timecode: "0:50 – 1:40",
    title: "异常出现",
    subtitle: "电池温度攀升 · 冷却效率下降 · 剪刀差形成",
    theme: "warn",
  },
  {
    index: 2,
    tag: "ACT 3",
    timecode: "1:40 – 2:50",
    title: "CarSoul Agent 分析",
    subtitle: "三条推理链 · 趋势 → 关联 → 知识匹配",
    theme: "warn",
  },
  {
    index: 3,
    tag: "ACT 4",
    timecode: "2:50 – 3:50",
    title: "AI 主动保护",
    subtitle: "风险指数 0.68 · 主动推送 · 深夜守护",
    theme: "danger",
  },
  {
    index: 4,
    tag: "ACT 5",
    timecode: "3:50 – 5:10",
    title: "数字生命成长",
    subtitle: "闭环归档 · 模型进化 · 数字生命持续成长",
    theme: "ok",
  },
];

// ---- Act 1: Vehicle status cards ----
export interface StatusCard {
  key: string;
  label: string;
  value: string;
  unit?: string;
  ok: boolean;
}

export const ACT1_STATUS: StatusCard[] = [
  { key: "battery", label: "电池健康", value: "96", unit: "% SOH", ok: true },
  { key: "motor", label: "电机状态", value: "98", unit: "% 效率", ok: true },
  { key: "brake", label: "制动状态", value: "72", unit: "% 余量", ok: true },
  { key: "software", label: "软件版本", value: "V2.4.1", unit: "最新", ok: true },
];

export const ACT1_HEALTH_SCORE = 92;

// ---- Act 2: Battery temperature & cooling efficiency curves ----
export interface TempPoint {
  time: string;
  label: string;
  temp: number;
  cooling: number;
  note?: string;
}

export const BATTERY_CURVE: TempPoint[] = [
  { time: "23:30", label: "T-0", temp: 32, cooling: 91, note: "正常区间" },
  { time: "23:40", label: "T-10", temp: 32, cooling: 90 },
  { time: "23:52", label: "T-22", temp: 38, cooling: 82, note: "温度上升" },
  { time: "00:00", label: "T-30", temp: 41, cooling: 73 },
  { time: "00:05", label: "T-35", temp: 43, cooling: 67, note: "超出历史均值" },
  { time: "00:10", label: "T-40", temp: 45, cooling: 61 },
];

export const ACT2_HIGHLIGHTS = [
  { time: "23:40", temp: 32, status: "正常区间", color: "#2A9D8F" },
  { time: "23:52", temp: 38, status: "温度上升", color: "#F77F00" },
  { time: "00:05", temp: 43, status: "超出历史均值", color: "#E76F51" },
];

// ---- Act 3: Multi-Agent Expert Panel (新增·交叉验证) ----
export interface ExpertOpinion {
  key: string;
  name: string;
  specialty: string;
  icon: string;
  severity: "info" | "warn" | "danger";
  finding: string;
  crossCheck: string;
  color: string;
}

export const EXPERT_PANEL: ExpertOpinion[] = [
  {
    key: "powertrain",
    name: "动力系统专家",
    specialty: "电池·电机·电控",
    icon: "🔋",
    severity: "danger",
    finding: "电池温度 25 分钟内攀升 11℃，升温速率为历史均值的 3.2 倍，符合热失控早期征兆特征。",
    crossCheck: "→ 请求电气专家验证温度传感器读数可靠性",
    color: "#E76F51",
  },
  {
    key: "electrical",
    name: "电气系统专家",
    specialty: "传感器·线束·BMS",
    icon: "⚡",
    severity: "warn",
    finding: "交叉验证 3 路温度传感器读数一致，排除传感器误报。冷却效率从 91% 降至 67%，确认冷却响应不足。",
    crossCheck: "→ 确认动力专家数据可信，冷却异常属实",
    color: "#F77F00",
  },
  {
    key: "chassis",
    name: "底盘系统专家",
    specialty: "悬挂·制动·转向",
    icon: "🛞",
    severity: "info",
    finding: "未发现底盘系统相关异常，制动/转向/悬挂数据均在正常区间。",
    crossCheck: "→ 排除底盘因素，缩小诊断范围",
    color: "#00A8E8",
  },
  {
    key: "driving",
    name: "驾驶行为专家",
    specialty: "驾驶风格·工况",
    icon: "🚗",
    severity: "info",
    finding: "近期驾驶风格平稳，无激烈驾驶记录。车辆处于静止停放状态，非人为因素导致温升。",
    crossCheck: "→ 排除驾驶行为因素",
    color: "#00A8E8",
  },
  {
    key: "maintenance",
    name: "保养规划专家",
    specialty: "维保·里程·寿命",
    icon: "📅",
    severity: "warn",
    finding: "里程 18,523 km 接近保养节点，上次冷却系统检查距今 8 个月，建议合并冷却检测。",
    crossCheck: "→ 补充维保历史，支持冷却系统老化假设",
    color: "#F77F00",
  },
];

export const CROSS_VALIDATION_SUMMARY =
  "五专科专家并行会诊完成交叉验证：动力专家发现异常 → 电气专家确认数据可信 → 底盘/驾驶专家排除其他因素 → 保养专家补充维保历史。会诊结论：动力电池热风险前置信号，非误报。";

// ---- Act 3: Reasoning chains ----
export interface ReasoningChain {
  id: number;
  label: string;
  title: string;
  content: string;
  severity: "info" | "warn" | "danger";
  metric?: string;
}

export const REASONING_CHAINS: ReasoningChain[] = [
  {
    id: 1,
    label: "推理链 1 · 趋势识别",
    title: "电池温度持续升高",
    content:
      "过去 25 分钟内电池温度持续升高 11℃，升温速率 0.44℃/min，超过该车型历史均值的 3.2 倍。",
    severity: "warn",
    metric: "+11℃ / 25min",
  },
  {
    id: 2,
    label: "推理链 2 · 系统关联",
    title: "冷却系统效率下降",
    content:
      "冷却系统效率从 91% 下降至 67%，与温度上升呈负相关。冷却响应不足，无法有效散热。",
    severity: "warn",
    metric: "91% → 67%",
  },
  {
    id: 3,
    label: "推理链 3 · 知识库匹配",
    title: "匹配热风险前置特征",
    content:
      "匹配知识库条目 KB-BMS-014：动力电池温度持续上升且冷却效率下降，符合「热风险前置特征」，历史案例中 73% 在 2 小时内发展为热失控预警。",
    severity: "danger",
    metric: "KB-BMS-014 · 73%",
  },
];

export const AGENT_JUDGMENT =
  "综合温度趋势、冷却系统响应、历史模式比对，当前存在动力电池热风险前置信号。尚未发生故障，但风险概率显著高于正常水平。";

// ---- Act 4: Risk assessment & notification ----
export const RISK_INDEX = 0.68;
export const RISK_LEVEL = "中高风险";

export interface PushNotification {
  appName: string;
  time: string;
  title: string;
  body: string;
  riskLevel: string;
  currentTemp: string;
  suggestion: string;
}

export const PUSH_NOTIFICATION: PushNotification = {
  appName: "CarSoul Guardian",
  time: "00:12",
  title: "⚠️ 车辆电池温度异常升高趋势",
  body: "您的车辆检测到动力电池温度异常升高趋势，目前未发生故障，但建议尽快检查车辆状态。",
  riskLevel: "中高风险",
  currentTemp: "43℃（持续上升中）",
  suggestion: "明日优先前往服务中心检测冷却系统",
};

// ---- Act 5: Service closure ----
export interface ClosureItem {
  key: string;
  title: string;
  description: string;
  icon: string;
  status: string;
}

export const CLOSURE_ITEMS: ClosureItem[] = [
  {
    key: "report",
    title: "车辆健康报告",
    description:
      "包含异常原因、风险等级、建议措施、历史对比，自动归档至车辆生命周期档案。",
    icon: "📄",
    status: "已生成 · 已归档",
  },
  {
    key: "notify",
    title: "通知车主",
    description:
      "推送已送达，车主次日早晨打开 App 即可查看完整报告与建议。",
    icon: "📱",
    status: "已送达 · 已读",
  },
  {
    key: "service",
    title: "连接服务中心",
    description:
      "模拟工单已生成，服务中心收到冷却系统检测建议，可提前备件。",
    icon: "🔧",
    status: "工单已创建",
  },
];

export const FINAL_HEALTH_SCORE = 87;
export const FINAL_STATUS = "关注中";

// ---- Act 5 (NEW): Digital Life Growth ----
export interface GrowthItem {
  key: string;
  title: string;
  description: string;
  icon: string;
  delta: string;
}

export const DIGITAL_LIFE_GROWTH: GrowthItem[] = [
  {
    key: "lifecycle",
    title: "生命周期事件归档",
    description: "本次热风险守护全过程写入车辆生命周期档案，成为可追溯的成长记忆。",
    icon: "🧬",
    delta: "累计事件 +1",
  },
  {
    key: "model",
    title: "风险预测模型更新",
    description: "AI 从本次冷却效率衰减模式中学习，热风险前置识别基线已校准。",
    icon: "📈",
    delta: "识别精度提升",
  },
  {
    key: "behavior",
    title: "驾驶行为画像刷新",
    description: "结合近期驾驶风格与工况数据，个性化健康基线同步更新。",
    icon: "🧠",
    delta: "画像基线 +1",
  },
  {
    key: "twin",
    title: "数字孪生进化",
    description: "数字孪生体与实体车辆状态同步，冷却系统健康权重重新平衡。",
    icon: "🔄",
    delta: "孪生同步",
  },
];

export const GUARDIAN_MEMORY = {
  totalEvents: 47,
  lifecycleRecords: 312,
  growthDays: 186,
};

// ---- Act 5 (NEW): Agent Dynamic Adaptation · 自纠错 ----
export interface AdaptationStep {
  key: string;
  step: string;
  title: string;
  content: string;
  icon: string;
  color: string;
}

export const AGENT_ADAPTATION: {
  title: string;
  subtitle: string;
  steps: AdaptationStep[];
  outcome: string;
} = {
  title: "Agent 动态调整 · 自纠错",
  subtitle: "维修反馈 → 重新学习 → 模型更新 → 下次更准",
  steps: [
    {
      key: "feedback",
      step: "01",
      title: "维修反馈回流",
      content:
        "服务中心检测完毕：冷却液位偏低导致散热效率下降，非电池热失控。实际风险等级低于 Agent 预测。",
      icon: "🔧",
      color: "#F77F00",
    },
    {
      key: "learn",
      step: "02",
      title: "Agent 重新学习",
      content:
        "Agent 对比预测结果与实际维修结论，识别偏差来源：未将冷却液位纳入热风险评估维度。",
      icon: "🧠",
      color: "#00A8E8",
    },
    {
      key: "update",
      step: "03",
      title: "风险模型更新",
      content:
        "热风险预测模型新增「冷却液位」辅助判断维度，冷却效率衰减权重从 0.3 调整至 0.2。",
      icon: "📈",
      color: "#2A9D8F",
    },
    {
      key: "correct",
      step: "04",
      title: "下次更准",
      content:
        "阈值已校准。类似工况下 Agent 将先检查冷却液位再判断热风险，预测精度提升 23%。",
      icon: "✅",
      color: "#2A9D8F",
    },
  ],
  outcome:
    "这不是一次性报警，而是一个会从经验中学习、持续进化的 Agent。",
};

// ---- Why Agent? (NEW) ----
export const WHY_AGENT = {
  question: "为什么一定要用 Agent？",
  answer:
    "车辆健康管理不是一次性问题——它需要每天感知数据、持续学习驾驶习惯、结合维修历史与知识库综合推理、动态调整建议，并不断更新数字生命。规则引擎做不到，单次聊天也做不到，这必须是一个持续工作的 Agent。",
  points: [
    { label: "持续", text: "7×24 感知，非触发才工作" },
    { label: "多步", text: "感知 → 会诊 → 预测 → 干预 → 成长" },
    { label: "综合推理", text: "跨系统关联 + 知识库 + 历史模式" },
  ],
};

// ---- Platform architecture chain (NEW) ----
export const ARCHITECTURE_CHAIN = [
  "数字孪生",
  "车辆记忆",
  "知识引擎",
  "AI Agent",
  "工作流",
  "生命周期库",
  "持续成长",
];

export const CLOSING_TAGLINE = "每一次守护，都让数字生命成长一步。";
export const CLOSING_BRAND = "CarSoul · 车辆数字生命系统";
export const CLOSING_SUBTITLE = "Vehicle Digital Life System";

// ---- Vehicle info for story context ----
export const STORY_VEHICLE = {
  brand: "领克",
  model: "08 EM-P",
  year: 2024,
  vin: "L6T79L4X9PE890123",
  mileage: 18523,
  batteryCapacity: "39.8 kWh",
  owner: "张先生",
  parkingLocation: "地下停车场 B2-037",
};
