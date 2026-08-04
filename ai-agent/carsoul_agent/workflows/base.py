"""Workflow orchestration (foundation).

Defines the workflow interface and a simple sequential pipeline.
The actual multi-agent orchestration is implemented in
``agents/core/workflow.py`` (five sub-agents: perception → diagnosis
→ risk → explainer → service). This module provides the reusable
base classes that other custom workflows can extend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowContext:
    user: str
    message: str
    session_id: str | None = None
    state: dict = field(default_factory=dict)


class BaseWorkflow(ABC):
    """A workflow runs a sequence of steps over a shared context."""

    name: str = "base_workflow"

    @abstractmethod
    def run(self, ctx: WorkflowContext) -> dict[str, Any]:
        """Execute the workflow and return a result dict."""


class SequentialWorkflow(BaseWorkflow):
    """Runs registered steps in order, merging their outputs."""

    name = "sequential"

    def __init__(self) -> None:
        self._steps: list = []

    def add_step(self, step) -> None:
        self._steps.append(step)

    def run(self, ctx: WorkflowContext) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for step in self._steps:
            out = step(ctx) if callable(step) else step.run(ctx)
            if isinstance(out, dict):
                result.update(out)
        return result
