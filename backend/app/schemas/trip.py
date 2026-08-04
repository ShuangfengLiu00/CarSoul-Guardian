"""Trip schemas — per-journey records."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TripBase(BaseModel):
    start_time: datetime = Field(..., description="出发时间")
    end_time: datetime | None = Field(None, description="到达时间")
    distance: float = Field(0.0, ge=0, description="距离(km)")
    average_speed: float | None = Field(None, ge=0, description="平均速度(km/h)")
    max_speed: float | None = Field(None, ge=0, description="最高速度(km/h)")
    energy_consumption: float | None = Field(None, ge=0, description="能耗(L或kWh)")
    road_condition: str | None = Field(None, max_length=32, description="路况")
    weather: str | None = Field(None, max_length=32, description="天气")
    harsh_acceleration_count: int = Field(0, ge=0)
    harsh_braking_count: int = Field(0, ge=0)
    overspeed_count: int = Field(0, ge=0)
    start_location: dict[str, Any] | None = Field(None)
    end_location: dict[str, Any] | None = Field(None)
    notes: str | None = Field(None, max_length=256)
    driver_id: int | None = None


class TripCreate(TripBase):
    pass


class TripOut(TripBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    created_at: datetime


class TripList(BaseModel):
    items: list[TripOut]
    total: int = 0


class TripSummary(BaseModel):
    """Aggregated trip statistics for a vehicle over a period."""
    trip_count: int = 0
    total_distance: float = 0.0
    total_duration_hours: float = 0.0
    total_energy: float = 0.0
    avg_speed: float | None = None
    harsh_events: int = 0
    first_trip_time: datetime | None = None
    last_trip_time: datetime | None = None
