/**
 * CarSoul Guardian Holographic Cockpit - Mock Data
 * Vehicle digital life data for holographic visualization
 */

import { createElement, type ReactNode } from "react";
import {
  PoweroffOutlined,
  RobotOutlined,
  CarOutlined,
  CompassOutlined,
  CrownOutlined,
  CustomerServiceOutlined,
  DashboardOutlined,
  DollarOutlined,
  EnvironmentOutlined,
  FallOutlined,
  FlagOutlined,
  HeartOutlined,
  SafetyOutlined,
  SettingOutlined,
  StarOutlined,
  StopOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  TrophyOutlined,
  WarningOutlined,
} from "@ant-design/icons";

// ===== Types =====
export interface VehicleTwin {
  id: string;
  name: string;
  model: string;
  health: number;
  age: number; // days
  mileage: number;
  battery: BatteryData;
  motor: MotorData;
  brake: BrakeData;
  tire: TireData;
  chassis: ChassisData;
  drivingDNA: DrivingDNA;
  memoryCount: number;
  lastUpdate: string;
}

export interface BatteryData {
  health: number;
  temperature: number;
  capacity: number;
  cycle: number;
  maxCycles: number;
  voltage: number;
  current: number;
  prediction: string;
  remainingLife: number;
  cells: { id: number; voltage: number; temp: number; health: number }[];
}

export interface MotorData {
  health: number;
  temperature: number;
  power: number;
  efficiency: number;
  rpm: number;
  torque: number;
}

export interface BrakeData {
  health: number;
  frontPad: number;
  rearPad: number;
  fluidLevel: number;
  frontPadPrediction: number;
}

export interface TireData {
  health: number;
  pressure: number;
  treadDepth: number;
  tires: {
    position: string;
    health: number;
    pressure: number;
    temp: number;
    tread: number;
    prediction: string;
  }[];
}

export interface ChassisData {
  health: number;
  suspension: number;
  steering: number;
  alignment: number;
}

export interface DrivingDNA {
  aggression: number;
  smoothness: number;
  energySaving: number;
  nightDriving: number;
  highwayRatio: number;
  personality: string;
  weeklyScore: number[];
}

export interface AgentInfo {
  id: string;
  name: string;
  nameCn: string;
  role: string;
  status: "idle" | "thinking" | "working";
  color: string;
  icon: ReactNode;
  tasksCompleted: number;
  monitoring: string;
  latestDecision: string;
  confidence: number;
  position: [number, number, number];
  orbitRadius: number;
  orbitSpeed: number;
}

export interface MemoryItem {
  id: string;
  time: string;
  type: "driving" | "maintenance" | "alert" | "emotion" | "milestone";
  content: string;
  aiLearning?: string;
  confidence?: number;
  icon: ReactNode;
}

export interface PredictionItem {
  component: string;
  currentValue: number;
  futureValue: number;
  unit: string;
  daysRemaining: number;
  risk: "low" | "medium" | "high";
  reason: string;
  suggestion: string;
}

export interface AlertItem {
  id: string;
  level: "info" | "warning" | "critical";
  title: string;
  detail: string;
  time: string;
  source: string;
}

export interface TimelineEvent {
  id: string;
  date: string;
  title: string;
  description: string;
  type: "birth" | "mileage" | "maintenance" | "alert" | "milestone";
  icon: ReactNode;
}

// ===== Mock Data =====

export const vehicleTwin: VehicleTwin = {
  id: "CSG-2025-0418",
  name: "星辰号",
  model: "Tesla Model Y Performance",
  health: 96,
  age: 438,
  mileage: 28456,
  battery: {
    health: 98,
    temperature: 32,
    capacity: 96,
    cycle: 420,
    maxCycles: 2000,
    voltage: 396.2,
    current: 12.5,
    prediction: "Healthy",
    remainingLife: 6.2,
    cells: Array.from({ length: 12 }, (_, i) => ({
      id: i + 1,
      voltage: 3.3 + Math.random() * 0.1,
      temp: 30 + Math.random() * 5,
      health: 95 + Math.random() * 5,
    })),
  },
  motor: {
    health: 97,
    temperature: 45,
    power: 358,
    efficiency: 94,
    rpm: 0,
    torque: 420,
  },
  brake: {
    health: 92,
    frontPad: 45,
    rearPad: 62,
    fluidLevel: 88,
    frontPadPrediction: 45,
  },
  tire: {
    health: 94,
    pressure: 2.5,
    treadDepth: 6.2,
    tires: [
      { position: "左前", health: 72, pressure: 2.4, temp: 38, tread: 5.2, prediction: "45天后建议更换" },
      { position: "右前", health: 75, pressure: 2.5, temp: 36, tread: 5.5, prediction: "60天后建议更换" },
      { position: "左后", health: 88, pressure: 2.5, temp: 35, tread: 7.1, prediction: "状态良好" },
      { position: "右后", health: 90, pressure: 2.5, temp: 34, tread: 7.3, prediction: "状态良好" },
    ],
  },
  chassis: {
    health: 95,
    suspension: 94,
    steering: 96,
    alignment: 93,
  },
  drivingDNA: {
    aggression: 35,
    smoothness: 82,
    energySaving: 76,
    nightDriving: 22,
    highwayRatio: 45,
    personality: "城市效率型",
    weeklyScore: [88, 92, 85, 90, 94, 87, 96],
  },
  memoryCount: 128432,
  lastUpdate: "2026-08-02 14:30",
};

