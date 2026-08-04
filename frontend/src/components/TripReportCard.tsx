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
  info: "#10b981",
  warning: "#f59e0b",
  urgent: "#ef4444",
};

/**
 * Renders the structured trip health report — the final output of the
 * long-trip Agent closed loop. Designed to make the Agent's analysis
 * visible to competition judges at a glance:
 *
 *   risk level → problems found → root cause → impact → recommendations
 *   → charging plan → knowledge sources → verdict
 */
export default function TripReportCard({ report }: Props) {
  const problems = report.problems ?? [];

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
          background: "linear-gradient(135deg, #0f172a, #1e293b)",
          borderRadius: "12px 12px 0 0",
          borderBottom: `3px solid ${
            report.risk_color === "red"
              ? "#ef4444"
              : report.risk_color === "orange"
              ? "#f59e0b"
              : "#10b981"
          }`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <CarOutlined style={{ fontSize: 20, color: "#3b82f6" }} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#f1f5f9" }}>
              {report.title}
            </div>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>
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
          background: "#f8fafc",
          borderRadius: "0 0 12px 12px",
          padding: 16,
          border: "1px solid #e2e8f0",
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
              background: "#eff6ff",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <EnvironmentOutlined style={{ color: "#3b82f6" }} />
            <span style={{ color: "#1e40af", fontWeight: 600 }}>
              {report.distance_km} km
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#f0fdf4",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <ClockCircleOutlined style={{ color: "#10b981" }} />
            <span style={{ color: "#166534", fontWeight: 600 }}>
              预计 {report.estimated_hours} 小时
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#fffbeb",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <ThunderboltOutlined style={{ color: "#f59e0b" }} />
            <span style={{ color: "#92400e", fontWeight: 600 }}>
              {report.charging_plan.stops} 个充电站
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#fef2f2",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            <WarningOutlined style={{ color: "#ef4444" }} />
            <span style={{ color: "#991b1b", fontWeight: 600 }}>
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
                color: "#475569",
                marginBottom: 8,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              检出问题（{problems.length} 项）
            </div>
            <div
              style={{
                background: "#fff",
                borderRadius: 8,
                border: "1px solid #e2e8f0",
                overflow: "hidden",
              }}
            >
              {problems.map((p, i) => {
                const Icon = SEVERITY_ICON[p.severity] || WarningOutlined;
                const color = SEVERITY_COLOR[p.severity] || "#f59e0b";
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
                          ? "1px solid #f1f5f9"
                          : "none",
                      fontSize: 13,
                    }}
                  >
                    <Icon style={{ color, fontSize: 16, flexShrink: 0 }} />
                    <span style={{ fontWeight: 600, color: "#334155", minWidth: 80 }}>
                      {p.item}
                    </span>
                    <span style={{ color: "#64748b" }}>
                      当前 <strong style={{ color }}>{p.value}</strong>
                    </span>
                    <span style={{ color: "#94a3b8", fontSize: 12 }}>
                      阈值 {p.threshold}
                    </span>
                    <Tooltip title={p.detail}>
                      <span
                        style={{
                          color: "#94a3b8",
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
              color: "#475569",
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: 0.5,
            }}
          >
            根因分析
          </div>
          <div
            style={{
              background: "#fff7ed",
              borderRadius: 8,
              padding: "10px 14px",
              fontSize: 13,
              color: "#9a3412",
              lineHeight: 1.6,
              border: "1px solid #fed7aa",
            }}
          >
            {report.root_cause}
            {report.knowledge_match && (
              <div style={{ marginTop: 6, fontSize: 12, color: "#c2410c" }}>
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
                color: "#475569",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              长途影响评估
            </div>
            <div
              style={{
                background: "#fef2f2",
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 13,
                color: "#991b1b",
                lineHeight: 1.6,
                border: "1px solid #fecaca",
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
                color: "#475569",
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
                    color: "#334155",
                  }}
                >
                  <CheckCircleOutlined
                    style={{ color: "#10b981", marginTop: 2, flexShrink: 0 }}
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
              color: "#475569",
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
                  background: "#ecfdf5",
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 12,
                  color: "#065f46",
                  border: "1px solid #a7f3d0",
                }}
              >
                <ThunderboltOutlined style={{ fontSize: 12 }} />
                充电站 {i + 1}
                <span style={{ color: "#94a3b8" }}>
                  (~{(i + 1) * report.charging_plan.interval_km}km)
                </span>
              </div>
            ))}
          </div>
          <div
            style={{ marginTop: 6, fontSize: 12, color: "#64748b" }}
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
                color: "#64748b",
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
            background:
              report.risk_color === "red"
                ? "linear-gradient(135deg, #fef2f2, #fecaca)"
                : report.risk_color === "orange"
                ? "linear-gradient(135deg, #fffbeb, #fed7aa)"
                : "linear-gradient(135deg, #f0fdf4, #bbf7d0)",
            borderRadius: 8,
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            border: `1px solid ${
              report.risk_color === "red"
                ? "#fca5a5"
                : report.risk_color === "orange"
                ? "#fdba74"
                : "#86efac"
            }`,
          }}
        >
          <BulbOutlined
            style={{
              fontSize: 20,
              color:
                report.risk_color === "red"
                  ? "#dc2626"
                  : report.risk_color === "orange"
                  ? "#d97706"
                  : "#16a34a",
            }}
          />
          <span
            style={{
              fontSize: 14,
              fontWeight: 700,
              color:
                report.risk_color === "red"
                  ? "#991b1b"
                  : report.risk_color === "orange"
                  ? "#92400e"
                  : "#166534",
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
            color: "#94a3b8",
          }}
        >
          <ReloadOutlined spin style={{ fontSize: 11 }} />
          已更新车辆数字生命档案 · 守护闭环完成
        </div>
      </div>
    </div>
  );
}
