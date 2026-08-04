"""Health snapshot schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthItemBase(BaseModel):
    category: str = Field(..., description="检测类别")
    item_name: str = Field(..., max_length=64, description="检测项名称")
    level: str = Field(..., description="等级: ok/info/warning/critical")
    score: int | None = Field(None, ge=0, le=100)
    detail: str | None = None
    recommendation: str | None = None


class HealthItemCreate(HealthItemBase):
    pass


class HealthItemOut(HealthItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    snapshot_id: int
    vehicle_id: int


class HealthSnapshotBase(BaseModel):
    health_score: int = Field(..., ge=0, le=100, description="综合健康指数")
    mileage: int = Field(..., ge=0)
    engine_score: int | None = Field(None, ge=0, le=100)
    brake_score: int | None = Field(None, ge=0, le=100)
    tire_score: int | None = Field(None, ge=0, le=100)
    battery_score: int | None = Field(None, ge=0, le=100)
    body_score: int | None = Field(None, ge=0, le=100)
    electronics_score: int | None = Field(None, ge=0, le=100)
    summary: str | None = None
    source: str = "manual"


class HealthSnapshotCreate(HealthSnapshotBase):
    items: list[HealthItemCreate] = Field(default_factory=list)


class HealthSnapshotOut(HealthSnapshotBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    snapshot_time: datetime
    items: list[HealthItemOut] = Field(default_factory=list)


class HealthSnapshotList(BaseModel):
    items: list[HealthSnapshotOut]
    total: int = 0
