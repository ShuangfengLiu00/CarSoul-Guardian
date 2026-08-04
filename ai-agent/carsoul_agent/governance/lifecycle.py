"""Agent Lifecycle Manager — Agent 生命周期管理 (§3.1).

Manages the real-time state transitions of every registered agent:

    ACTIVE ↔ BUSY         (task starts / completes)
    ACTIVE → ERROR         (execution failure)
    ERROR → ACTIVE         (recovery)
    ACTIVE → UPDATING      (version upgrade)
    UPDATING → ACTIVE      (upgrade complete)
    Any → OFFLINE          (shutdown)
    OFFLINE → ACTIVE       (restart)

The manager also tracks invocation statistics and emits lifecycle events
that the workflow engine can react to.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from carsoul_agent.governance.registry import AgentState, managed_registry

logger = logging.getLogger(__name__)

# Valid state transitions (state machine edges).
_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.ACTIVE: {AgentState.BUSY, AgentState.ERROR, AgentState.UPDATING, AgentState.OFFLINE},
    AgentState.BUSY: {AgentState.ACTIVE, AgentState.ERROR},
    AgentState.ERROR: {AgentState.ACTIVE, AgentState.OFFLINE},
    AgentState.UPDATING: {AgentState.ACTIVE, AgentState.ERROR},
    AgentState.OFFLINE: {AgentState.ACTIVE},
}


class LifecycleEvent:
    """An event emitted when an agent changes state."""

    def __init__(self, agent_id: str, old_state: AgentState, new_state: AgentState, reason: str = "") -> None:
        self.agent_id = agent_id
        self.old_state = old_state
        self.new_state = new_state
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "old_state": self.old_state.value,
            "new_state": self.new_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class AgentLifecycleManager:
    """Manages agent state transitions and lifecycle events.

    Provides a context manager for safe task execution:

        with lifecycle_manager.task_scope("battery_expert"):
            # agent is BUSY here; auto-recovers on success / ERROR on failure
            result = expert.consult(state)
    """

    def __init__(self) -> None:
        self._listeners: list[Callable[[LifecycleEvent], None]] = []
        self._event_log: list[dict[str, Any]] = []

    def transition(
        self,
        agent_id: str,
        new_state: AgentState,
        reason: str = "",
    ) -> bool:
        """Attempt a state transition. Returns False if invalid."""
        meta = managed_registry.get(agent_id)
        if meta is None:
            logger.warning("Lifecycle: unknown agent '%s'", agent_id)
            return False

        old_state = meta.state
        allowed = _TRANSITIONS.get(old_state, set())
        if new_state not in allowed and old_state != new_state:
            logger.warning(
                "Lifecycle: invalid transition %s %s→%s (allowed: %s)",
                agent_id, old_state.value, new_state.value,
                [s.value for s in allowed],
            )
            return False

        managed_registry.update_state(agent_id, new_state)
        event = LifecycleEvent(agent_id, old_state, new_state, reason)
        self._event_log.append(event.to_dict())
        self._notify(event)
        return True

    def task_scope(self, agent_id: str):
        """Context manager: marks an agent BUSY during a task, then ACTIVE/ERROR."""
        return _TaskScope(self, agent_id)

    def mark_error(self, agent_id: str, reason: str = "") -> None:
        self.transition(agent_id, AgentState.ERROR, reason)

    def recover(self, agent_id: str) -> bool:
        return self.transition(agent_id, AgentState.ACTIVE, "recovered")

    def shutdown(self, agent_id: str) -> None:
        self.transition(agent_id, AgentState.OFFLINE, "shutdown")

    def restart(self, agent_id: str) -> bool:
        return self.transition(agent_id, AgentState.ACTIVE, "restart")

    # ---- Event system ------------------------------------------------
    def on_event(self, listener: Callable[[LifecycleEvent], None]) -> None:
        self._listeners.append(listener)

    def _notify(self, event: LifecycleEvent) -> None:
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Lifecycle listener error: %s", exc)

    def event_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._event_log[-limit:]

    def health_summary(self) -> dict[str, Any]:
        """Overall health of the agent fleet."""
        all_agents = managed_registry.all_metadata()
        return {
            "total": len(all_agents),
            "active": sum(1 for a in all_agents if a.state == AgentState.ACTIVE),
            "busy": sum(1 for a in all_agents if a.state == AgentState.BUSY),
            "error": sum(1 for a in all_agents if a.state == AgentState.ERROR),
            "offline": sum(1 for a in all_agents if a.state == AgentState.OFFLINE),
            "recent_events": self._event_log[-10:],
        }


class _TaskScope:
    """Context manager that manages BUSY→ACTIVE/ERROR transitions."""

    def __init__(self, manager: AgentLifecycleManager, agent_id: str) -> None:
        self._manager = manager
        self._agent_id = agent_id
        self._success = True

    def __enter__(self):
        self._manager.transition(self._agent_id, AgentState.BUSY, "task_started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._success = False
            self._manager.transition(
                self._agent_id, AgentState.ERROR,
                f"task_failed: {exc_val}" if exc_val else "task_failed",
            )
            managed_registry.record_invocation(self._agent_id, success=False)
        else:
            self._manager.transition(self._agent_id, AgentState.ACTIVE, "task_completed")
            managed_registry.record_invocation(self._agent_id, success=True)
        return False  # don't suppress exceptions


# Singleton.
lifecycle_manager = AgentLifecycleManager()