export const agents: AgentInfo[] = [
  {
    id: "manager",
    name: "Manager Agent",
    nameCn: "守护指挥官",
    role: "总调度与决策",
    status: "working",
    color: "#a855f7",
    icon: createElement(CrownOutlined),
    tasksCompleted: 1523,
    monitoring: "全车系统",
    latestDecision: "调度电池Agent进行温度异常分析",
    confidence: 0.96,
    position: [0, 0, 0],
    orbitRadius: 0,
    orbitSpeed: 0,
  },
  {
    id: "battery",
    name: "Battery Agent",
    nameCn: "电池守护者",
    role: "电池健康监测",
    status: "working",
    color: "#00ff9d",
    icon: createElement(PoweroffOutlined),
    tasksCompleted: 384,
    monitoring: "12电芯 · 温度 · 容量",
    latestDecision: "检测到3号电芯温度偏高0.8°C",
    confidence: 0.93,
    position: [3, 0, 0],
    orbitRadius: 3,
    orbitSpeed: 0.3,
  },
  {
    id: "motor",
    name: "Motor Agent",
    nameCn: "动力守护者",
    role: "电机效率监控",
    status: "idle",
    color: "#3b82f6",
    icon: createElement(ThunderboltOutlined),
    tasksCompleted: 256,
    monitoring: "功率 · 扭矩 · 温度",
    latestDecision: "电机效率稳定在94%",
    confidence: 0.97,
    position: [2.1, 0, 2.1],
    orbitRadius: 3,
    orbitSpeed: 0.25,
  },
  {
    id: "brake",
    name: "Brake Agent",
    nameCn: "制动守护者",
    role: "刹车系统监测",
    status: "thinking",
    color: "#ffb800",
    icon: createElement(StopOutlined),
    tasksCompleted: 198,
    monitoring: "刹车片 · 液位",
    latestDecision: "前刹车片磨损达55%，建议关注",
    confidence: 0.89,
    position: [0, 0, 3],
    orbitRadius: 3,
    orbitSpeed: 0.2,
  },
  {
    id: "tire",
    name: "Tire Agent",
    nameCn: "轮胎守护者",
    role: "胎压与磨损",
    status: "working",
    color: "#00f0ff",
    icon: createElement(DashboardOutlined),
    tasksCompleted: 312,
    monitoring: "4轮胎压 · 胎纹",
    latestDecision: "左前轮胎纹偏低，预测45天需更换",
    confidence: 0.91,
    position: [-2.1, 0, 2.1],
    orbitRadius: 3,
    orbitSpeed: 0.35,
  },
  {
    id: "chassis",
    name: "Chassis Agent",
    nameCn: "底盘守护者",
    role: "悬挂与底盘",
    status: "idle",
    color: "#6366f1",
    icon: createElement(SettingOutlined),
    tasksCompleted: 142,
    monitoring: "悬挂 · 转向 · 对中",
    latestDecision: "底盘状态稳定",
    confidence: 0.95,
    position: [-3, 0, 0],
    orbitRadius: 3,
    orbitSpeed: 0.15,
  },
  {
    id: "safety",
    name: "Safety Agent",
    nameCn: "安全守护者",
    role: "安全风险评估",
    status: "working",
    color: "#ff3860",
    icon: createElement(SafetyOutlined),
    tasksCompleted: 445,
    monitoring: "碰撞 · 安全带 · 气囊",
    latestDecision: "过去30天急刹增加18%",
    confidence: 0.88,
    position: [-2.1, 0, -2.1],
    orbitRadius: 3,
    orbitSpeed: 0.28,
  },
  {
    id: "health",
    name: "Health Agent",
    nameCn: "健康分析师",
    role: "综合健康评估",
    status: "thinking",
    color: "#10b981",
    icon: createElement(HeartOutlined),
    tasksCompleted: 367,
    monitoring: "全车健康指数",
    latestDecision: "综合健康度96%，优于同级85%",
    confidence: 0.94,
    position: [0, 0, -3],
    orbitRadius: 3,
    orbitSpeed: 0.22,
  },
  {
    id: "repair",
    name: "Repair Agent",
    nameCn: "维修规划师",
    role: "维修任务规划",
    status: "idle",
    color: "#f59e0b",
    icon: createElement(ToolOutlined),
    tasksCompleted: 89,
    monitoring: "维修计划 · 预约",
    latestDecision: "生成前刹车片更换方案",
    confidence: 0.92,
    position: [2.1, 0, -2.1],
    orbitRadius: 3,
    orbitSpeed: 0.18,
  },
  {
    id: "memory",
    name: "Memory Agent",
    nameCn: "记忆管理者",
    role: "车辆记忆管理",
    status: "working",
    color: "#ec4899",
    icon: createElement(RobotOutlined),
    tasksCompleted: 128432,
    monitoring: "128,432条记忆",
    latestDecision: "记录今日驾驶行为数据",
    confidence: 0.99,
    position: [3, 0, 0],
    orbitRadius: 3,
    orbitSpeed: 0.3,
  },
  {
    id: "finance",
    name: "Finance Agent",
    nameCn: "价值评估师",
    role: "车辆价值预测",
    status: "idle",
    color: "#8b5cf6",
    icon: createElement(DollarOutlined),
    tasksCompleted: 56,
    monitoring: "残值 · 保险",
    latestDecision: "当前估值28.5万，年衰减率8.2%",
    confidence: 0.90,
    position: [0, 0, 3],
    orbitRadius: 3,
    orbitSpeed: 0.12,
  },
];

