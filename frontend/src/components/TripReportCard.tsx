import {
  Tag,
  Tooltip,
  Divider,
} from "antd";
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  EnvironmentOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  BookOutlined,
  CarOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { TripReport } from "@/services/types";

interface Props {
  report: TripReport;
}

const SEVERITY_ICON: Record<string, typeof CheckCircleOutlined> = {
  info: CheckCircleOutlined,
  warning: WarningOutlined,
  urgent: CloseCircleOutlined,
};

const SEVERITY_COLOR: Record<string, string> = {
  info: "var(--soul-500)",
  warning: "var(--warn-500)",
  urgent: "var(--danger-500)",
};

/** risk_color → CS-UI-DS 语义 token（红/橙/绿） */
function riskTone(color: string | undefined): {
  border: string;
  soft: string;
  strong: string;
} {
  if (color === "red") {
    return { border: "var(--danger-400)", soft: "var(--danger-soft)", strong: "var(--danger-400)" };
  }
  if (color === "orange") {
    return { border: "var(--warn-400)", soft: "var(--warn-soft)", strong: "var(--warn-400)" };
  }
  return { border: "var(--soul-400)", soft: "var(--soul-soft)", strong: "var(--soul-400)" };
}

/**
 * Renders the structured trip health report — the final output of the
 * long-trip Agent closed loop. Token-driven (CS-UI-DS v1.0, dark theme):
 *
 *   risk level → problems found → root cause → impact → recommendations
 *   → charging plan → knowledge sources → verdict
 */
