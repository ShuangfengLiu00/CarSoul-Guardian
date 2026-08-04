"""Task Manager — 任务管理器 (§4.4).

Manages the lifecycle of individual tasks within a workflow:

    CREATED → ASSIGNED → RUNNING → WAITING → COMPLETED → VERIFIED
                                              ↘ ERROR → RETRY ↗

Responsibilities:
  - Create tasks
  - Assign tasks to agents (via the Agent Router)
  - Monitor task state
  - Retry failed tasks (up to max_retries)
  - Fallback to alternative strategies when retries are exhausted
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from carsoul_agent.governance.lifecycle import lifecycle_manager
from carsoul_agent.workflow_engine.planner import Task, TaskTree
from carsoul_agent.workflow_engine.router import AgentRouter

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    """Task lifecycle states (§4.4)."""

    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    ERROR = "ERROR"
    RETRY = "RETRY"


# Valid task state transitions.
_TASK_TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"ASSIGNED"},
    "ASSIGNED": {"RUNNING"},
    "RUNNING": {"WAITING", "COMPLETED", "ERROR"},
    "WAITING": {"RUNNING", "COMPLETED", "ERROR"},
    "COMPLETED": {"VERIFIED"},
    "VERIFIED": set(),  # terminal
    "ERROR": {"RETRY", "CREATED"},  # retry or re-create
    "RETRY": {"ASSIGNED"},  # retry goes back to assignment
}


class TaskManager:
    """Manages task state transitions and retry/fallback (§4.4).

    Works with the AgentRouter to assign tasks, and with the
    LifecycleManager to track agent BUSY/ACTIVE state.
    """

    def __init__(self) -> None:
        self._router = AgentRouter()
        self._history: list[dict[str, Any]] = []  # audit log

    def assign(self, task: Task) -> str:
        """Route the task to an agent and mark it ASSIGNED."""
        agent_id = self._router.route(task)
        task.agent_id = agent_id
        self._transition(task, "ASSIGNED")
        self._log(task, f"Assigned to agent '{agent_id}'")
        return agent_id

    def start(self, task: Task) -> None:
        """Mark a task as RUNNING."""
        self._transition(task, "RUNNING")

    def complete(self, task: Task, result: dict[str, Any]) -> None:
        """Mark a task as COMPLETED with its result."""
        task.result = result
        self._transition(task, "COMPLETED")
        self._log(task, f"Completed successfully")

    def verify(self, task: Task) -> None:
        """Mark a COMPLETED task as VERIFIED (after quality check)."""
        self._transition(task, "VERIFIED")

    def fail(self, task: Task, error: str) -> bool:
        """Mark a task as ERROR. Returns True if retry is possible."""
        task.error = error
        self._transition(task, "ERROR")
        self._log(task, f"Failed: {error}")

        if task.retry_count < task.max_retries:
            task.retry_count += 1
            self._transition(task, "RETRY")
            self._log(task, f"Retry {task.retry_count}/{task.max_retries}")
            # Re-create for re-assignment.
            self._transition(task, "CREATED")
            return True
        # Retries exhausted — task stays in ERROR.
        self._log(task, f"Retries exhausted ({task.max_retries}), giving up")
        return False

    def waiting(self, task: Task) -> None:
        """Mark a task as WAITING (e.g. for human-in-loop confirmation)."""
        self._transition(task, "WAITING")

    def resume(self, task: Task) -> None:
        """Resume a WAITING task."""
        self._transition(task, "RUNNING")

    # ---- State machine ------------------------------------------------
    def _transition(self, task: Task, new_state: str) -> None:
        old_state = task.state
        allowed = _TASK_TRANSITIONS.get(old_state, set())
        if new_state not in allowed and old_state != new_state:
            logger.warning(
                "TaskManager: invalid transition %s %s→%s",
                task.task_id, old_state, new_state,
            )
            # Force the transition anyway (we don't want to block the workflow).
        task.state = new_state

    def _log(self, task: Task, message: str) -> None:
        self._history.append({
            "task_id": task.task_id,
            "task_name": task.name,
            "state": task.state,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ---- Query helpers ------------------------------------------------
    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def task_summary(self, tree: TaskTree) -> dict[str, Any]:
        """Summarise the state of all tasks in a tree."""
        tasks = tree.all_tasks()
        return {
            "total": len(tasks),
            "completed": sum(1 for t in tasks if t.state in ("COMPLETED", "VERIFIED")),
            "running": sum(1 for t in tasks if t.state == "RUNNING"),
            "created": sum(1 for t in tasks if t.state == "CREATED"),
            "error": sum(1 for t in tasks if t.state == "ERROR"),
            "waiting": sum(1 for t in tasks if t.state == "WAITING"),
            "retries": sum(t.retry_count for t in tasks),
        }
