"""Driving behaviour schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DrivingBehaviorBase(BaseModel):
    record_date: date = Field(..., description="记录日期")
    trip_count: int = Field(0, ge=0)
    total_distance: float = Field(0.0, ge=0, description="总距离(km)")
    total_duration: int = Field(0, ge=0, description="总时长(分钟)")
    avg_speed: float | None = Field(None, ge=0)
    max_speed: float | None = Field(None, ge=0)
    safety_score: int | None = Field(None, ge=0, le=100)
    eco_score: int | None = Field(None, ge=0, le=100)
    harsh_acceleration_count: int = Field(0, ge=0)
    harsh_braking_count: int = Field(0, ge=0)
    sharp_turn_count: int = Field(0, ge=0)
    overspeed_count: int = Field(0, ge=0)
    idle_duration: int = Field(0, ge=0, description="怠速时长(分钟)")
    fuel_consumption: float | None = Field(None, ge=0)
    energy_efficiency: float | None = Field(None, ge=0)


class DrivingBehaviorCreate(DrivingBehaviorBase):
    pass


class DrivingBehaviorOut(DrivingBehaviorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    created_at: datetime


class DrivingBehaviorList(BaseModel):
    items: list[DrivingBehaviorOut]
    total: int = 0
