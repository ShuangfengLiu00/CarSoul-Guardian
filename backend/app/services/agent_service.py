"""Agent service.

Thin adapter between the backend and the `carsoul_agent` package. This is
the ONLY place the API layer touches AI logic — keeping the architecture
modular and ready for multi-agent evolution (TASK008).

If the agent package is unavailable (e.g. partial install), we degrade
gracefully to a rule-based fallback so the API always returns something.
"""
from __future__ import annotations

import logging

from app.core.config import settings

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


def chat(user: str, message: str, session_id: str | None = None) -> dict:
    """Run the agent on a user message.

    Returns a dict matching AgentChatResponse: {answer, agent_status, ...}.
    """
    agent = _load_agent()
    if agent is not None:
        try:
            result = agent.handle(message=message, user=user, session_id=session_id)
            # Normalise the agent output into our response contract.
            return {
                "answer": str(result.get("answer", "")).strip(),
                "agent_status": result.get("agent_status", "active"),
                "session_id": result.get("session_id", session_id),
                "agent_name": getattr(agent, "name", "CarSoul Guardian Agent"),
                "closed_loop": result.get("closed_loop"),
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent execution failed: %s", exc)
            return {
                "answer": "守护引擎暂时离线，已切换到本地应急响应。请稍后重试。",
                "agent_status": "degraded",
                "session_id": session_id,
                "agent_name": "CarSoul Guardian Agent (fallback)",
            }

    # ---- Fallback rule-based responder (no LLM) ----
    return _fallback_respond(user, message, session_id)


def _fallback_respond(user: str, message: str, session_id: str | None) -> dict:
    """Deterministic local response used when no LLM backend is configured."""
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
    return {
        "answer": answer,
        "agent_status": "active",
        "session_id": session_id,
        "agent_name": "CarSoul Guardian Agent (offline)",
    }
