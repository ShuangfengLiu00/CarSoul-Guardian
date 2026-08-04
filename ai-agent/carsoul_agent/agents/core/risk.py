"""Sub-agent ③: 风险评估 (risk).

Inputs ``diagnosis`` and trend data, then quantifies the risk into a
level, probability, and estimated time-to-danger (ETA). The output
directly determines how urgent the service agent's reminder will be.

Output: ``risk_assessment`` dict.
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.agents.core.state import AgentState, Trace, trace_entry

logger = logging.getLogger(__name__)

# ---- severity → risk-level mapping -------------------------------- #
_SEVERITY_TO_LEVEL = {
    "low": "info",
    "medium": "warning",
    "high": "urgent",
    "urgent": "urgent",
}

# ---- severity → ETA hours (estimated time to danger) --------------- #
_SEVERITY_TO_ETA = {
    "low": 720,      # ~30 days
    "medium": 168,   # ~7 days
    "high": 2,       # 2 hours
    "urgent": 1,     # 1 hour
}

# ---- severity → probability (%) ----------------------------------- #
_SEVERITY_TO_PROB = {
    "low": 20,
    "medium": 50,
    "high": 80,
    "urgent": 95,
}

# ---- severity → trend direction ----------------------------------- #
_SEVERITY_TO_TREND = {
    "low": "stable",
    "medium": "rising",
    "high": "rising_fast",
    "urgent": "critical",
}


class RiskAgent:
    """Node ③ — 风险评估 Agent."""

    name = "risk"
    description = "量化风险等级、发生概率与预计剩余可用时间，决定提醒紧迫度。"

    def __init__(self, llm_client: Any | None = None, model_name: str = "gpt-4o-mini") -> None:
        self._llm = llm_client
        self._model = model_name

    # ------------------------------------------------------------------
    def run(self, state: AgentState) -> AgentState:
        diagnosis: dict = state.get("diagnosis", {})
        trace: list[dict] = state.get("trace_log", [])
        trip_context: dict = state.get("trip_context", {})
        calibration: dict = state.get("calibration_context", {}) or {}

        primary = diagnosis.get("primary", {})
        secondary = diagnosis.get("secondary", [])
        severity = primary.get("severity", "low")

        level = _SEVERITY_TO_LEVEL.get(severity, "info")
        eta_hours = _SEVERITY_TO_ETA.get(severity, 720)
        probability = _SEVERITY_TO_PROB.get(severity, 20)
        trend = _SEVERITY_TO_TREND.get(severity, "stable")

        # Factor in confidence — lower confidence widens the ETA window.
        confidence = primary.get("confidence", 0.85)
        if confidence < 0.6:
            eta_hours = int(eta_hours * 1.5)

        # ---- 自纠错校准：根据历史反馈调整本次评估 ----
        # 高误报率 → 下调置信度、放宽ETA、降低概率，避免过度预警；
        # 高准确率 → 维持标准。这是 Agent「从反馈中学习」的真实体现。
        calibration_applied = False
        calibration_note = ""
        if calibration.get("has_history"):
            false_alarm_rate = calibration.get("false_alarm_rate") or 0
            accuracy_rate = calibration.get("accuracy_rate") or 0
            if false_alarm_rate >= 0.4:
                # 误报率偏高：放宽ETA窗口1.5倍、概率下调15%
                eta_hours = int(eta_hours * 1.5)
                probability = max(10, probability - 15)
                confidence = max(0.4, confidence - 0.15)
                calibration_applied = True
                calibration_note = (
                    f"已根据历史反馈自纠错（误报率{false_alarm_rate*100:.0f}%）："
                    f"下调置信度至{confidence:.2f}，放宽ETA至{eta_hours}h。"
                )
            elif accuracy_rate >= 0.8:
                calibration_note = (
                    f"历史预测准确率{accuracy_rate*100:.0f}%良好，维持标准评估。"
                )

        # Multiple secondary issues bump the level one notch.
        if len(secondary) >= 2 and level == "info":
            level = "warning"

        # ---- Long-trip scenario risk amplification ----
        # In a long-trip context, battery/brake/tire anomalies are more
        # dangerous because the vehicle will be under sustained load.
        # We amplify the risk level and add trip-specific context.
        trip_risk_note = ""
        is_long_trip = trip_context.get("is_long_trip", False)
        if is_long_trip:
            distance = trip_context.get("distance_km", 500)
            anomaly_categories = {
                a.get("category") for a in state.get("anomalies", [])
            }
            # Battery thermal anomaly on a long trip = significantly higher risk.
            if "battery" in anomaly_categories:
                if level == "info":
                    level = "warning"
                    severity = "medium"
                elif level == "warning":
                    level = "urgent"
                    severity = "high"
                probability = min(95, probability + 20)
                trip_risk_note = (
                    f"长途出行 {distance}km，电池温控异常在高速连续大功率放电下"
                    f"可能恶化 3-8℃，途中快充可能再升 5-10℃"
                )
            # Brake/tire wear on long trip = elevated safety risk.
            if "brake" in anomaly_categories or "tire" in anomaly_categories:
                probability = min(95, probability + 10)
                if not trip_risk_note:
                    trip_risk_note = (
                        f"长途出行 {distance}km，制动/轮胎磨损在连续行驶中风险加剧"
                    )
            # Longer distance → shorter effective ETA (less margin).
            if distance >= 500:
                eta_hours = min(eta_hours, 168)  # cap at ~7 days

        risk_assessment = {
            "level": level,
            "severity": severity,
            "probability_percent": probability,
            "eta_hours": eta_hours,
            "trend": trend,
            "confidence": confidence,
            "primary_type": primary.get("type"),
            "secondary_count": len(secondary),
            "is_long_trip": is_long_trip,
            "trip_risk_note": trip_risk_note,
            "trip_distance": trip_context.get("distance_km") if is_long_trip else None,
            "calibration_applied": calibration_applied,
            "calibration_note": calibration_note,
        }

        trace.append(trace_entry(
            step=Trace.REASON,
            agent=self.name,
            detail=(
                f"风险量化：等级 {level}，概率 {probability}%，"
                f"预计 {eta_hours}h 触险，趋势 {trend}"
                + (f"（长途场景：{trip_risk_note}）" if trip_risk_note else "")
                + (f"（自纠错：{calibration_note}）" if calibration_note else "")
            ),
            data=risk_assessment,
        ))

        state["risk_assessment"] = risk_assessment
        state["trace_log"] = trace
        return state
