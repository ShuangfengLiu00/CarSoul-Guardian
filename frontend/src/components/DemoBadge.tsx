/**
 * DemoBadge — 演示模式水印角标
 *
 * 统一的"演示模式 · 模拟数据"标注组件，用于所有使用模拟数据的页面。
 * 对应 GOAI 红线2：消除"虚假演示"隐患。
 *
 * 用法：
 *   <DemoBadge />                 // 默认右上角固定
 *   <DemoBadge inline />          // 行内显示（放在标题旁）
 *   <DemoBadge position="bottom-right" />
 *
 * 红线要求：
 *   - 所有演示页面必须标注红色"演示模式 · 模拟数据"角标
 *   - 后端 demo_mode 始终为 True，返回确定性结果
 */
import { Tag, Tooltip } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";

export type DemoBadgePosition =
  | "top-right"
  | "top-left"
  | "bottom-right"
  | "bottom-left"
  | "inline";

interface DemoBadgeProps {
  /** 显示位置，默认 "top-right" */
  position?: DemoBadgePosition;
  /** 是否行内显示（放在标题旁），等价于 position="inline" */
  inline?: boolean;
  /** 自定义文本，默认"演示模式 · 模拟数据" */
  text?: string;
}

const FIXED_STYLES: Record<Exclude<DemoBadgePosition, "inline">, React.CSSProperties> = {
  "top-right": { position: "fixed", top: 16, right: 24, zIndex: 1000 },
  "top-left": { position: "fixed", top: 16, left: 24, zIndex: 1000 },
  "bottom-right": { position: "fixed", bottom: 16, right: 24, zIndex: 1000 },
  "bottom-left": { position: "fixed", bottom: 16, left: 24, zIndex: 1000 },
};

export default function DemoBadge({
  position = "top-right",
  inline = false,
  text = "演示模式 · 模拟数据",
}: DemoBadgeProps) {
  const tag = (
    <Tooltip title="本页面使用模拟数据，仅用于功能演示，不代表真实车辆状态。后端 demo_mode=true，返回确定性结果。">
      <Tag
        icon={<InfoCircleOutlined />}
        color="red"
        style={{ fontSize: 13, padding: "4px 12px", fontWeight: 600 }}
      >
        {text}
      </Tag>
    </Tooltip>
  );

  if (inline || position === "inline") {
    return tag;
  }

  return <div style={FIXED_STYLES[position as Exclude<DemoBadgePosition, "inline">]}>{tag}</div>;
}
