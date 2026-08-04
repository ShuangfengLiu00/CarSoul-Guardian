"""Evaluation Engine — Agent 评估引擎.

Implements the evaluation component of the Agent Observation Layer
(架构第四层). Quantifies every Agent / workflow along four
dimensions defined in the design doc:

  - 诊断准确率 accuracy            (0–1)
  - 响应效率 response_efficiency   (0–1, 基于 token 消耗与耗时)
  - 用户满意度 user_satisfaction   (0–1)
  - 风险预测准确率 risk_accuracy   (0–1)

Evaluation records are produced by ``evaluate`` and enriched by
explicit user feedback (``record_user_feedback``). Trends feed the
Optimization loop.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Reference budgets for response-efficiency scoring (tunable).
_TOKEN_BUDGET = 4000
_DURATION_BUDGET = 8000  # ms


def _compute_efficiency(token_consumed: int, duration_ms: float) -> float:
    """Heuristic 0–1 score: less token + less time → higher efficiency."""
    token_score = 1.0 - min(token_consumed / _TOKEN_BUDGET, 1.0)
    duration_score = 1.0 - min(duration_ms / _DURATION_BUDGET, 1.0)
    return round(0.5 * token_score + 0.5 * duration_score, 4)


@dataclass
class EvaluationRecord:
    """Single evaluation of one agent within one workflow."""

    evaluation_id: str
    agent_id: str
    workflow_id: str
    timestamp: str
    # ---- evaluation dimensions ----
    accuracy: float = 0.0              # 诊断准确率 0–1
    response_efficiency: float = 0.0   # 响应效率（基于 token 与耗时）
    user_satisfaction: float = 0.0     # 用户满意度 0–1
    risk_accuracy: float = 0.0         # 风险预测准确率 0–1
    # ---- detailed metrics ----
    token_consumed: int = 0
    duration_ms: float = 0.0
    error_count: int = 0
    user_feedback: str = ""            # positive/neutral/negative

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for API responses / persistence."""
        return {
            "evaluation_id": self.evaluation_id,
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "accuracy": self.accuracy,
            "response_efficiency": self.response_efficiency,
            "user_satisfaction": self.user_satisfaction,
            "risk_accuracy": self.risk_accuracy,
            "token_consumed": self.token_consumed,
            "duration_ms": self.duration_ms,
            "error_count": self.error_count,
            "user_feedback": self.user_feedback,
        }


