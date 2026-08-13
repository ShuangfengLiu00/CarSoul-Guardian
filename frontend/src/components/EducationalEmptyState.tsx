import { useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { Button } from "antd";
import { ArrowRightOutlined } from "@ant-design/icons";

/**
 * §6.6 空状态（教育意义）
 * 空壳页统一呈现：图标 + 「能力待接入」+ 占位说明 + 「查看接入状态」CTA。
 * 严禁用假数据填充（空壳页处置决议 D4：全按建议执行）。
 * 全部 Token 化，图标锁定 @ant-design/icons，无 emoji、无硬编码颜色、无渐变。
 */
export interface EducationalEmptyStateProps {
  /** 模块图标（锁定 SVG 图标库，24/40px 由 .cs-empty__icon 控制） */
  icon: ReactNode;
  /** 标题，默认「能力待接入」 */
  title?: string;
  /** 说明文案，默认 §6.6 占位说明 */
  desc?: string;
  /** 接通后将提供的真实能力（教育意义，非假数据），逐条罗列 */
  features?: string[];
  /** 「查看接入状态」跳转的真实路由 */
  ctaTo?: string;
  /** CTA 文案，默认「查看接入状态」 */
  ctaLabel?: string;
}

const DEFAULT_TITLE = "能力待接入";
const DEFAULT_DESC =
  "该模块的真实数据通道尚未接通。当前为占位说明，不展示模拟数据。";

export default function EducationalEmptyState({
  icon,
  title = DEFAULT_TITLE,
  desc = DEFAULT_DESC,
  features,
  ctaTo = "/",
  ctaLabel = "查看接入状态",
}: EducationalEmptyStateProps) {
  const navigate = useNavigate();
  return (
    <div
      className="holo-page"
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-8)",
      }}
    >
      <div className="cs-empty">
        <div className="cs-empty__icon" aria-hidden>
          {icon}
        </div>
        <div className="cs-empty__title">{title}</div>
        <p className="cs-empty__desc">{desc}</p>

        {features && features.length > 0 && (
          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-2)",
              maxWidth: 460,
              textAlign: "left",
            }}
          >
            {features.map((f, i) => (
              <li
                key={i}
                style={{
                  fontSize: 13,
                  lineHeight: 1.5,
                  color: "var(--text-300)",
                  paddingLeft: "var(--space-5)",
                  position: "relative",
                }}
              >
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    color: "var(--accent)",
                    fontWeight: 700,
                  }}
                >
                  ·
                </span>
                {f}
              </li>
            ))}
          </ul>
        )}

        <Button
          type="primary"
          onClick={() => navigate(ctaTo)}
          style={{ marginTop: "var(--space-2)" }}
        >
          {ctaLabel}
          <ArrowRightOutlined />
        </Button>
      </div>
    </div>
  );
}