export const memories: MemoryItem[] = [
  {
    id: "m1",
    time: "2026-08-02 14:30",
    type: "driving",
    content: "今日通勤驾驶32km，平均能耗14.2kWh/100km，能效评分A+",
    aiLearning: "用户已连续7天保持低能耗驾驶模式",
    confidence: 95,
    icon: createElement(CarOutlined),
  },
  {
    id: "m2",
    time: "2026-08-01 09:15",
    type: "alert",
    content: "检测到3号电芯温度偏高0.8°C，已自动启动散热策略",
    aiLearning: "可能与上周快充频率增加有关",
    confidence: 87,
    icon: createElement(WarningOutlined),
  },
  {
    id: "m3",
    time: "2026-07-30 18:00",
    type: "driving",
    content: "用户在下坡路段频繁急刹，单次行程急刹6次",
    aiLearning: "建议启用动能回收强档模式",
    confidence: 92,
    icon: createElement(FallOutlined),
  },
  {
    id: "m4",
    time: "2026-07-28 10:00",
    type: "maintenance",
    content: "完成第4次常规保养：空调滤芯更换、轮胎换位",
    aiLearning: "下次保养建议在32,000km时进行",
    confidence: 96,
    icon: createElement(ToolOutlined),
  },
  {
    id: "m5",
    time: "2026-07-25 22:30",
    type: "emotion",
    content: "夜间行驶时播放轻音乐，驾驶风格明显平稳",
    aiLearning: "音乐有助于改善驾驶习惯",
    confidence: 78,
    icon: createElement(CustomerServiceOutlined),
  },
  {
    id: "m6",
    time: "2026-07-20 08:00",
    type: "milestone",
    content: "累计行驶里程突破25,000km",
    aiLearning: "车辆进入稳定期，各项指标表现优异",
    confidence: 100,
    icon: createElement(TrophyOutlined),
  },
  {
    id: "m7",
    time: "2026-07-15 14:00",
    type: "driving",
    content: "长途出行500km，全程自动驾驶辅助开启",
    aiLearning: "高速场景AP使用率达92%",
    confidence: 94,
    icon: createElement(CompassOutlined),
  },
  {
    id: "m8",
    time: "2026-07-10 11:30",
    type: "alert",
    content: "左前轮胎压低于标准值0.2bar，建议补气",
    aiLearning: "近一个月胎压波动在正常范围内",
    confidence: 88,
    icon: createElement(DashboardOutlined),
  },
];

export const predictions: PredictionItem[] = [
  {
    component: "前刹车片",
    currentValue: 45,
    futureValue: 20,
    unit: "%",
    daysRemaining: 45,
    risk: "medium",
    reason: "过去30天急刹频率增加18%，加速刹车片磨损",
    suggestion: "建议45天内预约更换前刹车片",
  },
  {
    component: "左前轮胎",
    currentValue: 72,
    futureValue: 50,
    unit: "%",
    daysRemaining: 60,
    risk: "medium",
    reason: "胎纹深度5.2mm，磨损速率略高于平均值",
    suggestion: "建议60天后检查并考虑更换",
  },
  {
    component: "电池容量",
    currentValue: 96,
    futureValue: 90,
    unit: "%",
    daysRemaining: 365,
    risk: "low",
    reason: "衰减率0.8%/年，优于行业平均1.5%",
    suggestion: "保持良好的充电习惯，预计6.2年后到达80%",
  },
  {
    component: "变速箱油",
    currentValue: 85,
    futureValue: 60,
    unit: "%",
    daysRemaining: 120,
    risk: "low",
    reason: "油液状态良好，按保养周期更换即可",
    suggestion: "下次保养时一并更换",
  },
];

