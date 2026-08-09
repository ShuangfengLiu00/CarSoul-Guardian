/**
 * DemoBadge — 演示/数据性质分级角标（全站唯一来源，条件式）
 *
 * 对应 GOAI 红线2：消除"虚假演示"隐患。双维度设计：
 *   - `level`：数据性质分级（L0 真数据 / L1 预测标注 / L2b 持久虚构车 / L3 无后端demo）
 *   - `visible`：显隐开关（保留"是否挂载"这第二维度，避免无条件挂载）
 *
 * ⚠️ 双向失真都是违规，二者同等严重：
 *   - 正向失真：用模拟数据却不标注 → 把假的说成真的
 *   - 反向失真：用真实接口数据却挂角标 → 把真的说成假的
 * 因此 `level` 必填；`level="L0"`（真数据）时组件恒返回 null，绝不给真实数据挂角标。
 *
 * 用法（v1.1）：
 *   <DemoBadge level="L3" visible />              // 恒定无后端 demo 页（如 /evolution、/story、/simulator、/memory）
 *   <DemoBadge level="L2b" visible />             // 持久虚构车（如 /timeline，后端恒 demo_mode=true）
 *   <DemoBadge level="L2" visible={usingDemo} />  // 条件式：后端存在，仅当未连通才回落演示数据（如 /dashboard）
 *   <DemoBadge level="L1" visible />              // 预测标注（模型概率性输出，非确定性事实）
 *   <DemoBadge level="L0" visible />              // 真数据：组件返回 null，不渲染
 *
 * 分级说明：
 *   - L0 真数据：真实接口返回，无任何模拟/占位，不挂角标。
 *   - L1 预测标注：模型预测结果，属概率性推断，非确定性事实。
 *   - L2b 持久虚构车：后端恒 demo_mode=true，返回确定性占位（持久虚构车），不代表真实车辆。
 *   - L3 无后端demo：无后端、纯前端动画/占位，仅用于功能演示。
 */
import { Tag, Tooltip } from "antd";
import {
  InfoCircleOutlined,
  WarningOutlined,
  ExperimentOutlined,
  ApiOutlined,
} from "@ant-design/icons";

export type DemoLevel = "L0" | "L1" | "L2" | "L2b" | "L3";

export type DemoBadgePosition =
  | "top-right"
  | "top-left"
  | "bottom-right"
  | "bottom-left"
  | "inline";

interface LevelMeta {
  color: string;
  text: string;
  tooltip: string;
  icon: React.ReactNode;
}

const LEVEL_META: Record<DemoLevel, LevelMeta> = {
  // L0 不渲染，meta 仅为占位。
  L0: { color: "default", text: "", tooltip: "", icon: null },
  L1: {
    color: "gold",
    text: "预测标注 · 模型输出",
    tooltip:
      "本页展示模型预测结果，属概率性推断而非确定性事实，请结合专业检修机构结论判断。",
    icon: <WarningOutlined />,
  },
  L2: {
    color: "blue",
    text: "演示回落 · 后端未连通",
    tooltip:
      "后端存在但当前未连通，已回落到演示数据；后端恢复后角标自动消失（条件式标注，非恒定 demo）。",
    icon: <ApiOutlined />,
  },
  L2b: {
    color: "orange",
    text: "持久虚构车 · 演示数据",
    tooltip:
      "后端恒为 demo_mode=true，返回确定性占位数据（持久虚构车）。本页不代表真实车辆状态。",
    icon: <ExperimentOutlined />,
  },
  L3: {
    color: "red",
    text: "演示模式 · 模拟数据",
    tooltip:
      "本页面为无后端纯前端演示，使用模拟数据，仅用于功能展示，不代表真实车辆状态。",
    icon: <InfoCircleOutlined />,
  },
};

interface DemoBadgeProps {
  /** 数据性质分级：L0 真数据 / L1 预测标注 / L2b 持久虚构车 / L3 无后端demo。必填。 */
  level: DemoLevel;
  /** 是否挂载角标（第二维度：显隐开关）。默认 true。L0 恒不显示，与此无关。 */
  visible?: boolean;
  /** 显示位置，默认 "top-right" */
  position?: DemoBadgePosition;
  /** 是否行内显示（放在标题旁），等价于 position="inline" */
  inline?: boolean;
  /** 自定义文本，覆盖分级默认文案 */
  text?: string;
}

const FIXED_STYLES: Record<Exclude<DemoBadgePosition, "inline">, React.CSSProperties> = {
  "top-right": { position: "fixed", top: 16, right: 24, zIndex: 1000 },
  "top-left": { position: "fixed", top: 16, left: 24, zIndex: 1000 },
  "bottom-right": { position: "fixed", bottom: 16, right: 24, zIndex: 1000 },
  "bottom-left": { position: "fixed", bottom: 16, left: 24, zIndex: 1000 },
};

export default function DemoBadge({
  level,
  visible = true,
  position = "top-right",
  inline = false,
  text,
}: DemoBadgeProps) {
  // L0 真数据：永远不挂角标（反向失真红线）。visible 对 L0 无效。
  if (level === "L0") return null;
  // 非 L0 但调用方未要求显示：不渲染（保留显隐双维度）。
  if (!visible) return null;

  const meta = LEVEL_META[level];
  const label = text ?? meta.text;
  const tag = (
    <Tooltip title={meta.tooltip}>
      <Tag
        icon={meta.icon}
        color={meta.color}
        style={{ fontSize: 13, padding: "4px 12px", fontWeight: 600 }}
      >
        {label}
      </Tag>
    </Tooltip>
  );

  if (inline || position === "inline") {
    return tag;
  }

  return <div style={FIXED_STYLES[position as Exclude<DemoBadgePosition, "inline">]}>{tag}</div>;
}
