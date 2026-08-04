"""Evolution Manager — Agent 自进化机制.

Implements the evolution component of the Agent Observation Layer
(架构第四层): the mechanism that lets Agents "越用越聪明".

Based on the feedback from the Optimization loop, the Evolution
manager records before/after states whenever an Agent's Prompt,
Skill strategy or knowledge base is adjusted, and can proactively
detect when an Agent's performance has degraded enough to warrant
an evolution cycle.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# When recent accuracy / satisfaction drops below these, evolution is needed.
_EVOLUTION_ACCURACY = 0.65
_EVOLUTION_SATISFACTION = 0.55


@dataclass
class EvolutionRecord:
    """Record of a single evolution event for one agent."""

    record_id: str
    agent_id: str
    evolution_type: str  # prompt_refinement/skill_upgrade/strategy_adjustment/knowledge_expansion
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    improvement_metric: str = ""
    before_value: float = 0.0
    after_value: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for API responses / persistence."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "evolution_type": self.evolution_type,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "improvement_metric": self.improvement_metric,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "timestamp": self.timestamp,
        }


class EvolutionManager:
    """Agent 自进化管理器 — 让 Agent 越用越聪明.

    基于优化闭环的反馈，自动调整 Agent 的 Prompt、Skill 策略、知识库。
    """

    def __init__(self) -> None:
        self._records: list[EvolutionRecord] = []

    # ------------------------------------------------------------------
    #  Recording
    # ------------------------------------------------------------------
    def record_evolution(
        self,
        agent_id: str,
        evolution_type: str,
        before: dict[str, Any],
        after: dict[str, Any],
        **kwargs: Any,
    ) -> EvolutionRecord:
        """记录一次进化事件（before → after）."""
        record = EvolutionRecord(
            record_id=f"evo_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            evolution_type=evolution_type,
            before_state=before or {},
            after_state=after or {},
            improvement_metric=kwargs.get("improvement_metric", ""),
            before_value=float(kwargs.get("before_value", 0.0)),
            after_value=float(kwargs.get("after_value", 0.0)),
        )
        self._records.append(record)
        logger.info(
            "Evolution recorded: %s (%s) %s",
            record.record_id, agent_id, evolution_type,
        )
        return record

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_agent_evolution_history(self, agent_id: str) -> list[dict[str, Any]]:
        """返回某 Agent 的进化历史（oldest first）."""
        return [r.to_dict() for r in self._records if r.agent_id == agent_id]

    def get_evolution_summary(self) -> dict[str, Any]:
        """全舰队进化摘要."""
        per_agent: dict[str, int] = {}
        per_type: dict[str, int] = {}
        for record in self._records:
            per_agent[record.agent_id] = per_agent.get(record.agent_id, 0) + 1
            per_type[record.evolution_type] = per_type.get(record.evolution_type, 0) + 1
        return {
            "total_evolutions": len(self._records),
            "evolved_agent_count": len(per_agent),
            "per_agent": per_agent,
            "per_type": per_type,
        }

    # ------------------------------------------------------------------
    #  Proactive evolution
    # ------------------------------------------------------------------
    def check_evolution_needed(self, agent_id: str) -> bool:
        """检查 Agent 是否需要进化（基于最近评估指标）.

        Governance / workflow_engine / sibling observation imports are
        deferred to method scope to avoid circular imports.
        """
        try:
            from carsoul_agent.observation.evaluation import evaluation_engine
            from carsoul_agent.observation.optimization import optimization_loop
        except Exception as exc:  # noqa: BLE001
            logger.debug("evolution check skipped: %s", exc)
            return False
        evals = evaluation_engine.get_agent_evaluations(agent_id, limit=10)
        if not evals:
            return False
        avg_accuracy = sum(e.get("accuracy", 0.0) for e in evals) / len(evals)
        avg_satisfaction = sum(e.get("user_satisfaction", 0.0) for e in evals) / len(evals)
        if avg_accuracy < _EVOLUTION_ACCURACY:
            return True
        if avg_satisfaction < _EVOLUTION_SATISFACTION:
            return True
        # pending high-priority optimizations also trigger evolution
        for action in optimization_loop.get_pending_optimizations():
            if action.get("agent_id") == agent_id and action.get("priority") == "high":
                return True
        return False

    def trigger_evolution(self, agent_id: str) -> EvolutionRecord | None:
        """触发一次进化：判定类型、采集 before/after、记录事件."""
        if not self.check_evolution_needed(agent_id):
            logger.debug("Evolution not needed for %s", agent_id)
            return None
        # Lazy import.
        try:
            from carsoul_agent.observation.evaluation import evaluation_engine
        except Exception as exc:  # noqa: BLE001
            logger.debug("evolution trigger skipped: %s", exc)
            return None
        evals = evaluation_engine.get_agent_evaluations(agent_id, limit=10)
        avg_accuracy = (
            sum(e.get("accuracy", 0.0) for e in evals) / len(evals) if evals else 0.0
        )
        avg_satisfaction = (
            sum(e.get("user_satisfaction", 0.0) for e in evals) / len(evals)
            if evals else 0.0
        )
        # Decide evolution type from the weakest dimension.
        if avg_accuracy < _EVOLUTION_ACCURACY:
            evolution_type = "prompt_refinement"
            metric = "accuracy"
            before_value = avg_accuracy
            target = _EVOLUTION_ACCURACY
        elif avg_satisfaction < _EVOLUTION_SATISFACTION:
            evolution_type = "strategy_adjustment"
            metric = "satisfaction"
            before_value = avg_satisfaction
            target = _EVOLUTION_SATISFACTION
        else:
            evolution_type = "knowledge_expansion"
            metric = "accuracy"
            before_value = avg_accuracy
            target = _EVOLUTION_ACCURACY
        before = {
            "avg_accuracy": round(avg_accuracy, 4),
            "avg_satisfaction": round(avg_satisfaction, 4),
            "evaluation_count": len(evals),
        }
        after = {
            "target": target,
            "action": f"apply {evolution_type} improvements",
        }
        return self.record_evolution(
            agent_id=agent_id,
            evolution_type=evolution_type,
            before=before,
            after=after,
            improvement_metric=metric,
            before_value=before_value,
            after_value=target,
        )

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "total_evolutions": len(self._records),
            "summary": self.get_evolution_summary(),
            "recent": [r.to_dict() for r in self._records[-10:]],
        }


# Singleton instance.
evolution_manager = EvolutionManager()
