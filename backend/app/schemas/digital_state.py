"""Digital state schemas — real-time vehicle current state."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DigitalStateBase(BaseModel):
    engine_health: float | None = Field(None, ge=0, le=100)
    battery_health: float | None = Field(None, ge=0, le=100)
    brake_health: float | None = Field(None, ge=0, le=100)
    tire_health: float | None = Field(None, ge=0, le=100)
    body_health: float | None = Field(None, ge=0, le=100)
    electronics_health: float | None = Field(None, ge=0, le=100)
    overall_score: float | None = Field(None, ge=0, le=100)
    status: str = Field("GOOD", description="GOOD|WARNING|DANGER|END_OF_LIFE")
    temperature: float | None = Field(None, description="温度(℃)")
    mileage: int | None = Field(None, ge=0)
    fuel_level: float | None = Field(None, description="油量/电量(%)")
    location: dict[str, Any] | None = None


class DigitalStateCreate(DigitalStateBase):
    pass


class DigitalStateUpdate(DigitalStateBase):
    """Partial update — all fields optional."""
    engine_health: float | None = None
    battery_health: float | None = None
    brake_health: float | None = None
    tire_health: float | None = None
    body_health: float | None = None
    electronics_health: float | None = None
    overall_score: float | None = None
    status: str | None = None
    temperature: float | None = None
    mileage: int | None = None
    fuel_level: float | None = None
    location: dict[str, Any] | None = None


class DigitalStateOut(DigitalStateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    updated_at: datetime
    created_at: datetime
