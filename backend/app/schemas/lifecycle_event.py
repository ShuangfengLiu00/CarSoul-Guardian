"""Lifecycle event schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LifecycleEventBase(BaseModel):
    event_type: str = Field(..., description="事件类型")
    title: str = Field(..., max_length=128, description="事件标题")
    description: str | None = None
    event_date: date = Field(..., description="事件日期")
    mileage: int | None = Field(None, ge=0)
    cost: float | None = Field(None, ge=0)
    location: str | None = None
    severity: str | None = Field(None, description="严重程度")
    extra_data: dict[str, Any] | None = None


class LifecycleEventCreate(LifecycleEventBase):
    pass


class LifecycleEventOut(LifecycleEventBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    created_at: datetime


class LifecycleEventList(BaseModel):
    items: list[LifecycleEventOut]
    total: int = 0
