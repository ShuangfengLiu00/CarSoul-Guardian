"""Alert schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlertBase(BaseModel):
    alert_type: str = Field(..., description="告警类型")
    level: str = Field(..., description="等级: info/warning/critical")
    category: str | None = None
    title: str = Field(..., max_length=128)
    detail: str | None = None
    recommendation: str | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: str | None = Field(None, description="active/acknowledged/resolved")


class AlertOut(AlertBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    status: str
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    triggered_at: datetime


class AlertList(BaseModel):
    items: list[AlertOut]
    total: int = 0
