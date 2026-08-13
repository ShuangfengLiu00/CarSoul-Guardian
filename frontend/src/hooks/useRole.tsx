import { createContext, useContext, useState, type ReactNode } from "react";

/**
 * 全局客户角色 Context（§二 / §七）。
 *
 * 五角色对应五类客户视角，披露粒度不同：
 *   owner   C 端车主   —— 只看健康建议，不暴露技术细节
 *   fleet   车队运营   —— 关注处理状态与 ETA（运营闭环）
 *   insurer 保险       —— 关注风险概率与出险评级（精算）
 *   dealer  二手车商   —— 关注车况等级与残值影响
 *   oem     OEM        —— 全量技术参数与质量追溯
 *
 * 注意：此前 role 仅是 MainLayout 的局部 state、只驱动 CSS 强调色（"仅换色不换骨架"），
 * 数据层从未读取，导致"切换角色数据不变"。本 Context 把它提升为全局共享状态，
 * 让页面能按角色做差异化披露。
 */
export type Role = "owner" | "fleet" | "insurer" | "dealer" | "oem";

interface RoleContextValue {
  role: Role;
  setRole: (r: Role) => void;
}

const RoleContext = createContext<RoleContextValue | null>(null);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>("owner");
  return <RoleContext.Provider value={{ role, setRole }}>{children}</RoleContext.Provider>;
}

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error("useRole 必须在 <RoleProvider> 内使用");
  return ctx;
}

/** 角色中文标签（用于界面与横幅）。 */
export const ROLE_LABELS: Record<Role, string> = {
  owner: "C 端车主",
  fleet: "车队运营",
  insurer: "保险",
  dealer: "二手车商",
  oem: "OEM",
};

/** 角色选项（供 Select 使用）。 */
export const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "owner", label: "C 端车主 · 灵魂绿" },
  { value: "fleet", label: "车队运营 · 电光蓝" },
  { value: "insurer", label: "保险 · 琥珀" },
  { value: "dealer", label: "二手车商 · 琥珀" },
  { value: "oem", label: "OEM · 灵魂绿" },
];

/**
 * 每角色的披露策略。页面据此决定是否显示某些字段，
 * 从而让"切换角色"真正改变用户看到的数据，而非只换配色。
 */
export interface RoleDisclosure {
  /** 顶部视角横幅文案。 */
  perspective: string;
  /** 是否显示「风险概率 %」标签。 */
  showProbability: boolean;
  /** 是否显示技术字段（异常数、推理轨迹、原始故障类型）。OEM 全开。 */
  showTechnical: boolean;
  /** 是否显示内部 KPI（准确率、误报率、已反馈样本）。C 端 / 二手车商隐藏。 */
  showInternalKpi: boolean;
  /** 是否显示出险反馈结果（actual_outcome）。 */
  showOutcome: boolean;
}

export const ROLE_DISCLOSURE: Record<Role, RoleDisclosure> = {
  owner: {
    perspective: "C 端车主视角 · 只看健康建议与风险等级，不暴露技术细节与内部指标",
    showProbability: true,
    showTechnical: false,
    showInternalKpi: false,
    showOutcome: true,
  },
  fleet: {
    perspective: "车队运营视角 · 关注处理状态、ETA 与模型自校准 KPI",
    showProbability: true,
    showTechnical: false,
    showInternalKpi: true,
    showOutcome: true,
  },
  insurer: {
    perspective: "保险视角 · 关注风险概率、出险评级与反馈结果（精算口径）",
    showProbability: true,
    showTechnical: false,
    showInternalKpi: true,
    showOutcome: true,
  },
  dealer: {
    perspective: "二手车商视角 · 关注车况等级、恶化趋势与残值影响",
    showProbability: true,
    showTechnical: false,
    showInternalKpi: false,
    showOutcome: true,
  },
  oem: {
    perspective: "OEM 视角 · 全量技术参数、异常数与推理轨迹（质量追溯）",
    showProbability: true,
    showTechnical: true,
    showInternalKpi: true,
    showOutcome: true,
  },
};
