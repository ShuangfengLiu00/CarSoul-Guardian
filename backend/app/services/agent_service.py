"""Agent service.

Adapter between the Guardian API layer and the actual answering engines.

Priority order (P0 整改后)::

    1. carModel ``POST /agent/chat``  -> engine="carmodel_agent_chat"
       唯一带 RAG 检索、强制引用、合规闸门、诚实降级纪律的大模型入口。
    2. 本地 ``carsoul_agent`` 规则专家团 -> engine="local_agent"
       仅在 carModel 不可达时启用。它**不是大模型**，因此除非它自己能
       证明调了 LLM，一律强制 llm_available=False / llm_used=False。
    3. ``_fallback_respond`` 离线兜底  -> engine="offline_fallback"

诚实降级原则：**未证明可用即视为不可用**。任何一层都不许把"我没调大模型"
这件事洗成 ``agent_status="active"``。
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.services import carsoul_world

logger = logging.getLogger(__name__)

# Lazily import the agent so a missing optional dependency never breaks boot.
_Agent = None
_agent_instance = None


def _load_agent():
    global _Agent, _agent_instance
    if _agent_instance is not None:
        return _agent_instance
    try:
        from carsoul_agent.agents.carsoul_agent import CarSoulGuardianAgent

        _Agent = CarSoulGuardianAgent
        _agent_instance = _Agent(model_name=settings.MODEL_NAME)
        logger.info("CarSoul Guardian Agent loaded from carsoul_agent package.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("carsoul_agent unavailable, using fallback responder: %s", exc)
        _Agent = None
        _agent_instance = None
    return _agent_instance


def _derive_status(llm_available: bool, llm_used: bool) -> str:
    """只有'链路可用且本轮真的调了'才算 active，其余一律 degraded。"""
    return "active" if (llm_available and llm_used) else "degraded"


# ---- 最近一次真实观测到的大模型链路状态 ----
# Dashboard 的"AI 守护状态"必须反映**真实观测**，而不是硬编码常量。
# 在任何一轮对话真正发生之前，状态是 "unknown" —— 未观测即不表态，
# 绝不预设为 active。
_last_link_state: dict[str, Any] = {
    "agent_status": "unknown",
    "llm_available": False,
    "llm_used": False,
    "engine": "unknown",
    "degraded": None,
    "observed_at": None,
}


def _record_link_state(payload: dict) -> dict:
    """每轮对话后记录真实链路状态，供 /api/health/overview 如实上报。"""
    from datetime import datetime, timezone

    _last_link_state.update(
        {
            "agent_status": payload.get("agent_status", "unknown"),
            "llm_available": bool(payload.get("llm_available", False)),
            "llm_used": bool(payload.get("llm_used", False)),
            "engine": payload.get("engine", "unknown"),
            "degraded": payload.get("degraded"),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return payload


def get_last_link_state() -> dict[str, Any]:
    """返回最近一次真实观测到的链路状态（未观测过则为 unknown）。"""
    return dict(_last_link_state)


def _from_carmodel(result: dict, session_id: str | None) -> dict:
    """Map carModel /agent/chat 的 20 字段响应到 Guardian 响应契约。"""
    llm_available = bool(result.get("llm_available", False))
    llm_used = bool(result.get("llm_used", False))

    degraded = result.get("degraded")
    # carModel 有时在 llm_available=false 时仍返回 degraded=null（compose 规则
    # 路由成功应答的场景）。此处不替上游"补一个好看的理由"，但也不允许降级
    # 事实凭空消失：显式标注理由未知，由 UI 如实呈现。
    if not llm_available and not isinstance(degraded, dict):
        degraded = {
            "reason": "llm_unavailable_upstream_unspecified",
            "detail": "carModel 报告 llm_available=false 但未提供 degraded.reason",
        }

    return {
        "answer": str(result.get("answer", "")).strip(),
        "agent_status": _derive_status(llm_available, llm_used),
        "session_id": result.get("session_id") or session_id,
        "agent_name": "CarSoul World Model Agent",
        "closed_loop": result.get("closed_loop"),
        "llm_available": llm_available,
        "llm_used": llm_used,
        "degraded": degraded,
        "citations": result.get("citations") or [],
        "compliance_refused": bool(result.get("compliance_refused", False)),
        "compliance_category": result.get("compliance_category"),
        "model_version": result.get("model_version"),
        "engine": "carmodel_agent_chat",
    }


async def chat(
    user: str,
    message: str,
    session_id: str | None = None,
    *,
    role: str = "owner",
    vehicle_id: str | None = None,
) -> dict[str, Any]:
    """Answer a user message, preferring the real LLM link over local rules.

    Returns a dict matching AgentChatResponse.
    """
    # ---- 第一优先：carModel /agent/chat（唯一真实大模型链路）----
    try:
        cm = await carsoul_world.agent_chat(
            query=message, role=role, vehicle_id=vehicle_id, session_id=session_id
        )
        if isinstance(cm, dict) and "error" not in cm:
            return _record_link_state(_from_carmodel(cm, session_id))
        logger.warning(
            "carModel /agent/chat unavailable (%s), falling back to local agent: %s",
            (cm or {}).get("error"),
            (cm or {}).get("detail", "")[:200],
        )
        upstream_err = (cm or {}).get("error", "world_model_unavailable")
    except Exception as exc:  # noqa: BLE001
        logger.exception("carModel /agent/chat call raised: %s", exc)
        upstream_err = "world_model_call_exception"

    # ---- 第二优先：本地 carsoul_agent 规则专家团（不是大模型）----
    agent = _load_agent()
    if agent is not None:
        try:
            result = agent.handle(message=message, user=user, session_id=session_id)
            # 本地规则团默认没有 LLM。只有它自己显式证明调了 LLM 才认。
            llm_available = bool(result.get("llm_available", False))
            llm_used = bool(result.get("llm_used", False))
            answer = str(result.get("answer", "")).strip()
            # 降级纪律：与 carModel 对齐，未经大模型转述的回答必须自带可见前缀。
            if not (llm_available and llm_used):
                answer = f"[降级模式·未经大模型转述] {answer}"
            return _record_link_state({
                "answer": answer,
                # 刻意**不读** result["agent_status"]：carsoul_agent 包内
                # (agents/carsoul_agent.py L195) 硬编码 "active"，那是第七层
                # 洗白点。本地规则专家团不是大模型，状态只能由真实的
                # llm_available/llm_used 推导，不接受内层自述。
                "agent_status": _derive_status(llm_available, llm_used),
                "session_id": result.get("session_id", session_id),
                "agent_name": getattr(agent, "name", "CarSoul Guardian Agent"),
                "closed_loop": result.get("closed_loop"),
                "llm_available": llm_available,
                "llm_used": llm_used,
                "degraded": {
                    "reason": "carmodel_agent_chat_unreachable",
                    "detail": f"上游 {upstream_err}，已降级到本地规则专家团（无大模型转述）",
                },
                "citations": result.get("citations") or [],
                "compliance_refused": bool(result.get("compliance_refused", False)),
                "compliance_category": result.get("compliance_category"),
                "model_version": result.get("model_version"),
                "engine": "local_agent",
            })
        except Exception as exc:  # noqa: BLE001
            logger.exception("Local agent execution failed: %s", exc)

    # ---- 兜底：离线规则应答 ----
    return _record_link_state(_fallback_respond(user, message, session_id, upstream_err))


def _fallback_respond(
    user: str,
    message: str,
    session_id: str | None,
    upstream_err: str = "no_llm_backend_configured",
) -> dict:
    """Deterministic local response used when no LLM backend is reachable."""
    msg = (message or "").strip().lower()
    if any(k in msg for k in ["保养", "maintenance", "换油", "机油"]):
        answer = (
            f"【CarSoul 守护建议】{user}，根据当前里程与时间模型，建议关注机油与滤芯更换。"
            "具体保养项以车辆档案中的保养周期为准。"
            "（提示：以上为辅助参考，请以专业检修机构诊断为准。）"
        )
    elif any(k in msg for k in ["故障", "报警", "灯亮", "fault", "warning"]):
        answer = (
            f"【CarSoul 守护建议】{user}，已记录异常描述。建议尽快连接 OBD 读取故障码，"
            "并将描述细化（何时出现、伴随现象）。严重情况请优先联系专业检修或道路救援。"
            "（提示：以上为辅助参考，请以专业检修机构诊断为准。）"
        )
    elif any(k in msg for k in ["你好", "hello", "hi", "在吗"]):
        answer = (
            f"你好 {user}，我是 CarSoul Guardian 守护引擎。可向我询问保养、故障、"
            "用车行为等问题，我会基于车辆数字生命档案给出守护建议。"
        )
    else:
        answer = (
            f"【CarSoul 守护引擎】{user}，已收到你的问题：「{message}」。"
            "当前为离线应急模式，连接 LLM 后将提供完整分析。"
        )
    # 与 carModel 的降级纪律保持一致：降级回答必须自带可见前缀。
    answer = f"[降级模式·未经大模型转述] {answer}"
    return {
        "answer": answer,
        # 历史上这里硬编码 "active" —— 明明没有任何 LLM 却报"运行中"。
        "agent_status": "degraded",
        "session_id": session_id,
        "agent_name": "CarSoul Guardian Agent (offline)",
        "closed_loop": None,
        "llm_available": False,
        "llm_used": False,
        "degraded": {
            "reason": "no_llm_backend_configured",
            "detail": f"carModel 不可达（{upstream_err}）且本地规则专家团不可用，已使用离线兜底应答",
        },
        "citations": [],
        "compliance_refused": False,
        "compliance_category": None,
        "model_version": None,
        "engine": "offline_fallback",
    }
