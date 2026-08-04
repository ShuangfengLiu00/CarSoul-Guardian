"""Maintenance record and schedule schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---- Records (historical) ----

class MaintenanceRecordBase(BaseModel):
    maintenance_type: str = Field(..., description="保养类型")
    category: str = Field(..., max_length=64, description="保养类别")
    title: str = Field(..., max_length=128)
    description: str | None = None
    maintenance_date: date = Field(..., description="保养日期")
    mileage: int | None = Field(None, ge=0)
    cost: float | None = Field(None, ge=0)
    service_provider: str | None = None
    technician: str | None = None
    parts: list[dict[str, Any]] | None = None
    next_maintenance_date: date | None = None
    next_maintenance_mileage: int | None = Field(None, ge=0)


class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass


class MaintenanceRecordOut(MaintenanceRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    created_at: datetime


class MaintenanceRecordList(BaseModel):
    items: list[MaintenanceRecordOut]
    total: int = 0


# ---- Schedules (planned) ----

class MaintenanceScheduleBase(BaseModel):
    item_name: str = Field(..., max_length=64)
    category: str = Field(..., max_length=64)
    interval_km: int | None = Field(None, ge=0)
    interval_days: int | None = Field(None, ge=0)
    last_mileage: int | None = Field(None, ge=0)
    last_date: date | None = None
    priority: str = "medium"
    notes: str | None = None


class MaintenanceScheduleCreate(MaintenanceScheduleBase):
    pass


class MaintenanceScheduleOut(MaintenanceScheduleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    next_due_km: int | None = None
    next_due_date: date | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class MaintenanceScheduleList(BaseModel):
    items: list[MaintenanceScheduleOut]
    total: int = 0