class EvaluationEngine:
    """Agent 评估引擎 — 评估准确率、响应效率、用户满意度、风险率."""

    def __init__(self) -> None:
        self._records: list[EvaluationRecord] = []
        # workflow_id → feedback envelope
        self._feedback: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    #  Record production
    # ------------------------------------------------------------------
    def evaluate(
        self,
        agent_id: str,
        workflow_id: str,
        **metrics: Any,
    ) -> EvaluationRecord:
        """创建并存储一条评估记录.

        Accepted keyword metrics: ``accuracy``, ``response_efficiency``,
        ``user_satisfaction``, ``risk_accuracy``, ``token_consumed``,
        ``duration_ms``, ``error_count``, ``user_feedback``.
        """
        token_consumed = int(metrics.get("token_consumed", 0))
        duration_ms = float(metrics.get("duration_ms", 0.0))
        response_efficiency = float(metrics.get("response_efficiency", 0.0))
        # auto-derive efficiency from token + duration when not provided
        if response_efficiency == 0.0 and (token_consumed or duration_ms):
            response_efficiency = _compute_efficiency(token_consumed, duration_ms)
        record = EvaluationRecord(
            evaluation_id=f"eval_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            workflow_id=workflow_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            accuracy=float(metrics.get("accuracy", 0.0)),
            response_efficiency=response_efficiency,
            user_satisfaction=float(metrics.get("user_satisfaction", 0.0)),
            risk_accuracy=float(metrics.get("risk_accuracy", 0.0)),
            token_consumed=token_consumed,
            duration_ms=duration_ms,
            error_count=int(metrics.get("error_count", 0)),
            user_feedback=metrics.get("user_feedback", ""),
        )
        # if feedback already exists for this workflow, apply it now
        fb = self._feedback.get(workflow_id)
        if fb is not None:
            record.user_satisfaction = fb["satisfaction"]
            record.user_feedback = fb["feedback"]
        self._records.append(record)
        logger.debug("Evaluation recorded: %s (%s)", record.evaluation_id, agent_id)
        return record

    def record_user_feedback(
        self,
        workflow_id: str,
        feedback: str,
        rating: int,
    ) -> None:
        """记录用户反馈（rating 1–5），并回填到该 workflow 的评估记录."""
        rating = max(1, min(5, rating))
        satisfaction = round(rating / 5.0, 4)
        if rating >= 4:
            label = "positive"
        elif rating == 3:
            label = "neutral"
        else:
            label = "negative"
        envelope = {
            "workflow_id": workflow_id,
            "feedback": feedback or label,
            "rating": rating,
            "satisfaction": satisfaction,
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._feedback[workflow_id] = envelope
        # back-fill existing evaluation records for this workflow
        for record in self._records:
            if record.workflow_id == workflow_id:
                record.user_satisfaction = satisfaction
                record.user_feedback = feedback or label

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_agent_evaluations(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """返回某 Agent 最近的评估记录（newest first）."""
        records = [r for r in self._records if r.agent_id == agent_id]
        return [r.to_dict() for r in reversed(records[-limit:])]

    def get_fleet_evaluation(self) -> dict[str, Any]:
        """全舰队评估摘要（按 agent 聚合）."""
        per_agent: dict[str, dict[str, Any]] = {}
        for record in self._records:
            bucket = per_agent.setdefault(
                record.agent_id,
                {
                    "agent_id": record.agent_id,
                    "count": 0,
                    "accuracy_sum": 0.0,
                    "efficiency_sum": 0.0,
                    "satisfaction_sum": 0.0,
                    "risk_accuracy_sum": 0.0,
                    "token_sum": 0,
                    "error_sum": 0,
                },
            )
            bucket["count"] += 1
            bucket["accuracy_sum"] += record.accuracy
            bucket["efficiency_sum"] += record.response_efficiency
            bucket["satisfaction_sum"] += record.user_satisfaction
            bucket["risk_accuracy_sum"] += record.risk_accuracy
            bucket["token_sum"] += record.token_consumed
            bucket["error_sum"] += record.error_count
        agents: list[dict[str, Any]] = []
        for bucket in per_agent.values():
            n = bucket["count"]
            agents.append({
                "agent_id": bucket["agent_id"],
                "evaluation_count": n,
                "avg_accuracy": round(bucket["accuracy_sum"] / n, 4) if n else 0.0,
                "avg_response_efficiency": round(bucket["efficiency_sum"] / n, 4) if n else 0.0,
                "avg_user_satisfaction": round(bucket["satisfaction_sum"] / n, 4) if n else 0.0,
                "avg_risk_accuracy": round(bucket["risk_accuracy_sum"] / n, 4) if n else 0.0,
                "avg_token_consumed": round(bucket["token_sum"] / n, 2) if n else 0.0,
                "total_errors": bucket["error_sum"],
            })
        return {
            "total_evaluations": len(self._records),
            "feedback_count": len(self._feedback),
            "agents": agents,
        }

    def get_accuracy_trend(
        self,
        agent_id: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """返回某 Agent 准确率时间序列（按天聚合）."""
        return self._trend(agent_id, days, key="accuracy")

    def get_satisfaction_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """返回全舰队满意度时间序列（按天聚合）."""
        return self._trend(None, days, key="user_satisfaction")

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    def _trend(
        self,
        agent_id: str | None,
        days: int,
        key: str,
    ) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        buckets: dict[str, list[float]] = {}
        for record in self._records:
            if agent_id is not None and record.agent_id != agent_id:
                continue
            try:
                ts = datetime.fromisoformat(record.timestamp)
            except ValueError:
                continue
            if ts < cutoff:
                continue
            day = ts.date().isoformat()
            buckets.setdefault(day, []).append(float(getattr(record, key)))
        return [
            {"date": day, "value": round(sum(vals) / len(vals), 4)}
            for day, vals in sorted(buckets.items())
        ]

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "total_evaluations": len(self._records),
            "feedback_count": len(self._feedback),
            "fleet": self.get_fleet_evaluation(),
        }


# Singleton instance.
evaluation_engine = EvaluationEngine()
