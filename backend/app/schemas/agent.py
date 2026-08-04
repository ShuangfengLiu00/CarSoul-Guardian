"""Agent chat schemas."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    user: str = Field(..., description="用户标识/用户名")
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: str | None = Field(None, description="可选会话 ID，用于多轮记忆")


class AgentChatResponse(BaseModel):
    answer: str
    agent_status: str = "active"
    session_id: str | None = None
    agent_name: str = "CarSoul Guardian Agent"
    closed_loop: dict[str, Any] | None = Field(
        None,
        description="守护闭环摘要：steps(感知→诊断→风险→建议→执行)、anomalies、diagnosis、risk、actions、reminder",
    )
