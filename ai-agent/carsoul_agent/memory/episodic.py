"""情景记忆层（Episodic Memory）。

存储车辆历史事件与 Agent 任务经历，支持按车辆、按任务类型检索，
提供简单关键词搜索与车辆事件时间线回放，为 Agent 回顾过往经历、
复用历史经验提供数据支撑。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EpisodeRecord:
    """单条情景记忆记录。"""

    episode_id: str
    vehicle_id: str
    task_type: str
    event_description: str
    outcome: str
    timestamp: str
    agent_id: str
    related_data: dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "episode_id": self.episode_id,
            "vehicle_id": self.vehicle_id,
            "task_type": self.task_type,
            "event_description": self.event_description,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "related_data": self.related_data,
            "importance_score": self.importance_score,
        }


class EpisodicMemory:
    """情景记忆管理器：记录与检索车辆/任务事件。"""

    def __init__(self) -> None:
        self._episodes: list[EpisodeRecord] = []

    def record_episode(
        self,
        vehicle_id: str,
        task_type: str,
        event_description: str,
        outcome: str,
        agent_id: str,
        importance_score: float = 0.5,
        related_data: dict[str, Any] | None = None,
    ) -> EpisodeRecord:
        """记录一次车辆事件/任务经历。

        Args:
            vehicle_id: 关联车辆标识。
            task_type: 任务类型（如诊断、保养、救援等）。
            event_description: 事件描述。
            outcome: 事件结果/处置结果。
            agent_id: 执行该任务的 Agent 标识。
            importance_score: 重要程度评分（0.0-1.0）。
            related_data: 附加关联数据。

        Returns:
            新建的 EpisodeRecord。
        """
        episode = EpisodeRecord(
            episode_id=uuid.uuid4().hex[:12],
            vehicle_id=vehicle_id,
            task_type=task_type,
            event_description=event_description,
            outcome=outcome,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
            related_data=related_data or {},
            importance_score=importance_score,
        )
        self._episodes.append(episode)
        return episode

    def get_vehicle_episodes(self, vehicle_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """获取指定车辆的事件记录（按写入顺序，取最近 limit 条）。"""
        episodes = [e for e in self._episodes if e.vehicle_id == vehicle_id]
        return [e.to_dict() for e in episodes[-limit:]]

    def get_episodes_by_type(self, task_type: str, limit: int = 50) -> list[dict[str, Any]]:
        """按任务类型检索事件记录（取最近 limit 条）。"""
        episodes = [e for e in self._episodes if e.task_type == task_type]
        return [e.to_dict() for e in episodes[-limit:]]

    def search_episodes(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        """简单关键词搜索（匹配事件描述或结果，不区分大小写）。"""
        kw = keyword.lower()
        matched = [
            e
            for e in self._episodes
            if kw in e.event_description.lower() or kw in e.outcome.lower()
        ]
        return [e.to_dict() for e in matched[-limit:]]

    def get_vehicle_timeline(self, vehicle_id: str) -> list[dict[str, Any]]:
        """按时间升序返回指定车辆的事件时间线。"""
        episodes = [e for e in self._episodes if e.vehicle_id == vehicle_id]
        episodes.sort(key=lambda e: e.timestamp)
        return [e.to_dict() for e in episodes]

    def get_summary(self) -> dict[str, Any]:
        """情景记忆汇总信息。"""
        total = len(self._episodes)
        return {
            "total_episodes": total,
            "unique_vehicles": len({e.vehicle_id for e in self._episodes}),
            "task_types": list({e.task_type for e in self._episodes}),
            "avg_importance": (
                sum(e.importance_score for e in self._episodes) / total if total else 0.0
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（含全部记录与汇总）。"""
        return {
            "episodes": [e.to_dict() for e in self._episodes],
            "summary": self.get_summary(),
        }


# 默认共享实例（单进程开发/演示）。
episodic_memory = EpisodicMemory()
