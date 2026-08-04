"""技能记忆层（Skill Memory）。

存储 Agent 技能版本与执行历史，用于追踪技能成功率、执行耗时与版本演进，
为技能退化检测、版本回滚与技能优化提供数据支撑。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class SkillExecutionRecord:
    """单条技能执行记录。"""

    record_id: str
    skill_id: str
    skill_version: str
    agent_id: str
    task_id: str
    success: bool
    execution_time_ms: int
    result_summary: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "record_id": self.record_id,
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "result_summary": self.result_summary,
            "timestamp": self.timestamp,
        }


class SkillMemory:
    """技能记忆管理器：记录与检索技能执行历史。"""

    def __init__(self) -> None:
        self._records: list[SkillExecutionRecord] = []

    def record_execution(
        self,
        skill_id: str,
        skill_version: str,
        agent_id: str,
        task_id: str,
        success: bool,
        execution_time_ms: int,
        result_summary: str,
    ) -> SkillExecutionRecord:
        """记录一次技能执行。

        Args:
            skill_id: 技能标识。
            skill_version: 技能版本号。
            agent_id: 执行该技能的 Agent 标识。
            task_id: 关联任务标识。
            success: 是否执行成功。
            execution_time_ms: 执行耗时（毫秒）。
            result_summary: 结果摘要。

        Returns:
            新建的 SkillExecutionRecord。
        """
        record = SkillExecutionRecord(
            record_id=uuid.uuid4().hex[:12],
            skill_id=skill_id,
            skill_version=skill_version,
            agent_id=agent_id,
            task_id=task_id,
            success=success,
            execution_time_ms=execution_time_ms,
            result_summary=result_summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._records.append(record)
        return record

    def get_skill_history(self, skill_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """获取指定技能的执行历史（取最近 limit 条）。"""
        records = [r for r in self._records if r.skill_id == skill_id]
        return [r.to_dict() for r in records[-limit:]]

    def get_agent_skill_executions(self, agent_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """获取指定 Agent 的技能执行记录（取最近 limit 条）。"""
        records = [r for r in self._records if r.agent_id == agent_id]
        return [r.to_dict() for r in records[-limit:]]

    def get_skill_success_rate(self, skill_id: str) -> dict[str, Any]:
        """统计指定技能的成功率与平均耗时。"""
        records = [r for r in self._records if r.skill_id == skill_id]
        total = len(records)
        if total == 0:
            return {
                "skill_id": skill_id,
                "total": 0,
                "success": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
            }
        success_count = sum(1 for r in records if r.success)
        avg_time = sum(r.execution_time_ms for r in records) / total
        return {
            "skill_id": skill_id,
            "total": total,
            "success": success_count,
            "success_rate": success_count / total,
            "avg_execution_time_ms": avg_time,
        }

    def get_summary(self) -> dict[str, Any]:
        """技能记忆汇总信息。"""
        total = len(self._records)
        return {
            "total_records": total,
            "unique_skills": len({r.skill_id for r in self._records}),
            "unique_agents": len({r.agent_id for r in self._records}),
            "overall_success_rate": (
                sum(1 for r in self._records if r.success) / total if total else 0.0
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（含全部记录与汇总）。"""
        return {
            "records": [r.to_dict() for r in self._records],
            "summary": self.get_summary(),
        }


# 默认共享实例（单进程开发/演示）。
skill_memory = SkillMemory()
