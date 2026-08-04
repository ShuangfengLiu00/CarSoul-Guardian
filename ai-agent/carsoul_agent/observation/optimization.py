"""Optimization Loop — 自动优化闭环.

Implements the optimization component of the Agent Observation Layer
(架构第四层). Runs a closed loop:

    Collect → Analyze → Evaluate → Optimize

  - Collect:    采集 Agent 行为数据（trace + evaluation + registry 统计）
  - Analyze:    按阈值识别问题（低准确率 / 高 token / 低满意度 / 高错误率）
  - Evaluate:   对问题打分排序，映射优先级
  - Optimize:   生成可执行的优化建议（Prompt / Skill / Workflow）

Optimisation targets are Prompt, Skill and Workflow. Applied actions
are forwarded to the Evolution manager to record the before/after
state of the evolving agent.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---- analysis thresholds (tunable) -----------------------------------
_ACCURACY_THRESHOLD = 0.70       # 低于此值 → 低准确率
_SATISFACTION_THRESHOLD = 0.60   # 低于此值 → 低满意度
_TOKEN_THRESHOLD = 5000          # 高于此值 → 高 token 消耗
_ERROR_RATE_THRESHOLD = 0.20     # 错误率高于此值 → 高错误率


@dataclass
class OptimizationAction:
    """A single optimisation suggestion produced by the loop."""

    action_id: str
    agent_id: str
    issue_type: str          # low_accuracy/high_token/low_satisfaction/high_error
    description: str
    suggestion: str          # 优化建议
    priority: str = "medium"  # low/medium/high
    status: str = "pending"   # pending/applied/dismissed
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for API responses / persistence."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "issue_type": self.issue_type,
            "description": self.description,
            "suggestion": self.suggestion,
            "priority": self.priority,
            "status": self.status,
            "timestamp": self.timestamp,
        }


# Issue-type → suggestion templates.
_SUGGESTIONS: dict[str, str] = {
    "low_accuracy": (
        "优化 Prompt：补充 few-shot 示例与诊断校验步骤；"
        "核查 RAG 检索相关性，必要时扩充知识库条目。"
    ),
    "high_token": (
        "压缩 Prompt：精简系统提示、启用上下文缓存、"
        "裁剪冗余 Skill 步骤以降低 token 消耗。"
    ),
    "low_satisfaction": (
        "调整响应语气与结构：增加确认步骤、提升解释清晰度、"
        "对高风险结论补充行动建议。"
    ),
    "high_error": (
        "增强健壮性：增加输入校验、完善 fallback 路径、"
        "复查工具调用异常处理与重试策略。"
    ),
}


class OptimizationLoop:
    """自动优化闭环 — Collect → Analyze → Evaluate → Optimize.

    定期采集 Agent 行为数据，分析问题，评分，生成优化建议。
    优化对象：Prompt / Skill / Workflow。
    """

    def __init__(self) -> None:
        self._actions: list[OptimizationAction] = []

    # ------------------------------------------------------------------
    #  Collect
    # ------------------------------------------------------------------
    def collect(self) -> dict[str, Any]:
        """采集 Agent 行为数据（来自 trace_collector / evaluation_engine / registry）.

        Governance / workflow_engine imports are deferred to method scope
        to avoid circular imports.
        """
        from carsoul_agent.observation.trace import trace_collector
        from carsoul_agent.observation.evaluation import evaluation_engine

        try:
            from carsoul_agent.governance.registry import managed_registry
            registry_snapshot = managed_registry.to_dict()
        except Exception as exc:  # noqa: BLE001
            logger.debug("registry unavailable during collect: %s", exc)
            registry_snapshot = {"agents": []}

        return {
            "token_stats": trace_collector.get_token_stats(),
            "fleet_evaluation": evaluation_engine.get_fleet_evaluation(),
            "registry": registry_snapshot,
        }

    # ------------------------------------------------------------------
    #  Analyze
    # ------------------------------------------------------------------
    def analyze(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """分析问题：遍历舰队评估，按阈值识别 issue."""
        issues: list[dict[str, Any]] = []
        for agent in data.get("fleet_evaluation", {}).get("agents", []):
            agent_id = agent.get("agent_id", "unknown")
            avg_accuracy = agent.get("avg_accuracy", 1.0)
            avg_satisfaction = agent.get("avg_user_satisfaction", 1.0)
            avg_token = agent.get("avg_token_consumed", 0)
            total_errors = agent.get("total_errors", 0)
            count = agent.get("evaluation_count", 0)
            error_rate = total_errors / count if count else 0.0

            if avg_accuracy < _ACCURACY_THRESHOLD:
                issues.append({
                    "agent_id": agent_id,
                    "issue_type": "low_accuracy",
                    "value": avg_accuracy,
                    "threshold": _ACCURACY_THRESHOLD,
                    "description": f"诊断准确率 {avg_accuracy:.2f} 低于阈值 {_ACCURACY_THRESHOLD}",
                })
            if avg_token > _TOKEN_THRESHOLD:
                issues.append({
                    "agent_id": agent_id,
                    "issue_type": "high_token",
                    "value": avg_token,
                    "threshold": _TOKEN_THRESHOLD,
                    "description": f"平均 token 消耗 {avg_token:.0f} 高于阈值 {_TOKEN_THRESHOLD}",
                })
            if avg_satisfaction < _SATISFACTION_THRESHOLD:
                issues.append({
                    "agent_id": agent_id,
                    "issue_type": "low_satisfaction",
                    "value": avg_satisfaction,
                    "threshold": _SATISFACTION_THRESHOLD,
                    "description": f"用户满意度 {avg_satisfaction:.2f} 低于阈值 {_SATISFACTION_THRESHOLD}",
                })
            if error_rate > _ERROR_RATE_THRESHOLD:
                issues.append({
                    "agent_id": agent_id,
                    "issue_type": "high_error",
                    "value": error_rate,
                    "threshold": _ERROR_RATE_THRESHOLD,
                    "description": f"错误率 {error_rate:.2f} 高于阈值 {_ERROR_RATE_THRESHOLD}",
                })
        return issues

    # ------------------------------------------------------------------
    #  Evaluate
    # ------------------------------------------------------------------
    def evaluate_issues(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """对问题打分排序，映射优先级（high/medium/low）."""
        weighted: list[dict[str, Any]] = []
        for issue in issues:
            value = issue.get("value", 0.0)
            threshold = issue.get("threshold", 0.0)
            issue_type = issue.get("issue_type", "")
            # severity 0–1: how far the metric crosses the threshold.
            if issue_type in ("low_accuracy", "low_satisfaction"):
                severity = (threshold - value) / threshold if threshold else 0.0
            elif issue_type in ("high_token", "high_error"):
                severity = (value - threshold) / threshold if threshold else 0.0
            else:
                severity = 0.0
            severity = max(0.0, min(1.0, severity))
            if severity >= 0.5:
                priority = "high"
            elif severity >= 0.25:
                priority = "medium"
            else:
                priority = "low"
            enriched = dict(issue)
            enriched["severity"] = round(severity, 4)
            enriched["priority"] = priority
            weighted.append(enriched)
        # sort by severity descending
        weighted.sort(key=lambda x: x["severity"], reverse=True)
        return weighted

    # ------------------------------------------------------------------
    #  Optimize
    # ------------------------------------------------------------------
    def generate_optimizations(
        self,
        evaluated_issues: list[dict[str, Any]],
    ) -> list[OptimizationAction]:
        """根据已评分问题生成优化建议动作."""
        actions: list[OptimizationAction] = []
        for issue in evaluated_issues:
            issue_type = issue.get("issue_type", "")
            suggestion = _SUGGESTIONS.get(
                issue_type,
                "请人工复核该 Agent 的配置与最近执行记录。",
            )
            action = OptimizationAction(
                action_id=f"opt_{uuid.uuid4().hex[:12]}",
                agent_id=issue.get("agent_id", "unknown"),
                issue_type=issue_type,
                description=issue.get("description", ""),
                suggestion=suggestion,
                priority=issue.get("priority", "medium"),
            )
            self._actions.append(action)
            actions.append(action)
        logger.info("Generated %d optimization actions", len(actions))
        return actions

    def run_cycle(self) -> list[OptimizationAction]:
        """执行完整优化闭环：Collect → Analyze → Evaluate → Optimize."""
        data = self.collect()
        issues = self.analyze(data)
        evaluated = self.evaluate_issues(issues)
        return self.generate_optimizations(evaluated)

    # ------------------------------------------------------------------
    #  Action management
    # ------------------------------------------------------------------
    def _find_action(self, action_id: str) -> OptimizationAction | None:
        for action in self._actions:
            if action.action_id == action_id:
                return action
        return None

    def apply_optimization(self, action_id: str) -> bool:
        """标记优化动作为已应用，并记录到进化管理器."""
        action = self._find_action(action_id)
        if action is None or action.status != "pending":
            return False
        action.status = "applied"
        # Record the evolution (lazy import to avoid cycles).
        try:
            from carsoul_agent.observation.evolution import evolution_manager
            evolution_manager.record_evolution(
                agent_id=action.agent_id,
                evolution_type=_evolution_type_for(action.issue_type),
                before={"issue_type": action.issue_type, "status": "pending"},
                after={"suggestion": action.suggestion, "status": "applied"},
                improvement_metric=_metric_for(action.issue_type),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("evolution recording skipped: %s", exc)
        logger.info("Optimization applied: %s (%s)", action_id, action.agent_id)
        return True

    def dismiss_optimization(self, action_id: str) -> bool:
        """驳回优化建议."""
        action = self._find_action(action_id)
        if action is None or action.status != "pending":
            return False
        action.status = "dismissed"
        logger.info("Optimization dismissed: %s", action_id)
        return True

    def get_pending_optimizations(self) -> list[dict[str, Any]]:
        """返回所有待处理优化建议."""
        return [a.to_dict() for a in self._actions if a.status == "pending"]

    def get_optimization_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """返回最近的优化动作历史（newest first）."""
        return [a.to_dict() for a in reversed(self._actions[-limit:])]

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "total_actions": len(self._actions),
            "pending": len(self.get_pending_optimizations()),
            "history": self.get_optimization_history(limit=20),
        }


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
def _evolution_type_for(issue_type: str) -> str:
    """Map an issue type to an evolution type."""
    return {
        "low_accuracy": "prompt_refinement",
        "high_token": "prompt_refinement",
        "low_satisfaction": "strategy_adjustment",
        "high_error": "skill_upgrade",
    }.get(issue_type, "strategy_adjustment")


def _metric_for(issue_type: str) -> str:
    """Map an issue type to the improvement metric name."""
    return {
        "low_accuracy": "accuracy",
        "high_token": "token_consumed",
        "low_satisfaction": "satisfaction",
        "high_error": "error_rate",
    }.get(issue_type, "accuracy")


# Singleton instance.
optimization_loop = OptimizationLoop()
