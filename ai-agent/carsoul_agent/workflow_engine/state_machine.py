"""Workflow State Machine — 工作流状态管理 (§8).

Manages the lifecycle of an entire workflow execution:

              START
                ↓
           ANALYZING
                ↓
      ┌──────────┴──────────┐
      ↓                     ↓
   SUCCESS                ERROR
      ↓                     ↓
   VERIFY                 RETRY
      ↓                     ↓
  COMPLETE             (back to ANALYZING)

Each workflow execution transitions through these states, and the
state machine emits events that the engine and frontend can react to.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """Workflow-level states (§8)."""

    START = "START"
    ANALYZING = "ANALYZING"     # Tasks are being executed
    SUCCESS = "SUCCESS"         # All tasks completed
    ERROR = "ERROR"             # A task failed irrecoverably
    VERIFY = "VERIFY"           # Verifying results
    RETRY = "RETRY"             # Retrying after error
    COMPLETE = "COMPLETE"       # Done, verified, finalised
    HUMAN_PENDING = "HUMAN_PENDING"  # Waiting for human confirmation


# Valid workflow state transitions.
_WORKFLOW_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.START: {WorkflowState.ANALYZING},
    WorkflowState.ANALYZING: {WorkflowState.SUCCESS, WorkflowState.ERROR, WorkflowState.HUMAN_PENDING},
    WorkflowState.SUCCESS: {WorkflowState.VERIFY, WorkflowState.COMPLETE},
    WorkflowState.ERROR: {WorkflowState.RETRY, WorkflowState.COMPLETE},
    WorkflowState.VERIFY: {WorkflowState.COMPLETE, WorkflowState.ERROR},
    WorkflowState.RETRY: {WorkflowState.ANALYZING},
    WorkflowState.HUMAN_PENDING: {WorkflowState.ANALYZING, WorkflowState.COMPLETE},
    WorkflowState.COMPLETE: set(),  # terminal
}


class WorkflowEvent:
    """Emitted when a workflow changes state."""

    def __init__(
        self,
        workflow_id: str,
        old_state: WorkflowState,
        new_state: WorkflowState,
        detail: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.old_state = old_state
        self.new_state = new_state
        self.detail = detail
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "old_state": self.old_state.value,
            "new_state": self.new_state.value,
            "detail": self.detail,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class WorkflowStateMachine:
    """State machine for a single workflow execution.

    Tracks the current state, history of transitions, and supports
    event listeners for real-time monitoring.
    """

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        self._state = WorkflowState.START
        self._listeners: list[Callable[[WorkflowEvent], None]] = []
        self._history: list[dict[str, Any]] = []
        self._retry_count = 0
        self._max_workflow_retries = 1
        self._started_at = datetime.now(timezone.utc).isoformat()

    @property
    def state(self) -> WorkflowState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state == WorkflowState.COMPLETE

    def transition(
        self,
        new_state: WorkflowState,
        detail: str = "",
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Attempt a state transition. Returns False if invalid."""
        old_state = self._state
        allowed = _WORKFLOW_TRANSITIONS.get(old_state, set())
        if new_state not in allowed:
            logger.warning(
                "Workflow %s: invalid transition %s→%s",
                self.workflow_id, old_state.value, new_state.value,
            )
            return False

        self._state = new_state
        event = WorkflowEvent(self.workflow_id, old_state, new_state, detail, data)
        self._history.append(event.to_dict())
        self._notify(event)

        if new_state == WorkflowState.RETRY:
            self._retry_count += 1

        return True

    def can_retry(self) -> bool:
        return self._retry_count < self._max_workflow_retries

    def on_event(self, listener: Callable[[WorkflowEvent], None]) -> None:
        self._listeners.append(listener)

    def _notify(self, event: WorkflowEvent) -> None:
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Workflow listener error: %s", exc)

    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "state": self._state.value,
            "retry_count": self._retry_count,
            "started_at": self._started_at,
            "transitions": len(self._history),
            "history": self._history,
        }
