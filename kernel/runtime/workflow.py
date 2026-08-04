"""Workflow execution for the Runtime SDK.

The :func:`execute_workflow` function is the execution entry point.
It takes an :class:`AgentWrapper` and a vehicle frame, then runs a
lightweight perception → diagnosis → risk → answer pipeline that:

1. Analyses the vehicle frame using digital twin components
2. Detects anomalies from component health
3. Runs matching skills for diagnosis
4. Records memories for significant events
5. Retrieves memory summary for historical context
6. Produces a natural-language answer

The workflow is designed to work in **standalone mode** (no LLM, no
backend) by default, using the digital twin and rule-based analysis.
When the full agent layer is available, it can delegate to the
existing CoreWorkflow for richer analysis.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from kernel.memory_engine import Source
from kernel.runtime.agent import AgentWrapper
from kernel.runtime.skill import SkillFinding


# ------------------------------------------------------------------ #
#  Result types
# ------------------------------------------------------------------ #
@dataclass
class WorkflowResult:
    """Structured result of a workflow execution.

    Attributes
    ----------
    answer : str
        The natural-language answer for the user.
    agent_name : str
        Which agent produced this result.
    soul_score : float
        The vehicle's soul-score (0-100).
    grade : str
        Score grade: "legendary" / "excellent" / "normal" / "risk".
    anomalies : list[dict]
        Detected anomalies from the digital twin.
    skill_findings : list[dict]
        Findings from executed skills.
    memory_count : int
        Number of memories recorded during this workflow.
    memory_summary : str
        Token-budgeted memory summary for context.
    trace : list[dict]
        Execution trace (for debugging / closed-loop display).
    governance_violations : list[str]
        Tool calls blocked by governance (for audit).
    vehicle_id : str
        The vehicle this workflow ran for.
    """

    answer: str = ""
    agent_name: str = ""
    soul_score: float = 100.0
    grade: str = "normal"
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    skill_findings: list[dict[str, Any]] = field(default_factory=list)
    memory_count: int = 0
    memory_summary: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    governance_violations: list[str] = field(default_factory=list)
    vehicle_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "agent_name": self.agent_name,
            "soul_score": self.soul_score,
            "grade": self.grade,
            "anomalies": self.anomalies,
            "skill_findings": self.skill_findings,
            "memory_count": self.memory_count,
            "memory_summary": self.memory_summary,
            "trace": self.trace,
            "governance_violations": self.governance_violations,
            "vehicle_id": self.vehicle_id,
        }


# ------------------------------------------------------------------ #
#  Anomaly detection from digital twin
# ------------------------------------------------------------------ #
def _detect_anomalies(twin: Any) -> list[dict[str, Any]]:
    """Extract anomalies from a VehicleTwin's health results.

    Returns a list of anomaly dicts, each with:
    - ``component``: battery / motor / chassis
    - ``topic``: impact topic (e.g. battery_stress, temperature_anomaly)
    - ``severity``: warning / critical
    - ``detail``: human-readable description
    """
    anomalies: list[dict[str, Any]] = []
    score_result = twin.soul_score()

    for deduction in score_result.deductions:
        component = deduction.component
        metric = deduction.metric
        severity = "warning"
        if deduction.points >= 10:
            severity = "critical"

        # Map component+metric to impact topics.
        topic = _metric_to_topic(component, metric)

        anomalies.append({
            "component": component,
            "category": component,  # alias for ExpertSkillAdapter.match()
            "metric": metric,
            "value": deduction.value,
            "threshold": deduction.threshold,
            "points": deduction.points,
            "severity": severity,
            "topic": topic,
            "detail": deduction.reason,
        })

    # Also check component states for transitions.
    for transition in score_result.transitions:
        if transition.to_state in ("warning", "critical"):
            anomalies.append({
                "component": transition.component,
                "category": transition.component,  # alias for skill matching
                "metric": "state",
                "value": transition.to_state,
                "threshold": "normal",
                "points": 0,
                "severity": transition.to_state,
                "topic": f"{transition.component}_state",
                "detail": transition.reason,
            })

    return anomalies


def _metric_to_topic(component: str, metric: str) -> str:
    """Map a component+metric to a memory impact topic."""
    mapping = {
        "battery": {
            "soh": "battery_health",
            "temperature": "temperature_anomaly",
            "cell_imbalance": "battery_stress",
            "charge_cycles": "battery_health",
        },
        "motor": {
            "temperature": "motor_wear",
            "vibration": "motor_wear",
            "efficiency": "motor_wear",
        },
        "chassis": {
            "tire_pressure": "tire_safety",
            "brake_pad_wear": "brake_safety",
            "suspension": "suspension_comfort",
        },
    }
    return mapping.get(component, {}).get(metric, f"{component}_{metric}")


# ------------------------------------------------------------------ #
#  Answer generation
# ------------------------------------------------------------------ #
_GRADE_LABELS = {
    "legendary": "传奇状态",
    "excellent": "优秀状态",
    "normal": "正常状态",
    "risk": "风险状态",
}


def _generate_answer(
    agent_name: str,
    soul_score: float,
    grade: str,
    anomalies: list[dict[str, Any]],
    skill_findings: list[SkillFinding],
    memory_summary: str,
    user_query: str,
) -> str:
    """Generate a natural-language answer from the workflow results.

    This is a rule-based generator that works without an LLM.  When
    an LLM is available, the agent layer can override this with a
    richer response.
    """
    parts: list[str] = []
    grade_label = _GRADE_LABELS.get(grade, grade)

    # Opening with soul score.
    parts.append(
        f"【{agent_name} 会诊报告】车辆灵魂指数 {soul_score:.1f}（{grade_label}）。"
    )

    # Anomaly summary.
    if anomalies:
        critical = [a for a in anomalies if a["severity"] == "critical"]
        warnings = [a for a in anomalies if a["severity"] == "warning"]
        if critical:
            parts.append(f"发现 {len(critical)} 项严重异常：")
            for a in critical[:3]:
                parts.append(f"  · {a['component']} - {a['detail']}")
        if warnings:
            parts.append(f"发现 {len(warnings)} 项预警：")
            for a in warnings[:3]:
                parts.append(f"  · {a['component']} - {a['detail']}")
    else:
        parts.append("各系统状态正常，未检测到异常。")

    # Skill findings.
    for finding in skill_findings:
        if finding.recommendation:
            parts.append(f"【{finding.specialty}专家】{finding.recommendation}")

    # Memory context.
    if memory_summary and "暂无" not in memory_summary:
        # Extract key lines from the summary.
        for line in memory_summary.split("\n"):
            line = line.strip()
            if line.startswith("【") and ("关联" in line or "趋势" in line):
                parts.append(line)
                break

    # User query response.
    if user_query:
        parts.append(f"\n针对您的问题「{user_query}」：")
        if skill_findings:
            top_finding = skill_findings[0]
            parts.append(f"  {top_finding.recommendation or '建议进一步检查。'}")
        elif anomalies:
            parts.append("  建议根据上述异常项进行针对性检查。")
        else:
            parts.append("  当前各项指标正常，请继续保持良好的用车习惯。")

    return "\n".join(parts)


# ------------------------------------------------------------------ #
#  Skill execution helper (backward compatible)
# ------------------------------------------------------------------ #
def _run_skill(
    skill: Any,
    state: dict[str, Any],
    tools: Any,
    memory: Any,
) -> SkillFinding:
    """Execute a skill's ``run`` method with backward-compatible dispatch.

    Skills written before the ``knowledge`` parameter was added to the
    Skill protocol define ``run(self, state, tools, memory)`` without
    ``knowledge``.  This helper inspects the signature and calls the
    method with or without ``knowledge`` accordingly, ensuring full
    backward compatibility.
    """
    sig = inspect.signature(skill.run)
    params = sig.parameters
    # Check if the method explicitly accepts 'knowledge' or has **kwargs.
    has_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if "knowledge" in params or has_kwargs:
        return skill.run(state, tools, memory, knowledge=None)
    return skill.run(state, tools, memory)


# ------------------------------------------------------------------ #
#  Public API: execute_workflow
# ------------------------------------------------------------------ #
def execute_workflow(
    agent: AgentWrapper,
    vehicle_frame: Any,
    user_query: str = "",
) -> WorkflowResult:
    """Execute a diagnostic workflow for a vehicle.

    This is the SDK's execution entry point.  It analyses the vehicle
    frame, runs matching skills, records memories, and produces a
    structured result with a natural-language answer.

    Parameters
    ----------
    agent : AgentWrapper
        The agent to execute with (created via :func:`create_agent`).
    vehicle_frame : TelemetryFrame or list[TelemetryFrame]
        The vehicle telemetry to analyse.  Can be a single frame or a
        list of frames (the full simulator lifecycle).
    user_query : str
        The user's question (e.g. "电池最近怎么样").

    Returns
    -------
    WorkflowResult
        Structured result with answer, anomalies, findings, and trace.

    Example
    -------
    ::

        from kernel.runtime import create_agent, execute_workflow

        agent = create_agent("my_guardian", memory="sqlite:///carsoul.db")
        result = execute_workflow(agent, vehicle_frame, "电池最近怎么样")
        print(result.answer)
    """
    trace: list[dict[str, Any]] = []
    violations: list[str] = []

    def _trace(step: str, detail: str = "", data: dict | None = None) -> None:
        trace.append({
            "step": step,
            "agent": agent.name,
            "detail": detail,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    _trace("start", f"工作流启动，用户查询：{user_query or '(无)'}")

    # ---- Phase 1: Ingest vehicle frame into digital twin ----
    frames = vehicle_frame if isinstance(vehicle_frame, list) else [vehicle_frame]
    vehicle_id = frames[0].vin if frames else "UNKNOWN"

    try:
        from digital_twin.component_model import create_vehicle_twin_from_simulator
        twin = create_vehicle_twin_from_simulator(frames)
    except Exception as e:
        _trace("error", f"数字孪生初始化失败: {e}")
        return WorkflowResult(
            answer=f"无法分析车辆数据：{e}",
            agent_name=agent.name,
            vehicle_id=vehicle_id,
            trace=trace,
            governance_violations=violations,
        )

    _trace("perceive", f"摄入 {len(frames)} 帧遥测数据，VIN={vehicle_id}")

    # ---- Phase 2: Detect anomalies ----
    anomalies = _detect_anomalies(twin)
    anomaly_topics = list({a["topic"] for a in anomalies})

    _trace("diagnose", f"检测到 {len(anomalies)} 项异常", {
        "anomalies": len(anomalies),
        "topics": anomaly_topics,
    })

    # ---- Phase 3: Record memories for anomalies ----
    memory_before = agent.memory_engine.count(vehicle_id)
    for anomaly in anomalies:
        agent.remember(
            vehicle_id=vehicle_id,
            event_type=f"{anomaly['component']}_{anomaly['metric']}_anomaly",
            payload={
                "value": anomaly["value"],
                "threshold": anomaly["threshold"],
                "severity": anomaly["severity"],
                "detail": anomaly["detail"],
            },
            impact_target=anomaly["topic"],
            impact_delta=anomaly["points"] / 100.0,
            confidence=0.85 if anomaly["severity"] == "critical" else 0.7,
            source=Source.AGENT,
        )
    memory_recorded = agent.memory_engine.count(vehicle_id) - memory_before

    if memory_recorded > 0:
        _trace("memory", f"记录 {memory_recorded} 条记忆", {
            "topics": anomaly_topics,
        })

    # ---- Phase 4: Run matching skills ----
    state = {
        "anomalies": anomalies,
        "anomaly_topics": anomaly_topics,
        "vehicle_frame": frames[-1] if frames else None,
        "vehicle_id": vehicle_id,
        "user_query": user_query,
        "twin": twin,
    }

    skill_findings: list[SkillFinding] = []
    matched_skills = agent.match_skills(state)
    _trace("skill_match", f"匹配到 {len(matched_skills)} 个技能", {
        "skills": [s.name for s in matched_skills],
    })

    for skill in matched_skills:
        try:
            finding = _run_skill(skill, state, agent, agent.memory_engine)
            skill_findings.append(finding)
            _trace("skill_run", f"技能 {skill.name} 执行完成", finding.to_dict())
        except Exception as e:
            _trace("skill_error", f"技能 {skill.name} 执行失败: {e}")

    # ---- Phase 5: Governance audit ----
    # Verify that the agent's governance profile blocks write tools
    # in read-only mode (acceptance: 治理约束经 SDK 默认生效).
    from kernel.runtime.governance import WRITE_TOOLS
    for tool_name in WRITE_TOOLS:
        allowed, reason = agent.validate_tool(tool_name)
        if not allowed:
            violations.append(f"已拦截 {tool_name}: {reason}")

    if violations:
        _trace("governance", f"治理拦截 {len(violations)} 项写操作")

    # ---- Phase 6: Retrieve memory summary ----
    memory_summary_obj = agent.memory_summary(vehicle_id)
    memory_summary_text = memory_summary_obj.text

    _trace("memory_recall", f"召回记忆摘要（{memory_summary_obj.memory_count} 条）")

    # ---- Phase 7: Generate answer ----
    soul_score = twin.soul_score()
    answer = _generate_answer(
        agent_name=agent.name,
        soul_score=soul_score.score,
        grade=soul_score.grade,
        anomalies=anomalies,
        skill_findings=skill_findings,
        memory_summary=memory_summary_text,
        user_query=user_query,
    )

    _trace("answer", "生成会诊报告", {"answer_length": len(answer)})

    _trace("complete", "工作流完成")

    return WorkflowResult(
        answer=answer,
        agent_name=agent.name,
        soul_score=soul_score.score,
        grade=soul_score.grade,
        anomalies=anomalies,
        skill_findings=[f.to_dict() for f in skill_findings],
        memory_count=memory_summary_obj.memory_count,
        memory_summary=memory_summary_text,
        trace=trace,
        governance_violations=violations,
        vehicle_id=vehicle_id,
    )
