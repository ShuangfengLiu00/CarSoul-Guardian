"""Sensor data schemas — IoT telemetry time-series."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


# ---------------------------------------------------------------------------
# Full-vehicle sensor snapshot (6 domains / 58 signals)
# ---------------------------------------------------------------------------

class SensorSpecOut(BaseModel):
    """Static registry metadata for one sensor (ranges, thresholds, sampling)."""
    min: float
    max: float
    warn_low: float | None = None
    warn_high: float | None = None
    crit_low: float | None = None
    crit_high: float | None = None
    step: float
    sample_hz_can: float
    sample_hz_upload: float
    adjustable: bool


class SensorSnapshotSensor(BaseModel):
    """One sensor's current value plus its spec and derived status."""
    sensor_type: str
    label: str
    value: float
    unit: str | None = None
    spec: SensorSpecOut | None = None
    status: Literal["normal", "warn", "crit"] = "normal"
    source: str = Field("seed", description="db | default")


class SensorSnapshotDomain(BaseModel):
    """One sensor domain and its signals."""
    domain: str
    label: str
    vhs_component: str
    vhs_weight: float
    sensors: list[SensorSnapshotSensor]


class SensorSnapshotResponse(BaseModel):
    """Full-vehicle sensor snapshot — the simulation panel's baseline."""
    vehicle_id: int
    as_of: datetime
    energy_type: str
    domains: list[SensorSnapshotDomain]
    baseline: dict[str, Any] = Field(
        default_factory=dict,
        description="health_score / grade / grade_label / breakdown",
    )
    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="GOAI 数据来源溯源信封（data_source/demo_mode/badge_level/...）",
    )