export default function TripReportCard({ report }: Props) {
  const problems = report.problems ?? [];
  const tone = riskTone(report.risk_color);

  return (
    <div className="cs-trip-report" style={{ marginTop: 12 }}>
      {/* Header */}
      <div
        className="cs-trip-head"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "14px 16px",
          background: "var(--ink-850)",
          borderRadius: "12px 12px 0 0",
          borderBottom: `3px solid ${tone.border}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <CarOutlined style={{ fontSize: 20, color: "var(--info-400)" }} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-100)" }}>
              {report.title}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-300)" }}>
              CarSoul Guardian · Agent 闭环输出
            </div>
          </div>
        </div>
        <Tag
          color={report.risk_color}
          style={{ fontSize: 14, padding: "4px 16px", fontWeight: 700 }}
        >
          风险·{report.risk_level}
        </Tag>
      </div>

      {/* Body */}
      <div
        className="cs-trip-body"
        style={{
          background: "var(--ink-800)",
          borderRadius: "0 0 12px 12px",
          padding: 16,
          border: "1px solid var(--line)",
          borderTop: "none",
        }}
      >
        {/* Trip Summary */}
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 14,
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "var(--info-soft)",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <EnvironmentOutlined style={{ color: "var(--info-400)" }} />
            <span style={{ color: "var(--info-400)", fontWeight: 600 }}>
              {report.distance_km} km
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "var(--soul-soft)",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <ClockCircleOutlined style={{ color: "var(--soul-400)" }} />
            <span style={{ color: "var(--soul-400)", fontWeight: 600 }}>
              预计 {report.estimated_hours} 小时
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "var(--warn-soft)",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <ThunderboltOutlined style={{ color: "var(--warn-400)" }} />
            <span style={{ color: "var(--warn-400)", fontWeight: 600 }}>
              {report.charging_plan.stops} 个充电站
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "var(--danger-soft)",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <WarningOutlined style={{ color: "var(--danger-400)" }} />
            <span style={{ color: "var(--danger-400)", fontWeight: 600 }}>
              概率 {report.risk_probability}%
            </span>
          </div>
        </div>

        {/* Problems Table */}
        {problems.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--text-300)",
                marginBottom: 8,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              检出问题（{problems.length} 项）
            </div>
            <div
              style={{
                background: "var(--ink-800)",
                borderRadius: 8,
                border: "1px solid var(--line)",
                overflow: "hidden",
              }}
            >
              {problems.map((p, i) => {
                const Icon = SEVERITY_ICON[p.severity] || WarningOutlined;
                const color = SEVERITY_COLOR[p.severity] || "var(--warn-500)";
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "8px 12px",
                      borderBottom:
                        i < problems.length - 1
                          ? "1px solid var(--line)"
                          : "none",
                      fontSize: 13,
                    }}
                  >
                    <Icon style={{ color, fontSize: 16, flexShrink: 0 }} />
                    <span style={{ fontWeight: 600, color: "var(--text-200)", minWidth: 80 }}>
                      {p.item}
                    </span>
                    <span style={{ color: "var(--text-300)" }}>
                      当前 <strong style={{ color }}>{p.value}</strong>
                    </span>
                    <span style={{ color: "var(--text-400)", fontSize: 12 }}>
                      阈值 {p.threshold}
                    </span>
                    <Tooltip title={p.detail}>
                      <span
                        style={{
                          color: "var(--text-400)",
                          fontSize: 11,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          flex: 1,
                        }}
                      >
                        {p.detail}
                      </span>
                    </Tooltip>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Root Cause */}
        <div style={{ marginBottom: 12 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "var(--text-300)",
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: 0.5,
            }}
          >
            根因分析
          </div>
          <div
            style={{
              background: "var(--warn-soft)",
              borderRadius: 8,
              padding: "10px 14px",
              fontSize: 13,
              color: "var(--warn-400)",
              lineHeight: 1.6,
              border: "1px solid var(--warn-400)",
            }}
          >
            {report.root_cause}
            {report.knowledge_match && (
              <div style={{ marginTop: 6, fontSize: 12, color: "var(--warn-400)" }}>
                <BookOutlined style={{ marginRight: 4 }} />
                知识库匹配：{report.knowledge_match}
              </div>
            )}
          </div>
        </div>

        {/* Impact */}
        {report.impact && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--text-300)",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              长途影响评估
            </div>
            <div
              style={{
                background: "var(--danger-soft)",
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 13,
                color: "var(--danger-400)",
                lineHeight: 1.6,
                border: "1px solid var(--danger-400)",
              }}
            >
              {report.impact}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--text-300)",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              处理建议
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {report.recommendations.map((rec, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                    fontSize: 13,
                    color: "var(--text-200)",
                  }}
                >
                  <CheckCircleOutlined
                    style={{ color: "var(--soul-500)", marginTop: 2, flexShrink: 0 }}
                  />
                  <span>{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Charging Plan */}
        <div style={{ marginBottom: 12 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "var(--text-300)",
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: 0.5,
            }}
          >
            充电路线规划
          </div>
          <div
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {Array.from({ length: report.charging_plan.stops }).map((_, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  background: "var(--soul-soft)",
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 12,
                  color: "var(--soul-400)",
                  border: "1px solid var(--soul-400)",
                }}
              >
                <ThunderboltOutlined style={{ fontSize: 12 }} />
                充电站 {i + 1}
                <span style={{ color: "var(--text-400)" }}>
                  (~{(i + 1) * report.charging_plan.interval_km}km)
                </span>
              </div>
            ))}
          </div>
          <div
            style={{ marginTop: 6, fontSize: 12, color: "var(--text-400)" }}
          >
            {report.charging_plan.strategy}
          </div>
        </div>

        {/* Knowledge Sources */}
        {report.knowledge_sources.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <Divider style={{ margin: "8px 0" }} />
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                color: "var(--text-400)",
              }}
            >
              <BookOutlined />
              <span>知识库来源：</span>
              {report.knowledge_sources.map((src, i) => (
                <Tag key={i} style={{ fontSize: 11, margin: 0 }}>
                  {src}
                </Tag>
              ))}
            </div>
          </div>
        )}

        {/* Verdict */}
        <div
          style={{
            background: tone.soft,
            borderRadius: 8,
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            border: `1px solid ${tone.border}`,
          }}
        >
          <BulbOutlined style={{ fontSize: 20, color: tone.strong }} />
          <span
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: tone.strong,
            }}
          >
            {report.verdict}
          </span>
        </div>

        {/* Footer */}
        <div
          style={{
            marginTop: 10,
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: "var(--text-400)",
          }}
        >
          <ReloadOutlined spin style={{ fontSize: 11 }} />
          已更新车辆数字生命档案 · 守护闭环完成
        </div>
      </div>
    </div>
  );
}
