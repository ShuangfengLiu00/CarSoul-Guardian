"""Agent Router — Agent 路由器 (§4.3).

Selects the best agent for a task based on:
  1. 任务类型 (task type → required capability)
  2. Agent 能力 (does the agent have the capability?)
  3. 当前状态 (is the agent ACTIVE?)
  4. 历史准确率 (which agent has performed best historically?)

This implements the dynamic scheduling described in §4.3, replacing
the hard-coded routing in the original workflow.
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.governance.registry import AgentState, managed_registry
from carsoul_agent.workflow_engine.planner import Task

logger = logging.getLogger(__name__)

# Task type → required capability mapping.
_TASK_CAPABILITY_MAP: dict[str, list[str]] = {
    "perception": ["anomaly_detection", "threshold_analysis", "semantic_detection"],
    "diagnosis": ["expert_consultation", "root_cause_analysis", "knowledge_matching"],
    "judge": ["conflict_detection", "confidence_weighting", "decision_fusion"],
    "risk": ["risk_quantification", "probability_estimation", "eta_prediction"],
    "explainer": ["natural_language_generation", "report_formatting", "trip_report"],
    "service": ["action_recommendation", "reminder_generation", "escalation"],
}

# Task type → canonical agent_id (fallback when multiple agents match).
_TASK_DEFAULT_AGENT: dict[str, str] = {
    "perception": "perception",
    "diagnosis": "diagnosis",
    "judge": "judge",
    "risk": "risk",
    "explainer": "explainer",
    "service": "service",
}


class AgentRouter:
    """Routes tasks to the best available agent (§4.3).

    Routing logic:
      1. Find all ACTIVE agents with the required capability.
      2. If multiple candidates, pick the one with the highest
         historical success rate.
      3. If no candidate is ACTIVE, try BUSY agents (queue).
      4. If no agent at all, fall back to the default agent_id
         from the task definition.
    """

    def route(self, task: Task) -> str:
        """Select the best agent_id for a task. Returns an agent_id string."""
        required_caps = _TASK_CAPABILITY_MAP.get(task.task_type, [])

        # Step 1: find ACTIVE agents with matching capabilities.
        candidates = []
        for meta in managed_registry.all_metadata():
            if meta.state != AgentState.ACTIVE:
                continue
            if any(cap in meta.capabilities for cap in required_caps):
                success_rate = (
                    meta.success_count / meta.total_invocations
                    if meta.total_invocations > 0
                    else 0.75  # default for new agents
                )
                candidates.append((meta.agent_id, success_rate))

        if candidates:
            # Pick the highest success-rate agent.
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_id = candidates[0][0]
            logger.debug("Router: task %s → agent %s (success_rate=%.2f)",
                         task.task_id, best_id, candidates[0][1])
            return best_id

        # Step 2: fallback to the task's predefined agent_id.
        agent_id = task.agent_id or _TASK_DEFAULT_AGENT.get(task.task_type, "perception")
        logger.debug("Router: task %s → fallback agent %s", task.task_id, agent_id)
        return agent_id

    def route_batch(self, tasks: list[Task]) -> dict[str, str]:
        """Route a batch of tasks. Returns {task_id: agent_id}."""
        return {t.task_id: self.route(t) for t in tasks}
