import { Fragment } from "react";
import { Tag, Empty, Tooltip } from "antd";
import {
  EyeOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  SolutionOutlined,
  CheckCircleOutlined,
  HeartOutlined,
  RightOutlined,
  BulbOutlined,
  AlertOutlined,
  BookOutlined,
  EnvironmentOutlined,
  SafetyCertificateOutlined,
  ApartmentOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import type { ClosedLoop, ClosedLoopStep, KnowledgeRetrieval, TripContext, JudgeVerdict, WorkflowMeta } from "@/services/types";

const STEP_META: Record<string, { icon: typeof EyeOutlined; color: string }> = {
  perceive: { icon: EyeOutlined, color: "#3b82f6" },
  understand: { icon: SearchOutlined, color: "#8b5cf6" },
  reason: { icon: ThunderboltOutlined, color: "#f59e0b" },
  tool: { icon: SolutionOutlined, color: "#06b6d4" },
  act: { icon: CheckCircleOutlined, color: "#10b981" },
  normal_report: { icon: HeartOutlined, color: "#10b981" },
};

const RISK_COLOR: Record<string, string> = {
  low: "green",
  medium: "orange",
  high: "red",
  critical: "red",
};

interface Props {
  loop: ClosedLoop | null | undefined;
  /** Compact mode hides the per-step detail list (used inside chat bubbles). */
  compact?: boolean;
}

/**
 * Renders the CarSoul guardian closed-loop trace (感知 → 诊断 → 风险 → 建议 → 执行)
 * as a horizontal, touch-friendly stepper. Designed for the in-car large screen:
 * large nodes, high contrast, and the structured outputs (anomalies / risk /
 * actions / reminder) surfaced as chips so the whole loop is readable at a glance.
 */
export default function ClosedLoopTrace({ loop, compact = false }: Props) {
  if (!loop) return null;
  const steps: ClosedLoopStep[] = loop.steps ?? [];
  if (steps.length === 0) return null;

  const risk = (loop.risk ?? {}) as Record<string, unknown>;
  const riskLevel = String(risk.level ?? "");
  const anomalies = loop.anomalies ?? [];
  const actions = loop.actions ?? [];
  const details = steps.filter((s) => s.detail);
  const knowledge = (loop.knowledge_retrieval ?? null) as KnowledgeRetrieval | null;
  const tripCtx = (loop.trip_context ?? null) as TripContext | null;
  const isLongTrip = tripCtx?.is_long_trip ?? false;
  const judge = (loop.judge_verdict ?? null) as JudgeVerdict | null;
  const wfMeta = (loop.workflow_meta ?? null) as WorkflowMeta | null;

  const VERDICT_COLOR: Record<string, string> = {
    consensus: "#10b981",
    conflict_resolved: "#f59e0b",
    insufficient_data: "#94a3b8",
  };
  const TASK_STATE_COLOR: Record<string, string> = {
    COMPLETED: "#10b981",
    RUNNING: "#3b82f6",
    PENDING: "#94a3b8",
    FAILED: "#ef4444",
    SKIPPED: "#a78bfa",
  };

  return (
    <div className="cs-loop">
      {/* Inline animation styles for step reveal */}
      <style>{`
        @keyframes csStepReveal {
          0% { opacity: 0; transform: translateY(8px) scale(0.9); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .cs-loop-node {
          animation: csStepReveal 0.4s ease-out both;
        }
        @keyframes csKnowledgeSlide {
          0% { opacity: 0; transform: translateX(-12px); }
          100% { opacity: 1; transform: translateX(0); }
        }
        .cs-kb-chip {
          animation: csKnowledgeSlide 0.3s ease-out both;
        }
      `}</style>

      <div className="cs-loop-head">
        <span className="cs-loop-badge">
          <AlertOutlined style={{ marginRight: 6 }} />
          守护闭环
        </span>
        {loop.is_normal ? (
          <Tag color="green">正常报告</Tag>
        ) : (
          <Tag color="orange">异常守护</Tag>
        )}
        {isLongTrip && (
          <Tag color="blue" icon={<EnvironmentOutlined />}>
            长途出行 · {tripCtx?.distance_km}km
          </Tag>
        )}
        {riskLevel && (
          <Tag color={RISK_COLOR[riskLevel] ?? "orange"}>风险·{riskLevel}</Tag>
        )}
        {anomalies.length > 0 && (
          <Tag color="volcano">{anomalies.length} 项异常</Tag>
        )}
        {typeof risk.probability_percent === "number" && (
          <Tag color="blue">概率 {risk.probability_percent}%</Tag>
        )}
      </div>

      <div className="cs-loop-bar">
        {steps.map((s, i) => {
          const meta = STEP_META[s.step] ?? STEP_META.act;
          const Icon = meta.icon;
          return (
            <Fragment key={s.step}>
              <div
                className="cs-loop-node"
                title={s.detail || s.title}
                style={{ animationDelay: `${i * 0.15}s` }}
              >
                <div className="cs-loop-ico" style={{ background: meta.color }}>
                  <Icon />
                </div>
                <div className="cs-loop-label">
                  <strong>{s.title}</strong>
                  <span className="cs-loop-agent">{s.agent}</span>
                </div>
              </div>
              {i < steps.length - 1 && (
                <div className="cs-loop-arrow">
                  <RightOutlined />
                </div>
              )}
            </Fragment>
          );
        })}
      </div>

      {/* Knowledge Retrieval Display — makes RAG visible to judges */}
      {knowledge && !compact && knowledge.chunk_count > 0 && (
        <div
          className="cs-loop-kb"
          style={{
            marginTop: 10,
            padding: "8px 12px",
            background: "#f5f3ff",
            borderRadius: 8,
            border: "1px solid #ddd6fe",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 6,
              fontSize: 12,
              color: "#6d28d9",
              fontWeight: 600,
            }}
          >
            <BookOutlined />
            知识库检索 · {knowledge.chunk_count} 条相关片段
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {knowledge.chunks.slice(0, 3).map((chunk, i) => (
              <Tooltip
                key={i}
                title={`${chunk.preview}...（相关度 ${chunk.score}）`}
              >
                <div
                  className="cs-kb-chip"
                  style={{
                    animationDelay: `${i * 0.1}s`,
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    background: "#fff",
                    padding: "3px 8px",
                    borderRadius: 6,
                    fontSize: 11,
                    color: "#5b21b6",
                    border: "1px solid #e9d5ff",
                    cursor: "default",
                    maxWidth: 200,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  <SearchOutlined style={{ fontSize: 10 }} />
                  {chunk.title}
                  {chunk.heading && (
                    <span style={{ color: "#94a3b8" }}> · {chunk.heading}</span>
                  )}
                  <span style={{ color: "#a78bfa", fontWeight: 600 }}>
                    {chunk.score}
                  </span>
                </div>
              </Tooltip>
            ))}
          </div>
        </div>
      )}

      {/* Judge Agent Verdict — governance layer conflict resolution */}
      {judge && judge.verdict && (
        <div
          className="cs-loop-judge"
          style={{
            marginTop: 10,
            padding: "8px 12px",
            background: judge.conflict_detected ? "#fffbeb" : "#f0fdf4",
            borderRadius: 8,
            border: `1px solid ${judge.conflict_detected ? "#fde68a" : "#bbf7d0"}`,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 6,
              fontSize: 12,
              fontWeight: 600,
              color: judge.conflict_detected ? "#b45309" : "#15803d",
            }}
          >
            <SafetyCertificateOutlined />
            Judge Agent 仲裁
            <Tag
              color={judge.conflict_detected ? "orange" : "green"}
              style={{ marginLeft: 4, fontSize: 11 }}
            >
              {judge.verdict === "consensus"
                ? "专家一致"
                : judge.verdict === "conflict_resolved"
                  ? "冲突已仲裁"
                  : "数据不足"}
            </Tag>
            {judge.conflict_detected && (
              <Tag color="red" style={{ fontSize: 11 }}>
                检测到冲突
              </Tag>
            )}
          </div>
          <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.6 }}>
            {judge.primary_cause && (
              <div>
                <strong>主因:</strong> {judge.primary_cause}
                {judge.primary_specialty && (
                  <span style={{ color: "#94a3b8" }}>
                    {" "}
                    ({judge.primary_specialty})
                  </span>
                )}
              </div>
            )}
            <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
              <span>
                <strong>置信度:</strong>{" "}
                <span style={{ color: VERDICT_COLOR[judge.verdict] ?? "#475569", fontWeight: 600 }}>
                  {(judge.confidence * 100).toFixed(0)}%
                </span>
              </span>
              {judge.root_causes_seen && judge.root_causes_seen.length > 0 && (
                <span>
                  <strong>根因数:</strong> {judge.root_causes_seen.length}
                </span>
              )}
            </div>
            {Object.keys(judge.contributor_weights).length > 0 && (
              <div style={{ marginTop: 4, display: "flex", gap: 6, flexWrap: "wrap" }}>
                {Object.entries(judge.contributor_weights).map(([expert, weight]) => (
                  <Tag key={expert} style={{ fontSize: 11 }}>
                    {expert}: {(weight * 100).toFixed(0)}%
                  </Tag>
                ))}
              </div>
            )}
            {judge.reasoning && (
              <div style={{ marginTop: 4, color: "#64748b", fontStyle: "italic" }}>
                {judge.reasoning}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Workflow Engine DAG — task tree visualization */}
      {wfMeta && wfMeta.task_tree && wfMeta.task_tree.tasks.length > 0 && (
        <div
          className="cs-loop-dag"
          style={{
            marginTop: 10,
            padding: "8px 12px",
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 8,
              fontSize: 12,
              color: "#334155",
              fontWeight: 600,
            }}
          >
            <ApartmentOutlined />
            工作流引擎 · DAG 调度
            <Tag style={{ fontSize: 11 }}>
              {wfMeta.task_tree.task_count} 任务
            </Tag>
            {wfMeta.intent?.priority && (
              <Tag color="blue" style={{ fontSize: 11 }}>
                优先级·{wfMeta.intent.priority}
              </Tag>
            )}
            {wfMeta.state_machine?.state && (
              <Tag
                color={wfMeta.state_machine.state === "COMPLETED" ? "green" : "orange"}
                style={{ fontSize: 11 }}
              >
                {wfMeta.state_machine.state}
              </Tag>
            )}
          </div>
          {/* DAG task chain */}
          <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
            {wfMeta.task_tree.tasks.map((task, i) => {
              const stateColor = TASK_STATE_COLOR[task.state] ?? "#94a3b8";
              return (
                <Fragment key={task.task_id}>
                  <Tooltip
                    title={
                      <div style={{ fontSize: 12 }}>
                        <div>
                          <strong>{task.name}</strong> ({task.task_type})
                        </div>
                        <div>Agent: {task.agent_id}</div>
                        <div>状态: {task.state}</div>
                        {task.dependencies.length > 0 && (
                          <div>依赖: {task.dependencies.join(", ")}</div>
                        )}
                        {task.retry_count > 0 && (
                          <div>重试: {task.retry_count}/{task.max_retries}</div>
                        )}
                        {task.error && (
                          <div style={{ color: "#ef4444" }}>错误: {task.error}</div>
                        )}
                      </div>
                    }
                  >
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: 2,
                        cursor: "default",
                      }}
                    >
                      <div
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 6,
                          background: stateColor,
                          color: "#fff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: 10,
                          fontWeight: 700,
                        }}
                      >
                        {task.agent_id.slice(0, 3).toUpperCase()}
                      </div>
                      <span style={{ fontSize: 10, color: "#64748b" }}>
                        {task.name}
                      </span>
                    </div>
                  </Tooltip>
                  {i < wfMeta.task_tree.tasks.length - 1 && (
                    <RightOutlined style={{ fontSize: 10, color: "#cbd5e1" }} />
                  )}
                </Fragment>
              );
            })}
          </div>
          {/* Workflow metadata footer */}
          <div
            style={{
              marginTop: 6,
              display: "flex",
              gap: 12,
              fontSize: 11,
              color: "#94a3b8",
            }}
          >
            {wfMeta.intent?.scenario && (
              <span>场景: {wfMeta.intent.scenario}</span>
            )}
            {wfMeta.governance?.agent_count && (
              <span>治理Agent: {wfMeta.governance.agent_count}</span>
            )}
            {wfMeta.memory?.participating_agents && (
              <span>
                参与: {wfMeta.memory.participating_agents.length}
              </span>
            )}
          </div>
        </div>
      )}

      {!compact && details.length > 0 && (
        <div className="cs-loop-details">
          {details.map((s) => {
            const meta = STEP_META[s.step] ?? STEP_META.act;
            return (
              <div className="cs-loop-detail" key={s.step}>
                <span
                  className="cs-loop-dot"
                  style={{ background: meta.color }}
                />
                <span className="cs-loop-dtitle">{s.title}</span>
                <span className="cs-loop-dtext">{s.detail}</span>
              </div>
            );
          })}
        </div>
      )}

      {(actions.length > 0 || loop.reminder) && (
        <div className="cs-loop-foot">
          {loop.reminder && (
            <div className="cs-loop-reminder">
              <BulbOutlined style={{ color: "#f59e0b" }} />
              <span>
                已推送「{loop.reminder.title ?? "守护提醒"}」并记录至车辆数字生命档案
              </span>
            </div>
          )}
          {actions.length > 0 && (
            <ul className="cs-loop-actions">
              {actions.map((a, i) => (
                <li key={i}>
                  <CheckCircleOutlined style={{ color: "#10b981", marginRight: 6 }} />
                  {a}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {!compact && anomalies.length === 0 && actions.length === 0 && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <span style={{ fontSize: 13, color: "#94a3b8" }}>
              本次为正常巡检，未触发守护动作
            </span>
          }
          style={{ margin: "8px 0" }}
        />
      )}
    </div>
  );
}
