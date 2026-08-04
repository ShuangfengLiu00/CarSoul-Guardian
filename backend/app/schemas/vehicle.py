"""Vehicle schemas — full digital-life archive (TASK007)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VehicleBase(BaseModel):
    brand: str = Field(..., description="品牌")
    model: str = Field(..., description="型号")
    year: int = Field(..., ge=1900, le=2100, description="年份")
    vin: str = Field(..., min_length=11, max_length=32, description="车辆识别码")
    plate_number: str | None = Field(None, max_length=20, description="车牌号")
    color: str | None = Field(None, max_length=32, description="颜色")
    nickname: str | None = Field(None, max_length=64, description="车辆昵称")

    # Powertrain
    engine_type: str | None = Field(None, description="引擎类型")
    fuel_type: str = Field("gasoline", description="燃料类型")
    displacement: float | None = Field(None, description="排量(L)")
    battery_capacity: float | None = Field(None, description="电池容量(kWh)")

    # Status
    mileage: int = Field(0, ge=0, description="行驶里程(km)")
    status: str = Field("active", description="状态")

    # Purchase
    purchase_date: date | None = Field(None, description="购车日期")
    purchase_price: float | None = Field(None, description="购车价格")
    dealer: str | None = Field(None, description="经销商")

    # Insurance
    insurance_company: str | None = Field(None, description="保险公司")
    insurance_policy_no: str | None = Field(None, description="保单号")
    insurance_expiry: date | None = Field(None, description="保险到期日")

    # Registration
    registration_date: date | None = Field(None, description="注册日期")
    inspection_expiry: date | None = Field(None, description="年检到期日")

    # Digital twin
    twin_model_id: str | None = Field(None, description="数字孪生模型ID")

    # Misc
    avatar_url: str | None = Field(None, description="车辆头像URL")
    notes: str | None = Field(None, description="备注")


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    """Partial update — all fields optional."""
    brand: str | None = None
    model: str | None = None
    year: int | None = Field(None, ge=1900, le=2100)
    vin: str | None = Field(None, min_length=11, max_length=32)
    plate_number: str | None = None
    color: str | None = None
    nickname: str | None = None
    engine_type: str | None = None
    fuel_type: str | None = None
    displacement: float | None = None
    battery_capacity: float | None = None
    mileage: int | None = Field(None, ge=0)
    status: str | None = None
    purchase_date: date | None = None
    purchase_price: float | None = None
    dealer: str | None = None
    insurance_company: str | None = None
    insurance_policy_no: str | None = None
    insurance_expiry: date | None = None
    registration_date: date | None = None
    inspection_expiry: date | None = None
    twin_model_id: str | None = None
    avatar_url: str | None = None
    notes: str | None = None


class VehicleOut(VehicleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int | None = None
    twin_last_sync: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VehicleList(BaseModel):
    items: list[VehicleOut]
    total: int = 0


class VehicleArchiveOut(BaseModel):
    """The complete digital-life archive for a single vehicle.

    Aggregates the vehicle profile with all related sub-entities:
    lifecycle timeline, latest health snapshot, maintenance records,
    schedules, recent driving behaviour, alerts, ownership history,
    and digital-twin metadata.
    """
    model_config = ConfigDict(from_attributes=True)

    vehicle: VehicleOut
    lifecycle_events: list["LifecycleEventOut"] = Field(default_factory=list)
    latest_health: "HealthSnapshotOut | None" = None
    health_history: list["HealthSnapshotOut"] = Field(default_factory=list)
    maintenance_records: list["MaintenanceRecordOut"] = Field(default_factory=list)
    maintenance_schedules: list["MaintenanceScheduleOut"] = Field(default_factory=list)
    driving_behaviors: list["DrivingBehaviorOut"] = Field(default_factory=list)
    alerts: list["AlertOut"] = Field(default_factory=list)
    ownership_history: list["OwnershipRecordOut"] = Field(default_factory=list)
    digital_twin: "DigitalTwinOut | None" = None

    # ---- Computed summary ----
    health_score: int | None = None
    active_alert_count: int = 0
    total_maintenance_cost: float = 0.0
    next_maintenance_items: list[dict[str, Any]] = Field(default_factory=list)


# Forward references resolved at bottom of archive.py
from app.schemas.alert import AlertOut  # noqa: E402
from app.schemas.digital_twin import DigitalTwinOut  # noqa: E402
from app.schemas.driving_behavior import DrivingBehaviorOut  # noqa: E402
from app.schemas.health_snapshot import HealthSnapshotOut  # noqa: E402
from app.schemas.lifecycle_event import LifecycleEventOut  # noqa: E402
from app.schemas.maintenance import (  # noqa: E402
    MaintenanceRecordOut,
    MaintenanceScheduleOut,
)
from app.schemas.ownership_record import OwnershipRecordOut  # noqa: E402

VehicleArchiveOut.model_rebuild()
