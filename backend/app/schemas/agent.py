"""Agent chat schemas."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    user: str = Field(..., description="用户标识/用户名")
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: str | None = Field(None, description="可选会话 ID，用于多轮记忆")


class AgentChatResponse(BaseModel):
    """Agent 对话响应。

    诚实降级原则（本次 P0 整改核心）：所有可用性字段的默认值一律取
    "不可用 / 未使用" 这一侧。**未证明可用即视为不可用** —— 上游不显式
    表态就不许自动变绿。``agent_status`` 刻意不设默认值，强制上游表态。
    """

    answer: str
    # 无默认值：必填。历史上这里是 `= "active"`，导致任何未表态的响应
    # 都被 pydantic 自动洗成"运行中"。
    agent_status: str
    session_id: str | None = None
    agent_name: str = "CarSoul Guardian Agent"
    closed_loop: dict[str, Any] | None = Field(
        None,
        description="守护闭环摘要：steps(感知→诊断→风险→建议→执行)、anomalies、diagnosis、risk、actions、reminder",
    )

    # ---- 大模型链路真实性字段（透传自 carModel /agent/chat）----
    llm_available: bool = Field(
        False, description="本轮 LLM 链路是否真的可用（不是'环境变量配没配'）"
    )
    llm_used: bool = Field(
        False, description="本轮是否真的调用了 LLM。与 llm_available 正交，不可合并"
    )
    degraded: dict[str, Any] | None = Field(
        None,
        description=(
            "降级详情。非空 ⟺ llm_available=false（链路层事实）。"
            "含 reason（llm_endpoint_not_configured / llm_call_failed / "
            "carmodel_agent_chat_unreachable / no_llm_backend_configured）、detail、impact，"
            "以及 **affects_this_turn**（布尔，回答层事实：本轮回答是否真的因链路不可用而受损）。"
            "\n\n消费方注意：判断'本轮是否降级'必须用 degraded.affects_this_turn === true，"
            "**不能**用'degraded 非空'。合规拒答 / OOD 声明 / 信息不足反问是确定性路径，"
            "本就不经大模型，链路挂了它们的输出也不变，affects_this_turn=false；"
            "把这类回答标成'降级模式'是另一种失真。"
        ),
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list, description="RAG 检索引用，降级时可能为空"
    )
    compliance_refused: bool = Field(
        False,
        description="是否被合规闸门**拒答**。注意 safety_critical 类不拒答，此值为 false，"
                    "不能用它判断'闸门是否介入过'。",
    )
    compliance_category: str | None = Field(
        None,
        description="合规闸门命中类别：geo / identity / data_fraud / repair_mislead / "
                    "safety_critical。**非空即代表闸门介入过**，这才是判断闸门是否生效的唯一判据。",
    )
    compliance_action: str | None = Field(
        None,
        description="闸门处置动作：refuse=直接拒答；safety_disclaim=免责并导向专业检修"
                    "（**不是**拒答，compliance_refused 为 false）；None=未命中闸门。",
    )
    safety_scrubbed: bool = Field(
        False,
        description="答案中是否检出并移除了无工具证据的安全结论（安全时限/磨损到极限/立即停驶）。"
                    "false 仅表示未命中这三类模式，**不等于**答案已被证明安全。",
    )
    safety_scrub_hits: list[Any] = Field(
        default_factory=list, description="被移除的编造安全结论片段，便于溯源与复盘"
    )
    model_version: str | None = Field(None, description="carModel 模型版本指纹")
    engine: str = Field(
        "unknown",
        description="实际应答引擎：carmodel_agent_chat / local_agent / offline_fallback",
    )
