"""Sensor data schemas — IoT telemetry time-series."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SensorDataBase(BaseModel):
    sensor_type: str = Field(..., max_length=50, description="传感器类型")
    sensor_value: float = Field(..., description="传感器数值")
    unit: str | None = Field(None, max_length=20, description="单位")
    meta: dict[str, Any] | None = Field(None, description="附加元数据")


class SensorDataCreate(SensorDataBase):
    pass


class SensorDataBatchCreate(BaseModel):
    """Batch ingestion of sensor readings (one vehicle, many readings)."""
    readings: list[SensorDataCreate] = Field(..., min_length=1)


class SensorDataOut(SensorDataBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    created_at: datetime


class SensorDataList(BaseModel):
    items: list[SensorDataOut]
    total: int = 0


class SensorSeriesPoint(BaseModel):
    """A single point in a sensor time-series (for charting)."""
    timestamp: datetime
    value: float


class SensorSeriesOut(BaseModel):
    """Aggregated time-series for one sensor type."""
    sensor_type: str
    unit: str | None = None
    points: list[SensorSeriesPoint]
