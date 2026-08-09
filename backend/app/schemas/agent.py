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
        None, description="降级详情，含 reason（如 llm_endpoint_not_configured / llm_call_failed）"
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list, description="RAG 检索引用，降级时可能为空"
    )
    compliance_refused: bool = Field(False, description="是否被合规闸门拒答")
    compliance_category: str | None = Field(None, description="合规拒答类别")
    model_version: str | None = Field(None, description="carModel 模型版本指纹")
    engine: str = Field(
        "unknown",
        description="实际应答引擎：carmodel_agent_chat / local_agent / offline_fallback",
    )
