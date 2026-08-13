import type { LucideIcon } from "lucide-react";
import { ICON_SIZES, ICON_STROKE_WIDTH } from "@/lib/icons";

/**
 * Icon size tokens (SPEC §8.3).
 * - `inline`  → 16px  行内（与文字同行、表格内、徽章内）
 * - `nav`     → 20px  导航（导航项、按钮内图标、tab 图标）
 * - `card`    → 24px  卡片标题 / 仪表盘主图标
 */
export type IconSize = "inline" | "nav" | "card";

const sizeMap: Record<IconSize, number> = {
  inline: ICON_SIZES.inline, // 16
  nav: ICON_SIZES.navigation, // 20
  card: ICON_SIZES.cardHeader, // 24
};

export interface IconProps {
  /** Lucide icon component (import from `@/lib/icons`). */
  icon: LucideIcon;
  /** Semantic size token — never hardcode pixel values (SPEC §8.3). */
  size?: IconSize;
  /** Extra class names (color via `text-*`, spacing, etc.). */
  className?: string;
  /** Stroke width override. Defaults to 2px (Lucide default). Avoid overriding. */
  strokeWidth?: number;
  /** Accessible label. When set, renders `role="img"` + `aria-label`;
   * when omitted, the icon is decorative (`aria-hidden`). */
  "aria-label"?: string;
}

/**
 * Unified Lucide icon wrapper — enforces the 3-size system + 2px stroke
 * and accessible behavior. Prefer this (or direct imports from `@/lib/icons`)
 * over ad-hoc `<IconComp size={...} />` so sizes stay consistent project-wide.
 *
 * @see SPEC v1.0 §8.3, phase2-design-assets.md 资产 3.1
 *
 * @example
 * import { FlaskConical } from "@/lib/icons";
 * import { Icon } from "@/components/base";
 * <Icon icon={FlaskConical} size="inline" className="text-warn" />;
 */
export function Icon({
  icon: IconComp,
  size = "inline",
  className,
  strokeWidth = ICON_STROKE_WIDTH,
  "aria-label": ariaLabel,
}: IconProps) {
  return (
    <IconComp
      size={sizeMap[size]}
      strokeWidth={strokeWidth}
      className={className}
      aria-hidden={ariaLabel ? undefined : true}
      role={ariaLabel ? "img" : undefined}
      aria-label={ariaLabel}
    />
  );
}

export default Icon;
