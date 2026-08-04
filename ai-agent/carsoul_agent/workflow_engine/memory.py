"""Task Memory — 工作流记忆机制 (§7).

Each workflow execution has a Task Memory that records:

  - Task ID
  - 目标 (goal)
  - 参与 Agent (participating agents)
  - 输入数据 (input data)
  - 中间结果 (intermediate results)
  - 最终结论 (final conclusion)
  - 用户反馈 (user feedback)

This enables the system to learn from past executions and provide
context for future ones.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class TaskMemory:
    """Per-workflow execution record (§7).

    Stores the complete execution context of a workflow run, including
    all task inputs, intermediate results, agent participations, and
    the final conclusion. This is the workflow-level analogue of the
    vehicle Digital Twin Memory.
    """

    def __init__(self, workflow_id: str, goal: str) -> None:
        self.workflow_id = workflow_id
        self.goal = goal
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: str | None = None

        self._participating_agents: list[str] = []
        self._input_data: dict[str, Any] = {}
        self._intermediate_results: dict[str, Any] = {}  # task_id → result
        self._final_conclusion: dict[str, Any] = {}
        self._user_feedback: dict[str, Any] = {}
        self._agent_performance: dict[str, dict[str, Any]] = {}  # agent_id → {duration, success, ...}

    def record_input(self, key: str, data: Any) -> None:
        self._input_data[key] = data

    def record_agent_participation(self, agent_id: str) -> None:
        if agent_id not in self._participating_agents:
            self._participating_agents.append(agent_id)

    def record_intermediate(self, task_id: str, result: dict[str, Any]) -> None:
        self._intermediate_results[task_id] = result

    def record_final_conclusion(self, conclusion: dict[str, Any]) -> None:
        self._final_conclusion = conclusion
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def record_feedback(self, feedback: dict[str, Any]) -> None:
        self._user_feedback = feedback

    def record_agent_performance(
        self,
        agent_id: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        if agent_id not in self._agent_performance:
            self._agent_performance[agent_id] = {
                "invocations": 0,
                "total_duration_ms": 0.0,
                "successes": 0,
                "failures": 0,
            }
        perf = self._agent_performance[agent_id]
        perf["invocations"] += 1
        perf["total_duration_ms"] += duration_ms
        if success:
            perf["successes"] += 1
        else:
            perf["failures"] += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "participating_agents": self._participating_agents,
            "input_data_keys": list(self._input_data.keys()),
            "intermediate_result_keys": list(self._intermediate_results.keys()),
            "final_conclusion": self._final_conclusion,
            "user_feedback": self._user_feedback,
            "agent_performance": self._agent_performance,
        }


# In-memory store of recent workflow executions (for demo/audit).
_recent_memories: list[TaskMemory] = []
_MAX_RECENT = 20


def store_memory(memory: TaskMemory) -> None:
    """Store a completed workflow's memory for future reference."""
    _recent_memories.append(memory)
    if len(_recent_memories) > _MAX_RECENT:
        _recent_memories.pop(0)


def get_recent_memories(limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve recent workflow memories (newest first)."""
    return [m.to_dict() for m in reversed(_recent_memories[-limit:])]
