"""Fault log schemas — vehicle disease history."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FaultLogBase(BaseModel):
    fault_code: str = Field(..., max_length=50, description="OBD故障码")
    fault_level: str = Field("medium", description="危险等级 low|medium|high|critical")
    description: str | None = Field(None, description="故障描述")
    system: str | None = Field(None, max_length=32, description="所属系统")
    repair_status: str = Field("active", description="修复状态")
    mileage: int | None = Field(None, ge=0, description="发生时里程")
    occur_time: datetime | None = Field(None, description="发生时间")
    maintenance_record_id: int | None = None


class FaultLogCreate(FaultLogBase):
    pass


class FaultLogUpdate(BaseModel):
    fault_level: str | None = None
    description: str | None = None
    repair_status: str | None = None
    resolved_time: datetime | None = None
    maintenance_record_id: int | None = None


class FaultLogOut(FaultLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    occur_time: datetime
    resolved_time: datetime | None = None
    created_at: datetime


class FaultLogList(BaseModel):
    items: list[FaultLogOut]
    total: int = 0
