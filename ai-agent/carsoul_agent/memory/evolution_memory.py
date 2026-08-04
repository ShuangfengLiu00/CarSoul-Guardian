"""进化记忆层（Evolution Memory）。

存储系统进化历史与长期成长轨迹，包括技能演进（skill_evolution）、
经验发现（experience_discovery）、知识更新（knowledge_update）、
策略调整（strategy_adjustment）等里程碑事件，支撑 Agent 自我成长
与进化分析。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EvolutionMilestone:
    """单条进化里程碑记录。"""

    milestone_id: str
    agent_id: str
    milestone_type: str
    description: str
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    impact_metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "milestone_id": self.milestone_id,
            "agent_id": self.agent_id,
            "milestone_type": self.milestone_type,
            "description": self.description,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "impact_metrics": self.impact_metrics,
            "timestamp": self.timestamp,
        }


class EvolutionMemory:
    """进化记忆管理器：记录与检索系统进化里程碑。"""

    def __init__(self) -> None:
        self._milestones: list[EvolutionMilestone] = []

    def record_milestone(
        self,
        agent_id: str,
        milestone_type: str,
        description: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        impact_metrics: dict[str, Any] | None = None,
    ) -> EvolutionMilestone:
        """记录一次进化里程碑。

        Args:
            agent_id: 关联 Agent 标识。
            milestone_type: 里程碑类型，取值之一：
                skill_evolution / experience_discovery /
                knowledge_update / strategy_adjustment。
            description: 里程碑描述。
            before_state: 进化前状态快照。
            after_state: 进化后状态快照。
            impact_metrics: 影响度量指标。

        Returns:
            新建的 EvolutionMilestone。
        """
        milestone = EvolutionMilestone(
            milestone_id=uuid.uuid4().hex[:12],
            agent_id=agent_id,
            milestone_type=milestone_type,
            description=description,
            before_state=before_state or {},
            after_state=after_state or {},
            impact_metrics=impact_metrics or {},
        )
        self._milestones.append(milestone)
        return milestone

    def get_agent_milestones(self, agent_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """获取指定 Agent 的进化里程碑（取最近 limit 条）。"""
        milestones = [m for m in self._milestones if m.agent_id == agent_id]
        return [m.to_dict() for m in milestones[-limit:]]

    def get_milestones_by_type(self, milestone_type: str, limit: int = 50) -> list[dict[str, Any]]:
        """按里程碑类型检索（取最近 limit 条）。"""
        milestones = [m for m in self._milestones if m.milestone_type == milestone_type]
        return [m.to_dict() for m in milestones[-limit:]]

    def get_evolution_timeline(self, limit: int = 50) -> list[dict[str, Any]]:
        """全局进化时间线（按时间升序，取最近 limit 条）。"""
        milestones = sorted(self._milestones, key=lambda m: m.timestamp)
        return [m.to_dict() for m in milestones[-limit:]]

    def get_agent_growth(self, agent_id: str) -> dict[str, Any]:
        """获取某 Agent 的成长轨迹摘要。

        包含里程碑总数、技能演进次数（视为技能版本数）、经验发现次数
        （视为经验数），以及按类型分布的明细。
        """
        milestones = [m for m in self._milestones if m.agent_id == agent_id]
        type_counts: dict[str, int] = {}
        for m in milestones:
            type_counts[m.milestone_type] = type_counts.get(m.milestone_type, 0) + 1
        return {
            "agent_id": agent_id,
            "total_milestones": len(milestones),
            "skill_version_count": type_counts.get("skill_evolution", 0),
            "experience_count": type_counts.get("experience_discovery", 0),
            "milestone_type_breakdown": type_counts,
        }

    def get_summary(self) -> dict[str, Any]:
        """进化记忆汇总信息。"""
        type_counts: dict[str, int] = {}
        for m in self._milestones:
            type_counts[m.milestone_type] = type_counts.get(m.milestone_type, 0) + 1
        return {
            "total_milestones": len(self._milestones),
            "unique_agents": len({m.agent_id for m in self._milestones}),
            "milestone_type_breakdown": type_counts,
        }

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（含全部里程碑与汇总）。"""
        return {
            "milestones": [m.to_dict() for m in self._milestones],
            "summary": self.get_summary(),
        }


# 默认共享实例（单进程开发/演示）。
evolution_memory = EvolutionMemory()
