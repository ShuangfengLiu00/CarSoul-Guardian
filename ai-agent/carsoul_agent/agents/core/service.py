"""Sub-agent ⑤: 服务建议 / 处方·随访 (service).

The final node in the anomaly branch. Generates actionable advice and
fires the **guarded** tools:

    - push_reminder          → proactive user notification
    - record_lifecycle_event → archive entry
    - write_service_suggestion → persisted suggestion
    - create_service_order   → external service linkage (P0-1)

In addition, the service agent now drives the **three-level escalation
closed loop** (三级升级闭环) via ``EscalationManager``:

    Level 1 — 主动感知与判断 (already completed by the workflow)
    Level 2 — 分级通知车主 (first push → wait → escalated push)
    Level 3 — 联动外部救援 (create service orders)

**There are no actuator-control tools available.** This is the
tool-layer gate: the service agent physically cannot command the vehicle
to do anything — it can only remind, record, suggest, and link services.

Output: ``service_suggestion`` dict (also mirrored in ``action_store``).
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.agents.core.escalation import EscalationManager
from carsoul_agent.agents.core.state import AgentState, Trace, trace_entry
from carsoul_agent.tools import default_registry
from carsoul_agent.tools.guard_tools import action_store

logger = logging.getLogger(__name__)


class ServiceAgent:
    """Node ⑤ — 服务建议 Agent (guarded)."""

    name = "service"
    description = "生成可执行建议并触发主动提醒，仅限守护动作（提醒/记录/建议），不控制执行器。"

    def __init__(self, llm_client: Any | None = None, model_name: str = "gpt-4o-mini") -> None:
        self._llm = llm_client
        self._model = model_name
        self._tools = default_registry
        self._escalation = EscalationManager()

    # ------------------------------------------------------------------
    def run(self, state: AgentState) -> AgentState:
        trace: list[dict] = state.get("trace_log", [])
        is_normal = state.get("is_normal", False)

        if is_normal:
            # Normal branch: no reminder needed, just log the patrol.
            suggestion = self._normal_suggestion(state)
        else:
            suggestion = self._anomaly_suggestion(state)

        state["service_suggestion"] = suggestion
        trace.append(trace_entry(
            step=Trace.ACT,
            agent=self.name,
            detail=f"执行守护动作：{'记录巡检' if is_normal else '推送提醒 + 记录生命周期 + 写入建议'}",
            data=action_store.summary(),
        ))
        state["trace_log"] = trace
        return state

    # ------------------------------------------------------------------
    def _normal_suggestion(self, state: AgentState) -> dict:
        """Normal branch — record a patrol lifecycle event."""
        vehicle = state.get("vehicle_state", {})
        vehicle_id = vehicle.get("vehicle_id", 1)

        tool = self._tools.get("record_lifecycle_event")
        if tool:
            tool.run(
                vehicle_id=vehicle_id,
                event_type="guard_intervention",
                title="守护引擎例行巡检",
                detail="本轮巡检未发现异常，车辆状态正常。",
            )

        return {
            "actions": [],
            "reminder": None,
            "priority": "info",
            "patrol_completed": True,
        }

    # ------------------------------------------------------------------
    def _anomaly_suggestion(self, state: AgentState) -> dict:
        """Anomaly branch — push reminder + record event + write suggestion."""
        vehicle = state.get("vehicle_state", {})
        diagnosis = state.get("diagnosis", {}).get("primary", {})
        risk = state.get("risk_assessment", {})
        explanation = state.get("explanation", "")
        trip_context = state.get("trip_context", {})

        vehicle_id = vehicle.get("vehicle_id", 1)
        level = risk.get("level", "warning")
        root_cause = diagnosis.get("root_cause", "异常")
        # Expert-panel diagnoses carry `recommendation`; legacy ones carry
        # `actions_hint`. Fall back gracefully so the prescription always
        # has actionable steps.
        actions_hint = diagnosis.get("actions_hint") or []
        recommendation = diagnosis.get("recommendation", "")
        if not actions_hint and recommendation:
            actions_hint = [recommendation]

        # Determine priority from risk level.
        priority = "high" if level == "urgent" else "medium" if level == "warning" else "low"

        # 1. Push reminder (guarded tool).
        reminder_tool = self._tools.get("push_reminder")
        if reminder_tool:
            reminder_tool.run(
                vehicle_id=vehicle_id,
                level=level,
                title=f"CarSoul 守护提醒：{root_cause}",
                message=explanation,
            )

        # 2. Record lifecycle event (guarded tool).
        lifecycle_tool = self._tools.get("record_lifecycle_event")
        if lifecycle_tool:
            lifecycle_tool.run(
                vehicle_id=vehicle_id,
                event_type="anomaly_detected",
                title=f"检出异常：{root_cause}",
                detail=f"风险等级 {level}，概率 {risk.get('probability_percent', '—')}%",
            )

        # 2b. Long-trip: record a dedicated trip-check lifecycle event.
        if trip_context.get("is_long_trip") and lifecycle_tool:
            distance = trip_context.get("distance_km", 500)
            lifecycle_tool.run(
                vehicle_id=vehicle_id,
                event_type="trip_health_check",
                title=f"长途出行健康检查（{distance}km）",
                detail=(
                    f"出行前检查发现 {len(state.get('anomalies', []))} 项异常，"
                    f"风险等级 {level}。{risk.get('trip_risk_note', '')}"
                ),
            )

        # 3. Write service suggestion (guarded tool).
        suggestion_tool = self._tools.get("write_service_suggestion")
        if suggestion_tool:
            suggestion_tool.run(
                vehicle_id=vehicle_id,
                priority=priority,
                actions=actions_hint,
                explanation=explanation,
            )

        # 4. Execute three-level escalation closed loop (P0-1).
        escalation_result = self._escalation.execute(state)

        return {
            "actions": actions_hint,
            "reminder": {
                "level": level,
                "title": f"CarSoul 守护提醒：{root_cause}",
            },
            "priority": priority,
            "patrol_completed": False,
            "action_store_summary": action_store.summary(),
            "escalation": {
                "level_reached": escalation_result.level_reached,
                "chain": escalation_result.escalation_chain,
                "service_orders": escalation_result.service_orders,
            },
        }
