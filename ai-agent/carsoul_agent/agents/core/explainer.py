"""Sub-agent ④: 解释生成 (explainer).

This is the **dual-twin convergence node** — it merges the diagnosis +
risk assessment with the driver profile to produce user-facing language.

The driver profile's ``driving_style`` controls the tone:
  - ``eco`` (节能型)     → emphasise energy / thermal impact
  - ``aggressive`` (激进型) → emphasise safety risk
  - ``balanced`` (均衡型)   → balanced tone

An LLM (if configured) generates the natural-language explanation;
offline mode uses structured templates that still adapt to the profile.

This node also handles the **normal-report branch**: when the perception
agent found no anomalies, the explainer produces a reassuring summary
instead of running the full diagnosis→risk→service chain.
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.agents.core.state import AgentState, Trace, trace_entry

logger = logging.getLogger(__name__)

# ---- driver-profile → tone presets -------------------------------- #
_TONE_PRESETS = {
    "eco": {
        "label": "节能型",
        "safety_prefix": "温馨提示",
        "focus": "能耗与散热",
    },
    "aggressive": {
        "label": "激进型",
        "safety_prefix": "安全警告",
        "focus": "行车安全",
    },
    "balanced": {
        "label": "均衡型",
        "safety_prefix": "守护提醒",
        "focus": "综合状态",
    },
}


class ExplainerAgent:
    """Node ④ — 解释生成 Agent."""

    name = "explainer"
    description = "按驾驶者画像适配语言，将诊断与风险转为用户可理解的解释。"

    def __init__(self, llm_client: Any | None = None, model_name: str = "gpt-4o-mini") -> None:
        self._llm = llm_client
        self._model = model_name

    # ------------------------------------------------------------------
    def run(self, state: AgentState) -> AgentState:
        trace: list[dict] = state.get("trace_log", [])
        is_normal = state.get("is_normal", False)
        trip_context = state.get("trip_context", {})
        is_long_trip = trip_context.get("is_long_trip", False)

        if is_normal:
            explanation = self._normal_report(state)
            trace.append(trace_entry(
                step=Trace.NORMAL,
                agent=self.name,
                detail="生成正常报告",
                data={"is_normal": True},
            ))
        else:
            explanation = self._anomaly_report(state)
            # Build structured trip report for long-trip scenarios.
            if is_long_trip:
                trip_report = self._build_trip_report(state)
                state["trip_report"] = trip_report
                trace.append(trace_entry(
                    step=Trace.TOOL,
                    agent=self.name,
                    detail=f"生成结构化出行健康报告（风险等级：{trip_report.get('risk_level', 'N/A')}）",
                    data={"trip_report": True, "distance_km": trip_context.get("distance_km")},
                ))
            else:
                trace.append(trace_entry(
                    step=Trace.TOOL,
                    agent=self.name,
                    detail="按驾驶画像生成解释（画像适配工具）",
                    data={"driving_style": state.get("driver_profile", {}).get("driving_style")},
                ))

        state["explanation"] = explanation
        state["trace_log"] = trace
        return state

    # ------------------------------------------------------------------
    def _build_trip_report(self, state: AgentState) -> dict:
        """Build a structured trip health report for long-trip scenarios.

        This structured output is consumed by the frontend to render a
        visual report card — making the Agent's analysis visible to
        judges at a glance.
        """
        diagnosis = state.get("diagnosis", {}).get("primary", {})
        risk = state.get("risk_assessment", {})
        trip_context = state.get("trip_context", {})
        anomalies = state.get("anomalies", [])
        knowledge = state.get("knowledge_retrieval", {})

        distance = trip_context.get("distance_km", 500)
        charging_stops = trip_context.get("charging_stops_needed", 2)
        level = risk.get("level", "warning")

        # Map risk level to display.
        level_map = {"info": ("低", "green"), "warning": ("中", "orange"),
                      "urgent": ("高", "red")}
        risk_label, risk_color = level_map.get(level, ("中", "orange"))

        # Build problem list from anomalies.
        problems = []
        for a in anomalies:
            problems.append({
                "item": a.get("item", "未知"),
                "value": str(a.get("actual", "—")),
                "threshold": str(a.get("threshold", "—")),
                "severity": a.get("level", "info"),
                "detail": a.get("detail", ""),
            })

        # Build recommendations from diagnosis + risk.
        recommendations = []
        actions_hint = diagnosis.get("actions_hint") or []
        recommendation = diagnosis.get("recommendation", "")
        if actions_hint:
            recommendations.extend(actions_hint)
        elif recommendation:
            recommendations.append(recommendation)

        # Add trip-specific recommendations.
        recommendations.extend([
            f"途中每200km补电一次，共规划{charging_stops}个充电站点",
            "避免高温时段连续行驶，每2小时休息散热",
            "充电前静置15分钟散热，避免电池高温时快充",
        ])

        # Determine verdict.
        if level == "urgent":
            verdict = "建议出行前维修，暂不建议长途行驶"
        elif level == "warning":
            verdict = "建议出行前检测，可继续行驶但需密切监控"
        else:
            verdict = "车辆状态良好，可安全出行"

        return {
            "title": "长途出行健康检查报告",
            "risk_level": risk_label,
            "risk_color": risk_color,
            "risk_probability": risk.get("probability_percent", 0),
            "distance_km": distance,
            "estimated_hours": trip_context.get("estimated_hours", 8),
            "problems": problems,
            "root_cause": diagnosis.get("root_cause", "未知"),
            "knowledge_match": diagnosis.get("knowledge_match", ""),
            "impact": risk.get("trip_risk_note", ""),
            "recommendations": recommendations,
            "charging_plan": {
                "stops": charging_stops,
                "interval_km": 200,
                "strategy": "每次充至80%继续行驶，最后一段充满",
            },
            "knowledge_sources": knowledge.get("sources", [])[:3],
            "verdict": verdict,
        }

    # ------------------------------------------------------------------
    def _normal_report(self, state: AgentState) -> str:
        """Generate a reassuring report when no anomalies were found."""
        vehicle = state.get("vehicle_state", {})
        health_score = vehicle.get("health_score", "—")
        brand = vehicle.get("brand", "")
        model = vehicle.get("model", "")
        mileage = vehicle.get("mileage", "—")

        return (
            f"【CarSoul 守护 · 巡检报告】您的 {brand} {model}（里程 {mileage} km）"
            f"当前健康指数 {health_score}/100，各项指标正常。\n"
            f"守护引擎已完成本轮巡检，未发现异常。下次保养临近时将主动提醒您。"
        )

    # ------------------------------------------------------------------
    def _anomaly_report(self, state: AgentState) -> str:
        """Generate a risk-adapted explanation for the detected anomaly."""
        diagnosis = state.get("diagnosis", {}).get("primary", {})
        risk = state.get("risk_assessment", {})
        profile = state.get("driver_profile", {})
        vehicle = state.get("vehicle_state", {})

        style = profile.get("driving_style", "balanced")
        tone = _TONE_PRESETS.get(style, _TONE_PRESETS["balanced"])

        root_cause = diagnosis.get("root_cause", "未知异常")
        description = diagnosis.get("description", "")
        specialty = diagnosis.get("specialty", "")
        level = risk.get("level", "info")
        eta = risk.get("eta_hours", "—")
        prob = risk.get("probability_percent", "—")
        brand = vehicle.get("brand", "")
        model_name = vehicle.get("model", "")

        # Build the structured explanation (offline template).
        consult_tag = f"（{specialty}专家会诊）" if specialty else ""
        parts = [
            f"【{tone['safety_prefix']} · {'紧急' if level == 'urgent' else '警告' if level == 'warning' else '提示'}】",
            f"您的 {brand} {model_name} 检测到：{root_cause}{consult_tag}。",
        ]

        if description:
            parts.append(description)

        parts.append(
            f"风险评估：等级 {level}，发生概率约 {prob}%，"
            f"预计剩余安全时间约 {eta} 小时（侧重{tone['focus']}）。"
        )

        # Add profile-specific guidance.
        if style == "eco":
            parts.append("作为节能型驾驶者，建议关注能耗异常是否影响续航，优先排查散热与功耗。")
        elif style == "aggressive":
            parts.append("鉴于您的驾驶风格偏激烈，制动与轮胎负荷较高，请特别注意安全风险，避免高速行驶。")
        else:
            parts.append("建议综合评估，关注高优先级风险项。")

        # Add long-trip specific guidance.
        trip_context = state.get("trip_context", {})
        if trip_context.get("is_long_trip"):
            distance = trip_context.get("distance_km", 500)
            parts.append(
                f"\n【长途出行专项评估】本次计划行驶 {distance}km。"
                f"当前电池温控异常在高速连续行驶中可能恶化，"
                f"建议出行前完成检测，途中每200km补电并监控电池温度。"
                f"完整出行健康报告已生成，请查看下方报告卡片。"
            )

        # Try LLM for a more natural version.
        if self._llm is not None:
            llm_text = self._llm_explain("\n".join(parts), state)
            if llm_text:
                return llm_text

        return "\n".join(parts)

    # ------------------------------------------------------------------
    def _llm_explain(self, structured: str, state: AgentState) -> str:
        """Use LLM to produce a more natural, profile-adapted explanation."""
        try:
            profile = state.get("driver_profile", {})
            prompt = (
                "你是 CarSoul Guardian 守护引擎的解释生成模块。"
                "将以下结构化诊断信息转化为车主易懂的自然语言提醒。\n"
                "要求：先结论后依据再行动建议；中文专业易懂；标注严重程度；不编造数据。\n"
                f"驾驶者画像风格：{profile.get('driving_style', 'balanced')}\n\n"
                f"结构化信息：\n{structured}"
            )
            resp = self._llm.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM explanation skipped: %s", exc)
            return ""
