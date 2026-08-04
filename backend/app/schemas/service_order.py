"""Service order schemas — after-sales closed-loop (§3A.1)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.service_order import FEEDBACK_TYPES, STATUS_FLOW


class ServiceOrderBase(BaseModel):
    service_type: str = Field(..., description="服务类型")
    service_name: str = Field(..., max_length=128)
    priority: str = Field("medium", description="high | medium | low")
    reason: str = Field(..., description="创建工单的原因（通常来自 Agent 诊断）")
    description: str | None = None
    service_provider: str | None = None
    estimated_response: str | None = None
    diagnosis_summary: str | None = Field(
        None, description="触发此工单的 Agent 诊断摘要"
    )


class ServiceOrderCreate(ServiceOrderBase):
    pass


class ServiceOrderUpdate(BaseModel):
    """Advance the service order to the next status (or a specific status)."""
    status: str | None = Field(
        None, description="目标状态（留空则自动推进到下一阶段）"
    )
    note: str | None = Field(None, description="状态变更备注")
    service_provider: str | None = None
    estimated_response: str | None = None
    cost: float | None = Field(None, ge=0)


class ServiceOrderFeedback(BaseModel):
    """After-sales feedback collected from the vehicle owner."""
    feedback_type: str = Field(..., description=" | ".join(FEEDBACK_TYPES))
    feedback_note: str | None = None


class ServiceOrderOut(ServiceOrderBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    status: str
    booked_at: datetime | None = None
    in_service_at: datetime | None = None
    done_at: datetime | None = None
    closed_at: datetime | None = None
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    cost: float | None = None
    feedback_type: str | None = None
    feedback_note: str | None = None
    feedback_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ServiceOrderList(BaseModel):
    items: list[ServiceOrderOut]
    total: int = 0
