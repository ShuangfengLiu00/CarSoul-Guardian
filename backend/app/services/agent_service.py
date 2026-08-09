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


def affects_this_turn(degraded: Any) -> bool:
    """本轮回答是否**真的**因大模型链路不可用而受损。

    判据只认 ``degraded["affects_this_turn"] is True``，**不是** "degraded 非空"。
    这两者是 carModel 明确定义的两个正交事实（carModel api/main.py:499-520）：

      · ``degraded`` 非空  ⟺ ``llm_available is False``  —— 链路层事实
      · ``affects_this_turn`` ⟺ 本轮回答质量真的退化了    —— 回答层事实

    合规拒答 / OOD 声明 / 信息不足反问属于确定性路径，本就不经大模型，
    链路挂了也不改变它们的输出，所以 ``affects_this_turn=false``。
    用"degraded 非空"判降级会把一次**正常的合规拒答**显示成"降级模式" ——
    那是凭空制造一个不存在的缺陷，与硬编码 active 同属失真，方向相反而已。
    """
    return isinstance(degraded, dict) and degraded.get("affects_this_turn") is True


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
    "affects_last_turn": False,
    "observed_at": None,
}


def _record_link_state(payload: dict) -> dict:
    """每轮对话后记录真实链路状态，供 /api/health/overview 如实上报。

    口径（两个正交事实分开记，不许互相掩盖）：

      · ``agent_status`` 仍由 ``llm_available and llm_used`` 推导。
        因此**确定性路径的轮次照样计入"链路不可用"的观测** —— 合规拒答那一轮
        链路是真的挂着的，Dashboard 必须如实反映，不能因为"这轮回答没受影响"
        就把链路洗成在线。
      · ``affects_last_turn`` 单独记"最近一轮的回答质量是否真的受损"。
        Dashboard 用它决定措辞是"降级运行"还是"链路不可用但本轮未受影响"，
        避免把一次正常的合规拒答说成回答质量下降。
    """
    from datetime import datetime, timezone

    _last_link_state.update(
        {
            "agent_status": payload.get("agent_status", "unknown"),
            "llm_available": bool(payload.get("llm_available", False)),
            "llm_used": bool(payload.get("llm_used", False)),
            "engine": payload.get("engine", "unknown"),
            "degraded": payload.get("degraded"),
            "affects_last_turn": affects_this_turn(payload.get("degraded")),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return payload


def get_last_link_state() -> dict[str, Any]:
    """返回最近一次真实观测到的链路状态（未观测过则为 unknown）。"""
    return dict(_last_link_state)


def _from_carmodel(result: dict, session_id: str | None) -> dict:
    """Map carModel /agent/chat 的响应到 Guardian 响应契约。

    上游契约（carModel api/main.py:446-464 的出口不变式，有服务端自检兜底）：
    ``llm_available is False`` ⟹ ``degraded`` 必非空、带 ``reason``、带布尔
    ``affects_this_turn``。因此 Guardian **不再**替上游补
    ``llm_unavailable_upstream_unspecified`` —— 那层兜底是上游把"链路不可用"
    这个事实吞掉时的应急补丁，上游修好了就该撤，留着只会掩盖新的上游回归。
    """
    llm_available = bool(result.get("llm_available", False))
    llm_used = bool(result.get("llm_used", False))

    degraded = result.get("degraded")
    if isinstance(degraded, dict) and not isinstance(degraded.get("affects_this_turn"), bool):
        # 只有对面是**旧版 carModel**（或契约被改坏）才会走到这里。
        # 取"本轮受损"这一侧：没证明本轮没受影响，就不许当作没受影响 ——
        # 这是"未证明可用即视为不可用"落在本字段上的形态，不是替上游编理由。
        logger.warning(
            "carModel degraded 缺少 affects_this_turn（疑似旧版上游），按本轮受损保守处理: %s",
            degraded.get("reason"),
        )
        detail = str(degraded.get("detail") or "").strip()
        degraded = {
            **degraded,
            "affects_this_turn": True,
            "detail": (
                f"{detail}（注：上游未给出 affects_this_turn，"
                "Guardian 按'本轮受损'保守处理）"
            ).strip(),
        }
    elif degraded is None and not llm_available:
        # 上游违约。**不编造** degraded —— 理由是上游才知道的事，Guardian 编一个
        # 只是把违约藏起来。但事实不会丢：agent_status 由 llm_available/llm_used
        # 推导，此处必为 degraded，UI 与 Dashboard 照样不会变绿。
        logger.error(
            "carModel 违反降级契约：llm_available=false 但 degraded=null（上游版本过旧？）"
        )

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
        # 闸门处置动作：refuse / safety_disclaim / None。
        # safety_critical 类走 safety_disclaim（免责 + 导向专业检修），它的
        # compliance_refused 是 **False** —— 判断"闸门是否介入过"只能看
        # compliance_category 非空，只看 refused 会漏掉一整类。
        "compliance_action": result.get("compliance_action"),
        # 编造安全数值红线的后置清洗结果。false 只表示"未命中这三类模式"，
        # 不等于"答案已被证明安全"，不要当成安全背书往上加戏。
        "safety_scrubbed": bool(result.get("safety_scrubbed", False)),
        "safety_scrub_hits": result.get("safety_scrub_hits") or [],
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
                    "impact": "回答由本地规则生成，未经大模型转述，覆盖面与表达质量均低于正常链路。",
                    # 与 carModel 同一口径：这条路径本该由大模型转述却没转述，
                    # 本轮回答**确实**受损，所以是 True（合规拒答那种确定性
                    # 路径才是 False）。答案里也已加了可见的降级前缀。
                    "affects_this_turn": True,
                },
                "citations": result.get("citations") or [],
                "compliance_refused": bool(result.get("compliance_refused", False)),
                "compliance_category": result.get("compliance_category"),
                "compliance_action": result.get("compliance_action"),
                # 本地规则专家团没有 carModel 那套安全数值后置清洗，
                # 如实报 false / 空表，不假装做过这道工序。
                "safety_scrubbed": False,
                "safety_scrub_hits": [],
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
            "impact": "回答为固定模板，既无大模型转述也无真实车况推理，仅作占位。",
            # 离线兜底一定是真降级。
            "affects_this_turn": True,
        },
        "citations": [],
        "compliance_refused": False,
        "compliance_category": None,
        "compliance_action": None,
        "safety_scrubbed": False,
        "safety_scrub_hits": [],
        "model_version": None,
        "engine": "offline_fallback",
    }