export const alerts: AlertItem[] = [
  {
    id: "a1",
    level: "warning",
    title: "电池温度异常趋势",
    detail: "3号电芯温度持续偏高0.8°C，已启动主动散热",
    time: "2分钟前",
    source: "Battery Agent",
  },
  {
    id: "a2",
    level: "warning",
    title: "前刹车片磨损预警",
    detail: "磨损达55%，预测45天后需更换",
    time: "1小时前",
    source: "Brake Agent",
  },
  {
    id: "a3",
    level: "info",
    title: "长途出行检查完成",
    detail: "检测到7项注意事项，已生成出行报告",
    time: "3小时前",
    source: "Manager Agent",
  },
  {
    id: "a4",
    level: "info",
    title: "保养提醒",
    detail: "距下次保养还有3,544km",
    time: "昨天",
    source: "Repair Agent",
  },
];

export const timelineEvents: TimelineEvent[] = [
  {
    id: "t1",
    date: "2025-06-20",
    title: "车辆诞生",
    description: "CarSoul Guardian 系统初始化，开始记录车辆数字生命",
    type: "birth",
    icon: createElement(StarOutlined),
  },
  {
    id: "t2",
    date: "2025-06-20",
    title: "首次驾驶",
    description: "行驶里程0→12km，系统完成首次自检与标定",
    type: "mileage",
    icon: createElement(CarOutlined),
  },
  {
    id: "t3",
    date: "2025-08-15",
    title: "5,000km 里程碑",
    description: "首次保养完成，各项指标优异",
    type: "mileage",
    icon: createElement(FlagOutlined),
  },
  {
    id: "t4",
    date: "2025-12-01",
    title: "10,000km",
    description: "第二次保养，轮胎换位，刹车系统检查",
    type: "mileage",
    icon: createElement(FlagOutlined),
  },
  {
    id: "t5",
    date: "2026-03-10",
    title: "首次长途旅行",
    description: "单次行程820km，系统全程守护",
    type: "milestone",
    icon: createElement(CompassOutlined),
  },
  {
    id: "t6",
    date: "2026-05-20",
    title: "20,000km",
    description: "第三次保养，系统升级至V2.0",
    type: "mileage",
    icon: createElement(FlagOutlined),
  },
  {
    id: "t7",
    date: "2026-08-02",
    title: "现在",
    description: "28,456km · 健康度96% · 438天陪伴",
    type: "milestone",
    icon: createElement(EnvironmentOutlined),
  },
  {
    id: "t8",
    date: "2026-09-15",
    title: "预计保养",
    description: "前刹车片更换 · 32,000km保养",
    type: "maintenance",
    icon: createElement(ToolOutlined),
  },
];

export const healthRadarData = [
  { name: "电池", value: 98, fullMark: 100 },
  { name: "电机", value: 97, fullMark: 100 },
  { name: "制动", value: 92, fullMark: 100 },
  { name: "轮胎", value: 94, fullMark: 100 },
  { name: "底盘", value: 95, fullMark: 100 },
  { name: "安全", value: 96, fullMark: 100 },
];

export const batteryTrendData = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  health: 98 - i * 0.02 + Math.random() * 0.1,
  temp: 30 + Math.sin(i / 5) * 3 + Math.random() * 2,
}));

export const valuePredictionData = [
  { year: "2025", value: 100 },
  { year: "2026", value: 92 },
  { year: "2027", value: 84 },
  { year: "2028", value: 76 },
  { year: "2029", value: 68 },
  { year: "2030", value: 60 },
];

// Helper: get color by health value
export function getHealthColor(health: number): string {
  if (health >= 90) return "#00ff9d";
  if (health >= 75) return "#00f0ff";
  if (health >= 60) return "#ffb800";
  return "#ff3860";
}

export function getHealthLabel(health: number): string {
  if (health >= 90) return "优秀";
  if (health >= 75) return "良好";
  if (health >= 60) return "注意";
  return "危险";
}

export function getRiskColor(risk: string): string {
  switch (risk) {
    case "low": return "#00ff9d";
    case "medium": return "#ffb800";
    case "high": return "#ff3860";
    default: return "#94a3b8";
  }
}
