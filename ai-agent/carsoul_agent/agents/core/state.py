"""Shared state for the CarSoul Core Agent workflow.

Implements the ``AgentState`` TypedDict from the technical design
(``agents/core/state.py``). Every field is the output of one pipeline
stage; the full dict flows between the five sub-agent nodes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state that flows through the five-sub-agent graph.

    Fields mirror the technical-design spec. ``total=False`` lets nodes
    populate only the keys they produce.
    """

    # ---- inputs ----
    vehicle_state: dict          # 当前车辆数字孪生快照
    driver_profile: dict         # 驾驶者画像 (Driver Twin)
    sensor_window: list[dict]    # 最近 N 个传感器读数
    user_message: str            # 触发本次守护的用户消息（可为空=主动巡检）
    knowledge_context: str       # RAG 检索到的相关知识上下文
    trip_context: dict           # 长途出行场景上下文（距离、天数等）
    knowledge_retrieval: dict     # RAG 检索详情（来源、片段、分数）用于闭环可视化
    calibration_context: dict    # 自纠错校准上下文（历史反馈：误报/确认记录+准确率）

    # ---- perception output ----
    anomalies: list[dict]        # 感知 Agent 检出的异常
    is_normal: bool              # 是否走正常报告分支

    # ---- expert panel output (多智能体专家会诊) ----
    expert_opinions: list[dict]  # 各专科专家的会诊意见

    # ---- diagnosis output ----
    diagnosis: dict              # 诊断 Agent 汇总会诊后的根因结论

    # ---- risk output ----
    risk_assessment: dict        # 风险 Agent 的量化等级

    # ---- explainer output ----
    explanation: str             # 解释 Agent 的用户语言
    trip_report: dict            # 结构化出行健康报告（长途场景专用）

    # ---- service output ----
    service_suggestion: dict     # 服务 Agent 的建议与提醒

    # ---- cross-cutting ----
    trace_log: list[dict]        # 全程执行轨迹


# ------------------------------------------------------------------ #
#  Trace helpers
# ------------------------------------------------------------------ #
def trace_entry(
    step: str,
    agent: str,
    detail: str = "",
    data: dict | None = None,
) -> dict[str, Any]:
    """Build a single immutable trace record.

    Each sub-agent appends one of these to ``state["trace_log"]`` so the
    entire reasoning chain is replayable — a key
    criterion ("推理可追溯").
    """
    return {
        "step": step,
        "agent": agent,
        "detail": detail,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class Trace:
    """Convenience namespace for the canonical GOAI step names.

    These map to the ``step=`` markers in the closed-loop table of the
    technical design, ensuring trace logs use a consistent vocabulary.
    """

    PERCEIVE = "perceive"
    UNDERSTAND = "understand"
    REASON = "reason"
    TOOL = "tool"
    ACT = "act"
    NORMAL = "normal_report"

    ALL = (PERCEIVE, UNDERSTAND, REASON, TOOL, ACT, NORMAL)
